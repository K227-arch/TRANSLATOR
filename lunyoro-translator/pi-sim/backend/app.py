"""
pi-sim backend — app.py
========================
Virtual Raspberry Pi 5 AI Stick backend.

Runs NLLB-200 INT8 ONNX only (MarianMT removed).
Greedy decode, two ORT sessions (encoder + decoder), no KV cache —
mirrors translator_v2.cpp and verify_pi_models.py exactly.

Environment variables (all optional):
  MODEL_DIR      path to model root          (default: /models)
  NLLB_INT8_DIR  NLLB INT8 dir template      (default: nllb_{d}_int8)
  NLLB_ONNX_DIR  NLLB FP32 fallback template (default: nllb_{d}_onnx)
  NLLB_THREADS   ORT intra-op threads        (default: 4)
  CORS_ORIGINS   comma-separated origins     (default: localhost variants)
  HISTORY_FILE   path to history JSON        (default: /tmp/pisim/history.json)
  LOG_LEVEL      python log level            (default: INFO)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoTokenizer

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pi-sim")

# ── Path config ────────────────────────────────────────────────────────────────
MODEL_DIR   = Path(os.getenv("MODEL_DIR",   "/models"))
BACKEND_DIR = Path(os.getenv("BACKEND_DIR", "/backend"))

NLLB_INT8_TEMPLATE = os.getenv("NLLB_INT8_DIR", "nllb_{d}_int8")
NLLB_ONNX_TEMPLATE = os.getenv("NLLB_ONNX_DIR", "nllb_{d}_onnx")

NLLB_THREADS = int(os.getenv("NLLB_THREADS", "4"))

HISTORY_FILE  = Path(os.getenv("HISTORY_FILE", "/tmp/pisim/history.json"))
_history_lock = threading.Lock()

# ── NLLB language codes ────────────────────────────────────────────────────────
NLLB_LANG_EN  = "eng_Latn"
# The INT8 ONNX models use run_Latn (Rundi proxy) as the effective Runyoro token.
# nyo_Latn (ID 256205) is the custom fine-tuning token used by the FP32 PyTorch model,
# but INT8 quantization distorts its embedding (it's at the tail of the matrix, custom-added).
# run_Latn produces correct Runyoro output from the INT8 ONNX models — verified empirically.
# model_config.json in a model dir can still override this per-model if needed.
NLLB_LANG_LUN = "run_Latn"

MAX_LENGTH_NLLB = 200

# ── Model state ────────────────────────────────────────────────────────────────
_nllb_sessions: dict[str, dict] = {}   # keyed "en2lun" / "lun2en"
_nllb_ready   = {"en2lun": False, "lun2en": False}

# ── Retrieval helpers (from real backend) ─────────────────────────────────────
_retrieval_available = False


def _setup_backend_path():
    bp = str(BACKEND_DIR)
    if bp not in sys.path:
        sys.path.insert(0, bp)


def _init_retrieval():
    global _retrieval_available
    _setup_backend_path()
    try:
        import translate as _t
        _t._load_retrieval()
        _retrieval_available = True
        logger.info("Retrieval index loaded from %s", BACKEND_DIR)
    except Exception as e:
        logger.warning("Retrieval index unavailable: %s — lookup/spellcheck empty", e)


# ── Post/pre-processing helpers ────────────────────────────────────────────────
def _postprocess_lunyoro(text: str) -> str:
    try:
        _setup_backend_path()
        from translate import _postprocess_lunyoro as _pp
        return _pp(text)
    except Exception:
        return text


def _postprocess_english(text: str) -> str:
    try:
        _setup_backend_path()
        from translate import _postprocess_english as _ppe
        return _ppe(text)
    except Exception:
        return text


def _preprocess_lunyoro(text: str) -> str:
    try:
        _setup_backend_path()
        from translate import _preprocess_lunyoro_input as _pre
        return _pre(text)
    except Exception:
        return text


def _is_garbage(text: str) -> bool:
    """Detect degenerate repetitive output."""
    if not text:
        return True
    words = text.split()
    if len(words) >= 5:
        from collections import Counter
        freq = Counter(w.lower() for w in words)
        _, top_count = freq.most_common(1)[0]
        if top_count / len(words) > 0.4:
            return True
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        if bigrams:
            from collections import Counter as C2
            _, top_bg = C2(bigrams).most_common(1)[0]
            if top_bg / len(bigrams) > 0.35:
                return True
    return False


# ── ORT session factory ────────────────────────────────────────────────────────
def _make_session(path: Path, threads: int) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])


def _load_model_config(model_dir: Path) -> dict:
    cfg = model_dir / "model_config.json"
    if cfg.exists():
        try:
            with open(cfg) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ── NLLB INT8 loader ──────────────────────────────────────────────────────────
def _load_nllb(direction: str) -> bool:
    if _nllb_ready[direction]:
        return True

    for tmpl in (NLLB_INT8_TEMPLATE, NLLB_ONNX_TEMPLATE):
        d_name    = tmpl.format(d=direction)
        model_dir = MODEL_DIR / d_name
        if not model_dir.is_dir():
            continue

        enc_path = model_dir / "encoder_model.onnx"
        dec_path = model_dir / "decoder_model.onnx"
        if not enc_path.exists() or not dec_path.exists():
            logger.warning("NLLB %s: missing encoder/decoder in %s", direction, model_dir)
            continue

        try:
            logger.info("Loading NLLB %s from %s (threads=%d)…", direction, d_name, NLLB_THREADS)
            t0 = time.time()
            encoder = _make_session(enc_path, NLLB_THREADS)
            decoder = _make_session(dec_path, NLLB_THREADS)

            src_lang = NLLB_LANG_EN  if direction == "en2lun" else NLLB_LANG_LUN
            tgt_lang = NLLB_LANG_LUN if direction == "en2lun" else NLLB_LANG_EN

            cfg = _load_model_config(model_dir)
            if "runyoro_lang_code" in cfg:
                code = cfg["runyoro_lang_code"]
                if direction == "en2lun":
                    tgt_lang = code
                else:
                    src_lang = code
                logger.info("NLLB %s: pinned lang code %s", direction, code)

            tokenizer = AutoTokenizer.from_pretrained(str(model_dir), src_lang=src_lang)
            enc_input_names = {i.name for i in encoder.get_inputs()}
            dec_input_names = {i.name for i in decoder.get_inputs()}
            fmt = "int8" if "int8" in d_name else "fp32_onnx"

            _nllb_sessions[direction] = {
                "encoder":    encoder,
                "decoder":    decoder,
                "tokenizer":  tokenizer,
                "src_lang":   src_lang,
                "tgt_lang":   tgt_lang,
                "enc_inputs": enc_input_names,
                "dec_inputs": dec_input_names,
                "model_dir":  str(model_dir),
                "format":     fmt,
            }
            _nllb_ready[direction] = True
            logger.info("NLLB %s ready in %.1fs (format=%s)", direction,
                        time.time() - t0, fmt)
            return True
        except Exception as e:
            logger.warning("NLLB %s load failed for %s: %s", direction, d_name, e)

    logger.error("NLLB %s: no usable model found under %s", direction, MODEL_DIR)
    return False


# ── NLLB greedy inference ─────────────────────────────────────────────────────
def _nllb_translate(text: str, direction: str) -> Optional[str]:
    """Greedy decode — mirrors translator_v2.cpp and verify_pi_models.py exactly."""
    if not _nllb_ready.get(direction):
        if not _load_nllb(direction):
            return None

    sess      = _nllb_sessions[direction]
    tok       = sess["tokenizer"]
    encoder   = sess["encoder"]
    decoder   = sess["decoder"]
    src_lang  = sess["src_lang"]
    tgt_lang  = sess["tgt_lang"]
    enc_inputs = sess["enc_inputs"]
    dec_inputs = sess["dec_inputs"]

    if direction == "lun2en":
        text = _preprocess_lunyoro(text)
    else:
        # Sentence-case the English input so the model sees a consistent form.
        # NLLB was fine-tuned on properly-cased sentences; all-lowercase input
        # like "how are you" produces wrong-language output (e.g. "muli kurungi")
        # because it doesn't match any seen training pattern.
        text = text.strip()
        if text and not text[0].isupper():
            text = text[0].upper() + text[1:]
        # Add a question mark if input looks like a question but has no punctuation
        if text and text[-1] not in ".!?,;:" and any(
            text.lower().startswith(w) for w in
            ("how", "what", "where", "when", "who", "why", "which", "is ", "are ", "do ", "does ", "can ", "will ", "have ")
        ):
            text = text + "?"

    try:
        tok.src_lang = src_lang
        batch          = tok(text, return_tensors="np", truncation=True, max_length=256)
        input_ids      = batch["input_ids"].astype(np.int64)
        attention_mask = batch["attention_mask"].astype(np.int64)

        enc_feed = {"input_ids": input_ids, "attention_mask": attention_mask}
        hidden = encoder.run(None, {k: v for k, v in enc_feed.items() if k in enc_inputs})[0]

        # NLLB generation prefix: </s> + target language token
        tgt_id    = tok.convert_tokens_to_ids(tgt_lang)
        generated = [tok.eos_token_id, tgt_id]

        for _ in range(MAX_LENGTH_NLLB):
            dec_feed = {
                "input_ids":              np.array([generated], dtype=np.int64),
                "encoder_hidden_states":  hidden,
                "encoder_attention_mask": attention_mask,
            }
            logits  = decoder.run(None, {k: v for k, v in dec_feed.items() if k in dec_inputs})[0]
            next_id = int(np.argmax(logits[0, -1]))
            if next_id == tok.eos_token_id:
                break
            generated.append(next_id)

        result = tok.decode(generated[2:], skip_special_tokens=True)
        result = re.sub(r"▁", " ", result).strip()
        result = re.sub(r"\s+", " ", result).strip()
        result = re.sub(r"^(run_Latn|eng_Latn|nyk_Latn|nyn_Latn)\s*:\s*", "", result).strip()

        if direction == "en2lun":
            result = _postprocess_lunyoro(result)
        else:
            result = _postprocess_english(result)

        if _is_garbage(result):
            return None
        return result or None

    except Exception as e:
        logger.error("NLLB inference error (%s): %s", direction, e)
        return None


# ── High-level translate functions ────────────────────────────────────────────
def _translate_en2lun(text: str) -> dict:
    nllb_out = _nllb_translate(text, "en2lun")
    primary  = nllb_out or text

    if _retrieval_available:
        try:
            _setup_backend_path()
            from translate import translate as _real_translate
            rt = _real_translate(text)
            if rt.get("translation"):
                return rt
        except Exception:
            pass

    return {
        "translation":        primary,
        "translation_nllb":   nllb_out,
        "translation_marian": None,
        "method":             "neural_mt",
        "confidence":         0.85 if nllb_out else 0.5,
        "source":             text,
        "pi_sim":             True,
        "nllb_format":        _nllb_sessions.get("en2lun", {}).get("format", "unavailable"),
    }


def _translate_lun2en(text: str) -> dict:
    nllb_out = _nllb_translate(text, "lun2en")
    primary  = nllb_out or text

    if _retrieval_available:
        try:
            _setup_backend_path()
            from translate import translate_to_english as _real_rev
            rt = _real_rev(text)
            if rt.get("translation"):
                return rt
        except Exception:
            pass

    return {
        "translation":        primary,
        "translation_nllb":   nllb_out,
        "translation_marian": None,
        "method":             "neural_mt",
        "confidence":         0.85 if nllb_out else 0.5,
        "source":             text,
        "pi_sim":             True,
        "nllb_format":        _nllb_sessions.get("lun2en", {}).get("format", "unavailable"),
    }


# ── History ────────────────────────────────────────────────────────────────────
def _save_history(entry: dict):
    with _history_lock:
        history = []
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE) as f:
                    history = json.load(f)
            except Exception:
                history = []
        history.insert(0, entry)
        history = history[:500]
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI application
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Pi-Sim Translator API",
    version="1.0.0",
    description="Raspberry Pi 5 virtual environment — NLLB INT8 ONNX only",
)

_cors_origins = [
    o.strip() for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3090,http://localhost:3002,http://localhost:3000,http://pi-sim-frontend:3000",
    ).split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup():
    def _bg():
        logger.info("=== Pi-Sim startup: loading NLLB models ===")
        for d in ("en2lun", "lun2en"):
            _load_nllb(d)
        _init_retrieval()
        logger.info("=== Pi-Sim startup complete ===")
    threading.Thread(target=_bg, daemon=True, name="pisim-startup").start()


# ── Request models ─────────────────────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text:      str
    context:   str  = ""
    refine:    bool = False
    direction: str  = "en->lun"

class BatchTranslateRequest(BaseModel):
    sentences: list[str]
    direction: str = "en->lun"

class WordLookupRequest(BaseModel):
    word:      str
    direction: str = "en→lun"

class SpellCheckRequest(BaseModel):
    text: str

class FeedbackRequest(BaseModel):
    source_text:  str
    translation:  str
    direction:    str  = "en→lun"
    rating:       int  = 1
    correction:   str  = ""
    error_type:   str  = ""
    model_used:   str  = ""
    refined:      bool = False
    score_mng: Optional[int] = None
    score_grm: Optional[int] = None
    score_tns: Optional[int] = None
    score_vcb: Optional[int] = None
    score_ort: Optional[int] = None
    score_ctx: Optional[int] = None
    score_flu: Optional[int] = None
    score_cul: Optional[int] = None


# ── Core endpoints ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Pi-Sim Translator API — NLLB INT8 ONNX"}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "pi_sim": True}

@app.get("/ping")
def ping():
    return {"pong": True, "timestamp": datetime.utcnow().isoformat()}

@app.get("/system-info")
def system_info():
    import psutil
    mem = psutil.virtual_memory()
    return {
        "nllb_en2lun":        _nllb_ready.get("en2lun", False),
        "nllb_lun2en":        _nllb_ready.get("lun2en", False),
        "nllb_en2lun_format": _nllb_sessions.get("en2lun", {}).get("format", "not_loaded"),
        "nllb_lun2en_format": _nllb_sessions.get("lun2en", {}).get("format", "not_loaded"),
        "nllb_disabled":      False,
        # Marian removed — always False
        "marian_en2lun":  False,
        "marian_lun2en":  False,
        "marian_onnx":    False,
        "marian_mode":    "disabled",
        # Hardware
        "gpu_available":  False,
        "gpu_count":      0,
        "device":         "cpu",
        "pi_sim":         True,
        "pi_sim_version": "2.0.0",
        # Memory
        "ram_total_gb":     round(mem.total / 1e9, 1),
        "ram_used_gb":      round(mem.used  / 1e9, 1),
        "ram_available_gb": round(mem.available / 1e9, 1),
        "ram_percent":      mem.percent,
        # Config
        "nllb_threads":        NLLB_THREADS,
        "retrieval_available": _retrieval_available,
    }

@app.post("/translate")
def translate_text(req: TranslateRequest):
    if not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    if len(req.text) > 5000:
        raise HTTPException(400, "Text too long (max 5000 chars)")
    result = _translate_en2lun(req.text)
    _save_history({
        "input": req.text, "direction": "en→lun",
        "translation": result.get("translation"),
        "method": result.get("method"),
        "timestamp": datetime.utcnow().isoformat(), "pi_sim": True,
    })
    return result

@app.post("/translate-reverse")
def translate_reverse(req: TranslateRequest):
    if not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    if len(req.text) > 5000:
        raise HTTPException(400, "Text too long (max 5000 chars)")
    result = _translate_lun2en(req.text)
    _save_history({
        "input": req.text, "direction": "lun→en",
        "translation": result.get("translation"),
        "method": result.get("method"),
        "timestamp": datetime.utcnow().isoformat(), "pi_sim": True,
    })
    return result

@app.post("/translate-batch")
def translate_batch(req: BatchTranslateRequest):
    if not req.sentences:
        raise HTTPException(400, "No sentences provided")
    if len(req.sentences) > 100:
        raise HTTPException(400, "Maximum 100 sentences per batch")

    import concurrent.futures as _cf

    def _one(s: str) -> dict:
        text = s.strip()
        if not text:
            return {"source": s, "translation": "", "method": "skipped"}
        if len(text) > 5000:
            return {"source": s, "translation": "", "method": "error", "error": "Too long"}
        r = _translate_lun2en(text) if req.direction == "lun->en" else _translate_en2lun(text)
        return {"source": text, "translation": r.get("translation", ""),
                "method": r.get("method", "neural_mt"), "confidence": r.get("confidence")}

    results: list[dict] = [{}] * len(req.sentences)
    with _cf.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_one, s): i for i, s in enumerate(req.sentences)}
        for fut in _cf.as_completed(futures):
            idx = futures[fut]
            try:
                results[idx] = fut.result(timeout=120)
            except Exception as e:
                results[idx] = {"source": req.sentences[idx], "translation": "",
                                "method": "error", "error": str(e)}
    return {"results": results, "total": len(results), "direction": req.direction}

@app.post("/translate-batch-file")
async def translate_batch_file(file: UploadFile = File(...), direction: str = "en->lun"):
    import csv as _csv
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".txt"):
        raise HTTPException(400, "Supported formats: .csv, .txt")
    contents = await file.read()
    text = contents.decode("utf-8", errors="ignore")
    sentences: list[str] = []
    if ext == ".csv":
        for row in _csv.reader(text.splitlines()):
            if row:
                sentences.append(row[0].strip())
    else:
        sentences = [l.strip() for l in text.splitlines() if l.strip()]
    if not sentences:
        raise HTTPException(400, "No text found in file")
    sentences = sentences[:200]
    result = translate_batch(BatchTranslateRequest(sentences=sentences, direction=direction))
    result["filename"] = file.filename
    return result

@app.post("/lookup")
def word_lookup(req: WordLookupRequest):
    if not req.word.strip():
        raise HTTPException(400, "Word cannot be empty")
    if _retrieval_available:
        try:
            _setup_backend_path()
            from translate import lookup_word as _lw
            return {"word": req.word, "results": _lw(req.word, req.direction)}
        except Exception as e:
            logger.warning("lookup_word failed: %s", e)
    return {"word": req.word, "results": [], "error": "retrieval index not available"}

@app.post("/spellcheck")
def spellcheck_text(req: SpellCheckRequest):
    if not req.text.strip():
        return {"misspelled": []}
    if _retrieval_available:
        try:
            _setup_backend_path()
            from translate import spellcheck as _sc
            return {"misspelled": _sc(req.text)}
        except Exception as e:
            logger.warning("spellcheck failed: %s", e)
    return {"misspelled": []}

@app.get("/history")
def get_history():
    if not HISTORY_FILE.exists():
        return {"history": []}
    try:
        with open(HISTORY_FILE) as f:
            return {"history": json.load(f)}
    except Exception:
        return {"history": []}

@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    if not req.source_text.strip() or not req.translation.strip():
        raise HTTPException(400, "source_text and translation are required")
    if req.rating not in (-1, 0, 1):
        raise HTTPException(400, "rating must be -1, 0, or 1")
    try:
        _setup_backend_path()
        from feedback_store import save_feedback
        save_feedback({
            "source_text": req.source_text.strip(),
            "translation": req.translation.strip(),
            "direction":   req.direction,
            "rating":      req.rating,
            "correction":  req.correction.strip(),
            "error_type":  req.error_type.strip(),
            "model_used":  req.model_used.strip(),
            "refined":     req.refined,
            "pi_sim":      True,
            "timestamp":   datetime.utcnow().isoformat(),
        })
    except Exception:
        _save_history({**req.model_dump(), "type": "feedback",
                       "timestamp": datetime.utcnow().isoformat()})
    return {
        "status": "saved",
        "rating": req.rating,
        "correction_received": bool(req.correction.strip()),
        "error_type": req.error_type or None,
    }


# ── OCR endpoints ──────────────────────────────────────────────────────────────
def _get_ocr_result(img_bytes: bytes, direction: str) -> dict:
    try:
        _setup_backend_path()
        import numpy as _np
        try:
            import cv2
            nparr = _np.frombuffer(img_bytes, _np.uint8)
            img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except ImportError:
            from PIL import Image as _PIL
            img = _np.array(_PIL.open(io.BytesIO(img_bytes)).convert("RGB"))
        if img is None:
            return {"error": "Could not decode image"}
        h, w = img.shape[:2]
        from main import _get_ocr_engine, _run_ocr, _translate_region
        engine = _get_ocr_engine()
        if engine == "none":
            return {"error": "No OCR engine available", "regions": []}
        raw = _run_ocr(img)
        regions = []
        for (bbox, text, conf) in raw:
            if conf < 0.3 or not text.strip():
                continue
            x_min = int(min(p[0] for p in bbox))
            y_min = int(min(p[1] for p in bbox))
            x_max = int(max(p[0] for p in bbox))
            y_max = int(max(p[1] for p in bbox))
            regions.append({
                "original":   text,
                "translated": _translate_region(text, direction),
                "confidence": round(conf, 2),
                "bbox":      {"x": x_min, "y": y_min,
                               "width": x_max - x_min, "height": y_max - y_min},
                "bbox_norm": {"x": round(x_min/w,4), "y": round(y_min/h,4),
                               "width": round((x_max-x_min)/w,4),
                               "height": round((y_max-y_min)/h,4)},
            })
        return {"regions": regions, "image_size": {"width": w, "height": h},
                "direction": direction, "total_detected": len(raw),
                "total_translated": len(regions), "engine": engine}
    except Exception as e:
        logger.error("OCR error: %s", e)
        return {"error": str(e), "regions": []}

@app.post("/ocr-translate")
async def ocr_translate(file: UploadFile = File(...), direction: str = "en->lun"):
    return _get_ocr_result(await file.read(), direction)

@app.post("/ocr-translate-base64")
async def ocr_translate_base64(request: Request):
    body = await request.json()
    image_data = body.get("image", "")
    direction  = body.get("direction", "en->lun")
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(image_data)
    except Exception as e:
        return {"error": f"Could not decode base64: {e}", "regions": []}
    return _get_ocr_result(img_bytes, direction)


# ── Image classification ───────────────────────────────────────────────────────
@app.post("/classify-image")
async def classify_image(file: UploadFile = File(...), top_k: int = 1):
    try:
        _setup_backend_path()
        from image_classifier import image_classifier, validate_image_upload
        if not image_classifier.is_ready():
            raise HTTPException(503, "Image classifier not ready")
        contents  = await file.read()
        validated = validate_image_upload(
            content_type=file.content_type,
            filename=file.filename,
            file_bytes=contents,
        )
        predictions = image_classifier.classify(validated, top_k=min(top_k, 10))
        results = []
        for pred in predictions:
            label_en = pred["label"]
            r = _translate_en2lun(label_en)
            results.append({
                "label_en":   label_en,
                "label_lun":  r.get("translation", label_en),
                "confidence": pred["confidence"],
                "method":     r.get("method", "neural_mt"),
            })
        return {"predictions": results, "top_k": len(results),
                "model": "google/mobilenet_v2_1.0_224"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Classification error: {e}")

@app.get("/classify-image/status")
def classify_image_status():
    try:
        _setup_backend_path()
        from image_classifier import image_classifier
        return {"ready": image_classifier.is_ready(),
                "error": image_classifier.get_load_error()}
    except Exception:
        return {"ready": False, "error": "image_classifier module not available"}


# ── Language rules ─────────────────────────────────────────────────────────────
@app.get("/language-rules")
def language_rules():
    try:
        _setup_backend_path()
        from language_rules_data import (
            RL_RULE, EMPAAKO, INTERJECTIONS, IDIOMS, NUMBERS, PROVERBS,
            NOUN_CLASSES, CONCORDIAL_AGREEMENT, TENSES, VERB_SUFFIXES,
            GRAMMAR_SUMMARY,
        )
        return {
            "rl_rule": RL_RULE, "grammar_summary": GRAMMAR_SUMMARY,
            "empaako": EMPAAKO, "interjections": INTERJECTIONS,
            "idioms": IDIOMS, "numbers": {str(k): v for k, v in NUMBERS.items()},
            "proverbs": PROVERBS, "noun_classes": NOUN_CLASSES,
            "concordial_agreement": CONCORDIAL_AGREEMENT,
            "tenses": TENSES, "verb_suffixes": VERB_SUFFIXES,
        }
    except Exception as e:
        raise HTTPException(500, f"Language rules not available: {e}")


# ── Benchmark ──────────────────────────────────────────────────────────────────
@app.post("/benchmark")
async def benchmark():
    probes = [
        ("en2lun", "Good morning, my friend."),
        ("en2lun", "How are you today?"),
        ("en2lun", "Thank you very much."),
        ("lun2en", "Oli ota"),
        ("lun2en", "Webale muno"),
        ("lun2en", "Oraire ota"),
    ]
    results = []
    for direction, text in probes:
        t0  = time.time()
        out = _nllb_translate(text, direction)
        results.append({
            "direction":   direction,
            "source":      text,
            "nllb":        out,
            "elapsed_s":   round(time.time() - t0, 3),
            "nllb_format": _nllb_sessions.get(direction, {}).get("format", "not_loaded"),
        })
    return {"probes": results, "count": len(results), "pi_sim": True}
