#!/usr/bin/env python3
"""RESH RANKS: render a 24-second 5-clip YouTube Shorts ranking.

Sources must be supplied with per-source rights attestations. Only use videos
that you own, have permission to reuse, or have verified as appropriately CC.
Never tries to circumvent YouTube access controls: unavailable downloads fail.
"""
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw, ImageFont

WORK = Path(os.environ.get('RESH_WORK', 'out')).resolve()
WORK.mkdir(parents=True, exist_ok=True)
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
SIZES = [1.75, 3.8, 3.8, 3.8, 3.8, 7.05]
W, H = 720, 1280
VALID_RIGHTS = {'owned', 'permission', 'cc_by_verified'}


def run(cmd, timeout=300):
    print('RUN', ' '.join(str(x) for x in cmd[:8]), '...', flush=True)
    subprocess.run([str(x) for x in cmd], check=True, timeout=timeout)


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def textfit(draw, text, max_width, max_size=42, min_size=19):
    for size in range(max_size, min_size - 1, -1):
        f = font(size)
        if draw.textbbox((0, 0), text, font=f, stroke_width=2)[2] <= max_width:
            return f
    return font(min_size)


def center_text(draw, y, txt, *, max_width=680, size=42, color='white'):
    f = textfit(draw, txt, max_width, size)
    box = draw.textbbox((0, 0), txt, font=f, stroke_width=2)
    x = (W - (box[2] - box[0])) // 2
    draw.text((x, y), txt, font=f, fill=color, stroke_width=3,
              stroke_fill=(0, 0, 0, 225))


def overlay(stage, source, output):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Soft backdrop to keep captions readable without blocking subjects.
    d.rounded_rectangle((20, 45, 700, 135), radius=18, fill=(0, 0, 0, 105))
    if stage == 'hook':
        center_text(d, 65, 'This One Sounds İNSANE', size=40, color='#FFD037')
    else:
        center_text(d, 69, 'RANKING CRAZIEST REV SOUNDS', size=31)
        d.rounded_rectangle((575, 390, 695, 718), radius=17, fill=(0, 0, 0, 120))
        for j, rank in enumerate([5, 4, 3, 2, 1]):
            active = rank == source['rank']
            d.text((604, 404 + j * 63), f'#{rank}', font=font(33),
                   fill='#FFD037' if active else (230, 230, 230, 145),
                   stroke_width=2, stroke_fill=(0, 0, 0, 180))
        d.rounded_rectangle((25, 1033, 695, 1145), radius=18, fill=(0, 0, 0, 165))
        center_text(d, 1048, f"#{source['rank']}  {source['name'].upper()}", size=41, max_width=640)
        extra = source.get('subtitle', '')
        if extra:
            center_text(d, 1106, extra.upper(), size=22, color='#FFD037')
    # Tiny semi-transparent right-edge watermark.
    marker = Image.new('RGBA', (280, 42), (0, 0, 0, 0))
    ImageDraw.Draw(marker).text((5, 4), '@reshranks', fill=(255, 255, 255, 90), font=font(24))
    marker = marker.rotate(90, expand=True)
    im.alpha_composite(marker, (674, 735))
    im.save(output)


def probe(path):
    raw = subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                   '-show_format', '-of', 'json', str(path)], timeout=30)
    return json.loads(raw)


def validate_url(url):
    p = urllib.parse.urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Only public HTTPS video URLs are allowed')
    host = p.hostname.lower()
    if host in ('localhost', 'localhost.localdomain') or host.endswith('.local'):
        raise ValueError('Local URLs are not allowed')
    try:
        ipaddress.ip_address(host)
        raise ValueError('IP-address URLs are not accepted')
    except ValueError as e:
        if 'not accepted' in str(e):
            raise
    return host


