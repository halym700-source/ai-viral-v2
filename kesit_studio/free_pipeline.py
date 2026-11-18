#!/usr/bin/env python3
import argparse, json, re, subprocess, os
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path.cwd(); OUT=ROOT/"out"; WORK=ROOT/"work"

def run(cmd, **kw):
    print("$ "+" ".join(map(str,cmd)), flush=True)
    return subprocess.run(cmd, check=True, **kw)

def clean(s):
    s=re.sub(r"<[^>]+>"," ",s)
    s=re.sub(r"&(?:amp|lt|gt|quot|#39);",lambda m:{"&amp;":"&","&lt;":"<","&gt;":">","&quot;":'"',"&#39;":"'"}.get(m.group(),m.group()),s)
    return re.sub(r"\s+"," ",s).strip()

def parse_vtt(path):
    blocks=re.split(r"\n\s*\n",path.read_text(encoding="utf-8",errors="ignore")); out=[]
    for b in blocks:
        lines=[x.strip("\ufeff") for x in b.splitlines() if x.strip()]
        ts=next((x for x in lines if "-->" in x),None)
        if not ts: continue
        m=re.search(r"(\d{2}:\d{2}:\d{2}(?:\.\d{3})?)\s*-->\s*(\d{2}:\d{2}:\d{2}(?:\.\d{3})?)",ts)
        if not m: continue
        def sec(v):
            h,mi,rest=v.split(":"); return int(h)*3600+int(mi)*60+float(rest)
        text=clean(" ".join(x for x in lines[lines.index(ts)+1:] if "-->" not in x))
        if text: out.append({"start":sec(m.group(1)),"end":sec(m.group(2)),"text":text})
    return out

def srt_time(x):
    ms=int(round((x-int(x))*1000)); total=int(x); h=total//3600; m=(total%3600)//60; s=total%60
    if ms>=1000: s+=1; ms-=1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(items,path):
    with path.open("w",encoding="utf-8") as f:
        for i,x in enumerate(items,1):
            f.write(f"{i}\n{srt_time(x['start'])} --> {srt_time(x['end'])}\n{x['text']}\n\n")

HOOKS=["ama","fakat","çünkü","neden","aslında","inanılmaz","şok","sır","gerçek","önemli","asla","hiçbir zaman","ilk kez","en büyük","dikkat","unutma","hata","yanlış","how","why","but","because","secret","truth","important","never","mistake","first time","you need","don't","wait","crazy","exactly"]

def score(text,duration):
    lo=text.lower()
    return round(sum(2.5 for w in HOOKS if w in lo)+text.count("?")*1.5+text.count("!")*1.2+min(len(re.findall(r"\b\w+\b",text))/max(duration,1)/2.5,3),3)

def clips(cues,n):
    if not cues:return []
    total_end=cues[-1]["end"]; candidates=[]
    for i,c in enumerate(cues):
        for target in (30,45,60):
            start=max(0,c["start"]-2); end=min(total_end,start+target); j=i
            while j+1<len(cues) and cues[j]["end"]<end:j+=1
            end=min(total_end,max(end,cues[j]["end"]))
            if end-start<25:continue
            text=" ".join(x["text"] for x in cues[i:j+1]); s=score(text,end-start)
            if "?" in text[:220] or "!" in text[:220]:s+=1
            candidates.append({"start":start,"end":end,"text":text,"score":s})
    candidates.sort(key=lambda x:x["score"],reverse=True); selected=[]
    for c in candidates:
        if not any(max(0,min(c["end"],s["end"])-max(c["start"],s["start"])) / max(max(c["end"],s["end"])-min(c["start"],s["start"]),1) > .35 for s in selected):
            selected.append(c)
        if len(selected)>=n:break
    return sorted(selected,key=lambda x:x["start"])

def transcribe_local(video):
    from faster_whisper import WhisperModel
    model_name=os.getenv("WHISPER_MODEL","base"); device=os.getenv("WHISPER_DEVICE","cpu")
    compute=os.getenv("WHISPER_COMPUTE_TYPE","int8" if device=="cpu" else "float16")
    model=WhisperModel(model_name,device=device,compute_type=compute)
    segments,info=model.transcribe(str(video),beam_size=5,vad_filter=True)
    cues=[{"start":float(s.start),"end":float(s.end),"text":clean(s.text)} for s in segments if clean(s.text) and float(s.end)>float(s.start)]
    print(f"Whisper language={getattr(info,'language','?')} segments={len(cues)}",flush=True); return cues

def detect_webcam(video):
    # Free local heuristic: find a small, persistent face likely belonging to a webcam overlay.
    # Returns the best face box so the top panel can show the actual webcam area.
    try:
        import cv2
        cap=cv2.VideoCapture(str(video))
        if not cap.isOpened(): return None
        total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total<=0:return None
        cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        samples=[]
        for frac in (0.15,0.35,0.55,0.75,0.9):
            cap.set(cv2.CAP_PROP_POS_FRAMES,int(total*frac)); ok,frame=cap.read()
            if not ok: continue
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            faces=cascade.detectMultiScale(gray,1.1,5,minSize=(40,40))
            h,w=gray.shape
            candidates=[]
            for x,y,fw,fh in faces:
                area=(fw*fh)/(w*h)
                if area < 0.20 and (y < h*0.50 or x < w*0.50 or x+fw > w*0.50):
                    candidates.append((x,y,fw,fh))
            if candidates:
                candidates.sort(key=lambda box:min(box[0],box[1],w-(box[0]+box[2]),h-(box[1]+box[3])))
                samples.append(candidates[0])
        cap.release()
        if len(samples)<2:
            print(f"Webcam heuristic: {len(samples)}/5 -> False",flush=True)
            return None
        x=sum(box[0] for box in samples)//len(samples); y=sum(box[1] for box in samples)//len(samples)
        fw=sum(box[2] for box in samples)//len(samples); fh=sum(box[3] for box in samples)//len(samples)
        box={"x":x,"y":y,"w":fw,"h":fh}
        print(f"Webcam heuristic: {len(samples)}/5 -> {box}",flush=True)
        return box
    except Exception as e:
        print(f"Webcam detection skipped: {e}",flush=True)
        return None

