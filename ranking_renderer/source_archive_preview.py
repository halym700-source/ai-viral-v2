#!/usr/bin/env python3
"""Keyless Internet Archive Creative Commons footage preview.

This is a temporary camera-footage preview source, not a TikTok/Instagram/X
scraper or evidence of virality. Archive uploader license declarations and
camera authenticity are NOT independently verified. Preview only.
"""
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

BASE="https://archive.org"
HEADERS={"User-Agent":"ReshRanksPreview/1.0 (open-licensed research; contact via GitHub)"}
TOPICS=[
    ("RANKING WILDEST SKATEBOARD TRICKS","Ranking wildest skateboard tricks","skateboard"),
    ("RANKING BEST SURFING MOMENTS","Ranking best surfing moments","surfing"),
    ("RANKING CUTEST DOG MOMENTS","Ranking cutest dog moments","dogs"),
    ("RANKING CRAZIEST BASKETBALL MOVES","Ranking craziest basketball moves","basketball"),
    ("RANKING AMAZING BIKE TRICKS","Ranking amazing bike tricks","bmx"),
]
BAD=re.compile(r"\b(animation|animated|cartoon|gameplay|ai.generated|cgi|trailer|documentary|film festival|movie review)\b",re.I)
MAX_BYTES=105*1024*1024

def request_json(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=35) as res:return json.load(res)

def safe_license(url):
    url=str(url or "").replace("http://","https://").rstrip("/")
    # Commercial use permitted under CC BY / BY-SA / CC0; exclude NC and ND.
    return bool(re.fullmatch(
        r"https://creativecommons\.org/(?:licenses/(?:by|by-sa)/(?:2\.0|2\.5|3\.0|4\.0)|publicdomain/zero/1\.0)",url
    ))

def clean(v):
    if isinstance(v,list):v=" ".join(str(x) for x in v)
    return re.sub(r"\s+"," ",re.sub(r"<[^>]*>"," ",str(v or ""))).strip()

def search(topic,offset):
    term=topic.replace('"',"")
    q=f'mediatype:movies AND ({term}) AND (licenseurl:http*by* OR licenseurl:http*zero*)'
    params=[("q",q),("rows","60"),("page",str(1+offset%3)),("output","json"),
            ("sort[]","downloads desc"),("fl[]","identifier"),("fl[]","title"),
            ("fl[]","creator"),("fl[]","licenseurl")]
    url=BASE+"/advancedsearch.php?"+urllib.parse.urlencode(params)
    return request_json(url).get("response",{}).get("docs",[])

def select_video(identifier,creator,topic,licenseurl):
    data=request_json(BASE+"/metadata/"+urllib.parse.quote(identifier,safe=""))
    m=data.get("metadata") or {}
    lic=clean(m.get("licenseurl"))
    if not safe_license(lic) or lic.rstrip("/")!=licenseurl.rstrip("/"):return None
    title=clean(m.get("title"))
    author=clean(m.get("creator")) or creator
    if not author or not title or BAD.search(title+" "+clean(m.get("description"))[:250]):return None
    if topic.lower() not in (title+" "+clean(m.get("subject"))+" "+clean(m.get("description"))[:500]).lower():
        return None
    files=[]
    for f in data.get("files",[]):
        name=f.get("name","")
        if not name.lower().endswith(".mp4") or f.get("private")=="true":continue
        try:size=int(f.get("size") or 0);length=float(f.get("length") or 0)
        except (TypeError,ValueError):continue
        if not (300_000<size<MAX_BYTES and length>=5):continue
        files.append((0 if f.get("source")=="original" else 1,size,name))
    if not files:return None
    files.sort()
    name=files[0][2]
    url=BASE+"/download/"+urllib.parse.quote(identifier,safe="")+"/"+urllib.parse.quote(name,safe="")
    return {"url":url,"source":BASE+"/details/"+urllib.parse.quote(identifier,safe=""),
            "license":lic+"; creator credited by uploader: "+author,
            "creator":author,"title":title,"identifier":identifier}

def discover():
    index=os.getenv("RANK_TOPIC_INDEX","").strip()
    rotation=int(index) if index.isdigit() else dt.datetime.now(dt.timezone.utc).date().toordinal()
    for shift in range(len(TOPICS)):
        title,intro,topic=TOPICS[(rotation+shift)%len(TOPICS)]
        print("Searching",topic,flush=True)
        try:docs=search(topic,rotation)
        except Exception as exc:
            print("Archive search failed",str(exc),flush=True);continue
        selected=[];creators=set()
        for d in docs[:55]:
            identifier=d.get("identifier","")
            creator=clean(d.get("creator"))
            lic=clean(d.get("licenseurl"))
            if not identifier or not creator or not safe_license(lic):continue
            key=re.sub(r"\W+","",creator.casefold())
            if key in creators:continue
            try:clip=select_video(identifier,creator,topic,lic)
            except Exception as exc:
                print("Skipping unavailable item",identifier,str(exc)[:100],flush=True)
                continue
            if clip:
                creators.add(key);selected.append(clip)
                if len(selected)==5:break
        if len(selected)==5:
            return title,intro,selected
        print("Insufficient same-topic distinct creators",topic,len(selected),flush=True)
    raise RuntimeError("Archive returned fewer than five license-declared MP4 clips from different creators in one topic. No unrelated filler allowed.")

def main():
    title,intro,clips=discover()
    ranked=[{"rank":rank,"url":clip["url"],"start":0,
             "label":clip["title"][:42],"source":clip["source"],
             "license":clip["license"]} for rank,clip in zip(range(5,0,-1),clips)]
    manifest={"title":title,"intro":intro,"brand":"RESHRANKS","clip_seconds":4.8,"clips":ranked}
    out=Path("out");out.mkdir(exist_ok=True)
    (out/"ranking_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"topic":title,"clips":5,"creators":len({c["creator"] for c in clips}),
                      "source":"Internet Archive CC uploader metadata","preview_only":True,
                      "authenticity_verified":False,"permission_independently_verified":False}))
if __name__=="__main__":main()
