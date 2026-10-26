#!/usr/bin/env python3
"""Fail-closed two-day release guard; allows delayed GitHub scheduled runs."""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

def eligible(now: dt.datetime, config: dict) -> tuple[bool,str]:
    if config.get("auto_publish_enabled") is not True:
        return False,"auto_publish_disabled"
    first=config.get("first_publication_date")
    clock=config.get("publication_time_local")
    if not first or not clock:
        return False,"reference_time_or_first_date_unverified"
    try:
        tz=ZoneInfo(config["timezone"])
        local=now.astimezone(tz)
        anchor=dt.date.fromisoformat(first)
        scheduled_time=dt.time.fromisoformat(clock)
        cadence=int(config.get("every_n_days",2))
        if cadence < 1:
            raise ValueError("cadence")
        window=int(config.get("late_window_minutes",70))
        if not 0 < window <= 90:
            raise ValueError("window")
    except (ValueError,TypeError,KeyError):
        return False,"invalid_schedule"
    if local.date() < anchor:
        return False,"before_first_publication"
    if (local.date()-anchor).days % cadence:
        return False,"rest_day"
    target=dt.datetime.combine(local.date(),scheduled_time,tzinfo=tz)
    lag=(local-target).total_seconds()/60
    if not 0 <= lag < window:
        return False,"outside_publication_window"
    return True,"due_for_approved_publish"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default="ranking_renderer/schedule_config.json")
    ap.add_argument("--at",default=None)
    args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text(encoding="utf-8"))
    now=dt.datetime.fromisoformat(args.at) if args.at else dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        ap.error("--at requires an offset")
    due,reason=eligible(now,cfg)
    print(json.dumps({"publish_due":due,"reason":reason,
                      "local_time":now.astimezone(ZoneInfo(cfg["timezone"])).isoformat(),
                      "video_target_seconds":cfg.get("duration_seconds",24)}))
if __name__=="__main__":
    main()
