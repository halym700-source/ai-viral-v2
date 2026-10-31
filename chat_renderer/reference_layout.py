"""TextVibeStories reference-style 9:16 conversation renderer.

The two base character portraits are taken from the user's own design.
The right-bottom character never changes. Other contacts are visual
variations that follow their role; no stock photographs are fetched.
"""
import base64
import io
import json
from pathlib import Path
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

W,H = 720,1280
BLACK=(0,0,0)
PAGE=(245,239,227)
CREAM=(248,244,234)
TEXT=(42,44,43)
INCOMING=(252,254,254,255)
OUTGOING=(220,241,218,255)
ASSET_FILE=Path(__file__).resolve().parent/'reference_assets.json'

@lru_cache(maxsize=1)
def assets():
    if not ASSET_FILE.is_file():
        raise RuntimeError('Reference portraits missing: reference_assets.json')
    with ASSET_FILE.open(encoding='utf8') as fp:
        raw=json.load(fp)
    return {key:Image.open(io.BytesIO(base64.b64decode(value))).convert('RGBA')
            for key,value in raw.items()}

FEMALE={'girlfriend','mother','grandma','maternal_grandma','paternal_grandma',
        'daughter','aunt','sister'}
ELDERLY={'grandma','grandpa','maternal_grandma','paternal_grandma'}
MIDDLE_AGE={'mother','father','uncle','aunt'}

def hair_variant(image,role):
    """Add age/style changes only to the peer; never touch the main character."""
    if role in ('girlfriend','me'):
        return image
    img=image.convert('RGB')
    data=np.asarray(img,dtype=np.float32).copy()
    h,w=data.shape[:2]
    yy,xx=np.mgrid[:h,:w]
    lum=data.mean(axis=2)
    dark=np.clip((123-lum)/62,0,1)
    top=np.clip((h*.69-yy)/(h*.27),0,1)
    region=(xx>w*.12)&(xx<w*.95)
    mask=(dark**1.5)*top*region
    colors={
        'mother':((113,82,68),.29), 'father':((133,130,126),.47),
        'sister':((132,67,49),.54), 'brother':((85,64,48),.43),
        'aunt':((91,57,42),.5), 'uncle':((130,112,91),.48),
        'grandma':((180,172,164),.65), 'grandpa':((176,174,171),.65),
        'maternal_grandma':((181,174,169),.68),
        'paternal_grandma':((157,160,155),.68),
        'daughter':((136,78,54),.42), 'son':((89,67,52),.4),
        'boyfriend':((77,62,53),.38), 'friend':((119,83,64),.50),
    }
    color,strength=colors.get(role,((115,80,60),.5))
    a=(mask*strength)[:,:,None]
    data=data*(1-a)+np.array(color)[None,None,:]*a
    img=Image.fromarray(np.uint8(np.clip(data,0,255)),'RGB').convert('RGBA')
    if role in MIDDLE_AGE or role in ELDERLY:
        d=ImageDraw.Draw(img,'RGBA')
        if role in ('mother','grandma','maternal_grandma','paternal_grandma','grandpa'):
            y=int(h*(.40 if role in FEMALE else .43))
            x0=int(w*.20);x1=int(w*.45);x2=int(w*.50);x3=int(w*.75)
            c=(75,62,54,165) if role!='grandpa' else (82,84,86,185)
            d.rounded_rectangle((x0,y,x1,y+int(h*.13)),radius=5,outline=c,width=2)
            d.rounded_rectangle((x2,y,x3,y+int(h*.13)),radius=5,outline=c,width=2)
            d.line([(x1,y+4),(x2,y+4)],fill=c,width=2)
        if role in ELDERLY:
            face=(128,99,79,50)
            d.arc((int(w*.32),int(h*.59),int(w*.42),int(h*.61)),15,155,fill=face,width=2)
            d.arc((int(w*.57),int(h*.59),int(w*.67),int(h*.61)),15,160,fill=face,width=2)
    return img

def soft_mask(size):
    from PIL import ImageFilter
    w,h=size
    mask=Image.new('L',(w,h),0)
    d=ImageDraw.Draw(mask)
    d.rounded_rectangle((7,10,w-7,h-7),radius=46,fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=11))

