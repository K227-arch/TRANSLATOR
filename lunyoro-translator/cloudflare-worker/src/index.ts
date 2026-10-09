/**
 * Lunyoro-Rutooro Translator — Cloudflare Worker
 * ================================================
 * Pulls fine-tuned NLLB-200 models directly from HuggingFace Inference API
 * and exposes the same REST surface as the Python backend.
 *
 * Endpoints implemented:
 *   GET  /health          — liveness check
 *   GET  /ping            — keep-alive
 *   GET  /system-info     — model status
 *   POST /translate       — English → Runyoro (NLLB via HF API)
 *   POST /translate-reverse — Runyoro → English (NLLB via HF API)
 *   POST /chat            — LLM chat via HF Router
 *   POST /lookup          — dictionary word lookup (static data)
 *   POST /feedback        — save user feedback (logs it, future: KV store)
 *   GET  /history         — translation history (KV-backed, future)
 *
 * HF model repos used:
 *   keithtwesigye/lunyoro-nllb-en2lun  — English → Runyoro NLLB-200
 *   keithtwesigye/lunyoro-nllb-lun2en  — Runyoro → English NLLB-200
 *
 * Secrets (set with wrangler secret put):
 *   HF_TOKEN       — HuggingFace write token
 *
 * Variables (in wrangler.jsonc):
 *   HF_USERNAME, HF_CHAT_MODEL, CORS_ORIGINS
 */

export interface Env {
  // Secrets
  HF_TOKEN: string;
  // Variables
  HF_USERNAME:    string;
  HF_CHAT_MODEL:  string;
  CORS_ORIGINS:   string;
  // The HF Space URL to proxy to (set as a var so it can change without redeploy)
  HF_SPACE_URL:   string;
}

// ── HuggingFace Inference API endpoints ────────────────────────────────────
const HF_ROUTER   = "https://router.huggingface.co/hf-inference/models";
const HF_FALLBACK = "https://api-inference.huggingface.co/models";

// NLLB language codes
const LANG_EN  = "eng_Latn";
const LANG_LUN = "run_Latn";  // Rundi proxy for Runyoro-Rutooro

// ── NLLB translation via HF Inference API ──────────────────────────────────
async function nllbTranslate(
  text: string,
  direction: "en2lun" | "lun2en",
  hfToken: string,
  hfUsername: string
): Promise<string | null> {
  const repoId = `${hfUsername}/lunyoro-nllb-${direction}`;
  const srcLang = direction === "en2lun" ? LANG_EN : LANG_LUN;
  const tgtLang = direction === "en2lun" ? LANG_LUN : LANG_EN;

  const payload = {
    inputs: text.trim(),
    parameters: {
      src_lang: srcLang,
      tgt_lang: tgtLang,
      num_beams: 5,
      max_length: 512,
      no_repeat_ngram_size: 3,
    },
  };

  const headers: Record<string, string> = {
    "Authorization": `Bearer ${hfToken}`,
    "Content-Type":  "application/json",
  };

  // Try router first (works inside HF infra + free), then fallback
  for (const base of [HF_ROUTER, HF_FALLBACK]) {
    const url = `${base}/${repoId}`;
    try {
      let resp = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      // 503 = model cold-starting — wait and retry once
      if (resp.status === 503) {
        await new Promise(r => setTimeout(r, 8000));
        resp = await fetch(url, { method: "POST", headers, body: JSON.stringify(payload) });
      }

      if (resp.status === 200) {
        const data = await resp.json() as Array<{ translation_text?: string }> | { translation_text?: string };
        const result = Array.isArray(data) ? data[0]?.translation_text : data.translation_text;
        if (result?.trim()) {
          // Strip language-code prefix artifacts (e.g. "run_Latn: ...")
          return result.replace(/^[a-z_]+_[A-Z][a-z]+:\s*/g, "").trim();
        }
      }
    } catch {
      // Try next endpoint
      continue;
    }
  }
  return null;
}

