#!/usr/bin/env python3
"""Rights gate and review queue cannot silently approve viral downloads."""
from approved_manifest import build_manifest
from rights_review import queue_rows
rows=queue_rows([{"title":"Real football moment","url":"https://www.youtube.com/watch?v=abc",
                  "views":1000000,"views_per_day":500000}])
assert rows[0]["reuse_rights_status"]=="NOT_GRANTED"
assert rows[0]["authenticity_status"]=="NEEDS_MANUAL_VERIFICATION"
assert rows[0]["approved_mp4_url"]==""
try:
    build_manifest({"title":"TOP 5","clips":[]})
except ValueError:
    pass
else:
    raise AssertionError("Empty inventory must fail closed")
template=lambda rank:{"rank":rank,"source_page":f"https://owner.example/clip-{rank}",
    "approved_mp4_url":f"https://cdn.example/clip-{rank}.mp4",
    "permission_evidence_url":f"https://owner.example/permissions/{rank}",
    "rights_basis":"creator_permission","rights_holder":f"Creator {rank}",
    "reviewer":"Channel owner","reviewed_at":"2026-10-27",
    "authenticity_reviewed":True,"rights_reviewed":True,
    "label":f"REAL MOMENT {rank}"}
approved=[template(r) for r in range(5,0,-1)]
manifest=build_manifest({"title":"TOP 5 REAL MOMENTS","clips":approved})
assert len(manifest["clips"])==5
assert manifest["clips"][0]["rank"]==5
for change in [
    {"rights_reviewed":False},
    {"authenticity_reviewed":False},
    {"approved_mp4_url":"https://www.youtube.com/watch?v=abc"},
    {"permission_evidence_url":""},
    {"label":"AI-generated motorcycle stunt"},
]:
    modified=[dict(c) for c in approved]
    modified[0].update(change)
    try:
        build_manifest({"title":"TOP 5 REAL MOMENTS","clips":modified})
    except ValueError:
        pass
    else:
        raise AssertionError(f"Should reject {change}")
print("PASS: viral research rights queue, approved real footage and rejection cases")
