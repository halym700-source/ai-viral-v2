#!/usr/bin/env python3
"""Render a vertical short from a Gemini scene package using free stock footage and FFmpeg motion graphics.
Optional AI clips can be supplied per scene as ai_video_url; stock footage is the automatic fallback.
"""
import os, sys, json, re, subprocess, tempfile, urllib.parse, urllib.request, pathlib, random

ROOT = pathlib.Path(".")
OUT = pathlib.Path("output")
OUT.mkdir(exist_ok=True)

def run(cmd):
    subprocess.run(cmd, check=True)

def fetch(url, path, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent":"SevenChannelStudio/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r, open(path, "wb") as f:
        f.write(r.read())

def pixabay_clip(query, dest):
    key = os.getenv("PIXABAY_API_KEY")
    if not key: return False
    params = urllib.parse.urlencode({"key":key,"q":query,"video_type":"film","safesearch":"true","per_page":12})
    try:
        with urllib.request.urlopen("https://pixabay.com/api/videos/?"+params, timeout=30) as r:
            data=json.load(r)
        hits=data.get("hits",[])
        if not hits: return False
        hit=random.choice(hits)
        variants=hit.get("videos",{})
        variant=variants.get("medium") or variants.get("small") or variants.get("large")
        if not variant or not variant.get("url"): return False
        fetch(variant["url"],dest)
        return True
    except Exception as e:
        print("Pixabay lookup failed:",e)
        return False

def safe_text(s):
    return re.sub(r"[^A-Za-z0-9 ,.!?'-]", "", str(s or ""))[:110]

def make_generated_background(dest, seconds, label, index):
    # A deterministic animated motion-graphic fallback; does not pretend to be AI footage.
    colors=[("0x101827","0x263c5a"),("0x17251f","0x42634a"),("0x251a2e","0x65436b")]
    c1,c2=colors[index%len(colors)]
    draw=safe_text(label).replace("'", "")
    vf=f"scale=1080:1920,drawbox=x=0:y=0:w=1080:h=1920:color={c1}@1:t=fill,drawbox=x=0:y=1200:w=1080:h=720:color={c2}@0.65:t=fill,drawtext=text='{draw}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=h*0.43:box=1:boxcolor=black@0.25:boxborderw=24,format=yuv420p"
    run(["ffmpeg","-y","-f","lavfi","-i",f"color=c={c1}:s=1080x1920:r=30:d={seconds}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",dest])

def main():
    raw=os.getenv("PACKAGE_JSON","")
    if not raw:
        raise SystemExit("PACKAGE_JSON input is missing.")
    package=json.loads(raw)
    channel=os.getenv("CHANNEL_ID","unknown")
    scenes=package.get("scenes") or []
    if not scenes: raise SystemExit("No scenes in package.")
    with tempfile.TemporaryDirectory() as td:
        clips=[]
        for i,scene in enumerate(scenes):
            seconds=max(2,min(12,int(float(scene.get("duration_seconds",5)))))
            clip=os.path.join(td,f"scene_{i:02d}.mp4")
            ai_url=scene.get("ai_video_url")
            got=False
            if ai_url:
                try: fetch(ai_url,clip); got=True
                except Exception as e: print("AI clip download failed; fallback to stock:",e)
            query=safe_text(scene.get("stock_search_query") or scene.get("visual_description") or scene.get("image_prompt") or channel)
            if not got:
                stock=os.path.join(td,f"stock_{i:02d}.mp4")
                if pixabay_clip(query,stock):
                    # Crop source footage to vertical and normalize duration/fps.
                    run(["ffmpeg","-y","-stream_loop","-1","-i",stock,"-t",str(seconds),"-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p","-an","-c:v","libx264","-preset","veryfast",clip])
                    got=True
            if not got:
                make_generated_background(clip,seconds,scene.get("on_screen_text") or scene.get("visual_description") or channel,i)
            normalized=os.path.join(td,f"norm_{i:02d}.mp4")
            if got and ai_url:
                run(["ffmpeg","-y","-stream_loop","-1","-i",clip,"-t",str(seconds),"-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p","-an","-c:v","libx264","-preset","veryfast",normalized])
            elif got:
                normalized=clip
            clips.append(normalized)
        listing=os.path.join(td,"concat.txt")
        with open(listing,"w") as f:
            for p in clips: f.write("file '"+os.path.abspath(p)+"'\n")
        silent=os.path.join(td,"silent.mp4")
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",listing,"-c","copy",silent])
        final=OUT/f"{channel}.mp4"
        narration=package.get("script","").strip()
        audio=None
        if narration and channel!="microdetail_garage":
            try:
                import asyncio, edge_tts
                audio=os.path.join(td,"voice.mp3")
                async def tts():
                    communicate=edge_tts.Communicate(narration,os.getenv("TTS_VOICE","en-US-GuyNeural"))
                    await communicate.save(audio)
                asyncio.run(tts())
            except Exception as e:
                print("TTS unavailable; exporting without narration:",e)
        if audio:
            run(["ffmpeg","-y","-i",silent,"-i",audio,"-map","0:v:0","-map","1:a:0","-shortest","-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart",str(final)])
        else:
            run(["ffmpeg","-y","-i",silent,"-c:v","copy","-an","-movflags","+faststart",str(final)])
        metadata={"channel_id":channel,"title":package.get("youtube_title",""),"description":package.get("youtube_description",""),"tags":package.get("tags",[]),"video_file":str(final),"visual_source":"AI clips when supplied; otherwise Pixabay stock; otherwise FFmpeg motion graphics","automatic_youtube_upload":False}
        (OUT/f"{channel}_metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
        print(json.dumps(metadata,ensure_ascii=False))

if __name__=="__main__": main()
