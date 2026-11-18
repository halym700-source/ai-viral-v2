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
    blocks=re.split(r"\n\s*\n", path.read_text(encoding="utf-8",errors="ignore"))
    out=[]
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

def parse_srt(path):
    text=path.read_text(encoding="utf-8",errors="ignore")
    blocks=re.split(r"\n\s*\n",text); out=[]
    for b in blocks:
        lines=[x.strip() for x in b.splitlines() if x.strip()]
        ts=next((x for x in lines if "-->" in x),None)
        if not ts: continue
        m=re.search(r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})",ts)
        if not m: continue
        def sec(v):
            h,mi,rest=re.split(":",v.replace(",","."))
            return int(h)*3600+int(mi)*60+float(rest)
        text=clean(" ".join(x for x in lines[lines.index(ts)+1:] if "-->" not in x and not x.isdigit()))
        if text: out.append({"start":sec(m.group(1)),"end":sec(m.group(2)),"text":text})
    return out

def srt_time(x):
    ms=int(round((x-int(x))*1000)); total=int(x)
    h=total//3600; m=(total%3600)//60; s=total%60
    if ms>=1000: s+=1; ms-=1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(items,path):
    with path.open("w",encoding="utf-8") as f:
        for i,x in enumerate(items,1):
            f.write(f"{i}\n{srt_time(x['start'])} --> {srt_time(x['end'])}\n{x['text']}\n\n")

HOOKS=[
    "ama","fakat","çünkü","neden","aslında","inanılmaz","şok","sır","gerçek","önemli",
    "asla","hiçbir zaman","ilk kez","son kez","en büyük","dikkat","unutma","hata","yanlış",
    "how","why","but","because","secret","truth","important","never","mistake","first time",
    "you need","don't","didn't","wait","crazy","exactly"
]

def score(text, duration):
    lo=text.lower()
    hook=sum(2.5 for w in HOOKS if w in lo)
    questions=text.count("?")*1.5
    excitement=text.count("!")*1.2
    density=min(len(re.findall(r"\b\w+\b",text))/max(duration,1)/2.5,3)
    quotable=sum(1.0 for p in ["şunu söyleyeyim","bence","benim için","the point is","i think","listen"])
    return round(hook+questions+excitement+density+quotable,3)

def clips(cues,n):
    if not cues: return []
    total_end=cues[-1]["end"]; candidates=[]
    target_lengths=(30,45,60)
    for i,c in enumerate(cues):
        for target in target_lengths:
            start=max(0,c["start"]-2)
            end=min(total_end,start+target)
            j=i
            while j+1<len(cues) and cues[j]["end"]<end: j+=1
            end=min(total_end,max(end,cues[j]["end"]))
            if end-start<25: continue
            text=" ".join(x["text"] for x in cues[i:j+1])
            # Prefer clips with a complete sentence near the beginning and a strong hook.
            s=score(text,end-start)
            if "?" in text[:220] or "!" in text[:220]: s+=1
            candidates.append({"start":start,"end":end,"text":text,"score":s})
    # Deduplicate near-identical windows.
    candidates.sort(key=lambda x:x["score"],reverse=True)
    selected=[]
    for c in candidates:
        overlap=False
        for s in selected:
            inter=max(0,min(c["end"],s["end"])-max(c["start"],s["start"]))
            union=max(c["end"],s["end"])-min(c["start"],s["start"])
            if inter/max(union,1)>0.35: overlap=True; break
        if not overlap:
            selected.append(c)
        if len(selected)>=n: break
    return sorted(selected,key=lambda x:x["start"])

def transcribe_local(video):
    # No paid API: faster-whisper runs locally on the GitHub runner.
    from faster_whisper import WhisperModel
    model_name=os.getenv("WHISPER_MODEL","base")
    device=os.getenv("WHISPER_DEVICE","cpu")
    compute=os.getenv("WHISPER_COMPUTE_TYPE","int8" if device=="cpu" else "float16")
    print(f"Local Whisper: model={model_name} device={device} compute={compute}", flush=True)
    model=WhisperModel(model_name,device=device,compute_type=compute)
    segments,info=model.transcribe(str(video),beam_size=5,vad_filter=True,word_timestamps=False)
    cues=[]
    for seg in segments:
        text=clean(seg.text)
        if text and float(seg.end)>float(seg.start):
            cues.append({"start":float(seg.start),"end":float(seg.end),"text":text})
    print(f"Whisper detected language={getattr(info,'language','?')} segments={len(cues)}",flush=True)
    return cues

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    ap.add_argument("--count",type=int,default=5)
    a=ap.parse_args()
    if "youtube.com" not in urlparse(a.url).netloc and "youtu.be" not in urlparse(a.url).netloc:
        raise SystemExit("Only YouTube URLs are supported.")
    OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    # Prefer YouTube captions when available, then fall back to local Whisper.
    run(["yt-dlp","--no-playlist","--write-auto-subs","--write-subs","--sub-langs","tr.*,en.*","--sub-format","vtt","--skip-download","-o",str(WORK/"source.%(ext)s"),a.url])
    subs=list(WORK.glob("*.vtt"))
    cues=[]
    if subs:
        sub=next((p for p in subs if ".tr." in p.name.lower()),subs[0])
        cues=parse_vtt(sub)
        print(f"Using YouTube subtitles: {sub.name}",flush=True)
    info=WORK/"info.json"
    with info.open("w",encoding="utf-8") as f:
        run(["yt-dlp","--no-playlist","--dump-single-json","--skip-download",a.url],stdout=f)
    meta=json.loads(info.read_text(encoding="utf-8")); title=meta.get("title","YouTube Video")
    run(["yt-dlp","--no-playlist","-f","bv*[height<=1080]+ba/b[height<=1080]/b","--merge-output-format","mp4","-o",str(WORK/"source.%(ext)s"),a.url])
    video=WORK/"source.mp4"
    if not cues:
        cues=transcribe_local(video)
    if not cues: raise RuntimeError("No speech/subtitles were detected.")
    selected=clips(cues,a.count)
    if not selected: raise RuntimeError("No suitable clips were found.")
    manifest={"source":{"title":title,"url":a.url or "", "file":str(video.name) if a.file else ""},"clips":[]}
    for idx,c in enumerate(selected,1):
        stem=f"clip_{idx:02d}"; srt=OUT/(stem+".srt"); mp4=OUT/(stem+".mp4")
        local=[{"start":max(0,x["start"]-c["start"]),"end":min(c["end"],x["end"])-c["start"],"text":x["text"]}
               for x in cues if x["end"]>c["start"] and x["start"]<c["end"]]
        write_srt(local,srt)
        # Center crop to 9:16. For webcam/gameplay streams this is intentionally conservative.
        vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        vf+=f",subtitles={srt.as_posix()}:force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=120'"
        run(["ffmpeg","-y","-ss",str(c["start"]),"-i",str(video),"-t",str(c["end"]-c["start"]),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart",str(mp4)])
        manifest["clips"].append({"file":mp4.name,"srt":srt.name,"start":c["start"],"end":c["end"],"score":c["score"],"text":c["text"]})
    tags=["shorts","viral","kesit","youtubeshorts"]+re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]{4,}",title.lower())[:8]
    (OUT/"metadata.json").write_text(json.dumps({"title":title+" | En İyi Kesitler","description":title+"\n\nOtomatik seçilen kısa kesitler.","hashtags":["#shorts","#viral","#kesit","#youtubeshorts"],"tags":list(dict.fromkeys(tags))},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
