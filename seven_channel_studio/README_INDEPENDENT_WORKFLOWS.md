# Seven Channel Studio — Independent n8n Workflows

This folder contains seven independent n8n workflows. Each workflow has its own channel profile and channel-specific prompt logic. No workflow references another channel's profile.

## Workflows
- [Apex Reveal Studio](./workflows/apex_reveal_studio.json) — FIRST TEST WORKFLOW (only one marked active)
- [BrightBoard Academy](./workflows/brightboard_academy.json) — prepared, inactive
- [Creature Set Stories](./workflows/creature_set_stories.json) — prepared, inactive
- [Built Through Time](./workflows/built_through_time.json) — prepared, inactive
- [MicroDetail Garage](./workflows/microdetail_garage.json) — prepared, inactive
- [TwistFrame Stories](./workflows/twistframe_stories.json) — prepared, inactive
- [Inside the Line](./workflows/inside_the_line.json) — prepared, inactive

## Import
Import each JSON separately in n8n (Workflows → Import from File/URL). Set the `GEMINI_API_KEY` environment variable in n8n. The Gemini HTTP node uses Gemini 2.5 Flash.

## First test
Start with **Apex Reveal Studio** only. Its workflow is marked active; the other six are inactive. In the **Input - Topic & Settings** Code node, replace the empty topic with a specific topic, then run the workflow manually. Example: `A futuristic electric grand tourer reveal`.

## What is built
Each workflow has 12 nodes:
1. Manual test trigger
2. Input and settings
3. Topic validation
4. Independent channel profile
5. Creative brief
6. Gemini script and scene plan
7. Parse Gemini response
8. Validate script and scenes
9. Prepare scene-by-scene video prompts
10. Prepare narrator handoff
11. Prepare YouTube metadata/account handoff
12. Final production package

## Deliberate connection boundaries
- Video generation provider: **not connected**. Scene-by-scene image and image-to-video prompts are prepared.
- Narrator/TTS provider: **not connected**. English narration script and voice direction are prepared; MicroDetail Garage defaults to no narration.
- YouTube OAuth: **not connected**. Per-channel title, description and tags are prepared. Upload remains disabled and visibility is set to private as the intended first-test default.
- No workflow uploads or publishes anything.

## Important
The seven original full master prompts were not present in the retrievable prior files. The channel briefs here are carefully reconstructed from the available channel descriptions, not represented as recovered verbatim prompts. This version is a content-planning and production-handoff system, not yet an MP4 renderer or autopublisher. Actual end-to-end execution still requires a working Gemini key and subsequent video, voice and channel credentials.
