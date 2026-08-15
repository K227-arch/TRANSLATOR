"""
Pi Sidecar Service
==================
Lightweight FastAPI app that runs alongside the C++ translator on the Pi,
handling the 5 endpoints the C++ backend doesn't implement:

  - POST /classify-image       (MobileNetV2 image classification + translation)
  - GET  /classify-image/status
  - POST /translate-batch      (bulk translation, proxies to C++ /translate)
  - POST /translate-batch-file (file upload → batch translate)
  - POST /summarize-pdf        (extractive summarization + translation)
  - GET  /language-rules       (static grammar data)
  - GET  /language-rules/interjections
  - GET  /language-rules/idioms
  - GET  /language-rules/proverbs
  - POST /language-rules/apply

Runs on port 8001. Nginx on port 80 routes these paths here, everything else
goes to the C++ backend on port 8080.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8001

Resource budget:
    - MobileNetV2: ~14MB model + ~50MB runtime
    - pdfplumber: ~30MB peak during extraction
    - Total steady-state: ~100-200MB additional RAM
"""

import asyncio
import io
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
CPP_BACKEND = os.getenv("CPP_BACKEND_URL", "http://127.0.0.1:8080")
MODEL_DIR = Path(__file__).parent / "models"
MOBILENET_DIR = MODEL_DIR / "mobilenet_v2"

