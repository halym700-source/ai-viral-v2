import base64, io, json
from pathlib import Path
from PIL import ImageFilter, ImageOps
"""TextVibeStories pastel chat renderer. Original vector avatars, role-linked."""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
PAGE=(245,239,228)
CREAM=(249,245,238)
INK=(40,44,44)

ASSETS=Path(__file__).resolve().parent/'reference_assets.json'
FEMALE={'girlfriend','mother','grandma','maternal_grandma','paternal_grandma','daughter','aunt','sister'}
SENIOR={'grandma','grandpa','maternal_grandma','paternal_grandma'}
@lru_cache(maxsize=1)
def originals():
    if not ASSETS.is_file():
        raise RuntimeError("Reference character assets missing; refusing nonmatching video")
    data=json.loads(ASSETS.read_text(encoding='utf-8'))
    return {key:Image.open(io.BytesIO(base64.b64decode(raw))).convert('RGB')
            for key,raw in data.items()}

@lru_cache(maxsize=32)
def portrait(role,size=174):
    """The narrator is immutable. Role-specific contact keeps the same illustrated-photo style."""
    src=originals()['girlfriend' if role in FEMALE else 'me'].copy()
    if role not in ('girlfriend','me'):
        if role in ('sister','daughter','aunt','brother','son','friend'):
            src=ImageOps.mirror(src)
        tint={'father':((119,113,105),.22),'mother':((113,89,74),.16),
              'grandpa':((150,148,141),.36),'grandma':((157,151,140),.34),
              'maternal_grandma':((164,156,141),.32),
              'paternal_grandma':((145,144,140),.30),
              'sister':((143,80,61),.30),'brother':((108,81,61),.25),
              'aunt':((110,72,50),.23),'uncle':((123,108,92),.23),
              'daughter':((130,88,63),.18),'son':((95,76,62),.18),
              'boyfriend':((99,82,68),.20),'friend':((98,72,58),.25)}
        color,strength=tint.get(role,((107,81,67),.16))
        pixels=src.load()
        w,h=src.size
        for y in range(int(h*.1),int(h*.59)):
            height_weight=max(0,min(1,(.61*h-y)/(.23*h)))
            for x in range(int(w*.11),int(w*.94)):
                r,g,b=pixels[x,y]; brightness=(int(r)+int(g)+int(b))/3.
                # Restrict changes to darker hair, never recolor the bright face.
                alpha=max(0,min(1,(120-brightness)/75.)) * height_weight * strength
                if alpha>0:
                    pixels[x,y]=tuple(int(a*(1-alpha)+b*alpha) for a,b in zip((r,g,b),color))
        if role in SENIOR or role=='mother':
            d=ImageDraw.Draw(src)
            y=int(h*(.39 if role in FEMALE else .40))
            c=(92,82,76)
            for x in (int(w*.25),int(w*.53)):
                d.rounded_rectangle((x,y,x+int(w*.20),y+int(h*.09)),
                                    radius=4,outline=c,width=2)
            d.line((int(w*.45),y+4,int(w*.53),y+4),fill=c,width=2)
    src=ImageOps.fit(src,(size,size),centering=(.5,.45))
    mask=Image.new('L',(size,size),0)
    ImageDraw.Draw(mask).rounded_rectangle((7,8,size-7,size-6),radius=44,fill=255)
    src.putalpha(mask.filter(ImageFilter.GaussianBlur(9)))
    return src

@lru_cache(maxsize=1)
def fonts():
    f='/usr/share/fonts/truetype/dejavu/'
    return (ImageFont.truetype(f+'DejaVuSans.ttf',30),
            ImageFont.truetype(f+'DejaVuSans-Bold.ttf',29))
def wrap(draw,text,font,max_width=395):
    rows=[]
    current=''
    for word in text.split():
        proposed=(current+' '+word).strip()
        if current and draw.textbbox((0,0),proposed,font=font)[2]>max_width:
            rows.append(current);current=word
        else: current=proposed
    if current:rows.append(current)
    return rows or ['...']

def render_frame(t,starts,lines,contact_name,peer,duration,width=720,height=1280):
    """Exact cream/card/bubble placement based on the user's provided example."""
    if (width,height)!=(720,1280):
        raise ValueError('Reference template requires 720x1280')
    W,H=720,1280
    im=Image.new('RGB',(W,H),(0,0,0))
    d=ImageDraw.Draw(im)
    d.rectangle((0,122,720,1161),fill=(245,239,227))
    bg=(248,244,234)
    d.rounded_rectangle((18,143,702,1138),radius=39,fill=bg,
                        outline=(229,221,207),width=2)
    d.line((36,249,685,249),fill=(219,215,208),width=2)
    d.line([(63,194),(51,207),(63,219)],fill=INK,width=4,joint='curve')
    bubble_font,title_font=fonts()
    title=str(contact_name)[:22]
    tw=d.textbbox((0,0),title,font=title_font)[2]
    d.text(((720-tw)//2,186),title,font=title_font,fill=INK)
    d.ellipse((583,198,602,217),outline=INK,width=3)
    d.ellipse((588,203,598,213),fill=INK)
    d.arc((637,198,671,221),185,354,fill=INK,width=4)
    d.rounded_rectangle((639,204,669,214),radius=3,fill=INK)
    d.ellipse((646,207,658,218),fill=bg)
    contact=portrait(peer,208)
    im.paste(contact,(37,264),contact)
    me=portrait('me',207)
    im.paste(me,(485,899),me)
    layer=Image.new('RGBA',(W,H),(0,0,0,0))
    ld=ImageDraw.Draw(layer)
    entries=[]
    for i,m in enumerate(lines):
        rows=wrap(ld,m['text'],bubble_font,max_width=415)
        bh=35+35*len(rows)
        entries.append((i,m,rows,bh))
    top,bottom=467,902
    visible=[i for i,s in enumerate(starts) if s<=t]
    if visible:
        block=entries[:visible[-1]+1]
        full=sum(e[3]+12 for e in block)
        prev=sum(e[3]+12 for e in block[:-1])
        elapsed=max(0,min(1,(t-starts[visible[-1]])/.33))
        scroll=max(0,prev-(bottom-top-10))
        future=max(0,full-(bottom-top-10))
        y=top+7-round(scroll+(future-scroll)*(1-(1-elapsed)**3))
        for i,msg,rows,bh in block:
            if y+bh<top+25 or y>bottom:
                y+=bh+12
                continue
            own=msg['speaker']=='me'
            widest=max(ld.textbbox((0,0),row,font=bubble_font)[2] for row in rows)
            bw=max(185,min(460,widest+48))
            x=(674-bw) if own else 44
            x+=round((12 if own else -12)*max(0,1-(t-starts[i])/.22))
            color=(220,241,218,255) if own else (252,254,254,255)
            outline=(214,236,211,255) if own else (233,232,225,255)
            ld.rounded_rectangle((x,y,x+bw,y+bh),radius=25,fill=color,outline=outline,width=1)
            for j,row in enumerate(rows):
                ld.text((x+22,y+16+j*35),row,font=bubble_font,fill=INK)
            y+=bh+12
    view=layer.crop((30,467,691,902))
    im.paste(view,(30,467),view)
    return im
