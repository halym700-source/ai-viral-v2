#!/usr/bin/env python3
"""Five-to-one licensed video rankings, separate from TextVibe Shorts."""
import json, os, re, subprocess, tempfile, urllib.request, urllib.parse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FF = os.getenv("FFMPEG_BIN", "ffmpeg")
OUT = Path("out")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

def duration(path):
    p=subprocess.run([FF,"-hide_banner","-i",str(path)],capture_output=True,text=True)
    m=re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)",p.stderr)
    if not m: raise ValueError("Cannot read clip duration: "+str(path))
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def has_audio(path):
    return "Audio:" in subprocess.run([FF,"-hide_banner","-i",str(path)],capture_output=True,text=True).stderr

def font(sz):
    return ImageFont.truetype(FONT,sz) if Path(FONT).exists() else ImageFont.load_default()

def lines(text, n=24):
    out=[]
    for w in text.upper().split():
        if not out or len(out[-1])+len(w)+1>n: out.append(w)
        else: out[-1]+=" "+w
    return out[:3]

def draw_card(path, title, label, rank, brand, w, h):
    s=w/720; im=Image.new("RGBA",(w,h));d=ImageDraw.Draw(im,"RGBA")
    d.rounded_rectangle((17*s,18*s,w-17*s,218*s),radius=int(20*s),fill=(10,14,25,210))
    d.text((32*s,24*s),brand[:30].upper(),font=font(int(23*s)),fill="#FFCB38")
    for i,ln in enumerate(lines(title,max(12,int(28*720/w)))):
        d.text((32*s,(65+49*i)*s),ln,font=font(int(37*s)),fill="white",stroke_width=max(1,int(2*s)),stroke_fill="#0a0b10")
    d.ellipse((26*s,265*s,164*s,403*s),fill="#FFCB38",outline="white",width=max(1,int(3*s)))
    f=font(int(78*s));bb=d.textbbox((0,0),str(rank),font=f)
    d.text(((190*s-(bb[2]-bb[0]))/2,334*s-(bb[3]-bb[1])/2-bb[1]),str(rank),font=f,fill="#131722")
    if label:
        y=h-int(125*s)
        d.rounded_rectangle((20*s,y,w-20*s,h-int(52*s)),radius=int(16*s),fill=(8,10,16,197))
        f=font(int(30*s));text=label.upper()[:34]; bb=d.textbbox((0,0),text,font=f)
        d.text(((w-(bb[2]-bb[0]))/2,y+int(16*s)),text,font=f,fill="white")
    step=(w-60*s)/5
    for i in range(5):
        x=30*s+i*step
        d.rounded_rectangle((x,h-35*s,x+step-6*s,h-23*s),radius=int(4*s),
            fill="#FFCB38" if i==5-rank else (255,255,255,170))
    im.save(path)

def download(url, path):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise ValueError("Clips require public HTTPS direct MP4 URLs")
    host=p.hostname.lower()
    if host in ("localhost","127.0.0.1","0.0.0.0") or host.endswith(".local"):
        raise ValueError("Private hosts are disallowed")
    req=urllib.request.Request(url,headers={"User-Agent":"RankingShorts/1.0"})
    with urllib.request.urlopen(req,timeout=40) as res, path.open("wb") as dst:
        count=0
        while True:
            buf=res.read(1024*1024)
            if not buf:break
            count+=len(buf)
            if count>180*1024*1024: raise ValueError("Clip too large")
            dst.write(buf)
    if count<1024:raise ValueError("Clip is empty")

def intro_voice(text, path):
    if os.getenv("RANK_TEST_MODE")=="1":
        run([FF,"-y","-hide_banner","-loglevel","error","-f","lavfi","-i",
             "sine=frequency=640:duration=1.2","-af","volume=0.08",str(path)])
    else:
        subprocess.run([sys.executable,"-m","edge_tts","--voice","en-US-GuyNeural",
                        "--text",text,"--write-media",str(path)],check=True,timeout=75)
    return path

