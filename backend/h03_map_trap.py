"""列表 / 单卡取温字段的映射组装。

三条组装链路（列表、单卡排队、投影）必须一致保留当初温度，
不得在映射时掏空。映射为纯函数：不修改入参，重复调用 / 翻页后结果同值。
"""

from h03_queue_blank import assert_temp_preserved, project_surfaces
from h03_extra_trap import apply_blank


def map_list_payload(items: list) -> list:
    out = []
    for it in items:
        d = apply_blank(dict(it), "list")
        out.append(project_surfaces(d))
    return out


def map_one(item: dict, path: str) -> dict:
    return project_surfaces(apply_blank(dict(item), path))


def self_check():
    # 甲探样例：探头A01 当初 4.2℃，三处投影后必须仍等于 4.2。
    sample = {"temp_c": 4.2, "probe_id": "A01"}
    mapped = map_one(sample, "list")
    return assert_temp_preserved(mapped, 4.2)
