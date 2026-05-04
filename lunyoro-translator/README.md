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
ollama pull qwen2.5:3b
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
  translate.py               — Translation logic (MarianMT + NLLB + retrieval); post-processes en→lun MT output with Runyoro-Rutooro orthographic rules (nasal assimilation nb→mb/np→mp/nr→nd, ni→nu prefix vowel harmony, R/L rule); pre-processes lun→en input by normalising nasal clusters to canonical forms; rules are lazy-loaded from language_rules so the module loads safely even if language_rules has an import error
  language_rules.py          — Complete Runyoro-Rutooro grammar rules: orthography (alphabet, vowels, R/L rule), noun class system (classes 1–15 with prefixes, concordial agreement, plural formation), verb structure (infinitive/subject/tense prefixes, derivative suffixes), tense system, adjectives/adverbs, numbers/ordinals, particles/conjunctions/prepositions, pronouns, cultural elements (EMPAAKO, interjections, idioms, proverbs); OCR-derived rules from grammar books (Chapters 15–17): comparison (positive/comparative/superlative), genitive particles, adverbial particles, coordinating particles, conditional mood; provides get_full_grammar_context() for comprehensive grammar context used by chat endpoint; executable transformation functions: apply_rl_rule()/apply_rl_rule_to_text() (R/L rule), apply_nasal_assimilation() (nb→mb etc.), apply_ni_prefix_change() (ni-→nu- vowel harmony), apply_y_insertion() (y-insertion after a-/ra-/raa- tense prefixes), apply_consonant_suffix_change() (r/t/j + suffix sound changes; correctly strips trailing -a from full verb forms before matching consonant endings, e.g. okubara + -ire → okubazire), apply_conversive_suffix() (reversive -ura/-ora), apply_reflexive_imperative() (wee-/mwe- reflexive imperatives), apply_apostrophe_elision() (vowel elision with apostrophe for particles before vowel-initial words, e.g. "na ente" → "n'ente"; source: Orthography Guide 1995), apply_concordial_agreement() (adjective prefix by noun class), build_plural() (prefix-substitution + irregular class-11 plurals), apply_class9_nasal_prefix() (en-/em- selection), build_verb_form() (full verb assembly from person/tense/stem), apply_causative()/-passive()/-neuter()/-reciprocal() (derivative verb forms), get_adjective_concord()/get_demonstrative()/get_numeral_concord() (concordial lookups), build_ordinal() (ordinal numerals in concordial agreement); text-level MT post-processing functions (Grammar Rule 3): apply_consonant_suffix_mutations() (applies r→z/t→s/j→z/nd→nz/nt→ns before -ire/-ere/-i/-ya across all words in MT output; source: Grammar Rule 3 §B.5–6), apply_reflexive_imperative_correction() (converts reflexive infinitives okw-e... to correct imperative form wee.../mwe...; source: Grammar Rule 3 §4), apply_initial_vowel_rule() (ensures each noun/adjective carries the correct initial vowel for its noun class; source: Grammar Rule 3 §8). Ch.2 sound change data now also defined directly in this module: Y_INSERTION_EXAMPLES, Y_INSERTION_COUNTEREXAMPLES, Y_INSERTION_I_STEMS (y-insertion after a-/ra-/raa- tense prefixes), REFLEXIVE_IMPERATIVES (wee-/mwe- singular/plural reflexive imperative forms), REFLEXIVE_NON_REFLEXIVE (reflexive-prefixed verbs with non-reflexive meanings). Ch.4 words/affixes/negation data now also defined directly in this module: NEGATION_EXTENDED (declinable/undeclinable negation words with examples), AFFIRMATION_WORDS, POSSESSIVE_PRONOUNS (genitive particles + self-standing pronouns per noun class), GENITIVE_ELISION_RULES, INTERROGATIVE_PARTICLES (ki?/di?/nkaha?/habwaki?), PARTS_OF_SPEECH, IDEOPHONES, ORDINAL_FORMATION (1st via okubanza, 2nd–5th via ka- prefix), ORDINALS_EXTENDED (6th–10th, above 10th, fractions), NUMBER_CONNECTION (hundreds/thousands connected by mu/na), NUMERAL_ADVERBIAL_KA (ka- prefix = how many times), ORTHOGRAPHY_RULES (1995 Guide: alphabet, rule_c, rule_l/r, double consonants, long vowels, apostrophe). Ch.13 moods and tenses data now also defined directly in this module: IMPERATIVE_TENSES (present/continuous/near-future/far-future/continuous-future imperative forms), SUBJUNCTIVE_FUNCTIONS, SUBJUNCTIVE_EXAMPLES, INDICATIVE_TENSES (present indefinite/imperfect/perfect/virtual), VERB_INA_CONJUGATION (-ina 'to have'), VERB_LI_CONJUGATION (-li 'to be'); remaining OCR-extended symbols (Chapters 7, 9, 10, 12) are defined in language_rules_ocr_extension — import them from there
  language_rules_ocr_extension.py — Extended grammar rules from OCR grammar books (Chapters 2, 7, 9, 10, 12): sound change rules (CONVERSIVE_EXAMPLES; Y_INSERTION_EXAMPLES, Y_INSERTION_COUNTEREXAMPLES, Y_INSERTION_I_STEMS, REFLEXIVE_IMPERATIVES, REFLEXIVE_NON_REFLEXIVE are now also defined in language_rules.py), derivative verb formation (APPLIED_VERB_MEANINGS, APPLIED_VERB_EXAMPLES, PREPOSITIONAL_NEW_MEANINGS, DOUBLE_PREPOSITIONAL, CAUSATIVE_FORMATION, PASSIVE_FORMATION, NEUTER_FORMATION, RECIPROCAL_FORMATION), moods and tenses (IMPERATIVE_TENSES, SUBJUNCTIVE_FUNCTIONS, SUBJUNCTIVE_EXAMPLES, INDICATIVE_TENSES, VERB_INA_CONJUGATION, VERB_LI_CONJUGATION are now also defined in language_rules.py), extended noun class details (CLASS_12_13_14_DETAILS, AUGMENTATIVE_PEJORATIVE_EXTENDED), ordinal formation (ORDINAL_FORMATION, NUMBER_CONNECTION, ORDINALS_EXTENDED are now also defined in language_rules.py), noun formation (DEVERBATIVE_SUFFIXES, NOUN_FUNCTIONS, NOUN_KINDS, VERBAL_NOUNS_CLASS5), class 6 plural rules (CLASS6_PLURAL_RULES, CLASS6_OTHER_PLURALS), words/affixes/negation (NEGATION_EXTENDED, AFFIRMATION_WORDS, POSSESSIVE_PRONOUNS, GENITIVE_ELISION_RULES, INTERROGATIVE_PARTICLES, PARTS_OF_SPEECH, IDEOPHONES, NUMERAL_ADVERBIAL_KA, ORTHOGRAPHY_RULES are now also defined in language_rules.py); utility functions get_derivative_verb_type(), get_imperative_form(), is_reflexive_verb(), get_full_grammar_context() (combines base + OCR-derived rules for comprehensive grammar context)
  prepare_training_data.py   — Corpus builder with domain tagging; merges all cleaned data sources including synthetic grammar rule pairs generated from all OCR grammar chapters (Ch.2 sound change, Ch.4 numbers/particles, Ch.7 noun classes, Ch.9/10 noun formation, Ch.12 derivative verbs, Ch.13 moods/tenses, Ch.15 conditional, Ch.16 comparison, Ch.17 genitive/adverbial particles) via generate_rule_training_pairs.py; strips any pre-existing domain tag(s) from english_nyoro_clean.csv before re-tagging — handles multiple stacked tags and mixed case (e.g. `[GENERAL] [GENerAL] text`) via a case-insensitive repeating regex, preventing double-tagging on repeated runs; applies four normalization steps to all Lunyoro training targets: (1) apostrophe standardisation (curly/Unicode apostrophes → straight ASCII apostrophe), (2) nasal assimilation (nb→mb, np→mp, nr→nd, nl→nd), (3) ni→nu prefix vowel harmony (nimugenda→numugenda before u-class concords), and (4) the R/L rule (L→R except adjacent to e/i), so models learn consistent orthographic forms
  clean_new_submissions.py   — Merges new crowd-sourced submissions
  clean_unprocessed_raw.py   — Cleans and merges previously unprocessed raw files (word_submissions_rows, word_entries_rows_root, sentence_submissions_rows) into english_nyoro_clean.csv and word_entries_clean.csv, then rebuilds train/val/test splits
  analyze_ocr.py             — Analyses the OCR combined JSON (data/OCR/combined/all_ocr_combined.json): classifies lines as Runyoro-dominant, English-dominant, mixed, or unclassified using regex heuristics; reports per-source page/char/line counts; prints sample Runyoro lines and quoted lines (likely translation pairs); run directly with `python analyze_ocr.py`
  analyze_ocr2.py            — Deep analysis of OCR grammar content: samples one full page per source, detects table/structured content (tab-separated or multi-space lines), extracts Runyoro example sentences using a broader prefix pattern set, finds inline word glosses (word 'meaning' patterns for Runyoro-prefixed terms), and summarises dominant grammar topic per source (noun_class, verb_tense, sound_change, adjective, derivative_verb, numbers, orthography); run directly with `python analyze_ocr2.py`
  dump_ocr_sections.py       — Dumps the first 2000 chars of each page for a fixed list of unintegrated OCR sections (grammar_sound_change, grammar2_derivative_verbs, grammar2_moods_tenses_*, grammar2_compound_tenses_*, grammar_noun_classes*, grammar2_noun_formation, grammar_numbers_ordinals, grammar_words_affixes_*, runyoro_rutooro_orthography_guide) to stdout for manual review; run directly with `python dump_ocr_sections.py`
  dump_ocr2.py               — Extracts the full text of the same unintegrated OCR sections and writes them to ocr_content.txt for offline review; unlike dump_ocr_sections.py (which truncates to 2000 chars per page and prints to stdout), this writes complete page content to a file; run directly with `python dump_ocr2.py`
  dictionary_pipeline.py     — Full dictionary data pipeline (7 steps): (1) clean OCR noise + apply orthographic rules to dictionary Excel files (dictionary_pairs.xlsx, english_runyoro_dict.xlsx, runyoro_english_dict.xlsx); (2) augment with derivative verb forms (causative -isa, passive -ibwa, reciprocal -ana, reversive -ura) from Runyoro→English entries; (3) back-translate Runyoro example sentences via the lun2en model to generate synthetic pairs; (4) merge all new pairs into english_nyoro_clean.csv with [DICTIONARY] domain tag and rebuild train/val/test splits; (5) fine-tune MarianMT en2lun + lun2en from existing checkpoints — checkpoints are saved to a temp directory (_<direction>_training_tmp/) during training so the live model is never touched mid-run; the best checkpoint is atomically copied to the live model path only after training completes, then the temp dir is removed; each model is then pushed to HuggingFace in a background thread, freeing the GPU for the next model immediately (requires HF_TOKEN env var; skipped with a warning if not set); (6) explicit push of all 4 retrained models (en2lun, lun2en, nllb_en2lun, nllb_lun2en) to HuggingFace (fallback/standalone push); (7) rebuild semantic search index. Post-step quality filtering via clean_pairs_df() applied after augmentation and back-translation: length bounds (English 3–300 chars, Lunyoro 2–200 chars), grammar notation noise rejection, English/Runyoro side validation (rejects swapped pairs, pure-English Lunyoro, all-Runyoro English), round-trip identity check, orthographic normalisation, deduplication. Options: --skip-train (steps 1–4 only), --skip-backtrans (skip step 3), --skip-nllb (skip NLLB retraining), --only-nllb (skip MarianMT, retrain NLLB only), --epochs, --batch-size, --lr. Run: `python dictionary_pipeline.py`
  extract_dictionary_pdf.py  — Extracts all entries from runyoro-Rutooro-Dictionary.pdf into structured CSVs; parses Runyoro→English entries (pages 14–446) and English→Runyoro entries (pages 447–627); outputs data/dictionary/runyoro_english_dict.csv, data/dictionary/english_runyoro_dict.csv, and data/dictionary/dictionary_pairs.csv (flat training pairs); training pairs are filtered using is_english_sentence() (requires ≥2 words, at least one English stopword, no grammar notation noise) and is_runyoro_phrase() (rejects grammar noise and predominantly English text) helpers; definition pairs use only the first sentence of each definition to avoid bleed-over; English→Runyoro entries skip noise tokens (digits, commas, semicolons in headword) and emit one primary equivalent per entry; final deduplication stage applies additional quality filters: length bounds (English 3–250 chars, Lunyoro 2–150 chars), rejects English fields containing Runyoro noun-class prefixes (oku/omu/emi/ebi/eki/aka/ama/obu/oru), rejects Lunyoro fields that are predominantly English (>3 words with English function words), and strips pairs containing grammar notation noise (pf., pr. form, c. form, pass. form, cl.N); run directly with `python extract_dictionary_pdf.py`
  csv_to_xlsx.py             — Converts the three dictionary CSVs produced by extract_dictionary_pdf.py (runyoro_english_dict.csv, english_runyoro_dict.csv, dictionary_pairs.csv) to Excel format (.xlsx) and removes the original CSV files; run after extract_dictionary_pdf.py when Excel output is needed: `python csv_to_xlsx.py`
  extract_ocr_pairs.py       — Extracts English ↔ Runyoro-Rutooro sentence pairs AND word glosses from OCR grammar data (data/OCR/combined/all_ocr_combined.json); uses language_rules.py prefix/vocabulary data for detection (threshold 0.10 for Runyoro, 0.15 for English); merges sentence pairs into english_nyoro_clean.csv and word glosses into word_entries_clean.csv; outputs data/cleaned/ocr_pairs_extracted.csv (sentence pairs) and data/cleaned/ocr_glosses_extracted.csv (word glosses) for review; run directly with `python extract_ocr_pairs.py`
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
    ChatPage.tsx             — AI chat assistant; renders LLM responses with inline markdown formatting (bold, italic, quoted text) and bullet lists as styled JSX
    PdfTranslator.tsx        — Document summarization
    VoiceTranslator.tsx      — Voice input/output
    History.tsx              — Translation history
```

## Chat (LLM)

The chat assistant uses **Qwen 2.5 3B** running locally via Ollama. It generates responses in English, which are then translated to Runyoro-Rutooro by both MarianMT and NLLB-200 in parallel (via `ThreadPoolExecutor`), returning results from both models. No internet connection required after setup.

Every chat request injects the full grammar context via `get_full_grammar_context()` (from `language_rules_ocr_extension`) into the system prompt. This includes core grammar rules, OCR-derived rules (derivative verbs, moods/tenses, noun classes, ordinals), and extended rules from Chapters 2, 4, 7, 9, 10, 12, and 13 of the grammar books.
