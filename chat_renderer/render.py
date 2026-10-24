#!/usr/bin/env python3
"""Generate an original portrait fictional-chat short with per-character TTS.

Usage: set CHAT_JSON and CHAT_LANG=en|tr environment variables, run:
    python chat_renderer/render.py

The speech backend is unofficial edge-tts, whose availability and downstream
content/licensing conditions must be checked separately before commercial use.
"""
import asyncio
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

import edge_tts
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment

W, H, FPS = 720, 1280, 20
OUT = Path("out")
OUT.mkdir(exist_ok=True)
TMP = OUT / "tts"
TMP.mkdir(exist_ok=True)

LANG = os.environ.get("CHAT_LANG", "en").strip().lower()
if LANG not in ("en", "tr"):
    raise ValueError("CHAT_LANG must be en or tr")
story = json.loads(os.environ["CHAT_JSON"])
lines = story.get("dialogue", [])
if not isinstance(lines, list) or not (9 <= len(lines) <= 16):
    raise ValueError("Expected 9 to 16 chat messages")
allowed = {"me", "girlfriend", "boyfriend", "mother", "father", "grandpa",
           "grandma", "uncle", "aunt", "friend", "sister", "brother"}
for line in lines:
    if line.get("speaker") not in allowed:
        raise ValueError(f"Unrecognized speaker: {line.get('speaker')}")
    if not isinstance(line.get("text"), str) or not (1 <= len(line["text"]) <= 180):
        raise ValueError("Message text must be 1-180 characters")
if len({m["speaker"] for m in lines}) > 3:
    raise ValueError("At most 3 voices per story")

EN_VOICES = {
    "me": ("en-US-GuyNeural", "+0%", "+0Hz"),
    "girlfriend": ("en-US-JennyNeural", "+0%", "+0Hz"),
    "boyfriend": ("en-US-EricNeural", "+0%", "+0Hz"),
    "mother": ("en-US-AriaNeural", "-1%", "+0Hz"),
    "father": ("en-US-ChristopherNeural", "+0%", "+0Hz"),
    "grandpa": ("en-US-ChristopherNeural", "-5%", "-2Hz"),
    "grandma": ("en-US-AriaNeural", "-3%", "-1Hz"),
    "uncle": ("en-US-ChristopherNeural", "+0%", "+0Hz"),
    "aunt": ("en-US-AriaNeural", "+0%", "+0Hz"),
    "friend": ("en-US-DavisNeural", "+0%", "+0Hz"),
    "sister": ("en-US-JennyNeural", "+0%", "+0Hz"),
    "brother": ("en-US-EricNeural", "+0%", "+0Hz"),
}
TR_VOICES = {
    "me": ("tr-TR-AhmetNeural", "+0%", "+0Hz"),
    "girlfriend": ("tr-TR-EmelNeural", "+5%", "+8Hz"),
    "boyfriend": ("tr-TR-AhmetNeural", "-3%", "-3Hz"),
    "mother": ("tr-TR-EmelNeural", "-10%", "-8Hz"),
    "father": ("tr-TR-AhmetNeural", "-10%", "-9Hz"),
    "grandpa": ("tr-TR-AhmetNeural", "-18%", "-20Hz"),
    "grandma": ("tr-TR-EmelNeural", "-16%", "-16Hz"),
    "uncle": ("tr-TR-AhmetNeural", "-14%", "-14Hz"),
    "aunt": ("tr-TR-EmelNeural", "-10%", "-10Hz"),
    "friend": ("tr-TR-AhmetNeural", "+6%", "+3Hz"),
    "sister": ("tr-TR-EmelNeural", "+7%", "+9Hz"),
    "brother": ("tr-TR-AhmetNeural", "+4%", "+4Hz"),
}
VOICES = EN_VOICES if LANG == "en" else TR_VOICES
DISPLAY = {
    "en": {"me": "You", "girlfriend": "Babe", "boyfriend": "Babe",
           "mother": "Mom", "father": "Dad", "grandpa": "Grandpa",
           "grandma": "Grandma", "uncle": "Uncle", "aunt": "Aunt",
           "friend": "Bestie", "sister": "Sis", "brother": "Bro"},
    "tr": {"me": "Sen", "girlfriend": "Aşkım", "boyfriend": "Aşkım",
           "mother": "Annem", "father": "Babam", "grandpa": "Dedem",
           "grandma": "Ninem", "uncle": "Amcam", "aunt": "Teyzem",
           "friend": "Kankam", "sister": "Ablam", "brother": "Abim"},
}[LANG]


