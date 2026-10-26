#!/usr/bin/env python3
"""Fetch five distinct openly licensed video clips for a style-only demo.

Unlike production Pexels videos, Commons videos may need credit. This demo
uses them solely to illustrate the ranking editor and records source/license.
"""
import json
import os
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path

API="https://commons.wikimedia.org/w/api.php"
QUERIES=["skateboard", "surfing", "bicycle", "skiing", "snowboarding"]
LABELS=["SKATEBOARD", "SURFING", "BICYCLE", "SKIING", "SNOWBOARD"]
def request(params):
    url=API+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"RankingDemo/1.0 (noncommercial testing; contact: github.com/halym700-source/ai-viral-v2)",
                                             "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)

def pick(query,used):
    data=request({"action":"query","generator":"search","gsrsearch":"filetype:video "+query,
                  "gsrnamespace":"6","gsrlimit":"40","prop":"imageinfo",
                  "iiprop":"url|size|mime|extmetadata","format":"json","formatversion":"2"})
    pages=data.get("query",{}).get("pages",[])
    candidates=[]
    for page in pages:
        info=(page.get("imageinfo") or [{}])[0]
        url=info.get("url","")
        size=info.get("size",0)
        title=page.get("title","")
        if title in used or not url.startswith("https://") or not 50000<size<25000000:
            continue
        if not url.lower().split("?")[0].endswith((".webm",".ogv",".ogg",".mp4")):
            continue
        meta=info.get("extmetadata",{})
        lic=meta.get("LicenseShortName",{}).get("value","")
        if not any(word in lic.lower() for word in ("cc","public domain","pd","copyrighted free use")):
            continue
        candidates.append((title,url,lic,info.get("descriptionurl","")))
    if not candidates:
        raise RuntimeError("No reusable Commons video for "+query)
    candidates.sort(key=lambda c: (not c[1].endswith(".webm"),len(c[0])))
    return candidates[0]

def main():
    used=set()
    clips=[]
    for idx,(query,label) in enumerate(zip(QUERIES,LABELS)):
        title,url,lic,page=pick(query,used)
        used.add(title)
        print("CLIP",idx+1,title,url[:120],lic,flush=True)
        clips.append({"rank":5-idx,"url":url,"start":0,"label":label,
                      "source":page or "https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_")),
                      "license":lic})
    manifest={"title":"RANKING BEST EXTREME SPORTS MOMENTS","intro":"Ranking the best extreme sports moments!",
              "brand":"RANKING","clip_seconds":4.8,"clips":clips}
    out=Path("out/ranking_manifest.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(manifest,indent=2))
    print("READY",len(clips),flush=True)
if __name__=="__main__":
    main()
