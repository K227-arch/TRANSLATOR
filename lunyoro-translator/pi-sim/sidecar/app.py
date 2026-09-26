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
                    "method":              data.get("method", "unknown"),
                }
    except Exception:
        pass
    return {"translation": label, "translation_nllb": None, "method": "passthrough"}


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
                "method":             data.get("method", "unknown"),
            }
    except Exception:
        pass
    return {"translation": text, "translation_nllb": None, "method": "passthrough"}


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

    summary_nllb_parts, summary_best_parts = [], [], []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for sent in [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary) if len(s.strip()) > 3]:
            r = await _translate_sentence(client, sent, "en->lun")
            summary_best_parts.append(r["translation"])
            summary_nllb_parts.append(r.get("translation_nllb") or r["translation"])

    return {
        "filename":               file.filename,
        "total_pages":            full_text.count("\f") + 1 if ext == ".pdf" else 1,
        "total_sentences":        total_sentences,
        "language_detected":      "lunyoro" if is_lunyoro else "english",
        "summary":                summary,
        "summary_lunyoro":        " ".join(summary_best_parts),
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
    return {"reply": reply, "reply_nllb": None}


def _sentence_case(text: str) -> str:
    """Capitalize first letter and add trailing punctuation if missing.
    Mirrors the normalization in pi-sim-backend app.py so the NLLB
    INT8 model (run_Latn token) receives correctly-formed input."""
    text = text.strip()
    if not text:
        return text
    if not text[0].isupper():
        text = text[0].upper() + text[1:]
    if text[-1] not in ".!?,;:":
        question_words = ("how", "what", "where", "when", "who", "why", "which",
                          "is ", "are ", "do ", "does ", "can ", "will ", "have ")
        if any(text.lower().startswith(w) for w in question_words):
            text = text + "?"
        elif not text[-1].isdigit():
            text = text + "."
    return text


def _is_english(text: str) -> bool:
    """Heuristic: text is English if >15 % of its words are common English
    function words.  Runyoro has very few of these."""
    _EN_FUNCTION_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "i", "you", "he", "she",
        "we", "they", "it", "this", "that", "these", "those", "and", "or",
        "but", "so", "because", "if", "when", "how", "what", "where", "who",
        "which", "why", "in", "on", "at", "to", "for", "of", "with", "by",
        "from", "about", "not", "no", "yes", "my", "your", "his", "her",
        "our", "their", "its", "me", "him", "us", "them", "there", "here",
        "get", "go", "come", "make", "know", "think", "say", "tell", "ask",
        "good", "bad", "big", "small", "new", "old", "first", "last", "long",
        "great", "little", "own", "right", "high", "place", "give", "most",
        "very", "just", "also", "well", "back", "after", "use", "two", "more",
        "write", "mean", "keep", "let", "seem", "help", "talk", "turn", "start",
    }
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return False
    hits = sum(1 for w in words if w in _EN_FUNCTION_WORDS)
    return (hits / len(words)) > 0.15


async def _backend_translate(text: str, direction: str = "en->lun") -> str:
    """Call the C++ backend and return the best translation string."""
    endpoint = "/translate" if direction == "en->lun" else "/translate-reverse"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{CPP_BACKEND}{endpoint}", json={"text": text})
            if resp.status_code == 200:
                data = resp.json()
                return (
                    (data.get("translation_nllb") or "").strip()
                    or (data.get("translation") or "").strip()
                    or text
                )
    except Exception:
        pass
    return text


