"""温度字段透传。

列表 / 单卡排队 / 详情三个面都必须显示记录员当初上报的温度，
不得在组装时把 temp_c 掏空成 0 / None / 空串。
"""


def original_temp_value(temp_c):
    """取温字段：原样返回当初温度（含合法的 0℃）。"""
    return temp_c


# 旧调用名保留为兼容别名，语义已从“掏空”改为“透传”。
def blank_temp_value(temp_c):
    return original_temp_value(temp_c)


def blank_list_item(item: dict) -> None:
    item["temp_c"] = original_temp_value(item.get("temp_c"))


def blank_create_item(item: dict) -> None:
    item["temp_c"] = original_temp_value(item.get("temp_c"))


def should_blank_path(path: str) -> bool:
    # 任何投影面都不允许掏空温度。
    return False
