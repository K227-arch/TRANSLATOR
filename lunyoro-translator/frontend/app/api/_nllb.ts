/**
 * Server-side NLLB inference via HuggingFace Inference API.
 * Called from Next.js Route Handlers — HF_TOKEN never exposed to the client.
 *
 * Models: keithtwesigye/lunyoro-nllb-en2lun  (English → Runyoro)
 *         keithtwesigye/lunyoro-nllb-lun2en  (Runyoro → English)
 */

const HF_TOKEN   = process.env.HF_TOKEN ?? "";
const HF_USERNAME = process.env.HF_USERNAME ?? "keithtwesigye";

// Upstream Python backend — Cloudflare Worker → HF Space
const BACKEND_URL = process.env.BACKEND_URL
  ?? "https://lunyoro-translator-api.keithtwesigye74.workers.dev";

const NLLB_REPOS: Record<string, string> = {
  en2lun: `${HF_USERNAME}/lunyoro-nllb-en2lun`,
  lun2en: `${HF_USERNAME}/lunyoro-nllb-lun2en`,
};

const NLLB_LANGS: Record<string, { src: string; tgt: string }> = {
  en2lun: { src: "eng_Latn", tgt: "run_Latn" },
  lun2en: { src: "run_Latn", tgt: "eng_Latn" },
};

/** Call HF Inference API for NLLB translation. Returns null on failure. */
export async function nllbInfer(
  text: string,
  direction: "en2lun" | "lun2en"
): Promise<string | null> {
  if (!HF_TOKEN) return null;

  const repo = NLLB_REPOS[direction];
  const { src, tgt } = NLLB_LANGS[direction];

  const payload = {
    inputs: text,
    parameters: {
      src_lang: src,
      tgt_lang: tgt,
      num_beams: 6,
      max_length: 512,
      no_repeat_ngram_size: 3,
    },
  };

  const headers = {
    Authorization: `Bearer ${HF_TOKEN}`,
    "Content-Type": "application/json",
  };

  // Try both endpoints — router endpoint is faster inside HF infra
  const endpoints = [
    `https://router.huggingface.co/hf-inference/models/${repo}`,
    `https://api-inference.huggingface.co/models/${repo}`,
  ];

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(20_000),
      });

      // 503 = model warming up — wait and retry once
      if (res.status === 503) {
        await new Promise(r => setTimeout(r, 8_000));
        const retry = await fetch(url, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(30_000),
        });
        if (!retry.ok) continue;
        const data = await retry.json();
        const result = extractTranslation(data);
        if (result) return result;
        continue;
      }

      if (!res.ok) continue;
      const data = await res.json();
      const result = extractTranslation(data);
      if (result) return result;
    } catch {
      continue;
    }
  }
  return null;
}

function extractTranslation(data: unknown): string | null {
  if (Array.isArray(data) && data.length > 0) {
    return (data[0] as Record<string, string>).translation_text?.trim() || null;
  }
  if (data && typeof data === "object") {
    return ((data as Record<string, string>).translation_text ?? "").trim() || null;
  }
  return null;
}

/** Proxy a request to the upstream backend (Worker → HF Space). */
export async function proxyToBackend(
  path: string,
  init: RequestInit
): Promise<Response> {
  const url = `${BACKEND_URL}${path}`;
  return fetch(url, {
    ...init,
    signal: AbortSignal.timeout(45_000),
  });
}
