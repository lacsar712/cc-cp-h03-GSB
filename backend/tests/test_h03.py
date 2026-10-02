"""H03 温度对拍回归。

样例（甲探）：探头A01 = 4.2℃（合格），探头B02 = 12.5℃（超温）。

验收点：
1. 三处组装——首页表格 map_list_payload、单卡排队栏 project_queue_row /
   project_card、详情 project_detail（project_surfaces 合装）——temp_c 必须
   等于原始温度，不得变为 0 / None / 空白；
2. 直读接口 GET /api/readings 与提交接口 POST 回包的 temp_c 等于库值；
3. 空窗（列表清空）翻页 / 反复刷新后，三处仍与原值同值；
4. 0.0℃ 是合法读数，必须显示为 0，不得被遮成空白；
5. 工人处理完成后温度不变，结论正确。
"""

import asyncio
import importlib
import os
from pathlib import Path

import pytest

from db import DSN
from projection import (
    format_temp,
    map_list_payload,
    map_one,
    project_card,
    project_detail,
    project_queue_row,
    project_surfaces,
)

# 甲探样例：提交入库时的原始读数
A01 = {"id": 1, "probe_id": "探头A01", "temp_c": 4.2}
B02 = {"id": 2, "probe_id": "探头B02", "temp_c": 12.5}

BACKEND_DIR = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# A. 三处组装对拍：温度必须原样透传
# ---------------------------------------------------------------------------


def test_queue_row_keeps_temp():
    """单卡排队栏：temp_c 不置 0，temp_display 不掏空。"""
    q = project_queue_row(dict(A01))
    assert q["temp_c"] == 4.2
    assert q["temp_display"] == "4.2℃"


def test_card_keeps_temp_and_footnote():
    """单卡：temp_c 不置 None，已有脚注不被清空。"""
    card = project_card({**A01, "footnote": "甲探复核"})
    assert card["temp_c"] == 4.2
    assert card["temp_display"] == "4.2℃"
    assert card["footnote"] == "甲探复核"


def test_detail_keeps_temp():
    """详情：temp_c 不置 0。"""
    assert project_detail(dict(A01))["temp_c"] == 4.2


def test_surfaces_three_places_equal_origin():
    """排队栏 / 单卡 / 详情三面合装：三处都等于当初温度。"""
    s = project_surfaces(dict(A01))
    assert s["temp_c"] == 4.2
    assert s["temp_display"] == "4.2℃"

    s_b = project_surfaces(dict(B02))
    assert s_b["temp_c"] == 12.5
    assert s_b["temp_display"] == "12.5℃"


def test_map_list_payload_table_keeps_temp():
    """首页表格组装：逐行温度等于入库原值。"""
    rows = map_list_payload([dict(A01), dict(B02)])
    assert [r["temp_c"] for r in rows] == [4.2, 12.5]
    assert [r["probe_id"] for r in rows] == ["探头A01", "探头B02"]


def test_map_one_keeps_temp():
    assert map_one(dict(A01))["temp_c"] == 4.2


def test_zero_reading_is_preserved_not_blanked():
    """0.0℃ 是合法读数：任何界面都必须保留为 0，展示为 0℃。"""
    zero = {"id": 3, "probe_id": "探头Z00", "temp_c": 0.0}
    assert project_queue_row(dict(zero))["temp_c"] == 0.0
    assert project_card(dict(zero))["temp_c"] == 0.0
    assert project_detail(dict(zero))["temp_c"] == 0.0
    assert project_surfaces(dict(zero))["temp_display"] == "0℃"
    assert map_list_payload([dict(zero)])[0]["temp_c"] == 0.0


def test_format_temp_rules():
    assert format_temp(4.2) == "4.2℃"
    assert format_temp(0) == "0℃"
    assert format_temp(None) == ""


def test_projection_idempotent_across_pages_and_refresh():
    """翻页 / 刷新=反复组装：幂等，第三次组装后三处仍同值。"""
    once = project_surfaces(dict(A01))
    twice = project_surfaces(dict(once))
    thrice = project_surfaces(dict(twice))
    for s in (once, twice, thrice):
        assert s["temp_c"] == 4.2
        assert s["temp_display"] == "4.2℃"
    # 翻页：第 1 页与第 2 次取页结果一致
    page_one = map_list_payload([dict(A01)])
    page_two = map_list_payload([dict(A01)])
    assert page_one == page_two


