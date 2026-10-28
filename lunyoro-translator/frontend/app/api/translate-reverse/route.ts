/**
 * POST /api/translate-reverse  — Runyoro/Rutooro → English
 *
 * Same strategy as /api/translate:
 *   1. NLLB via HF Inference API (server-side)
 *   2. Fallback to upstream backend
 */
import { NextRequest, NextResponse } from "next/server";
import { nllbInfer, proxyToBackend } from "../_nllb";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: NextRequest) {
  let body: { text?: string; context?: string } = {};
  try { body = await req.json(); } catch { /* ignore */ }

  const text = (body.text ?? "").trim();
  if (!text) {
    return NextResponse.json({ error: "text is required" }, { status: 400 });
  }

  // ── 1. NLLB via HF Inference API ─────────────────────────────────────────
  const nllbResult = await nllbInfer(text, "lun2en");

  if (nllbResult) {
    return NextResponse.json({
      translation:        nllbResult,
      translation_nllb:   nllbResult,
      translation_marian: null,
      method:             "nllb_inference_api",
      confidence:         1.0,
      alternatives:       [],
      source:             "vercel_api_route",
    });
  }

  // ── 2. Fallback: proxy to upstream backend ────────────────────────────────
  try {
    const upstream = await proxyToBackend("/translate-reverse", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    const data = await upstream.json();
    return NextResponse.json({ ...data, source: "upstream_backend" }, {
      status: upstream.status,
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Translation service unavailable", detail: String(e) },
      { status: 503 }
    );
  }
}
