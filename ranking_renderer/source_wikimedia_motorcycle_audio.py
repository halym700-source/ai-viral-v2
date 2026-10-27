#!/usr/bin/env python3
"""Five Wikimedia Commons original-audio motorcycle clips. Attribution in manifest."""
import json
from pathlib import Path
from urllib.parse import quote

items=[
("Wall of Death - Pitts Todeswand 2017 - Jagath Perera.webm","Toothswung","CC BY-SA 3.0","WALL OF DEATH"),
("DragBike FIM STTF 2024.webm","Auge=mit","CC BY-SA 4.0","DRAG RACE"),
("2 Stroke Dirt Bike Engine.webm","2StrokeFever","CC BY 4.0","2-STROKE ENGINE"),
("2018 Montevideo Karting Grand Prix - Exhibición de motocicletas 09.webm","NaBUru38","CC BY-SA 4.0","RACE SHOW"),
("Wall of Death - Four motocycles at Motodrom 2017.webm","Toothswung","CC BY-SA 3.0","FOUR BIKES"),
]
clips=[]
for rank,(name,creator,license,label) in zip(range(5,0,-1),items):
    page="https://commons.wikimedia.org/wiki/File:"+quote(name.replace(" ","_"))
    url="https://commons.wikimedia.org/wiki/Special:Redirect/file/"+quote(name)
    clips.append({"rank":rank,"url":url,"start":0,"label":label,
                  "source":page,"creator":creator,"license":license,
                  "require_original_audio":True})
Path("out").mkdir(exist_ok=True)
Path("out/ranking_manifest.json").write_text(json.dumps({
    "title":"RANKING WILDEST MOTORCYCLE MOMENTS",
    "intro":"Ranking wildest motorcycle moments",
    "brand":"RESHRANKS","clip_seconds":4.8,"clips":clips
},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
Path("out/ATTRIBUTION.txt").write_text(
    "Video: RANKING WILDEST MOTORCYCLE MOMENTS (edited 24-second ranking)\n"+
    "\n".join(f"{name} — {creator} — {license} — https://commons.wikimedia.org/wiki/File:{quote(name.replace(' ','_'))}" for name,creator,license,label in items)+
    "\nLicense links: https://creativecommons.org/licenses/by/4.0/ ; https://creativecommons.org/licenses/by-sa/4.0/ ; https://creativecommons.org/licenses/by-sa/3.0/\n"+
    "Adapted footage: cut, cropped to 9:16, ranked, mixed with intro voice and sound effects. BY-SA derivative licensing obligations apply.\n",
    encoding="utf-8")
print(json.dumps({"sources":len(clips),"all_required_original_audio":True}))