@lru_cache(maxsize=40)
def portrait(role,width=196,height=205):
    base=assets()['girlfriend' if role in FEMALE else 'me']
    if role not in ('me','girlfriend'):
        base=hair_variant(base,role)
        if role in ('sister','daughter','aunt','friend','brother','son'):
            base=ImageOps.mirror(base)
    base=ImageOps.fit(base,(width,height),centering=(.5,.45))
    base.putalpha(soft_mask(base.size))
    return base

@lru_cache(maxsize=1)
def fonts():
    f='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return (ImageFont.truetype(f,27),ImageFont.truetype(f,29))

def wrap(draw,text,font,max_width=420):
    lines=[];s=''
    for word in text.split():
        candidate=(s+' '+word).strip()
        if s and draw.textbbox((0,0),candidate,font=font)[2]>max_width:
            lines.append(s);s=word
        else:s=candidate
    if s:lines.append(s)
    return lines or ['…']

def render_frame(t,starts,lines,contact_name,peer,duration,width=720,height=1280):
    if (width,height)!=(W,H):
        raise ValueError('Reference layout designed for 720x1280 Shorts')
    image=Image.new('RGB',(W,H),BLACK)
    d=ImageDraw.Draw(image)
    d.rectangle((0,122,W,1161),fill=PAGE)
    d.rounded_rectangle((18,143,702,1138),radius=39,
                        fill=CREAM,outline=(229,221,207),width=2)
    d.line([(36,249),(685,249)],fill=(219,215,208),width=2)
    d.line([(63,194),(51,207),(63,219)],fill=TEXT,width=4,joint='curve')
    bubble_font,title_font=fonts()
    title=str(contact_name)[:22]
    tw=d.textbbox((0,0),title,font=title_font)[2]
    d.text(((720-tw)//2,186),title,fill=TEXT,font=title_font)
    d.ellipse((583,198,602,217),outline=TEXT,width=3)
    d.ellipse((588,203,598,213),fill=TEXT)
    d.arc((637,198,671,221),185,354,fill=TEXT,width=4)
    d.rounded_rectangle((639,204,669,214),radius=3,fill=TEXT)
    d.ellipse((646,207,658,218),fill=CREAM)
    left=portrait(peer,208,208)
    image.paste(left,(37,264),left)
    main=portrait('me',207,222)
    image.paste(main,(479,897),main)
    layer=Image.new('RGBA',(W,H),(0,0,0,0))
    ld=ImageDraw.Draw(layer)
    entries=[]
    for i,m in enumerate(lines):
        textrows=wrap(ld,m['text'],bubble_font,max_width=415)
        ht=35+35*len(textrows)
        entries.append((i,m,textrows,ht))
    first,last=467,902
    indices=[i for i,s in enumerate(starts) if s<=t]
    if indices:
        visible=entries[:indices[-1]+1]
        full=sum(e[3]+12 for e in visible)
        prev=sum(e[3]+12 for e in visible[:-1])
        elapsed=max(0,min(1,(t-starts[indices[-1]])/.33))
        scroll=max(0,prev-(last-first-10))
        future=max(0,full-(last-first-10))
        offset=scroll+(future-scroll)*(1-(1-elapsed)**3)
        ypos=first+7-round(offset)
        for i,m,rows,ht in visible:
            if ypos<first+8 or ypos+ht>last+85 or ypos>last:
                ypos+=ht+12;continue
            own=m['speaker']=='me'
            max_row=max(ld.textbbox((0,0),row,font=bubble_font)[2] for row in rows)
            bw=max(185,min(460,max_row+48))
            left_x=(674-bw) if own else 44
            ease=max(0,1-(t-starts[i])/.22)
            left_x+=round((12 if own else -12)*ease)
            bg=OUTGOING if own else INCOMING
            border=(214,236,211,255) if own else (233,232,225,255)
            ld.rounded_rectangle((left_x,ypos,left_x+bw,ypos+ht),radius=25,
                                 fill=bg,outline=border,width=1)
            for ri,row in enumerate(rows):
                ld.text((left_x+22,ypos+16+ri*35),row,font=bubble_font,fill=TEXT)
            ypos+=ht+12
    viewport=layer.crop((30,467,691,902))
    image.paste(viewport,(30,467),viewport)
    return image