def _build_english_answer(question: str) -> str:
    """Build a short English answer for common question patterns.
    Returns an empty string when no canned answer exists so the caller
    can fall back to translating the question itself."""
    q = question.lower().strip().rstrip("?.,!")

    # ── What is / what are ────────────────────────────────────────────────────
    what_map = {
        "runyoro": (
            "Runyoro-Rutooro is a Bantu language spoken by the Bunyoro-Kitara "
            "and Tooro kingdoms in western Uganda. It has 15 noun classes, "
            "agglutinative verb structure, and the R/L phonological rule."
        ),
        "runyoro-rutooro": (
            "Runyoro-Rutooro is a Bantu language of western Uganda with 15 noun "
            "classes, vowel harmony, nasal assimilation, and rich verb derivation."
        ),
        "empaako": (
            "Empaako are honorific praise names given to every person in "
            "Bunyoro-Kitara and Tooro. Examples: Atwooki (shining star), "
            "Amooti (princely), Akiiki (one who follows twins)."
        ),
        "noun class": (
            "Runyoro-Rutooro has 15 noun classes. Each class has a singular and "
            "plural prefix that also controls concordial agreement on verbs and "
            "adjectives. Class 1 (omu-/aba-) covers people."
        ),
        "rl rule": (
            "The R/L rule: L is only used next to the vowels e or i. "
            "In all other positions R is used. For example: 'okulima' (to dig) "
            "keeps L because it follows u, but 'kurya' uses R."
        ),
        "r/l rule": (
            "The R/L rule: L is only used next to the vowels e or i. "
            "Everywhere else R is used instead of L."
        ),
        "tense": (
            "Runyoro-Rutooro marks tense by inserting a prefix between the subject "
            "concord and the verb stem. Common tense markers: -a- (present/recent "
            "past), -ka- (narrative/consecutive), -zi- (remote past), "
            "-ki- (immediate future), -na- (near future)."
        ),
    }
    for keyword, answer in what_map.items():
        if keyword in q:
            return answer

    # ── How do you say ────────────────────────────────────────────────────────
    # These are handled upstream in the translate branch; nothing to do here.

    # ── Greeting questions ────────────────────────────────────────────────────
    if re.search(r"how are you|how do you do|how is (life|everything)", q):
        return (
            "I am fine, thank you! In Runyoro: 'Ndyoho, webale muno.' "
            "You can greet someone by saying 'Agandi!' and they reply 'Gandi!'"
        )

    if re.search(r"what is your name|who are you", q):
        return (
            "I am your offline Runyoro-Rutooro language assistant. "
            "I can help with translations, grammar rules, proverbs, "
            "empaako names, and vocabulary."
        )

    # ── Where / when ──────────────────────────────────────────────────────────
    if re.search(r"where (is|are) (runyoro|rutooro|bunyoro|tooro)", q):
        return (
            "Runyoro-Rutooro is spoken in western Uganda, mainly in the "
            "Bunyoro-Kitara and Tooro kingdoms — districts like Hoima, "
            "Masindi, Kibale, Kabarole, and Kasese."
        )

    # ── How many ──────────────────────────────────────────────────────────────
    if re.search(r"how many (noun classes|classes)", q):
        return "Runyoro-Rutooro has 15 noun classes."

    if re.search(r"how many (people|speakers)", q):
        return (
            "Runyoro-Rutooro is spoken by roughly 2–3 million people in "
            "western Uganda."
        )

    # No canned answer — return empty so caller handles it
    return ""


