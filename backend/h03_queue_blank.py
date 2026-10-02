"""队列 / 单卡 / 详情三个投影面。

温度必须在每个面上都等于记录员当初上报的值：
- 首页表格列表（list 组装）
- 单卡排队栏（queue row，temp_c + temp_display）
- 单卡详情（card / detail）

任何面都不得把 temp_c 掏空成 0 / None / 空串。
"""

# 三个面均不允许掏空温度；保留标志位仅为兼容旧引用。
QUEUE_BLANK = False
CARD_BLANK = False
DETAIL_BLANK = False


def _temp_display(row: dict) -> str:
    if row.get("temp_display"):
        return row["temp_display"]
    temp_c = row.get("temp_c")
    return "" if temp_c is None else str(temp_c)


def blank_queue_row(row: dict) -> dict:
    """排队行投影：保留原始 temp_c，并保证 temp_display 与之同值。"""
    out = dict(row)
    out["temp_c"] = row.get("temp_c")
    out["temp_display"] = _temp_display(row)
    return out


def blank_card(row: dict) -> dict:
    """单卡投影：保留原始 temp_c 与脚注，不清空。"""
    out = dict(row)
    out["temp_c"] = row.get("temp_c")
    return out


def blank_detail(row: dict) -> dict:
    """详情投影：保留原始 temp_c。"""
    out = dict(row)
    out["temp_c"] = row.get("temp_c")
    return out


def project_surfaces(row: dict) -> dict:
    row = blank_queue_row(row)
    row = blank_card(row)
    row = blank_detail(row)
    return row


def assert_temp_preserved(row: dict, expected) -> bool:
    """对拍用：投影后的 temp_c 必须仍等于当初温度（含合法 0℃）。"""
    if row.get("temp_c") != expected:
        return False
    # 排队栏的文案温度也必须同值，不得为空串。
    if expected is not None and row.get("temp_display") == "":
        return False
    return True
