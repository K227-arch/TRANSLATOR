/**
 * POST /api/translate  — English → Runyoro/Rutooro
 *
 * Strategy (in order):
 *   1. HF Space backend directly — NLLB is kept warm by the 20-min warmup ping
 *      in main.py, so this returns NLLB results with no cold-start delay
 *   2. HF Inference API fallback — if the Space is sleeping/restarting
 */
import { NextRequest, NextResponse } from "next/server";
import { nllbInfer, proxyToBackend } from "../_nllb";

export const runtime = "nodejs";
export const maxDuration = 90;

const HF_SPACE_URL = process.env.HF_SPACE_URL
  ?? "https://keithtwesigye-runyoro-translator-api.hf.space";

export async function POST(req: NextRequest) {
  let body: { text?: string; context?: string; direction?: string } = {};
  try { body = await req.json(); } catch { /* ignore */ }

  const text = (body.text ?? "").trim();
  if (!text) {
    return NextResponse.json({ error: "text is required" }, { status: 400 });
  }

  // ── 1. HF Space — NLLB is kept warm in memory by the warmup ping ─────────
  try {
    const spaceRes = await fetch(`${HF_SPACE_URL}/translate`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(45_000),
    });
    if (spaceRes.ok) {
      const data = await spaceRes.json();
      return NextResponse.json({ ...data, source: "hf_space_nllb" });
    }
  } catch { /* space sleeping — fall through */ }

  // ── 2. HF Inference API fallback (cold-start, ~30–60s on first call) ─────
  const nllbResult = await nllbInfer(text, "en2lun");
  if (nllbResult) {
    return NextResponse.json({
      translation:        nllbResult,
      translation_nllb:   nllbResult,
      translation_marian: null,
      method:             "nllb_inference_api",
      confidence:         1.0,
      alternatives:       [],
      source:             "hf_inference_api",
    });
  }

  // ── 3. Cloudflare Worker proxy (Marian + RAG fallback) ───────────────────
  try {
    const upstream = await proxyToBackend("/translate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    const data = await upstream.json();
    return NextResponse.json({ ...data, source: "worker_fallback" }, {
      status: upstream.status,
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Translation service unavailable", detail: String(e) },
      { status: 503 }
    );
  }
}
