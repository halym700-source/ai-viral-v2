#!/usr/bin/env python3
"""Two-day cadence, delayed scheduling, and default disabled behavior."""
import datetime as dt
import json
from pathlib import Path
from schedule_guard import eligible
base=json.loads(Path("ranking_renderer/schedule_config.json").read_text())
assert eligible(dt.datetime.now(dt.timezone.utc),base)==(False,"auto_publish_disabled")
base.update({"auto_publish_enabled":True,
    "first_publication_date":"2026-10-28","publication_time_local":"20:20",
    "late_window_minutes":70})
assert eligible(dt.datetime.fromisoformat("2026-10-28T20:20:00+03:00"),base)[0]
assert eligible(dt.datetime.fromisoformat("2026-10-28T21:05:00+03:00"),base)[0]
assert not eligible(dt.datetime.fromisoformat("2026-10-28T20:19:00+03:00"),base)[0]
assert not eligible(dt.datetime.fromisoformat("2026-10-28T21:30:00+03:00"),base)[0]
assert not eligible(dt.datetime.fromisoformat("2026-10-29T20:20:00+03:00"),base)[0]
assert eligible(dt.datetime.fromisoformat("2026-10-30T20:20:00+03:00"),base)[0]
base["publication_time_local"]=None
assert not eligible(dt.datetime.fromisoformat("2026-10-30T20:20:00+03:00"),base)[0]
print("PASS: cadence, late-window, blocked defaults")
