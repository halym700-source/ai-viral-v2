#!/usr/bin/env python3
"""Offline video test for five independently generated video clips."""
import json,os,subprocess,tempfile
from pathlib import Path
FF=os.getenv("FFMPEG_BIN","ffmpeg")
with tempfile.TemporaryDirectory() as td:
    clips=[]
    for rank in (5,4,3,2,1):
        p=Path(td)/f"clip_{rank}.mp4"
        subprocess.run([FF,"-y","-hide_banner","-loglevel","error",
                        "-f","lavfi","-i","testsrc2=size=240x426:rate=12:duration=3",
                        "-f","lavfi","-i",f"sine=frequency={rank*110+180}:duration=3",
                        "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
                        "-c:a","aac",str(p)],check=True)
        clips.append({"rank":rank,"file":str(p),"label":f"MOMENT {rank}"})
    os.environ["RANK_TEST_MODE"]="1"
    os.environ["RANK_WIDTH"]="360"
    os.environ["RANK_HEIGHT"]="640"
    os.environ["RANK_FPS"]="12"
    os.environ["RANKING_JSON"]=json.dumps({"title":"TOP 5 CRAZIEST MOMENTS",
        "brand":"RANKING SHORTS","intro":"Top five craziest moments!",
        "clip_seconds":4.8,"clips":clips})
    import render
    render.main()
    target=Path("out/ranking_short.mp4")
    assert target.is_file() and target.stat().st_size>200000
    dur=render.duration(target)
    assert 23<dur<25.5,dur
    assert render.has_audio(target)
    frame=target.parent/"ranking_preview.png"
    subprocess.run([FF,"-y","-hide_banner","-loglevel","error","-ss","5",
                    "-i",str(target),"-frames:v","1",str(frame)],check=True)
    assert frame.stat().st_size>5000
    assert (target.parent/"ranking_sources.json").is_file()
    print(f"PASS: 5 ordered clips; {dur:.2f}s; clip audio; overlay; intro placeholder")
