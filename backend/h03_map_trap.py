from h03_queue_blank import assert_blanked, project_surfaces
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
    sample = {"temp_c": 4.2, "probe_id": "A01"}
    mapped = map_one(sample, "list")
    return assert_blanked(mapped)

