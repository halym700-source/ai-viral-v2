#!/usr/bin/env python3
"""Safe every-other-day release guard for the independent Ranking Shorts channel.

Prints JSON with publish_due, with a reason if blocked. Does not publish.
Only set publication_time_local after verifying Polar Ranks' exact publishedAt
using public YouTube Data API or a reliable timestamp source.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo


def eligible(now: dt.datetime, config: dict) -> tuple[bool, str]:
    tz = ZoneInfo(config["timezone"])
    local = now.astimezone(tz)
    if config.get("auto_publish_enabled") is not True:
        return False, "auto_publish_disabled"
    first = config.get("first_publication_date")
    clock = config.get("publication_time_local")
    if not first or not clock:
        return False, "reference_time_or_first_date_unverified"
    try:
        anchor = dt.date.fromisoformat(first)
        scheduled_time = dt.time.fromisoformat(clock)
    except (ValueError, TypeError):
        return False, "invalid_schedule"
    if local.date() < anchor:
        return False, "before_first_publication"
    if (local.date() - anchor).days % int(config.get("every_n_days", 2)):
        return False, "rest_day"
    if (local.hour, local.minute) != (scheduled_time.hour, scheduled_time.minute):
        return False, "not_publication_minute"
    return True, "due_for_manual_approved_publish"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="ranking_renderer/schedule_config.json")
    ap.add_argument("--at", default=None, help="ISO 8601 aware timestamp for testing")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    now = dt.datetime.fromisoformat(a.at) if a.at else dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        ap.error("--at requires a timezone offset")
    due, reason = eligible(now, cfg)
    print(json.dumps({"publish_due":due, "reason":reason,
        "local_time":now.astimezone(ZoneInfo(cfg["timezone"])).isoformat(),
        "video_target_seconds":cfg.get("duration_seconds",24)}))


if __name__ == "__main__":
    main()
