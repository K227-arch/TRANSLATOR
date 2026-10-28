/**
 * POST /api/translate-reverse  — Runyoro/Rutooro → English
 *
 * Strategy (in order):
 *   1. HF Space backend directly — NLLB is kept warm by the 20-min warmup ping
 *   2. HF Inference API fallback — if the Space is sleeping/restarting
 *   3. Cloudflare Worker proxy — Marian + RAG fallback
 */
import { NextRequest, NextResponse } from "next/server";
import { nllbInfer, proxyToBackend } from "../_nllb";

export const runtime = "nodejs";
export const maxDuration = 90;

const HF_SPACE_URL = process.env.HF_SPACE_URL
  ?? "https://keithtwesigye-runyoro-translator-api.hf.space";

export async function POST(req: NextRequest) {
  let body: { text?: string; context?: string } = {};
  try { body = await req.json(); } catch { /* ignore */ }

  const text = (body.text ?? "").trim();
  if (!text) {
    return NextResponse.json({ error: "text is required" }, { status: 400 });
  }

  // ── 1. HF Space — NLLB warm in memory ────────────────────────────────────
  try {
    const spaceRes = await fetch(`${HF_SPACE_URL}/translate-reverse`, {
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

  // ── 2. HF Inference API fallback ─────────────────────────────────────────
  const nllbResult = await nllbInfer(text, "lun2en");
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

  // ── 3. Cloudflare Worker proxy ───────────────────────────────────────────
  try {
    const upstream = await proxyToBackend("/translate-reverse", {
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
