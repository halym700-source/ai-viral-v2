#!/usr/bin/env python3
"""Generate an original portrait fictional-chat short with per-character TTS.

Usage: set CHAT_JSON and CHAT_LANG=en|tr environment variables, run:
    python chat_renderer/render.py

The speech backend is unofficial edge-tts, whose availability and downstream
content/licensing conditions must be checked separately before commercial use.
"""
import asyncio
import base64
import io
import json
import math
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlencode
import subprocess
import time
import urllib.request
import urllib.error

import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydub import AudioSegment
from pydub.generators import Sine

W, H, FPS = 720, 1280, int(os.environ.get('CHAT_RENDER_FPS', '20'))
if FPS < 4 or FPS > 30:
    raise ValueError('CHAT_RENDER_FPS must be between 4 and 30')
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
           "grandma", "maternal_grandma", "paternal_grandma", "daughter", "son",
           "uncle", "aunt", "friend", "sister", "brother"}
for line in lines:
    if line.get("speaker") not in allowed:
        raise ValueError(f"Unrecognized speaker: {line.get('speaker')}")
    if not isinstance(line.get("text"), str) or not (1 <= len(line["text"]) <= 180):
        raise ValueError("Message text must be 1-180 characters")
if len({m["speaker"] for m in lines}) > 3:
    raise ValueError("At most 3 voices per story")