# Contacts are based on the ACTUAL speakers, not an AI-generated headline.
# The same name is used in the fixed top bar and in the incoming bubbles.
CONTACTS_EN = {
    "girlfriend": ("Sophie", "Girlfriend"),
    "boyfriend": ("Ryan", "Boyfriend"),
    "mother": ("Mom", "Mother"),
    "father": ("Dad", "Father"),
    "grandpa": ("Grandpa", "Grandfather"),
    "grandma": ("Grandma", "Grandmother"),
    "uncle": ("Uncle Mike", "Uncle"),
    "aunt": ("Aunt Lisa", "Aunt"),
    "friend": ("Alex", "Best friend"),
    "sister": ("Mia", "Sister"),
    "brother": ("Jake", "Brother"),
}
CONTACTS_TR = {
    "girlfriend": ("Zeynep", "Sevgilin"),
    "boyfriend": ("Emir", "Sevgilin"),
    "mother": ("Annem", "Anne"),
    "father": ("Babam", "Baba"),
    "grandpa": ("Dedem", "Dede"),
    "grandma": ("Ninem", "Nine"),
    "uncle": ("Amcam", "Amca"),
    "aunt": ("Teyzem", "Teyze"),
    "friend": ("Ege", "Arkadaşın"),
    "sister": ("Elif", "Kardeşin"),
    "brother": ("Mert", "Kardeşin"),
}
CONTACTS = CONTACTS_EN if LANG == "en" else CONTACTS_TR
OTHER_SPEAKERS = [m["speaker"] for m in lines if m["speaker"] != "me"]
PEER = OTHER_SPEAKERS[0] if OTHER_SPEAKERS else "friend"
CONTACT_NAME, CONTACT_ROLE = CONTACTS.get(PEER, ("Alex", "Friend"))
CONTACT_NAME_BY_ROLE = {role: data[0] for role, data in CONTACTS.items()}

font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F = {
    "text": ImageFont.truetype(font_regular, 30),
    "name": ImageFont.truetype(font_bold, 23),
    "head": ImageFont.truetype(font_bold, 36),
    "tiny": ImageFont.truetype(font_regular, 22),
    "badge": ImageFont.truetype(font_bold, 22),
    "cover": ImageFont.truetype(font_bold, 47),
    "cover_small": ImageFont.truetype(font_bold, 39),
}

async def generate_voice(index, msg):
    voice, rate, pitch = VOICES[msg["speaker"]]
    output = TMP / f"{index:03d}.mp3"
    last_exc = None
    for attempt in range(3):
        try:
            await edge_tts.Communicate(
                msg["text"], voice=voice, rate=rate, pitch=pitch
            ).save(str(output))
            if output.stat().st_size < 1000:
                raise RuntimeError("Audio returned empty")
            return output
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep((attempt + 1) * 3)
    raise RuntimeError(f"TTS failed at line {index}: {last_exc}")

async def synthesize():
    paths = []
    # Deliberately sequential to avoid many simultaneous TTS connections.
    for index, msg in enumerate(lines):
        paths.append(await generate_voice(index, msg))
    return paths

def safe_wrap(draw, text, font, width):
    words = text.split()
    output, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if current and draw.textbbox((0, 0), trial, font=font)[2] > width:
            output.append(current)
            current = word
        else:
            current = trial
    if current:
        output.append(current)
    if not output:
        output = ["..."]
    return output

def gradient_background():
    im = Image.new("RGB", (W, H), "#0b141a")
    dr = ImageDraw.Draw(im)
    for yy in range(H):
        mix = yy / H
        dr.line((0, yy, W, yy),
                fill=(int(11 + 7 * mix), int(20 + 8 * mix), int(26 + 11 * mix)))
    # Subtle decorative dots, not another brand's exact UI.
    for yy in range(145, 1200, 95):
        for xx in range(45, 730, 130):
            dr.ellipse((xx, yy, xx + 3, yy + 3), fill=(28, 45, 54))
    return im

