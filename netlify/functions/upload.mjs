import { getStore } from "@netlify/blobs";

const CHUNK_BYTES = 4 * 1024 * 1024;
const JOB_STORE = "kesit-jobs";
const CHUNK_STORE = "kesit-upload-chunks";
const REPO = "halym700-source/ai-viral-v2";
const WORKFLOW = "openshorts_free.yml";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json", "access-control-allow-origin": "*" }
  });
}

function stores() {
  return {
    jobs: getStore({ name: JOB_STORE, region: "eu-central-1" }),
    chunks: getStore({ name: CHUNK_STORE, region: "eu-central-1" })
  };
}

export default async (req) => {
  const url = new URL(req.url);
  const { jobs, chunks } = stores();

  if (req.method === "OPTIONS") {
    return new Response("", {
      status: 204,
      headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET,POST,OPTIONS",
        "access-control-allow-headers": "content-type,x-upload-id,x-chunk-index"
      }
    });
  }

  if (req.method === "POST" && url.searchParams.get("action") === "init") {
    const body = await req.json();
    const id = crypto.randomUUID();
    const job = {
      id,
      filename: String(body.filename || "video.mp4").slice(0, 200),
      size: Number(body.size || 0),
      chunks: Number(body.chunks || 0),
      clipCount: Number(body.clipCount || 3),
      layout: ["auto", "center", "webcam-top"].includes(body.layout) ? body.layout : "auto",
      subtitleStyle: ["bold", "classic", "yellow", "minimal"].includes(body.subtitleStyle) ? body.subtitleStyle : "bold",
      youtubeUrl: typeof body.youtubeUrl === "string" ? body.youtubeUrl.slice(0, 1000) : "",
      status: "uploading",
      createdAt: new Date().toISOString()
    };
    await jobs.setJSON(id, job);
    return json({ ok: true, uploadId: id, chunkSize: CHUNK_BYTES });
  }

  if (req.method === "POST" && url.searchParams.get("action") === "chunk") {
    const id = req.headers.get("x-upload-id");
    const index = Number(req.headers.get("x-chunk-index"));
    if (!id || !Number.isInteger(index) || index < 0) return json({ error: "Invalid chunk" }, 400);
    const data = await req.arrayBuffer();
    if (data.byteLength > CHUNK_BYTES + 1024) return json({ error: "Chunk too large" }, 413);
    await chunks.set(id + "/" + index, data);
    return json({ ok: true, index });
  }

  if (req.method === "POST" && url.searchParams.get("action") === "finish") {
    const id = url.searchParams.get("id");
    if (!id) return json({ error: "Missing upload id" }, 400);
    const job = await jobs.get(id, { type: "json" });
    if (!job) return json({ error: "Job not found" }, 404);

    const token = process.env.GITHUB_ACTIONS_TOKEN || (typeof Netlify !== "undefined" && Netlify.env ? Netlify.env.get("GITHUB_ACTIONS_TOKEN") : "");
    if (!token) {
      await jobs.setJSON(id, { ...job, status: "waiting-for-token" });
      return json({
        error: "GITHUB_ACTIONS_TOKEN is not configured in Netlify.",
        uploadId: id
      }, 500);
    }

    const origin = url.origin;
    const sourceUrl = origin + "/.netlify/functions/upload?action=download&id=" + encodeURIComponent(id);
    const response = await fetch("https://api.github.com/repos/" + REPO + "/actions/workflows/" + WORKFLOW + "/dispatches", {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2026-03-10",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        ref: "main",
        inputs: {
          source_url: job.youtubeUrl ? "" : sourceUrl,
          youtube_url: job.youtubeUrl || "",
          upload_id: id,
          chunk_count: String(job.chunks),
          filename: job.filename,
          clip_count: String(job.clipCount),
          layout: job.layout,
          subtitle_style: job.subtitleStyle
        }
      })
    });

    if (!response.ok) {
      const detail = await response.text();
      await jobs.setJSON(id, { ...job, status: "dispatch-error", error: detail.slice(0, 500) });
      return json({ error: "GitHub Actions başlatılamadı.", detail: detail.slice(0, 500) }, 502);
    }

    await jobs.setJSON(id, { ...job, status: "processing", sourceUrl, dispatchedAt: new Date().toISOString() });
    return json({ ok: true, uploadId: id, status: "processing" });
  }

  if (req.method === "GET" && url.searchParams.get("action") === "status") {
    const id = url.searchParams.get("id");
    if (!id) return json({ error: "Missing id" }, 400);
    const job = await jobs.get(id, { type: "json" });
    return job ? json(job) : json({ error: "Not found" }, 404);
  }

  if (req.method === "GET" && url.searchParams.get("action") === "download") {
    const id = url.searchParams.get("id");
    const index = Number(url.searchParams.get("chunk"));
    const job = id ? await jobs.get(id, { type: "json" }) : null;
    if (!job) return new Response("Not found", { status: 404 });
    if (!Number.isInteger(index) || index < 0 || index >= job.chunks) return new Response("Invalid chunk", { status: 400 });
    const data = await chunks.get(id + "/" + index, { type: "arrayBuffer" });
    if (!data) return new Response("Chunk not found", { status: 404 });
    return new Response(data, {
      headers: {
        "content-type": "application/octet-stream",
        "content-length": String(data.byteLength),
        "cache-control": "no-store"
      }
    });
  }

  return json({ error: "Not found" }, 404);
};
