#!/usr/bin/env python3
"""ReshRanks social-platform research queue; NEVER downloads or republishes posts.

YouTube discovery is handled by viral_discovery.py. Optional official Instagram
and X APIs enrich this queue only when the user provides valid credentials.
TikTok public video research is restricted to eligible approved researchers and
not appropriate for this commercial Shorts workflow. Provide TikTok search links
for creator outreach and authorized submission instead.
"""
import csv
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOPICS=[
    ("skateboarding","skateboardtricks","skateboard tricks"),
    ("funny animals","funnyanimals","funny animals"),
    ("surfing","surfing","surfing"),
    ("basketball","basketball","basketball highlights"),
    ("motorcycle moments","motorcycle","motorcycle moments"),
    ("real life surprises","unexpected","unexpected moments"),
]
HEADERS={"User-Agent":"ReshRanksResearch/1.0"}
MAX_PER_PLATFORM=60

def get_json(url, headers=None):
    request=urllib.request.Request(url,headers={**HEADERS,**(headers or {})})
    with urllib.request.urlopen(request,timeout=35) as res:
        return json.load(res)

def candidate(platform, url, title="", author="", published_at="", views=None, likes=None, topic=""):
    return {"platform":platform,"url":url,"title":title,"author":author,
            "published_at":published_at,"views":views,"likes":likes,"topic":topic,
            "camera_authenticity":"unverified","reuse_permission":"not_granted",
            "download_url":None,"status":"research_only"}

def x_recent(token):
    if not token:return [],"missing X_BEARER_TOKEN"
    items=[]
    try:
        for topic,_,q in TOPICS[:4]:
            params=urllib.parse.urlencode({
                "query":f"({q}) has:videos -is:retweet lang:en",
                "max_results":"20",
                "tweet.fields":"created_at,public_metrics,author_id",
                "expansions":"author_id",
                "user.fields":"username",
            })
            data=get_json("https://api.x.com/2/tweets/search/recent?"+params,
                          {"Authorization":"Bearer "+token})
            users={u["id"]:u.get("username","") for u in data.get("includes",{}).get("users",[])}
            for post in data.get("data",[]):
                author=users.get(post.get("author_id"),"")
                metrics=post.get("public_metrics",{})
                link="https://x.com/"+author+"/status/"+post["id"] if author else "https://x.com/i/status/"+post["id"]
                items.append(candidate("X",link,post.get("text","")[:200],author,
                                       post.get("created_at",""),metrics.get("impression_count"),
                                       metrics.get("like_count"),topic))
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as exc:
        return items,"X API error: "+str(exc)
    return items[:MAX_PER_PLATFORM],"connected"

def instagram_hashtags(token,user_id):
    if not token or not user_id:return [],"missing INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_USER_ID"
    items=[]
    try:
        # Hashtag Search requires Instagram Professional account, appropriate
        # permissions and app review. It cannot search arbitrary consumer posts.
        for topic,hashtag,_ in TOPICS[:4]:
            params=urllib.parse.urlencode({"user_id":user_id,"q":hashtag,"access_token":token})
            data=get_json("https://graph.facebook.com/v23.0/ig_hashtag_search?"+params)
            ids=data.get("data",[])
            if not ids:continue
            tagid=ids[0]["id"]
            fields="id,caption,media_type,permalink,timestamp,like_count,comments_count"
            params=urllib.parse.urlencode({"user_id":user_id,"fields":fields,"limit":"25","access_token":token})
            result=get_json(f"https://graph.facebook.com/v23.0/{tagid}/recent_media?"+params)
            for media in result.get("data",[]):
                if media.get("media_type") not in ("VIDEO","REELS"):continue
                link=media.get("permalink","")
                if link.startswith("https://www.instagram.com/"):
                    items.append(candidate("Instagram",link,media.get("caption","")[:200],"",
                                           media.get("timestamp",""),None,media.get("like_count"),topic))
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as exc:
        return items,"Instagram API error: "+str(exc)
    return items[:MAX_PER_PLATFORM],"connected"

def tiktok_links():
    # TikTok Research API is non-commercial and requires research eligibility.
    # Search URLs are prompts for discovering and contacting creators; they are
    # NOT results or proof that a video exists or may be reused.
    return [{"platform":"TikTok","topic":topic,
             "search_url":"https://www.tiktok.com/search/video?q="+urllib.parse.quote(q),
             "status":"creator_discovery_link_only"} for topic,_,q in TOPICS]

def youtube_items():
    p=Path("out/viral_research.json")
    if not p.exists():return [],"YouTube API research not available"
    data=json.loads(p.read_text(encoding="utf-8"))
    items=[candidate("YouTube",x.get("url",""),x.get("title",""),x.get("channel",""),
                     x.get("published_at",""),x.get("views"),None,x.get("query",""))
           for x in data.get("videos",[]) if x.get("url","").startswith("https://www.youtube.com/")]
    return items,"connected"

def main():
    out=Path("out");out.mkdir(exist_ok=True)
    youtube,ystatus=youtube_items()
    instagram,istatus=instagram_hashtags(os.getenv("INSTAGRAM_ACCESS_TOKEN",""),
                                          os.getenv("INSTAGRAM_USER_ID",""))
    x,xstatus=x_recent(os.getenv("X_BEARER_TOKEN",""))
    items=youtube+instagram+x
    items=sorted(items,key=lambda i:(
        i["views"] is not None,int(i["views"] or 0),int(i["likes"] or 0)),reverse=True)
    data={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
          "purpose":"Cross-platform video research and creator outreach; no media downloaded",
          "platform_status":{"YouTube":ystatus,"Instagram":istatus,"X":xstatus,
                             "TikTok":"creator search links only; no commercial Research API access"},
          "candidate_count":len(items),
          "candidates":items,
          "tiktok_creator_searches":tiktok_links(),
          "reuse_notice":"Popularity and public URLs do not grant reuse rights. No automatic downloads."}
    (out/"multiplatform_research.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (out/"multiplatform_research.csv").open("w",newline="",encoding="utf-8-sig") as fp:
        fields=["platform","topic","title","author","url","published_at","views","likes","camera_authenticity","reuse_permission","status"]
        writer=csv.DictWriter(fp,fieldnames=fields,extrasaction="ignore")
        writer.writeheader();writer.writerows(items)
    print(json.dumps({"candidate_count":len(items),"by_platform":{
        p:sum(x["platform"]==p for x in items) for p in ("YouTube","Instagram","X")},
        "status":data["platform_status"]}))
if __name__=="__main__":main()