BASE = gradient_background()

def build_audio(paths):
    master = AudioSegment.silent(duration=180)
    start_times = []
    for path in paths:
        sound = AudioSegment.from_file(str(path)).set_channels(1).set_frame_rate(44100)
        start_times.append(len(master) / 1000.0)
        master += sound + AudioSegment.silent(duration=175)
    master += AudioSegment.silent(duration=750)
    wav = OUT / "audio.wav"
    master.export(str(wav), format="wav")
    return wav, start_times, len(master) / 1000.0

# Keep all text within the actual video-safe chat viewport.
CHAT_TOP, CHAT_BOTTOM = 177, 1023
CHAT_GAP = 14
CHAT_TEXT_WIDTH = 405
CHAT_LINE_HEIGHT = 39

def display_sender(role):
    if role == "me":
        return "You" if LANG == "en" else "Sen"
    return CONTACT_NAME_BY_ROLE.get(role, role.title())

def bubble_size(draw, msg):
    rows = safe_wrap(draw, msg["text"], F["text"], CHAT_TEXT_WIDTH)
    # Name on each incoming bubble lets the audience identify speakers fast.
    return rows, 64 + len(rows) * CHAT_LINE_HEIGHT + 12

def draw_frame(t, start_times):
    image = BASE.copy()
    d = ImageDraw.Draw(image)

    # Messenger-like pinned contact header; no vague AI-generated "Caught in 4K".
    d.rectangle((0, 0, W, 154), fill=(19, 32, 41))
    d.line((0, 153, W, 153), fill=(47, 71, 83), width=2)
    d.line([(27, 71), (13, 84), (27, 97)], fill=(204, 226, 234), width=5)
    d.ellipse((47, 36, 125, 114), fill=(54, 144, 136))
    initials = CONTACT_NAME[0].upper()
    d.text((86, 75), initials, font=F["head"], anchor="mm", fill="white")
    # Long contact names are kept within the title bar.
    name = CONTACT_NAME[:16]
    d.text((143, 39), name, font=F["head"], fill=(248, 252, 253))
    status = (CONTACT_ROLE + "  ·  online") if LANG == "en" else (CONTACT_ROLE + "  ·  çevrimiçi")
    d.text((145, 94), status, font=F["tiny"], fill=(125, 208, 188))
    # Small menu dots rather than a huge headline obscuring the story.
    for y in (59, 76, 93):
        d.ellipse((677, y, 683, y + 6), fill=(177, 204, 211))

    # Paint bubbles to a separate transparent layer, then clip it exactly.
    # This avoids text spilling into the header and disappearing under the
    # YouTube Shorts controls when later messages arrive.
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    visible = [i for i, start in enumerate(start_times) if start <= t]
    if visible:
        entries = []
        for i in visible:
            rows, height = bubble_size(ld, lines[i])
            entries.append((i, lines[i], rows, height))
        heights = [entry[3] + CHAT_GAP for entry in entries]
        full_height = sum(heights)
        viewport_height = CHAT_BOTTOM - CHAT_TOP - 22
        # Show the newest full bubble by scrolling older ones UP. Ease the
        # scroll over 260 ms so there is no sudden empty screen.
        last_start = start_times[visible[-1]]
        amount = max(0.0, min(1.0, (t - last_start) / 0.26))
        easing = 1 - (1 - amount) ** 3
        prev_total = full_height - heights[-1]
        prev_scroll = max(0, prev_total - viewport_height)
        next_scroll = max(0, full_height - viewport_height)
        scroll = prev_scroll + (next_scroll - prev_scroll) * easing
        y = CHAT_TOP + 14 - round(scroll)
        for index, msg, rows, height in entries:
            # Entirely offscreen bubbles do not need drawing.
            if y + height < CHAT_TOP or y > CHAT_BOTTOM:
                y += height + CHAT_GAP
                continue
            own = msg["speaker"] == "me"
            left, right = (102, 618) if own else (30, 546)
            # Chat bubbles briefly slide in, then remain fully stable.
            reveal = max(0.0, min(1.0, (t - start_times[index]) / 0.22))
            shift = round((1 - reveal) * (16 if own else -16))
            x0, x1 = left + shift, right + shift
            bg = (24, 94, 78, 255) if own else (43, 59, 70, 255)
            fg = (179, 249, 209, 255) if own else (144, 208, 250, 255)
            ld.rounded_rectangle((x0, y, x1, y + height), radius=21, fill=bg)
            ld.text((x0 + 19, y + 11), display_sender(msg["speaker"]), font=F["name"], fill=fg)
            baseline = y + 44
            for row in rows:
                ld.text((x0 + 19, baseline), row, font=F["text"], fill=(252, 252, 252, 255))
                baseline += CHAT_LINE_HEIGHT
            y += height + CHAT_GAP
    viewport = layer.crop((0, CHAT_TOP, W, CHAT_BOTTOM))
    image.paste(viewport, (0, CHAT_TOP), viewport)

    # A fixed input area conveys the phone-chat context without hiding text.
    d.rounded_rectangle((27, 1045, 629, 1111), radius=29,
                        fill=(29, 48, 57), outline=(61, 82, 90), width=2)
    placeholder = "Message..." if LANG == "en" else "Mesaj..."
    d.text((49, 1060), placeholder, font=F["text"], fill=(137, 160, 170))
    d.ellipse((649, 1055, 700, 1107), fill=(42, 162, 133))
    d.polygon([(663, 1081), (685, 1069), (679, 1095)], fill="white")
    # Reserve the last 150 pixels for Shorts overlay, title and channel name.
    d.line((0, 1138, W, 1138), fill=(44, 73, 79), width=2)
    total = max(VIDEO_DURATION, 0.001)
    progress = max(0.0, min(1.0, t / total))
    d.rectangle((0, 1141, max(1, round(W * progress)), 1148),
                fill=(45, 212, 174))
    return image

