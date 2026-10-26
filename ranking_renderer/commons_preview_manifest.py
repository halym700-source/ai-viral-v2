#!/usr/bin/env python3
"""Five independently sourced real-camera footage candidates for PREVIEW ONLY.

Source descriptions, licenses and authors are checked against Wikimedia metadata.
Different file/creator/location helps avoid the same-camera montage; actual camera
identity and reuse rights still require review before publication.
"""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

# Five different filming subjects, places and credited creators, not a sequence
# of frames from one recording or several files from one filming session.
SOURCES = [
    {"title":"File:Sumatran Tiger playing with a ball at Los Angeles Zoo.webm",
     "creator":"LA Zoo","label":"TIGER PLAYS BALL"},
    {"title":"File:Table Cloth Trick - SloMo, Real Plates.webm",
     "creator":"Dan Spencer","label":"TABLECLOTH TRICK"},
    {"title":"File:Freeride Skateboarding & Downhill Slides.webm",
     "creator":"GravitySkateboards","label":"DOWNHILL RIDE"},
    {"title":"File:Skateboarding at Mexico City - Flip - 010.webm",
     "creator":"Jarek Tuszyński","label":"SKATEBOARD FLIP"},
    {"title":"File:People playing at the beach.webm",
     "creator":"Eyongblaise","label":"BEACH MOMENT"},
]
API = "https://commons.wikimedia.org/w/api.php"

def metadata(title):
    args = urllib.parse.urlencode({
        "action":"query", "format":"json", "titles":title,
        "prop":"imageinfo", "iiprop":"url|mime|extmetadata",
        "iiextmetadatafilter":"LicenseShortName|LicenseUrl|Artist|Attribution",
    })
    request = urllib.request.Request(API+"?"+args, headers={
        "User-Agent":"ReshRanksPreview/1.0 (https://github.com/halym700-source/ai-viral-v2)",
        "Accept":"application/json",
    })
    with urllib.request.urlopen(request, timeout=35) as response:
        data=json.load(response)
    page=next(iter(data["query"]["pages"].values()))
    info=page.get("imageinfo",[])
    if not info:
        raise ValueError("Missing Commons file: "+title)
    obj=info[0]
    meta=obj.get("extmetadata",{})
    lic=meta.get("LicenseShortName",{}).get("value","").strip()
    licurl=meta.get("LicenseUrl",{}).get("value","")
    if lic not in ("CC BY 3.0","CC BY 4.0","CC BY-SA 4.0"):
        raise ValueError("Unexpected license for "+title+": "+lic)
    expected="https://creativecommons.org/licenses/"+("by-sa" if "BY-SA" in lic else "by")+"/"+lic.rsplit(" ",1)[1]
    if not licurl.startswith(expected):
        raise ValueError("License URL does not match "+title)
    url=obj.get("url","")
    if not url.startswith("https://upload.wikimedia.org/") or obj.get("mime")!="video/webm":
        raise ValueError("Unexpected media source or type: "+title)
    pageurl=obj.get("descriptionurl") or "https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_"),safe=":/()")
    raw=meta.get("Attribution",{}).get("value","") or meta.get("Artist",{}).get("value","")
    credit=re.sub(r"<[^>]+>"," ",raw).strip()
    return url,pageurl,lic,licurl,credit

def main():
    # Rotate the ranking order without reusing a filming series in one video.
    offset=dt.datetime.now(dt.timezone.utc).date().toordinal()%len(SOURCES)
    selected=SOURCES[offset:]+SOURCES[:offset]
    if len({s["title"] for s in selected})!=5 or len({s["creator"] for s in selected})!=5:
        raise ValueError("Five distinct files and filming creators are required")
    clips=[]
    for rank,entry in zip(range(5,0,-1),selected):
        url,source,license_name,license_url,credit=metadata(entry["title"])
        clips.append({"rank":rank,"url":url,"start":0,
                      "label":entry["label"],"source":source,
                      "creator":entry["creator"],
                      "license":license_name+"; "+license_url+"; creator credit: "+(credit or entry["creator"])})
    out=Path("out")
    out.mkdir(exist_ok=True)
    manifest={"title":"TOP 5 REAL LIFE MOMENTS","intro":"Top five real life moments",
              "brand":"RESHRANKS","clip_seconds":4.8,"clips":clips}
    (out/"ranking_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"preview_sources":len(clips),"different_source_creators":5,
                      "mode":"commons_cc_preview","camera_origin_verified":False,
                      "reuse_rights_final_reviewed":False,"upload_allowed":False}))
if __name__=="__main__":
    main()
