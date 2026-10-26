#!/usr/bin/env python3
"""Read-only validation of Pexels key, YouTube OAuth and destination channel.

This script never uploads videos and never prints tokens or API keys.
"""
import json
import os
import urllib.parse
import urllib.request

def fail(message):
    raise SystemExit("NOT_READY: "+message)

def main():
    required=("PEXELS_API_KEY","YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET",
              "YOUTUBE_REFRESH_TOKEN","YOUTUBE_CHANNEL_ID")
    missing=[key for key in required if not os.getenv(key)]
    if missing:
        fail("Missing repository secrets/variable: "+", ".join(missing))
    pexels=urllib.request.Request(
        "https://api.pexels.com/v1/videos/search?query=surfing&orientation=portrait&per_page=1",
        headers={"Authorization":os.environ["PEXELS_API_KEY"],
                 "User-Agent":"RankingShorts/1.0"})
    try:
        with urllib.request.urlopen(pexels,timeout=25) as response:
            payload=json.load(response)
        if not payload.get("videos"):
            fail("Pexels key works, but no video results")
    except Exception as error:
        fail("Pexels connection failed: "+type(error).__name__)
    print("OK: Pexels API key and video search")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                      token_uri="https://oauth2.googleapis.com/token",
                      client_id=os.environ["YOUTUBE_CLIENT_ID"],
                      client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
                      scopes=["https://www.googleapis.com/auth/youtube.upload",
                              "https://www.googleapis.com/auth/youtube.readonly"])
    try:
        creds.refresh(Request())
        youtube=build("youtube","v3",credentials=creds,cache_discovery=False)
        result=youtube.channels().list(part="id,snippet",mine=True).execute()
        channels=result.get("items",[])
    except Exception as error:
        fail("YouTube OAuth validation failed: "+type(error).__name__)
    if len(channels)!=1:
        fail("OAuth did not resolve to exactly one YouTube channel")
    actual=channels[0]["id"]
    expected=os.environ["YOUTUBE_CHANNEL_ID"].strip()
    if actual!=expected:
        fail("OAuth is linked to a different channel; no uploads will occur")
    print("OK: YouTube OAuth connected to the configured channel")
    print("READY: API connections validated; all future uploads remain PRIVATE")

if __name__=="__main__":
    main()
