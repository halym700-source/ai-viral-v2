"""Story-driven visual layout for TextVibeStories Shorts."""
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reference_layout import portrait
import hashlib

W, H = 720, 1280
THEMES = {
    "midnight": {"bg1": (13, 20, 38), "bg2": (29, 39, 67), "panel": (25, 34, 55), "incoming": (48, 61, 86), "outgoing": (52, 111, 104), "text": (246, 248, 255), "muted": (170, 184, 207), "accent": (91, 224, 190)},
    "neon": {"bg1": (17, 12, 35), "bg2": (48, 17, 64), "panel": (30, 21, 48), "incoming": (61, 44, 83), "outgoing": (106, 44, 101), "text": (255, 248, 255), "muted": (197, 169, 211), "accent": (255, 91, 190)},
    "sunset": {"bg1": (69, 36, 35), "bg2": (151, 75, 54), "panel": (250, 232, 211), "incoming": (255, 250, 239), "outgoing": (255, 214, 174), "text": (53, 39, 37), "muted": (124, 87, 72), "accent": (215, 104, 70)},
    "ice": {"bg1": (17, 48, 70), "bg2": (44, 105, 125), "panel": (232, 247, 250), "incoming": (255, 255, 255), "outgoing": (194, 235, 242), "text": (24, 48, 61), "muted": (85, 120, 135), "accent": (35, 162, 183)},
}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_BODY = ImageFont.truetype(FONT, 27)
F_NAME = ImageFont.truetype(BOLD, 20)
F_HOOK = ImageFont.truetype(BOLD, 42)
F_SMALL = ImageFont.truetype(BOLD, 18)
F_META = ImageFont.truetype(FONT, 17)

def pick_theme(theme, lines):
    if theme in THEMES:
        return theme
    seed = "|".join(m.get("text", "") for m in lines[:3])
    return list(THEMES)[int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(THEMES)]

def wrap(draw, text, font, max_width):
    rows, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
            rows.append(current)
            current = word
        else:
            current = trial
    if current:
        rows.append(current)
    return rows or ["…"]

def avatar(role, size=54):
    im = portrait(role, size, size).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, size-1, size-1), fill=255)
    im.putalpha(mask)
    return im

def render_frame(t, starts, lines, contact_name, peer, duration, hook_text="", theme=None, width=720, height=1280):
    if (width, height) != (W, H):
        raise ValueError("Story layout is designed for 720x1280 Shorts")
    theme_name = pick_theme(theme, lines)
    c = THEMES[theme_name]
    im = Image.new("RGB", (W, H), c["bg1"])
    px = im.load()
    for y in range(H):
        f = y / max(1, H-1)
        col = tuple(int(c["bg1"][i] * (1-f) + c["bg2"][i] * f) for i in range(3))
        for x in range(W):
            px[x, y] = col
    d = ImageDraw.Draw(im, "RGBA")
    # Abstract, story-specific energy shapes replace the old static wallpaper.
    d.ellipse((500, -170, 850, 180), fill=(*c["accent"], 35))
    d.ellipse((-180, 880, 180, 1240), fill=(*c["accent"], 25))
    d.rounded_rectangle((24, 30, 696, 1250), radius=42, fill=(*c["panel"], 248), outline=(*c["accent"], 110), width=2)

    d.rounded_rectangle((48, 55, 240, 91), radius=17, fill=(*c["accent"], 255))
    d.text((65, 63), "TEXTVIBE STORIES", font=F_SMALL, fill=c["bg1"] if theme_name != "sunset" else (255,255,255))
    d.text((50, 112), "PRIVATE CHAT", font=F_META, fill=c["muted"])
    d.text((50, 140), str(contact_name)[:24], font=F_HOOK if len(str(contact_name)) < 15 else F_NAME, fill=c["text"])
    d.ellipse((624, 116, 641, 133), fill=(*c["accent"], 255))
    d.text((650, 115), "LIVE", font=F_SMALL, fill=c["text"])

    # Opening hook dominates the first two seconds, then gives way to the chat.
    hook = (hook_text or (lines[0].get("text", "") if lines else "A message changed everything")).strip()
    hook_rows = wrap(d, hook.upper(), F_HOOK, 600)
    if t < 2.15:
        d.rounded_rectangle((48, 190, 672, 350), radius=28, fill=(*c["accent"], 255))
        yy = 218
        for row in hook_rows[:2]:
            d.text((72, yy), row, font=F_HOOK, fill=c["bg1"] if theme_name != "sunset" else (255,255,255))
            yy += 54
    else:
        d.text((50, 205), "THE CONVERSATION", font=F_SMALL, fill=c["accent"])

    # Chat viewport with avatars, sender labels, distinct bubble shapes and progress.
    top, bottom = (385 if t < 2.15 else 285), 1128
    d.rounded_rectangle((44, top, 676, bottom), radius=30, fill=(*c["bg1"], 105), outline=(*c["accent"], 55), width=1)
    active = [i for i, start in enumerate(starts) if start <= t]
    if active:
        last = active[-1]
        visible = []
        for i in range(last + 1):
            msg = lines[i]
            rows = wrap(d, msg["text"], F_BODY, 440)
            h = 34 + len(rows) * 35
            visible.append((i, msg, rows, h))
        total = sum(v[3] + 18 for v in visible)
        available = bottom - top - 28
        scroll = max(0, total - available)
        current_elapsed = max(0, min(1, (t - starts[last]) / .28))
        y = top + 16 - scroll + round((1-current_elapsed) * 14)
        for i, msg, rows, bh in visible:
            own = msg["speaker"] == "me"
            x1 = 166 if own else 112
            x2 = 650 if own else 594
            if y + bh < top or y > bottom:
                y += bh + 18
                continue
            role = "me" if own else msg["speaker"]
            av = avatar(role, 42)
            im.paste(av, (x1-52 if own else 54, y+4), av)
            d.rounded_rectangle((x1, y, x2, y+bh), radius=22, fill=(* (c["outgoing"] if own else c["incoming"]), 255))
            sender = "YOU" if own else str(contact_name).upper()[:20]
            d.text((x1+17, y+8), sender, font=F_NAME, fill=c["muted"] if theme_name in ("sunset","ice") else c["accent"])
            for ri, row in enumerate(rows):
                d.text((x1+17, y+34+ri*35), row, font=F_BODY, fill=c["text"])
            y += bh + 18
    # Progress line and final-message pulse.
    progress = min(1.0, max(0.0, t / max(duration, 0.1)))
    d.rounded_rectangle((50, 1170, 670, 1178), radius=4, fill=(*c["muted"], 70))
    d.rounded_rectangle((50, 1170, 50 + int(620*progress), 1178), radius=4, fill=(*c["accent"], 255))
    d.text((50, 1194), "WAIT FOR THE LAST MESSAGE", font=F_SMALL, fill=c["muted"])
    return im