# Prefer neural voices marked for conversational reading, not news narration.
# Natural pauses are handled in build_audio; no extreme pitch manipulation.
EN_VOICES = {
    "me": ("en-US-AndrewNeural", "+0%", "+0Hz"),
    "girlfriend": ("en-US-AvaNeural", "+0%", "+0Hz"),
    "boyfriend": ("en-US-BrianNeural", "+0%", "+0Hz"),
    "mother": ("en-US-EmmaNeural", "-2%", "+0Hz"),
    "father": ("en-US-BrianNeural", "-2%", "+0Hz"),
    "grandpa": ("en-US-ChristopherNeural", "-4%", "+0Hz"),
    "grandma": ("en-US-MichelleNeural", "-3%", "+0Hz"),
    "maternal_grandma": ("en-US-MichelleNeural", "-3%", "+0Hz"),
    "paternal_grandma": ("en-US-MichelleNeural", "-3%", "+0Hz"),
    "daughter": ("en-US-AvaNeural", "+0%", "+0Hz"),
    "son": ("en-US-EricNeural", "+0%", "+0Hz"),
    "uncle": ("en-US-RogerNeural", "-1%", "+0Hz"),
    "aunt": ("en-US-EmmaNeural", "-2%", "+0Hz"),
    "friend": ("en-US-SteffanNeural", "+0%", "+0Hz"),
    "sister": ("en-US-AvaNeural", "+0%", "+0Hz"),
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
    "maternal_grandma": ("tr-TR-EmelNeural", "-16%", "-16Hz"),
    "paternal_grandma": ("tr-TR-EmelNeural", "-16%", "-16Hz"),
    "daughter": ("tr-TR-EmelNeural", "+5%", "+8Hz"),
    "son": ("tr-TR-AhmetNeural", "+4%", "+4Hz"),
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
           "grandma": "Grandma", "maternal_grandma": "Grandma",
           "paternal_grandma": "Grandma", "daughter": "Daughter", "son": "Son",
           "uncle": "Uncle", "aunt": "Aunt",
           "friend": "Bestie", "sister": "Sis", "brother": "Bro"},
    "tr": {"me": "Sen", "girlfriend": "Aşkım", "boyfriend": "Aşkım",
           "mother": "Annem", "father": "Babam", "grandpa": "Dedem",
           "grandma": "Ninem", "maternal_grandma": "Anneannem",
           "paternal_grandma": "Babaannem", "daughter": "Kızım", "son": "Oğlum",
           "uncle": "Amcam", "aunt": "Teyzem",
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
    "maternal_grandma": ("Grandma", "Maternal grandmother"),
    "paternal_grandma": ("Grandma", "Paternal grandmother"),
    "daughter": ("My Daughter", "Daughter"),
    "son": ("My Son", "Son"),
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
    "maternal_grandma": ("Anneannem", "Anneanne"),
    "paternal_grandma": ("Babaannem", "Babaanne"),
    "daughter": ("Kızım", "Kızın"),
    "son": ("Oğlum", "Oğlun"),
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

# Default stays on the existing service until the owner explicitly enables paid
# premium narration. Never store API keys in code or a public workflow payload.
TTS_PROVIDER = os.environ.get("CHAT_TTS_PROVIDER", "edge").lower().strip()
if TTS_PROVIDER not in ("edge", "gemini"):
    raise ValueError("CHAT_TTS_PROVIDER must be 'edge' or 'gemini'")

GEMINI_VOICES = {
    "me": "Puck",
    "girlfriend": "Kore",
    "boyfriend": "Fenrir",
    "mother": "Kore",
    "father": "Charon",
    "grandpa": "Charon",
    "grandma": "Kore",
    "maternal_grandma": "Kore",
    "paternal_grandma": "Kore",
    "daughter": "Kore",
    "son": "Fenrir",
    "uncle": "Charon",
    "aunt": "Kore",
    "friend": "Puck",
    "sister": "Kore",
    "brother": "Fenrir",
}

def gemini_delivery(index, msg):
    role = msg["speaker"]
    text = msg["text"].strip()
    notes = [
        "sound like a real person talking casually to family in a private chat",
        "US English, natural breathing and lively but understated emphasis",
        "NOT a commercial announcer, robotic narrator, or exaggerated character",
    ]
    if role in ("father", "grandpa", "uncle"):
        notes.append("wry, older family member with subtle deadpan humor")
    elif role in ("mother", "grandma", "maternal_grandma", "paternal_grandma", "aunt"):
        notes.append("warm, conversational and slightly amused")
    elif role == "me":
        notes.append("young adult reacting spontaneously")
    else:
        notes.append("young adult with relaxed, believable inflection")
    if text.endswith("?"):
        notes.append("genuine curiosity, not a staged question")
    if index == len(lines)-1:
        notes.append("deliver the punchline dryly with a barely suppressed smile")
    return "; ".join(notes)

def gemini_voice_blocking(index, msg):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Premium Gemini narration selected but GEMINI_API_KEY GitHub secret "
            "is missing; do not publish this video."
        )
    model = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
    if model not in ("gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"):
        raise ValueError("Unsupported TTS model")
    output = TMP / f"{index:03d}.wav"
    payload = {
        "model": model,
        "input": [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": msg["text"],
                "annotations": [{"type": "speech_metadata",
                                 "style": gemini_delivery(index, msg)}],
            }]
        }],
        "response_format": {"type": "audio"},
        "generation_config": {
            "speech_config": [{"voice": GEMINI_VOICES[msg["speaker"]]}]
        }
    }
    body = json.dumps(payload).encode("utf-8")
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={"x-goog-api-key":key,
                         "Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                response = json.load(resp)
            # In raw REST responses, the last model-output audio block carries
            # base64 data at steps[].content[].data (not response.output_audio).
            audio_b64 = None
            for step in response.get("steps", []):
                if step.get("type") != "model_output":
                    continue
                for piece in step.get("content", []):
                    if piece.get("type") == "audio" and piece.get("data"):
                        audio_b64 = piece["data"]
            if not audio_b64:
                audio_b64 = (response.get("output_audio") or {}).get("data")
            if not audio_b64:
                raise RuntimeError("Gemini returned no audio payload")
            audio_bytes = base64.b64decode(audio_b64, validate=True)
            if len(audio_bytes) < 1000:
                raise RuntimeError("Gemini speech output is empty")
            output.write_bytes(audio_bytes)
            return output
        except urllib.error.HTTPError as e:
            details = e.read(512).decode("utf-8","replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep((attempt+1)*15)
                continue
            raise RuntimeError(
                f"Gemini TTS request {index} HTTP {e.code}: {details}"
            ) from e
        except (TimeoutError, urllib.error.URLError) as e:
            if attempt < 2:
                time.sleep((attempt+1)*15)
                continue
            raise RuntimeError(f"Gemini TTS network error at line {index}: {e}") from e
    raise RuntimeError("Gemini TTS failed")

async def generate_voice(index, msg):
    # Local and CI visual test mode never calls paid/remote speech services.
    # The production GitHub workflow does not set this variable.
    if os.environ.get("CHAT_TEST_MODE", "0") == "1":
        output = TMP / f"{index:03d}.wav"
        duration = 600 + min(300, len(msg["text"]) * 5)
        test_tone = Sine(220 + (index % 4) * 70).to_audio_segment(
            duration=duration).apply_gain(-23)
        test_tone.export(str(output), format="wav")
        return output
    if TTS_PROVIDER == "gemini":
        # One request per message preserves exact visual/audio synchronization.
        # It incurs API usage cost; do not enable without consent.
        return await asyncio.to_thread(gemini_voice_blocking, index, msg)

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
    """Warm home-wallpaper illustration; original artwork, no borrowed video images."""
    import random
    rng = random.Random(41)
    im = Image.new("RGB", (W, H), "#e5d7c6")
    d = ImageDraw.Draw(im)

    # Soft indoor plaster tones and low-contrast texture.
    for y in range(H):
        f = y / float(H)
        d.line((0, y, W, y), fill=(
            int(234 - 31 * f), int(224 - 37 * f), int(207 - 37 * f)))
    for _ in range(500):
        x, y = rng.randrange(W), rng.randrange(130, H)
        c = rng.choice([(227, 213, 196), (240, 231, 217), (211, 202, 184)])
        d.ellipse((x, y, x+2, y+2), fill=c)

    # Walnut wall trim and a distant interior scene.
    d.rectangle((0, 155, W, 184), fill=(87, 55, 39))
    d.rectangle((0, 184, W, 194), fill=(130, 85, 56))
    d.rectangle((0, 880, W, 916), fill=(112, 72, 51))
    for xx in range(60, W, 230):
        d.rectangle((xx, 915, xx+13, H), fill=(113, 81, 63))
        d.line((xx+7, 915, xx+7, H), fill=(163, 123, 91), width=2)

    # Muted leaf silhouettes in the middle background.
    for seedx, seedy, scale in [(43, 930, 1.0), (665, 965, 1.3),
                                (465, 875, 0.85)]:
        base_x, base_y = int(seedx), int(seedy)
        for k in range(12):
            dx = rng.randrange(-100, 100) * scale
            dy = rng.randrange(-205, 20) * scale
            end_x, end_y = int(base_x+dx), int(base_y+dy)
            d.line((base_x, base_y, end_x, end_y), fill=(55, 91, 62), width=4)
            sz = rng.randrange(18, 36) * scale
            d.ellipse((end_x-sz, end_y-sz/2, end_x+sz, end_y+sz/2),
                      fill=rng.choice([(66, 110, 75), (78, 121, 77), (91, 131, 83)]))
        d.polygon([(base_x-20,base_y-8),(base_x+24,base_y-8),
                   (base_x+13,base_y+70),(base_x-8,base_y+70)],
                  fill=(163, 108, 78))
    # Small red flowers make the background feel lived-in.
    for x,y in [(52,712),(104,745),(640,780),(671,741),(421,800),
                (480,830),(525,771)]:
        for dx,dy in [(-12,0),(10,0),(0,-11),(0,11)]:
            d.ellipse((x+dx-10,y+dy-10,x+dx+10,y+dy+10),fill=(183,49,57))
        d.ellipse((x-7,y-7,x+7,y+7),fill=(234,185,81))
    # Keep wallpaper behind chat bubbles slightly muted for readability.
    wash = Image.new("RGB",(W,H),(240,234,221))
    return Image.blend(im,wash,0.18)

BASE = gradient_background()

# A new portrait is picked for each rendered story, based on the real contact
# role rather than the headline. Use Pexels free-use stock photos first, then
# Wikimedia Commons CC0/public domain; never scrape Google image search.
PHOTO_SEARCHES = {
    "father": "portrait middle aged man face photograph",
    "mother": "portrait middle aged woman face photograph",
    "grandpa": "portrait elderly man face photograph",
    "grandma": "portrait elderly woman face photograph",
    "maternal_grandma": "portrait elderly woman face photograph",
    "paternal_grandma": "portrait elderly woman face photograph",
    "girlfriend": "portrait young adult woman face photograph",
    "boyfriend": "portrait young adult man face photograph",
    "daughter": "portrait young woman face photograph",
    "son": "portrait young man face photograph",
    "aunt": "portrait woman face photograph",
    "uncle": "portrait man face photograph",
    "sister": "portrait young woman face photograph",
    "brother": "portrait young man face photograph",
    "friend": "portrait adult face photograph",
}
# Hand-checked role/age categories from Pexels free-use portrait pages.
# Pexels allows reuse in videos without attribution, but no real identity or
# endorsement is implied by a fictional contact name.
PEXELS_PORTRAITS = {
    "father": [35828102, 28513050, 19285927, 17824398],
    "mother": [29405854, 15026471],
    "grandpa": [6667746, 17575432],
    "grandma": [6972646, 7937532, 12950150, 5610408],
    "maternal_grandma": [6972646, 7937532, 12950150, 5610408],
    "paternal_grandma": [12950150, 5610408, 6972646, 7937532],
    "girlfriend": [35736940, 17532983],
    "boyfriend": [23285865, 20709195, 3958799],
    "daughter": [35736940, 17532983],
    "son": [23285865, 20709195, 3958799],
    "aunt": [29405854, 15026471],
    "uncle": [28513050, 19285927, 17824398],
    "sister": [35736940, 17532983],
    "brother": [23285865, 20709195, 3958799],
    "friend": [17532983, 23285865, 35736940, 20709195],
}
PHOTO_AGENT = "TextVibeStories/1.0 (https://github.com/halym700-source/ai-viral-v2)"
PROFILE_PHOTO = None

def load_contact_portrait(role):
    """Try a freely usable role-matched photo; never fail the video on network issues.

    No remote calls in offline tests. The returned face is visual fiction and
    does not imply that the photographed person is a real family member.
    """
    if os.environ.get("CHAT_TEST_MODE") == "1":
        return None
    if os.environ.get("CHAT_PROFILE_PHOTOS", "on").lower() in ("off", "0", "false"):
        return None
    # Start with a small curated collection to avoid paintings, public
    # figures, or unrelated images in broad image-search results.
    ids = list(PEXELS_PORTRAITS.get(role, PEXELS_PORTRAITS["friend"]))
    secrets.SystemRandom().shuffle(ids)
    for photo_id in ids:
        url = (f"https://images.pexels.com/photos/{photo_id}/"
               f"pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w=256&h=256&fit=crop")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": PHOTO_AGENT})
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read(1_200_001)
            if len(raw) > 1_200_000:
                continue
            with Image.open(io.BytesIO(raw)) as img:
                if min(img.size) < 80:
                    continue
                portrait = ImageOps.fit(img.convert("RGB"), (92, 92))
            (OUT / "profile_photo_source.json").write_text(
                json.dumps({"role": role, "source": f"https://www.pexels.com/photo/{photo_id}/",
                            "license": "Pexels License"}, ensure_ascii=False),
                encoding="utf-8")
            return portrait
        except (OSError, ValueError, urllib.error.URLError):
            continue

    # If Pexels is unavailable, search Wikimedia Commons for CC0/PD photos.
    search = PHOTO_SEARCHES.get(role, "portrait adult face photograph")
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": search, "gsrnamespace": 6, "gsrlimit": 24,
        "prop": "imageinfo", "iiprop": "url|mime|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|AttributionRequired",
        "iiurlwidth": 256,
    }
    api_url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    try:
        request = urllib.request.Request(
            api_url, headers={"User-Agent": PHOTO_AGENT, "Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=9) as response:
            pages = json.load(response).get("query", {}).get("pages", {})
        options = []
        for page in pages.values():
            if not page.get("title", "").lower().endswith(
                    (".jpg", ".jpeg", ".png", ".webp")):
                continue
            info = (page.get("imageinfo") or [{}])[0]
            if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
                continue
            meta = info.get("extmetadata", {})
            license_name = str(meta.get("LicenseShortName", {}).get("value", "")).lower()
            permitted = ("cc0" in license_name or "public domain" in license_name
                         or license_name.startswith("pd-") or license_name == "pd")
            if not permitted:
                continue
            url = info.get("thumburl")
            if url and url.startswith("https://upload.wikimedia.org/"):
                options.append((url, info.get("descriptionurl", ""), license_name))
        secrets.SystemRandom().shuffle(options)
        for image_url, source_page, license_name in options[:6]:
            try:
                req = urllib.request.Request(
                    image_url, headers={"User-Agent": PHOTO_AGENT}
                )
                with urllib.request.urlopen(req, timeout=7) as result:
                    raw = result.read(2_000_001)
                if len(raw) > 2_000_000:
                    continue
                with Image.open(io.BytesIO(raw)) as candidate:
                    if min(candidate.size) < 80:
                        continue
                    portrait = ImageOps.fit(candidate.convert("RGB"), (92, 92))
                # Include provenance as a sidecar for auditing. Only PD/CC0.
                (OUT / "profile_photo_source.json").write_text(
                    json.dumps({"role": role, "source": source_page,
                                "license": license_name}, ensure_ascii=False),
                    encoding="utf-8"
                )
                return portrait
            except (OSError, ValueError, urllib.error.URLError):
                continue
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        pass
    print(f"Portrait unavailable for {role}; using local fallback avatar.")
    return None

PROFILE_PHOTO = load_contact_portrait(PEER)

def build_audio(paths):
    master = AudioSegment.silent(duration=180)
    start_times = []
    for path in paths:
        sound = AudioSegment.from_file(str(path)).set_channels(1).set_frame_rate(44100)
        # Gently level very quiet/loud lines so different speakers feel
        # like participants in the same conversation without crushing dynamics.
        if sound.dBFS != float("-inf"):
            gain = max(-3.0, min(3.0, -20.0 - sound.dBFS))
            sound = sound.apply_gain(gain)
        start_times.append(len(master) / 1000.0)
        # A brief conversational beat, slightly longer after questions.
        previous_text = lines[len(start_times)-1]["text"].strip()
        pause_ms = 235 if previous_text.endswith("?") else 155
        master += sound + AudioSegment.silent(duration=pause_ms)
    master += AudioSegment.silent(duration=750)
    wav = OUT / "audio.wav"
    master.export(str(wav), format="wav")
    return wav, start_times, len(master) / 1000.0

# The reference places content in a light conversation view with warm wallpaper.
# Keep a small margin on both sides; the former 112px right gutter
# made outgoing messages look squeezed and left a visible empty strip.
CHAT_TOP, CHAT_BOTTOM = 144, 1010
CHAT_GAP = 11
CHAT_TEXT_WIDTH = 583
CHAT_LINE_HEIGHT = 38

def display_sender(role):
    if role == "me":
        return "You" if LANG == "en" else "Sen"
    return CONTACT_NAME_BY_ROLE.get(role, role.title())

def bubble_size(draw, msg):
    rows = safe_wrap(draw, msg["text"], F["text"], CHAT_TEXT_WIDTH)
    return rows, 24 + len(rows) * CHAT_LINE_HEIGHT + 25

def draw_frame(t, start_times):
    image = BASE.copy()
    d = ImageDraw.Draw(image)

    # Familiar yet originally drawn chat app header, not an app screenshot.
    d.rectangle((0, 0, W, 127), fill=(255, 255, 255))
    d.line((0, 126, W, 126), fill=(204, 204, 202), width=2)
    d.line(((23, 49), (11, 63), (23, 77)), fill=(67, 74, 77), width=4)
    d.ellipse((42, 20, 133, 111), fill=(182, 195, 172))
    if PROFILE_PHOTO is not None:
        mask = Image.new("L", (92, 92), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 91, 91), fill=255)
        image.paste(PROFILE_PHOTO, (42, 20), mask)
        d.ellipse((42, 20, 133, 111), outline=(234, 234, 231), width=2)
    else:
        # Offline/no-connection avatar: real photo is never fabricated.
        d.ellipse((68, 43, 109, 85), fill=(229, 206, 167))
        d.arc((64, 48, 113, 101), 185, 356, fill=(107, 93, 77), width=3)
    name = CONTACT_NAME[:16].upper()
    d.text((150, 28), name, font=F["head"], fill=(29, 34, 37))
    subtitle = (CONTACT_ROLE + "  •  online") if LANG == "en" else (CONTACT_ROLE + "  •  çevrimiçi")
    d.text((153, 81), subtitle, font=F["tiny"], fill=(113, 117, 115))
    # Camcorder, telephone, more buttons in our own glyph style.
    d.rounded_rectangle((541, 47, 575, 75), radius=4, outline=(41,45,48),width=3)
    d.polygon([(575, 54), (589, 46), (589, 77), (575, 70)],fill=(41,45,48))
    d.arc((610, 41, 651, 81), 32, 143, fill=(41,45,48), width=5)
    for yy in (48, 60, 72):
        d.ellipse((686, yy, 693, yy+7),fill=(43,46,49))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    visible = [i for i, start in enumerate(start_times) if start <= t]
    if visible:
        entries = [(i, lines[i], *bubble_size(ld, lines[i])) for i in visible]
        heights = [entry[3] + CHAT_GAP for entry in entries]
        usable = CHAT_BOTTOM - CHAT_TOP - 12
        cumulative = sum(heights)
        prev = cumulative - heights[-1]
        elapsed = max(0.0, min(1.0, (t - start_times[visible[-1]]) / .34))
        ease = 1.0 - (1.0 - elapsed)**3
        scroll_prev = max(0, prev - usable)
        scroll_next = max(0, cumulative - usable)
        scroll = scroll_prev + (scroll_next - scroll_prev) * ease
        y = CHAT_TOP + 9 - round(scroll)

        for i, msg, rows, height in entries:
            if y + height < CHAT_TOP or y > CHAT_BOTTOM:
                y += height + CHAT_GAP
                continue
            own = msg["speaker"] == "me"
            widest = max(ld.textbbox((0, 0), row, font=F["text"])[2] for row in rows)
            bubble_w = max(195, min(W - 49, widest + 48))
            left = W - 24 - bubble_w if own else 24
            right = left + bubble_w
            easing = max(0, min(1, (t-start_times[i])/.20))
            left += int((1-easing)*(13 if own else -13))
            right += int((1-easing)*(13 if own else -13))
            background = (213, 246, 195, 255) if own else (255, 255, 255, 255)
            outline = (191, 226, 176, 255) if own else (225, 226, 219, 255)
            ld.rounded_rectangle((left, y, right, y+height), radius=19,
                                 fill=background, outline=outline, width=1)
            # Speech-bubble tails: subtle, readable and familiar.
            if own:
                ld.polygon([(right-3,y+11),(right+9,y+16),(right-3,y+31)],fill=background)
            else:
                ld.polygon([(left+3,y+11),(left-8,y+16),(left+3,y+31)],fill=background)
            ty = y+14
            for row in rows:
                ld.text((left+21, ty), row, font=F["text"], fill=(23, 29, 29, 255))
                ty += CHAT_LINE_HEIGHT
            # A small timestamp and double checkmarks make it feel like a chat.
            mm = 35+(i//6)
            stamp = f"14:{mm:02d}"
            font = F["tiny"]
            sw = ld.textbbox((0,0),stamp,font=font)[2]
            ld.text((right-15-sw-(29 if own else 0),y+height-30),
                    stamp,font=font,fill=(125,135,134,255))
            if own:
                check_x = right - 31
                cy=y+height-20
                ld.line([(check_x-7,cy-2),(check_x-3,cy+2),(check_x+4,cy-6)],
                        fill=(40,153,201,255),width=2)
                ld.line([(check_x,cy-2),(check_x+4,cy+2),(check_x+11,cy-6)],
                        fill=(40,153,201,255),width=2)
            y += height + CHAT_GAP
    viewport = layer.crop((0,CHAT_TOP,W,CHAT_BOTTOM))
    image.paste(viewport,(0,CHAT_TOP),viewport)

    # The bottom remains wallpaper, not a fake message box covering the ending.
    # A quiet timeline under the chat avoids interference with Shorts UI.
    d.rectangle((0,1110,W,1118),fill=(221,219,206))
    progress = max(0,min(1,t/max(VIDEO_DURATION,0.001)))
    d.rectangle((0,1110,round(W*progress),1118),fill=(90,174,138))
    return image

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
