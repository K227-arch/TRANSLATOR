# Complete Pipeline Implementation Guide

## Overview

This guide documents the complete implementation of the Runyoro-Rutooro translator pipeline, including grammar rules integration, OCR data extraction, model training, and automated deployment.

## Architecture

### Grammar Rules System

**Core Module**: `backend/language_rules.py`
- Orthography rules (alphabet, R/L rule, vowels, diphthongs)
- Noun class system (classes 1-15 with prefixes and concordial agreement)
- Verb structure (infinitive/subject/tense prefixes, derivative suffixes)
- Tense system (present, past, future, perfect, conditional)
- Adjectives, adverbs, comparison rules
- Numbers, ordinals, numeral concords
- Particles, conjunctions, prepositions
- Cultural elements (EMPAAKO, interjections, idioms, proverbs)
- OCR-derived rules (Chapters 15-17): comparison, genitive particles, adverbial particles

**Extension Module**: `backend/language_rules_ocr_extension.py`
- Sound change rules (Y-insertion, reflexive verbs, conversive suffixes)
- Derivative verbs (applied, causative, passive, neuter, reciprocal)
- Moods and tenses (imperative, subjunctive, indicative)
- Extended noun classes (12-14, augmentative/pejorative)
- Ordinal formation, fractions
- Noun formation (deverbative suffixes, functions, kinds)
- Extended negation, affirmation, interrogatives
- Parts of speech, ideophones
- Orthography guide (1995)

**Integration**: All rules are re-exported from `language_rules.py` for single-module import.

### API Endpoints

**Chat Endpoint** (`/chat`):
- Uses `get_full_grammar_context()` in system prompt
- Injects complete grammar rules (core + OCR-derived) into every LLM request
- Translates LLM English output to Runyoro using MarianMT + language rules

**Language Rules Endpoint** (`/language-rules`):
- Exposes all grammar rules as JSON
- Includes: noun classes, verb tenses, derivative verbs, comparison rules, genitive particles, ordinals, numbers, cultural elements
- Also exposes sound change data: nasal assimilation, ni-prefix changes, consonant suffix changes, conversive suffix map, subject prefixes, tense markers, numeral concords
- Returns 50+ rule categories with examples

**Grammar Rule Application Endpoint** (`POST /language-rules/apply`):
- Programmatically applies any Runyoro-Rutooro grammar transformation
- Accepts a `rule` name plus optional `text`, `verb_stem`, `person`, `tense`, `negative`, `noun_class`, `number`, `n` fields
- Supported rules: `rl_rule`, `nasal_assimilation`, `ni_prefix_change`, `y_insertion`, `consonant_suffix`, `conversive`, `reflexive_imperative`, `concordial_agreement`, `build_plural`, `class9_nasal`, `build_verb`, `causative`, `passive`, `neuter`, `reciprocal`, `adjective_concord`, `demonstrative`, `numeral_concord`, `ordinal`

### Data Pipeline

**OCR Extraction** (`extract_ocr_pairs.py`):
- Reads `data/OCR/combined/all_ocr_combined.json`
- Uses `language_rules.py` prefix/vocabulary data for detection
- Extracts sentence pairs (English ↔ Runyoro)
- Extracts word glosses (word → definition)
- Outputs:
  - `data/cleaned/ocr_pairs_extracted.csv` (sentence pairs)
  - `data/cleaned/ocr_glosses_extracted.csv` (word glosses)
- Merges into:
  - `data/cleaned/english_nyoro_clean.csv` (main corpus)
  - `data/cleaned/word_entries_clean.csv` (dictionary)

**Back-Translation** (`back_translate.py`):
- Takes Lunyoro sentences from corpus
- Translates to English using fine-tuned lun2en model
- Adds (synthetic_english, lunyoro) pairs to training data
- Quality filters: length checks, hallucination detection, ASCII ratio

**Quality Filtering** (`clean_backtranslated.py`):
- Round-trip consistency checks
- Semantic similarity filtering
- Removes repeated word runs
- Deduplicates pairs

