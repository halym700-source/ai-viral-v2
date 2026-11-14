# n8n Cloud setup — Seven Channel Studio

This workflow is intentionally **inactive** when imported. It contains all seven channel profiles, but only Apex Reveal Studio is enabled for the first test.

## Import on n8n Cloud (iPhone)

1. Open your n8n workspace: https://halym700.app.n8n.cloud
2. Create a new workflow, open the workflow menu, and choose **Import from URL**.
3. Paste this raw workflow URL:
   https://raw.githubusercontent.com/halym700-source/ai-viral-v2/main/seven_channel_studio/n8n/seven_channel_master.json
4. Save the workflow. Do not activate it; it uses a Manual Trigger for the first test.

## Add the two credentials

The workflow now uses n8n credentials instead of environment variables. This avoids relying on `$env` access in n8n Cloud.

### A. Gemini API credential

1. Open the **Gemini - Generate Script & Scene Plan** node.
2. Under Authentication choose **Generic Credential Type** and select **Query Auth**.
3. Create a new Query Auth credential:
   - Name: `key`
   - Value: your Google AI Studio Gemini API key
4. Save the credential and select it in the node.

### B. GitHub token credential

1. Open the **Dispatch Free Hybrid MP4 Render** node.
2. Under Authentication choose **Generic Credential Type** and select **Header Auth**.
3. Create a new Header Auth credential:
   - Name: `Authorization`
   - Value: `Bearer YOUR_GITHUB_TOKEN` (replace with your token)
4. Create a fine-grained GitHub token restricted to `halym700-source/ai-viral-v2` and grant **Actions: Read and write**.
5. Save the credential and select it in the node.

Never paste either secret into the workflow's Code nodes or commit it to GitHub.

## Optional stock footage

For Pixabay stock clips, add a repository Actions secret named `PIXABAY_API_KEY`:
GitHub repository → Settings → Secrets and variables → Actions → New repository secret.

Without it, the renderer uses its own FFmpeg motion-graphics fallback. This is not AI-generated footage.

## First test boundaries

- Apex Reveal Studio is the only enabled channel.
- The other six profiles are included but disabled.
- The workflow generates a script/scene plan and dispatches the free hybrid MP4 renderer.
- The renderer can use Pixabay footage or motion graphics and Edge TTS narration.
- It does not yet complete YouTube upload or automatic publishing. Do not enable publishing until a private test and the remaining upload steps are implemented and checked.