def subtitle_style(name):
    styles={
      "bold":"FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=130",
      "classic":"FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=120",
      "yellow":"FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=130",
      "minimal":"FontName=DejaVu Sans,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=100",
    }
    return styles.get(name,styles["bold"])

def render_video(src,mp4,start,duration,srt,layout,substyle,webcam):
    st=srt.as_posix().replace("'", "\\'")
    sub=f"subtitles='{st}':force_style='{subtitle_style(substyle)}'"
    if layout=="webcam-top" or (layout=="auto" and webcam):
        # Top panel shows the detected webcam face; bottom panel keeps the main video.
        if webcam:
            x,y,w,h=webcam["x"],webcam["y"],webcam["w"],webcam["h"]
            pad_x=max(w*2.2,120); pad_y=max(h*2.2,100)
            left=max(0,int(x-pad_x)); top=max(0,int(y-pad_y))
            cw=max(1,int(w+2*pad_x)); ch=max(1,int(h+2*pad_y))
            top_filter=f"crop={cw}:{ch}:{left}:{top},scale=1080:640"
        else:
            top_filter="crop=iw:ih*0.33:0:0,scale=1080:640"
        bottom_filter="scale=1080:1280:force_original_aspect_ratio=increase,crop=1080:1280"
        vf=f"[0:v]split=2[a][b];[a]{top_filter}[a1];[b]{bottom_filter}[b1];[a1][b1]vstack=inputs=2,{sub}"
    else:
        vf=f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{sub}"
    run(["ffmpeg","-y","-ss",str(start),"-i",str(src),"-t",str(duration),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart",str(mp4)])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--file")
    ap.add_argument("--count",type=int,default=5)
    ap.add_argument("--layout",choices=["auto","center","webcam-top"],default="auto")
    ap.add_argument("--subtitle-style",choices=["bold","classic","yellow","minimal"],default="bold")
    a=ap.parse_args()
    if not a.url and not a.file: raise SystemExit("Provide --url or --file.")
    OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)

    if a.file:
        video=Path(a.file); title=video.stem
        if not video.exists(): raise SystemExit(f"Video not found: {video}")
        subs=list(WORK.glob("*.vtt")); cues=[]
    else:
        if "youtube.com" not in urlparse(a.url).netloc and "youtu.be" not in urlparse(a.url).netloc: raise SystemExit("Only YouTube URLs are supported.")
        run(["yt-dlp","--no-playlist","--write-auto-subs","--write-subs","--sub-langs","tr.*,en.*","--sub-format","vtt","--skip-download","-o",str(WORK/"source.%(ext)s"),a.url])
        subs=list(WORK.glob("*.vtt")); cues=[]
        info=WORK/"info.json"
        with info.open("w",encoding="utf-8") as f: run(["yt-dlp","--no-playlist","--dump-single-json","--skip-download",a.url],stdout=f)
        meta=json.loads(info.read_text(encoding="utf-8")); title=meta.get("title","YouTube Video")
        run(["yt-dlp","--no-playlist","-f","bv*[height<=1080]+ba/b[height<=1080]/b","--merge-output-format","mp4","-o",str(WORK/"source.%(ext)s"),a.url])
        video=WORK/"source.mp4"

    if subs:
        sub=next((p for p in subs if ".tr." in p.name.lower()),subs[0]); cues=parse_vtt(sub); print(f"Using subtitles: {sub.name}",flush=True)
    if not cues: cues=transcribe_local(video)
    if not cues: raise RuntimeError("No speech/subtitles detected.")
    selected=clips(cues,max(1,a.count))
    if not selected: raise RuntimeError("No suitable clips found.")

    webcam=detect_webcam(video) if a.layout=="auto" else ({"x":0,"y":0,"w":1,"h":1} if a.layout=="webcam-top" else None)
    manifest={"source":{"title":title,"url":a.url or "","file":video.name},"settings":{"layout":a.layout,"webcam_detected":bool(webcam),"webcam_box":webcam,"subtitle_style":a.subtitle_style},"clips":[]}

    for idx,c in enumerate(selected,1):
        stem=f"clip_{idx:02d}"; srt=OUT/(stem+".srt"); mp4=OUT/(stem+".mp4")
        local=[{"start":max(0,x["start"]-c["start"]),"end":min(c["end"],x["end"])-c["start"],"text":x["text"]} for x in cues if x["end"]>c["start"] and x["start"]<c["end"]]
        write_srt(local,srt)
        render_video(video,mp4,c["start"],c["end"]-c["start"],srt,a.layout,a.subtitle_style,webcam)
        manifest["clips"].append({"file":mp4.name,"srt":srt.name,"start":c["start"],"end":c["end"],"score":c["score"],"text":c["text"]})

    tags=["shorts","viral","kesit","youtubeshorts"]+re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]{4,}",title.lower())[:8]
    (OUT/"metadata.json").write_text(json.dumps({"title":title+" | En İyi Kesitler","description":title+"\n\nOtomatik seçilen kısa kesitler.","hashtags":["#shorts","#viral","#kesit","#youtubeshorts"],"tags":list(dict.fromkeys(tags))},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
