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
    "girlfriend": ("en-US-JennyNeural", "+5%", "+8Hz"),
    "boyfriend": ("en-US-EricNeural", "-3%", "-2Hz"),
    "mother": ("en-US-AriaNeural", "-6%", "-4Hz"),
    "father": ("en-US-ChristopherNeural", "-8%", "-8Hz"),
    "grandpa": ("en-US-ChristopherNeural", "-18%", "-18Hz"),
    "grandma": ("en-US-AriaNeural", "-15%", "-12Hz"),
    "uncle": ("en-US-ChristopherNeural", "-12%", "-13Hz"),
    "aunt": ("en-US-AriaNeural", "-9%", "-7Hz"),
    "friend": ("en-US-DavisNeural", "+3%", "+2Hz"),
    "sister": ("en-US-JennyNeural", "+4%", "+8Hz"),
    "brother": ("en-US-EricNeural", "+2%", "+3Hz"),
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

font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F = {
    "text": ImageFont.truetype(font_regular, 28),
    "name": ImageFont.truetype(font_bold, 23),
    "head": ImageFont.truetype(font_bold, 31),
    "tiny": ImageFont.truetype(font_regular, 20),
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
        master += sound + AudioSegment.silent(duration=220)
    master += AudioSegment.silent(duration=750)
    wav = OUT / "audio.wav"
    master.export(str(wav), format="wav")
    return wav, start_times, len(master) / 1000.0

def draw_frame(t, start_times):
    image = BASE.copy()
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((0, 0, W, 116), radius=0, fill=(23, 40, 49))
    d.ellipse((28, 25, 90, 87), fill=(35, 133, 121))
    d.text((48, 31), "C", font=F["head"], fill="white")
    theme = story.get("chatTitle", "Chat")
    d.text((110, 26), str(theme)[:28], font=F["head"], fill="#ecf1f3")
    d.text((112, 74), "fictional chat  •  voice acted" if LANG == "en" else
           "kurgu sohbet  •  seslendirmeli", font=F["tiny"], fill="#91b1b1")

    # The initial frame doubles as an optional high-contrast Shorts preview.
    # This is NOT a YouTube custom thumbnail: YouTube picks its own preview.
    cover_text = str(story.get("coverText", "")).strip().upper()[:40]
    if cover_text and t < 1.45:
        accent = (251, 191, 36) if LANG == "en" else (45, 212, 191)
        panel = (246, 248, 249)
        d.rounded_rectangle((30, 152, 690, 330), radius=24,
                            fill=(22, 31, 42), outline=accent, width=5)
        d.rounded_rectangle((48, 170, 58, 305), radius=5, fill=accent)
        cover_font = F["cover"]
        chunks = safe_wrap(d, cover_text, cover_font, 575)
        if len(chunks) > 2:
            cover_font = F["cover_small"]
            chunks = safe_wrap(d, cover_text, cover_font, 575)
        # Maximum two lines and no tiny/unreadable captions.
        chunks = chunks[:2]
        block = len(chunks) * 54
        y = 241 - block // 2
        for line in chunks:
            box = d.textbbox((0, 0), line, font=cover_font)
            tw = box[2] - box[0]
            d.text(((W - tw) // 2, y), line, font=cover_font, fill=panel)
            y += 54

    visible = [i for i, val in enumerate(start_times) if val <= t]
    drawables = []
    # Layout only the last six visible bubbles; avoids overflow and simulates scrolling.
    for idx in visible[-7:]:
        msg = lines[idx]
        text_lines = safe_wrap(d, msg["text"], F["text"], 482)
        height = 44 + len(text_lines) * 37 + 24
        drawables.append((idx, msg, text_lines, height))
    total_height = sum(v[3] + 16 for v in drawables)
    ypos = max(150, min(1090 - total_height, 375))

    for idx, msg, wrapped, height in drawables:
        own = msg["speaker"] == "me"
        left, right = ((143, 692) if own else (28, 577))
        # Slide from 15px off-screen during the first 0.2s of each message.
        anim = max(0.0, min(1.0, (t - start_times[idx]) / 0.20))
        slide = round((1.0 - (1 - anim)**2) * 20)
        shift = (20 - slide) if own else (slide - 20)
        left += shift
        right += shift
        color = (20, 89, 77) if own else (37, 52, 63)
        d.rounded_rectangle((left, ypos, right, ypos + height),
                            radius=22, fill=color)
        d.text((left + 16, ypos + 11), DISPLAY[msg["speaker"]],
               font=F["name"], fill=(151, 241, 188) if own else (110, 204, 250))
        ty = ypos + 45
        for line in wrapped:
            d.text((left + 16, ty), line, font=F["text"], fill="#f8f8f8")
            ty += 37
        ypos += height + 16

    d.rounded_rectangle((14, 1190, 706, 1255), radius=28, fill=(30, 49, 60))
    d.text((34, 1206), "Type a message..." if LANG == "en" else "Bir mesaj yaz...",
           font=F["text"], fill="#748d97")
    # Progress bar shows the duration clearly during playback.
    progress = min(t / max(start_times[-1] + 1.0, t + .000001), 1.0)
    d.rounded_rectangle((0, 1272, int(W * progress), H), radius=0,
                        fill=(39, 179, 144))
    return image

def encode(wav, starts, duration):
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

def fit_short_duration(wav, start_times, seconds, target_seconds=48.0):
    """Keep every spoken message while gently accelerating overlong Shorts.

    ffmpeg's atempo changes duration without shifting voice pitch. Bubble
    reveal times are scaled to stay in sync with the accelerated narration.
    """
    if seconds <= target_seconds:
        return wav, start_times, seconds
    speed = seconds / target_seconds
    if speed > 2.0:
        raise ValueError(
            f"Dialogue narration {seconds:.1f}s needs over 2x speed. "
            "Generate a much shorter dialogue instead."
        )
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
        f"Duration adjusted: {seconds:.1f}s -> {fitted_seconds:.1f}s "
        f"(tempo {speed:.2f}x)"
    )
    return faster_wav, fitted_starts, fitted_seconds


def main():
    paths = asyncio.run(synthesize())
    wav, times, length = build_audio(paths)
    wav, times, length = fit_short_duration(wav, times, length)
    encode(wav, times, length)

if __name__ == "__main__":
    main()
