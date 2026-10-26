#!/usr/bin/env python3
"""Fail-closed conversion of owner-reviewed real footage into renderer manifest.

Only sources with documented ownership/permission and verified camera origin
are eligible. The code checks required attestations, not the truth of evidence.
"""
import json
import os
import urllib.parse
from pathlib import Path

ALLOWED_RIGHTS={"original_owner","creator_permission","commercial_license","pexels_license"}
AI_MARKERS=("ai-generated","ai generated","synthetic footage","text-to-video","image-to-video","generative ai")

def valid_https_url(value):
    if not isinstance(value,str):
        return False
    p=urllib.parse.urlsplit(value)
    return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password

def build_manifest(inventory):
    if not isinstance(inventory,dict):
        raise ValueError("Approved inventory must be a JSON object")
    clips=inventory.get("clips",[])
    if len(clips)!=5 or sorted(c.get("rank") for c in clips)!=[1,2,3,4,5]:
        raise ValueError("Exactly five ranked and approved real clips are required")
    seen=set()
    approved=[]
    for c in clips:
        rank=c["rank"]
        source=c.get("source_page")
        video=c.get("approved_mp4_url")
        evidence=c.get("permission_evidence_url")
        rights=c.get("rights_basis")
        if c.get("authenticity_reviewed") is not True or c.get("rights_reviewed") is not True:
            raise ValueError(f"Rank {rank}: real-camera origin and rights must both be manually reviewed")
        if rights not in ALLOWED_RIGHTS:
            raise ValueError(f"Rank {rank}: invalid rights basis")
        if not all(valid_https_url(v) for v in (source,video,evidence)):
            raise ValueError(f"Rank {rank}: source, approved MP4 and rights evidence must be HTTPS URLs")
        if urllib.parse.urlsplit(video).path.lower().endswith(".mp4") is False:
            raise ValueError(f"Rank {rank}: approved clip must be a direct MP4 URL, not a social media watch page")
        if not c.get("rights_holder") or not c.get("reviewer") or not c.get("reviewed_at"):
            raise ValueError(f"Rank {rank}: missing rights holder or reviewer audit metadata")
        if not c.get("label") or not isinstance(c["label"],str):
            raise ValueError(f"Rank {rank}: clip label is required")
        if any(marker in " ".join(str(c.get(k,"")) for k in
            ("label","source_page","rights_holder","notes")).lower() for marker in AI_MARKERS):
            raise ValueError(f"Rank {rank}: AI-generated footage is forbidden")
        if source in seen or video in seen:
            raise ValueError(f"Rank {rank}: duplicate footage source")
        seen.update((source,video))
        approved.append({"rank":rank,"url":video,"start":max(0,float(c.get("start",0))),
            "label":c["label"],"source":source,
            "license":f"{rights}; rights holder: {c['rights_holder']}; evidence: {evidence}"})
    title=inventory.get("title")
    if not isinstance(title,str) or not title.strip():
        raise ValueError("An editorial ranking title is required")
    return {"title":title,"intro":inventory.get("intro",title),
            "brand":"RESHRANKS","clip_seconds":4.8,"clips":approved}

def main():
    path=Path(os.getenv("RANK_APPROVED_INVENTORY","ranking_renderer/approved_sources.json"))
    inventory=json.loads(path.read_text(encoding="utf-8"))
    manifest=build_manifest(inventory)
    output=Path("out/ranking_manifest.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"approved_real_clips":len(manifest["clips"]),"manifest":str(output)}))

if __name__=="__main__":
    main()
