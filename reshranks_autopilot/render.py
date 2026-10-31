#!/usr/bin/env python3
"""HPC Ranking Shorts renderer: Hook -> Progression -> Climax (22.8 seconds).

Accepts only a verified five-source autodiscovery manifest. This produces a
video and provenance manifest; it does NOT publish to YouTube.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

OUT = Path(os.environ.get('RESH_WORK', 'out')).resolve()
OUT.mkdir(parents=True,exist_ok=True)
W,H,FPS = 1080,1920,30
SLOTS=[1.6,3.5,3.5,3.5,3.5,7.2]
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
YELLOW=(255,206,50,255)
WHITE=(255,255,255,255)


def cmd(argv,timeout=270):
    subprocess.run([str(v) for v in argv],timeout=timeout,check=True)


def ffprobe(file):
    data=subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)],timeout=35)
    return json.loads(data)


def getfont(size,bold=True):
    return ImageFont.truetype(BOLD if bold else FONT,size)


def fit(d,label,max_width,max_size=60):
    for size in range(max_size,19,-1):
        f=getfont(size)
        if d.textbbox((0,0),label,font=f,stroke_width=2)[2]<=max_width:
            return f
    return getfont(20)


def center(d,label,y,max_width=1010,max_size=59,color=WHITE):
    f=fit(d,label,max_width,max_size)
    box=d.textbbox((0,0),label,font=f,stroke_width=3)
    x=(W-(box[2]-box[0]))//2
    d.text((x,y),label,font=f,fill=color,stroke_width=4,stroke_fill=(0,0,0,225))


def badge(d,x,y,text,highlight=False):
    fill=YELLOW if highlight else (238,238,238,215)
    f=getfont(59)
    d.text((x,y),text,fill=fill,font=f,stroke_fill=(0,0,0,220),stroke_width=3)


def make_overlay(kind,topic,source,path):
    base=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(base)
    if kind=='hook':
        d.rounded_rectangle((40,90,1040,232),fill=(0,0,0,130),radius=30)
        center(d,'This One Sounds İNSANE',115,990,60,YELLOW)
    else:
        d.rounded_rectangle((35,70,1045,230),fill=(0,0,0,112),radius=25)
        center(d,topic.upper(),103,980,49,WHITE)
        # Right-side 5-to-1 progress indicator, deliberately small.
        d.rounded_rectangle((880,535,1040,940),fill=(0,0,0,118),radius=27)
        for i,rank in enumerate((5,4,3,2,1)):
            badge(d,923,555+i*75,f'#{rank}',highlight=rank==source['rank'])
        d.rounded_rectangle((38,1514,1043,1717),fill=(0,0,0,145),radius=28)
        center(d,f"#{source['rank']}  {source['name'].upper()}",1540,945,53,WHITE)
        center(d,source.get('subtitle','REAL ENGINE SOUND').upper(),1632,920,31,YELLOW)
    # Vertical, faint watermark on right edge.
    f=getfont(31)
    tmp=Image.new('RGBA',(330,51),(0,0,0,0))
    ImageDraw.Draw(tmp).text((5,6),'@reshranks',font=f,fill=(255,255,255,94))
    tmp=tmp.rotate(90,expand=True)
    base.alpha_composite(tmp,(1022,1150))
    base.save(path)


def split_segment(src,start,length,overlay,out,zoom=False):
    meta=ffprobe(src)
    streams=meta['streams']
    if not any(x['codec_type']=='audio' for x in streams):
        raise RuntimeError('Source does not contain an original audio track')
    if not any(x['codec_type']=='video' for x in streams):
        raise RuntimeError('Source lacks video track')
    duration=float(meta['format'].get('duration') or 0)
    if duration<length+0.15:
        raise RuntimeError(f'Source clip too short: {duration:.2f}s')
    begin=max(0,min(float(start),duration-length-0.1))
    # Slight center zoom hides unrelated lower thirds without distorting the bikes.
    filt='scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1'
    if zoom:
        filt+=',scale=1190:2116:flags=lanczos,crop=1080:1920'
    filt+=',fps=30,eq=contrast=1.045:saturation=1.08,format=yuv420p'
    graph=(f'[0:v]{filt}[b];[b][1:v]overlay=0:0:shortest=1:format=auto,'
           'format=yuv420p[v]')
    # Normalize wildly different recording volumes while leaving engine audio intact.
    af=f'aresample=44100,loudnorm=I=-16:TP=-2.0:LRA=11,afade=t=in:st=0:d=0.08,' \
       f'afade=t=out:st={max(0,length-0.12):.2f}:d=0.12'
    cmd(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{begin:.3f}',
         '-i',src,'-loop','1','-framerate','30','-i',overlay,
         '-filter_complex',graph,'-map','[v]','-map','0:a:0',
         '-af',af,'-t',f'{length:.3f}', '-r','30','-c:v','libx264',
         '-preset','fast','-crf','21','-g','60','-pix_fmt','yuv420p',
         '-c:a','aac','-ar','44100','-ac','2','-b:a','160k','-movflags','+faststart',out])


def describe(topic,sources):
    headline={'motorcycle_revs':'Ranking CRAZIEST Motorcycle Engine Sounds 🔥 #shorts',
              'supercar_exhaust':'Ranking WILDEST Supercar Exhaust Sounds 🔥 #shorts',
              'motorcycle_startups':'Ranking BEST Motorcycle Startup Sounds 🏍️ #shorts'}
    title=headline.get(topic,'Ranking CRAZIEST Engine Sounds 🔥 #shorts')
    names='\n'.join(f"#{s['rank']} {s['name']}" for s in sources)
    credits='\n'.join(f"#{s['rank']} {s.get('source_title',s['name'])[:75]} — {s.get('channel','Original creator')} — {s['url']} (CC BY indicated on YouTube)" for s in sources)
    description=(f'Which sound wins? 🔊 Listen to 5 engine sounds and comment your favorite.\n\n'
                 f'{names}\n\nAudio/video attribution (Creative Commons licenses as listed by their uploaders):\n'
                 f'{credits}\n\nSubjective sound ranking edited by @reshranks.\n'
                 '#shorts #ranking #enginesounds #motorcycle #reshranks')
    return title,description


def main():
    infile=OUT/'autodiscovered.json'
    if not infile.is_file(): raise RuntimeError('Missing autodiscovered.json')
    data=json.loads(infile.read_text())
    sources=data['sources']
    if len(sources)!=5 or [s.get('rank') for s in sources]!=[5,4,3,2,1]:
        raise RuntimeError('Requires precisely five ordered Ranking sources')
    ids=[s.get('video_id') for s in sources]
    if len(set(ids))!=5: raise RuntimeError('Duplicate YouTube videos in source list')
    for s in sources:
        if s.get('rights')!='cc_by_verified' or 'YouTube Data API' not in s.get('rights_evidence',''):
            raise RuntimeError('Source lacks verifiable Creative Commons record')
        file=Path(s.get('local_file','')).resolve()
        if not file.is_file() or not file.is_relative_to(OUT):
            raise RuntimeError('Source file was not downloaded into the authorized work directory')
        s['local_file']=str(file)
    entries=[(sources[-1],SLOTS[0],'hook')]+[(s,SLOTS[i+1],'rank') for i,s in enumerate(sources)]
    files=[]
    for i,(source,seconds,kind) in enumerate(entries):
        overlay=OUT/f'overlay_{i}.png'
        video=OUT/f'clip_{i}.mp4'
        make_overlay(kind,data['topic'],source,overlay)
        zoom= 'h2r' in source['name'].lower() or bool(source.get('crop_lower_label'))
        split_segment(source['local_file'],source.get('start',0),seconds,overlay,video,zoom=zoom)
        files.append(video)
    concat=OUT/'concat.txt'
    concat.write_text(''.join(f"file '{f}'\n" for f in files))
    video=OUT/'short.mp4'
    cmd(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
         '-i',concat,'-c','copy','-movflags','+faststart',video],timeout=120)
    info=ffprobe(video)
    duration=float(info['format']['duration'])
    streams=info['streams']
    shape=next((s for s in streams if s['codec_type']=='video'),{})
    if not (20<=duration<=24) or shape.get('width')!=W or shape.get('height')!=H:
        raise RuntimeError(f'Failed QA: unexpected duration/resolution {duration:.3f}s {shape.get("width")}x{shape.get("height")}')
    if not any(s['codec_type']=='audio' for s in streams):raise RuntimeError('Failed QA: no audio')
    title,description=describe(data.get('theme',''),sources)
    manifest={'status':'rendered_not_published','topic':data['topic'],
              'theme':data.get('theme'), 'duration_seconds':round(duration,2),
              'width':W,'height':H,'title':title,'description':description,
              'rights_warning':data.get('license_warning',''),
              'sources':[{k:v for k,v in s.items() if k not in {'local_file'}} for s in sources]}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    cmd(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','9.2','-i',video,'-frames:v','1',OUT/'preview.jpg'])
    print('DONE',str(video),duration,title,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('RESH RANKS RENDER ERROR:',type(exc).__name__,exc,file=sys.stderr)
        raise