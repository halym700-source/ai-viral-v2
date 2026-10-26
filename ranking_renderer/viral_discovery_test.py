#!/usr/bin/env python3
"""Offline tests: ranking signals do not imply authenticity or reuse rights."""
import datetime as dt
from viral_discovery import rank_candidates, synthetic
now=dt.datetime(2026,10,27,tzinfo=dt.timezone.utc)
pages=[("real sports fails shorts",[
    {"id":{"videoId":"real1"},"snippet":{"title":"Skateboard fail captured live",
     "publishedAt":"2026-10-25T00:00:00Z","channelTitle":"A"}},
    {"id":{"videoId":"fake1"},"snippet":{"title":"AI generated motorcycle stunt",
     "publishedAt":"2026-10-25T00:00:00Z","channelTitle":"B"}},
    {"id":{"videoId":"real2"},"snippet":{"title":"Unexpected football moment",
     "publishedAt":"2026-10-20T00:00:00Z","channelTitle":"C"}}
])]
details=[
    {"id":"real1","statistics":{"viewCount":"1200000"}},
    {"id":"fake1","statistics":{"viewCount":"9999999"}},
    {"id":"real2","statistics":{"viewCount":"300000"}},
]
items=rank_candidates(pages,details,now)
assert len(items)==2
assert items[0]["id"]=="real1"
assert all(x["reuse_rights"]=="not_granted" and x["download_url"] is None for x in items)
assert all(x["authenticity"]=="unverified" and x["approval"]=="research_only" for x in items)
assert synthetic("An AI-generated video") and not synthetic("Actual camera recording")
print("PASS: viral discovery, synthetic markers, ranking and rights gates")
