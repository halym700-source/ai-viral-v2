"""TextVibeStories pastel chat renderer. Original vector avatars, role-linked."""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
PAGE=(245,239,228)
CREAM=(249,245,238)
INK=(40,44,44)
SPECS={
 'me':('male',(69,43,32),(217,169,128),(253,249,240)),
 'girlfriend':('female',(86,53,39),(235,185,148),(251,249,243)),
 'boyfriend':('male',(91,55,37),(225,173,134),(230,237,248)),
 'mother':('female',(93,61,47),(225,172,133),(221,232,214)),
 'father':('male',(94,73,64),(215,157,117),(220,234,239)),
 'grandma':('female',(172,166,154),(228,181,146),(229,221,234)),
 'grandpa':('male',(174,168,155),(221,169,129),(231,233,222)),
 'daughter':('female',(110,74,53),(235,178,139),(244,225,226)),
 'son':('male',(69,49,39),(224,173,135),(229,237,245)),
 'uncle':('male',(78,66,49),(207,156,120),(215,235,216)),
 'aunt':('female',(113,65,48),(231,178,144),(242,230,220)),
 'friend':('female',(92,57,43),(219,157,123),(240,226,211)),
 'sister':('female',(77,49,40),(238,184,148),(245,230,235)),
 'brother':('male',(64,50,42),(222,164,120),(231,230,246))
}
SPECS['maternal_grandma']=SPECS['grandma']
SPECS['paternal_grandma']=SPECS['grandma']
def lighter(c,n):return tuple(min(255,x+n) for x in c)
def darker(c,n):return tuple(max(0,x-n) for x in c)
@lru_cache(maxsize=32)
def portrait(role,size=174):
    gender,hair,skin,shirt=SPECS.get(role,SPECS['friend'])
    older=role in ('mother','father','grandma','grandpa','maternal_grandma','paternal_grandma','uncle','aunt')
    elderly=role in ('grandma','grandpa','maternal_grandma','paternal_grandma')
    beard=gender=='male' and role not in ('son',)
    s=3
    im=Image.new('RGBA',(630,630),(0,0,0,0))
    d=ImageDraw.Draw(im)
    def ell(b,fill):
        d.ellipse(tuple(int(x*s) for x in b),fill=fill)
    def rect(b,fill,r=0):
        d.rounded_rectangle(tuple(int(x*s) for x in b),radius=r*s,fill=fill)
    def line(points,fill,w=2):
        d.line([(int(x*s),int(y*s)) for x,y in points],fill=fill,width=w*s,joint='curve')
    ell((8,8,202,202),(239,236,228,255))
    ell((35,24,179,184),(232,229,220,255))
    if gender=='female':
        ell((44,28,165,194),hair)
        ell((37,64,79,177),hair)
        ell((131,63,173,185),hair)
    else: ell((51,29,160,136),hair)
    ell((14,151,196,280),shirt)
    ell((28,161,181,259),lighter(shirt,2))
    rect((84,127,126,176),skin,12)
    ell((56,41,156,158),skin)
    ell((49,99,68,119),skin)
    ell((147,99,163,119),skin)
    ell((70,105,90,118),lighter(skin,10))
    ell((123,105,143,118),lighter(skin,11))
    ell((100,103,113,133),darker(skin,7))
    ell((101,101,112,125),skin)
    line([(72,94),(88,91),(95,94)],darker(hair,17),3)
    line([(118,94),(135,91),(145,94)],darker(hair,17),3)
    ell((76,99,92,110),(254,251,245))
    ell((123,99,139,110),(254,251,245))
    ell((83,99,90,109),(58,48,43))
    ell((127,99,134,109),(58,48,43))
    ell((85,101,87,104),(255,255,255))
    ell((129,101,131,104),(255,255,255))
    if beard:
        ell((76,122,142,160),darker(hair,10))
        ell((82,115,136,146),skin)
        line([(88,123),(101,126),(119,126),(133,121)],darker(hair,12),3)
        ell((101,146,117,154),darker(hair,12))
    d.arc((276,381,381,432),5,165,fill=(120,71,66),width=9)
    if older:
        line([(72,116),(77,119)],darker(skin,25),1)
        line([(137,116),(142,119)],darker(skin,25),1)
    if elderly:
        line([(80,76),(96,72)],darker(skin,21),1)
        line([(120,72),(135,76)],darker(skin,21),1)
    if role=='me':
        for x,y,r in [(60,53,19),(78,42,18),(96,36,21),(116,36,20),
                      (137,43,18),(149,59,15),(62,70,13)]:
            ell((x-r,y-r,x+r,y+r),hair)
        for x,y in [(72,38),(102,25),(131,37),(142,53)]:
            d.arc((x*s,y*s,(x+22)*s,(y+17)*s),180,330,
                  fill=lighter(hair,24),width=3*s)
    elif gender=='female':
        ell((51,35,164,90),hair)
        ell((51,39,92,102),hair)
        ell((134,39,164,110),hair)
        for x,y in [(44,98),(43,124),(47,149),(159,98),(163,126),(158,151)]:
            ell((x-11,y-16,x+13,y+17),hair)
        d.arc((210,114,432,243),160,305,fill=lighter(hair,26),width=9)
    else:
        for x,y,r in [(63,56,19),(85,41,20),(110,36,21),(136,44,19),(150,58,15)]:
            ell((x-r,y-r,x+r,y+r),hair)
        if elderly: line([(63,57),(80,44),(106,39),(130,45)],lighter(hair,20),4)
    im=im.resize((size,size),Image.Resampling.LANCZOS)
    return im
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
    if (width,height)!=(720,1280):
        raise ValueError('Pastel template requires 720x1280')
    im=Image.new('RGB',(width,height),(0,0,0))
    d=ImageDraw.Draw(im)
    d.rectangle((0,108,720,1162),fill=PAGE)
    d.rounded_rectangle((20,131,700,1135),radius=36,fill=CREAM,
                        outline=(227,219,205),width=2)
    d.line([(57,247),(683,247)],fill=(221,215,206),width=2)
    d.line([(66,197),(53,209),(66,221)],fill=INK,width=5,joint='curve')
    bubble_font,title_font=fonts()
    title=str(contact_name)[:24]
    tw=d.textbbox((0,0),title,font=title_font)[2]
    d.text(((720-tw)//2,188),title,font=title_font,fill=INK)
    d.ellipse((571,195,589,213),outline=INK,width=3)
    d.ellipse((577,201,583,207),fill=INK)
    d.arc((626,195,655,215),190,350,fill=INK,width=5)
    d.rounded_rectangle((629,201,654,212),radius=3,fill=INK)
    d.ellipse((635,203,648,215),fill=CREAM)
    avatar=portrait(peer,174)
    im.paste(avatar,(42,261),avatar)
    main_avatar=portrait('me',174)
    im.paste(main_avatar,(504,929),main_avatar)
    layer=Image.new('RGBA',(720,1280),(0,0,0,0))
    ld=ImageDraw.Draw(layer)
    entries=[]
    for i,msg in enumerate(lines):
        rows=wrap(ld,msg['text'],bubble_font)
        height=38+len(rows)*36
        entries.append((i,msg,rows,height))
    top,bottom=445,922
    visible=[i for i,start in enumerate(starts) if start<=t]
    if visible:
        block=entries[:visible[-1]+1]
        total=sum(e[3]+11 for e in block)
        previous=sum(e[3]+11 for e in block[:-1])
        fraction=min(1,max(0,(t-starts[visible[-1]])/.32))
        easing=1-(1-fraction)**3
        scroll_before=max(0,previous-(bottom-top-6))
        scroll_after=max(0,total-(bottom-top-6))
        y=top+5-round(scroll_before+(scroll_after-scroll_before)*easing)
        for i,msg,rows,bh in block:
            if y+bh<top or y>bottom:
                y+=bh+11;continue
            own=msg['speaker']=='me'
            line_width=max(ld.textbbox((0,0),row,font=bubble_font)[2] for row in rows)
            bw=max(165,min(455,line_width+49))
            x=(720-45-bw) if own else 42
            motion=max(0,1-(t-starts[i])/.20)
            x+=round((12 if own else -12)*motion)
            color=(218,240,215,255) if own else (253,254,254,255)
            border=(209,232,204,255) if own else (229,228,222,255)
            ld.rounded_rectangle((x,y,x+bw,y+bh),radius=25,fill=color,outline=border,width=1)
            for ri,row in enumerate(rows):
                ld.text((x+23,y+18+ri*36),row,font=bubble_font,fill=INK)
            y+=bh+11
    view=layer.crop((28,top,692,bottom))
    im.paste(view,(28,top),view)
    d=ImageDraw.Draw(im)
    d.rectangle((28,top,692,top+5),fill=CREAM)
    return im