**Training Split Builder** (`prepare_training_data.py`):
- Merges all cleaned data sources
- Applies domain tagging
- Injects synthetic grammar rule pairs from `generate_rule_training_pairs.py`, covering all OCR grammar chapters: Ch.2 (sound change), Ch.4 (numbers/particles), Ch.7 (noun classes), Ch.9/10 (noun formation), Ch.12 (derivative verbs), Ch.13 (moods/tenses), Ch.15 (conditional), Ch.16 (comparison), Ch.17 (genitive/adverbial particles)
- Strips any pre-existing domain tag(s) from `english_nyoro_clean.csv` before re-tagging — handles multiple stacked tags and mixed case (e.g. `[GENERAL] [GENerAL] text`) using a case-insensitive repeating regex, preventing double-tagging on repeated runs
- Normalizes all Lunyoro training targets with four steps in sequence:
  1. Apostrophe standardisation (curly/Unicode apostrophes → straight ASCII `'`)
  2. Nasal assimilation (nb→mb, np→mp, nr→nd, nl→nd)
  3. ni→nu prefix vowel harmony (nimugenda→numugenda before u-class concords)
  4. R/L rule (L→R except adjacent to e/i)
- Splits: 80% train, 10% val, 10% test
- Outputs: `data/training/{train,val,test}.csv`

### Model Training

**MarianMT** (`fine_tune.py`):
- Fine-tunes from existing checkpoint (not from scratch)
- 15 epochs, LR=2e-5, label_smoothing=0.2
- Batch size 32 (per GPU)
- Supports multi-GPU via DataParallel
- Directions: en2lun, lun2en

**NLLB-200** (`fine_tune_nllb.py`):
- Fine-tunes from existing checkpoint
- 8 epochs, LR=2e-5, label_smoothing=0.2
- Batch size 8 per GPU, gradient accumulation 4
- Uses DistributedDataParallel (DDP) for 2+ GPUs
- Gloo backend (Windows-compatible)
- Falls back to single-GPU automatically
- Directions: nllb_en2lun, nllb_lun2en

**Semantic Search Index** (`train.py`):
- Encodes all corpus pairs with sentence-transformers
- Builds retrieval index for context-aware translation
- Saves to `retrieval_index.pkl`

### Deployment

