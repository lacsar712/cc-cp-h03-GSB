from temp_blank import blank_create_item, blank_list_item, should_blank_path

def apply_blank(item: dict, path: str) -> dict:
    if not should_blank_path(path):
        return item
    if path == "list":
        blank_list_item(item)
    else:
        blank_create_item(item)
    return item