def test_trap_modules_removed():
    """四个清零陷阱模块必须已移除，任何 import 都不应复活。"""
    for name in (
        "temp_blank",
        "h03_extra_trap",
        "h03_queue_blank",
        "h03_map_trap",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(name)


def test_api_source_has_no_blank_hook():
    """直读接口源码中不得再有清零钩子。"""
    source = (BACKEND_DIR / "api.py").read_text(encoding="utf-8")
    assert "apply_blank" not in source
    assert "blank" not in source.lower()


# ---------------------------------------------------------------------------
# B. 真实 PostgreSQL 端到端：直读接口 / 提交 / 空窗翻页 / 刷新
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


async def _start_app():
    from aiohttp.test_utils import TestClient, TestServer

    from api import create_app
    from db import seed_if_empty

    app = create_app()
    client = TestClient(TestServer(app))
    await client.start_server()
    # 每个用例从干净表开始，只保留甲探种子
    await app["pool"].execute("TRUNCATE probe_readings RESTART IDENTITY")
    await seed_if_empty(app["pool"])
    return app, client


async def _token(client, username="logger", password="log123456"):
    resp = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert resp.status == 200
    return (await resp.json())["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _get_readings(client, token):
    resp = await client.get("/api/readings", headers=_auth(token))
    assert resp.status == 200
    return await resp.json()


def _find(rows, probe_id):
    return next(r for r in rows if r["probe_id"] == probe_id)


def test_get_readings_matches_db_seed(pg_server):
    """刷新后页面与直读接口同值：GET 返回的 A01=4.2、B02=12.5。"""

    async def scenario():
        import asyncpg

        app, client = await _start_app()
        try:
            token = await _token(client)
            rows = await _get_readings(client, token)
            a01 = _find(rows, "探头A01")
            b02 = _find(rows, "探头B02")

            pool = await asyncpg.create_pool(DSN)
            async with pool.acquire() as conn:
                db_a01 = await conn.fetchval(
                    "SELECT temp_c FROM probe_readings WHERE probe_id='探头A01'"
                )
                db_b02 = await conn.fetchval(
                    "SELECT temp_c FROM probe_readings WHERE probe_id='探头B02'"
                )
            await pool.close()

            # 接口值 == 库值 == 甲探原始温度
            assert a01["temp_c"] == db_a01 == 4.2
            assert b02["temp_c"] == db_b02 == 12.5

            # 页面三面（排队栏/单卡/详情）由接口行组装，三处与接口同值
            surfaces = project_surfaces(dict(a01))
            assert surfaces["temp_c"] == a01["temp_c"] == 4.2
        finally:
            await client.close()

    _run(scenario())


def test_post_reading_echoes_origin_and_list_keeps_it(pg_server):
    """提交甲探读数：回包温度=原值，列表中该行温度=原值。"""

    async def scenario():
        app, client = await _start_app()
        try:
            token = await _token(client)
            resp = await client.post(
                "/api/readings",
                headers=_auth(token),
                json={"probe_id": "探头A01", "temp_c": 4.2},
            )
            assert resp.status == 201
            created = await resp.json()
            assert created["temp_c"] == 4.2
            assert map_one(created)["temp_c"] == 4.2

            rows = await _get_readings(client, token)
            assert _find(rows, "探头A01")["temp_c"] == 4.2
        finally:
            await client.close()

    _run(scenario())


def test_refresh_and_pagination_keep_three_surfaces_stable(pg_server):
    """反复刷新（3 次 GET）+ 模拟翻页（两次取页）：三处始终 4.2。"""

    async def scenario():
        app, client = await _start_app()
        try:
            token = await _token(client)
            seen = []
            for _ in range(3):  # 刷新
                rows = await _get_readings(client, token)
                seen.append(_find(rows, "探头A01")["temp_c"])
            assert seen == [4.2, 4.2, 4.2]

            # 翻页：对接口行分别做首页表格组装，两页同值
            page1 = map_list_payload(await _get_readings(client, token))
            page2 = map_list_payload(await _get_readings(client, token))
            assert _find(page1, "探头A01")["temp_c"] == 4.2
            assert _find(page2, "探头A01")["temp_c"] == 4.2
        finally:
            await client.close()

    _run(scenario())


def test_empty_window_then_value_returns_everywhere(pg_server):
    """空窗：清空列表后接口返回空数组（不回退 0/None）；
    重新写入甲探后，接口与三处投影恢复同值。"""

    async def scenario():
        app, client = await _start_app()
        try:
            token = await _token(client)
            await app["pool"].execute("TRUNCATE probe_readings RESTART IDENTITY")

            empty = await _get_readings(client, token)
            assert empty == []  # 空窗就是空窗，不造 0 值行

            # 甲探重新上报
            resp = await client.post(
                "/api/readings",
                headers=_auth(token),
                json={"probe_id": "探头A01", "temp_c": 4.2},
            )
            assert resp.status == 201
            rows = await _get_readings(client, token)
            a01 = _find(rows, "探头A01")

            # 空窗翻页后：接口行 → 三处投影仍同值
            queue_row = project_queue_row(dict(a01))
            card = project_card(dict(a01))
            detail = project_detail(dict(a01))
            assert a01["temp_c"] == 4.2
            assert queue_row["temp_c"] == card["temp_c"] == detail["temp_c"] == 4.2
            assert queue_row["temp_display"] == "4.2℃"
        finally:
            await client.close()

    _run(scenario())


def test_zero_temp_roundtrip(pg_server):
    """0.0℃ 读数经提交、工人前的 pending 列表、再刷新：仍是数字 0。"""

    async def scenario():
        app, client = await _start_app()
        try:
            token = await _token(client)
            resp = await client.post(
                "/api/readings",
                headers=_auth(token),
                json={"probe_id": "探头Z00", "temp_c": 0},
            )
            assert resp.status == 201
            created = await resp.json()
            assert created["temp_c"] == 0.0

            rows = await _get_readings(client, token)
            z = _find(rows, "探头Z00")
            assert z["temp_c"] == 0.0  # 不允许变成 None/空白
            assert project_card(dict(z))["temp_display"] == "0℃"
        finally:
            await client.close()

    _run(scenario())


# ---------------------------------------------------------------------------
# C. 后台工人认领判定后温度不变
# ---------------------------------------------------------------------------


def test_worker_keeps_temp_and_judges(pg_server):
    """pending 读数被工人认领处理后：temp_c 仍为 4.2 / 12.5，结论正确。"""

    async def scenario():
        import psycopg

        from db import connect_sync
        from worker import run_once

        app, client = await _start_app()
        try:
            token = await _token(client)
            for probe, temp in (("探头A01", 4.2), ("探头B02", 12.5)):
                resp = await client.post(
                    "/api/readings",
                    headers=_auth(token),
                    json={"probe_id": probe, "temp_c": temp},
                )
                assert resp.status == 201

            # 工人逐条认领（psycopg 同步连接，独立事务）
            with connect_sync() as conn:
                assert run_once(conn) is True  # A01 合格
            with connect_sync() as conn:
                assert run_once(conn) is True  # B02 超温
            with connect_sync() as conn:
                assert run_once(conn) is False  # 队列已空

            rows = await _get_readings(client, token)
            a01 = _find(rows, "探头A01")
            b02 = _find(rows, "探头B02")
            assert a01["temp_c"] == 4.2 and a01["status"] == "done"
            assert a01["verdict"] == "合格"
            assert b02["temp_c"] == 12.5 and b02["status"] == "done"
            assert b02["verdict"] == "超温"

            # 直连库复核：接口值 == 库值
            with psycopg.connect(DSN) as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT probe_id, temp_c, verdict FROM probe_readings "
                    "WHERE probe_id IN ('探头A01','探头B02') ORDER BY probe_id"
                )
                db_rows = cur.fetchall()
            db_map = {r[0]: (float(r[1]), r[2]) for r in db_rows}
            assert db_map["探头A01"] == (4.2, "合格")
            assert db_map["探头B02"] == (12.5, "超温")
        finally:
            await client.close()

    _run(scenario())
