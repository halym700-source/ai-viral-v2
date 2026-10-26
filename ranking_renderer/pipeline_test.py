#!/usr/bin/env python3
"""Offline checks for source uniqueness, rights and YouTube metadata."""
from source_pexels import choose_files
from upload_youtube import video_metadata, contact_line
videos=[]
for n in range(6):
    videos.append({"id":n+1,"duration":12,"url":f"https://www.pexels.com/video/example-{n+1}/",
        "video_files":[{"file_type":"video/mp4","link":f"https://videos.pexels.com/video-{n}.mp4",
                        "width":720,"height":1280}]})
picks=choose_files(videos)
assert len(picks)==5 and [p["rank"] for p in picks]==[5,4,3,2,1]
assert len(set(p["source"] for p in picks))==5
manifest={"title":"TOP 5 EXAMPLE MOMENTS","clips":picks}
body=video_metadata(manifest)
assert body["status"]["privacyStatus"]=="private"
assert all(p["source"] in body["snippet"]["description"] for p in picks)
assert body["snippet"]["title"].endswith("#Shorts")
contact_body=video_metadata(manifest,contact_email="rights@example.org")
assert "rights@example.org" in contact_body["snippet"]["description"]
assert "rights@example.org" not in body["snippet"]["description"]
try:
    contact_line("not-an-email")
except ValueError:
    pass
else:
    raise AssertionError("Invalid public contact email must be rejected")
try:
    choose_files(videos[:4])
except ValueError:
    pass
else:
    raise AssertionError("Must fail when fewer than five licensed clips")
print("PASS: source selection, ranking, license metadata and upload description")
