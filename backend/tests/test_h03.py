from h03_extra_trap import apply_blank
from h03_map_trap import map_list_payload, self_check
from h03_queue_blank import blank_card, blank_queue_row

def test_blank_list():
    d = {"temp_c": 4.2}
    apply_blank(d, "list")
    assert d["temp_c"] == 0

def test_queue_blank():
    assert blank_queue_row({"temp_c": 4.2})["temp_c"] == 0

def test_card_blank():
    assert blank_card({"temp_c": 4.2})["temp_c"] is None

def test_map_list():
    rows = map_list_payload([{"temp_c": 4.2, "probe_id": "A01"}])
    assert rows[0]["temp_c"] in (0, None)

def test_self_check():
    assert self_check() is True