app = FastAPI(title="Lunyoro Translator Pi Sidecar", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

_classifier_model = None
_classifier_processor = None
_classifier_ready = False
_classifier_error: Optional[str] = None

SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


def _detect_mime(data: bytes) -> Optional[str]:
    if not data:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and len(data) > 11 and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _load_classifier():
    """Load MobileNetV2 from local cache at startup."""
    global _classifier_model, _classifier_processor, _classifier_ready, _classifier_error

    try:
        from transformers import (
            MobileNetV2ForImageClassification,
            MobileNetV2ImageProcessor,
        )

        if not MOBILENET_DIR.is_dir() or not any(MOBILENET_DIR.iterdir()):
            _classifier_error = (
                f"MobileNetV2 model not found at {MOBILENET_DIR}. "
                "Run: python download_model.py"
            )
            print(f"[classify] {_classifier_error}")
            return

        print(f"[classify] Loading MobileNetV2 from {MOBILENET_DIR} ...")
        t0 = time.time()
        _classifier_processor = MobileNetV2ImageProcessor.from_pretrained(str(MOBILENET_DIR))
        _classifier_model = MobileNetV2ForImageClassification.from_pretrained(str(MOBILENET_DIR))
        _classifier_model.eval()
        _classifier_ready = True
        print(f"[classify] Model loaded in {time.time() - t0:.1f}s")

    except Exception as e:
        _classifier_error = str(e)
        print(f"[classify] FAILED: {e}")


def _classify_image(image_bytes: bytes, top_k: int = 5) -> list[dict]:
    """Run classification on raw image bytes."""
    import torch
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = _classifier_processor(images=image, return_tensors="pt")

    with torch.no_grad():
        logits = _classifier_model(**inputs).logits

    probs = torch.nn.functional.softmax(logits, dim=-1)[0]
    top_probs, top_indices = torch.topk(probs, min(top_k, len(probs)))

    results = []
    for prob, idx in zip(top_probs, top_indices):
        label = _classifier_model.config.id2label[idx.item()]
        label = label.split(",")[0].strip().lower()
        results.append({"label": label, "confidence": round(prob.item(), 4)})
    return results


async def _translate_label(label: str) -> dict:
    """Translate an English label to Lunyoro via the C++ backend, returning both models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CPP_BACKEND}/translate",
                json={"text": label},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "translation": data.get("translation", label),
                    "translation_nllb": data.get("translation_nllb"),
                    "translation_marian": data.get("translation_marian"),
                    "method": data.get("method", "unknown"),
                }
    except Exception:
        pass
    return {"translation": label, "translation_nllb": None, "translation_marian": None, "method": "passthrough"}


@app.post("/classify-image")
async def classify_image(file: UploadFile = File(...), top_k: int = Query(5, le=10)):
    if not _classifier_ready:
        if _classifier_error:
            raise HTTPException(503, f"Image classifier failed to load: {_classifier_error}")
        raise HTTPException(503, "Image classifier is still loading.")

    contents = await file.read()

    # Validate
    if not contents:
        raise HTTPException(400, "File is empty.")
    mime = _detect_mime(contents)
    if mime not in SUPPORTED_IMAGE_MIMES:
        raise HTTPException(400, "Unsupported format. Accepted: JPEG, PNG, WebP.")
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"File too large. Max 10 MB, got {len(contents)/1e6:.1f} MB.")

    # Classify
    try:
        predictions = _classify_image(contents, top_k=top_k)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Classification failed: {e}")

    # Translate labels in parallel
    tasks = [_translate_label(p["label"]) for p in predictions]
    translations = await asyncio.gather(*tasks)

    results = []
    for pred, tr in zip(predictions, translations):
        results.append({
            "label_en": pred["label"],
            "label_lun": tr["translation"],
            "label_lun_nllb": tr.get("translation_nllb"),
            "label_lun_marian": tr.get("translation_marian"),
            "confidence": pred["confidence"],
            "method": tr["method"],
        })

    return {"predictions": results, "top_k": len(results), "model": "google/mobilenet_v2_1.0_224"}


@app.get("/classify-image/status")
def classify_image_status():
    return {"ready": _classifier_ready, "error": _classifier_error}


# ══════════════════════════════════════════════════════════════════════════════
# BATCH TRANSLATION (proxies to C++ backend)
# ══════════════════════════════════════════════════════════════════════════════

class BatchTranslateRequest(BaseModel):
    sentences: list[str]
    direction: str = "en->lun"


@app.post("/translate-batch")
async def translate_batch(req: BatchTranslateRequest):
    if not req.sentences:
        raise HTTPException(400, "No sentences provided")
    if len(req.sentences) > 100:
        raise HTTPException(400, "Maximum 100 sentences per batch")

    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for sentence in req.sentences:
            text = sentence.strip()
            if not text:
                results.append({"source": sentence, "translation": "", "method": "skipped"})
                continue
            if len(text) > 1000:
                results.append({"source": sentence, "translation": "", "method": "error", "error": "Too long"})
                continue

            endpoint = "/translate-reverse" if req.direction == "lun->en" else "/translate"
            try:
                resp = await client.post(f"{CPP_BACKEND}{endpoint}", json={"text": text})
                if resp.status_code == 200:
                    data = resp.json()
                    results.append({
                        "source": text,
                        "translation": data.get("translation", ""),
                        "method": data.get("method", "unknown"),
                        "confidence": data.get("confidence"),
                    })
                else:
                    results.append({"source": text, "translation": "", "method": "error", "error": "Backend error"})
            except Exception:
                results.append({"source": text, "translation": "", "method": "error", "error": "Connection failed"})

    return {"results": results, "total": len(results), "direction": req.direction}


@app.post("/translate-batch-file")
async def translate_batch_file(file: UploadFile = File(...), direction: str = "en->lun"):
    import csv as _csv

    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".txt"):
        raise HTTPException(400, "Only .csv and .txt files are supported")

    contents = await file.read()
    try:
        text_content = contents.decode("utf-8")
    except UnicodeDecodeError:
        text_content = contents.decode("latin-1")

    # Extract sentences
    sentences = []
    if ext == ".csv":
        reader = _csv.reader(io.StringIO(text_content))
        for row in reader:
            if row and row[0].strip():
                sentences.append(row[0].strip())
    else:
        for line in text_content.split("\n"):
            if line.strip():
                sentences.append(line.strip())

    if not sentences:
        raise HTTPException(400, "No text found in file")
    if len(sentences) > 200:
        sentences = sentences[:200]

    # Translate via batch endpoint
    batch_req = BatchTranslateRequest(sentences=sentences, direction=direction)
    result = await translate_batch(batch_req)

    return {
        "results": result["results"],
        "total": result["total"],
        "direction": direction,
        "filename": file.filename,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PDF / DOCUMENT SUMMARIZATION
# ══════════════════════════════════════════════════════════════════════════════

SUPPORTED_DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def _extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from uploaded document."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        import pdfplumber

        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    elif ext in (".docx", ".doc"):
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".txt":
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")

    raise ValueError(f"Unsupported file type: {ext}")


async def _translate_sentence(client: httpx.AsyncClient, text: str, direction: str) -> dict:
    """Translate a single sentence via the C++ backend, returning both model outputs."""
    endpoint = "/translate-reverse" if direction == "lun->en" else "/translate"
    try:
        resp = await client.post(f"{CPP_BACKEND}{endpoint}", json={"text": text})
        if resp.status_code == 200:
            data = resp.json()
            return {
                "translation": data.get("translation", text),
                "translation_nllb": data.get("translation_nllb"),
                "translation_marian": data.get("translation_marian"),
                "method": data.get("method", "unknown"),
            }
    except Exception:
        pass
    return {"translation": text, "translation_nllb": None, "translation_marian": None, "method": "passthrough"}


@app.post("/summarize-pdf")
async def summarize_pdf(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_DOC_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type. Supported: {', '.join(SUPPORTED_DOC_EXTENSIONS)}")

    contents = await file.read()
    try:
        full_text = _extract_text(file.filename, contents)
    except Exception as e:
        raise HTTPException(400, f"Could not extract text: {e}")

    if not full_text or len(full_text.strip()) < 20:
        raise HTTPException(400, "No text found in document")

    # Split into sentences
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if len(s.strip()) > 10]
    total_sentences = len(sentences)

    if not sentences:
        raise HTTPException(400, "No meaningful sentences found in document")

    # Simple language detection — check if text looks like Lunyoro
    # (presence of common Runyoro markers)
    sample = " ".join(sentences[:20]).lower()
    lunyoro_markers = ["oku", "omu", "eki", "eri", "ebi", "aba", "emi", "enk", "omw"]
    marker_hits = sum(1 for m in lunyoro_markers if m in sample)
    is_lunyoro = marker_hits >= 3

    # If Lunyoro, translate to English first
    english_sentences = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        if is_lunyoro:
            for sent in sentences:
                result = await _translate_sentence(client, sent, "lun->en")
                english_sentences.append(result["translation"])
        else:
            english_sentences = sentences

    # Extractive summarization — score by word frequency + position
    all_words = " ".join(english_sentences).lower().split()
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "were", "be", "been", "it", "this",
        "that", "as", "by", "from", "have", "has", "had", "not", "he", "she",
        "they", "we", "i", "you", "his", "her", "their", "its", "my", "our",
    }
    word_freq = Counter(w for w in all_words if w not in stopwords and len(w) > 3)

    def score_sentence(sent: str, idx: int, total: int) -> float:
        words = sent.lower().split()
        freq_score = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
        position_score = 1.5 if idx < total * 0.15 else (1.2 if idx > total * 0.85 else 1.0)
        return freq_score * position_score

    scored = [(score_sentence(s, i, len(english_sentences)), s)
              for i, s in enumerate(english_sentences)]
    scored.sort(key=lambda x: -x[0])

    top_n = max(3, min(10, len(english_sentences) // 5))
    top_sentences = [s for _, s in scored[:top_n]]

    # Re-order by original position
    order = {s: i for i, s in enumerate(english_sentences)}
    top_sentences.sort(key=lambda s: order.get(s, 0))
    summary = " ".join(top_sentences)

    # Translate summary to Lunyoro — get both model outputs
    summary_nllb_parts = []
    summary_marian_parts = []
    summary_best_parts = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        summary_sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary) if len(s.strip()) > 3]
        for sent in summary_sents:
            result = await _translate_sentence(client, sent, "en->lun")
            summary_best_parts.append(result["translation"])
            summary_nllb_parts.append(result.get("translation_nllb") or result["translation"])
            summary_marian_parts.append(result.get("translation_marian") or result["translation"])

    summary_lunyoro = " ".join(summary_best_parts)
    summary_lunyoro_nllb = " ".join(summary_nllb_parts)
    summary_lunyoro_marian = " ".join(summary_marian_parts)

    return {
        "filename": file.filename,
        "total_pages": full_text.count("\f") + 1 if ext == ".pdf" else 1,
        "total_sentences": total_sentences,
        "language_detected": "lunyoro" if is_lunyoro else "english",
        "summary": summary,
        "summary_lunyoro": summary_lunyoro,
        "summary_lunyoro_marian": summary_lunyoro_marian,
        "summary_lunyoro_nllb": summary_lunyoro_nllb,
        "sentences_used": top_n,
    }


# ══════════════════════════════════════════════════════════════════════════════
# LANGUAGE RULES
# ══════════════════════════════════════════════════════════════════════════════

# Import grammar data from bundled module
from language_rules_data import (
    RL_RULE, EMPAAKO, INTERJECTIONS, IDIOMS, NUMBERS, PROVERBS,
    NOUN_CLASSES, CONCORDIAL_AGREEMENT, TENSES, VERB_SUFFIXES,
    DERIVATIVE_SUFFIXES, CONJUNCTIONS, PREPOSITIONS, NEGATION_WORDS,
    ADJECTIVE_STEMS, ADVERBS_OF_MANNER, PERSONAL_PRONOUNS,
    NUMERAL_CONCORDS, GRAMMAR_SUMMARY,
)


@app.get("/language-rules")
def get_language_rules():
    return {
        "rl_rule": RL_RULE,
        "grammar_summary": GRAMMAR_SUMMARY,
        "empaako": EMPAAKO,
        "interjections": INTERJECTIONS,
        "idioms": IDIOMS,
        "numbers": {str(k): v for k, v in NUMBERS.items()},
        "proverbs": PROVERBS,
        "noun_classes": NOUN_CLASSES,
        "concordial_agreement": CONCORDIAL_AGREEMENT,
        "tenses": TENSES,
        "verb_suffixes": VERB_SUFFIXES,
        "derivative_suffixes": DERIVATIVE_SUFFIXES,
        "conjunctions": CONJUNCTIONS,
        "prepositions": PREPOSITIONS,
        "negation_words": NEGATION_WORDS,
        "adjective_stems": ADJECTIVE_STEMS,
        "adverbs_of_manner": ADVERBS_OF_MANNER,
        "personal_pronouns": PERSONAL_PRONOUNS,
        "numeral_concords": {str(k): v for k, v in NUMERAL_CONCORDS.items()},
    }


@app.get("/language-rules/interjections")
def get_interjections():
    return {"interjections": INTERJECTIONS}


@app.get("/language-rules/idioms")
def get_idioms():
    return {"idioms": IDIOMS}


@app.get("/language-rules/proverbs")
def get_proverbs():
    import random
    return {"proverbs": PROVERBS, "random": random.choice(PROVERBS) if PROVERBS else ""}


class ApplyRuleRequest(BaseModel):
    rule: str
    text: str = ""
    verb_stem: str = ""
    person: str = ""
    tense: str = ""
    negative: bool = False
    noun_class: int = 1
    number: int = 1
    n: int = 1


@app.post("/language-rules/apply")
def apply_rule(req: ApplyRuleRequest):
    """Apply a specific grammar rule to text."""
    from language_rules_data import apply_rl_rule

    if req.rule == "rl_rule":
        result = apply_rl_rule(req.text)
        return {"rule": "rl_rule", "input": req.text, "output": result}

    return {"rule": req.rule, "input": req.text, "output": req.text, "note": "Rule not available on Pi"}


# ══════════════════════════════════════════════════════════════════════════════
# CHAT (Retrieval-based — no LLM, works offline)
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    history: list = []
    sector: Optional[str] = None
    conversation_mode: bool = False


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Offline chat assistant — uses retrieval from grammar rules and corpus
    instead of an LLM. Provides grammar explanations, vocabulary lookups,
    and translation help without needing internet.
    """
    from language_rules_data import (
        RL_RULE, EMPAAKO, INTERJECTIONS, IDIOMS, NUMBERS, PROVERBS,
        NOUN_CLASSES, TENSES, CONJUNCTIONS, PREPOSITIONS, PERSONAL_PRONOUNS,
        GRAMMAR_SUMMARY, apply_rl_rule,
    )

    msg = req.message.strip().lower()

    # ── Pattern matching for common question types ────────────────────────────

    # Translation request (check FIRST — before greetings)
    if "translate" in msg or "how do you say" in msg or "what is" in msg:
        # Extract text to translate and proxy to C++ backend
        text_to_translate = msg.replace("translate", "").replace("how do you say", "").replace("what is", "").strip().strip('"\'')
        if text_to_translate:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{CPP_BACKEND}/translate", json={"text": text_to_translate})
                    if resp.status_code == 200:
                        data = resp.json()
                        nllb = data.get("translation_nllb") or ""
                        marian = data.get("translation_marian") or ""
                        primary = data.get("translation", "")
                        method = data.get("method", "")

                        reply_parts = [f'"{text_to_translate}" in Runyoro-Rutooro:\n']
                        if nllb:
                            reply_parts.append(f"  NLLB: {nllb}")
                        if marian:
                            reply_parts.append(f"  Marian: {marian}")
                        if not nllb and not marian:
                            reply_parts.append(f"  Translation: {primary}")
                        reply_parts.append(f"\n(Method: {method})")

                        return {
                            "reply": "\n".join(reply_parts),
                            "reply_nllb": nllb or None,
                            "reply_marian": marian or None,
                        }
            except Exception:
                pass
        return _chat_response(
            "I can translate for you! Try: 'translate good morning' or 'how do you say thank you'"
        )

    # Greetings
    if any(g in msg for g in ["hello", "hi ", "hey ", "how are you"]) or msg in ("hi", "hey"):
        return _chat_response(
            "Agandi! (How are you?) Welcome to the Runyoro-Rutooro language assistant. "
            "I can help you with grammar rules, vocabulary, translations, proverbs, and more. "
            "Try asking about noun classes, the R/L rule, tenses, or empaako names."
        )

    # Default — general help
    return _chat_response(
        f"{GRAMMAR_SUMMARY}\n\n"
        "I'm the offline language assistant. I can help with:\n"
        "• Grammar rules (noun classes, tenses, R/L rule)\n"
        "• Empaako (honorific names)\n"
        "• Proverbs (enfumo) and idioms\n"
        "• Numbers and counting\n"
        "• Translations (say 'translate hello')\n"
        "• Interjections and conjunctions\n\n"
        "What would you like to learn about?"
    )


def _chat_response(reply: str) -> dict:
    """Format a chat response matching the expected frontend schema."""
    return {
        "reply": reply,
        "reply_marian": None,
        "reply_nllb": None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
def startup():
    print(f"[sidecar] Starting Pi sidecar service...")
    print(f"[sidecar] C++ backend: {CPP_BACKEND}")
    _load_classifier()
    print(f"[sidecar] Ready on port 8001")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pi-sidecar",
        "classifier_ready": _classifier_ready,
    }
