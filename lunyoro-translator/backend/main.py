from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import os
import io
import time
from collections import defaultdict

# Load .env file if present (development convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Allow HuggingFace Hub downloads for models (sem_model may need to download)
# Set offline mode only if explicitly requested via environment variable
if os.getenv("FORCE_OFFLINE", "0").strip() in ("1", "true", "yes"):
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"

from translate import translate, translate_to_english, lookup_word, spellcheck, get_index_and_model
from translate import _mt_translate, _nllb_translate
import re as _re


def _clean_translation(text: str) -> str:
    """
    Post-process a translated reply:
    - Remove repeated comma-joined phrases (e.g. "n'ebyokurya, n'ebyokurya, ...")
    - Deduplicate repeated sentences
    - Strip incomplete trailing fragments
    - Collapse excess whitespace/punctuation
    """
    if not text:
        return text

    # 1. Remove runs of repeated short comma/conjunction-separated fragments
    #    e.g. "n'ebyokurya, n'ebyokurya, n'ebyokurya" → "n'ebyokurya"
    text = _re.sub(r"((?:[^,\.]{2,40}),\s*)\1{2,}", r"\1", text)
    # Also catch "na X, na X, na X" style
    text = _re.sub(r"(\b\S+(?:\s+\S+){0,4})((?:,\s*\1){2,})", r"\1", text)

    # 2. Deduplicate repeated sentences (keep first occurrence)
    sentences = _re.split(r'(?<=[.!?])\s+', text.strip())
    seen, deduped = set(), []
    for s in sentences:
        key = _re.sub(r'\s+', ' ', s.strip().lower())
        if key and key not in seen:
            seen.add(key)
            deduped.append(s.strip())
    text = ' '.join(deduped)

    # 3. Remove trailing incomplete fragment after last full stop
    last_end = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_end > len(text) // 2:
        text = text[:last_end + 1]

    # 4. Collapse whitespace and fix double punctuation
    text = _re.sub(r'\s+', ' ', text).strip()
    text = _re.sub(r'([,\.!?])\s*\1+', r'\1', text)

    return text

app = FastAPI(title="Lunyoro/Rutooro Translator API")

# CORS — configurable via CORS_ORIGINS env var (comma-separated)
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3002,http://localhost:3000,https://horizonx.kathay.tech,https://runyoro-rutooro-translator.vercel.app")
_cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple in-memory rate limiter for /chat ───────────────────────────────────
# Max 5 requests per 60 seconds per IP to prevent Ollama overload
_chat_rate: dict = defaultdict(list)
_CHAT_RATE_LIMIT = 5
_CHAT_RATE_WINDOW = 60  # seconds

def _check_chat_rate(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    window_start = now - _CHAT_RATE_WINDOW
    _chat_rate[ip] = [t for t in _chat_rate[ip] if t > window_start]
    if len(_chat_rate[ip]) >= _CHAT_RATE_LIMIT:
        return False
    _chat_rate[ip].append(now)
    return True

_GRAMMAR_CONTEXT_CACHE: str | None = None

@app.on_event("startup")
def preload_model():
    """Load models in background — app must respond to /health fast for HF Space."""
    global _GRAMMAR_CONTEXT_CACHE
    _GRAMMAR_CONTEXT_CACHE = ""

    # Restore feedback history
    try:
        from feedback_store import restore_from_github
        restore_from_github()
    except Exception as _e:
        print(f"[startup] feedback restore skipped: {_e}")

    # Load ALL models in a background thread so uvicorn responds immediately
    import threading
    def _bg_load():
        global _GRAMMAR_CONTEXT_CACHE
        try:
            get_index_and_model()
            print("[startup/bg] Retrieval index loaded")
        except Exception as _e:
            print(f"[startup/bg] Retrieval index failed: {_e}")

        from translate import _load_mt, _load_nllb
        if os.getenv("DISABLE_MARIAN", "0").strip() not in ("1", "true", "yes"):
            _load_mt("en2lun")
            _load_mt("lun2en")

        for d in ["en2lun", "lun2en"]:
            try:
                _load_nllb(d)
            except Exception as _e:
                print(f"[startup/bg] NLLB {d} failed: {_e}")

        try:
            from language_rules import get_full_grammar_context
            from language_rules_gr4 import get_gr4_grammar_context
            from language_rules_gr5 import get_gr5_grammar_context
            core_ctx = get_full_grammar_context()[:2000]
            gr4_ctx = get_gr4_grammar_context()[:1800]
            gr5_ctx = get_gr5_grammar_context()[:2200]
            _GRAMMAR_CONTEXT_CACHE = core_ctx + gr4_ctx + gr5_ctx
            print(f"[startup/bg] Grammar context: {len(_GRAMMAR_CONTEXT_CACHE)} chars")
        except Exception as _e:
            print(f"[startup/bg] Grammar context failed: {_e}")

        # Load image classifier (MobileNetV2) — lightweight, ~14MB
        try:
            from image_classifier import image_classifier
            image_classifier.load_model()
        except Exception as _e:
            print(f"[startup/bg] Image classifier failed: {_e}")

        print("[startup/bg] All models loaded successfully")

    threading.Thread(target=_bg_load, daemon=True).start()
    print("[startup] App ready — models loading in background")

# History file — configurable via HISTORY_FILE env var
HISTORY_FILE = os.getenv("HISTORY_FILE") or os.path.join(os.path.dirname(__file__), "history.json")


def save_history(entry: dict):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    history.insert(0, entry)
    history = history[:500]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


class TranslateRequest(BaseModel):
    text: str
    context: str = ""  # optional previous sentence for context-aware translation
    refine: bool = False  # optional LLM refinement pass for higher quality
    direction: str = "en->lun"  # accepted but ignored — endpoint determines direction


def _qwen_refine_translation(source_en: str, draft_lun: str) -> str:
    """
    Run a Qwen LLM pass to refine an MT draft translation.
    Only called when refine=True. Returns draft unchanged on failure.
    """
    try:
        hf_token = os.getenv("HF_TOKEN", "")
        hf_model = os.getenv("HF_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        if not hf_token:
            return draft_lun
        from openai import OpenAI as _OAI
        grammar_hint = (_GRAMMAR_CONTEXT_CACHE or "")[:1500]
        prompt = (
            "You are a Runyoro-Rutooro language expert. "
            "Improve the machine-translated draft for accuracy and correct grammar.\n"
            f"Grammar rules:\n{grammar_hint}\n\n"
            "Rules:\n"
            "- Fix noun class prefixes and concordial agreement\n"
            "- Apply R/L rule: L only before/after e or i\n"
            "- Apply apostrophe elision: na ente → n'ente, ni omuntu → n'omuntu\n"
            "- Fix kinship terms: ise wange → isange, nyina wawe → nyinawe\n"
            "- Output ONLY the corrected Runyoro-Rutooro text, nothing else\n"
        )
        client = _OAI(base_url="https://router.huggingface.co/v1", api_key=hf_token)
        resp = client.chat.completions.create(
            model=hf_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"English: {source_en}\nDraft: {draft_lun}\nRefined:"},
            ],
            max_tokens=256,
            temperature=0.2,
        )
        refined = resp.choices[0].message.content.strip()
        # Apply grammar rules on top of LLM output
        try:
            from language_rules_gr4 import apply_gr4_rules
            refined = apply_gr4_rules(refined, direction="en->lun")
        except Exception:
            pass
        return refined if refined and len(refined) > 3 else draft_lun
    except Exception:
        return draft_lun


class WordLookupRequest(BaseModel):
    word: str
    direction: str = "en→lun"

class SpellCheckRequest(BaseModel):
    text: str


@app.get("/")
def root():
    return {"message": "Lunyoro/Rutooro Translator API is running"}


@app.post("/translate")
def translate_text(req: TranslateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 chars)")
    result = translate(req.text, context=req.context)
    # Optional LLM refinement pass
    if req.refine and result.get("translation"):
        refined = _qwen_refine_translation(req.text, result["translation"])
        result["translation_refined"] = refined
        result["translation"] = refined  # use refined as primary
    save_history({
        "input": req.text,
        "direction": "en→lun",
        "translation": result.get("translation"),
        "method": result.get("method") + ("+refined" if req.refine else ""),
        "confidence": result.get("confidence"),
        "timestamp": datetime.utcnow().isoformat(),
    })
    return result


