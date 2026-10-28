/**
 * GET /api/system-info
 * Proxies to upstream backend and enriches with NLLB API status.
 */
import { NextResponse } from "next/server";
import { proxyToBackend } from "../_nllb";

export const runtime = "nodejs";
export const maxDuration = 15;

export async function GET() {
  const hfTokenSet = Boolean(process.env.HF_TOKEN);

  try {
    const upstream = await proxyToBackend("/system-info", { method: "GET" });
    const data = await upstream.json();
    return NextResponse.json({
      ...data,
      nllb_inference_api: hfTokenSet,
      vercel_api_route:   true,
    });
  } catch {
    return NextResponse.json({
      nllb_inference_api: hfTokenSet,
      vercel_api_route:   true,
      backend_available:  false,
    }, { status: 200 });
  }
}
