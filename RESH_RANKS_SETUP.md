# ReshRanks: YouTube URLs -> 24-second Ranking -> Dropbox

**Status: SETUP REQUIRED.** Renderer was smoke-tested locally on synthetic clips. Real YouTube downloads, GitHub Actions execution, and n8n/Dropbox integration are NOT yet verified end-to-end. The n8n workflow is disabled by default and starts manually.

## What it does
- Accepts exactly five videos in ranking order #5 -> #1.
- Attempts YouTube downloads using yt-dlp; accepts public direct MP4 URLs.
- Stops on download failure, missing audio, insufficient duration, or missing reuse-rights evidence.
- Renders 24 seconds: 1.75s hook + four 3.8s clips + 7.05s #1 finale.
- Adds animated-looking static typography/numbering and transparent @reshranks watermark, retaining source audio.
- Stores MP4 and rights manifest in GitHub Actions artifact.
- n8n downloads artifact ZIP, extracts MP4, and uploads it to Dropbox if configured.
- Does NOT automatically upload to YouTube.

## iPhone setup
1. In n8n Cloud (halym700.app.n8n.cloud), choose Workflows > Import from File, then import workflows/RESH_RANKS_YOUTUBE_TO_SHORTS_N8N.json.
2. In GitHub HTTP Request nodes 03, 05, and 10, select a GitHub Header Auth credential with repository Actions permissions. Never paste secret tokens in code.
3. Connect Dropbox OAuth credentials in the n8n Dropbox upload node 14. Your ChatGPT Dropbox connection does not transfer to n8n.
4. Edit node 01: five video links and correct labels/timestamps. Set each source rights to owned, permission, or cc_by_verified ONLY if supported, with a nonempty rights_evidence field.
5. Run one manual test. On success MP4 is uploaded into your Dropbox root. Review the final file; do not automatically publish before you verify the result.
6. For failed downloads inspect GitHub Actions > ReshRanks Video Downloader + 24s Renderer job logs.

## Important limitations
- YouTube may block automated downloading and this pipeline cannot guarantee every URL succeeds. No bypass of login/PO-token or other access restrictions is included.
- Copyright reuse permission must be assessed; a license label alone does not guarantee all third-party visual/audio rights.
- The discovery stage (automatically finding and reviewing new links) is not connected. The current workflow processes five links you enter.
- GitHub Actions uses FFmpeg and Pillow on Ubuntu. Output is 720x1280 at 30 fps to control runtime.
- This pipeline is not live until the n8n workflow has been imported, credentials connected and a successful test run completed.

## Files
- .github/workflows/reshranks_render.yml
- reshranks_renderer/render.py
- workflows/RESH_RANKS_YOUTUBE_TO_SHORTS_N8N.json
