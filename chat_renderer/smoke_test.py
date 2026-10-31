#!/usr/bin/env python3
"""Offline smoke-test for the TextVibe renderer.

Runs with synthetic tones (not speech), never makes paid TTS calls, and
never uploads anything to YouTube. Verifies frame rendering and MP4 encoding.
"""
import json
import os
import subprocess
from pathlib import Path
from pydub import AudioSegment

os.environ["CHAT_TEST_MODE"] = "1"
os.environ["CHAT_RENDER_FPS"] = "4"
os.environ["CHAT_LANG"] = "en"
os.environ["CHAT_TTS_PROVIDER"] = "edge"
os.environ["CHAT_JSON"] = json.dumps({
    "chatTitle": "Ignore This Title",
    "coverText": "This Is Not A Subtitle",
    "dialogue": [
        {"speaker": "me", "text": "Dad, why is the kitchen locked?"},
        {"speaker": "father", "text": "Don't open it. Trust me."},
        {"speaker": "me", "text": "Why do I hear barking?"},
        {"speaker": "father", "text": "Because your mother bought a surprise."},
        {"speaker": "me", "text": "We already have a dog!"},
        {"speaker": "father", "text": "This one is slightly different."},
        {"speaker": "me", "text": "What do you mean slightly?"},
        {"speaker": "father", "text": "It can open the fridge."},
        {"speaker": "me", "text": "That sounds like my brother."},
        {"speaker": "father", "text": "I said what I said."},
        {"speaker": "me", "text": "So there isn't another dog?"},
        {"speaker": "father", "text": "No, but the fridge is empty."}
    ]
})
import render

# Reference layout: black bars, a cream conversation card, fixed main avatar
# and distinctly illustrated contact roles. No network or speech API needed.
assert render.PEER == "father"
from pastel_layout import portrait
CREAM = (248, 244, 234)
assert portrait("me").tobytes() == portrait("me").tobytes()
assert portrait("father").tobytes() != portrait("mother").tobytes()
assert portrait("sister").tobytes() != portrait("grandpa").tobytes()
render.VIDEO_DURATION = 12
preview = render.draw_frame(0, [])
assert preview.size == (720, 1280)
assert preview.getpixel((5, 5)) == (0, 0, 0), "Top black safe space missing"
assert preview.getpixel((30, 180)) == CREAM, "Cream card missing"
assert preview.getpixel((590, 1005)) != CREAM, "Main character not visible"
assert preview.getpixel((100, 330)) != CREAM, "Contact character not visible"
# After a message begins, its first bubble appears on the correct side.
frame = render.draw_frame(1.5, [1.0])
assert frame.getpixel((500, 505)) != CREAM, "First message bubble missing"
render.main()

target = Path("out/short.mp4")
assert target.exists(), "No MP4 produced"
assert target.stat().st_size > 50000, "MP4 is suspiciously tiny"
# The standalone FFmpeg wheel does not bundle ffprobe; read its duration
# from FFmpeg's standard stream diagnostic instead.
probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(target)],
    capture_output=True, text=True)
import re
match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", probe.stderr)
assert match, f"FFmpeg could not inspect MP4: {probe.stderr[:300]}"
duration = int(match.group(1))*3600 + int(match.group(2))*60 + float(match.group(3))
assert duration > 8, f"Video too short: {duration}"
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-ss", "4", "-i", str(target), "-frames:v", "1",
    "out/smoke-preview.png"
], check=True)
assert Path("out/smoke-preview.png").exists()
print(json.dumps({"smoke_test": "passed", "duration": round(duration,2),
                  "mp4_bytes":target.stat().st_size}))
