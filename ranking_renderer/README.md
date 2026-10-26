# Ranking Shorts — independent from TextVibe Stories

Inspired by PolarRanks' five-to-one ranking *format*, but not its branding or third-party copyrighted footage.

Output: 5 licensed or self-owned clips ranked #5 to #1, 4.8 seconds each (24 seconds total), 720 x 1280 vertical MP4. Includes one English neural voice introduction at the beginning, original clip audio where present, large rankings, text and progress display.

## Automatic pipeline

The new gated pipeline is in `.github/workflows/ranking_auto_pipeline.yml`. It defaults to five explicitly approved authentic viral clips from `approved_sources.json`, renders a 24-second preview, and can upload PRIVATE review drafts to a separately authorized YouTube channel after one-time credential and schedule setup. See [AUTO_SETUP.md](AUTO_SETUP.md). Automatic publishing is **disabled by default**.

## Run

Find five clips that permit redistribution and YouTube monetization; ensure their embedded audio/music is also covered. Fill the source page and actual license in the JSON manifest. The placeholder URLs in example_manifest.json are NOT real assets.

Go to GitHub Actions > Ranking Shorts Renderer > Run workflow. Enter unique job_id and paste the complete manifest JSON into manifest_json. Download the output artifact when rendering finishes.

Alternatively, call the GitHub workflow_dispatch API from an independent n8n workflow. The renderer deliberately does not publish to YouTube or touch the existing TextVibe n8n process. A new channel must first be created and authorized separately.

The separate Ranking Shorts Smoke Test generates its own synthetic sample clips. Its intro tone is only a test placeholder; actual jobs use an Edge TTS English spoken intro, subject to voice service availability. Real stock clips might have no audio. Source and license details are saved with the video artifact.

Scheduling: every other day (one upload day, one rest day), beginning on a configured first-publication date. Choose and confirm a publication hour in the schedule config before enabling uploads. All uploads stay PRIVATE until reviewed by the owner. Use `ranking_renderer/schedule_guard.py` and `ranking_renderer/schedule_config.json`; the default hour and first-date fields are null and fail closed. TextVibe's separate channel and timetable remain unchanged.

Important: There is no blanket 5-15 second copyright exception. Merely numbering snippets and adding an intro does not guarantee rights, monetization, or adherence to reused-content policy. Review original editorial contribution before uploading.


## Real viral footage research and permissions (ReshRanks)

- GitHub Actions **ReshRanks Viral Research** runs daily after `YOUTUBE_RESEARCH_API_KEY` is set. It researches YouTube candidates via the official API and creates `viral_research.csv` and `rights_review_queue.csv` artifacts. It does **not** download videos, prove authenticity, or confer rights.
- Review the original camera footage and secure explicit reuse rights from each creator or rights holder. Review embedded music/audio separately. A YouTube URL alone is **not** permission or a direct MP4 URL.
- For five approved clips, fill `ranking_renderer/approved_sources.json` with title, intro, and five entries. Each entry needs rank 5..1, label, source_page, approved_mp4_url (an authorized direct MP4), permission_evidence_url, rights_basis (original_owner, creator_permission, commercial_license or pexels_license), rights_holder, reviewer, reviewed_at, authenticity_reviewed=true and rights_reviewed=true. These are audit attestations and must be truthful.
- Run GitHub Actions **ReshRanks Approved Real Footage Preview** to generate the 24-second MP4. It fails safely if there are fewer than five verified entries or if rights evidence is missing. It never uploads to YouTube.
- The automated pipeline defaults to `approved_real_viral`. A `licensed_stock_demo` choice exists for manually requested previews only; it cannot publish. Scheduled runs cannot silently switch to stock footage.
- No generative visuals or AI-created video are permitted. Text, voiceover, ranking layout and cuts may be automated. Research cannot prove that a clip is real from metadata alone.
- Automatic upload remains disabled until channel authorization, a confirmed schedule and user approval. Even once enabled, uploads are PRIVATE for review.
