# Ranking Shorts — automation setup (separate channel)

The GitHub pipeline is at `.github/workflows/ranking_auto_pipeline.yml`. It does **not** modify the existing TextVibe or AI Viral V2 workflows.

## What is ready
- Automatic topic rotation across six English action/sports ranking themes.
- Pexels API source selection: five distinct portrait MP4s, source page and Pexels license record.
- 24-second (5 x 4.8s) vertical edit, five-to-one ranking graphics, English voice only at the beginning, and clip audio if present.
- GitHub Actions hourly schedule with an alternate-day release guard, an upload receipt, and a publication ledger.
- YouTube OAuth upload with an explicit destination-channel ID check, PRIVATE visibility for the owner's review and source attribution.
- Manual preview workflow that renders without publishing.

## One-time owner configuration
1. Create the **new** YouTube channel, distinct from TextVibe Stories, and copy its canonical channel ID (starts with UC).
2. Obtain a Pexels API key from the Pexels developer dashboard. In GitHub repository **Settings > Secrets and variables > Actions > Secrets**, add `PEXELS_API_KEY`.
3. In Google Cloud, enable **YouTube Data API v3** and create an OAuth consent screen and OAuth client. Authorize **the new channel**, not TextVibe, with scopes `https://www.googleapis.com/auth/youtube.upload` and `https://www.googleapis.com/auth/youtube.readonly`. Generate a refresh token using your own local secure OAuth flow. Store `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` as GitHub Actions secrets. **Never put these credentials in GitHub code or chat.**
4. Under **Settings > Secrets and variables > Actions > Variables**, set `RANKING_YOUTUBE_CHANNEL_ID` to the new channel ID.
5. In **Actions > Ranking Shorts Auto Pipeline > Run workflow**, choose `preview`. Download the `ranking-preview-...` artifact and inspect the footage, voice, rights and source record. Pexels clips may be silent; music/audio rights need separate checks.
6. Verify the desired publication hour from reliable source timestamps. Edit `ranking_renderer/schedule_config.json`: set `first_publication_date` (YYYY-MM-DD), `publication_time_local` (HH:MM in Europe/Istanbul), and `auto_publish_enabled` to `true` **only after** a successful preview, valid credentials, and confirmed channel ID. The schedule is every two days. GitHub Actions hourly runs can be delayed; uploads may happen up to 70 minutes after the configured hour.
7. GitHub scheduled runs will then produce and upload videos as PRIVATE drafts on due dates. The owner reviews each draft in YouTube Studio and manually changes visibility to Public when satisfied. Receipts are stored in the Actions artifacts and `ranking_renderer/published_days.json`.

## Safety and limitations
- The default `auto_publish_enabled: false` deliberately prevents unreviewed uploads.
- Source videos are **licensed stock**, not verified viral videos. They are not copied from Polar Ranks. Avoid claiming original audio exists when stock footage is silent.
- Pexels licensing is not a blanket music/soundtrack license. Check each clip and platform reuse policies before enabling publication. YouTube reused-content monetization is not guaranteed by overlays and rankings alone.
- GitHub scheduled runs are not real-time. A job can be delayed or skipped; the ledger reduces duplicate publishing but cannot guarantee exactly-once behavior if an upload succeeds and recording its receipt fails.
- GitHub Actions execution, YouTube API quotas and Pexels rate limits are subject to their providers' policies and account limits.
- Upload requires the correct channel and OAuth credentials; this cannot be set by a repository code change.

## Publishing policy

The user requires PRIVATE-first review. Do not automatically change visibility to Public. All scheduled uploads stay private until the channel owner reviews them in YouTube Studio. Do not enable the release guard before Pexels and OAuth checks are green and the destination channel is verified.