// ── LLM chat via HF Router ─────────────────────────────────────────────────
async function llmChat(
  messages: Array<{ role: string; content: string }>,
  hfToken: string,
  model: string
): Promise<string | null> {
  try {
    const resp = await fetch("https://router.huggingface.co/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${hfToken}`,
        "Content-Type":  "application/json",
      },
      body: JSON.stringify({ model, messages, max_tokens: 600, temperature: 0.6 }),
    });
    if (resp.status === 200) {
      const data = await resp.json() as { choices: Array<{ message: { content: string } }> };
      return data.choices[0]?.message?.content?.trim() ?? null;
    }
  } catch { /* fall through */ }
  return null;
}

// ── CORS helpers ───────────────────────────────────────────────────────────
function corsHeaders(env: Env, reqOrigin: string | null): Record<string, string> {
  const allowed = env.CORS_ORIGINS.split(",").map(o => o.trim());
  const origin = reqOrigin && allowed.includes(reqOrigin) ? reqOrigin : allowed[0] ?? "*";
  return {
    "Access-Control-Allow-Origin":  origin ?? "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age":       "86400",
  };
}

function json(data: unknown, status = 200, cors: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...cors },
  });
}

// ── Main handler ───────────────────────────────────────────────────────────
export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url    = new URL(req.url);
    const path   = url.pathname;
    const origin = req.headers.get("Origin");
    const cors   = corsHeaders(env, origin);
    const space  = (env.HF_SPACE_URL || "https://keithtwesigye-runyoro-translator-api.hf.space").replace(/\/$/, "");

    // Handle CORS preflight
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    // ── Local endpoints — always served by the Worker ─────────────────────
    if (path === "/health" && req.method === "GET") {
      return json({ status: "ok", timestamp: new Date().toISOString(), worker: true, space }, 200, cors);
    }
    if (path === "/ping" && req.method === "GET") {
      return json({ pong: true, timestamp: new Date().toISOString() }, 200, cors);
    }

    // ── Debug endpoint ────────────────────────────────────────────────────
    if (path === "/debug-hf" && req.method === "GET") {
      // Test that the HF Space is reachable
      try {
        const r = await fetch(`${space}/health`, { signal: AbortSignal.timeout(8000) });
        return json({ space, space_status: r.status, worker: true }, 200, cors);
      } catch (e) {
        return json({ space, space_error: String(e), worker: true }, 200, cors);
      }
    }

    // ── Proxy everything else to the HF Space ─────────────────────────────
    const targetUrl = `${space}${path}${url.search}`;
    try {
      const proxyHeaders = new Headers(req.headers);
      // Remove headers that cause issues
      proxyHeaders.delete("host");
      proxyHeaders.delete("cf-connecting-ip");
      proxyHeaders.delete("cf-ray");
      proxyHeaders.delete("cf-visitor");
      proxyHeaders.delete("x-forwarded-for");
      proxyHeaders.delete("x-forwarded-proto");

      const body = req.method !== "GET" && req.method !== "HEAD" ? await req.arrayBuffer() : undefined;

      const resp = await fetch(targetUrl, {
        method:  req.method,
        headers: proxyHeaders,
        body,
        signal:  AbortSignal.timeout(30000),
      });

      // Copy response headers, add CORS
      const respHeaders = new Headers(resp.headers);
      for (const [k, v] of Object.entries(cors)) respHeaders.set(k, v);
      // Remove encoding headers that would cause issues
      respHeaders.delete("content-encoding");
      respHeaders.delete("transfer-encoding");

      return new Response(resp.body, {
        status:  resp.status,
        headers: respHeaders,
      });

    } catch (e) {
      // Space is down — return a clear error with the space URL
      return json({
        error:   "HF Space unreachable",
        space,
        detail:  String(e),
        tip:     "The HF Space may be loading models. Try again in 30s.",
      }, 503, cors);
    }
  },
} satisfies ExportedHandler<Env>;
