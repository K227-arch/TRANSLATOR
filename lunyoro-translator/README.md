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
- Sources:
  - `english_nyoro_clean.csv` — main sentence pairs with domain tagging
  - `runyoro_english_sentences_clean.csv` — April crowd-sourced sentence submissions
  - `rutooro_dictionary_clean.csv` — word/definition/example pairs from the Rutooro dictionary
  - `word_entries_clean.csv` — dictionary example sentences and word-level definition pairs
  - `empaako_pairs.csv`, `idioms_pairs.csv`, `numbers_pairs.csv`, `interjections_pairs_clean.csv`, `proverbs_pairs_clean.csv` — small cultural/linguistic extras
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
- `python-dotenv` (optional — auto-loads `backend/.env` at startup if present)

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

> The Next.js API proxy rewrite has been removed from `next.config.ts`. Frontend components call the backend directly at `http://localhost:8000` (e.g. `/translate`, `/lookup`). Make sure the backend is running and CORS is enabled (it is, via FastAPI's `CORSMiddleware`) before starting the frontend.

## Training

### Full Automated Pipeline (Recommended)

Complete end-to-end pipeline that implements all Runyoro language rules:

```bash
cd backend

# Full pipeline: OCR extraction → back-translation → training → indexing → deployment
python full_pipeline.py

# Verify grammar integration and API endpoints only (no training)
python full_pipeline.py --verify-only

# Skip OCR extraction (if already done)
python full_pipeline.py --skip-ocr

# Skip data preparation (if data already prepared)
python full_pipeline.py --skip-data

# Skip training, only push to HuggingFace/Git
python full_pipeline.py --skip-train
```

The full pipeline executes:
1. Extract OCR word glosses + sentence pairs using language_rules.py
2. Back-translate sentence_submissions to augment training data
3. Quality-filter synthetic pairs (round-trip + semantic checks)
4. Rebuild training splits (train/val/test)
5. Fine-tune MarianMT from checkpoint (15 epochs, LR=2e-5, label_smoothing=0.2)
6. Fine-tune NLLB from checkpoint (8 epochs, DDP across 2+ GPUs if available)
7. Rebuild semantic search index
8. Push all 4 models to HuggingFace
9. Commit and push to Git LFS

Grammar rules integration:
- Full Runyoro-Rutooro grammar context wired to /chat endpoint
- All grammar rules exposed via /language-rules endpoint
- OCR-derived rules from Chapters 2, 4, 7, 9, 10, 12, 13, 15, 16, 17

### Manual Training Steps

For more control over individual steps:

```bash
cd backend

# 1. Merge new submissions and rebuild training splits
python clean_new_submissions.py

# (Alternative) Clean and merge previously unprocessed raw files
python clean_unprocessed_raw.py

# 2. Extract OCR pairs and glosses
python extract_ocr_pairs.py

# 3. Back-translation augmentation
python back_translate.py
python clean_backtranslated.py

# 4. Retrain MarianMT models
python fine_tune.py --direction both --epochs 10 --batch_size 32

# 5. Retrain NLLB models
python fine_tune_nllb.py --direction both --epochs 10 --batch_size 4

# 6. Rebuild semantic search index
python train.py

# 7. Evaluate all 4 models on the test set
python run_eval.py  # Sequential single-GPU (auto-selects GPU)
python eval_all_parallel.py  # Parallel across 2 GPUs
python eval_marian.py  # MarianMT only (CPU, leaves GPUs free)
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
  language_rules.py          — Orthography constants (alphabet, vowels, diphthongs, apostrophe contexts), R/L rule, noun class system (classes 1–15 with prefixes), get_noun_class() for morphological prefix analysis, concordial agreement table (subject/object/adjective concords per class) with get_subject_concord()/get_object_concord() helpers, plural sound changes (class 11→10), get_class6_prefix() for class 5→6 plural prefix selection, verb structure constants (infinitive prefixes, subject prefixes, tense/aspect markers, negative markers, verb suffixes, derivative suffixes), full tense system reference (TENSES dict + CONDITIONAL_PARTICLES), detailed derivative verb formation rules (PREPOSITIONAL_FORMATION for -ira/-era applied verbs, PASSIVE_FORMATION for -ibwa/-ebwa passives, CAUSATIVE_FORMATION for -isa/-esa/-ya causatives, NEUTER_FORMATION for -ika/-eka statives, CONVERSIVE_FORMATION for -ura/-ora reversives), adjective/adverb constants (COMPARISON degrees, ADJECTIVE_STEMS, ADVERBS_OF_MANNER), number system (NUMBERS 1–1B, NUMERAL_CONCORDS per noun class, ORDINAL_NOTE), particles/conjunctions/prepositions (CONJUNCTIONS, PREPOSITIONS, NEGATION_WORDS, NYA_PARTICLE), pronouns (PERSONAL_PRONOUNS, OBJECT_PRONOUNS), language names (LANGUAGE_NAMES), augmentative/pejorative prefix examples (AUGMENTATIVE_EXAMPLES, MAGNITUDE_EXAMPLES, MAGNITUDE_ERI_EXAMPLES), honorific names (EMPAAKO), interjections (INTERJECTIONS), idiomatic expressions (IDIOMS), proverbs (PROVERBS), compound tense conditional constructions (CONDITIONAL_CONSTRUCTIONS, CONDITIONAL_TENSE_PATTERNS by time reference, CONDITIONAL_KU_MARKER, INFINITIVE_CONDITIONAL, RELATIVE_CONDITIONAL) with get_conditional_pattern() helper, genitive particles per noun class (GENITIVE_PARTICLES) with get_genitive_particle() helper, relative concords and particles (RELATIVE_CONCORDS, RELATIVE_PARTICLES) with get_relative_concord() helper, noun derivation patterns (NOUN_DERIVATION, NOUN_DERIVATION_SUFFIXES) with derive_agent_noun() helper, complete orthography rules (PRENASALIZATION_RULES, DOUBLE_CONSONANT_RULES, SYLLABIFICATION_RULES, INITIAL_VOWEL_RULES, TONE_RULES), imperative mood with object prefixes (IMPERATIVE_WITH_OBJECTS, REFLEXIVE_IMPERATIVE), utility functions is_prenasalized() and has_initial_vowel(); translation pipeline helpers: apply_rl_rule_to_text() applies R/L rule across a full sentence, postprocess_lunyoro() applies an 8-step post-processing pipeline to every en→lun neural MT output (1. absent letter removal q/v/x per Orthography Rule 1, 2. R/L rule per Grammar Ch.2, 3. nasal assimilation nb→mb/np→mp/nr→nd/nm→mm, 4. ni- prefix vowel change nimu→numu/nigu→nugu, 5. consonant+suffix changes: vowel+r+-ire→-zire, vowel+t+-ire→-sire, nd+-ire→-nzire, nt+-ire→-nsire per Grammar Ch.2 — r+-i and r+-ya not applied globally to avoid stem-internal false positives, 6. y-insertion after a-/ra-/raa- before vowel stems (only when the following vowel differs from the prefix vowel, to avoid false positives on long-vowel words), 7. long vowel prefix merging aba+ana→abaana per Orthography Rule 7, 8. bb double consonant fixes for known words per Orthography Rule 5), preprocess_english() normalises English input before translation, get_noun_class_hint() returns a human-readable noun class description for a word, validate_runyoro_word() checks a word against alphabet/R-L/nasal-assimilation rules and returns valid + warnings + noun_class + is_verb
  language_rules_extra.py    — Additional grammar rules from OCR grammar books and the official Runyoro-Rutooro Orthography Guide (Ministry of Gender, Uganda, 1995); contains ORTHOGRAPHY_RULES dict (rules 1–27) covering alphabet, c/l/r usage, double consonants, long vowels, prenasals, proper names, possessives, copula forms, negative particles, foreign word spelling, and place/people name conventions; RELATIVE_PHRASE_PARTICLES covering -nyaku-/-owa-/-eya- particles used in relative phrases across tenses; SUBJECT_RELATIVE_CONCORDS_FULL with full initial-vowel forms for all 15 noun classes; RELATIVE_CONCORD_ELISION rule; LOCATIVE_PREFIXES (omu-/ha-/ku-/owa-/omba- with meanings and examples), LOCATIVE_DEMONSTRATIVES (munu/muli/hanu/hali/kunu/kuli), ADVERBIAL_SUFFIXES (-ho/-yo/-mu/-ko with examples), LOCATIVE_POSSESSIVES; COLLECTIVE_NOUNS (ekitebe/igana/omuzinga/eka/oruganda/ihanga/orukurato/ihe with concordial agreement note); FIVE_MOODS (infinitive, imperative, indicative, subjunctive, conditional with forms and examples); PARTICIPLES (present-imperfect, not-yet, virtual-present, present-perfect); AUXILIARY_VERBS (okuba/okubanza/okugaruka/okumanya/okumalira/okubaleka with roles and examples); ORDINALS (formation via genitive particle + okubanza, with class examples); FRACTIONS and DISTRIBUTIVES (reduplication pattern, buli alternative); NUMBER_CONNECTORS (mu/na for hundreds/thousands); NUMERAL_CONCORD_DETAILS (concord rules for classes 10–15); ADJECTIVE_TYPES (true adjectives, nouns-as-qualifiers, relative phrases, pronouns, numerals); RELATIVE_ADJECTIVE_EXAMPLES (present-imperfect and present-perfect relative phrase adjectives); ADVERB_TYPES (manner/place/time); BU_ADVERBS (bu- prefix formation with sentence examples); ADVERBS_OF_PLACE and ADVERBS_OF_TIME; VERBAL_MANNER_EXPRESSIONS (verbs implying both action and manner); SENTENCE_STRUCTURE and SENTENCE_TYPES (basic subject+predicate pattern, 9 sentence type templates, verb forms after self-standing pronouns, negative copula in questions); FOREIGN_WORDS (loanword spellings as pronounced by Banyoro/Batooro, per Orthography Rule 24); imported by language_rules.py
  prepare_training_data.py   — Corpus builder with domain tagging
  clean_new_submissions.py   — Merges new crowd-sourced submissions
  clean_unprocessed_raw.py   — Cleans and merges previously unprocessed raw files (word_submissions_rows, word_entries_rows_root, sentence_submissions_rows) into english_nyoro_clean.csv and word_entries_clean.csv, then rebuilds train/val/test splits
  extract_ocr_pairs.py       — Extracts English ↔ Runyoro-Rutooro sentence pairs from OCR grammar data (data/OCR/combined/all_ocr_combined.json) and merges them into english_nyoro_clean.csv; uses heuristic language detection (Runyoro prefix patterns + English function words) to validate pairs before merging; outputs data/cleaned/ocr_pairs_extracted.csv for review; run directly with `python extract_ocr_pairs.py`
  check_ocr_coverage.py      — Inspects each OCR source in all_ocr_combined.json and prints a preview of its pages; useful for auditing which grammar topics are covered before running extract_ocr_pairs.py; run directly with `python check_ocr_coverage.py` from the backend directory
  push_models_hf.py            — Uploads all 4 fine-tuned model folders (en2lun, lun2en, nllb_en2lun, nllb_lun2en) to their respective HuggingFace repos; requires HF_TOKEN env var with write access
  clean_sentence_submission.py — Cleans the April sentence submission Excel file (Runyoro-English_Translation.xlsx); standardises columns, strips whitespace, drops empty rows and duplicates, writes data/cleaned/runyoro_english_sentences_clean.csv
  clean_remaining_raw.py     — Extracts translation pairs from remaining raw CSVs (word_submissions_rows*.csv, corpus_sentences_rows (1).csv); merges new pairs into english_nyoro_clean.csv after deduplication
  clean_extra.py             — Merges Excel dictionary datasets
  clean_dictionaries.py      — Cleans and converts Rutooro/Runyoro Excel dictionary files to CSV; normalises column names, strips definition noise (grammar notation, cross-references, OCR-duplicated phrases), deduplicates entries, and writes data/cleaned/rutooro_dictionary_clean.csv
  inspect_raw.py             — Inspects raw CSV files: prints row counts, column names, null counts, and sample rows for word/sentence submission and corpus files
  _audit.py                  — Full audit of training data quality AND grammar rule coverage: (1) quality checks — double-tagged pairs, source==target, repeated word runs, short/empty rows, exact duplicates; (2) orthographic rule checks — R/L rule violations, nasal assimilation violations, ni→nu prefix violations, apostrophe normalisation violations; (3) grammar rule coverage — verifies every OCR chapter (Ch.2 sound change, Ch.4 numbers/particles, Ch.7 noun classes, Ch.9/10 noun formation, Ch.12 derivative verbs, Ch.13 moods/tenses, Ch.15 conditional, Ch.16 comparison, Ch.17 particles) plus cultural data and orthography examples are represented in the corpus; prints OK/MISSING per category with match counts; exits with "DATA IS CLEAN AND QUALIFIED FOR TRAINING" or "ISSUES REMAIN - DO NOT TRAIN YET"
  audit_csvs.py              — Audits all CSV files in data/: reports row counts, nulls, duplicates, and whether a cleaned version exists
  check_dups.py              — Checks whether pairs of raw CSV files are identical (e.g. versioned duplicates like word_entries_rows.csv vs word_entries_rows (1).csv)
  verify_dict.py             — Verifies the cleaned dictionary CSV: prints row count, null counts per column, and sample rows that have both a definition and a Runyoro example sentence
  generate_rule_training_pairs.py — Generates synthetic (english, lunyoro) training pairs by mining every grammar rule constant in language_rules.py and language_rules_ocr_extension.py; covers all OCR grammar chapters (Ch.2 sound changes, Ch.4 numbers/particles, Ch.7 noun classes, Ch.9/10 noun formation, Ch.12 derivative verbs, Ch.13 moods/tenses, Ch.15 conditional mood, Ch.16 adjectives/comparison, Ch.17 genitive/adverbial/coordinating particles) plus cultural data (EMPAAKO, interjections, idioms) and orthography examples; also synthesises derivative verb pairs (causative, passive, neuter, reciprocal, conversive) for 18 common verb stems; deduplicates output; run directly with `python generate_rule_training_pairs.py` to preview generated pairs
  back_translate.py          — Back-translation augmentation
  clean_backtranslated.py    — Quality filtering for synthetic pairs
  improve_and_retrain.py     — Full improvement pipeline: extracts OCR pairs (step 0), back-translates sentence_submissions, quality-filters synthetic pairs, rebuilds training splits, fine-tunes MarianMT (15 epochs, LR=2e-5, label_smoothing=0.2) and NLLB (8 epochs, label_smoothing=0.2) from existing checkpoints, rebuilds the semantic search index, then pushes all 4 models + updated dataset to HuggingFace and commits/pushes code and data to GitHub. NLLB training uses DistributedDataParallel (DDP) via torchrun when 2+ GPUs are available (gloo backend, compatible with Windows); falls back to single-GPU automatically. Pass --skip-ocr to skip OCR extraction (step 0); pass --skip-data to skip steps 0-3; pass --skip-train to skip training and only push existing models to HuggingFace
  verify_implementation.py   — Standalone verification script: checks grammar rules files exist and import correctly (NOUN_CLASSES, TENSES, IMPERATIVE_TENSES, CAUSATIVE_FORMATION, COMPARISON_POSITIVE, GENITIVE_PARTICLES, get_full_grammar_context()), validates R/L rule application and noun class detection, confirms /chat and /language-rules endpoints are wired in main.py, checks pipeline scripts exist, verifies OCR data and cleaned data directories, and checks all 4 model directories; run directly with `python verify_implementation.py`
  full_pipeline.py           — Orchestrator that wraps improve_and_retrain.py with pre-flight verification: checks grammar rule integration (NOUN_CLASSES, TENSES, IMPERATIVE_TENSES, CAUSATIVE_FORMATION, COMPARISON_POSITIVE, GENITIVE_PARTICLES, get_full_grammar_context()) and API endpoint configuration (/chat wired with full grammar context, /language-rules exposing all OCR-derived rules) before running the pipeline. Accepts the same --skip-ocr / --skip-data / --skip-train flags as improve_and_retrain.py, plus --verify-only to run checks without executing the pipeline. Steps: 0 (OCR extraction) → 1 (back-translate) → 2 (quality filter) → 3 (rebuild splits) → 4 (fine-tune MarianMT) → 5 (fine-tune NLLB) → 6 (rebuild index) → 7 (push to HuggingFace) → 8 (push to Git LFS)
  fine_tune.py               — MarianMT fine-tuning
  fine_tune_nllb.py          — NLLB-200 fine-tuning
  eval_models.py             — Evaluates all 4 models on the test set (BLEU, token F1, exact match)
  eval_marian.py             — MarianMT-only evaluation: runs on CPU, leaving both GPUs free for concurrent NLLB training; outputs eval_marian_results.json (BLEU, token F1, exact match)
  run_eval.py                — Sequential single-GPU evaluation: auto-selects the GPU with the most free memory (avoids conflicts with Ollama); outputs eval_results_all.json
  eval_all_parallel.py       — Evaluates all 4 models in parallel across 2 GPUs (GPU 0: MarianMT, GPU 1: NLLB); outputs eval_results_all.json
  download_models.py         — Downloads all models from HuggingFace
  model/
    en2lun/                  — MarianMT English→Lunyoro
    lun2en/                  — MarianMT Lunyoro→English
    nllb_en2lun/             — NLLB-200 English→Lunyoro
    nllb_lun2en/             — NLLB-200 Lunyoro→English
    sem_model/               — Sentence transformer for semantic search

frontend/
  next.config.ts             — Next.js config; standalone output is enabled only for Docker
                               builds (DOCKER_BUILD=1 env var, set automatically by the
                               Dockerfile). Vercel and local dev use Next.js default output.
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
