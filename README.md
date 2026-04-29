# Lunyoro-Rutooro Translator

An AI-powered translation system for the Runyoro-Rutooro language of the Bunyoro-Kitara and Tooro kingdoms in Uganda.

## Features

- English ↔ Lunyoro/Rutooro translation (MarianMT + NLLB-200)
- Dictionary lookup with example sentences
- AI chat assistant powered by LLaMA 3.2 (via Ollama)
- PDF/DOCX document summarization and translation
- Voice translation
- Spellcheck
- Domain-aware translation (Medical, Education, Agriculture, etc.)
- Model comparison view (MarianMT vs NLLB-200)

## Dataset

- ~53,948 English-Lunyoro sentence pairs
- Sources: crowd-sourced submissions, dictionary entries, sentence corpora
- Augmented via back-translation using the fine-tuned lun2en model
- Cleaned with quality filters: deduplication, length checks, hallucination detection, round-trip consistency

## Models

All models are hosted on HuggingFace under [keithtwesigye](https://huggingface.co/keithtwesigye):

| Model | Repo | Description |
|-------|------|-------------|
| MarianMT en→lun | `keithtwesigye/lunyoro-en2lun` | English to Lunyoro |
| MarianMT lun→en | `keithtwesigye/lunyoro-lun2en` | Lunyoro to English |
| NLLB-200 en→lun | `keithtwesigye/lunyoro-nllb_en2lun` | English to Lunyoro (NLLB) |
| NLLB-200 lun→en | `keithtwesigye/lunyoro-nllb_lun2en` | Lunyoro to English (NLLB) |

## Requirements

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) (for AI chat)

## Quick Setup

### Linux / macOS
```bash
cd lunyoro-translator
bash setup.sh
```

### Windows
```bat
cd lunyoro-translator
setup.bat
```

Or manually:

```bash
# 1. Python backend
pip install -r backend/requirements.txt

# 2. Download models from HuggingFace
cd backend
python download_models.py

# 3. Frontend
cd ../frontend && npm install

# 4. Ollama — download from https://ollama.com/download
ollama pull llama3.2:3b
```

## Running the App

Open 3 terminals:

```bash
# Terminal 1 — Backend API (port 8000)
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend (port 3002)
cd frontend
npm run dev

# Terminal 3 — Ollama (if not running as a service)
ollama serve
```

Then open **http://localhost:3002**

## Training

To rebuild training data and retrain models:

```bash
cd backend

# 1. Merge new submissions and rebuild training splits
python clean_new_submissions.py

# 2. (Optional) Back-translation augmentation
python back_translate.py
python clean_backtranslated.py

# 3. Retrain MarianMT models
python fine_tune.py --direction both --epochs 10 --batch_size 32

# 4. Retrain NLLB models
python fine_tune_nllb.py --direction both --epochs 10 --batch_size 4

# 5. (Optional) Evaluate all 4 models on the test set
python eval_models.py
# Results saved to eval_results_full.json (BLEU, token F1, exact match)
```

## Publishing Models to HuggingFace

To push README files to the 4 HuggingFace model repos, set your HuggingFace token as an environment variable before running the script:

```bash
# Linux / macOS
export HF_TOKEN=your_token_here
python backend/_push_hf_readmes.py

# Windows
set HF_TOKEN=your_token_here
python backend\_push_hf_readmes.py
```

You can generate a token at https://huggingface.co/settings/tokens (needs write access to the target repos).

## Architecture

