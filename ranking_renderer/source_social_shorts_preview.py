#!/usr/bin/env python3
"""Research five SAME-TOPIC, DIFFERENT-CHANNEL short clips and render a preview.

YouTube's official Data API is used for discovery; yt-dlp attempts to retrieve
publicly accessible source media. A search hit does not prove camera
authenticity, original ownership, or permission to republish. Preview only.
Fail closed rather than inserting unrelated footage.
"""
import datetime as dt
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

TOPICS=[
    {"title":"RANKING WILDEST SKATEBOARD TRICKS",
     "intro":"Ranking wildest skateboard tricks",
     "query":"skateboard trick shorts",
     "pattern":r"\b(skateboard(?:ing|er)?|skater|kickflip|heelflip|ollie|tre flip)\b",
     "label":"SKATE TRICK"},
    {"title":"RANKING CRAZIEST BMX TRICKS",
     "intro":"Ranking craziest BMX tricks",
     "query":"bmx stunt shorts",
     "pattern":r"\b(bmx|bike stunt|bicycle trick|bike trick)\b",
     "label":"BMX TRICK"},
    {"title":"RANKING BEST SURFING MOMENTS",
     "intro":"Ranking best surfing moments",
     "query":"surfing waves shorts",
     "pattern":r"\b(surfing|surfer|surfboard|surf)\b",
     "label":"SURF MOMENT"},
    {"title":"RANKING WILDEST BASKETBALL SHOTS",
     "intro":"Ranking wildest basketball shots",
     "query":"basketball trick shot shorts",
     "pattern":r"\b(basketball|dunk|hoop|three.pointer|trick shot)\b",
     "label":"BASKETBALL SHOT"},
    {"title":"RANKING CRAZIEST PARKOUR MOVES",
     "intro":"Ranking craziest parkour moves",
     "query":"parkour flip shorts",
     "pattern":r"\b(parkour|freerun(?:ning)?|backflip|frontflip)\b",
     "label":"PARKOUR MOVE"},
]
EXCLUDE=re.compile(
    r"\b(ai.generated|ai generated|sora|veo 3|cgi|animation|cartoon|"
    r"compilation|reaction|ranking|top (?:5|10|five|ten)|"
    r"highlights|tutorial|how to|gameplay|roblox|minecraft|"
    r"edit(?:s|ed|ing)?|montage|best of|movie|trailer)\b",re.I)
KEY=os.getenv("YOUTUBE_RESEARCH_API_KEY","")
UA={"User-Agent":"ReshRanksResearch/1.0"}
OUT=Path("out")

def api(endpoint,params):
    if not KEY:raise ValueError("YOUTUBE_RESEARCH_API_KEY missing")
    url="https://www.googleapis.com/youtube/v3/"+endpoint+"?"+urllib.parse.urlencode({**params,"key":KEY})
    with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=45) as response:
        return json.load(response)

def seconds(iso):
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",iso or "")
    if not m:return 0
    h,minute,sec=(int(x or 0) for x in m.groups())
    return 3600*h+60*minute+sec

def find_candidates(topic):
    since=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result=api("search",{"part":"snippet","q":topic["query"],"type":"video",
                         "videoDuration":"short","order":"viewCount",
                         "publishedAfter":since,"maxResults":50,"safeSearch":"moderate"})
    ids=[x.get("id",{}).get("videoId") for x in result.get("items",[])]
    ids=[x for x in ids if x]
    if not ids:return []
    details=api("videos",{"part":"snippet,statistics,contentDetails","id":",".join(ids)})
    found=[]
    for item in details.get("items",[]):
        snippet=item.get("snippet") or {}
        title=snippet.get("title","")
        description=snippet.get("description","")
        # Strong topical match in the *title*, not just a generic description.
        if not re.search(topic["pattern"],title,re.I):continue
        if EXCLUDE.search(title+" "+description[:250]):continue
        dur=seconds((item.get("contentDetails") or {}).get("duration",""))
        if dur<6 or dur>90:continue
        stats=item.get("statistics") or {}
        views=int(stats.get("viewCount") or 0)
        if views<1000:continue
        channel=snippet.get("channelId","")
        if not channel:continue
        published=snippet.get("publishedAt","")
        try:age=max(1,(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(
            published.replace("Z","+00:00"))).total_seconds()/86400)
        except ValueError:age=120
        found.append({"id":item["id"],"title":title,"channel":channel,
                      "views":views,"views_per_day":round(views/age),
                      "duration":dur,"source":"https://www.youtube.com/watch?v="+item["id"]})
    found.sort(key=lambda x:(x["views_per_day"],x["views"]),reverse=True)
    return found

def download(candidate,rank):
    dest=OUT/f"source_rank_{rank}.mp4"
    dest.unlink(missing_ok=True)
    # Only public videos are attempted; no cookies, login, or DRM bypass.
    command=["yt-dlp","--no-playlist","--no-progress","--no-warnings",
             "--socket-timeout","18","--retries","2","--fragment-retries","2",
             "--max-filesize","100M","--download-sections","*0-00:15",
             "-f","bv*[height<=1080]+ba/b[height<=1080]/best",
             "--merge-output-format","mp4","--recode-video","mp4",
             "-o",str(dest),candidate["source"]]
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=110)
    except subprocess.TimeoutExpired:
        return None
    if result.returncode!=0 or not dest.exists() or dest.stat().st_size<10000:
        print("Source not downloadable",candidate["id"],result.stderr[-250:],flush=True)
        dest.unlink(missing_ok=True)
        return None
    return dest

def main():
    OUT.mkdir(exist_ok=True)
    idx=os.getenv("RANK_TOPIC_INDEX","").strip()
    index=int(idx)%len(TOPICS) if idx.isdigit() else dt.datetime.now(dt.timezone.utc).date().toordinal()%len(TOPICS)
    topic=TOPICS[index]
    candidates=find_candidates(topic)
    print(json.dumps({"topic":topic["title"],"topically_matched_candidates":len(candidates)}),flush=True)
    chosen=[];seen_channels=set()
    for c in candidates:
        if c["channel"] in seen_channels:continue
        rank=5-len(chosen)
        path=download(c,rank)
        if path is None:continue
        chosen.append((c,path))
        seen_channels.add(c["channel"])
        if len(chosen)==5:break
    if len(chosen)!=5:
        for _,path in chosen:path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Only {len(chosen)} of 5 distinct-channel {topic['title']} videos downloaded. "
            "Refusing to mix in unrelated videos."
        )
    clips=[]
    for rank,(c,path) in zip(range(5,0,-1),chosen):
        clips.append({"rank":rank,"file":str(path),"start":0,
                      "label":topic["label"],"source":c["source"],
                      "license":"Research preview; reuse rights unverified",
                      "channel":c["channel"],"original_title":c["title"]})
    manifest={"title":topic["title"],"intro":topic["intro"],"brand":"RESHRANKS",
              "clip_seconds":4.8,"clips":clips}
    (OUT/"ranking_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"title":topic["title"],"clips":5,"distinct_channels":5,
                      "source":"YouTube Shorts","preview_only":True,
                      "reuse_rights":"unverified"}))
if __name__=="__main__":main()
