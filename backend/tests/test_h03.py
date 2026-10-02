"""H03 对拍：列表组装 / 单卡排队栏 / 投影三处温度必须都等于当初温度。

甲探样例：探头A01 = 4.2℃（合格）；乙探样例：探头B02 = 12.5℃（超温）。
另覆盖合法 0℃、空列表（空窗）、翻页重复映射、直读接口与页面同源同值。
"""

import json
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase

from aiohttp.test_utils import TestClient, TestServer
import jwt

from h03_extra_trap import apply_blank
from h03_map_trap import map_list_payload, map_one, self_check
from h03_queue_blank import (
    assert_temp_preserved,
    blank_card,
    blank_detail,
    blank_queue_row,
    project_surfaces,
)
from temp_blank import blank_list_item, original_temp_value, should_blank_path

# 甲探上报的当初温度，所有面都必须与它一致。
JIA_PROBE = "探头A01"
JIA_TEMP = 4.2
YI_PROBE = "探头B02"
YI_TEMP = 12.5


def _jia_row(temp_c=JIA_TEMP, **extra):
    row = {
        "id": 1,
        "probe_id": JIA_PROBE,
        "temp_c": temp_c,
        "verdict": "合格",
        "reason": "探头温度未超过 8℃ 上限",
        "status": "done",
        "created_by": "logger",
        "temp_display": str(temp_c),
    }
    row.update(extra)
    return row


# ---------- 取温字段 ----------

def test_original_temp_value_passes_through():
    assert original_temp_value(JIA_TEMP) == JIA_TEMP
    assert original_temp_value(0) == 0
    assert original_temp_value(-3.5) == -3.5


def test_no_path_is_blanked():
    # 任何投影面都不允许掏空。
    assert should_blank_path("list") is False
    assert should_blank_path("create") is False
    assert should_blank_path("queue") is False


# ---------- 组装点 1：首页表格列表 ----------

def test_list_assembly_keeps_temp():
    item = _jia_row()
    blank_list_item(item)
    assert item["temp_c"] == JIA_TEMP


def test_apply_blank_list_and_create_keep_temp():
    for path in ("list", "create"):
        item = _jia_row(temp_c=YI_TEMP, probe_id=YI_PROBE)
        apply_blank(item, path)
        assert item["temp_c"] == YI_TEMP


def test_list_assembly_keeps_legitimate_zero():
    item = _jia_row(temp_c=0)
    blank_list_item(item)
    assert item["temp_c"] == 0  # 合法 0℃ 不得被当成空值清掉


# ---------- 组装点 2：单卡排队栏 ----------

def test_queue_row_keeps_temp_and_display():
    row = blank_queue_row(_jia_row())
    assert row["temp_c"] == JIA_TEMP
    assert row["temp_display"] == str(JIA_TEMP)  # 排队栏文案不得为空


def test_queue_row_zero_temp_display_nonempty():
    row = blank_queue_row(_jia_row(temp_c=0, temp_display="0"))
    assert row["temp_c"] == 0
    assert row["temp_display"] == "0"


def test_card_and_detail_keep_temp():
    assert blank_card(_jia_row())["temp_c"] == JIA_TEMP
    assert blank_detail(_jia_row(temp_c=YI_TEMP))["temp_c"] == YI_TEMP


# ---------- 组装点 3：投影 ----------

def test_project_surfaces_all_three_equal_original():
    projected = project_surfaces(_jia_row())
    assert assert_temp_preserved(projected, JIA_TEMP) is True
    # 三处显式逐一核对
    assert projected["temp_c"] == JIA_TEMP
    assert projected["temp_display"] == str(JIA_TEMP)


def test_project_does_not_mutate_input():
    src = _jia_row()
    project_surfaces(src)
    assert src["temp_c"] == JIA_TEMP
    assert src["temp_display"] == str(JIA_TEMP)


def test_map_list_payload_jia_yi_pair():
    rows = map_list_payload(
        [
            _jia_row(),
            _jia_row(temp_c=YI_TEMP, probe_id=YI_PROBE, verdict="超温", id=2),
        ]
    )
    assert rows[0]["probe_id"] == JIA_PROBE
    assert rows[0]["temp_c"] == JIA_TEMP
    assert rows[1]["probe_id"] == YI_PROBE
    assert rows[1]["temp_c"] == YI_TEMP


def test_self_check_passes_with_original_temp():
    assert self_check() is True


# ---------- 空窗翻页：空列表、重复映射、多页结果同值 ----------

def test_empty_window_maps_to_empty():
    assert map_list_payload([]) == []


def test_pagination_pages_keep_same_values():
    page1 = map_list_payload([_jia_row(id=1)])
    # 翻页后对同一读数再次组装（空窗刷新场景），值必须仍一致
    page2 = map_list_payload([_jia_row(id=1)])
    page3 = map_list_payload([map_one(_jia_row(id=1), "list")])  # 二次投影幂等
    for page in (page1, page2, page3):
        assert page[0]["temp_c"] == JIA_TEMP
        assert page[0]["temp_display"] == str(JIA_TEMP)


def test_repeated_projection_is_idempotent():
    row = _jia_row()
    once = project_surfaces(dict(row))
    twice = project_surfaces(dict(once))
    assert twice["temp_c"] == JIA_TEMP
    assert twice["temp_display"] == str(JIA_TEMP)


# ---------- 直读接口对拍：接口返回必须等于库行原值 ----------

class _FakePool:
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, _sql):
        return list(self._rows)


def _db_row(rid, probe_id, temp_c, verdict, status="done"):
    return {
        "id": rid,
        "probe_id": probe_id,
        "temp_c": temp_c,
        "verdict": verdict,
        "reason": "x",
        "status": status,
        "created_by": "logger",
        "created_at": datetime(2026, 10, 2, tzinfo=timezone.utc),
        "processed_at": datetime(2026, 10, 2, tzinfo=timezone.utc),
    }


class ApiDifferentialTests(IsolatedAsyncioTestCase):
    async def test_readings_api_matches_direct_rows(self):
        from api import create_app, SECRET

        db_rows = [
            _db_row(2, YI_PROBE, 12.5, "超温"),
            _db_row(1, JIA_PROBE, 4.2, "合格"),
            _db_row(3, "探头Z00", 0, "合格"),
        ]
        app = create_app()
        app.on_startup.clear()
        app.on_cleanup.clear()
        app["pool"] = _FakePool(db_rows)

        token = jwt.encode({"sub": "watcher", "role": "reader"}, SECRET, algorithm="HS256")
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            res = await client.get(
                "/api/readings", headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(res.status, 200)
            payload = json.loads(await res.text())
        finally:
            await client.close()

        # 页面表格直接渲染 payload 的 temp_c，因此接口与页面同源：
        # 逐条对拍接口 JSON 与库行（直读）原值。
        self.assertEqual(len(payload), len(db_rows))
        for got, db in zip(payload, db_rows):
            self.assertEqual(got["probe_id"], db["probe_id"])
            self.assertEqual(got["temp_c"], db["temp_c"], msg=db["probe_id"])
            self.assertIsNotNone(got["temp_c"])

        by_probe = {r["probe_id"]: r["temp_c"] for r in payload}
        self.assertEqual(by_probe[JIA_PROBE], JIA_TEMP)
        self.assertEqual(by_probe[YI_PROBE], YI_TEMP)
        self.assertEqual(by_probe["探头Z00"], 0)  # 合法 0℃ 正常返回
