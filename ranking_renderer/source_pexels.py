#!/usr/bin/env python3
"""Choose five distinct licensed Pexels videos for an original ranking edit."""
import datetime as dt
import json
import os
import random
import urllib.parse
import urllib.request
from pathlib import Path

TOPICS = [
    ("TOP 5 EPIC MOTORCYCLE MOMENTS", "Top five epic motorcycle moments!", "motorcycle stunt"),
    ("TOP 5 AMAZING SKATEBOARD TRICKS", "Top five amazing skateboard tricks!", "skateboard tricks"),
    ("TOP 5 INCREDIBLE SURFING MOMENTS", "Top five incredible surfing moments!", "surfing waves"),
    ("TOP 5 WILD BMX TRICKS", "Top five wild BMX tricks!", "bmx tricks"),
    ("TOP 5 EXTREME SNOWBOARD MOMENTS", "Top five extreme snowboard moments!", "snowboard tricks"),
    ("TOP 5 BREATHTAKING PARKOUR MOVES", "Top five breathtaking parkour moves!", "parkour"),
]

def choose_files(videos, min_seconds=4.8):
    """Prefer vertical HD, five unique Pexels IDs and safe source metadata."""
    picks = []
    seen = set()
    for video in videos:
        video_id = video.get("id")
        if not video_id or video_id in seen or float(video.get("duration") or 0) < min_seconds:
            continue
        page = str(video.get("url") or "")
        if not page.startswith("https://www.pexels.com/"):
            continue
        files = [f for f in video.get("video_files", []) if
                 f.get("file_type") == "video/mp4" and
                 str(f.get("link") or "").startswith("https://") and
                 (f.get("height") or 0) > (f.get("width") or 0) and
                 (f.get("width") or 0) >= 540]
        if not files:
            continue
        files.sort(key=lambda f: (abs((f.get("width") or 720)-720), -(f.get("height") or 0)))
        picks.append({"rank": 5-len(picks), "url": files[0]["link"],
                      "start": 0, "label": "MOMENT "+str(5-len(picks)),
                      "source": page, "license": "Pexels License; verify music/audio separately"})
        seen.add(video_id)
        if len(picks) == 5:
            break
    if len(picks) != 5:
        raise ValueError("Fewer than five distinct vertical licensed clips available")
    return picks

def build_manifest(api_key, day, topic_index=None):
    if not api_key:
        raise ValueError("PEXELS_API_KEY is missing")
    if topic_index is None:
        topic_index = (day.toordinal() // 2) % len(TOPICS)
    title, intro, query = TOPICS[int(topic_index) % len(TOPICS)]
    params = urllib.parse.urlencode({"query":query, "per_page":80, "orientation":"portrait"})
    request = urllib.request.Request("https://api.pexels.com/videos/search?"+params,
                                     headers={"Authorization":api_key, "User-Agent":"RankingShorts/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        videos = json.load(response).get("videos", [])
    random.Random(day.isoformat()+query).shuffle(videos)
    return {"title":title, "intro":intro, "brand":"TOP FIVE",
            "clip_seconds":4.8, "clips":choose_files(videos)}

def main():
    day = dt.date.fromisoformat(os.getenv("RANK_DATE",dt.date.today().isoformat()))
    manifest = build_manifest(os.getenv("PEXELS_API_KEY",""),day,
                              os.getenv("RANK_TOPIC_INDEX") or None)
    output = Path("out/ranking_manifest.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"manifest":str(output),"title":manifest["title"],"clips":len(manifest["clips"])}))

if __name__ == "__main__":
    main()