@app.post("/translate-reverse")
def translate_reverse(req: TranslateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 chars)")
    result = translate_to_english(req.text, context=req.context)

    # Apply English post-processing to the final translation (catches any path)
    from translate import _postprocess_english as _ppenglish
    if result.get("translation"):
        result["translation"] = _ppenglish(result["translation"])

    # ── LLM refinement pass — always on for lun→en (opt out with refine=False) ──
    # Qwen improves fluency, resolves double-subjects, and naturalises English.
    # Falls back silently so translation still returns if the API is down.
    should_refine = req.refine is not False  # True by default, opt-out with refine=False
    if should_refine and result.get("translation"):
        try:
            hf_token = os.getenv("HF_TOKEN", "")
            hf_model = os.getenv("HF_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            if hf_token:
                from openai import OpenAI as _OAI
                client = _OAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=hf_token,
                    timeout=12.0,  # hard cap — don't block the response beyond 12s
                )
                resp = client.chat.completions.create(
                    model=hf_model,
                    messages=[
                        {"role": "system", "content": (
                            "You are an expert translator from Runyoro-Rutooro (a Bantu language spoken in "
                            "western Uganda) to English. You receive a Runyoro/Rutooro source sentence and "
                            "a machine-translated English draft. Your task is to:\n"
                            "1. Fix any grammatical errors (especially double subjects like 'The man he went')\n"
                            "2. Make the English natural and fluent\n"
                            "3. Preserve the original meaning exactly — do not add or remove content\n"
                            "4. Output ONLY the corrected English sentence, nothing else."
                        )},
                        {"role": "user", "content": (
                            f"Runyoro/Rutooro: {req.text}\n"
                            f"Draft English: {result['translation']}\n"
                            f"Corrected English:"
                        )},
                    ],
                    max_tokens=256,
                    temperature=0.15,
                )
                refined = resp.choices[0].message.content.strip()
                # Only use the refined version if it's substantively different and non-empty
                if refined and len(refined) > 3 and refined.lower() != result["translation"].lower():
                    result["translation_draft"] = result["translation"]
                    result["translation"] = refined
                    result["refined"] = True
        except Exception:
            pass  # refinement is best-effort — raw MT is still returned

    save_history({
        "input": req.text,
        "direction": "lun→en",
        "translation": result.get("translation"),
        "method": result.get("method", "") + ("+refined" if result.get("refined") else ""),
        "confidence": result.get("confidence"),
        "timestamp": datetime.utcnow().isoformat(),
    })
    return result


# ── Batch/Bulk Translation ─────────────────────────────────────────────────────

class BatchTranslateRequest(BaseModel):
    sentences: list[str]
    direction: str = "en->lun"  # "en->lun" or "lun->en"


@app.post("/translate-batch")
def translate_batch(req: BatchTranslateRequest):
    """Translate a list of sentences in bulk. Max 100 sentences per request."""
    if not req.sentences:
        raise HTTPException(status_code=400, detail="No sentences provided")
    if len(req.sentences) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 sentences per batch")

    results = []
    for sentence in req.sentences:
        text = sentence.strip()
        if not text:
            results.append({"source": sentence, "translation": "", "method": "skipped"})
            continue
        if len(text) > 1000:
            results.append({"source": sentence, "translation": "", "method": "error", "error": "Too long (max 1000 chars)"})
            continue

        if req.direction == "lun->en":
            result = translate_to_english(text)
        else:
            result = translate(text)

        results.append({
            "source": text,
            "translation": result.get("translation", ""),
            "method": result.get("method", "unknown"),
            "confidence": result.get("confidence"),
        })

    return {
        "results": results,
        "total": len(results),
        "direction": req.direction,
    }


@app.post("/translate-batch-file")
async def translate_batch_file(file: UploadFile = File(...), direction: str = "en->lun"):
    """Upload a CSV or TXT file, translate each line/row, return results as JSON."""
    import csv as _csv

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".txt"):
        raise HTTPException(status_code=400, detail="Supported formats: .csv, .txt")

    contents = await file.read()
    text_content = contents.decode("utf-8", errors="ignore")

    # Parse sentences
    sentences: list[str] = []
    if ext == ".csv":
        reader = _csv.reader(text_content.splitlines())
        for row in reader:
            if row:
                sentences.append(row[0].strip())
    else:
        sentences = [line.strip() for line in text_content.splitlines() if line.strip()]

    if not sentences:
        raise HTTPException(status_code=400, detail="No text found in file")
    if len(sentences) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 sentences per file upload")

    # Translate
    results = []
    for text in sentences:
        if not text or len(text) > 1000:
            results.append({"source": text, "translation": "", "method": "skipped"})
            continue
        if direction == "lun->en":
            result = translate_to_english(text)
        else:
            result = translate(text)
        results.append({
            "source": text,
            "translation": result.get("translation", ""),
            "method": result.get("method", "unknown"),
        })

    return {
        "results": results,
        "total": len(results),
        "direction": direction,
        "filename": file.filename,
    }


@app.post("/lookup")
def word_lookup(req: WordLookupRequest):
    if not req.word.strip():
        raise HTTPException(status_code=400, detail="Word cannot be empty")
    results = lookup_word(req.word, req.direction)
    return {"word": req.word, "results": results}


@app.post("/spellcheck")
def spellcheck_text(req: SpellCheckRequest):
    if not req.text.strip():
        return {"misspelled": []}
    results = spellcheck(req.text)
    return {"misspelled": results}


@app.get("/history")
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return {"history": []}
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    return {"history": history}


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/system-info")
def system_info():
    """Return which models are loaded and hardware info — used by frontend to show model badges."""
    from translate import _mt_available, _nllb_available, _mt_onnx
    import torch
    return {
        "marian_en2lun":  _mt_available.get("en2lun", False),
        "marian_lun2en":  _mt_available.get("lun2en", False),
        "marian_onnx":    _mt_onnx.get("en2lun", False) or _mt_onnx.get("lun2en", False),
        "nllb_en2lun":    _nllb_available.get("en2lun", False),
        "nllb_lun2en":    _nllb_available.get("lun2en", False),
        "nllb_disabled":  os.getenv("DISABLE_NLLB", "").strip() in ("1", "true", "yes"),
        "gpu_available":  torch.cuda.is_available(),
        "gpu_count":      torch.cuda.device_count(),
    }