def fetch_source(source, idx):
    url = source['url']
    # Local input is for automated smoke tests, not the remote workflow.
    if url.startswith('file://') and os.environ.get('RESH_TEST_LOCAL') == '1':
        p = Path(urllib.parse.urlparse(url).path)
        if not p.is_file():
            raise ValueError('Local smoke-test file not found')
        return p
    host = validate_url(url)
    target = WORK / f'source_{idx}'
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'music.youtube.com'}:
        # yt-dlp does not guarantee success: fail instead of faking output.
        template = str(target) + '.%(ext)s'
        run(['yt-dlp', '--no-playlist', '--no-progress', '--restrict-filenames',
             '--socket-timeout', '20', '--retries', '2', '--fragment-retries', '2',
             '--max-filesize', '180M', '-f', 'bv*[height<=1080]+ba/b[height<=1080]/b',
             '--merge-output-format', 'mp4', '-o', template, url], 240)
        matches = list(WORK.glob(target.name + '.*'))
        if len(matches) != 1:
            raise ValueError('YouTube download did not produce one video file')
        return matches[0]
    if not p_url_is_mp4(url):
        raise ValueError('For non-YouTube URLs provide a direct .mp4 file link')
    path = Path(str(target) + '.mp4')
    req = urllib.request.Request(url, headers={'User-Agent': 'ReshRanksRenderer/1.0'})
    with urllib.request.urlopen(req, timeout=35) as resp, path.open('wb') as out:
        final_host = validate_url(resp.geturl())
        if not final_host:
            raise ValueError('Redirect target invalid')
        total = 0
        while block := resp.read(1024 * 1024):
            total += len(block)
            if total > 180 * 1024 * 1024:
                raise ValueError('File exceeds size limit')
            out.write(block)
    return path


def p_url_is_mp4(url):
    return urllib.parse.urlparse(url).path.lower().endswith('.mp4')


def segment(src, start, seconds, ovl, output):
    info = probe(src)
    duration = float(info['format']['duration'])
    if duration < seconds + 0.05:
        raise ValueError(f'Clip too short ({duration:.1f}s < {seconds:.1f}s)')
    if not any(s['codec_type'] == 'audio' for s in info['streams']):
        raise ValueError('Original clip has no audio; sound ranking requires real audio')
    start = max(0, min(float(start), duration - seconds - 0.02))
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-ss', f'{start:.3f}', '-i', src,
           '-loop', '1', '-framerate', '30', '-i', ovl,
           '-filter_complex',
           '[0:v]scale=720:1280:force_original_aspect_ratio=increase,'
           'crop=720:1280,setsar=1,fps=30,format=yuv420p[base];'
           '[base][1:v]overlay=shortest=1,format=yuv420p[v]',
           '-map', '[v]', '-map', '0:a:0', '-t', f'{seconds:.3f}',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
           '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-ac', '2',
           '-movflags', '+faststart', '-pix_fmt', 'yuv420p', output]
    run(cmd, 220)


def main():
    raw = os.environ.get('RESH_SOURCES_JSON')
    if not raw:
        raise ValueError('Missing RESH_SOURCES_JSON')
    obj = json.loads(raw)
    sources = obj['sources']
    if not isinstance(sources, list) or len(sources) != 5:
        raise ValueError('Exactly five source videos are required')
    ranks = [s.get('rank') for s in sources]
    if ranks != [5, 4, 3, 2, 1]:
        raise ValueError('Source order must be ranks 5,4,3,2,1')
    for s in sources:
        if s.get('rights') not in VALID_RIGHTS or not s.get('rights_evidence'):
            raise ValueError(f"#{s['rank']} source rights not confirmed. "
                             'Required rights: owned, permission, cc_by_verified + rights_evidence')
        if not s.get('name') or len(s['name']) > 80:
            raise ValueError('Invalid video label')
    files = [fetch_source(s, i) for i, s in enumerate(sources)]
    jobs = [(sources[-1], files[-1], 'hook', SIZES[0], sources[-1].get('hook_start', 0))]
    jobs += [(s, p, 'rank', SIZES[i+1], s.get('start', 0))
             for i, (s, p) in enumerate(zip(sources, files))]
    segments = []
    for i, (s, p, stage, secs, start) in enumerate(jobs):
        ovl = WORK / f'overlay_{i}.png'
        dst = WORK / f'segment_{i}.mp4'
        overlay(stage, s, ovl)
        segment(p, start, secs, ovl, dst)
        segments.append(dst)
    playlist = WORK / 'concat.txt'
    playlist.write_text(''.join("file '" + str(p).replace("'", "'\\''") + "'\n"
                                for p in segments), encoding='utf-8')
    output = WORK / 'short.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat',
         '-safe', '0', '-i', playlist, '-c', 'copy', '-movflags', '+faststart', output])
    length = float(probe(output)['format']['duration'])
    if not 23.5 <= length <= 24.5:
        raise ValueError(f'Output length unexpected: {length:.3f}s')
    (WORK / 'manifest.json').write_text(json.dumps({
        'status': 'rendered_not_published', 'duration_seconds': length,
        'output': 'short.mp4', 'sources': [
            {k: v for k, v in s.items() if k in ('rank', 'name', 'url', 'rights', 'rights_evidence')}
            for s in sources]
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print('SUCCESS:', output, f'{length:.2f}s', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('RESH RANKS RENDER FAILED:', type(exc).__name__, str(exc), file=sys.stderr)
        raise
