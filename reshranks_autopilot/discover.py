#!/usr/bin/env python3
"""YouTube CC-BY footage discovery for a single, coherent ReshRanks topic.

Requires YOUTUBE_DATA_API_KEY. Filters YouTube's API for Creative Commons, checks
its video status, downloads via yt-dlp without authentication bypass, and skips
videos without usable original audio. No publication occurs in this script.
"""
import datetime as dt
import io
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile

OUT = Path(os.environ.get('RESH_WORK', 'out')).resolve()
OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ.get('YOUTUBE_DATA_API_KEY', '')
REPO = os.environ.get('GITHUB_REPOSITORY', 'halym700-source/ai-viral-v2')
GHTOKEN = os.environ.get('GITHUB_TOKEN', '')

THEMES = [
    {'key': 'motorcycle_revs', 'name': 'CRAZIEST MOTORCYCLE REV SOUNDS',
     'queries': ['motorcycle exhaust rev sound', 'sportbike motorcycle revving exhaust'],
     'required': ['motorcycle','motorbike','exhaust','rev','revs','r1','h2r','cbr','gsxr','ninja','ducati','yamaha','kawasaki','ktm','triumph','bmw s1000'],
     'reject': ['compilation', 'reaction', 'remix', 'ranking', 'top 5', 'royalty free music', 'sound effect']},
    {'key': 'supercar_exhaust', 'name': 'WILDEST SUPERCAR EXHAUST SOUNDS',
     'queries': ['supercar exhaust revving sound', 'lamborghini ferrari supercar engine rev'],
     'required': ['supercar','exhaust','rev','revs','ferrari','lamborghini','mclaren','porsche','pagani','bugatti','corvette','gtr','v8','v10','v12'],
     'reject': ['compilation', 'reaction', 'remix', 'ranking', 'top 5', 'royalty free music', 'sound effect']},
    {'key': 'motorcycle_startups', 'name': 'BEST MOTORCYCLE STARTUP SOUNDS',
     'queries': ['motorcycle engine startup exhaust sound', 'sportbike cold start sound'],
     'required': ['motorcycle','bike','cold start','startup','start up','exhaust','ducati','yamaha','kawasaki','honda','bmw','ktm','triumph'],
     'reject': ['compilation', 'reaction', 'remix', 'ranking', 'top 5', 'royalty free music', 'sound effect']},
]


