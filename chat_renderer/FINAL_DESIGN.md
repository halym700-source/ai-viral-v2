# TextVibeStories — Final Video Design

**Approved design:** 2026-10-31  
**Status:** Final baseline for future English Shorts renders (and shared renderer).

This file records the user's approved template. The production renderer is
`chat_renderer/reference_layout.py`, called from `chat_renderer/render.py`.
The n8n-driven GitHub workflow is `.github/workflows/chat_video_render.yml`.

## Locked visual elements

1. **Canvas:** 720 × 1280, vertical 9:16 YouTube Shorts; black top/bottom bands.
2. **Chat frame:** Soft cream, rounded corners, a familiar minimal messenger header.
3. **Main character:** The same 22-year-old young male illustrated portrait in the **bottom-right** on every video. It must never be recycled as another role.
4. **Other characters:** No oversized illustration in the chat area. Instead a **small circular contact profile photograph** in the **top-left header**, selected by the story's speaker role (mom/dad/grandparents/siblings/girlfriend etc.).
5. **Messages:** White incoming bubbles and pale-green outgoing bubbles, appearing in sequence and synchronized to the speech.
6. **Wallpaper:** A **photographic chat background**, selected anew for each rendering job. The photo is gently muted so chat messages remain readable. The chosen photo remains fixed *within* the video (no flicker).
7. **Audio:** Retain existing role-based speech pipeline. No change to narration providers or YouTube upload nodes.

## Variation and quality

- `chat_renderer/photo_wallpapers.py` selects a photo and a per-job crop.
- `CHAT_JOB_ID` is passed from n8n as a unique per-video job id via GitHub Actions.
- Each production video keeps one wallpaper throughout. Different jobs are given different selections/crops; the finite photo catalogue does not guarantee that no source photo will ever repeat.
- If all image sources are unavailable, fail the render rather than silently publishing a plain-color background.
- Source-photo licensing information is recorded in the render's `out/wallpaper_source.json`.
- Keep a private render smoke test and verify visual changes before publishing any design revision.

## Approval

The user confirmed that this final design is correct and requested it to be finalized.
Do not adjust the main-character position, contact-photo format or rotating
wallpaper system without a new explicit design request.

## Operational boundary

The GitHub main-branch renderer and dispatch workflow are configured for this
design. Whether a separate live n8n instance is currently active/published,
and whether its channel credentials are correctly configured, cannot be
inferred from GitHub files alone.
