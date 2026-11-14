# Seven Channel Studio (AI Viral V2 add-on)

This folder adds a separate seven-channel English YouTube content-planning workflow to the existing repository. It does not modify legacy workflows.

## The seven allowed channels
- **Apex Reveal Studio** — Cinematic automotive reveals
- **BrightBoard Academy** — Whiteboard educational explainers
- **Creature Set Stories** — AI creature concepts and fictional behind-the-scenes VFX stories
- **Built Through Time** — Company, brand and technology history explainers
- **MicroDetail Garage** — Miniature car cleaning and restoration ASMR
- **TwistFrame Stories** — 2D stickman adventures with unexpected endings
- **Inside the Line** — Factory and manufacturing documentaries

## Files
- `config/channels.json`: channel-specific format, voice direction, visual brief and story structure.
- `n8n/seven_channel_studio.json`: importable n8n webhook workflow. It validates the channel, asks Gemini 2.5 Flash for an English content package, and validates the JSON response.

## Import and test
1. Import `n8n/seven_channel_studio.json` into n8n.
2. Set environment variable `GEMINI_API_KEY` on the n8n instance (or replace the expression with your own n8n credential).
3. Activate the workflow and copy its Production Webhook URL.
4. POST JSON such as:

```json
{
  "channel_id": "apex_reveal_studio",
  "topic": "A futuristic electric grand tourer reveal"
}
```

Allowed IDs: apex_reveal_studio, brightboard_academy, creature_set_stories, built_through_time, microdetail_garage, twistframe_stories, inside_the_line.

## Important status boundary
This is a **content-planning workflow**, not a completed end-to-end autopublisher. It produces an English script, title, description, tags, scene prompts and voice direction. It does **not** yet generate video/image assets, synthesize synchronized voice audio, render an MP4, or upload to YouTube. Those stages need a selected media/TTS provider and a tested per-channel YouTube OAuth connection. No fake success status is returned.

## Prompt provenance
The retrievable prior-chat record contained the seven channel names and creative formats, but not the complete original master prompts. The channel briefs in `channels.json` are explicitly marked as reconstructions, not represented as the user's verbatim originals.
