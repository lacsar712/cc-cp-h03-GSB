"""Queue / card projection also blanks temp for H03 multi-surface plant."""

QUEUE_BLANK = True
CARD_BLANK = True
DETAIL_BLANK = True

def blank_queue_row(row: dict) -> dict:
    if not QUEUE_BLANK:
        return row
    out = dict(row)
    out["temp_c"] = 0
    out["temp_display"] = ""
    return out

def blank_card(row: dict) -> dict:
    if not CARD_BLANK:
        return row
    out = dict(row)
    out["temp_c"] = None
    out["footnote"] = ""
    return out

def blank_detail(row: dict) -> dict:
    if not DETAIL_BLANK:
        return row
    out = dict(row)
    out["temp_c"] = 0
    return out

def project_surfaces(row: dict) -> dict:
    row = blank_queue_row(row)
    row = blank_card(row)
    row = blank_detail(row)
    return row

def assert_blanked(row: dict) -> bool:
    return row.get("temp_c") in (0, None, "")

