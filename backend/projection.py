"""读数多界面投影：首页表格、单卡（排队栏 / 详情）共用同一份温度原值。

历史上本模块曾把 temp_c 掏空（排队栏置 0、单卡置 None、详情置 0），
导致三处界面偶发显示空白或零。现约定：

- temp_c 在任何投影中都必须等于入库时的原始读数，不得改写、清零或置空；
- 只允许新增派生展示字段（temp_display），且必须由原值格式化而来。
"""


def format_temp(temp_c) -> str:
    if temp_c is None:
        return ""
    return f"{float(temp_c):g}℃"


def project_queue_row(row: dict) -> dict:
    """排队栏（待处理队列）投影：温度保持原值。"""
    out = dict(row)
    out["temp_display"] = format_temp(out.get("temp_c"))
    return out


def project_card(row: dict) -> dict:
    """单卡投影：温度保持原值，展示串由原值派生。"""
    out = dict(row)
    out["temp_display"] = format_temp(out.get("temp_c"))
    return out


def project_detail(row: dict) -> dict:
    """单卡详情投影：温度保持原值。"""
    out = dict(row)
    out["temp_display"] = format_temp(out.get("temp_c"))
    return out


def project_surfaces(row: dict) -> dict:
    """组装三处界面（排队栏 / 单卡 / 详情）。

    三处的 temp_c 必须与入参原值严格相等，重复组装（翻页 / 刷新）幂等。
    """
    out = project_queue_row(dict(row))
    out = project_card(out)
    out = project_detail(out)
    return out


def map_list_payload(items: list) -> list:
    """首页表格列表组装：逐条做三面投影，每条 temp_c 等于原值。"""
    return [project_surfaces(it) for it in items]


def map_one(item: dict) -> dict:
    """单条读数（提交回包 / 直读单条）组装，temp_c 等于原值。"""
    return project_surfaces(dict(item))
