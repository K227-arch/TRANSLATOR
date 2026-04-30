from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import os
import io

# Load .env file if present (development convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ensure all HuggingFace/transformers calls stay fully offline
os.environ.setdefault("TRANSFORMERS_OFFLINE", os.getenv("TRANSFORMERS_OFFLINE", "1"))
os.environ.setdefault("HF_DATASETS_OFFLINE", os.getenv("HF_DATASETS_OFFLINE", "1"))
os.environ.setdefault("HF_HUB_OFFLINE", os.getenv("HF_HUB_OFFLINE", "1"))

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
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3002,http://localhost:3000")
_cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def preload_model():
    """Load retrieval index and all neural MT models at startup."""
    get_index_and_model()
    from translate import _load_mt, _load_nllb
    _load_mt("en2lun")
    _load_mt("lun2en")
    _load_nllb("en2lun")
    _load_nllb("lun2en")

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
    save_history({
        "input": req.text,
        "direction": "en→lun",
        "translation": result.get("translation"),
        "method": result.get("method"),
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
    save_history({
        "input": req.text,
        "direction": "lun→en",
        "translation": result.get("translation"),
        "method": result.get("method"),
        "confidence": result.get("confidence"),
        "timestamp": datetime.utcnow().isoformat(),
    })
    return result


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
            out.append(result)
        return " ".join(out)

    summary_lunyoro_marian = _translate_summary(summary, use_nllb=False)
    summary_lunyoro_nllb   = _translate_summary(summary, use_nllb=True)
    summary_lunyoro = summary_lunyoro_nllb or summary_lunyoro_marian

    save_history({
        "input": f"[DOC Summary] {file.filename}",
        "direction": "en→lun",
        "translation": summary_lunyoro[:200] + "..." if len(summary_lunyoro) > 200 else summary_lunyoro,
        "method": "extractive_summary",
        "confidence": None,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "filename": file.filename,
        "total_pages": full_text.count("\f") + 1 if file.filename.lower().endswith(".pdf") else 1,
        "total_sentences": total_sentences,
        "language_detected": "lunyoro" if is_lunyoro else "english",
        "summary": summary,
        "summary_lunyoro": summary_lunyoro,
        "summary_lunyoro_marian": summary_lunyoro_marian,
        "summary_lunyoro_nllb": summary_lunyoro_nllb,
        "sentences_used": top_n,
    }


class ChatRequest(BaseModel):
    message: str
    history: list = []
    sector: str | None = None
    conversation_mode: bool = False


@app.post("/chat")
def chat(req: ChatRequest):
    """AI Language Assistant — LLM-powered generative replies about Runyoro-Rutooro."""
    import re, requests as _requests
    from translate import _mt_translate, _load_retrieval, _normalise, _index, _sem_model
    from language_rules import get_full_grammar_context, EMPAAKO, PROVERBS, NUMBERS
    import numpy as np
    from sentence_transformers import util as st_util

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
    grammar_ctx  = get_full_grammar_context()

    system_prompt = (
        "You are an expert AI assistant for the Runyoro-Rutooro language of the Bunyoro-Kitara and Tooro kingdoms in Uganda. /no_think\n"
        "Answer questions about the language, grammar, culture, vocabulary, and translation.\n"
        "Give detailed, helpful answers with examples where relevant.\n"
        "Use numbered lists or bullet points when listing items.\n"
        "Write in clear English sentences. Do not use overly complex grammar.\n"
    )
    system_prompt += f"\n{grammar_ctx}\n"
    if corpus_ctx:
        system_prompt += f"\nRelevant examples (English → Runyoro-Rutooro):\n{corpus_ctx}\n"
    if sector_label:
        system_prompt += f"\nSector focus: {sector_label}\n"
    if dict_ctx:
        system_prompt += f"Vocabulary:\n{dict_ctx}\n"
    system_prompt += "\nAlways reply in English. Be clear and concise."

    # ── Build message history for Ollama ─────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for turn in (req.history or [])[-10:]:
        role    = turn.get("role", "")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": msg})

    # ── Call Ollama ───────────────────────────────────────────────────────────
    _ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    _ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    try:
        resp = _requests.post(
            f"{_ollama_url}/api/chat",
            json={
                "model": _ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": 1024,
                    "num_predict": 300,
                    "temperature": 0.7,
                }
            },
            timeout=300,
        )
        resp.raise_for_status()
        reply_en = resp.json()["message"]["content"].strip()
    except Exception as e:
        import logging
        logging.warning(f"Ollama call failed: {e}")
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
        return {"reply": "Sorry, the chat assistant is unavailable right now. Please try again.",
                "reply_marian": None, "reply_nllb": None}

    return {
        "reply":         marian_out or nllb_out,  # MarianMT is primary
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
    }


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