def main():
    cfg=json.loads(os.environ["RANKING_JSON"]) if os.getenv("RANKING_JSON") else json.loads(
        Path(os.getenv("RANKING_MANIFEST","ranking_renderer/example_manifest.json")).read_text())
    clips=cfg["clips"]
    if len(clips)!=5 or sorted([int(c["rank"]) for c in clips])!=[1,2,3,4,5]:
        raise ValueError("Exactly five clips with ranks 5,4,3,2,1 are required")
    clips=sorted(clips,key=lambda c:int(c["rank"]),reverse=True)
    test=os.getenv("RANK_TEST_MODE")=="1"
    w=int(os.getenv("RANK_WIDTH","720"));h=int(os.getenv("RANK_HEIGHT","1280"))
    fps=int(os.getenv("RANK_FPS","30"));seconds=float(cfg.get("clip_seconds",4.8))
    if not (240<=w<=1080 and 426<=h<=1920 and 8<=fps<=60 and 4<=seconds<=10):
        raise ValueError("Invalid output dimensions or segment length")
    title=str(cfg.get("title","TOP 5 CRAZIEST MOMENTS"))
    brand=str(cfg.get("brand","RANKING SHORTS"))
    intro=str(cfg.get("intro",title))[:180]
    OUT.mkdir(exist_ok=True)
    records=[]
    with tempfile.TemporaryDirectory() as temp:
        tmp=Path(temp);segments=[]
        for i,c in enumerate(clips):
            if not test and (not c.get("source") or not c.get("license")):
                raise ValueError("Each clip needs verified source and license metadata")
            if bool(c.get("url"))==bool(c.get("file")):
                raise ValueError("Provide either file or url per clip")
            path=Path(c["file"]).resolve() if c.get("file") else tmp/f"source_{i}.mp4"
            if c.get("url"): download(c["url"],path)
            if not path.is_file():raise FileNotFoundError(path)
            start=max(0,float(c.get("start",0)))
            if duration(path)<start+0.5:raise ValueError("Source too short")
            card=tmp/f"card_{i}.png"
            draw_card(card,title,str(c.get("label","")),int(c["rank"]),brand,w,h)
            segment=tmp/f"segment_{i}.mp4"
            cmd=[FF,"-y","-hide_banner","-loglevel","error","-stream_loop","-1",
                 "-ss",str(start),"-i",str(path),"-loop","1","-i",str(card)]
            audio=has_audio(path)
            if not audio:cmd+=["-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100"]
            v=(f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
               f"crop={w}:{h},fps={fps},setsar=1[v0];[v0][1:v]overlay=0:0:shortest=1[v]")
            cmd+=["-filter_complex",v,"-map","[v]","-map","0:a:0" if audio else "2:a:0",
                  "-t",str(seconds),"-c:v","libx264","-preset","veryfast","-crf","23",
                  "-pix_fmt","yuv420p","-c:a","aac","-ar","44100","-ac","2",
                  "-b:a","128k","-shortest",str(segment)]
            run(cmd);segments.append(segment)
            records.append({"rank":int(c["rank"]),"source":c.get("source",str(path)),
                            "license":c.get("license","synthetic CI test"),"label":c.get("label","")})
        listing=tmp/"concat.txt"
        listing.write_text("".join("file '"+str(p)+"'\n" for p in segments))
        joined=tmp/"joined.mp4"
        run([FF,"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0",
             "-i",str(listing),"-c","copy",str(joined)])
        speech=Path(os.environ["RANKING_INTRO_AUDIO"]) if os.getenv("RANKING_INTRO_AUDIO") else intro_voice(intro,tmp/"intro.mp3")
        video=OUT/"ranking_short.mp4"
        mix=("[0:a]volume='if(lt(t,3),0.30,1)':eval=frame[bg];"
             "[1:a]adelay=180:all=1,volume=1.5[tts];"
             "[bg][tts]amix=inputs=2:duration=first:dropout_transition=0[a]")
        run([FF,"-y","-hide_banner","-loglevel","error","-i",str(joined),"-i",str(speech),
             "-filter_complex",mix,"-map","0:v:0","-map","[a]","-c:v","copy",
             "-c:a","aac","-b:a","160k","-movflags","+faststart",str(video)])
    (OUT/"ranking_sources.json").write_text(json.dumps({"title":title,"clips":records},indent=2))
    print(json.dumps({"output":str(video),"duration":duration(video),"bytes":video.stat().st_size}))
if __name__=="__main__":main()
