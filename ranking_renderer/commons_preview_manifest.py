#!/usr/bin/env python3
"""Build a preview manifest from Wikimedia Commons CC BY 4.0 skate videos.

Metadata-based research only; NOT a certification of footage authenticity,
rights ownership or suitability for publication. Preview mode only.
"""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

TITLES = [
    "File:Skateboarding at Mexico City - Flip - 010.webm",
    "File:Skateboarding at Mexico City - Flip - 040.webm",
    "File:Skateboarding at Mexico City - Flip - 060.webm",
    "File:Skateboarding at Mexico City - Flip - 070.webm",
    "File:Skateboarding at Mexico City - Flip - 080.webm",
    "File:Skateboarding at Mexico City - Flip - 090.webm",
    "File:Skateboarding at Mexico City - Flip - 120a.webm",
    "File:Skateboarding at Mexico City - Ollie - 030.webm",
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
    lic=meta.get("LicenseShortName",{}).get("value","")
    licurl=meta.get("LicenseUrl",{}).get("value","")
    if lic.strip()!="CC BY 4.0" or not licurl.startswith("https://creativecommons.org/licenses/by/4.0"):
        raise ValueError("Unexpected license for "+title+": "+lic)
    url=obj.get("url","")
    if not url.startswith("https://upload.wikimedia.org/") or obj.get("mime")!="video/webm":
        raise ValueError("Unexpected media source or type: "+title)
    pageurl=obj.get("descriptionurl") or "https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_"),safe=":/()")
    credit=re.sub("<[^>]+>"," ",meta.get("Attribution",{}).get("value","")).strip()
    return url,pageurl,lic,licurl,credit

def main():
    # Rotate source files per day; keep the list distinct within a single preview.
    offset=dt.datetime.now(dt.timezone.utc).date().toordinal()%len(TITLES)
    selection=[TITLES[(offset+i)%len(TITLES)] for i in range(5)]
    clips=[]
    for rank,title in zip(range(5,0,-1),selection):
        url,source,license_name,license_url,credit=metadata(title)
        clips.append({"rank":rank,"url":url,"start":0,
                      "label":("SKATE TRICK "+str(rank)),
                      "source":source,
                      "license":license_name+"; "+license_url+"; creator credit: "+credit})
    out=Path("out")
    out.mkdir(exist_ok=True)
    manifest={"title":"TOP 5 REAL SKATEBOARD TRICKS","intro":"Top five real skateboard tricks",
              "brand":"RESHRANKS","clip_seconds":4.8,"clips":clips}
    (out/"ranking_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"preview_sources":len(clips),"mode":"commons_cc_by_preview",
                      "camera_origin_verified":False,"reuse_rights_final_reviewed":False,
                      "upload_allowed":False}))
if __name__=="__main__":
    main()