# ── Human Feedback Loop ───────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    source_text: str
    translation: str
    direction: str = "en→lun"   # "en→lun" or "lun→en"
    rating: int = 1             # 1 = correct, -1 = incorrect
    correction: str = ""        # user-provided correct translation
    error_type: str = ""        # grammar, spelling, context, vocabulary, other
    model_used: str = ""        # "marian", "nllb", "both", "none"
    refined: bool = False       # whether AI refinement was applied to this translation

    # ── Benchmark dimensions (from Runyooro-Rutooro LLM Benchmarking Form) ──
    # Each scored 0–5 by the evaluator; None means not scored (casual feedback)
    score_mng: int | None = None   # Meaning Fidelity        (weight 25%)
    score_grm: int | None = None   # Grammar & Syntax        (weight 15%)
    score_tns: int | None = None   # Tense & Aspect          (weight 12%)
    score_vcb: int | None = None   # Vocabulary Choice       (weight 12%)
    score_ort: int | None = None   # Orthography & Spelling  (weight  8%)
    score_ctx: int | None = None   # Context Awareness       (weight 10%)
    score_flu: int | None = None   # Fluency & Naturalness   (weight 10%)
    score_cul: int | None = None   # Cultural & Idiomatic    (weight  8%)
    # Computed SQS (0–100) — calculated server-side if any dimension scores present
    sqs: float | None = None


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest, request: Request):
    """Submit a translation rating with error categorization and correction."""
    if not req.source_text.strip() or not req.translation.strip():
        raise HTTPException(status_code=400, detail="source_text and translation are required")
    if req.rating not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="rating must be -1, 0, or 1")

    from feedback_store import save_feedback, compute_sqs

    # Compute SQS if any dimension scores were provided
    dim_scores = {
        "score_mng": req.score_mng, "score_grm": req.score_grm,
        "score_tns": req.score_tns, "score_vcb": req.score_vcb,
        "score_ort": req.score_ort, "score_ctx": req.score_ctx,
        "score_flu": req.score_flu, "score_cul": req.score_cul,
    }
    sqs = compute_sqs(dim_scores) if any(v is not None for v in dim_scores.values()) else None

    entry = {
        "source_text": req.source_text.strip(),
        "translation": req.translation.strip(),
        "direction":   req.direction,
        "rating":      req.rating,
        "correction":  req.correction.strip(),
        "error_type":  req.error_type.strip(),
        "model_used":  req.model_used.strip(),
        "refined":     req.refined,
        "ip":          request.client.host if request.client else "unknown",
        # Benchmark dimension scores (None if not provided)
        **{k: v for k, v in dim_scores.items() if v is not None},
        **({"sqs": round(sqs, 1)} if sqs is not None else {}),
    }
    save_feedback(entry)
    
    # Check if auto-retrain should be triggered (async, non-blocking)
    try:
        import threading
        from auto_retrain import check_and_retrain
        # Run check in background thread to avoid blocking the response
        threading.Thread(target=check_and_retrain, daemon=True).start()
    except Exception:
        pass  # Don't fail feedback submission if auto-retrain check fails
    
    # If user provided a correction, use it immediately for the current session
    # (stored in feedback.jsonl for future retraining)
    return {
        "status": "saved",
        "rating": req.rating,
        "correction_received": bool(req.correction.strip()),
        "error_type": req.error_type or None,
        "sqs": round(sqs, 1) if sqs is not None else None,
    }




@app.get("/debug-nllb")
def debug_nllb():
    """Try to load NLLB and return any error."""
    import traceback
    errors = {}
    for direction in ["en2lun", "lun2en"]:
        try:
            from translate import _load_nllb, _nllb_available, MODEL_DIR
            import os
            # Prefer the trained model dir; fall back to legacy _pre_nyo
            path = os.path.join(MODEL_DIR, f"nllb_{direction}")
            if not (os.path.isdir(path) and any(f.endswith((".safetensors", ".bin")) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)))):
                path = os.path.join(MODEL_DIR, f"nllb_{direction}_pre_nyo")
            exists = os.path.isdir(path)
            files = os.listdir(path) if exists else []
            has_weights = any(f.endswith((".safetensors", ".bin")) for f in files)
            
            if not has_weights:
                errors[direction] = f"No weights at {path}. Files: {files[:10]}"
            else:
                # Try loading
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                import torch
                tok = AutoTokenizer.from_pretrained(path)
                errors[direction] = f"Tokenizer OK. Vocab: {tok.vocab_size}. Trying model load (float16)..."
                model = AutoModelForSeq2SeqLM.from_pretrained(path, torch_dtype=torch.float16)
                errors[direction] = f"LOADED OK on CPU (float16). Params: {sum(p.numel() for p in model.parameters())/1e6:.0f}M"
                del model
                import gc; gc.collect()
        except Exception as e:
            errors[direction] = f"FAILED: {traceback.format_exc()[-500:]}"
    
    # Memory info
    import psutil
    mem = psutil.virtual_memory()
    return {
        "ram_total_gb": round(mem.total / 1e9, 1),
        "ram_used_gb": round(mem.used / 1e9, 1),
        "ram_available_gb": round(mem.available / 1e9, 1),
        "ram_percent": mem.percent,
        "nllb_status": errors,
    }