**HuggingFace Upload** (`push_models_hf.py`):
- Uploads all 4 models to keithtwesigye/* repos
- Requires HF_TOKEN environment variable
- Repos:
  - `keithtwesigye/lunyoro-en2lun`
  - `keithtwesigye/lunyoro-lun2en`
  - `keithtwesigye/lunyoro-nllb_en2lun`
  - `keithtwesigye/lunyoro-nllb_lun2en`

**Git LFS Push**:
- Stages model weights, data, scripts
- Commits with descriptive message
- Pushes to origin/main with LFS

## Complete Pipeline Execution

### Option 1: Full Automated Pipeline (Recommended)

```bash
cd backend
python full_pipeline.py
```

This executes all steps in sequence:
1. Verify grammar integration
2. Extract OCR pairs and glosses
3. Back-translate sentence submissions
4. Quality-filter synthetic pairs
5. Rebuild training splits
6. Fine-tune MarianMT (15 epochs)
7. Fine-tune NLLB (8 epochs, DDP)
8. Rebuild semantic search index
9. Push to HuggingFace
10. Push to Git LFS

**Options**:
- `--verify-only`: Check grammar integration without training
- `--skip-ocr`: Skip OCR extraction (if already done)
- `--skip-data`: Skip data prep (steps 1-5)
- `--skip-train`: Skip training, only deploy

### Option 2: Manual Step-by-Step

```bash
# 1. Extract OCR data
python extract_ocr_pairs.py

# 2. Back-translate
python back_translate.py
python clean_backtranslated.py

# 3. Rebuild splits
python prepare_training_data.py

# 4. Train MarianMT
python fine_tune.py --direction both --epochs 15

# 5. Train NLLB
python fine_tune_nllb.py --direction both --epochs 8

# 6. Rebuild index
python train.py

# 7. Deploy
python push_models_hf.py
git add -A && git commit -m "Retrain" && git push
```

### Option 3: Using improve_and_retrain.py

```bash
# Full pipeline (legacy script)
python improve_and_retrain.py

# With options
python improve_and_retrain.py --skip-ocr
python improve_and_retrain.py --skip-data
python improve_and_retrain.py --skip-train
```

## Verification

### Training Data Audit

Before training, run the full data audit to verify quality and grammar coverage:

```bash
python _audit.py
```

`_audit.py` checks:
- **Quality**: double-tagged pairs, source==target rows, repeated word runs, short/empty rows, exact duplicates
- **Orthographic rules**: R/L rule violations, nasal assimilation violations, ni→nu prefix violations, apostrophe normalisation violations
- **Grammar rule coverage**: verifies every OCR chapter is represented in the corpus — Ch.2 (sound change), Ch.4 (numbers/particles), Ch.7 (noun classes), Ch.9/10 (noun formation), Ch.12 (derivative verbs), Ch.13 (moods/tenses), Ch.15 (conditional), Ch.16 (comparison), Ch.17 (particles), plus cultural data and orthography examples

Prints `OK`/`MISSING` per category with match counts. Exits with either:
- `DATA IS CLEAN AND QUALIFIED FOR TRAINING`
- `ISSUES REMAIN - DO NOT TRAIN YET`

### Grammar Integration Check

Two scripts are available for verification:

```bash
# Lightweight standalone check (no model loading, no training deps)
python verify_implementation.py

# Full pre-flight check integrated into the pipeline
python full_pipeline.py --verify-only
```

`verify_implementation.py` checks:
- Grammar rules files exist (`language_rules.py`, `language_rules_ocr_extension.py`)
- Core and OCR-derived rules import correctly (NOUN_CLASSES, TENSES, IMPERATIVE_TENSES, CAUSATIVE_FORMATION, COMPARISON_POSITIVE, GENITIVE_PARTICLES)
- Full grammar context available (>1000 chars) and contains expected sections
- R/L rule applies correctly (`olulimi` → `orurimi`, `okulya` preserved)
- Noun class detection works (`omuntu` → class 1, `abantu` → class 2)
- `/chat` endpoint uses `get_full_grammar_context()` in `main.py`
- `/language-rules` endpoint exposes all OCR-derived rule sets
- All pipeline scripts exist
- OCR data and cleaned data directories are present
- All 4 model directories exist

`full_pipeline.py --verify-only` additionally checks endpoint configuration in detail before running the pipeline.

### Model Evaluation

```bash
# Sequential single-GPU (auto-selects GPU with most free memory)
python run_eval.py

# Parallel across 2 GPUs
python eval_all_parallel.py

# MarianMT only (CPU, leaves GPUs free)
python eval_marian.py
```

Metrics:
- BLEU score
- Token-level F1
- Exact match rate
- Inference speed (ms/sample)

## Grammar Rules Usage

### In Python Code

```python
from language_rules import (
    get_full_grammar_context,
    NOUN_CLASSES,
    TENSES,
    IMPERATIVE_TENSES,
    CAUSATIVE_FORMATION,
    COMPARISON_POSITIVE,
    GENITIVE_PARTICLES,
    # Executable transformation functions
    apply_rl_rule,
    apply_rl_rule_to_text,
    apply_nasal_assimilation,
    apply_ni_prefix_change,
    apply_y_insertion,
    apply_consonant_suffix_change,
    apply_conversive_suffix,
    apply_reflexive_imperative,
    apply_concordial_agreement,
    apply_causative,
    apply_passive,
    apply_neuter,
    apply_reciprocal,
    build_plural,
    build_verb_form,
    build_ordinal,
    apply_class9_nasal_prefix,
    get_noun_class,
    get_adjective_concord,
    get_demonstrative,
    get_numeral_concord,
)

# Get complete grammar context for LLM prompts
context = get_full_grammar_context()

# Apply R/L rule (single word or full sentence)
corrected = apply_rl_rule("olulimi")          # → "orulimi"
corrected = apply_rl_rule_to_text("olulimi olunene")  # → "orulimi orunene"

# Detect noun class
classes = get_noun_class("omuntu")  # → [1]

# Build verb forms
form = build_verb_form("genda", "1sg", "present_imperfect")  # → "nigenda"
form = build_verb_form("genda", "1sg", "present_imperfect", negative=True)  # → "tinigenda"

# Derivative verb forms
caus = apply_causative("genda")    # → "gendya"
pasv = apply_passive("gaba")       # → "gabwa"
neut = apply_neuter("sobora")      # → "soboka"
recp = apply_reciprocal("gonza")   # → "gonzangana"
conv = apply_conversive_suffix("bamba")  # → "bambura"

# Concordial agreement
adj  = apply_concordial_agreement("-rungi", 1)  # → "omurungi"
plur = build_plural("omuntu")                   # → "abantu"
ord1 = build_ordinal(1, 1)                      # → "gwa okubanza"
ord2 = build_ordinal(2, 5)                      # → "lya kabiri"

# Sound change rules
assm = apply_nasal_assimilation("omboga")  # → "emboga"
refl = apply_reflexive_imperative("okwesereka")  # → "weesereke"
```

### Via API

```bash
# Get all grammar rules
curl http://localhost:8000/language-rules

# Apply a grammar rule programmatically
curl -X POST http://localhost:8000/language-rules/apply \
  -H "Content-Type: application/json" \
  -d '{"rule": "rl_rule", "text": "olulimi olunene"}'
# → {"result": "orulimi orunene"}

curl -X POST http://localhost:8000/language-rules/apply \
  -H "Content-Type: application/json" \
  -d '{"rule": "build_verb", "verb_stem": "genda", "person": "1sg", "tense": "present_imperfect"}'
# → {"result": "nigenda"}

curl -X POST http://localhost:8000/language-rules/apply \
  -H "Content-Type: application/json" \
  -d '{"rule": "ordinal", "n": 2, "noun_class": 5}'
# → {"result": "lya kabiri"}

# Chat with grammar context
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do you say hello in Runyoro?"}'
```

## File Structure

```
backend/
├── language_rules.py              # Core + OCR grammar rules
├── language_rules_ocr_extension.py # Extended OCR rules (Ch 2,4,7,9,10,12,13)
├── extract_ocr_pairs.py           # OCR data extraction
├── back_translate.py              # Back-translation augmentation
├── clean_backtranslated.py        # Quality filtering
├── prepare_training_data.py       # Training split builder
├── fine_tune.py                   # MarianMT training
├── fine_tune_nllb.py              # NLLB training
├── train.py                       # Semantic search index builder
├── improve_and_retrain.py         # Legacy full pipeline
├── full_pipeline.py               # New orchestrator with verification
├── main.py                        # FastAPI server
├── translate.py                   # Translation logic
├── chatbot.py                     # Chat assistant
└── data/
    ├── OCR/combined/all_ocr_combined.json  # Source OCR data
    ├── cleaned/                            # Cleaned datasets
    │   ├── english_nyoro_clean.csv
    │   ├── word_entries_clean.csv
    │   ├── ocr_pairs_extracted.csv
    │   └── ocr_glosses_extracted.csv
    └── training/                           # Training splits
        ├── train.csv
        ├── val.csv
        └── test.csv
```

## Environment Variables

```bash
# HuggingFace token (for model upload)
export HF_TOKEN=your_token_here

# Transformers offline mode (optional)
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
```

## Hardware Requirements

**Minimum**:
- 16GB RAM
- 8GB VRAM (single GPU)
- 50GB disk space

**Recommended**:
- 32GB RAM
- 2x 24GB VRAM (dual GPU for DDP)
- 100GB disk space (for LFS)

**Training Time** (on 2x RTX 3090):
- MarianMT: ~2h per direction (15 epochs)
- NLLB: ~4h per direction (8 epochs)
- Total: ~12h for full pipeline

## Troubleshooting

### Grammar Rules Not Loading

```bash
# Check if extension module exists
ls backend/language_rules_ocr_extension.py

# Verify import
python -c "from language_rules import get_full_grammar_context; print(len(get_full_grammar_context()))"
```

### NLLB DDP Fails

- Check gloo backend is available: `python -c "import torch.distributed as dist; print(dist.is_gloo_available())"`
- Verify 2+ GPUs: `python -c "import torch; print(torch.cuda.device_count())"`
- Falls back to single-GPU automatically

### HuggingFace Upload Fails

- Check token: `echo $HF_TOKEN`
- Verify write access to repos
- Check network connection

### Git LFS Push Fails

- Check LFS is installed: `git lfs version`
- Verify LFS tracking: `git lfs track "*.bin" "*.pkl"`
- Check credentials: `git config credential.helper`

## Next Steps

After running the pipeline:

1. **Evaluate models**: `python run_eval.py`
2. **Start API**: `uvicorn main:app --reload --port 8000`
3. **Start frontend**: `cd ../frontend && npm run dev`
4. **Test chat**: Visit http://localhost:3002 and try the chat feature
5. **Verify grammar**: Check /language-rules endpoint returns all rules

## References

- Grammar source: A Grammar of Runyoro-Rutooro (Chapters 2, 4, 7, 9, 10, 12, 13, 15, 16, 17)
- Orthography: Runyoro-Rutooro Orthography Guide (Ministry of Gender, Uganda, 1995)
- OCR data: `data/OCR/combined/all_ocr_combined.json`
- Models: https://huggingface.co/keithtwesigye
- Code: https://github.com/chriskagenda/TRANSLATOR
