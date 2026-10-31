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
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

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

# Stable 22-year-old narrator: nobody else ever reuses his portrait.
FEMALE={'girlfriend','mother','grandma','maternal_grandma','paternal_grandma',
        'daughter','aunt','sister','younger_sister'}
FAMILY_ASSET_FILE=Path(__file__).resolve().parent/'family_face_sources.json'

@lru_cache(maxsize=1)
def family_assets():
    if not FAMILY_ASSET_FILE.is_file():
        raise RuntimeError('Missing independent family portraits')
    with FAMILY_ASSET_FILE.open(encoding='utf8') as fp:
        raw=json.load(fp)
    return {key:Image.open(io.BytesIO(base64.b64decode(value))).convert('RGBA')
            for key,value in raw.items()}

def recolor_hair(image,color,strength=.6):
    data=np.asarray(image.convert('RGB'),dtype=np.float32).copy()
    h,w=data.shape[:2]
    y,x=np.mgrid[:h,:w]
    dark=np.clip((155-data.mean(2))/95,0,1)
    top=np.clip((h*.63-y)/(h*.25),0,1)
    sides=np.clip((x-w*.07)/(w*.10),0,1)*np.clip((w*.95-x)/(w*.09),0,1)
    alpha=(dark**1.8*top*sides*strength)[:,:,None]
    data=data*(1-alpha)+np.asarray(color)[None,None,:]*alpha
    return Image.fromarray(np.uint8(data.clip(0,255))).convert('RGBA')

def identity_variant(im,role):
    if role in ('father','mother'):
        return im
    im=im.convert('RGBA')
    w,h=im.size
    if role in ('grandpa','grandma','maternal_grandma','paternal_grandma'):
        im=recolor_hair(im,(178,175,171),.82)
        d=ImageDraw.Draw(im,'RGBA'); y=int(h*.43); c=(65,63,59,185)
        for x1,x2 in [(.18,.43),(.51,.76)]:
            d.rounded_rectangle((int(w*x1),y,int(w*x2),y+int(h*.11)),
                                radius=4,outline=c,width=2)
        d.line([(int(w*.43),y+5),(int(w*.51),y+5)],fill=c,width=2)
        for x in (.31,.64):
            d.arc((int(w*(x-.07)),int(h*.59),int(w*(x+.07)),int(h*.67)),
                  10,165,fill=(96,77,65,90),width=2)
    elif role in ('sister','younger_sister','daughter'):
        im=ImageOps.mirror(recolor_hair(im,(94,48,54),.52))
        d=ImageDraw.Draw(im,'RGBA')
        d.arc((int(w*.20),int(h*.12),int(w*.77),int(h*.48)),
              195,327,fill=(125,61,74,235),width=4)
    elif role in ('brother','younger_brother','son'):
        im=ImageOps.mirror(recolor_hair(im,(52,43,38),.65))
        d=ImageDraw.Draw(im,'RGBA')
        d.pieslice((int(w*.11),int(h*.07),int(w*.87),int(h*.45)),
                   185,355,fill=(45,62,81,242))
        d.ellipse((int(w*.40),int(h*.26),int(w*.96),int(h*.35)),
                  fill=(40,56,74,240))
    elif role in ('older_brother','boyfriend'):
        im=ImageOps.mirror(recolor_hair(im,(65,51,41),.62))
        if role=='older_brother':
            d=ImageDraw.Draw(im,'RGBA'); y=int(h*.41)
            for x1,x2 in [(.18,.43),(.52,.77)]:
                d.rounded_rectangle((int(w*x1),y,int(w*x2),y+int(h*.11)),
                                    radius=4,outline=(46,48,53,205),width=2)
            d.line([(int(w*.43),y+6),(int(w*.52),y+6)],
                   fill=(46,48,53,205),width=2)
    elif role in ('aunt','friend'):
        im=ImageOps.mirror(recolor_hair(im,(90,64,49),.35))
    elif role=='uncle':
        im=recolor_hair(im,(117,100,88),.35)
    return im

def soft_mask(size):
    from PIL import ImageFilter
    w,h=size
    mask=Image.new('L',(w,h),0)
    d=ImageDraw.Draw(mask)
    d.rounded_rectangle((7,10,w-7,h-7),radius=46,fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=10))

@lru_cache(maxsize=120)
def portrait(role,width=196,height=205):
    if role=='me':
        base=assets()['me']
    elif role=='girlfriend':
        base=assets()['girlfriend']
    else:
        sources=family_assets()
        image_key={
            'father':'father','mother':'mother',
            'grandpa':'father_alt','grandma':'mother_alt',
            'maternal_grandma':'mother_alt','paternal_grandma':'mother_alt',
            'sister':'mother_alt','younger_sister':'mother_alt','daughter':'mother_alt',
            'brother':'father_alt','younger_brother':'father_alt','son':'father_alt',
            'older_brother':'father','boyfriend':'father_alt',
            'aunt':'mother','uncle':'father_alt','friend':'mother_alt'
        }.get(role,'mother_alt')
        base=identity_variant(sources[image_key],role)
    base=ImageOps.fit(base,(width,height),centering=(.5,.44))
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
    # Contact name moves beside its small profile photo in the top bar.
    d.text((174,185),title,fill=TEXT,font=title_font)
    d.ellipse((583,198,602,217),outline=TEXT,width=3)
    d.ellipse((588,203,598,213),fill=TEXT)
    d.arc((637,198,671,221),185,354,fill=TEXT,width=4)
    d.rounded_rectangle((639,204,669,214),radius=3,fill=TEXT)
    d.ellipse((646,207,658,218),fill=CREAM)
    # Only one large character remains: the original fixed 22-year-old narrator
    # at bottom LEFT. All other people appear only as circular contact photos.
    photo=portrait(peer,76,76)
    circle=Image.new('L',(76,76),0)
    ImageDraw.Draw(circle).ellipse((2,2,73,73),fill=255)
    # Combine circular crop with existing soft portrait transparency.
    from PIL import ImageChops
    photo.putalpha(ImageChops.multiply(photo.getchannel('A'),circle))
    image.paste(photo,(85,167),photo)
    d=ImageDraw.Draw(image)
    d.ellipse((85,167,160,242),outline=(224,218,209),width=2)
    main=portrait('me',207,222)
    image.paste(main,(35,897),main)

    layer=Image.new('RGBA',(W,H),(0,0,0,0))
    ld=ImageDraw.Draw(layer)
    entries=[]
    for i,m in enumerate(lines):
        textrows=wrap(ld,m['text'],bubble_font,max_width=415)
        ht=35+35*len(textrows)
        entries.append((i,m,textrows,ht))
    first,last=279,902
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
            if ypos+ht<first or ypos>last:
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
    viewport=layer.crop((30,279,691,902))
    image.paste(viewport,(30,279),viewport)
    return image
