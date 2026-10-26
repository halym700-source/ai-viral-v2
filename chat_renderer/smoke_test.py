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

# Verify full-width outgoing bubble layout and a real image can be loaded into
# the 92px circular avatar without relying on external image-host availability.
assert render.CHAT_TEXT_WIDTH >= 560
assert render.PEER == "father"
from unittest.mock import patch
from PIL import Image
import io

jpeg = io.BytesIO()
Image.new("RGB", (128, 128), (84, 131, 152)).save(jpeg, format="JPEG")
def fake_pexels_response(req, timeout=8):
    assert req.full_url.startswith("https://images.pexels.com/photos/")
    return io.BytesIO(jpeg.getvalue())

with patch.dict(os.environ, {"CHAT_TEST_MODE": "0"}):
    with patch.object(render.urllib.request, "urlopen",
                      side_effect=fake_pexels_response):
        photo = render.load_contact_portrait("father")
assert photo is not None and photo.size == (92, 92)
# Force the test image into the actual rendered video frame as well.
render.PROFILE_PHOTO = photo
render.VIDEO_DURATION = 12
preview = render.draw_frame(0, [])
assert preview.getpixel((85, 60)) == (84, 131, 152), "Profile image is not visible in header"

render.main()

target = Path("out/short.mp4")
assert target.exists(), "No MP4 produced"
assert target.stat().st_size > 50000, "MP4 is suspiciously tiny"
duration = float(subprocess.check_output([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", str(target)
], text=True).strip())
assert duration > 8, f"Video too short: {duration}"
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-ss", "4", "-i", str(target), "-frames:v", "1",
    "out/smoke-preview.png"
], check=True)
assert Path("out/smoke-preview.png").exists()
print(json.dumps({"smoke_test": "passed", "duration": round(duration,2),
                  "mp4_bytes":target.stat().st_size}))