```
backend/
  main.py                    — FastAPI server
  translate.py               — Translation logic (MarianMT + NLLB + retrieval)
  language_rules.py          — Orthography constants (alphabet, vowels, diphthongs, apostrophe contexts), R/L rule, noun class system (classes 1–15 with prefixes), get_noun_class() for morphological prefix analysis, concordial agreement table (subject/object/adjective concords per class) with get_subject_concord()/get_object_concord() helpers, plural sound changes (class 11→10), get_class6_prefix() for class 5→6 plural prefix selection, verb structure constants (infinitive prefixes, subject prefixes, tense/aspect markers, negative markers, verb suffixes, derivative suffixes), full tense system reference (TENSES dict + CONDITIONAL_PARTICLES), detailed derivative verb formation rules (PREPOSITIONAL_FORMATION for -ira/-era applied verbs, PASSIVE_FORMATION for -ibwa/-ebwa passives, CAUSATIVE_FORMATION for -isa/-esa/-ya causatives, NEUTER_FORMATION for -ika/-eka statives, CONVERSIVE_FORMATION for -ura/-ora reversives), adjective/adverb constants (COMPARISON degrees, ADJECTIVE_STEMS, ADVERBS_OF_MANNER), number system (NUMBERS 1–1B, NUMERAL_CONCORDS per noun class, ORDINAL_NOTE), particles/conjunctions/prepositions (CONJUNCTIONS, PREPOSITIONS, NEGATION_WORDS, NYA_PARTICLE), pronouns (PERSONAL_PRONOUNS, OBJECT_PRONOUNS), language names (LANGUAGE_NAMES), augmentative/pejorative prefix examples (AUGMENTATIVE_EXAMPLES, MAGNITUDE_EXAMPLES, MAGNITUDE_ERI_EXAMPLES), honorific names (EMPAAKO), interjections (INTERJECTIONS), idiomatic expressions (IDIOMS), proverbs (PROVERBS); translation pipeline helpers: apply_rl_rule_to_text() applies R/L rule across a full sentence, postprocess_lunyoro() applies an 8-step post-processing pipeline to every en→lun neural MT output (1. absent letter removal q/v/x per Orthography Rule 1, 2. R/L rule per Grammar Ch.2, 3. nasal assimilation nb→mb/np→mp/nr→nd/nm→mm, 4. ni- prefix vowel change nimu→numu/nigu→nugu, 5. consonant+suffix changes: vowel+r+-ire→-zire, vowel+t+-ire→-sire, nd+-ire→-nzire, nt+-ire→-nsire per Grammar Ch.2 — r+-i and r+-ya not applied globally to avoid stem-internal false positives, 6. y-insertion after a-/ra-/raa- before vowel stems (only when the following vowel differs from the prefix vowel, to avoid false positives on long-vowel words), 7. long vowel prefix merging aba+ana→abaana per Orthography Rule 7, 8. bb double consonant fixes for known words per Orthography Rule 5), preprocess_english() normalises English input before translation, get_noun_class_hint() returns a human-readable noun class description for a word, validate_runyoro_word() checks a word against alphabet/R-L/nasal-assimilation rules and returns valid + warnings + noun_class + is_verb
  prepare_training_data.py   — Corpus builder with domain tagging
  clean_new_submissions.py   — Merges new crowd-sourced submissions
  clean_extra.py             — Merges Excel dictionary datasets
  clean_remaining_raw.py     — Extracts translation pairs from remaining raw CSVs (word_submissions_rows*.csv, corpus_sentences_rows (1).csv); merges new pairs into english_nyoro_clean.csv after deduplication
  extract_ocr_pairs.py       — Extracts English ↔ Runyoro-Rutooro sentence pairs from OCR grammar data and merges them into english_nyoro_clean.csv; outputs data/cleaned/ocr_pairs_extracted.csv for review; run directly with `python extract_ocr_pairs.py`
  check_ocr_coverage.py      — Inspects each OCR source in all_ocr_combined.json and prints a page-by-page preview; useful for auditing grammar topic coverage before running extract_ocr_pairs.py; run directly with `python check_ocr_coverage.py` from the backend directory
  inspect_raw.py             — Inspects raw CSV files: prints row counts, column names, null counts, and sample rows
  back_translate.py          — Back-translation augmentation
  clean_backtranslated.py    — Quality filtering for synthetic pairs
  fine_tune.py               — MarianMT fine-tuning
  fine_tune_nllb.py          — NLLB-200 fine-tuning
  eval_models.py             — Evaluates all 4 models on the test set (BLEU, token F1, exact match)
  download_models.py         — Downloads all models from HuggingFace
  model/
    en2lun/                  — MarianMT English→Lunyoro
    lun2en/                  — MarianMT Lunyoro→English
    nllb_en2lun/             — NLLB-200 English→Lunyoro
    nllb_lun2en/             — NLLB-200 Lunyoro→English
    sem_model/               — Sentence transformer for semantic search

frontend/
  components/
    Translator.tsx           — Main translation UI
    Dictionary.tsx           — Dictionary lookup
    ChatPage.tsx             — AI chat assistant; renders bullet-point replies as numbered lists
    PdfTranslator.tsx        — Document summarization
    VoiceTranslator.tsx      — Voice input/output
    History.tsx              — Translation history
```

## Chat (LLM)

The chat assistant uses **LLaMA 3.2 3B** running locally via Ollama. It generates responses in English, which are then translated to Runyoro-Rutooro by the fine-tuned MarianMT model. No internet connection required after setup.

Before each request, the backend probes `localhost:11434` with a 1-second socket timeout. If Ollama is unreachable the call is skipped entirely (no hanging request). When reachable, the HTTP request timeout is 60 seconds. If Ollama is unavailable or the call fails, the `/chat` endpoint falls back to a built-in keyword-based responder that answers common question types (greetings, numbers, proverbs, grammar, translation requests) using the local language rules and corpus data — so the chat tab remains functional without Ollama running.

