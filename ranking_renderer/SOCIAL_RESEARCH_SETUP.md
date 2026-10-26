# ReshRanks: four-platform research pipeline

GitHub Actions: `.github/workflows/ranking_viral_research.yml`
Run manually with **ReshRanks Viral Research > Run workflow** or allow its daily schedule.

## What works

- **YouTube Shorts:** official YouTube Data API; ranks popular video research leads by views and views/day. Requires existing `YOUTUBE_RESEARCH_API_KEY` secret.
- **Instagram Reels:** optional official Instagram Graph API hashtag research, requiring an Instagram Professional account, appropriate app permissions/review, `INSTAGRAM_ACCESS_TOKEN` GitHub secret and `INSTAGRAM_USER_ID` Actions variable.
- **X:** optional official recent-post search API for video posts, requiring `X_BEARER_TOKEN` GitHub secret and an X API plan that supports recent search.
- **TikTok:** creator-discovery search links by topic, **not an automated public video search feed**. TikTok's Research API is limited to approved noncommercial research and is not a commercial content-aggregation API.

Every run writes `out/multiplatform_research.json` and `out/multiplatform_research.csv` in the Actions artifact, with connection statuses. A missing credential does not break the entire research run.

## What does not work yet

Research results contain source post URLs and popularity data, **not downloadable footage**. Public availability does not authorize reuploading, and a title alone cannot verify camera origin. The separate ranking video renderer currently requires five approved real footage MP4 URLs and rights/source evidence via `ranking_renderer/approved_sources.json`. It will not auto-download arbitrary TikTok, Instagram, YouTube, or X posts. Wikimedia preview mode has been removed from the active ranking video workflow.

A completed research run is **not** a finished YouTube video and does not publish to the channel.

## Secrets and variables

In GitHub > Settings > Secrets and variables > Actions:

- Existing secret: `YOUTUBE_RESEARCH_API_KEY`
- Optional secret: `INSTAGRAM_ACCESS_TOKEN`
- Optional variable: `INSTAGRAM_USER_ID`
- Optional secret: `X_BEARER_TOKEN`

Never commit access tokens to the repository. TikTok does not need an access token for the creator-search link queue.