@app.get("/feedback/stats")
def feedback_stats():
    """Return summary statistics and save to feedback folder."""
    from feedback_store import get_stats
    from pathlib import Path
    import pandas as pd
    import json
    
    stats = get_stats()
    
    # Save stats to feedback folder
    feedback_dir = Path(__file__).parent / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    json_path = feedback_dir / "stats.json"
    with open(json_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Save as CSV
    stats_df = pd.DataFrame([{
        'Metric': 'Total Feedback',
        'Value': stats['total']
    }, {
        'Metric': 'Thumbs Up',
        'Value': stats['thumbs_up']
    }, {
        'Metric': 'Thumbs Down',
        'Value': stats['thumbs_down']
    }, {
        'Metric': 'Neutral',
        'Value': stats['neutral']
    }, {
        'Metric': 'Exportable Pairs',
        'Value': stats['exportable']
    }])
    
    csv_path = feedback_dir / "stats.csv"
    stats_df.to_csv(csv_path, index=False)
    
    stats['files_saved'] = ["feedback/stats.json", "feedback/stats.csv"]
    
    return stats


@app.get("/feedback/analytics")
def feedback_analytics():
    """Return detailed analytics about feedback patterns and model usage."""
    from feedback_store import get_detailed_analytics
    return get_detailed_analytics()


@app.get("/feedback/model-comparison")
def model_comparison():
    """Compare performance between MarianMT and NLLB models."""
    from feedback_store import get_model_comparison
    return get_model_comparison()


@app.get("/feedback/export")
def export_feedback():
    """Export approved (thumbs-up) pairs as CSV to feedback folder."""
    from feedback_store import get_approved_pairs
    from pathlib import Path
    import pandas as pd
    
    approved = get_approved_pairs(min_rating=1)
    if not approved:
        return {"message": "No approved pairs yet", "count": 0, "files": []}
    
    # Create feedback directory
    feedback_dir = Path(__file__).parent / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    
    # Export approved pairs
    rows = []
    for e in approved:
        src = e.get("source_text", "").strip()
        tgt = e.get("translation", "").strip()
        direction = e.get("direction", "en→lun")
        if not src or not tgt:
            continue
        if direction == "en→lun":
            rows.append({"english": src, "lunyoro": tgt})
        else:
            rows.append({"english": tgt, "lunyoro": src})
    
    if not rows:
        return {"message": "No valid pairs to export", "count": 0, "files": []}
    
    df = pd.DataFrame(rows).drop_duplicates(subset=["english", "lunyoro"])
    
    # Save to feedback folder
    csv_path = feedback_dir / "approved_pairs.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    
    return {
        "message": "Exported approved pairs to feedback folder",
        "count": len(df),
        "files": ["feedback/approved_pairs.csv"],
        "path": str(csv_path)
    }


@app.get("/feedback/auto-retrain-status")
def auto_retrain_status():
    """Get status of automatic retraining system."""
    try:
        from auto_retrain import get_clean_approved_pairs, get_last_retrain_count, RETRAIN_THRESHOLD, LAST_RETRAIN_FILE
        import json
        
        clean_pairs = get_clean_approved_pairs()
        last_count = get_last_retrain_count()
        new_pairs = len(clean_pairs) - last_count
        
        last_retrain_time = None
        if LAST_RETRAIN_FILE.exists():
            with open(LAST_RETRAIN_FILE, 'r') as f:
                data = json.load(f)
                last_retrain_time = data.get('timestamp')
        
        return {
            "total_clean_pairs": len(clean_pairs),
            "pairs_in_last_retrain": last_count,
            "new_pairs_since_retrain": new_pairs,
            "threshold": RETRAIN_THRESHOLD,
            "progress_percentage": round(100 * new_pairs / RETRAIN_THRESHOLD, 1) if RETRAIN_THRESHOLD > 0 else 0,
            "ready_for_retrain": new_pairs >= RETRAIN_THRESHOLD,
            "last_retrain_timestamp": last_retrain_time,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/feedback/dump")
def feedback_dump():
    """Return all raw feedback entries as JSON — used for local sync."""
    from feedback_store import load_all_feedback
    return {"entries": load_all_feedback()}


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def extract_text_from_file(filename: str, contents: bytes) -> str:
    """Extract plain text from PDF, DOCX, DOC, or TXT files."""
    import re
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(contents))
        text = " ".join(page.extract_text() or "" for page in reader.pages)

    elif ext in (".docx", ".doc"):
        from docx import Document
        doc = Document(io.BytesIO(contents))
        text = " ".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".txt":
        text = contents.decode("utf-8", errors="ignore")

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return re.sub(r'\s+', ' ', text).strip()


def validate_upload(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )


@app.post("/summarize-pdf")
async def summarize_pdf(file: UploadFile = File(...)):
    """Upload a PDF, DOCX, DOC, or TXT and get an English summary."""
    validate_upload(file.filename)

    import re
    from translate import _mt_translate, _load_retrieval, _dictionary

    contents = await file.read()
    try:
        full_text = extract_text_from_file(file.filename, contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not full_text:
        raise HTTPException(status_code=400, detail="No text found in document")

    # Split into sentences
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if len(s.strip()) > 10]
    total_sentences = len(sentences)

    # Detect language — if majority of words match Lunyoro dictionary, translate first
    _load_retrieval()
    known_lunyoro = set(d["word"].lower() for d in _dictionary if d.get("word"))
    sample_words = " ".join(sentences[:20]).lower().split()
    lunyoro_hits = sum(1 for w in sample_words if w in known_lunyoro)
    is_lunyoro = lunyoro_hits / max(len(sample_words), 1) > 0.1

    # Translate Lunyoro → English if needed
    if is_lunyoro:
        english_sentences = []
        for sent in sentences:
            # Apply grammar rules to normalise Lunyoro input before translation
            try:
                from language_rules import (
                    apply_rl_rule_to_text, apply_nasal_assimilation,
                    apply_particle_elision,
                )
                from language_rules_gr4 import apply_kinship_correction, apply_copula_to_text
                sent = apply_nasal_assimilation(sent)
                sent = apply_particle_elision(sent)
                sent = apply_kinship_correction(sent)
                sent = apply_copula_to_text(sent)
            except Exception:
                pass
            translated = _mt_translate(sent, "lun2en") or sent
            english_sentences.append(translated)
    else:
        english_sentences = sentences

    # Extractive summarization — score sentences by position + keyword frequency
    from collections import Counter
    all_words = " ".join(english_sentences).lower().split()
    stopwords = {"the","a","an","and","or","but","in","on","at","to","for","of","with","is","was","are","were","be","been","it","this","that","as","by","from","have","has","had","not","he","she","they","we","i","you","his","her","their","its","my","our","your"}
    word_freq = Counter(w for w in all_words if w not in stopwords and len(w) > 3)

    def score_sentence(sent: str, idx: int, total: int) -> float:
        words = sent.lower().split()
        freq_score = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
        # Boost first and last sentences
        position_score = 1.5 if idx < total * 0.15 else (1.2 if idx > total * 0.85 else 1.0)
        return freq_score * position_score

    scored = [(score_sentence(s, i, len(english_sentences)), s)
              for i, s in enumerate(english_sentences)]
    scored.sort(key=lambda x: -x[0])

    # Pick top sentences — roughly 20% of document or max 10
    top_n = max(3, min(10, len(english_sentences) // 5))
    top_sentences = [s for _, s in scored[:top_n]]

    # Re-order by original position for coherent reading
    order = {s: i for i, s in enumerate(english_sentences)}
    top_sentences.sort(key=lambda s: order.get(s, 0))

    summary = " ".join(top_sentences)

    # Translate the English summary to Lunyoro sentence-by-sentence
    from translate import _mt_translate, _nllb_translate
    import re as _re2

    def _translate_summary(text: str, use_nllb: bool) -> str:
        sentences = _re2.split(r'(?<=[.!?])\s+', text.strip())
        out = []
        for sent in sentences:
            if len(sent.strip()) < 3:
                out.append(sent)
                continue
            if use_nllb:
                result = _nllb_translate(sent, "en2lun") or _mt_translate(sent, "en2lun") or sent
            else:
                result = _mt_translate(sent, "en2lun") or sent
            # Apply all grammar rules (including gr4) to Lunyoro output
            try:
                from language_rules_gr4 import apply_gr4_rules
                result = apply_gr4_rules(result, direction="en->lun")
            except Exception:
                pass
            out.append(result)
        return " ".join(out)

    summary_lunyoro_marian = _translate_summary(summary, use_nllb=False)
    summary_lunyoro_nllb   = _translate_summary(summary, use_nllb=True)
    summary_lunyoro = summary_lunyoro_nllb or summary_lunyoro_marian

    # ── Qwen refinement pass (both models independently) ─────────────────────
    def _qwen_refine(draft: str) -> str:
        """Refine a single MT draft with Qwen. Returns draft unchanged on failure."""
        try:
            _hf_token = os.getenv("HF_TOKEN", "")
            _hf_model = os.getenv("HF_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            if not _hf_token:
                return draft
            from openai import OpenAI as _OpenAI
            from language_rules_gr4 import get_gr4_grammar_context, apply_gr4_rules
            _grammar_hint = (_GRAMMAR_CONTEXT_CACHE or "")[:2000] + get_gr4_grammar_context()[:1000]
            _refine_prompt = (
                "You are a Runyoro-Rutooro language expert. "
                "You will be given an English text and a machine-translated Runyoro-Rutooro draft. "
                "Improve the draft for accuracy, natural flow, and correct grammar.\n"
                f"Grammar rules:\n{_grammar_hint}\n\n"
                "Rules:\n"
                "- Keep the same meaning as the English source\n"
                "- Fix grammar errors, noun class prefixes, concordial agreement\n"
                "- Apply R/L rule: L only before/after e or i\n"
                "- Apply apostrophe elision: na ente → n'ente\n"
                "- Output ONLY the improved Runyoro-Rutooro text, nothing else\n"
            )
            _client = _OpenAI(base_url="https://router.huggingface.co/v1", api_key=_hf_token)
            _resp = _client.chat.completions.create(
                model=_hf_model,
                messages=[
                    {"role": "system", "content": _refine_prompt},
                    {"role": "user", "content": (
                        f"English source:\n{summary}\n\n"
                        f"MT draft:\n{draft}\n\n"
                        "Improved translation:"
                    )},
                ],
                max_tokens=1024,
                temperature=0.2,
            )
            refined = _resp.choices[0].message.content.strip()
            if refined and len(refined) > 10:
                refined = apply_gr4_rules(refined, direction="en->lun")
                return refined
        except Exception:
            pass
        return draft

    summary_lunyoro_marian_refined = _qwen_refine(summary_lunyoro_marian)
    summary_lunyoro_nllb_refined   = _qwen_refine(summary_lunyoro_nllb) if summary_lunyoro_nllb else summary_lunyoro_nllb
    # Primary output: prefer NLLB-refined, fall back to Marian-refined
    summary_lunyoro_best = summary_lunyoro_nllb_refined or summary_lunyoro_marian_refined

    save_history({
        "input": f"[DOC Summary] {file.filename}",
        "direction": "en→lun",
        "translation": summary_lunyoro_best[:200] + "..." if len(summary_lunyoro_best) > 200 else summary_lunyoro_best,
        "method": "extractive_summary+qwen",
        "confidence": None,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "filename": file.filename,
        "total_pages": full_text.count("\f") + 1 if file.filename.lower().endswith(".pdf") else 1,
        "total_sentences": total_sentences,
        "language_detected": "lunyoro" if is_lunyoro else "english",
        "summary": summary,
        "summary_lunyoro": summary_lunyoro_best,
        "summary_lunyoro_marian": summary_lunyoro_marian_refined,
        "summary_lunyoro_nllb": summary_lunyoro_nllb_refined,
        "sentences_used": top_n,
    }


class ChatRequest(BaseModel):
    message: str
    history: list = []
    sector: str | None = None
    conversation_mode: bool = False


@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    """AI Language Assistant — LLM-powered generative replies about Runyoro-Rutooro."""
    import re, requests as _requests
    from translate import _mt_translate, _load_retrieval, _normalise, _index, _sem_model
    from language_rules import EMPAAKO, PROVERBS, NUMBERS
    import numpy as np
    from sentence_transformers import util as st_util

    # Rate limit: 5 requests per 60s per IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_chat_rate(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment before sending another message.")

    _load_retrieval()
    from translate import _dictionary

    msg    = _normalise(req.message.strip())
    sector = (req.sector or "").upper()

    SECTOR_LABELS = {
        "CUL": "Culture & Traditions", "ART": "Arts & Music",
        "AGR": "Agriculture",          "ENV": "Environment & Nature",
        "EDU": "Education",            "SPR": "Spirituality",
        "DLY": "Daily Life",           "NAR": "Storytelling",
        "ECO": "Economy & Trade",      "GOV": "Governance",
        "HIS": "History",              "HLT": "Health",
        "POL": "Politics",             "ALL": "All Sectors",
    }

    def to_runyoro_marian(text: str) -> str:
        """Translate using MarianMT only (primary)."""
        import re as _r
        lines = text.split("\n")
        out = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                out.append(""); continue
            bullet_match = _r.match(r'^([*\-•]\s*|\d+\.\s*)', stripped)
            marker = bullet_match.group(0) if bullet_match else ""
            content = stripped[len(marker):].strip() if bullet_match else stripped
            if not content:
                out.append(line); continue
            sentences = _r.split(r'(?<=[.!?])\s+', content)
            out.append(marker + " ".join(
                _mt_translate(s, "en2lun") or s for s in sentences if len(s.strip()) >= 3
            ))
        return "\n".join(out)

    def to_runyoro_nllb(text: str) -> str:
        """Translate using NLLB-200 only (comparison)."""
        import re as _r
        lines = text.split("\n")
        out = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                out.append(""); continue
            bullet_match = _r.match(r'^([*\-•]\s*|\d+\.\s*)', stripped)
            marker = bullet_match.group(0) if bullet_match else ""
            content = stripped[len(marker):].strip() if bullet_match else stripped
            if not content:
                out.append(line); continue
            sentences = _r.split(r'(?<=[.!?])\s+', content)
            out.append(marker + " ".join(
                _nllb_translate(s, "en2lun") or s for s in sentences if len(s.strip()) >= 3
            ))
        return "\n".join(out)

    # ── Retrieve relevant corpus context ─────────────────────────────────────
    def corpus_context(query: str, k: int = 2) -> str:
        q_emb  = _sem_model.encode(query, convert_to_numpy=True)
        scores = st_util.cos_sim(q_emb, _index["embeddings"])[0].numpy()
        top    = np.argsort(scores)[::-1][:k]
        pairs  = []
        for i in top:
            if float(scores[i]) > 0.2:
                en  = _index["english_sentences"][i][:120]
                lun = _index["lunyoro_sentences"][i][:120]
                pairs.append(f'  "{en}" → "{lun}"')
        return "\n".join(pairs)

    def dict_context(code: str, n: int = 4) -> str:
        if code == "ALL":
            entries = [d for d in _dictionary if d.get("word") and d.get("definitionEnglish")][:n]
        else:
            entries = [d for d in _dictionary
                       if (d.get("domain") or "").upper() == code
                       and d.get("word") and d.get("definitionEnglish")][:n]
        return "\n".join(f'  {e["word"]} = {e["definitionEnglish"]}' for e in entries)

    # ── Build system prompt ───────────────────────────────────────────────────
    corpus_ctx   = corpus_context(msg)
    sector_label = SECTOR_LABELS.get(sector, "")
    dict_ctx     = dict_context(sector) if sector else ""
    grammar_ctx  = (_GRAMMAR_CONTEXT_CACHE or "")[:3000]

    system_prompt = (
        "You are an expert AI assistant for the Runyoro-Rutooro language of the Bunyoro-Kitara and Tooro kingdoms in Uganda.\n"
        "RULES:\n"
        "1. Write your ENTIRE reply in English only. Do NOT include any Runyoro or Rutooro words.\n"
        "2. Be informative and well-explained — aim for 2-4 solid paragraphs.\n"
        "3. Always explain the grammar rule behind any concept (noun class, verb prefix, tense marker, concordial agreement, etc.).\n"
        "4. Stay context-aware: use the conversation history and corpus examples provided.\n"
        "5. Write in flowing prose. No bullet lists, no headers.\n"
        "6. Do not mix languages. Every word must be English.\n"
        f"\nGrammar rules reference:\n{grammar_ctx}\n"
    )
    if corpus_ctx:
        system_prompt += f"\nRelevant corpus examples for context:\n{corpus_ctx}\n"
    if sector_label:
        system_prompt += f"\nSector focus: {sector_label}\n"
    if dict_ctx:
        system_prompt += f"Vocabulary reference:\n{dict_ctx}\n"
    system_prompt += "\nRemember: reply in plain English prose only. Be thorough but avoid unnecessary padding."

    # ── Build message history for Ollama ─────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for turn in (req.history or [])[-8:]:
        role    = turn.get("role", "")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": msg})

    # ── Call HuggingFace Router (Qwen2.5) ────────────────────────────────────
    _hf_token = os.getenv("HF_TOKEN", "")
    _hf_model = os.getenv("HF_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    try:
        from openai import OpenAI
        _hf_client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=_hf_token,
            timeout=45.0,
        )
        completion = _hf_client.chat.completions.create(
            model=_hf_model,
            messages=messages,
            max_tokens=600,
            temperature=0.6,
        )
        reply_en = completion.choices[0].message.content.strip()
    except Exception as e:
        import logging
        logging.warning(f"HF Router call failed: {e}")
        reply_en = None

    # ── Translate reply with both models in parallel ──────────────────────────
    from language_rules import apply_rl_rule_to_text
    import concurrent.futures as _cf

    marian_out = nllb_out = None
    if reply_en:
        with _cf.ThreadPoolExecutor(max_workers=2) as pool:
            f_marian = pool.submit(to_runyoro_marian, reply_en)
            f_nllb   = pool.submit(to_runyoro_nllb,   reply_en)
            marian_out = f_marian.result()
            nllb_out   = f_nllb.result()
        if marian_out:
            marian_out = apply_rl_rule_to_text(_clean_translation(marian_out))
        if nllb_out:
            nllb_out = apply_rl_rule_to_text(_clean_translation(nllb_out))

    if not marian_out and not nllb_out:
        # If LLM replied but translation failed, return English reply
        if reply_en:
            return {"reply": reply_en, "reply_marian": None, "reply_nllb": None}
        return {"reply": "Sorry, the chat assistant is unavailable right now. Please try again.",
                "reply_marian": None, "reply_nllb": None}

    return {
        "reply":         nllb_out or marian_out,  # NLLB is primary
        "reply_marian":  marian_out,
        "reply_nllb":    nllb_out,
    }

@app.get("/language-rules")
def get_language_rules():
    """Return language rules, interjections, idioms, numbers and proverbs."""
    from language_rules import (
        RL_RULE, EMPAAKO, INTERJECTIONS, IDIOMS, NUMBERS, PROVERBS,
        get_grammar_context, get_full_grammar_context,
        NOUN_CLASSES, CONCORDIAL_AGREEMENT, TENSES, VERB_SUFFIXES,
        DERIVATIVE_SUFFIXES, CONJUNCTIONS, PREPOSITIONS, NEGATION_WORDS,
        ADJECTIVE_STEMS, ADVERBS_OF_MANNER, PERSONAL_PRONOUNS,
        COMPARISON_POSITIVE, COMPARISON_COMPARATIVE, COMPARISON_SUPERLATIVE,
        GENITIVE_PARTICLES, CONDITIONAL_MOOD, COORDINATING_PARTICLES,
        ADVERBIAL_PARTICLES, SIMILES,
        NASAL_ASSIMILATION, NI_PREFIX_CHANGE, CONSONANT_SUFFIX_CHANGES,
        CONVERSIVE_SUFFIX, SUBJECT_PREFIXES, TENSE_MARKERS, NUMERAL_CONCORDS,
        # OCR extension
        IMPERATIVE_TENSES, INDICATIVE_TENSES, SUBJUNCTIVE_FUNCTIONS,
        VERB_INA_CONJUGATION, VERB_LI_CONJUGATION,
        CAUSATIVE_FORMATION, PASSIVE_FORMATION, NEUTER_FORMATION,
        RECIPROCAL_FORMATION, CONVERSIVE_EXAMPLES,
        DEVERBATIVE_SUFFIXES, NOUN_FUNCTIONS, NOUN_KINDS,
        NEGATION_EXTENDED, AFFIRMATION_WORDS, INTERROGATIVE_PARTICLES,
        PARTS_OF_SPEECH, IDEOPHONES,
        ORDINAL_FORMATION, ORDINALS_EXTENDED, NUMERAL_ADVERBIAL_KA,
        CLASS_12_13_14_DETAILS, ORTHOGRAPHY_RULES,
        REFLEXIVE_IMPERATIVES, Y_INSERTION_EXAMPLES,
    )
    return {
        # Core
        "rl_rule":              RL_RULE.strip(),
        "grammar_summary":      get_grammar_context().strip(),
        "full_grammar_context": get_full_grammar_context().strip(),
        # Cultural
        "empaako":              EMPAAKO,
        "interjections":        INTERJECTIONS,
        "idioms":               IDIOMS,
        "numbers":              {str(k): v for k, v in NUMBERS.items()},
        "proverbs":             PROVERBS,
        # Noun system
        "noun_classes":         {str(k): v for k, v in NOUN_CLASSES.items()},
        "concordial_agreement": {str(k): v for k, v in CONCORDIAL_AGREEMENT.items()},
        "class_12_13_14":       CLASS_12_13_14_DETAILS,
        "noun_functions":       NOUN_FUNCTIONS,
        "noun_kinds":           NOUN_KINDS,
        "deverbative_suffixes": DEVERBATIVE_SUFFIXES,
        # Verb system
        "tenses":               TENSES,
        "imperative_tenses":    IMPERATIVE_TENSES,
        "indicative_tenses":    INDICATIVE_TENSES,
        "subjunctive_functions":SUBJUNCTIVE_FUNCTIONS,
        "verb_suffixes":        VERB_SUFFIXES,
        "derivative_suffixes":  DERIVATIVE_SUFFIXES,
        "causative_formation":  CAUSATIVE_FORMATION,
        "passive_formation":    PASSIVE_FORMATION,
        "neuter_formation":     NEUTER_FORMATION,
        "reciprocal_formation": RECIPROCAL_FORMATION,
        "conversive_examples":  CONVERSIVE_EXAMPLES,
        "reflexive_imperatives":REFLEXIVE_IMPERATIVES,
        "y_insertion_examples": Y_INSERTION_EXAMPLES,
        "verb_ina":             VERB_INA_CONJUGATION,
        "verb_li":              VERB_LI_CONJUGATION,
        # Sound change rules (data)
        "nasal_assimilation":   NASAL_ASSIMILATION,
        "ni_prefix_change":     NI_PREFIX_CHANGE,
        "consonant_suffix_changes": {str(k): v for k, v in CONSONANT_SUFFIX_CHANGES.items()},
        "conversive_suffix_map":CONVERSIVE_SUFFIX,
        "subject_prefixes":     SUBJECT_PREFIXES,
        "tense_markers":        TENSE_MARKERS,
        "numeral_concords":     {str(k): v for k, v in NUMERAL_CONCORDS.items()},
        # Particles & grammar words
        "conjunctions":         CONJUNCTIONS,
        "prepositions":         PREPOSITIONS,
        "negation_words":       NEGATION_WORDS,
        "negation_extended":    NEGATION_EXTENDED,
        "affirmation_words":    AFFIRMATION_WORDS,
        "interrogatives":       INTERROGATIVE_PARTICLES,
        "coordinating_particles": COORDINATING_PARTICLES,
        "adverbial_particles":  ADVERBIAL_PARTICLES,
        "genitive_particles":   GENITIVE_PARTICLES,
        "conditional_mood":     CONDITIONAL_MOOD,
        # Adjectives & comparison
        "adjective_stems":      ADJECTIVE_STEMS,
        "adverbs_of_manner":    ADVERBS_OF_MANNER,
        "comparison_positive":  COMPARISON_POSITIVE,
        "comparison_comparative": COMPARISON_COMPARATIVE,
        "comparison_superlative": COMPARISON_SUPERLATIVE,
        "similes":              SIMILES,
        # Numbers & ordinals
        "ordinal_formation":    ORDINAL_FORMATION,
        "ordinals_extended":    ORDINALS_EXTENDED,
        "numeral_adverbial_ka": NUMERAL_ADVERBIAL_KA,
        # Pronouns
        "personal_pronouns":    PERSONAL_PRONOUNS,
        # Parts of speech & ideophones
        "parts_of_speech":      PARTS_OF_SPEECH,
        "ideophones":           IDEOPHONES,
        # Orthography
        "orthography_rules":    ORTHOGRAPHY_RULES,
        # Grammar Rules 4 (new)
        **_get_gr4_rules(),
    }


def _get_gr4_rules() -> dict:
    """Load Grammar Rules 4 data for the /language-rules endpoint."""
    try:
        from language_rules_gr4 import (
            ENUMERATIVE_PRONOUNS, DEMONSTRATIVES_NEAR_FULL,
            DEMONSTRATIVES_FAR_FULL, DEMONSTRATIVES_IN_MIND_FULL,
            SUBJECT_RELATIVE_CONCORDS_FULL, OBJECT_RELATIVE_CONCORDS_FULL,
            MODAL_TA_PATTERNS, DARA_PRONOUNS, DARA_NOUN_CLASSES,
            COPULA_NI_PRONOUNS, COPULA_N_NEAR, COPULA_N_FAR, COPULA_RULES,
            KA_EMPHATIC_PATTERNS, KA_PERMISSIVE_EXAMPLES,
            KINSHIP_TERMS, VERB_NOUN_DERIVATION, VERB_NOUN_EXAMPLES,
            GR4_GRAMMAR_CONTEXT,
        )
        return {
            "enumerative_pronouns":         ENUMERATIVE_PRONOUNS,
            "demonstratives_near":          {str(k): v for k, v in DEMONSTRATIVES_NEAR_FULL.items()},
            "demonstratives_far":           {str(k): v for k, v in DEMONSTRATIVES_FAR_FULL.items()},
            "demonstratives_in_mind":       {str(k): v for k, v in DEMONSTRATIVES_IN_MIND_FULL.items()},
            "subject_relative_concords":    {str(k): v for k, v in SUBJECT_RELATIVE_CONCORDS_FULL.items()},
            "object_relative_concords":     {str(k): v for k, v in OBJECT_RELATIVE_CONCORDS_FULL.items()},
            "modal_ta_patterns":            MODAL_TA_PATTERNS,
            "dara_pronouns":                DARA_PRONOUNS,
            "dara_noun_classes":            {str(k): v for k, v in DARA_NOUN_CLASSES.items()},
            "copula_ni_pronouns":           COPULA_NI_PRONOUNS,
            "copula_n_near":                {str(k): v for k, v in COPULA_N_NEAR.items()},
            "copula_n_far":                 {str(k): v for k, v in COPULA_N_FAR.items()},
            "copula_rules":                 COPULA_RULES,
            "ka_emphatic":                  KA_EMPHATIC_PATTERNS,
            "ka_permissive":                KA_PERMISSIVE_EXAMPLES,
            "kinship_terms":                KINSHIP_TERMS,
            "verb_noun_derivation":         VERB_NOUN_DERIVATION,
            "verb_noun_examples":           VERB_NOUN_EXAMPLES,
            "gr4_grammar_context":          GR4_GRAMMAR_CONTEXT,
        }
    except Exception:
        return {}


class ApplyRuleRequest(BaseModel):
    rule: str
    text: str = ""
    verb_stem: str = ""
    person: str = "3sg"
    tense: str = "present_imperfect"
    negative: bool = False
    noun_class: int = 1
    number: str = "singular"
    n: int = 1


@app.post("/language-rules/apply")
def apply_language_rule(req: ApplyRuleRequest):
    """
    Apply a specific Runyoro-Rutooro grammar rule programmatically.

    rule options:
      rl_rule              — apply R/L rule to text
      nasal_assimilation   — apply nasal assimilation to text
      ni_prefix_change     — apply ni→nu prefix change to text
      y_insertion          — insert y between tense prefix and vowel-initial stem
      consonant_suffix     — apply consonant+suffix sound change to verb_stem
      conversive           — build conversive form of verb_stem
      reflexive_imperative — build reflexive imperative from verb_stem (okw-e... infinitive)
      concordial_agreement — prefix adjective stem (text) with concord for noun_class
      build_plural         — build plural of noun (text)
      class9_nasal         — apply class 9 nasal prefix to stem (text)
      build_verb           — assemble full verb form (verb_stem, person, tense, negative)
      causative            — build causative form of verb_stem
      passive              — build passive form of verb_stem
      neuter               — build neuter/stative form of verb_stem
      reciprocal           — build reciprocal form of verb_stem
      adjective_concord    — get adjectival concord for noun_class
      demonstrative        — get demonstrative for noun_class
      numeral_concord      — get numeral concord for noun_class
      ordinal              — build ordinal n in agreement with noun_class
    """
    from language_rules import (
        apply_rl_rule_to_text, apply_nasal_assimilation, apply_ni_prefix_change,
        apply_y_insertion, apply_consonant_suffix_change, apply_conversive_suffix,
        apply_reflexive_imperative, apply_concordial_agreement, build_plural,
        apply_class9_nasal_prefix, build_verb_form, apply_causative, apply_passive,
        apply_neuter, apply_reciprocal, get_adjective_concord, get_demonstrative,
        get_numeral_concord, build_ordinal,
    )

    r = req.rule.lower().strip()
    try:
        if r == "rl_rule":
            return {"result": apply_rl_rule_to_text(req.text)}
        elif r == "nasal_assimilation":
            return {"result": apply_nasal_assimilation(req.text)}
        elif r == "ni_prefix_change":
            return {"result": apply_ni_prefix_change(req.text)}
        elif r == "y_insertion":
            # text = "subject_prefix:tense_prefix:verb_stem"
            parts = req.text.split(":")
            if len(parts) == 3:
                return {"result": apply_y_insertion(parts[0], parts[1], parts[2])}
            return {"result": apply_y_insertion("", req.tense, req.verb_stem)}
        elif r == "consonant_suffix":
            # text = suffix (e.g. "-ire"), verb_stem = stem
            return {"result": apply_consonant_suffix_change(req.verb_stem, req.text)}
        elif r == "conversive":
            return {"result": apply_conversive_suffix(req.verb_stem or req.text)}
        elif r == "reflexive_imperative":
            return {"result": apply_reflexive_imperative(req.verb_stem or req.text, req.number)}
        elif r == "concordial_agreement":
            return {"result": apply_concordial_agreement(req.text, req.noun_class)}
        elif r == "build_plural":
            result = build_plural(req.text)
            return {"result": result or "unknown"}
        elif r == "class9_nasal":
            return {"result": apply_class9_nasal_prefix(req.text)}
        elif r == "build_verb":
            return {"result": build_verb_form(req.verb_stem, req.person, req.tense, req.negative)}
        elif r == "causative":
            return {"result": apply_causative(req.verb_stem or req.text)}
        elif r == "passive":
            return {"result": apply_passive(req.verb_stem or req.text)}
        elif r == "neuter":
            return {"result": apply_neuter(req.verb_stem or req.text)}
        elif r == "reciprocal":
            return {"result": apply_reciprocal(req.verb_stem or req.text)}
        elif r == "adjective_concord":
            return {"result": get_adjective_concord(req.noun_class)}
        elif r == "demonstrative":
            return {"result": get_demonstrative(req.noun_class)}
        elif r == "numeral_concord":
            return {"result": get_numeral_concord(req.noun_class)}
        elif r == "ordinal":
            return {"result": build_ordinal(req.n, req.noun_class)}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown rule: '{req.rule}'. "
                "Valid rules: rl_rule, nasal_assimilation, ni_prefix_change, y_insertion, "
                "consonant_suffix, conversive, reflexive_imperative, concordial_agreement, "
                "build_plural, class9_nasal, build_verb, causative, passive, neuter, "
                "reciprocal, adjective_concord, demonstrative, numeral_concord, ordinal")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/language-rules/interjections")
def get_interjections():
    from language_rules import INTERJECTIONS
    return {"interjections": INTERJECTIONS}


@app.get("/language-rules/idioms")
def get_idioms():
    from language_rules import IDIOMS
    return {"idioms": IDIOMS}


@app.get("/language-rules/proverbs")
def get_proverbs():
    from language_rules import PROVERBS
    import random
    return {"proverbs": PROVERBS, "random": random.choice(PROVERBS)}


# ── Knowledge Graph endpoints ─────────────────────────────────────────────────

_kg = None

def _get_kg():
    """Lazy-load the knowledge graph singleton."""
    global _kg
    if _kg is None:
        try:
            from knowledge_graph import get_kg
            _kg = get_kg()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Knowledge graph unavailable: {e}")
    return _kg


@app.get("/knowledge-graph/stats")
def kg_stats():
    """Return knowledge graph statistics: node/edge counts by type."""
    kg = _get_kg()
    return kg.stats()


@app.get("/knowledge-graph/noun-class/{class_num}")
def kg_noun_class(class_num: str):
    """
    Get full info about a noun class including concords, plural class, and example words.
    class_num: 1-15 (integer) or '1a', '2a', '9a', '10a' (string classes)
    """
    kg = _get_kg()
    # Try int first, then string
    try:
        key = int(class_num)
    except ValueError:
        key = class_num
    result = kg.get_noun_class_info(key)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/knowledge-graph/explain/{word}")
def kg_explain_word(word: str):
    """
    Explain a Runyoro-Rutooro word: its noun class, derivation chain,
    plural/singular forms, and applicable grammar rules.
    Enables explainable AI translation.
    """
    kg = _get_kg()
    return kg.explain_word(word)


@app.get("/knowledge-graph/related/{word}")
def kg_related(word: str, rel: str | None = None, direction: str = "both"):
    """
    Find nodes related to a word in the knowledge graph.
    rel: optional relationship filter (e.g. DERIVES_FROM, PLURAL_IS, BELONGS_TO)
    direction: 'out', 'in', or 'both'
    """
    kg = _get_kg()
    results = kg.find_related(word, rel=rel, direction=direction)
    return {"word": word, "rel": rel, "direction": direction, "results": results}


@app.get("/knowledge-graph/path")
def kg_path(word_a: str, word_b: str):
    """
    Find the grammatical relationship path between two words.
    Example: /knowledge-graph/path?word_a=okulima&word_b=omulimi
    Returns the chain: okulima --[DERIVES_TO]--> omulimi --[BELONGS_TO]--> nc_1
    """
    kg = _get_kg()
    return kg.grammar_path(word_a, word_b)


@app.get("/knowledge-graph/correct")
def kg_correct(word: str, target: str):
    """
    Get the correct grammatical form of a word.
    target: 'plural', 'singular', 'agent_noun', 'action_noun', 'source_verb'
    Example: /knowledge-graph/correct?word=omulimi&target=plural
    """
    kg = _get_kg()
    return kg.correct_form(word, target)


class TutorRequest(BaseModel):
    question: str


@app.post("/knowledge-graph/tutor")
def kg_tutor(req: TutorRequest):
    """
    Answer a grammar tutoring question using the knowledge graph.
    Supports natural language questions like:
      - 'What is the plural of omuntu?'
      - 'What class is ekitabu?'
      - 'What is the agent noun of okulima?'
      - 'What does omulimi mean?'
    """
    kg = _get_kg()
    return kg.tutor_question(req.question)


@app.get("/knowledge-graph/search")
def kg_search(q: str, node_type: str | None = None):
    """
    Search the knowledge graph by label.
    q: search string (case-insensitive substring match)
    node_type: optional filter (WORD, NOUN_CLASS, TENSE, RULE, DERIVATION, etc.)
    """
    kg = _get_kg()
    results = kg.find_nodes(node_type=node_type, label_contains=q)
    return {"query": q, "node_type": node_type, "count": len(results), "results": results[:50]}


@app.get("/knowledge-graph/export")
def kg_export():
    """
    Export the full knowledge graph as JSON.
    Returns all nodes and edges — useful for frontend graph visualisation.
    """
    kg = _get_kg()
    import json
    data = json.loads(kg.to_json())
    return data


@app.get("/knowledge-graph/tenses")
def kg_tenses():
    """Return all tense nodes with their markers and examples."""
    kg = _get_kg()
    tenses = kg.find_nodes(node_type="TENSE")
    return {"tenses": tenses, "count": len(tenses)}


@app.get("/knowledge-graph/derivations")
def kg_derivations():
    """Return all verb derivation types with their suffixes."""
    kg = _get_kg()
    derivations = kg.find_nodes(node_type="DERIVATION")
    return {"derivations": derivations, "count": len(derivations)}


# ── Camera OCR Translation (AI Stick Lens) ────────────────────────────────────
import base64
import io
from typing import Optional

# Global OCR state
_ocr_reader = None
_ocr_engine = None  # "easyocr" or "tesseract"


def _get_ocr_engine():
    """Initialize OCR engine — EasyOCR preferred, Tesseract fallback."""
    global _ocr_reader, _ocr_engine
    if _ocr_engine:
        return _ocr_engine

    try:
        import easyocr
        import torch
        use_gpu = torch.cuda.is_available()
        _ocr_reader = easyocr.Reader(["en"], gpu=use_gpu)
        _ocr_engine = "easyocr"
        print(f"[ocr] Using EasyOCR engine (GPU={use_gpu})")
    except ImportError:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            _ocr_engine = "tesseract"
            print("[ocr] Using Tesseract OCR engine")
        except Exception:
            _ocr_engine = "none"
            print("[ocr] No OCR engine available")
    return _ocr_engine


def _run_ocr(img):
    """Run OCR on an image (numpy array). Returns list of (bbox, text, confidence)."""
    import numpy as np
    engine = _get_ocr_engine()

    if engine == "easyocr":
        global _ocr_reader
        if _ocr_reader is None:
            import easyocr
            import torch
            _ocr_reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
        return _ocr_reader.readtext(img)

    elif engine == "tesseract":
        import pytesseract
        from PIL import Image
        # Convert BGR to RGB for PIL
        if len(img.shape) == 3:
            pil_img = Image.fromarray(img[:, :, ::-1])
        else:
            pil_img = Image.fromarray(img)

        # Get bounding box data from Tesseract
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        results = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i]) if data["conf"][i] != "-1" else 0
            if not text or conf < 30:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
            results.append((bbox, text, conf / 100.0))
        return results

    return []


def _translate_region(text: str, direction: str) -> str:
    """Translate a detected text region using NLLB (primary) + MarianMT fallback."""
    from translate import _nllb_translate, _mt_translate
    if direction == "en->lun":
        translation = _nllb_translate(text, "en2lun")
        if not translation:
            translation = _mt_translate(text, "en2lun")
    else:
        translation = _nllb_translate(text, "lun2en")
        if not translation:
            translation = _mt_translate(text, "lun2en")
    return translation or text


@app.post("/ocr-translate")
async def ocr_translate(file: UploadFile = File(...), direction: str = "en->lun"):
    """Accept an image file, run OCR to detect text, translate, return bounding boxes."""
    import numpy as np

    engine = _get_ocr_engine()
    if engine == "none":
        return {"error": "No OCR engine available. Install easyocr or tesseract."}

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)

    try:
        import cv2
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except ImportError:
        # Fallback: use PIL
        from PIL import Image
        pil_img = Image.open(io.BytesIO(contents))
        img = np.array(pil_img)

    if img is None:
        return {"error": "Could not decode image"}

    h, w = img.shape[:2]
    results = _run_ocr(img)

    translated_regions = []
    for (bbox, text, confidence) in results:
        if confidence < 0.3 or not text.strip():
            continue

        x_min = int(min(p[0] for p in bbox))
        y_min = int(min(p[1] for p in bbox))
        x_max = int(max(p[0] for p in bbox))
        y_max = int(max(p[1] for p in bbox))

        translation = _translate_region(text, direction)

        translated_regions.append({
            "original": text,
            "translated": translation,
            "confidence": round(confidence, 2),
            "bbox": {"x": x_min, "y": y_min, "width": x_max - x_min, "height": y_max - y_min},
            "bbox_norm": {
                "x": round(x_min / w, 4),
                "y": round(y_min / h, 4),
                "width": round((x_max - x_min) / w, 4),
                "height": round((y_max - y_min) / h, 4),
            }
        })

    return {
        "regions": translated_regions,
        "image_size": {"width": w, "height": h},
        "direction": direction,
        "total_detected": len(results),
        "total_translated": len(translated_regions),
        "engine": engine,
    }


@app.post("/ocr-translate-base64")
async def ocr_translate_base64(request: Request):
    """Accept a base64 image frame (from camera), run OCR + translate."""
    import numpy as np

    engine = _get_ocr_engine()
    if engine == "none":
        return {"error": "No OCR engine available"}

    body = await request.json()
    image_data = body.get("image", "")
    direction = body.get("direction", "en->lun")

    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        try:
            import cv2
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except ImportError:
            from PIL import Image
            pil_img = Image.open(io.BytesIO(img_bytes))
            img = np.array(pil_img)
    except Exception as e:
        return {"error": f"Could not decode image: {e}"}

    if img is None:
        return {"error": "Invalid image data"}

    h, w = img.shape[:2]
    results = _run_ocr(img)

    translated_regions = []
    for (bbox, text, confidence) in results:
        if confidence < 0.3 or not text.strip():
            continue

        x_min = int(min(p[0] for p in bbox))
        y_min = int(min(p[1] for p in bbox))
        x_max = int(max(p[0] for p in bbox))
        y_max = int(max(p[1] for p in bbox))

        translation = _translate_region(text, direction)

        translated_regions.append({
            "original": text,
            "translated": translation,
            "confidence": round(confidence, 2),
            "bbox_norm": {
                "x": round(x_min / w, 4),
                "y": round(y_min / h, 4),
                "width": round((x_max - x_min) / w, 4),
                "height": round((y_max - y_min) / h, 4),
            }
        })

    return {
        "regions": translated_regions,
        "image_size": {"width": w, "height": h},
        "direction": direction,
        "engine": engine,
    }


# ── Image Classification & Translation ────────────────────────────────────────

@app.post("/classify-image")
async def classify_image(file: UploadFile = File(...), top_k: int = 5):
    """
    Upload an image → classify objects with MobileNetV2 → translate labels to Runyoro.

    Returns top-K predictions with English labels and their Runyoro translations.
    Supported formats: JPEG, PNG, WebP (validated via magic bytes).
    Max file size: 10 MB.
    """
    from image_classifier import image_classifier, validate_image_upload

    # Check model readiness
    if not image_classifier.is_ready():
        load_err = image_classifier.get_load_error()
        if load_err:
            raise HTTPException(status_code=503, detail=f"Image classifier failed to load: {load_err}")
        raise HTTPException(status_code=503, detail="Image classifier is still loading. Try again in a moment.")

    # Read and validate
    contents = await file.read()
    try:
        validated_bytes = validate_image_upload(
            content_type=file.content_type,
            filename=file.filename,
            file_bytes=contents,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Classify
    try:
        predictions = image_classifier.classify(validated_bytes, top_k=min(top_k, 10))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Translate each English label to Runyoro
    results = []
    for pred in predictions:
        label_en = pred["label"]
        translation_result = translate(label_en)
        label_lun = translation_result.get("translation", label_en)
        results.append({
            "label_en": label_en,
            "label_lun": label_lun,
            "confidence": pred["confidence"],
            "method": translation_result.get("method", "unknown"),
        })

    return {
        "predictions": results,
        "top_k": len(results),
        "model": "google/mobilenet_v2_1.0_224",
    }


@app.get("/classify-image/status")
def classify_image_status():
    """Check whether the image classification model is ready."""
    from image_classifier import image_classifier
    return {
        "ready": image_classifier.is_ready(),
        "error": image_classifier.get_load_error(),
    }

