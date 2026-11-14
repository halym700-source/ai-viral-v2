# Seven Channel Studio — Hybrid Free Render Layer

This layer adds a real MP4 render path to the existing content planner.

## What it does
- Accepts one channel ID and a Gemini scene package through GitHub Actions manual dispatch.
- Uses supplied per-scene `ai_video_url` clips when present.
- Otherwise searches Pixabay video footage when `PIXABAY_API_KEY` is configured.
- If no stock footage is available, creates a simple animated motion-graphics fallback with FFmpeg. This fallback is explicitly not represented as AI-generated footage.
- Generates English narration with the community `edge-tts` client when script text exists.
- Produces a 1080x1920 MP4 and metadata JSON as a downloadable Actions artifact.

## Channel-specific visual direction
The seven creative profiles remain separate in `config/channels.json`. Scene prompts should request:
- Apex Reveal Studio: cinematic vehicle detail and hero-reveal footage; AI clip preferred if a real AI video endpoint is separately connected.
- BrightBoard Academy: clean diagrams and whiteboard-style animated graphics.
- Creature Set Stories: original fictional creature visuals; AI-generated clips preferred where available, otherwise clearly illustrative stock/motion graphics.
- Built Through Time: period-appropriate stock and timeline motion graphics; verify factual dates.
- MicroDetail Garage: macro miniature-detailing visuals and natural sound; narration is omitted by default.
- TwistFrame Stories: consistent 2D stick-figure/vector animation; do not use unrelated stock footage as if it were the story.
- Inside the Line: manufacturing stock footage and process labels; never invent factory facts.

## Required setup
1. Add repository secret `PIXABAY_API_KEY` (optional; without it the renderer uses motion graphics fallback).
2. The Gemini key remains configured in n8n as before.
3. Trigger this workflow with `channel_id` and the complete scene package JSON.

## Honest free-tier boundary
This repository contains no magic unlimited AI video service. A true AI-generated video clip requires either a compatible self-hosted ComfyUI/video model endpoint with GPU access or a third-party provider's free quota. The renderer supports AI clips supplied in a scene as `ai_video_url`, but does not fabricate an AI generation result or silently call a paid service. On the iPhone-only setup, a self-hosted GPU model is not available locally; the automatic no-cost path is stock footage plus FFmpeg motion graphics and TTS.

## YouTube upload
The renderer deliberately does not upload to YouTube. Add and test a separate OAuth connection for each channel first. The first test remains Apex Reveal Studio only.
