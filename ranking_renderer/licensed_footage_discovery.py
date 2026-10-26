#!/usr/bin/env python3
"""Discover candidate real-world videos with Commons license metadata.

This is a RESEARCH queue, not permission, camera-authenticity or MP4 approval.
Never download, publish or set rights_reviewed=True based on this output.
"""
import csv
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ReshRanksResearch/1.0 (https://github.com/halym700-source/ai-viral-v2; metadata-only)"
SEARCHES = (
    "funny cat filetype:video",
    "funny dog filetype:video",
    "animal playing filetype:video",
    "skateboarding filetype:video",
    "sports trick filetype:video",
    "unexpected moment filetype:video",
)
ALLOWED_LICENSES = {"cc0", "cc-by", "cc-by-sa", "public domain", "pd"}
REJECT_WORDS = ("ai-generated", "ai generated", "synthetic", "deepfake", "animation",
                "animated", "cartoon", "rendered", "cgi", "simulation", "video game")
FIELDS = (
    "topic", "title", "file_page", "media_url", "mime", "license_name",
    "license_url", "creator_credit", "license_metadata_status",
    "camera_authenticity_status", "rights_verification_status",
    "video_format_note", "review_notes"
)

def plain(value):
    raw = value.get("value", "") if isinstance(value, dict) else (value or "")
    return html.unescape(re.sub(r"<[^>]+>", " ", str(raw))).strip()[:400]

def license_candidate(name, url):
    norm = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if norm.startswith("cc-by-sa"):
        kind = "cc-by-sa"
    elif norm.startswith("cc-by"):
        kind = "cc-by"
    elif norm.startswith("cc0") or norm == "cc-zero":
        kind = "cc0"
    elif norm in ("public-domain", "pd", "pd-old", "pd-us"):
        kind = "public domain"
    else:
        return False
    # Reject non-commercial / no-derivatives licenses and require source link.
    if any(x in norm for x in ("-nc", "-nd")):
        return False
    return bool(url and url.startswith("https://") and kind in ALLOWED_LICENSES)

def request_json(params):
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(API + "?" + query, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json"
    })
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)

def search(topic, limit=15):
    data = request_json({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": topic, "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|mime|mediatype|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit|Attribution|UsageTerms",
        "iiextmetadatalanguage": "en",
    })
    return data.get("query", {}).get("pages", {}).values()

def candidate(page, topic):
    title = page.get("title", "")
    if any(word in title.lower() for word in REJECT_WORDS):
        return None
    info = next(iter(page.get("imageinfo", [])), {})
    media = info.get("url", "")
    mime = info.get("mime", "")
    if not (mime.startswith("video/") and media.startswith("https://")):
        return None
    meta = info.get("extmetadata", {})
    license_name = plain(meta.get("LicenseShortName"))
    license_url = plain(meta.get("LicenseUrl"))
    if not license_candidate(license_name, license_url):
        return None
    credit = plain(meta.get("Attribution") or meta.get("Artist") or meta.get("Credit"))
    file_page = info.get("descriptionurl", "")
    if not file_page.startswith("https://"):
        return None
    mp4 = urllib.parse.urlsplit(media).path.lower().endswith(".mp4")
    return {
        "topic": topic, "title": title, "file_page": file_page,
        "media_url": media, "mime": mime,
        "license_name": license_name, "license_url": license_url,
        "creator_credit": credit,
        "license_metadata_status": "OPEN_LICENSE_CANDIDATE_REVIEW_REQUIRED",
        "camera_authenticity_status": "UNVERIFIED",
        "rights_verification_status": "REVIEW_REQUIRED",
        "video_format_note": "MP4_DIRECT" if mp4 else "TRANSCODE_REQUIRED_AFTER_APPROVAL",
        "review_notes": "Review file history, creator, embedded rights, people/music, license conditions and actual camera footage before approval.",
    }

def discover():
    found, errors = {}, []
    for topic in SEARCHES:
        try:
            for page in search(topic):
                item = candidate(page, topic)
                if item:
                    found.setdefault(item["file_page"], item)
        except Exception as exc:
            errors.append({"topic": topic, "error_type": type(exc).__name__})
    return list(found.values())[:50], errors

def main():
    rows, errors = discover()
    out = Path("out")
    out.mkdir(parents=True, exist_ok=True)
    with (out / "licensed_real_footage_candidates.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out / "licensed_real_footage_candidates.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Wikimedia Commons metadata search",
        "disclaimer": "NOT verified as real camera footage or cleared for reuse. Manual file-page and rights review required. No files downloaded.",
        "candidates": rows, "query_errors": errors,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"open_license_metadata_candidates": len(rows),
                      "query_errors": errors, "approval": "NONE",
                      "next": "manual camera authenticity, attribution, ownership and usage-rights review"}))

if __name__ == "__main__":
    main()
