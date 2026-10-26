#!/usr/bin/env python3
"""Topic-coherent five-camera ranking PREVIEWS using Commons metadata.

This is a footage discovery preview, not proof of virality, real-camera
provenance or a final reuse-rights clearance. No automated publication.
"""
import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

API="https://commons.wikimedia.org/w/api.php"
HEADERS={"User-Agent":"ReshRanksPreview/1.0 (https://github.com/halym700-source/ai-viral-v2)","Accept":"application/json"}
ALLOWED={"CC BY 3.0","CC BY 4.0","CC BY-SA 4.0","CC BY-SA 3.0","CC0"}
# Entire video is about one subject. Across episodes, subjects rotate.
TOPICS=[
    {"title":"RANKING CRAZIEST SKATEBOARD MOMENTS",
     "intro":"Ranking craziest skateboard moments",
     "search":["skateboarding filetype:video","skateboard trick filetype:video"],
     "match":r"skateboard|skating|skater|longboard|downhill slides",
     "label":"SKATE MOMENT"},
    {"title":"RANKING CUTEST ANIMALS PLAYING",
     "intro":"Ranking cutest animals playing",
     "search":["animals playing filetype:video","tiger playing filetype:video","cats playing filetype:video"],
     "match":r"animal|tiger|cat|dog|fossa|playing|playful|puppy|kitten",
     "label":"PLAY MOMENT"},
    {"title":"RANKING CRAZIEST SURFING MOMENTS",
     "intro":"Ranking craziest surfing moments",
     "search":["surfing filetype:video","surfboard waves filetype:video"],
     "match":r"surf|wave|surfboard",
     "label":"SURF MOMENT"},
    {"title":"RANKING BEST BASKETBALL MOMENTS",
     "intro":"Ranking best basketball moments",
     "search":["basketball filetype:video","basketball dunk filetype:video"],
     "match":r"basketball|dunk|basket ball",
     "label":"BASKETBALL MOMENT"},
]
# Backup set: five different credited sources, all about animals playing.
# This ensures a coherent preview when Commons search returns too few clips.
ANIMAL_BACKUP=[
    "File:Finchen+Lotti playing 02 (1) ies.webm",
    "File:Sumatran Tiger playing with a ball at Los Angeles Zoo.webm",
    "File:Tiger playing with a piece of wood in a pool.webm",
    "File:Playing fossas.webm",
    "File:Adorable Animals Enjoying A Belly Rub Compilation 2014 NEW.webm",
]

def api(params):
    query=urllib.parse.urlencode({"action":"query","format":"json",**params})
    req=urllib.request.Request(API+"?"+query,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=40) as response:
        return json.load(response)

def clean(value):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",value or ""))).strip()

def parse(page):
    if page.get("ns")!=6 or not page.get("imageinfo"): return None
    info=page["imageinfo"][0]
    meta=info.get("extmetadata",{})
    license_name=clean(meta.get("LicenseShortName",{}).get("value",""))
    license_url=meta.get("LicenseUrl",{}).get("value","")
    if license_name not in ALLOWED:return None
    if license_name!="CC0":
        slug=("by-sa" if "BY-SA" in license_name else "by")
        if not license_url.startswith("https://creativecommons.org/licenses/"+slug+"/"):return None
    url=info.get("url","")
    if not url.startswith("https://upload.wikimedia.org/") or info.get("mime")!="video/webm":return None
    if info.get("size",0)>120*1024*1024:return None
    credit=clean(meta.get("Artist",{}).get("value","")) or clean(meta.get("Attribution",{}).get("value",""))
    # A missing creator cannot establish a different camera origin.
    if not credit or len(credit)>180:return None
    title=page["title"]
    pageurl=info.get("descriptionurl") or "https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_"),safe=":/()")
    return {"title":title,"url":url,"source":pageurl,"license":license_name+"; "+license_url+"; creator credit: "+credit,
            "creator":credit,"size":info.get("size",0)}

def query_pages(params):
    params={**params,"prop":"imageinfo","iiprop":"url|mime|size|extmetadata",
            "iiextmetadatafilter":"LicenseShortName|LicenseUrl|Artist|Attribution"}
    data=api(params)
    return [parse(p) for p in data.get("query",{}).get("pages",{}).values()]

def candidates(topic):
    found={}
    for search in topic["search"]:
        try:
            pages=query_pages({"generator":"search","gsrsearch":search,"gsrnamespace":"6","gsrlimit":"50"})
            for c in pages:
                if c and re.search(topic["match"],c["title"],re.I):
                    found[c["title"]]=c
        except Exception as exc:
            print("Commons search unavailable:",str(exc),flush=True)
    return list(found.values())

def backup_animals():
    try:
        pages=query_pages({"titles":"|".join(ANIMAL_BACKUP)})
        found={p["title"]:p for p in pages if p}
        return [found[x] for x in ANIMAL_BACKUP if x in found]
    except Exception as exc:
        print("Commons backup lookup failed:",str(exc),flush=True)
        return []

def pick_distinct(pool,topic):
    # Prevent multiple videos from a single camera series or credited creator.
    seen_creators=set();seen_series=set();chosen=[]
    for c in pool:
        creator=re.sub(r"\W+","",c["creator"].lower())
        series=re.sub(r"\b\d+[a-z]?\b","",c["title"].lower())
        series=re.sub(r"[^a-z]+","",series)[:38]
        if not creator or creator in seen_creators or series in seen_series:continue
        seen_creators.add(creator);seen_series.add(series);chosen.append(c)
        if len(chosen)==5:break
    return chosen

def main():
    index=os.getenv("RANK_TOPIC_INDEX","").strip()
    start=int(index)%len(TOPICS) if index.isdigit() else dt.datetime.now(dt.timezone.utc).date().toordinal()%len(TOPICS)
    selected=None
    for step in range(len(TOPICS)):
        topic=TOPICS[(start+step)%len(TOPICS)]
        pool=candidates(topic)
        if topic is TOPICS[1]:
            pool+=backup_animals()
        clips=pick_distinct(pool,topic)
        if len(clips)==5:
            selected=(topic,clips)
            break
        print("Insufficient distinct creator footage for",topic["title"],len(clips),flush=True)
    if not selected:
        # The backup topic is coherent; never fill a rank with unrelated footage.
        topic=TOPICS[1];clips=pick_distinct(backup_animals(),topic)
        if len(clips)!=5:raise ValueError("Not enough distinct same-topic real footage. Refusing unrelated filler.")
    else:topic,clips=selected
    offset=dt.datetime.now(dt.timezone.utc).date().toordinal()%5
    clips=clips[offset:]+clips[:offset]
    ranked=[]
    for rank,c in zip(range(5,0,-1),clips):
        ranked.append({"rank":rank,"url":c["url"],"start":0,
                       "label":topic["label"],"source":c["source"],
                       "creator":c["creator"],"license":c["license"]})
    out=Path("out");out.mkdir(exist_ok=True)
    manifest={"title":topic["title"],"intro":topic["intro"],
              "brand":"RESHRANKS","clip_seconds":4.8,"clips":ranked}
    (out/"ranking_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"topic":topic["title"],"distinct_creators":len({c["creator"] for c in clips}),
                      "preview_only":True,"camera_identity_verified":False,"viral_status_verified":False}))
if __name__=="__main__":main()
