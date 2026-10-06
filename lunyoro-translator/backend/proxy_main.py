"""
proxy_main.py
=============
Thin FastAPI proxy that runs on the HF Space (cpu-basic, free) and
forwards every request to the Colab backend (NLLB on T4 GPU).

How it works:
  1. Colab opens a cloudflared tunnel and posts the URL to the HF Space
     secret COLAB_URL via the HF API.
  2. This proxy reads COLAB_URL at startup and on every request (so a
     tunnel URL change takes effect within REFRESH_INTERVAL seconds).
  3. Every incoming request is forwarded to {COLAB_URL}{path} with the
     same method, headers, body and query string.
  4. If Colab is unreachable (timeout / tunnel down), the proxy falls back
     to the local Marian translation path so the Space is never fully dead.

Environment variables (set as HF Space secrets):
  COLAB_URL          — set automatically by the Colab notebook
  COLAB_TIMEOUT      — per-request timeout in seconds (default: 25)
  REFRESH_INTERVAL   — how often to re-read COLAB_URL from HF secrets (default: 60s)
  HF_TOKEN           — used to read the COLAB_URL secret value at runtime
  DISABLE_MARIAN     — set to 0 to keep Marian as fallback (default: 0)
  CORS_ORIGINS       — comma-separated allowed origins
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import threading
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [proxy] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("proxy")

# ── Config ─────────────────────────────────────────────────────────────────────
COLAB_TIMEOUT    = int(os.getenv("COLAB_TIMEOUT", "25"))
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "60"))   # seconds
HF_TOKEN         = os.getenv("HF_TOKEN", "")
HF_SPACE_ID      = os.getenv("HF_SPACE_ID", "keithtwesigye/runyoro-translator-api")

# Paths that should NEVER be forwarded to Colab (served locally)
LOCAL_PATHS = {"/health", "/ping", "/system-info", "/docs", "/openapi.json", "/redoc"}

# ── State ──────────────────────────────────────────────────────────────────────
_colab_url: str = os.getenv("COLAB_URL", "").rstrip("/")
_last_refresh: float = 0.0
_colab_healthy: bool = False   # updated by background health-check thread
_state_lock = threading.Lock()


def _fetch_colab_url_from_secret() -> str:
    """Read COLAB_URL from the HF Space secrets API (so it picks up Colab restarts)."""
    if not HF_TOKEN:
        return ""
    try:
        import requests as _req
        r = _req.get(
            f"https://huggingface.co/api/spaces/{HF_SPACE_ID}/secrets",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            timeout=8,
        )
        if r.status_code == 200:
            secrets = r.json()
            # Secrets API only returns key names for security — we can't read the value
            # COLAB_URL must be set in the container env by HF from secrets at startup
            pass
    except Exception as e:
        logger.debug("Could not fetch secrets: %s", e)
    return ""


def _get_colab_url() -> str:
    """Return the current Colab tunnel URL, refreshed from env every REFRESH_INTERVAL."""
    global _colab_url, _last_refresh
    now = time.monotonic()
    with _state_lock:
        if now - _last_refresh > REFRESH_INTERVAL:
            _last_refresh = now
            # Re-read from environment — HF Space injects secret as env var at container start.
            # When Colab restarts and updates the secret, the Space restarts too (triggered by
            # Cell 5 of the Colab notebook), so the new value IS in the env on restart.
            fresh = os.getenv("COLAB_URL", "").rstrip("/")
            if fresh and fresh != _colab_url:
                logger.info("COLAB_URL updated: %s", fresh)
                _colab_url = fresh
        return _colab_url


def _health_check_loop():
    """Background thread: probe Colab /ping every 30s, update _colab_healthy."""
    global _colab_healthy
    while True:
        url = _get_colab_url()
        if url:
            try:
                r = httpx.get(f"{url}/ping", timeout=8)
                healthy = r.status_code == 200
            except Exception:
                healthy = False
        else:
            healthy = False
        with _state_lock:
            _colab_healthy = healthy
        if not healthy and url:
            logger.warning("Colab backend unreachable — falling back to local Marian")
        time.sleep(30)


# Start health-check thread
threading.Thread(target=_health_check_loop, daemon=True, name="colab-health").start()

# ── Fallback: local Marian (runs when Colab is down) ──────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from translate import translate as _local_translate, translate_to_english as _local_reverse
    _marian_available = True
    logger.info("Local Marian loaded as fallback")
except Exception as _e:
    _marian_available = False
    logger.warning("Local Marian not available: %s", _e)

# Load models in background
def _load_fallback():
    if not _marian_available:
        return
    try:
        from translate import _load_mt
        _load_mt("en2lun")
        _load_mt("lun2en")
        logger.info("Fallback Marian models loaded")
    except Exception as e:
        logger.warning("Fallback load failed: %s", e)

threading.Thread(target=_load_fallback, daemon=True, name="fallback-load").start()

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Stick Proxy", description="Forwards requests to Colab NLLB backend")

_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "https://frontend-six-phi-25.vercel.app,https://horizonx.kathay.tech,"
    "https://runyoro-rutooro-translator.vercel.app,http://localhost:3002"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _raw_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Local endpoints (always served here) ─────────────────────────────────────
@app.get("/health")
def health():
    colab_url = _get_colab_url()
    with _state_lock:
        healthy = _colab_healthy
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "colab_url": colab_url or None,
        "colab_healthy": healthy,
        "marian_fallback": _marian_available,
        "proxy_mode": True,
    }


@app.get("/ping")
def ping():
    return {"pong": True, "timestamp": datetime.utcnow().isoformat()}


@app.get("/system-info")
def system_info():
    colab_url = _get_colab_url()
    with _state_lock:
        healthy = _colab_healthy
    # Try to fetch live system-info from Colab
    if colab_url and healthy:
        try:
            r = httpx.get(f"{colab_url}/system-info", timeout=8)
            if r.status_code == 200:
                data = r.json()
                data["proxy_mode"] = True
                data["colab_url"] = colab_url
                return data
        except Exception:
            pass
    # Fallback: show proxy status
    return {
        "marian_en2lun": _marian_available,
        "marian_lun2en": _marian_available,
        "marian_onnx": False,
        "nllb_en2lun": healthy,
        "nllb_lun2en": healthy,
        "nllb_disabled": not healthy,
        "gpu_available": healthy,   # Colab has GPU
        "gpu_count": 1 if healthy else 0,
        "proxy_mode": True,
        "colab_url": colab_url or None,
        "colab_healthy": healthy,
    }


# ── Fallback translate endpoints (when Colab is down) ────────────────────────
def _fallback_translate(text: str, context: str = "") -> dict:
    if not _marian_available:
        return {"translation": text, "method": "passthrough", "confidence": 0}
    try:
        return _local_translate(text, context=context)
    except Exception as e:
        logger.error("Fallback translate error: %s", e)
        return {"translation": text, "method": "error", "confidence": 0}


def _fallback_reverse(text: str, context: str = "") -> dict:
    if not _marian_available:
        return {"translation": text, "method": "passthrough", "confidence": 0}
    try:
        return _local_reverse(text, context=context)
    except Exception as e:
        logger.error("Fallback reverse error: %s", e)
        return {"translation": text, "method": "error", "confidence": 0}


# ── Universal proxy handler ────────────────────────────────────────────────────
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy(path: str, request: Request):
    """Forward every request to the Colab backend. Fall back to Marian on failure."""
    colab_url = _get_colab_url()
    with _state_lock:
        healthy = _colab_healthy

    # ── Forward to Colab ──────────────────────────────────────────────────────
    if colab_url and healthy:
        target_url = f"{colab_url}/{path}"
        if request.url.query:
            target_url += f"?{request.url.query}"
        try:
            body = await request.body()
            async with httpx.AsyncClient(timeout=COLAB_TIMEOUT) as client:
                resp = await client.request(
                    method=request.method,
                    url=target_url,
                    headers={
                        k: v for k, v in request.headers.items()
                        if k.lower() not in ("host", "content-length")
                    },
                    content=body,
                )
            logger.debug("Proxied %s /%s → %s", request.method, path, resp.status_code)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )
        except httpx.TimeoutException:
            logger.warning("Colab timeout on /%s — using fallback", path)
        except Exception as e:
            logger.warning("Colab error on /%s: %s — using fallback", path, e)

    # ── Fallback: handle translate/translate-reverse locally with Marian ──────
    if path in ("translate", "translate-reverse"):
        try:
            body_json = await request.json()
        except Exception:
            body_json = {}
        text    = body_json.get("text", "")
        context = body_json.get("context", "")
        if not text.strip():
            return JSONResponse({"error": "text cannot be empty"}, status_code=400)
        if path == "translate":
            result = _fallback_translate(text, context)
        else:
            result = _fallback_reverse(text, context)
        result["fallback"] = True
        result["colab_url"] = colab_url or None
        return JSONResponse(result)

    # ── For all other paths with no Colab and no local fallback ──────────────
    return JSONResponse(
        {
            "error": "Colab backend unavailable",
            "colab_url": colab_url or None,
            "colab_healthy": False,
            "tip": "Run the Colab notebook: lunyoro-translator/colab/nllb_backend.ipynb",
        },
        status_code=503,
    )
