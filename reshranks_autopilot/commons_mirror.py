"""Fail-closed Wikimedia Commons mirror downloader for CC-BY YouTube videos.

Only use an archive whose file-page wikitext cites the EXACT YouTube video ID.
A YouTube CC license flag is not itself proof that all components are reusable.
"""
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request

UA = "ReshRanksBot/0.1 (Creative Commons research; media validation)"


def api(**params):
    args = dict(action="query", format="json", formatversion="2", **params)
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(args)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


def _metadata_value(meta, name):
    return str((meta.get(name) or {}).get("value") or "")


def _verified_page(video_id, title):
    result = api(prop="imageinfo|revisions", titles=title,
                 iiprop="url|size|mime|extmetadata", rvprop="content", rvslots="main")
    pages = result.get("query", {}).get("pages", [])
    for page in pages:
        raw = ((page.get("revisions") or [{}])[0].get("slots") or {}).get("main", {}).get("content", "")
        raw = str(raw)
        # Avoid accepting a different work merely because it mentions the requested ID.
        if video_id not in raw or not re.search(r'youtube|youtu\.be', raw, re.I):
            continue
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        file_url = str(info.get("url") or "")
        parsed = urllib.parse.urlparse(file_url)
        if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
            continue
        mime = str(info.get("mime") or "")
        if mime not in ("video/webm", "video/ogg", "video/mp4"):
            continue
        size = int(info.get("size") or 0)
        if size < 100_000 or size > 90_000_000:
            continue
        meta = info.get("extmetadata") or {}
        license_name = re.sub(r"<[^>]+>", "", _metadata_value(meta, "LicenseShortName"))
        license_url = re.sub(r"<[^>]+>", "", _metadata_value(meta, "LicenseUrl"))
        if not re.search(r"\bCC\s*BY\s*(?:3\.0|4\.0)\b", license_name, re.I):
            continue
        if not license_url.startswith("https://creativecommons.org/licenses/by/"):
            continue
        return {
            "url": file_url, "size": size, "mime": mime,
            "license": license_name, "license_url": license_url,
            "archive_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "title": title
        }
    return None


def _probe_av(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)], timeout=22)
    streams = json.loads(out)["streams"]
    return (any(s.get("codec_type") == "video" for s in streams) and
            any(s.get("codec_type") == "audio" for s in streams))


def find_youtube_archive(video_id):
    if not re.fullmatch(r"[-_A-Za-z0-9]{11}", video_id):
        raise ValueError("Invalid YouTube video ID")
    data = api(list="search", srsearch=video_id, srnamespace="6", srlimit="10")
    for hit in data.get("query", {}).get("search", []):
        title = hit.get("title") or ""
        if not title.startswith("File:"):
            continue
        try:
            verified = _verified_page(video_id, title)
            if verified:
                return verified
        except Exception as exc:
            print("Commons metadata skipped:", type(exc).__name__, flush=True)
    return None


def download_youtube_cc_archive(video_id, destination):
    """Return (download_path, source_metadata), or None when not available."""
    item = find_youtube_archive(video_id)
    if not item:
        return None
    extension = {"video/webm": ".webm", "video/ogg": ".ogv", "video/mp4": ".mp4"}[item["mime"]]
    out = Path(str(destination) + extension)
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(item["url"], headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as inp, out.open("wb") as dest:
            if urllib.parse.urlparse(inp.geturl()).hostname != "upload.wikimedia.org":
                raise ValueError("Unexpected media redirect")
            count = 0
            while True:
                block = inp.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                if count > 90_000_000:
                    raise ValueError("Archive exceeds size cap")
                dest.write(block)
        if not _probe_av(out):
            raise ValueError("Archive does not contain both video and original audio")
    except Exception:
        out.unlink(missing_ok=True)
        raise
    return out, item
