#!/usr/bin/env python3
"""Prepare a review queue for REAL viral footage without asserting reuse rights.

The research API returns popularity signals, NOT media files or permissions.
This module never downloads third-party footage or grants approval.
"""
import csv
import json
from pathlib import Path

COLUMNS = (
    "rank", "title", "channel", "views", "views_per_day", "video_url",
    "research_query", "authenticity_status", "reuse_rights_status",
    "rights_holder", "permission_evidence_url", "approved_mp4_url",
    "reviewer_notes",
)

def queue_rows(videos):
    result=[]
    for index, video in enumerate(videos,1):
        result.append({
            "rank":index,
            "title":video.get("title",""),
            "channel":video.get("channel",""),
            "views":video.get("views",0),
            "views_per_day":video.get("views_per_day",0),
            "video_url":video.get("url",""),
            "research_query":video.get("query",""),
            "authenticity_status":"NEEDS_MANUAL_VERIFICATION",
            "reuse_rights_status":"NOT_GRANTED",
            "rights_holder":"",
            "permission_evidence_url":"",
            "approved_mp4_url":"",
            "reviewer_notes":"",
        })
    return result

def write_queue(research_path,output_path):
    report=json.loads(Path(research_path).read_text(encoding="utf-8"))
    rows=queue_rows(report.get("videos",[]))
    path=Path(output_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)

if __name__=="__main__":
    count=write_queue("out/viral_research.json","out/rights_review_queue.csv")
    print(json.dumps({"candidates_to_review":count,
        "warning":"NO footage is licensed or approved by this queue; verify authenticity, ownership and reuse permission first."}))
