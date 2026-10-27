#!/usr/bin/env python3
"""Select five coherent, distinct-author, real-camera Pixabay clips for a preview.

Pixabay supplies MP4 download URLs directly. YouTube is still used only for
trend research, not downloading. The Pixabay key is read from a GitHub secret.
If five suitable videos cannot be found, fail rather than mix topics.
"""
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

KEY=os.getenv("PIXABAY_API_KEY","").strip()
OUT=Path("out")
TOPICS=[
    {"title":"RANKING WILDEST MOTORCYCLE MOMENTS","intro":"Ranking wildest motorcycle moments",
     "queries":["motorcycle stunt","motocross","motorcycle racing","dirt bike","motorcycle","motorbike"],
     "must":r"\b(motorcycle|motorbike|motorbikes|motorcycles|biker|bikers|motocross|dirt bike)\b",
     "reject":r"\b(animation|cgi|simulation|toy|game|bicycle|motorcycle helmet|motorcycle repair)\b",
     "label":"MOTORCYCLE MOMENT",
     "event":r"\b(stunt|jump|race|racing|motocross|offroad|off-road|wheelie|drift|trick|dirt bike|enduro|freestyle)\b"},
    {"title":"RANKING WILDEST SKATEBOARD TRICKS","intro":"Ranking wildest skateboard tricks",
     "queries":["skateboard","skateboarding","skate trick"],
     "must":r"\b(skateboard|skateboarding|skate|skater|skating)\b",
     "reject":r"\b(ice skate|roller skate|figure skating|skate shoes)\b","label":"SKATE TRICK"},
    {"title":"RANKING CRAZIEST BMX TRICKS","intro":"Ranking craziest BMX tricks",
     "queries":["bmx","bmx trick","bicycle stunt"],
     "must":r"\b(bmx|bicycle stunt|bike stunt|bike trick)\b",
     "reject":r"\b(motorcycle|motorbike|motorcross|motocross)\b","label":"BMX MOVE"},
    {"title":"RANKING BEST SURFING MOMENTS","intro":"Ranking best surfing moments",
     "queries":["surfing","surfer","surfboard"],
     "must":r"\b(surfing|surfer|surfboard|surf)\b",
     "reject":r"\b(windsurf|kitesurf|internet surfing)\b","label":"SURF MOMENT"},
    {"title":"RANKING AMAZING DOG MOMENTS","intro":"Ranking amazing dog moments",
     "queries":["dog playing","dogs","dog running"],
     "must":r"\b(dog|dogs|puppy|puppies|canine)\b",
     "reject":r"\b(hot dog|dog food|dog cartoon)\b","label":"DOG MOMENT"},
    {"title":"RANKING CRAZIEST PARKOUR MOVES","intro":"Ranking craziest parkour moves",
     "queries":["parkour","freerunning","backflip"],
     "must":r"\b(parkour|freerun|freerunning|backflip|frontflip)\b",
     "reject":r"\b(animation|game|cartoon|gymnastics competition)\b","label":"PARKOUR MOVE"},
]
FAKE=re.compile(r"\b(ai generated|ai-generated|cgi|3d animation|cartoon|animation|gameplay)\b",re.I)

def query(q,page):
    params=urllib.parse.urlencode({"key":KEY,"q":q,"video_type":"film",
        "per_page":100,"page":page,"safesearch":"true","order":"popular"})
    url="https://pixabay.com/api/videos/?"+params
    with urllib.request.urlopen(urllib.request.Request(url,headers={
        "User-Agent":"ReshRanksTopicPreview/1.0"}),timeout=45) as response:
        return json.load(response)

def valid(hit,topic):
    tags=str(hit.get("tags") or "")
    if not re.search(topic["must"],tags,re.I):return False
    if re.search(topic["reject"],tags,re.I) or FAKE.search(tags):return False
    if topic.get("event") and not re.search(topic["event"],tags,re.I):return False
    if hit.get("type") not in (None,"film"):return False
    if int(hit.get("duration") or 0)<5:return False
    user=hit.get("user_id") or hit.get("user")
    if not user:return False
    vids=hit.get("videos") or {}
    # Prefer a compact 720p file; original video is downloaded only once.
    for quality in ("medium","large","small"):
        media=vids.get(quality) or {}
        src=media.get("url","")
        size=int(media.get("size") or 0)
        if src.startswith("https://") and 100_000<size<90_000_000:
            return {"url":src,"user":str(user),"tags":tags,"id":hit["id"],
                    "page":hit.get("pageURL") or f"https://pixabay.com/videos/id-{hit['id']}/",
                    "size":size}
    return False

def main():
    if not KEY:
        raise ValueError("PIXABAY_API_KEY is missing. Add your existing Pixabay API key as a GitHub Actions repository secret.")
    idx=os.getenv("RANK_TOPIC_INDEX","").strip()
    rotation=int(idx) if idx.isdigit() else dt.datetime.now(dt.timezone.utc).date().toordinal()
    OUT.mkdir(exist_ok=True)
    indices=[rotation%len(TOPICS)] if idx.isdigit() else [(rotation+o)%len(TOPICS) for o in range(len(TOPICS))]
    for topic_index in indices:
        topic=TOPICS[topic_index]
        chosen=[];authors=set();seen=set();extra=[]
        for term in topic["queries"]:
            for page in (1,2):
                try:
                    data=query(term,page)
                except Exception as exc:
                    print("Pixabay query failed",term,type(exc).__name__,str(exc)[:160],flush=True)
                    continue
                for hit in data.get("hits",[]):
                    v=valid(hit,topic)
                    if not v or v["id"] in seen:continue
                    seen.add(v["id"])
                    if v["user"] in authors:
                        extra.append(v)
                        continue
                    authors.add(v["user"]);chosen.append(v)
                    if len(chosen)==5:break
                if len(chosen)==5:break
            if len(chosen)==5:break
        if len(chosen)<5:
            for v in extra:
                if len(chosen)==5:break
                if sum(x["user"]==v["user"] for x in chosen)>=2:continue
                chosen.append(v)
        print(json.dumps({"topic":topic["title"],"qualified_clips":len(chosen),"unique_creators":len({v["user"] for v in chosen}),"chosen_tags":[v["tags"] for v in chosen]}),flush=True)
        if len(chosen)<5:continue
        clips=[{"rank":rank,"url":v["url"],"start":0,"label":topic["label"],
                "source":v["page"],"license":"Pixabay Content License; confirm source details",
                "creator":v["user"],"tags":v["tags"]} for rank,v in zip(range(5,0,-1),chosen)]
        manifest={"title":topic["title"],"intro":topic["intro"],"brand":"RESHRANKS",
                  "clip_seconds":4.8,"clips":clips}
        (OUT/"ranking_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps({"topic":topic["title"],"clips":5,"creators":len({v["user"] for v in chosen}),
                          "source":"Pixabay video API","preview_only":True}),flush=True)
        return
    raise RuntimeError("Could not find five distinct real-camera action videos on one topic. Unrelated filler is forbidden.")

if __name__=="__main__":main()
