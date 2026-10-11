/**
 * Lunyoro-Rutooro Translator — Cloudflare Worker
 * ================================================
 * Routing priority:
 *   1. Colab T4 (COLAB_URL secret) — live when notebook is running
 *   2. HF Space (HF_SPACE_URL var)  — permanent fallback
 *
 * Special endpoints (handled by Worker, not proxied):
 *   GET  /health            — liveness, reports which backend is active
 *   GET  /ping              — keep-alive
 *   POST /update-colab-url  — called by Colab notebook to register its tunnel URL
 *   GET  /colab-status      — returns current COLAB_URL (for debugging)
 *
 * All other requests are proxied to Colab (if live) or HF Space.
 *
 * Secrets  (set with: npx wrangler secret put <NAME>)
 *   HF_TOKEN        — HuggingFace token
 *   COLAB_URL       — set automatically by the notebook via POST /update-colab-url
 *   WORKER_SECRET   — shared secret so only the notebook can update COLAB_URL
 *
 * Variables (wrangler.jsonc → vars)
 *   HF_USERNAME, HF_CHAT_MODEL, CORS_ORIGINS, HF_SPACE_URL
 */

export interface Env {
  // Secrets
  HF_TOKEN:       string;
  COLAB_URL:      string;   // *.trycloudflare.com — updated each Colab session
  WORKER_SECRET:  string;   // shared secret for /update-colab-url
  // KV namespace for persisting COLAB_URL across Worker restarts
  COLAB_KV?: KVNamespace;
  // Variables
  HF_USERNAME:   string;
  HF_CHAT_MODEL: string;
  CORS_ORIGINS:  string;
  HF_SPACE_URL:  string;
}

// ── CORS ──────────────────────────────────────────────────────────────────────
function corsHeaders(env: Env, origin: string | null): Record<string, string> {
  const allowed = (env.CORS_ORIGINS ?? "").split(",").map(o => o.trim()).filter(Boolean);
  const o = origin && allowed.includes(origin) ? origin : (allowed[0] ?? "*");
  return {
    "Access-Control-Allow-Origin":  o,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Worker-Secret",
    "Access-Control-Max-Age":       "86400",
  };
}

function json(data: unknown, status = 200, cors: Record<string,string> = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...cors },
  });
}

// ── Resolve which backend URL to use ─────────────────────────────────────────
async function resolveBackend(env: Env): Promise<{ url: string; source: "colab" | "hfspace" }> {
  // KV takes priority (updated by /update-colab-url), then the secret binding
  const kvUrl = env.COLAB_KV ? await env.COLAB_KV.get("COLAB_URL") : null;
  const colabUrl = (kvUrl || env.COLAB_URL || "").trim().replace(/\/$/, "");
  const hfUrl    = (env.HF_SPACE_URL || "https://keithtwesigye-runyoro-translator-api.hf.space")
                     .trim().replace(/\/$/, "");

  if (colabUrl) {
    // Quick liveness probe — 4 s timeout so we don't delay the user
    try {
      const probe = await fetch(`${colabUrl}/ping`, {
        signal: AbortSignal.timeout(4000),
      });
      if (probe.ok) return { url: colabUrl, source: "colab" };
    } catch {
      // Colab session timed out — fall through to HF Space
    }
  }

  return { url: hfUrl, source: "hfspace" };
}

// ── Main handler ──────────────────────────────────────────────────────────────
export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url    = new URL(req.url);
    const path   = url.pathname;
    const origin = req.headers.get("Origin");
    const cors   = corsHeaders(env, origin);

    // Preflight
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    // ── /ping ────────────────────────────────────────────────────────────────
    if (path === "/ping" && req.method === "GET") {
      return json({ pong: true, ts: new Date().toISOString() }, 200, cors);
    }

    // ── /health ──────────────────────────────────────────────────────────────
    if (path === "/health" && req.method === "GET") {
      const { url: backendUrl, source } = await resolveBackend(env);
      return json({
        status: "ok",
        backend: source,
        backend_url: backendUrl,
        ts: new Date().toISOString(),
        worker: true,
      }, 200, cors);
    }

    // ── /colab-status ────────────────────────────────────────────────────────
    if (path === "/colab-status" && req.method === "GET") {
      const kvUrl    = env.COLAB_KV ? await env.COLAB_KV.get("COLAB_URL") : null;
      const colabUrl = (kvUrl || env.COLAB_URL || "").trim();
      return json({ colab_url: colabUrl || null, has_colab: Boolean(colabUrl) }, 200, cors);
    }

    // ── /update-colab-url — called by Colab notebook ─────────────────────────
    if (path === "/update-colab-url" && req.method === "POST") {
      // Verify shared secret
      const secret = req.headers.get("X-Worker-Secret") ?? "";
      if (env.WORKER_SECRET && secret !== env.WORKER_SECRET) {
        return json({ error: "Unauthorized" }, 401, cors);
      }

      let body: { url?: string } = {};
      try { body = await req.json(); } catch { /* ignore */ }

      const newUrl = (body.url ?? "").trim().replace(/\/$/, "");
      if (!newUrl || !newUrl.startsWith("https://")) {
        return json({ error: "Invalid URL — must be https://" }, 400, cors);
      }

      // Persist in KV if available, otherwise just acknowledge
      if (env.COLAB_KV) {
        // TTL: 14 hours (Colab free sessions max ~12h)
        await env.COLAB_KV.put("COLAB_URL", newUrl, { expirationTtl: 14 * 3600 });
      }

      console.log(`[update-colab-url] set to ${newUrl}`);
      return json({ status: "ok", colab_url: newUrl }, 200, cors);
    }

    // ── Proxy everything else ─────────────────────────────────────────────────
    const { url: backendUrl, source } = await resolveBackend(env);
    const targetUrl = `${backendUrl}${path}${url.search}`;

    try {
      const proxyHeaders = new Headers(req.headers);
      proxyHeaders.delete("host");
      proxyHeaders.delete("cf-connecting-ip");
      proxyHeaders.delete("cf-ray");
      proxyHeaders.delete("cf-visitor");
      proxyHeaders.delete("x-forwarded-for");
      proxyHeaders.delete("x-forwarded-proto");

      const body = req.method !== "GET" && req.method !== "HEAD"
        ? await req.arrayBuffer()
        : undefined;

      const resp = await fetch(targetUrl, {
        method:  req.method,
        headers: proxyHeaders,
        body,
        signal:  AbortSignal.timeout(60000),
      });

      const respHeaders = new Headers(resp.headers);
      for (const [k, v] of Object.entries(cors)) respHeaders.set(k, v);
      respHeaders.set("X-Backend-Source", source);
      respHeaders.delete("content-encoding");
      respHeaders.delete("transfer-encoding");

      return new Response(resp.body, { status: resp.status, headers: respHeaders });

    } catch (e) {
      return json({
        error:   "Backend unreachable",
        backend: source,
        target:  targetUrl,
        detail:  String(e),
        tip:     source === "colab"
          ? "Colab session may have ended — notebook needs to be re-run."
          : "HF Space may be loading models — try again in 30s.",
      }, 503, cors);
    }
  },
} satisfies ExportedHandler<Env>;
