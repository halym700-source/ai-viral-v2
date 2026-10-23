# AI Viral V2 — EN & TR fictional chat Shorts

Two independent n8n JSON workflows:
- [English](workflows/CHAT_SHORTS_ENGLISH_N8N.json)
- [Turkish](workflows/CHAT_SHORTS_TURKCE_N8N.json)

The workflows use Gemini to invent original dialogues, and dispatch the same
[GitHub Actions renderer](.github/workflows/chat_video_render.yml). Rendering
produces a 720x1280 MP4 with distinct role-based voices, timed chat bubbles,
and sequential messages. Both workflows fetch their own MP4 artifact and upload
using separate YouTube OAuth credentials.

## REQUIRED SETUP (in n8n Cloud; iPhone works)
1. Import each JSON as a **new workflow**; leave both **unpublished** initially.
2. In each workflow, select a working **Gemini API Header Auth** credential
   for its '03 Gemini dialogue' HTTP Request node.
3. Create a **fine-grained GitHub PAT** limited to this repo, with
   **Actions: Read and Write** (dispatch and download artifacts).
   In n8n, create **Header Auth** with
   **Name** `Authorization` and **Value** `Bearer github_pat_...`.
   Select this credential for the GitHub HTTP Request nodes (06, 08 and 12).
   NEVER add the PAT to the public GitHub repo or JSON.
4. Select the *correct, separate* Google/YouTube OAuth account for the
   '15 Upload to YouTube' node in EACH language workflow.
5. Check cron times and workflow timezone `Europe/Istanbul`.
   English default 12:15/19:15, Turkish 12:45/19:45.
6. In the n8n YouTube Upload node, default visibility is **private** so you
   can verify account ownership, voices, sound, timing and originality before
   enabling public publishing.
7. Run a SINGLE manual test after credentials are ready; GitHub Actions may
   take minutes. Check GitHub Actions if the renderer times out/fails.
8. ONLY after confirming a successful test, change both Upload nodes from
   `private` to `public` if you want fully public automated uploads;
   then Publish each workflow.

## Costs and limitations
- No fal.ai / paid generative video clips. Renders graphics programmatically
  on GitHub Actions; consumes applicable GitHub Actions quotas and n8n usage.
- Gemini API may incur charges/limits.
- `edge-tts` is an **unofficial** client for a third-party online speech
  service. It is NOT guaranteed always free or reliable, and any commercial
  rights/terms must be checked independently. This is a **prototype**, not
  a guaranteed zero-cost monetizable production service.
- 30–45 sec is a writing target, not a hard runtime guarantee. Actual
  durations depend on the TTS speech; renderer rejects >60 sec.
- Each YouTube channel must be a separate channel/account OAuth selection.
- The workflows are templates NOT activated on the user's n8n instance.
- GitHub artifacts expire after 2 days; the n8n workflow downloads
  immediately within the same run.
- YouTube reused-content policy: dialogues are original fictional text.
  No other creator's video/visuals are copied.

## Security
No tokens are committed to the repository. Avoid sharing execution
records containing dialogue if privacy matters. For older GitHub Actions
repositories, workflow_dispatch must be enabled under the Actions tab.
