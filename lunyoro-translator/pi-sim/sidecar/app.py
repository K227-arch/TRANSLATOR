"""
Pi-Sim Sidecar Service
======================
Identical to pi-sidecar/app.py — same endpoints, same logic.
The only change: CPP_BACKEND_URL defaults to http://pi-sim-backend:8080
instead of http://127.0.0.1:8080, so it routes to the Docker service
rather than a local C++ binary.

Endpoints handled here (mirroring Pi nginx routing):
  POST /classify-image
  GET  /classify-image/status
  POST /translate-batch
  POST /translate-batch-file
  POST /summarize-pdf
  GET  /language-rules
  GET  /language-rules/interjections
  GET  /language-rules/idioms
  GET  /language-rules/proverbs
  POST /language-rules/apply
  POST /chat
  GET  /health
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
# Points to pi-sim-backend service (not localhost:8080 as on the real Pi)
CPP_BACKEND = os.getenv("CPP_BACKEND_URL", "http://pi-sim-backend:8080")
MODEL_DIR = Path(__file__).parent / "models"
MOBILENET_DIR = MODEL_DIR / "mobilenet_v2"

app = FastAPI(title="Lunyoro Translator Pi-Sim Sidecar", version="1.0.0")

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
                "Run: python download_model.py inside the sidecar container."
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
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{CPP_BACKEND}/translate", json={"text": label})
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "translation":         data.get("translation", label),
                    "translation_nllb":    data.get("translation_nllb"),
                    "translation_marian":  data.get("translation_marian"),
                    "method":              data.get("method", "unknown"),
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
    if not contents:
        raise HTTPException(400, "File is empty.")
    mime = _detect_mime(contents)
    if mime not in SUPPORTED_IMAGE_MIMES:
        raise HTTPException(400, "Unsupported format. Accepted: JPEG, PNG, WebP.")
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"File too large. Max 10 MB, got {len(contents)/1e6:.1f} MB.")

    try:
        predictions = _classify_image(contents, top_k=top_k)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Classification failed: {e}")

    tasks = [_translate_label(p["label"]) for p in predictions]
    translations = await asyncio.gather(*tasks)

    results = []
    for pred, tr in zip(predictions, translations):
        results.append({
            "label_en":          pred["label"],
            "label_lun":         tr["translation"],
            "label_lun_nllb":    tr.get("translation_nllb"),
            "label_lun_marian":  tr.get("translation_marian"),
            "confidence":        pred["confidence"],
            "method":            tr["method"],
        })
    return {"predictions": results, "top_k": len(results), "model": "google/mobilenet_v2_1.0_224"}


@app.get("/classify-image/status")
def classify_image_status():
    return {"ready": _classifier_ready, "error": _classifier_error}


# ══════════════════════════════════════════════════════════════════════════════
# BATCH TRANSLATION (proxies to pi-sim-backend)
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
    async with httpx.AsyncClient(timeout=30.0) as client:
        for sentence in req.sentences:
            text = sentence.strip()
            if not text:
                results.append({"source": sentence, "translation": "", "method": "skipped"})
                continue
            if len(text) > 5000:
                results.append({"source": sentence, "translation": "", "method": "error", "error": "Too long"})
                continue
            endpoint = "/translate-reverse" if req.direction == "lun->en" else "/translate"
            try:
                resp = await client.post(f"{CPP_BACKEND}{endpoint}", json={"text": text})
                if resp.status_code == 200:
                    data = resp.json()
                    results.append({
                        "source":      text,
                        "translation": data.get("translation", ""),
                        "method":      data.get("method", "unknown"),
                        "confidence":  data.get("confidence"),
                    })
                else:
                    results.append({"source": text, "translation": "", "method": "error",
                                    "error": f"Backend returned {resp.status_code}"})
            except Exception as e:
                results.append({"source": text, "translation": "", "method": "error", "error": str(e)})

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

    sentences = []
    if ext == ".csv":
        for row in _csv.reader(io.StringIO(text_content)):
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

    batch_req = BatchTranslateRequest(sentences=sentences, direction=direction)
    result = await translate_batch(batch_req)
    return {**result, "filename": file.filename}


# ══════════════════════════════════════════════════════════════════════════════
# PDF / DOCUMENT SUMMARIZATION
# ══════════════════════════════════════════════════════════════════════════════

SUPPORTED_DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def _extract_text(filename: str, content: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
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
    endpoint = "/translate-reverse" if direction == "lun->en" else "/translate"
    try:
        resp = await client.post(f"{CPP_BACKEND}{endpoint}", json={"text": text})
        if resp.status_code == 200:
            data = resp.json()
            return {
                "translation":        data.get("translation", text),
                "translation_nllb":   data.get("translation_nllb"),
                "translation_marian": data.get("translation_marian"),
                "method":             data.get("method", "unknown"),
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
        raise HTTPException(400, f"Supported: {', '.join(SUPPORTED_DOC_EXTENSIONS)}")

    contents = await file.read()
    try:
        full_text = _extract_text(file.filename, contents)
    except Exception as e:
        raise HTTPException(400, f"Could not extract text: {e}")
    if not full_text or len(full_text.strip()) < 20:
        raise HTTPException(400, "No text found in document")

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if len(s.strip()) > 10]
    total_sentences = len(sentences)
    if not sentences:
        raise HTTPException(400, "No meaningful sentences found")

    sample = " ".join(sentences[:20]).lower()
    lunyoro_markers = ["oku", "omu", "eki", "eri", "ebi", "aba", "emi", "enk", "omw"]
    is_lunyoro = sum(1 for m in lunyoro_markers if m in sample) >= 3

    english_sentences: list[str] = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        if is_lunyoro:
            for sent in sentences:
                r = await _translate_sentence(client, sent, "lun->en")
                english_sentences.append(r["translation"])
        else:
            english_sentences = sentences

    all_words = " ".join(english_sentences).lower().split()
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "were", "be", "been", "it", "this",
        "that", "as", "by", "from", "have", "has", "had", "not", "he", "she",
        "they", "we", "i", "you", "his", "her", "their", "its", "my", "our",
    }
    word_freq = Counter(w for w in all_words if w not in stopwords and len(w) > 3)

    def score(sent: str, idx: int, total: int) -> float:
        words = sent.lower().split()
        fs = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
        ps = 1.5 if idx < total * 0.15 else (1.2 if idx > total * 0.85 else 1.0)
        return fs * ps

    scored = sorted(
        [(score(s, i, len(english_sentences)), s) for i, s in enumerate(english_sentences)],
        key=lambda x: -x[0],
    )
    top_n = max(3, min(10, len(english_sentences) // 5))
    top_sentences = [s for _, s in scored[:top_n]]
    order = {s: i for i, s in enumerate(english_sentences)}
    top_sentences.sort(key=lambda s: order.get(s, 0))
    summary = " ".join(top_sentences)

    summary_nllb_parts, summary_marian_parts, summary_best_parts = [], [], []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for sent in [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary) if len(s.strip()) > 3]:
            r = await _translate_sentence(client, sent, "en->lun")
            summary_best_parts.append(r["translation"])
            summary_nllb_parts.append(r.get("translation_nllb") or r["translation"])
            summary_marian_parts.append(r.get("translation_marian") or r["translation"])

    return {
        "filename":               file.filename,
        "total_pages":            full_text.count("\f") + 1 if ext == ".pdf" else 1,
        "total_sentences":        total_sentences,
        "language_detected":      "lunyoro" if is_lunyoro else "english",
        "summary":                summary,
        "summary_lunyoro":        " ".join(summary_best_parts),
        "summary_lunyoro_marian": " ".join(summary_marian_parts),
        "summary_lunyoro_nllb":   " ".join(summary_nllb_parts),
        "sentences_used":         top_n,
    }


# ══════════════════════════════════════════════════════════════════════════════
# LANGUAGE RULES
# ══════════════════════════════════════════════════════════════════════════════

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
        "rl_rule":              RL_RULE,
        "grammar_summary":      GRAMMAR_SUMMARY,
        "empaako":              EMPAAKO,
        "interjections":        INTERJECTIONS,
        "idioms":               IDIOMS,
        "numbers":              {str(k): v for k, v in NUMBERS.items()},
        "proverbs":             PROVERBS,
        "noun_classes":         NOUN_CLASSES,
        "concordial_agreement": CONCORDIAL_AGREEMENT,
        "tenses":               TENSES,
        "verb_suffixes":        VERB_SUFFIXES,
        "derivative_suffixes":  DERIVATIVE_SUFFIXES,
        "conjunctions":         CONJUNCTIONS,
        "prepositions":         PREPOSITIONS,
        "negation_words":       NEGATION_WORDS,
        "adjective_stems":      ADJECTIVE_STEMS,
        "adverbs_of_manner":    ADVERBS_OF_MANNER,
        "personal_pronouns":    PERSONAL_PRONOUNS,
        "numeral_concords":     {str(k): v for k, v in NUMERAL_CONCORDS.items()},
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
    try:
        from language_rules_data import apply_rl_rule
        if req.rule == "rl_rule":
            result = apply_rl_rule(req.text)
            return {"rule": "rl_rule", "input": req.text, "output": result}
    except Exception:
        pass
    return {"rule": req.rule, "input": req.text, "output": req.text, "note": "Rule unavailable"}


# ══════════════════════════════════════════════════════════════════════════════
# CHAT (Offline retrieval-based — no LLM, works without internet)
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    history: list = []
    sector: Optional[str] = None
    conversation_mode: bool = False


def _chat_response(reply: str) -> dict:
    return {"reply": reply, "reply_marian": None, "reply_nllb": None}


@app.post("/chat")
async def chat(req: ChatRequest):
    msg = req.message.strip().lower()

    # Translation request
    if any(k in msg for k in ("translate", "how do you say", "what is")):
        text = msg.replace("translate", "").replace("how do you say", "").replace("what is", "").strip().strip("\"'")
        if text:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{CPP_BACKEND}/translate", json={"text": text})
                    if resp.status_code == 200:
                        data = resp.json()
                        nllb   = data.get("translation_nllb", "")
                        marian = data.get("translation_marian", "")
                        primary = data.get("translation", "")
                        method  = data.get("method", "")
                        parts = [f'"{text}" in Runyoro-Rutooro:']
                        if nllb:
                            parts.append(f"  NLLB-200:  {nllb}")
                        if marian:
                            parts.append(f"  MarianMT:  {marian}")
                        if not nllb and not marian:
                            parts.append(f"  Translation: {primary}")
                        parts.append(f"(Method: {method})")
                        return {"reply": "\n".join(parts), "reply_nllb": nllb or None, "reply_marian": marian or None}
            except Exception:
                pass

    # Greetings
    if any(g in msg for g in ("hello", "hi", "hey", "agandi", "ota")):
        return _chat_response(
            "Agandi! (Hello!) I'm your offline Runyoro-Rutooro language assistant.\n"
            "I can help with grammar, vocabulary, translations, proverbs, and empaako names.\n"
            "Try: 'translate good morning' or ask about noun classes or the R/L rule."
        )

    # Specific grammar topics
    if "rl rule" in msg or "r/l" in msg or "l rule" in msg:
        return _chat_response(f"R/L Rule:\n{RL_RULE}")

    if "empaako" in msg or "honorific" in msg:
        names = ", ".join(f"{e['name']} ({e.get('meaning','') or e.get('description','')})"
                          for e in EMPAAKO[:8]) if EMPAAKO else "See grammar guide"
        return _chat_response(f"Empaako (Tooro/Bunyoro honorific names):\n{names}")

    if "proverb" in msg or "enfumo" in msg:
        import random
        p = random.choice(PROVERBS) if PROVERBS else {"lunyoro": "N/A", "english": "N/A"}
        return _chat_response(
            f"Proverb (Enfumo):\n  Runyoro: {p.get('lunyoro', p)}\n  English: {p.get('english', '')}"
            if isinstance(p, dict) else f"Proverb: {p}"
        )

    if "noun class" in msg or "omuntu" in msg or "aba" in msg:
        nc = NOUN_CLASSES[:3] if NOUN_CLASSES else []
        summary = "\n".join(
            f"  Class {c.get('class','')} ({c.get('singular_prefix','')}/{c.get('plural_prefix','')}): "
            f"{c.get('meaning','')}" for c in nc
        ) if nc else "Noun classes not available."
        return _chat_response(f"Noun Classes (sample):\n{summary}\n\nAsk 'translate [word]' to see a word in context.")

    if "tense" in msg or "past" in msg or "future" in msg or "present" in msg:
        t_summary = "\n".join(
            f"  {t.get('tense','')}: {t.get('description','')}" for t in TENSES[:5]
        ) if TENSES else "Tense data not available."
        return _chat_response(f"Tenses in Runyoro-Rutooro:\n{t_summary}")

    if "number" in msg or "count" in msg or "one" in msg or "two" in msg:
        nums = {str(k): v for k, v in list(NUMBERS.items())[:10]}
        num_str = "\n".join(f"  {k}: {v}" for k, v in nums.items())
        return _chat_response(f"Numbers in Runyoro-Rutooro:\n{num_str}")

    if "greeting" in msg or "good morning" in msg or "good evening" in msg:
        greetings = [i for i in INTERJECTIONS if "greet" in str(i.get("category","")).lower()][:5]
        g_str = "\n".join(
            f"  {g.get('lunyoro','')} — {g.get('english','')}" for g in greetings
        ) if greetings else "Try: Agandi (how are you?), Oraire ota (good morning)"
        return _chat_response(f"Greetings:\n{g_str}")

    # Default
    return _chat_response(
        f"{GRAMMAR_SUMMARY[:500]}\n\n"
        "I'm your offline Runyoro-Rutooro assistant. Ask me about:\n"
        "• Grammar: 'noun classes', 'R/L rule', 'tenses'\n"
        "• Culture: 'empaako', 'proverb'\n"
        "• Numbers: 'numbers'\n"
        "• Greetings: 'greetings'\n"
        "• Translation: 'translate hello'\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP + HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
def startup():
    print(f"[pi-sim-sidecar] Starting — backend: {CPP_BACKEND}")
    _load_classifier()
    print(f"[pi-sim-sidecar] Ready on port 8001")


@app.get("/health")
def health():
    return {
        "status":             "ok",
        "service":            "pi-sim-sidecar",
        "classifier_ready":   _classifier_ready,
        "backend":            CPP_BACKEND,
        "pi_sim":             True,
    }