VIDEO_DURATION = 55.0

def encode(wav, starts, duration):
    global VIDEO_DURATION
    VIDEO_DURATION = duration
    target = OUT / "short.mp4"
    proc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "pipe:0",
        "-i", str(wav),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", "-shortest", str(target)
    ], stdin=subprocess.PIPE)
    frames = math.ceil(duration * FPS)
    try:
        for j in range(frames):
            frame = draw_frame(j / FPS, starts)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        returncode = proc.wait(timeout=300)
    except Exception:
        proc.kill()
        raise
    if returncode != 0 or not target.exists() or target.stat().st_size < 50_000:
        raise RuntimeError("ffmpeg did not produce a valid MP4")
    print(json.dumps({
        "file": str(target), "seconds": round(duration, 2), "bytes": target.stat().st_size,
        "language": LANG, "messages": len(lines)
    }, ensure_ascii=False))

def fit_short_duration(wav, start_times, seconds, target_seconds=55.0):
    """Prefer natural voices over squeezing long scripts into 48 seconds.

    A gentle <=8% tempo correction is acceptable. Longer scripts are kept
    at their natural length instead of speeding voices up by 30-80%.
    """
    if seconds <= target_seconds:
        return wav, start_times, seconds
    speed = min(seconds / target_seconds, 1.08)
    if speed < 1.015:
        return wav, start_times, seconds
    faster_wav = OUT / "audio_fitted.wav"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(wav), "-filter:a", f"atempo={speed:.6f}",
        str(faster_wav)
    ], check=True)
    fitted_seconds = AudioSegment.from_file(str(faster_wav)).duration_seconds
    factor = fitted_seconds / seconds
    fitted_starts = [round(start * factor, 5) for start in start_times]
    print(
        f"Natural tempo maintained: {seconds:.1f}s -> {fitted_seconds:.1f}s "
        f"({speed:.2f}x)"
    )
    return faster_wav, fitted_starts, fitted_seconds


def main():
    paths = asyncio.run(synthesize())
    wav, times, length = build_audio(paths)
    wav, times, length = fit_short_duration(wav, times, length)
    encode(wav, times, length)

if __name__ == "__main__":
    main()
