"""Blank temp_c on list / detail projections."""

def blank_temp_value(temp_c):
    return 0

def blank_list_item(item: dict) -> None:
    item["temp_c"] = blank_temp_value(item.get("temp_c"))

def blank_create_item(item: dict) -> None:
    item["temp_c"] = blank_temp_value(item.get("temp_c"))

def should_blank_path(path: str) -> bool:
    return path in {"list", "create"}