def api(endpoint, args):
    if not KEY:
        raise RuntimeError('Missing YOUTUBE_DATA_API_KEY in GitHub Actions secrets')
    args = dict(args, key=KEY)
    url = 'https://www.googleapis.com/youtube/v3/' + endpoint + '?' + urllib.parse.urlencode(args)
    request = urllib.request.Request(url, headers={'Accept':'application/json', 'User-Agent':'ReshRanks Autopilot/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Avoid echoing the API key in logs; URL in error text can contain it.
        raise RuntimeError(f'YouTube Data API {endpoint}: HTTP {error.code}') from None


def iso_duration_seconds(value):
    m = re.fullmatch(r'P(?:([0-9]+)D)?T?(?:([0-9]+)H)?(?:([0-9]+)M)?(?:([0-9]+)S)?', value or '')
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def used_video_ids(limit=16):
    if not GHTOKEN or not REPO or '/' not in REPO:
        return set()
    req = urllib.request.Request(
        f'https://api.github.com/repos/{REPO}/actions/artifacts?per_page=100',
        headers={'Accept':'application/vnd.github+json', 'Authorization':'Bearer '+GHTOKEN,
                 'X-GitHub-Api-Version':'2022-11-28'})
    ids = set()
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            assets = json.load(resp).get('artifacts', [])
        matched = [a for a in assets if not a.get('expired') and a.get('name','').startswith('reshranks-ledger-')][:limit]
        for a in matched:
            req = urllib.request.Request(a['archive_download_url'], headers={'Authorization':'Bearer '+GHTOKEN,
                                               'Accept':'application/vnd.github+json'})
            with urllib.request.urlopen(req, timeout=25) as rr:
                raw = rr.read(250_000)
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                record = json.loads(zf.read('manifest.json'))
            for src in record.get('sources', []):
                if src.get('video_id'):
                    ids.add(src['video_id'])
    except Exception as exc:
        # Fail closed on network errors: otherwise repeated content may publish.
        raise RuntimeError(f'Cannot check ReshRanks history artifacts: {type(exc).__name__}') from exc
    return ids


def find_candidates(theme, excluded):
    hits = {}
    for term in theme['queries']:
        result = api('search', {'part':'snippet', 'type':'video', 'q':term,
                   'videoLicense':'creativeCommon', 'videoDuration':'short',
                   'maxResults':50, 'order':('date' if theme['queries'].index(term) == 1 else 'viewCount'), 'safeSearch':'strict'})
        for item in result.get('items', []):
            vid = item.get('id', {}).get('videoId')
            if vid and vid not in excluded:
                hits[vid] = item
    if not hits:
        return []
    videos = {}
    ids = list(hits)
    for i in range(0, len(ids), 50):
        data = api('videos', {'part':'snippet,status,contentDetails,statistics', 'id':','.join(ids[i:i+50])})
        for item in data.get('items', []):
            videos[item['id']] = item
    scored = []
    for vid, video in videos.items():
        status = video.get('status') or {}
        if status.get('license') != 'creativeCommon' or status.get('privacyStatus') != 'public':
            continue
        if (video.get('contentDetails') or {}).get('contentRating', {}).get('ytRating'):
            continue
        duration = iso_duration_seconds(video.get('contentDetails', {}).get('duration',''))
        if duration < 12 or duration > 240:
            continue
        snippet = video.get('snippet', {})
        title = snippet.get('title','')
        low = title.lower().replace('–','-').replace('—','-')
        if not any(word in low for word in theme['required']):
            continue
        if any(word in low for word in theme['reject']):
            continue
        if not snippet.get('channelTitle') or 'official audio' in low or 'music video' in low:
            continue
        views = int((video.get('statistics') or {}).get('viewCount','0'))
        # Consider engagement and ranking, but favor diverse and correctly labeled scenes.
        age=max(1,(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(snippet.get('publishedAt','2000-01-01T00:00:00Z').replace('Z','+00:00'))).days)
        views_per_day=views/age
        score = math.log1p(views) + 0.35*math.log1p(views_per_day) + (0.75 if 'sound' in low else 0) + (0.65 if 'exhaust' in low else 0)
        scored.append({'video_id':vid,'url':'https://www.youtube.com/watch?v='+vid,
            'title':title, 'channel':snippet['channelTitle'], 'channel_id':snippet.get('channelId',''),
            'published_at':snippet.get('publishedAt',''), 'duration':duration,
            'views':views,'score':score, 'rights':'cc_by_verified',
            'rights_evidence':'YouTube Data API status.license=creativeCommon checked at selection time'})
    scored.sort(key=lambda r: (-r['score'],r['video_id']))
    return scored


def run(cmd, timeout=190):
    subprocess.run(cmd, check=True, timeout=timeout, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE)


def audio_analysis(path, seconds=55):
    args=['ffmpeg','-hide_banner','-v','error','-i',str(path),'-t',str(seconds),
          '-map','0:a:0','-ac','1','-ar','8000','-f','s16le','pipe:1']
    try:
        pcm=subprocess.check_output(args,timeout=60,stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    if len(pcm)<8000*2*9: return None
    from array import array
    arr=array('h'); arr.frombytes(pcm[:len(pcm)//2*2])
    try:
        window=4000
        rms=[math.sqrt(sum(int(x)*int(x) for x in arr[i:i+window])/window)
             for i in range(0,len(arr)-window,window)]
        if len(rms)<18 or max(rms)<120: return None
        best=max(range(0,len(rms)-12), key=lambda k: sum(rms[k:k+12])/12)
        # Seek close to beginning of best sustained energetic part.
        start=max(0, best*0.5 - 0.5)
        peak=max(rms)
        return {'start':round(start,2),'energy':round(sum(rms[best:best+12])/12,2),'peak':round(peak,2)}
    except Exception:
        return None


def download_videos(candidates, work, wanted=5):
    selected=[]; used_channels=set()
    for i,c in enumerate(candidates[:40]):
        if c['channel_id'] and c['channel_id'] in used_channels:
            continue
        out=work/f'candidate_{i}.%(ext)s'
        cmd=['yt-dlp','--no-playlist','--no-progress','--no-warnings',
             '--socket-timeout','20','--retries','1','--fragment-retries','1',
             '--max-filesize','160M','-f','bv*[height<=1080]+ba/b[height<=1080]/b',
             '--merge-output-format','mp4','-o',str(out),c['url']]
        try:
            run(cmd,timeout=160)
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
            print('Skipping unavailable video:',c['video_id'],flush=True)
            continue
        matches=list(work.glob(f'candidate_{i}.*'))
        if len(matches)!=1: continue
        quality=audio_analysis(matches[0])
        if not quality:
            print('Skipping silent/unsuitable video:',c['video_id'],flush=True)
            matches[0].unlink(missing_ok=True)
            continue
        c=dict(c, **quality, file=str(matches[0].resolve()))
        selected.append(c)
        if c['channel_id']: used_channels.add(c['channel_id'])
        print('Selected:',c['video_id'], 'audio=',c['energy'],flush=True)
        if len(selected)>=wanted:break
    if len(selected)<wanted:
        raise RuntimeError(f'Only {len(selected)}/{wanted} usable licensed videos. No MP4 or upload will be created.')
    # The ranking is editorial; move the strongest sound near the climax.
    selected.sort(key=lambda s:s['energy'])
    return selected


def choose_title(video, theme):
    # No hallucinated bike models: prefer creator's own title, sanitized.
    title=re.sub(r'(?i)#\w+','',video['title'])
    title=re.sub(r'[^\w\s\-./]','',title).strip()
    title=re.sub(r'\s+',' ',title)
    return title[:42] if title else theme['key'].replace('_',' ').title()


def choose_theme():
    override = os.environ.get('RESH_THEME','').strip().lower()
    if override:
        m=next((t for t in THEMES if t['key']==override),None)
        if not m: raise ValueError('Unknown theme: '+override)
        return [m]
    # Rotate topics across runs; try backup themes if CC materials are unavailable.
    now=dt.datetime.now(dt.timezone.utc)
    day=now.timetuple().tm_yday
    start=(day*2+(1 if now.hour>=12 else 0))%len(THEMES)
    return THEMES[start:]+THEMES[:start]


def main():
    excluded=used_video_ids()
    failures=[]
    for theme in choose_theme():
        try:
            candidates=find_candidates(theme,excluded)
            if len(candidates)<5:
                raise RuntimeError('Insufficient YouTube videos with verified CC-BY label')
            found=download_videos(candidates,OUT)
            sources=[]
            for i,c in enumerate(found):
                sources.append({'rank':5-i,'name':choose_title(c,theme),'subtitle':'ORIGINAL ENGINE SOUND',
                    'url':c['url'], 'local_file':c['file'], 'start':c['start'],
                    'video_id':c['video_id'], 'channel':c['channel'], 'rights':'cc_by_verified',
                    'rights_evidence':c['rights_evidence'], 'energy':c['energy'],
                    'source_title':c['title'], 'attribution':c['url']})
            # Final rank #1 is the strongest selected sound (relative audio level only).
            payload={'topic':theme['name'], 'theme':theme['key'], 'sources':sources,
                'discovery_mode':'youtube_api_cc_by',
                'license_warning':'Creator-selected CC-BY is not a guarantee of rights to every element.'}
            file=OUT/'autodiscovered.json'
            file.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
            print('AUTODISCOVERY SUCCESS:',theme['key'], len(sources),flush=True)
            return
        except Exception as err:
            failures.append(f"{theme['key']}: {type(err).__name__} {str(err)[:140]}")
            print('Theme skipped:',failures[-1],flush=True)
    raise RuntimeError('No sufficiently licensed/downloadable coherent topic found. '+ ' | '.join(failures))

if __name__=='__main__':main()