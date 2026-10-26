#!/usr/bin/env python3
"""Select five real Pexels-licensed sample street clips mirrored on GitHub.

Source provenance: aparsoft/yolo-streamlit-detection-tracking/videos/ATTRIBUTION.md
The sample repository provides attribution and an independently hosted release.
"""
import json
from pathlib import Path
RELEASE="https://github.com/aparsoft/yolo-streamlit-detection-tracking/releases/download/sample-videos/"
ITEMS=[
 ("crosswalk_red_car.mp4","CROSSWALK","https://www.pexels.com/video/people-waiting-to-cross-the-street-on-the-pedestrian-lane-2836277/"),
 ("street_person_in_red.mp4","STREET STYLE","https://www.pexels.com/video/lively-urban-scene-with-diverse-pedestrians-37567255/"),
 ("street_dogs_bikes.mp4","BIKES & DOGS","https://www.pexels.com/video/vibrant-city-street-with-people-strolling-30507204/"),
 ("busy_intersection.mp4","INTERSECTION","https://www.pexels.com/video/busy-city-intersection-with-pedestrians-crossing-33865608/"),
 ("city_traffic_dense.mp4","RUSH HOUR","https://www.pexels.com/video/traffic-in-a-city-5681670/"),
]
def main():
    clips=[]
    for i,(name,label,page) in enumerate(ITEMS):
        clips.append({"rank":5-i,"url":RELEASE+name,"start":0,"label":label,
                      "source":page,"license":"Pexels License; original creator credited on Pexels"})
        print("CLIP",i+1,name,flush=True)
    manifest={"title":"RANKING BEST CITY STREET MOMENTS","intro":"Ranking the best city street moments!",
              "brand":"RANKING","clip_seconds":4.8,"clips":clips}
    out=Path("out/ranking_manifest.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(manifest,indent=2))
    print("READY",len(clips),flush=True)
if __name__=="__main__":
    main()
