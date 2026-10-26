#!/usr/bin/env python3
"""Five-to-one licensed video rankings, separate from TextVibe Shorts."""
import json, os, re, subprocess, tempfile, urllib.request, urllib.parse, urllib.error, sys, time, email.utils, datetime
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

def text_width(draw, text, f, stroke=0):
    box=draw.textbbox((0,0),text,font=f,stroke_width=stroke)
    return box[2]-box[0]

def draw_card(path, title, label, rank, brand, w, h):
    """Minimal Polar-style ranking layout: bold top banner and left-side rank list."""
    s=w/720
    im=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(im,"RGBA")
    banner=int(182*s)
    d.rectangle((0,0,w,banner),fill=(0,0,0,255))
    raw=title.upper().replace("TOP 5 ","").replace("TOP FIVE ","")
    words=raw.split()
    if words and words[0]=="RANKING":
        words=words[1:]
    # Split the topic over two lines; highlight its hook word, not the whole line.
    if len(words)>=3:
        top=["RANKING",words[0]]
        bottom=words[1:]
    elif len(words)==2:
        top=["RANKING",words[0]]
        bottom=[words[1]]
    else:
        top=["RANKING"]
        bottom=words
    title_font=font(int(51*s))
    for row,y in ((top,35*s),(bottom,99*s)):
        while row and text_width(d," ".join(row),title_font)>w-34*s:
            title_font=font(max(22,int(title_font.size-2*s)))
        widths=[text_width(d,word,title_font,stroke=max(1,int(2*s))) for word in row]
        gap=11*s
        x=(w-sum(widths)-gap*max(0,len(row)-1))/2
        for j,word in enumerate(row):
            color="#FFFFFF"
            if row is top and j==1: color="#FFDF42"
            if row is bottom and j==0: color="#43C9FF"
            d.text((x,y),word,font=title_font,fill=color,
                   stroke_width=max(1,int(2*s)),stroke_fill="#0B0B0B")
            x+=widths[j]+gap
    # Five small outlined rank numbers at fixed positions. Only the current
    # clip's label appears, making the footage visible without heavy cards.
    palette={1:"#FFDC35",2:"#45B8FF",3:"#FF4D55",4:"#FFFFFF",5:"#FFFFFF"}
    f=font(int(45*s))
    labelfont=font(int(31*s))
    for r in range(1,6):
        y=(273+(r-1)*111)*s
        number=f"{r}."
        d.text((43*s,y+3*s),number,font=f,fill=palette[r],
               stroke_width=max(2,int(4*s)),stroke_fill="#121212")
        if r==rank:
            active=str(label or f"MOMENT {r}").upper()[:24]
            # Shrink the label so it never crosses the YouTube UI on the right.
            current_font=labelfont
            while text_width(d,active,current_font)>w-165*s and current_font.size>15*s:
                current_font=font(current_font.size-2)
            d.text((127*s,y+10*s),active,font=current_font,fill="#FFFFFF",
                   stroke_width=max(2,int(4*s)),stroke_fill="#141414")
    im.save(path)

def download(url, path):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise ValueError("Clips require public HTTPS direct media URLs")
    host=p.hostname.lower()
    if host in ("localhost","127.0.0.1","0.0.0.0") or host.endswith(".local"):
        raise ValueError("Private hosts are disallowed")
    # Commons can rate-limit shared GitHub Actions IPs. Respect Retry-After
    # and retry a bounded number of times instead of failing on first 429.
    req=urllib.request.Request(url,headers={
        "User-Agent":"ReshRanksPreview/1.0 (https://github.com/halym700-source/ai-viral-v2)",
        "Accept":"video/*,application/octet-stream;q=0.9,*/*;q=0.5",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=60) as res, path.open("wb") as dst:
                count=0
                while True:
                    buf=res.read(1024*1024)
                    if not buf:break
                    count+=len(buf)
                    if count>180*1024*1024:
                        raise ValueError("Clip too large")
                    dst.write(buf)
            if count<1024:
                raise ValueError("Clip is empty")
            return
        except urllib.error.HTTPError as exc:
            path.unlink(missing_ok=True)
            if exc.code != 429 or attempt == 2:
                raise
            raw=exc.headers.get("Retry-After","")
            try:
                wait=max(15,min(120,int(raw)))
            except ValueError:
                wait=30*(attempt+1)
            print(f"Source rate limited (429). Respecting Retry-After: waiting {wait}s before retry {attempt+2}/3",flush=True)
            time.sleep(wait)
        except Exception:
            path.unlink(missing_ok=True)
            raise

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
        # Three-layer original transition: bright cue, short whoosh, low punch.
        # Identical timing and sound design for each of ranks 5,4,3,2,1.
        delays=[round(i*seconds*1000) for i in range(5)]
        filters=[]
        for input_index,prefix in ((2,"beep"),(3,"whoosh"),(4,"punch")):
            filters.append(f"[{input_index}:a]asplit=5"+ "".join(f"[{prefix}{i}]" for i in range(5)))
            for i,ms in enumerate(delays):
                if prefix=="beep":
                    effect="afade=t=out:st=0.06:d=0.19,volume=0.38"
                elif prefix=="whoosh":
                    effect="highpass=f=500,afade=t=out:st=0.03:d=0.18,volume=0.16"
                else:
                    effect="afade=t=out:st=0.01:d=0.16,volume=0.25"
                filters.append(f"[{prefix}{i}]{effect},adelay={ms}:all=1[{prefix}hit{i}]")
        inputs="".join(f"[{prefix}hit{i}]" for prefix in ("beep","whoosh","punch") for i in range(5))
        filters.append(inputs+"amix=inputs=15:duration=longest:normalize=0[sfx]")
        filters.append("[0:a]volume='if(lt(t,3),0.30,0.72)':eval=frame[bg]")
        filters.append("[1:a]adelay=180:all=1,volume=1.5[tts]")
        filters.append("[bg][tts][sfx]amix=inputs=3:duration=first:dropout_transition=0[a]")
        mix=";".join(filters)
        run([FF,"-y","-hide_banner","-loglevel","error",
             "-i",str(joined),"-i",str(speech),
             "-f","lavfi","-i","sine=frequency=940:sample_rate=44100:duration=0.25",
             "-f","lavfi","-i","anoisesrc=color=pink:sample_rate=44100:duration=0.21",
             "-f","lavfi","-i","sine=frequency=125:sample_rate=44100:duration=0.17",
             "-filter_complex",mix,"-map","0:v:0","-map","[a]","-c:v","copy",
             "-c:a","aac","-b:a","160k","-movflags","+faststart",str(video)])
    (OUT/"ranking_sources.json").write_text(json.dumps({"title":title,"clips":records},indent=2))
    print(json.dumps({"output":str(video),"duration":duration(video),"bytes":video.stat().st_size}))
if __name__=="__main__":main()
