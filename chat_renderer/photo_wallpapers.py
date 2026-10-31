"""Per-video licensed photographic chat wallpapers for TextVibeStories.

Only the chat BODY changes; the contact header, message bubbles, and
main character remain readable and consistent. Landscape source photos
are downloaded from Pexels (https://www.pexels.com/license/).
The same story/job id always gets the same wallpaper; distinct job ids
also vary the photo crop. A video renders a single stable backdrop.
"""
import hashlib
import io
import json
import os
import re
import secrets
import urllib.request
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

# Curated landscapes and interiors, avoiding identifiable faces and logos.
PHOTO_IDS = (
    417074, 15286, 1366919, 1323550, 167964, 459203,
    1450353, 2559941, 210186, 753626, 1080721, 1519088, 2774879,
)
PAPER_W, PAPER_H = 656, 882
WASH = (248, 244, 234)
AGENT = 'TextVibeStories wallpaper renderer (https://github.com/halym700-source/ai-viral-v2)'
CACHED_BACKGROUND = None
CACHED_PHOTO_ID = None

def seed_value():
    # The n8n-dispatched job_id is unique for each finished video.
    # Use GitHub's unique run id in standalone Action previews.
    return (os.environ.get('CHAT_JOB_ID') or
            os.environ.get('GITHUB_RUN_ID') or
            secrets.token_hex(12))

def choice_for_seed(seed):
    raw = hashlib.blake2b(str(seed).encode('utf8'), digest_size=16).digest()
    # n8n job ids include a base36 Date.now() timestamp.
    # Hour-by-hour cycling through a prime-sized catalogue makes consecutive
    # scheduled videos (even videos exactly one day apart) use another photo.
    match = re.match(r'^(?:en|tr)-([0-9a-z]+)-', str(seed))
    if match:
        try:
            hour = int(match.group(1), 36) // 3_600_000
            return hour % len(PHOTO_IDS), raw
        except ValueError:
            pass
    # Other manual/private jobs still get independent random-looking choices.
    return int.from_bytes(raw[:4], 'big') % len(PHOTO_IDS), raw

def image_from_photo(photo_id):
    url = (f'https://images.pexels.com/photos/{photo_id}/'
           f'pexels-photo-{photo_id}.jpeg'
           '?auto=compress&cs=tinysrgb&w=760&h=1050&fit=crop')
    req = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        typ = (resp.headers.get('Content-Type') or '').lower()
        if not typ.startswith('image/'):
            raise RuntimeError(f'Not an image: {photo_id}')
        raw = resp.read(3_000_001)
    if len(raw) > 3_000_000:
        raise RuntimeError('Wallpaper exceeds size limit')
    with Image.open(io.BytesIO(raw)) as img:
        img.verify()
    with Image.open(io.BytesIO(raw)) as img:
        if min(img.size) < 180:
            raise RuntimeError('Wallpaper source resolution too small')
        return img.convert('RGB')

def test_photo(raw):
    """Offline synthetic fixture: only used by CI test, never published."""
    from PIL import ImageDraw
    c=(raw[0],raw[1],raw[2])
    im=Image.new('RGB', (850, 1200), (45+c[0]//5, 69+c[1]//4, 101+c[2]//5))
    d=ImageDraw.Draw(im)
    for y in range(1200):
        d.line((0,y,850,y),fill=(35+(y+c[0])%130,85+(y//5)%100,125+(c[1]+y//9)%100))
    d.polygon([(0,760),(280,300),(495,780),(790,440),(850,630),(850,1200),(0,1200)],
              fill=(45,79,82))
    return im

def build_photo_wallpaper(seed=None):
    seed = str(seed or seed_value())
    index, key = choice_for_seed(seed)
    # The single selected photograph is consistent across all frames.
    if os.environ.get('CHAT_WALLPAPER_TEST_MODE') == '1':
        source = test_photo(key)
        photo_id = 'test-fixture'
    else:
        source = None
        photo_id = None
        errors = []
        # Try several distinct photos if a CDN source becomes unavailable.
        for offset in range(min(6, len(PHOTO_IDS))):
            candidate = PHOTO_IDS[(index+offset) % len(PHOTO_IDS)]
            try:
                source = image_from_photo(candidate)
                photo_id = candidate
                break
            except (OSError, ValueError, RuntimeError) as e:
                errors.append(f'{candidate}:{e}')
        if source is None:
            raise RuntimeError('No photographic wallpaper available, video not rendered: '+
                               '; '.join(errors)[:400])

    # Repeat-safe style: unique crop centering + tint for each job.
    cx = .32 + key[5]/255*.36
    cy = .35 + key[6]/255*.30
    photo = ImageOps.fit(source, (PAPER_W,PAPER_H), centering=(cx,cy),
                         method=Image.Resampling.LANCZOS)
    if key[7] % 2:
        photo=ImageOps.mirror(photo)
    color_factor=.68+key[8]/255*.19
    photo=ImageEnhance.Color(photo).enhance(color_factor)
    # Keep the requested PHOTO visible, while giving text legible contrast.
    photo=Image.blend(photo,Image.new('RGB',photo.size,WASH),.64)
    return photo, photo_id

def apply_wallpaper(image, seed=None):
    global CACHED_BACKGROUND,CACHED_PHOTO_ID
    if CACHED_BACKGROUND is None:
        CACHED_BACKGROUND, CACHED_PHOTO_ID = build_photo_wallpaper(seed)
        # Record source and licensing for audits, not for onscreen attribution.
        if CACHED_PHOTO_ID != 'test-fixture':
            out=Path('out');out.mkdir(exist_ok=True)
            (out/'wallpaper_source.json').write_text(json.dumps({
                'provider':'Pexels', 'photo_id':CACHED_PHOTO_ID,
                'source':f'https://www.pexels.com/photo/{CACHED_PHOTO_ID}/',
                'license':'https://www.pexels.com/license/',
            }),encoding='utf8')
            print(f'Wallpaper photo selected: {CACHED_PHOTO_ID}')
    mask=Image.new('L',(PAPER_W,PAPER_H),0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,PAPER_W-1,PAPER_H-1),
                                           radius=20,fill=255)
    image.paste(CACHED_BACKGROUND,(32,252),mask)
    return image
