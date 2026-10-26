#!/usr/bin/env python3
"""Publish an approved ranking MP4 using the owner's YouTube OAuth credentials."""
import json
import os
from pathlib import Path

def video_metadata(manifest):
    title = str(manifest["title"]).strip()[:90]
    if not title:
        raise ValueError("Missing video title")
    sources = manifest.get("clips", [])
    if len(sources) != 5:
        raise ValueError("Five licensed sources required")
    for clip in sources:
        if not str(clip.get("source","")).startswith("https://") or not clip.get("license"):
            raise ValueError("Missing source URL or license for a clip")
    description = ("Five standout moments, ranked from #5 to #1. Original edit and English intro.\n\n"
                   "Footage sources and reuse rights:\n" +
                   "\n".join(f"#{c['rank']}: {c['source']} ({c['license']})" for c in sources) +
                   "\n\n#Shorts #Top5 #Ranking")
    return {"snippet":{"title":title+" #Shorts", "description":description,
                       "categoryId":"24", "defaultLanguage":"en",
                       "tags":["Shorts","Top 5","Ranking"]},
            "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}

def main():
    if os.getenv("RANK_PUBLISH_APPROVED") != "YES":
        raise RuntimeError("Upload disabled: explicit publish approval required")
    path = Path("out/ranking_short.mp4")
    if not path.is_file() or path.stat().st_size < 100000:
        raise ValueError("Rendered MP4 missing")
    manifest = json.loads(Path("out/ranking_manifest.json").read_text())
    body = video_metadata(manifest)
    required = ["YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("YouTube OAuth secrets missing: "+", ".join(missing))
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(token=None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YOUTUBE_CLIENT_ID"],
                        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
                        scopes=["https://www.googleapis.com/auth/youtube.upload",
                                "https://www.googleapis.com/auth/youtube.readonly"])
    creds.refresh(Request())
    youtube = build("youtube","v3",credentials=creds,cache_discovery=False)
    channel = youtube.channels().list(part="id,snippet",mine=True).execute()
    items = channel.get("items",[])
    if len(items)!=1:
        raise RuntimeError("OAuth must resolve to exactly one YouTube channel")
    actual = items[0]["id"]
    expected = os.getenv("YOUTUBE_CHANNEL_ID","").strip()
    if not expected or actual != expected:
        raise RuntimeError("Wrong YouTube channel: expected configured channel ID")
    media = MediaFileUpload(str(path),mimetype="video/mp4",resumable=True,chunksize=8*1024*1024)
    request = youtube.videos().insert(part="snippet,status",body=body,media_body=media)
    result = None
    while result is None:
        _,result = request.next_chunk()
    video_id = result["id"]
    Path("out/youtube_publish.json").write_text(json.dumps({
        "video_id":video_id,"channel_id":actual,"url":"https://www.youtube.com/watch?v="+video_id
    },indent=2))
    print("Uploaded PRIVATE video for review: https://www.youtube.com/watch?v="+video_id)

if __name__=="__main__":
    main()
