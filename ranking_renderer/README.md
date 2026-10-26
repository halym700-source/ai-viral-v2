# Ranking Shorts — independent from TextVibe Stories

Inspired by PolarRanks' five-to-one ranking *format*, but not its branding or third-party copyrighted footage.

Output: 5 licensed or self-owned clips ranked #5 to #1, 4.8 seconds each (24 seconds total), 720 x 1280 vertical MP4. Includes one English neural voice introduction at the beginning, original clip audio where present, large rankings, text and progress display.

## Run

Find five clips that permit redistribution and YouTube monetization; ensure their embedded audio/music is also covered. Fill the source page and actual license in the JSON manifest. The placeholder URLs in example_manifest.json are NOT real assets.

Go to GitHub Actions > Ranking Shorts Renderer > Run workflow. Enter unique job_id and paste the complete manifest JSON into manifest_json. Download the output artifact when rendering finishes.

Alternatively, call the GitHub workflow_dispatch API from an independent n8n workflow. The renderer deliberately does not publish to YouTube or touch the existing TextVibe n8n process. A new channel must first be created and authorized separately.

The separate Ranking Shorts Smoke Test generates its own synthetic sample clips. Its intro tone is only a test placeholder; actual jobs use an Edge TTS English spoken intro, subject to voice service availability. Real stock clips might have no audio. Source and license details are saved with the video artifact.

Scheduling: every other day (one upload day, one rest day), beginning on a configured first-publication date. Exact posting hour must be verified from Polar Ranks' public publishedAt timestamps before enabling publishing. Use `ranking_renderer/schedule_guard.py` and `ranking_renderer/schedule_config.json`; the default hour and first-date fields are null and fail closed. TextVibe's separate channel and timetable remain unchanged.\n\nImportant: There is no blanket 5-15 second copyright exception. Merely numbering snippets and adding an intro does not guarantee rights, monetization, or adherence to reused-content policy. Review original editorial contribution before uploading.