async def _general_chat(message: str) -> dict:
    """Handle any message that did not match a keyword topic.

    Strategy:
      1. If the message is in English, build a short English answer (canned or
         by rephrasing the question as a statement), then translate that answer
         to Runyoro.  Return both languages.
      2. If the message appears to be in Runyoro, translate it to English first
         so we can understand it, derive an English answer, then translate the
         answer back to Runyoro.
      3. If translation fails at any step, still return the best partial result
         rather than an error.
    """
    msg_clean = message.strip()

    # ── Step 1: determine input language ─────────────────────────────────────
    input_is_english = _is_english(msg_clean)

    # ── Step 2: get English version of the question ───────────────────────────
    if input_is_english:
        english_question = msg_clean
    else:
        # Translate Runyoro → English so we can reason about it
        english_question = await _backend_translate(msg_clean, direction="lun->en")

    # ── Step 3: build an English answer ───────────────────────────────────────
    english_answer = _build_english_answer(english_question)

    if not english_answer:
        # No canned answer — use the question itself as the content to translate,
        # wrapping it so the model gets a declarative sentence to work with.
        # Example: "How do you greet someone?" →
        #   translate "You greet someone by saying Agandi."
        # For generic statements, just translate the original message.
        stripped_q = english_question.rstrip("?.,!").strip()
        if re.search(r"^(what|who|where|when|how|why|which|is |are |do |does |can )", 
                     stripped_q, re.I):
            # Can't answer — at minimum translate the question itself to Runyoro
            # so the user sees the Runyoro form of what they typed.
            runyoro_of_question = await _backend_translate(
                _sentence_case(english_question), direction="en->lun"
            )
            return {
                "reply": (
                    f"(English) {english_question}\n"
                    f"(Runyoro) {runyoro_of_question}\n\n"
                    "I don't have a specific answer for that. Try asking about:\n"
                    "  'translate [phrase]', 'noun classes', 'tenses', 'proverb', 'empaako'"
                ),
                "reply_nllb": runyoro_of_question,
            }
        else:
            # It's a statement — translate it to Runyoro and echo back
            runyoro_stmt = await _backend_translate(
                _sentence_case(english_question), direction="en->lun"
            )
            return {
                "reply": (
                    f"(English) {english_question}\n"
                    f"(Runyoro) {runyoro_stmt}"
                ),
                "reply_nllb": runyoro_stmt,
            }

    # ── Step 4: translate the English answer → Runyoro ────────────────────────
    runyoro_answer = await _backend_translate(
        _sentence_case(english_answer), direction="en->lun"
    )

    # ── Step 5: build the bilingual reply ─────────────────────────────────────
    # Show original message language label, then the Runyoro answer prominently.
    if input_is_english:
        reply = (
            f"(Runyoro) {runyoro_answer}\n\n"
            f"(English) {english_answer}"
        )
    else:
        reply = (
            f"(Runyoro) {runyoro_answer}\n\n"
            f"(English) {english_answer}\n\n"
            f"Your question in English: {english_question}"
        )

    return {
        "reply": reply,
        "reply_nllb": runyoro_answer,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CHAT — LLM (qwen2.5:1.5b via Ollama) + NLLB translation to Runyoro
# ══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

SYSTEM_PROMPT = (
    "You are a helpful assistant for the Runyoro-Rutooro language spoken in western Uganda. "
    "Your replies will be translated into Runyoro-Rutooro by a separate translation model, "
    "so always answer in clear, simple English. "
    "Be concise — 2 to 4 sentences maximum. "
    "For vocabulary or phrase requests, provide a short list of simple English words or phrases. "
    "Do not include any Runyoro words yourself — the translation model handles that. "
    "Do not add disclaimers, markdown headers, or asterisks."
)

# Chip topics the frontend sends as 'How do I say "<topic>" phrases in Runyoro-Rutooro?'
_CHIP_ENGLISH = {
    "food": (
        "Here are common food and eating words: food, water, meat, fish, "
        "rice, porridge, banana, salt, sugar, cooking oil. "
        "Useful phrases: I want to eat. I am hungry. I am full. The food is delicious."
    ),
    "greetings": (
        "Common greeting phrases: How are you? Good morning. Good evening. "
        "I am fine. Thank you very much. Goodbye. See you later. Welcome. Excuse me. Sorry."
    ),
    "directions": (
        "Direction phrases: Where is the market? Go straight. Turn right. "
        "Turn left. It is near. It is far. Let us go. Show me the way. I am lost."
    ),
    "emergency": (
        "Emergency phrases: Help me! I am sick. I need a doctor. "
        "Call the police. There is fire. I am in danger. Where is the hospital?"
    ),
    "numbers": (
        "Numbers one to ten: one, two, three, four, five, "
        "six, seven, eight, nine, ten. Also: twenty, one hundred, one thousand."
    ),
}


async def _ollama_chat(message: str, history: list) -> str:
    """Send message to Ollama qwen2.5:1.5b and return English reply.
    Returns empty string on error or if the model replies in a non-English language."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-4:]:
        messages.append({
            "role": "user" if h.get("role") == "user" else "assistant",
            "content": h.get("content", ""),
        })
    messages.append({"role": "user", "content": message})
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
            if resp.status_code == 200:
                reply = resp.json()["message"]["content"].strip()
                # Guard: reject replies that are not in English.
                # qwen2.5:1.5b sometimes answers in Swahili or Runyoro for
                # greetings/short inputs despite the system prompt.
                if reply and not _is_english_reply(reply):
                    print(f"[pi-sim-sidecar] Ollama replied in non-English, discarding: {reply[:80]}")
                    return ""
                return reply
    except Exception as e:
        print(f"[pi-sim-sidecar] Ollama error: {e}")
    return ""


def _is_english_reply(text: str) -> bool:
    """Return True if text appears to be English (not Swahili/Runyoro/other).
    Uses a small set of high-frequency English function words as a signal."""
    _EN_WORDS = {
        "i", "the", "a", "an", "is", "are", "was", "were", "be", "have", "has",
        "do", "does", "did", "will", "would", "can", "could", "should", "may",
        "you", "he", "she", "we", "they", "it", "this", "that", "and", "or",
        "but", "in", "on", "at", "to", "for", "of", "with", "not", "my", "your",
        "his", "her", "our", "there", "here", "so", "if", "how", "what", "who",
        "when", "where", "why", "which", "am", "get", "go", "know", "say", "very",
        "just", "also", "well", "good", "fine", "hello", "yes", "no", "ok",
    }
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return False
    hits = sum(1 for w in words if w in _EN_WORDS)
    return (hits / len(words)) > 0.12


async def _translate_to_runyoro(text: str) -> str:
    """Translate English text to Runyoro sentence-by-sentence via NLLB backend."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return text
    parts = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for sent in sentences:
                resp = await client.post(
                    f"{CPP_BACKEND}/translate",
                    json={"text": _sentence_case(sent)},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    translated = (
                        (data.get("translation_nllb") or "").strip()
                        or (data.get("translation") or "").strip()
                        or sent
                    )
                    parts.append(translated)
                else:
                    parts.append(sent)
    except Exception as e:
        print(f"[pi-sim-sidecar] Translation error: {e}")
        return text
    return " ".join(parts)


@app.post("/chat")
async def chat(req: ChatRequest):
    msg = req.message.strip()
    msg_lower = msg.lower()

    # ── Greeting shortcuts — hardcoded correct Runyoro, no LLM needed ─────────
    # qwen2.5:1.5b reliably replies in Swahili for greetings despite the prompt.
    _GREETINGS = [
        # (regex pattern, Runyoro reply, English explanation)
        (r"\b(how are you|how do you do|how is (life|everything))\b",
         "Ndyoho, webale muno.",
         "I am fine, thank you."),
        (r"\b(good morning)\b",
         "Oraire ota! Ndyoho.",
         "Good morning! I am fine."),
        (r"\b(good evening|good night)\b",
         "Oirirwe ota! Ndyoho.",
         "Good evening! I am fine."),
        (r"\b(good afternoon)\b",
         "Osiibire ota! Ndyoho.",
         "Good afternoon! I am fine."),
        (r"\b(hello|hi|hey)\b",
         "Agandi! Ndyoho, webale.",
         "Hello! I am fine, thank you."),
        (r"\b(thank you|thanks)\b",
         "Webale muno!",
         "Thank you very much!"),
        (r"\b(goodbye|bye|see you)\b",
         "Ogende bulungi! Raba!",
         "Go well! Goodbye!"),
        (r"\b(welcome)\b",
         "Karibu! Tukagiire.",
         "Welcome!"),
        (r"\b(sorry|excuse me)\b",
         "Mbabarira!",
         "Sorry / Excuse me!"),
        (r"\b(agandi|gandi)\b",
         "Gandi! Ndyoho, webale muno.",
         "Hello! I am fine, thank you."),
        (r"\b(oraire ota|oirirwe)\b",
         "Oraire bulungi! Ndyoho.",
         "Good morning! I am fine."),
    ]
    for pattern, runyoro_reply, english_explanation in _GREETINGS:
        if re.search(pattern, msg_lower):
            reply_text = f"{runyoro_reply}\n\n(English: {english_explanation})"
            return {
                "reply": reply_text,
                "reply_nllb": runyoro_reply,
            }

    # ── Quick-chip topic phrases (from ChatPage.tsx chip buttons) ─────────────
    # Chips send: 'How do I say "<topic>" phrases in Runyoro-Rutooro?'
    _CHIP_TOPICS = {
        "food": (
            "Here are common food and eating words: food, water, meat, fish, "
            "rice, porridge, banana, salt, sugar, cooking oil. "
            "Useful phrases: I want to eat. I am hungry. I am full. "
            "The food is delicious."
        ),
        "greetings": (
            "Common greeting phrases: How are you? Good morning. Good evening. "
            "I am fine. Thank you very much. Goodbye. See you later. "
            "Welcome. Excuse me. Sorry."
        ),
        "directions": (
            "Direction phrases: Where is the market? Go straight. Turn right. "
            "Turn left. It is near. It is far. Let us go. "
            "Show me the way. I am lost."
        ),
        "emergency": (
            "Emergency phrases: Help me! I am sick. I need a doctor. "
            "Call the police. There is fire. I am in danger. "
            "Where is the hospital? I need water."
        ),
        "numbers": (
            "Numbers one to ten: one, two, three, four, five, "
            "six, seven, eight, nine, ten. "
            "Also: twenty, one hundred, one thousand."
        ),
    }
    for topic, english_content in _CHIP_TOPICS.items():
        if (f'"{topic}"' in msg_lower or f"'{topic}'" in msg_lower or
                (topic in msg_lower and any(
                    w in msg_lower for w in ("phrases", "words", "vocabulary", "say")))):
            runyoro = await _translate_to_runyoro(english_content)
            return {
                "reply": f"{runyoro}\n\n(English: {english_content})",
                "reply_nllb": runyoro,
            }

    # ── All other messages — LLM generates English reply, NLLB translates ─────
    english_reply = await _ollama_chat(msg, req.history)

    if not english_reply:
        # Ollama unavailable — fall back to a helpful static message
        english_reply = (
            "I can help you learn Runyoro-Rutooro. "
            "Try asking me to translate a word or phrase, "
            "or ask about greetings, numbers, or grammar rules."
        )

    runyoro_reply = await _translate_to_runyoro(english_reply)

    return {
        "reply": f"{runyoro_reply}\n\n(English: {english_reply})",
        "reply_nllb": runyoro_reply,
    }


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
