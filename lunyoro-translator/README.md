# AI Stick — Runyoro / Rutooro Translator

**Version 2.8** - Qwen Refinement for `/translate-reverse`

A neural machine translation system for Runyoro-Rutooro ↔ English with:
- Fine-tuned MarianMT + NLLB-200 models
- Semantic search fallback with 80k+ sentence pairs
- Grammar rule post-processing (R/L rule, nasal assimilation, etc.)
- Human feedback loop for continuous improvement
- Chat assistant powered by Qwen 2.5 7B

**Live Demo:** [frontend-six-phi-25.vercel.app](https://frontend-six-phi-25.vercel.app)  
**API:** [keithtwesigye-runyoro-translator-api.hf.space](https://keithtwesigye-runyoro-translator-api.hf.space)

---

## Features

### Translation
- **Dual neural models:** NLLB-200 (primary for both directions) + MarianMT (fallback/comparison)
- **HuggingFace Hub integration:** Models loaded automatically from HF Hub on first use and cached locally
- **Context-aware:** Uses previous sentence for better coherence
- **Grammar rules:** Automatic R/L rule, apostrophe elision, nasal assimilation, Grammar Rules 4 (copula, kinship, enumeratives, ka particle, demonstratives, dara presentative, verb-noun derivation)
- **Translation chain (en→lun):** Selective RAG (high-confidence corpus match) → Neural MT (NLLB + MarianMT) → Semantic search → Dictionary lookup
- **Spellcheck:** Real-time Lunyoro spellcheck with suggestions

### Runyoro-Rutooro Writing Editor (`RunyoroEditor.tsx`)
- **Contenteditable canvas:** Rich-text editor with caret preservation across spellcheck re-renders
- **Real-time spellcheck:** Wavy underlines on misspelled words; hover tooltip with suggestions or ignore option; debounced 800ms after typing stops
- **Grammar hints panel:** Six collapsible reference cards covering R/L Rule, Noun Classes, Verb Infinitives, Tense Markers, Apostrophe elision, and Long Vowels
- **Formatting toolbar:** Bold, italic, underline, ordered/unordered lists, and left/center/right alignment via `execCommand`
- **AI grammar review:** Sends editor text to `/chat` endpoint for Qwen-powered grammar feedback
- **Save to file:** Downloads editor content as a `.txt` file with a datestamped filename
- **Word count:** Live word count displayed in the editor footer

### Chat Assistant
- **LLM-powered:** Qwen 2.5 7B via HuggingFace Router
- **Domain-aware:** Sector-specific vocabulary across 8 domains (Daily Life, Storytelling, Spirituality, Agriculture, Education, Culture, Health, All Sectors)
- **Bilingual output:** Replies in English + Lunyoro (MarianMT + NLLB side-by-side)
- **Grammar context:** First 3000 chars of Runyoro-Rutooro grammar rules injected into system prompt for richer rule coverage
- **Detailed replies:** System prompt instructs the model to reply in plain English prose, 2–4 well-explained paragraphs, with the grammar rule behind every concept explained
- **Corpus-grounded:** Up to 2 relevant sentence pairs from the training corpus are retrieved and included as examples
- **Conversation mode:** Type in Runyoro-Rutooro for immersive practice
- **Multi-line input:** Textarea with mic button for voice input (UI placeholder)

### Human Feedback
- **Primary feedback:** Simple Yes/No rating for translation quality
- **Multi-select error categorization:** Select multiple issue types (grammar, spelling, context, vocabulary, other)
- **Model comparison:** 2x2 grid interface to choose between MarianMT, NLLB-200, both correct, or both wrong
- **Model preference learning:** When a user selects a preferred model, the translation immediately updates to show that model's output, and future translations automatically use that model as primary
- **Corrections:** Submit better translations with optional error details
- **Separate feedback flows:** Primary quality feedback and model comparison feedback tracked independently
- **Continuous learning:** Approved pairs feed back into training

---

## Quick Start

### Frontend (Next.js)
```bash
cd lunyoro-translator/frontend
npm install
npm run dev
# → http://localhost:3002
```

### Backend (FastAPI)
```bash
cd lunyoro-translator/backend
pip install -r requirements.txt
# Models are automatically downloaded from HuggingFace Hub on first use (~2GB)
# Or pre-download with: python download_models.py
python main.py
# → http://localhost:8000
```

---

## Model Improvement Pipeline

See **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** for full details.

### 1. Build Translation Index
```bash
python backend/build_index.py
# Builds semantic search index from dictionary data + training corpus
# Loads word_entries_clean.csv and rutooro_dictionary_clean.csv (dictionary entries)
# Loads data/training/train.csv (sentence pairs for semantic search)
# Encodes English sentences with all-MiniLM-L6-v2 into dense embeddings
# Creates model/translation_index.pkl containing:
#   - dictionary entries
#   - english_sentences / lunyoro_sentences arrays
#   - embeddings matrix for cosine-similarity retrieval
```

### 2. Clean Training Data
```bash
python backend/clean_training_data.py
# Removes 13,899 noisy rows (domain tags, OCR garbage, duplicates)
# 80,733 → 66,834 clean pairs
```

### 2b. Clean OCR Pairs
```bash
python backend/clean_ocr_pairs.py
# Removes noisy/truncated rows from data/cleaned/ocr_pairs_extracted.csv
# Filters out rows where:
#   - English side starts with a lowercase letter (truncated left margin)
#   - English side starts with truncation punctuation (', ", >, \, etc.)
#   - Either side is empty or < 4 characters
#   - English side contains grammar meta-notation (e.g., "e.g.", "formative", "tense prefix")
#   - English side matches a page-header pattern (e.g. "Conditions expressed by verbs 279")
#   - Either side contains LaTeX/notation artifacts (\varphi, c/.14, pl. nil, n. cl)
#   - Lunyoro side starts with a grammar label (e.g. "ru ya:", "aba:", "na:")
#   - Lunyoro side starts lowercase and contains an inline colon label with a capitalised continuation
#     (e.g. "okuruga ... okuhikya: From morning till evening")
#   - Lunyoro side matches a short label pattern like "in'ekindi:" (up to 15 chars ending in colon)
# Backs up the original file to ocr_pairs_extracted.csv.bak before overwriting
```

### 2c. Clean Newly Added Training Pairs
```bash
python backend/clean_new_training_data.py
# Cleans train.csv and val.csv after any data merge step:
#   1. Fixes malformed/stacked domain tags (e.g. [AGICAL], [REERAL] → stripped or corrected)
#   2. Removes pairs where either side is < 3 characters
#   3. Removes identical pairs (English == Lunyoro after lowercasing)
#   4. Removes English-passthrough pairs in the Lunyoro column
#      (detected when > 50% of words are common English function words)
#   5. Removes very long pairs (> 500 characters on either side)
#   6. Removes pairs containing HTML/entity artifacts (<tag>, &amp;, etc.)
#   7. Drops rows with NaN or empty values
# Backs up both files (.bak2) before overwriting.
# Run this after merge_untrained_data.py or any step that appends new pairs.
```

### 2d. Merge Untrained Data
```bash
python backend/merge_untrained_data.py
# Finds all clean data not yet in train.csv / val.csv and merges it in.
# Sources scanned:
#   - data/cleaned/*.csv          (any file with english + lunyoro columns)
#   - data/raw/proverbs_pairs.csv
#   - data/raw/english_nyoro.csv / english_nyoro_root.csv
#   - feedback/approved_pairs.csv (human-approved pairs)
# Deduplicates against existing train + val keys before adding.
# Splits new pairs 90/10 into train.csv / val.csv.
# Backs up both files (.bak) before writing.
# Prints a per-source breakdown of new pairs added.
# Run after any data cleaning step to ensure nothing is left out of training.
```

### 3. Back-Translation (Data Augmentation)
```bash
python backend/back_translate.py --max 5000 --bleu-threshold 0.25
# Generates 2,000-3,000 synthetic pairs via round-trip translation
python backend/merge_back_translated.py
```

### 4. Retrain Tokenizer (Better OOV Handling)
```bash
python backend/retrain_tokenizer.py --vocab-size 65000 --direction both
# Expands vocab from 64k → 65k tokens with subword regularization
```

### 5. Fine-Tune Models
```bash
python backend/train_marian.py --direction both --epochs 5 --resize-embeddings
# Features:
#   - Subword regularization (SPM sampling, alpha=0.1)
#   - Longer context window (prepends previous sentence)
#   - Mixed precision (fp16) on GPU
#   - Multi-GPU training: automatically uses all available GPUs via DataParallel
#   - BLEU-based checkpoint selection
#   - Weighted sampler: gr4 pairs get 4x weight, back-translated pairs 2x
```

### 6. Fine-Tune NLLB-200 Models
```bash
python backend/train_nllb.py                          # both directions, 5 epochs
python backend/train_nllb.py --direction en2lun       # one direction only
python backend/train_nllb.py --epochs 5 --lr 2e-5
python backend/train_nllb.py --fp16                   # mixed precision (GPU)
python backend/train_nllb.py --new-only               # train only on new (untrained) pairs
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--direction` | `both` | `en2lun`, `lun2en`, or `both` |
| `--epochs` | `5` | Number of training epochs |
| `--batch-size` | `8` | Keep low (8–16) — NLLB is large |
| `--lr` | `1e-5` | Learning rate (lower than MarianMT) |
| `--max-length` | `256` | Max token length |
| `--fp16` / `--no-fp16` | enabled | Mixed precision (GPU only) |
| `--min-lun-words` | `3` | (`lun2en` only) Filter out pairs where the Lunyoro side has fewer than N words. Removes single-word dictionary entries that hurt lun→en BLEU. Set to `0` to disable. |
| `--new-only` | `false` | Train only on pairs not yet seen by the model (`data/training/new_only_train.csv` / `new_only_val.csv`). Falls back to the full `train.csv` / `val.csv` if those files don't exist. Note: `train_marian.py --new-only` always validates on the full `val.csv` regardless of this flag. |

**Notes:**
- Always fine-tunes from the existing local checkpoint in `model/nllb_{direction}/` — never trains from scratch
- Best checkpoint (by validation BLEU) is saved to `model/nllb_{direction}/best_checkpoint/` and promoted to the model root at the end
- Requires `model/nllb_en2lun/` and/or `model/nllb_lun2en/` to exist — run `python download_models.py` first if needed
- Uses a weighted sampler: Grammar Rules 4 and Grammar Rules 5 pairs get 4× weight, back-translated pairs 2×, all others 1× (same strategy as `train_marian.py`); seed vocabulary CSVs (medical, education, daily life, low-frequency, agriculture) are also loaded and deduplicated against the main training set
- Multi-GPU training: automatically uses all available GPUs via `DataParallel` when more than one GPU is detected (prints device names at startup)
- **lun→en data fixes (applied automatically):** Before training the `lun2en` direction, two preprocessing steps run in sequence: (1) domain tags (e.g. `[MEDICAL]`, `[GENERAL]`) are stripped from the English target column — these tags are en→lun artefacts that corrupt lun→en targets; (2) pairs where the Lunyoro source has fewer than `--min-lun-words` words are dropped, removing single-word dictionary entries that degrade sentence-level BLEU

### 6b. Augment Data + Full Training Pipeline (CI/CD)
```bash
python backend/augment_and_train.py                  # full pipeline (augment → train → push)
python backend/augment_and_train.py --augment-only   # only generate + clean augmented data
python backend/augment_and_train.py --train-only     # skip augmentation, just train
python backend/augment_and_train.py --no-push        # skip all pushes
python backend/augment_and_train.py --epochs 3       # set training epochs
python backend/augment_and_train.py --marian-only    # skip NLLB
python backend/augment_and_train.py --nllb-only      # skip MarianMT
```

End-to-end CI/CD pipeline that combines data augmentation with training and deployment:

1. **Augment** — generates new training pairs from the domain dictionary POS data:
   - POS-tagged pairs (`[NOUN]` / `[VERB]` / `[ADJ]` prefixed English entries)
   - Plural augmentation using noun class rules (omu-→aba-, eki-→ebi-, eri-→ama-, etc.); English side strips leading articles (a/an/the) and applies correct suffix rules: `-s`/`-x`/`-z`/`-sh`/`-ch` endings → `+es`, consonant+`y` endings → `-y+ies`, all others → `+s`
   - Verb conjugation pairs (present 1sg/3sg, perfect 1sg, imperative, negative present)
2. **Clean** — applies the same orthographic pipeline as all other data (nasal assimilation, R/L rule)
3. **Merge** — deduplicates and appends new pairs into `train.csv` / `val.csv`
4. **Train** — fine-tunes MarianMT en2lun + lun2en, then NLLB en2lun + lun2en
5. **Push** — uploads models to HuggingFace Hub and backend to HF Space
6. **GitHub** — pushes code to both repos

**Noun class plural rules supported:**

| Singular prefix | Plural prefix | Example |
|-----------------|---------------|---------|
| `omu-` / `omw-` | `aba-` / `ab-` | omuntu → abantu |
| `eki-` / `eky-` | `ebi-` / `eby-` | ekitabu → ebitabu |
| `eri-` / `ery-` | `ama-` | eriiso → amaiso |
| `aka-` / `akw-` | `utu-` / `utw-` | akana → utunana |
| `oru-` / `orw-` | `en-` / `em-` | orulimi → endimi |

**Verb conjugation pairs generated per infinitive:**
- Present 1sg: `n` + stem (I do X)
- Present 3sg: `a` + stem (he/she does X)
- Perfect 1sg: `n` + mutated root + `ire` (I have done X)
- Imperative: stem alone (do X!)
- Negative present: `tin` + stem (I don't do X)

### 6c. Run Full Training Pipeline (MarianMT + NLLB)
```bash
python backend/train_all.py                          # 3 epochs each, both directions
python backend/train_all.py --epochs 5               # 5 epochs each
python backend/train_all.py --marian-only            # skip NLLB
python backend/train_all.py --nllb-only              # skip MarianMT
python backend/train_all.py --no-push                # skip HuggingFace push
python backend/train_all.py --direction en2lun       # one direction only
```

Runs `train_marian.py` and `train_nllb.py` sequentially, then pushes both models to HuggingFace automatically. Reads `HF_TOKEN` from the environment or from `backend/.env`.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--epochs` | `3` | Number of training epochs for both models |
| `--batch-marian` | `64` | Batch size for MarianMT |
| `--batch-nllb` | `8` | Batch size for NLLB-200 |
| `--direction` | `both` | `en2lun`, `lun2en`, or `both` |
| `--marian-only` | — | Skip NLLB fine-tuning |
| `--nllb-only` | — | Skip MarianMT fine-tuning |
| `--no-push` | — | Skip HuggingFace push after training |

**Notes:**
- HF push is skipped automatically if any training step fails
- If `HF_TOKEN` is not set and `--no-push` is not passed, a warning is printed and the push is skipped silently
- Exit code is non-zero if any step fails

### 6d. Run Full Training Pipeline with New-Only Data + Full Deploy
```bash
python backend/run_full_training.py                                  # full pipeline (5 epochs each)
python backend/run_full_training.py --skip-marian                    # NLLB only, then MarianMT retrain
python backend/run_full_training.py --skip-nllb                      # MarianMT only
python backend/run_full_training.py --no-push                        # skip all pushes after training
python backend/run_full_training.py --retrain-marian-only            # just run the MarianMT retrain step
python backend/run_full_training.py --marian-en2lun-epochs 3         # custom epoch count for MarianMT en→lun
python backend/run_full_training.py --marian-lun2en-epochs 3         # custom epoch count for MarianMT lun→en
python backend/run_full_training.py --nllb-en2lun-epochs 8           # custom epoch count for NLLB en→lun
python backend/run_full_training.py --nllb-lun2en-epochs 8           # custom epoch count for NLLB lun→en
python backend/run_full_training.py --retrain-en2lun-epochs 3        # epochs for MarianMT retrain en→lun
python backend/run_full_training.py --retrain-lun2en-epochs 3        # epochs for MarianMT retrain lun→en
```

A focused alternative to `train_all.py` that trains on **new-only data** (pairs not yet seen by the models) and handles the full deploy chain in one command: HuggingFace Hub push → HF Space push → git push to both repos.

Each direction is trained as a separate step, so you can tune epoch counts independently for en→lun and lun→en without affecting the other direction.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--marian-en2lun-epochs` | `5` | Training epochs for initial MarianMT English → Lunyoro (new-only data) |
| `--marian-lun2en-epochs` | `5` | Training epochs for initial MarianMT Lunyoro → English (new-only data) |
| `--nllb-en2lun-epochs` | `5` | Training epochs for NLLB-200 English → Lunyoro |
| `--nllb-lun2en-epochs` | `5` | Training epochs for NLLB-200 Lunyoro → English |
| `--retrain-en2lun-epochs` | `5` | Epochs for MarianMT retrain en→lun (validates on full val set) |
| `--retrain-lun2en-epochs` | `5` | Epochs for MarianMT retrain lun→en (validates on full val set) |
| `--skip-marian` | — | Skip initial MarianMT fine-tuning (retrain step still runs after NLLB) |
| `--skip-nllb` | — | Skip both NLLB fine-tuning steps |
| `--no-push` | — | Skip all post-training pushes (HF Hub, HF Space, git) |
| `--retrain-marian-only` | — | Skip all initial training; only run the MarianMT retrain step |

**Pipeline steps (in order):**
1. **MarianMT en2lun** — `train_marian.py --direction en2lun --new-only` *(skipped with `--skip-marian` or `--retrain-marian-only`)*
2. **MarianMT lun2en** — `train_marian.py --direction lun2en --new-only` *(skipped with `--skip-marian` or `--retrain-marian-only`)*
3. **NLLB en2lun** — `train_nllb.py --direction en2lun --new-only` *(skipped with `--skip-nllb` or `--retrain-marian-only`)*
4. **NLLB lun2en** — `train_nllb.py --direction lun2en --new-only` *(skipped with `--skip-nllb` or `--retrain-marian-only`)*
5. **MarianMT retrain en2lun** — `train_marian.py --direction en2lun --new-only` on new-only data, validated against the **full `val.csv`** *(always runs)*
6. **MarianMT retrain lun2en** — same as above for lun→en *(always runs)*
7. **HF Hub push** — `push_models.py --all`
8. **HF Space push** — `push_to_hf_space.py`
9. **Git push** — stages training CSVs + pipeline scripts (including `language_rules_gr4.py`, `language_rules_gr5.py`, `translate.py`, `generate_grammar_pairs.py`), commits with a datestamped message, and pushes to both `origin` and `k227` remotes

**Notes:**
- Steps 7–9 are skipped automatically if any training step fails
- `--new-only` trains only on `data/training/new_only_train.csv` (generated by `merge_untrained_data.py`); falls back to the full `train.csv` if that file doesn't exist. **MarianMT always validates on the full `val.csv`** regardless of `--new-only`, so BLEU scores are comparable across runs. NLLB also falls back to `val.csv` if `new_only_val.csv` doesn't exist.
- The MarianMT retrain step (steps 5–6) **always runs** unless `--skip-nllb` is also set; use `--retrain-marian-only` to run only those steps without any initial training.
- Each step prints a timestamped start/end line for easy progress tracking
- Exit code is non-zero if any training step fails
- Use `train_all.py` instead if you want to train on the full dataset or need per-batch-size control

### 7. Grammar Rules 4 Full Pipeline (Automated)
```bash
python backend/gr4_full_pipeline.py
# Complete automated pipeline for Grammar Rules 4 training data:
#   1. Extract clean pairs from language_rules_gr4.py
#   2. Back-translate for data augmentation
#   3. Clean and deduplicate
#   4. Merge into training data
#   5. Rebuild semantic index
#   6. Fine-tune MarianMT models (both directions, 5 epochs)
#   7. Fine-tune NLLB-200 models (both directions, 5 epochs)
# Estimated time: 1-3 hours (depending on hardware)
```

**Features:**
- Fully automated end-to-end pipeline (runs non-interactively, no confirmation prompt)
- Error handling with recovery options
- Summary report of completed/failed steps
- Orchestrates 7 pipeline steps sequentially

**Manual alternative** (run steps individually):
```bash
# Step 1: Extract GR4 pairs
python backend/extract_gr4_training_pairs.py

# Step 2: Back-translate for augmentation
python backend/back_translate.py --input data/cleaned/gr4_pairs.csv --output data/training/gr4_back_translated.csv

# Step 3: Merge back-translations
python backend/merge_back_translated.py --source data/training/gr4_back_translated.csv

# Step 4: Clean training data
python backend/clean_training_data.py

# Step 5: Rebuild semantic index
python backend/build_index.py

# Step 6: Fine-tune MarianMT
python backend/train_marian.py --direction both --epochs 5 --batch-size 32

# Step 7: Fine-tune NLLB-200
python backend/train_nllb.py --direction both --epochs 5 --batch-size 8
```

### 7b. Extract Grammar Rules 5 Training Pairs
```bash
python backend/extract_gr5_training_pairs.py
# Extracts clean English <-> Runyoro-Rutooro training pairs from grammar rules 5.docx
# (Chapters 5, 6, 7: locatives, sentences, noun classes 1a/2a/9a/10a)
# Writes pairs to data/cleaned/gr5_pairs.csv
# Merges 90% into train.csv and 10% into val.csv (skips duplicates)
```

**Coverage (~300 pairs across):**
- Chapter 5: locative agreement, locative demonstratives, genitive locatives, locative possessives, adverbial suffixes (-mu/-ho/-yo), concord prefix ha-, hamu/handi, ho + enumerative roots, dara + locative, copula ni- + locatives
- Chapter 6: sentence types, reversed-object sentences
- Chapter 7: noun class examples (classes 1/2/1a/2a/9/9a/10a), colour names, augmentative/pejorative forms, negative nouns, class 9 professional nouns, twin names, kinship terms

### 7c. Generate Grammar Training Pairs (Bulk)
```bash
python backend/generate_grammar_pairs.py
# Generates 8,000+ grammar training pairs from the rule tables in
# language_rules_gr4.py and language_rules_gr5.py.
# Output: data/cleaned/gr_grammar_pairs.csv  (english, lunyoro columns)
#
# On completion, prints:
#   - Total pair count
#   - Per-category breakdown (LOCATIVE, COPULA, KINSHIP, VERB_CONJ, etc.)
#   - Suggested next steps
```

**Coverage:**
- Locative constructions (all prefixes × nouns, + 15 sentence examples)
- Locative demonstratives (munu/muli/hanu/hali/kunu/kuli, + copula forms)
- Adverbial suffixes (-mu/-ho/-yo in sentence context)
- Locative possessives (omwange/owaawe/omwaitu etc., all 6 persons × omwa-/owa- types, + sentence examples)
- Enumerative pronouns (exclusive -enka/-onka, inclusive -ena/-ona, reflexive -enyini/-onyini, dual -embi/-ombi, all persons + sentence examples)
- Copula ni- + locatives (nihanu/nuho/numwo etc.)
- Dara presentative (all persons + noun classes)
- Demonstratives near/far (all 15 classes)
- Copula ni-/n- distribution (all 15 classes)
- Ka particle (emphatic + permissive, + sentence examples)
- Kinship terms (father/mother/grandparents/other relations × all persons, + sentence examples)
- Fractions and distributives
- Verb-to-noun derivation (agent/action/method)
- Colour names (all colours in sentence context)
- Negative nouns (omu-ta- pattern)
- Class 9 professional nouns
- Objectival concord sentences
- Verb conjugation tables (all 6 persons × tenses)

All pairs are tagged with a `[GRAMMAR]` prefix on the English side, NFC-normalised, and deduplicated before writing. After running, merge the output into training data and retrain:

```bash
python backend/merge_untrained_data.py
python backend/run_full_training.py --marian-epochs 5 --nllb-epochs 5
```

### 8. Upload Models to HuggingFace Hub
```bash
# Upload all models
python backend/upload_models_to_hf.py --token YOUR_HF_TOKEN

# Upload specific models
python backend/upload_models_to_hf.py --token YOUR_HF_TOKEN --models en2lun lun2en

# Use custom username/organization
python backend/upload_models_to_hf.py --token YOUR_HF_TOKEN --username your-username

# Available models: en2lun, lun2en, nllb_en2lun, nllb_lun2en, sem_model
```

**Features:**
- Uploads models directly to HuggingFace Hub (no Git LFS needed)
- Creates repositories automatically if they don't exist
- Supports selective model upload
- Configurable username/organization

### 9. Retrain from Human Feedback
```bash
python backend/retrain_from_feedback.py --epochs 5 --push
# Exports thumbs-up pairs → merges into train.csv → fine-tunes → pushes to HF
```

### 10. Automated Retraining (Background Service)
```bash
# Check current feedback stats
python backend/auto_retrain.py --stats

# Run single check (triggers retrain if threshold met)
python backend/auto_retrain.py --check

# Run as continuous monitoring service (checks every hour)
python backend/auto_retrain.py --monitor --interval 3600

# Custom threshold (overrides default of 100 new pairs)
python backend/auto_retrain.py --monitor --threshold 200
python backend/auto_retrain.py --check --threshold 50
```

### 11. Check Backend Syntax
```bash
python check_syntax.py
# Runs a quick AST parse over the core backend Python files to catch syntax
# errors before pushing or retraining.  Run from the project root
# (TRANSLATOR/).
#
# Files checked:
#   train_marian.py, train_nllb.py, back_translate_lun2en.py,
#   knowledge_graph.py, main.py, translate.py, eval_bleu.py,
#   run_full_training.py, run_k227_pipeline.py,
#   language_rules_gr4.py, language_rules_gr5.py
#
# Output:
#   OK  <filename>   — file parsed without errors
#   ERR <filename>: <SyntaxError message>  — file has a syntax error
#   "All OK" or "ERRORS FOUND - fix before pushing" summary line
```

### 11c. Inspect Benchmark Scores
```bash
python show_benchmarks.py
# Prints a formatted view of both benchmark score files:
#   - benchmark_scores.csv  — tabular dump of all benchmark entries
#   - benchmark_scores.json — per-entry breakdown showing:
#       Source text, domain, SQS score + band, and all eight
#       sub-scores (MNG, GRM, TNS, VCB, ORT, CTX, FLU, CUL)
# Run from the lunyoro-translator/ root directory.
```

### 11b. Inspect Training Data Composition
```bash
python backend/check_weights.py
# Prints a breakdown of training data by source:
#   - Total pairs in train.csv
#   - Domain-tagged pairs (e.g. [MEDICAL], [EDUCATION]) and their counts
#   - Pair counts per seed vocabulary file (medical, education, daily_life, low_freq, agriculture)
#   - gr4_pairs.csv and gr5_pairs.csv counts
#   - back_translated.csv and gr4_back_translated.csv counts
#   - english_nyoro_clean.csv (main corpus) count
# Run this after any data pipeline step to verify the training set composition.
```

### 11c. Inspect Dictionary POS Coverage
```bash
python backend/check_dict_pos.py
# Audits POS (part-of-speech) data in the cleaned dictionary and training set:
#   - Column listing and total entry count for runyoro_domain_dictionary_clean.csv
#   - POS value distribution (top 20 values, entries with/without POS data)
#   - 15 random sample entries that have POS annotations
#   - Count of domain-tagged pairs in train.csv (e.g. [MEDICAL], [EDUCATION])
#   - 10 random sample domain-tagged pairs (English + Lunyoro)
#   - Count of pairs with plural indicators (aba-/ebi-/emi-/ama-/en-/em-/utu-/zaa- prefixes)
#   - Count of POS-tagged training pairs ([NOUN]/[VERB]/[ADJ] in English column)
# Useful for verifying that POS and plural data from the domain dictionary
# were correctly propagated into the training set.
```

### 11d. Inspect lun→en Training Data Quality
```bash
python backend/check_lun2en_data.py
# Analyses the Lunyoro-side word count distribution across train.csv + val.csv
# to diagnose why the lun→en model may underperform:
#   - Word count statistics (min, max, mean, percentiles) for the Lunyoro column
#   - Pair counts split into three buckets:
#       lun_words <= 2  — single-word / two-word dictionary entries (hurt lun→en)
#       lun_words 3–4   — short phrases
#       lun_words >= 5  — full sentences (the useful signal for lun→en)
#   - Total pair count
#   - Count of [DOMAIN]-tagged pairs (en→lun format only; useless as lun→en source)
#   - Percentage of sentence-level pairs (lun_words >= 5) vs total
# Use this to decide whether to filter short pairs before lun→en training
# (e.g. pass --min-lun-words 3 to train_marian.py / train_nllb.py).
```

### 11e. Inspect Back-Translation Candidates
```bash
python backend/check_bt_candidates.py
# Analyses train.csv + val.csv to identify which pairs are useful candidates
# for back-translation augmentation and which are redundant:
#   - Tagged pairs (en→lun-only format, e.g. [MEDICAL] prefix):
#       The lun→en model never saw these as source — back-translating their
#       English produces genuinely new lun→en training data.
#   - Short dict pairs (lun_words <= 2):
#       Filtered out of lun→en training by --min-lun-words; their English side
#       is valid but the Runyoro side is too short to be useful as source.
#   - Good sentence pairs (lun_words >= 3, no tag):
#       Already in lun→en training — back-translating these is redundant.
#   - Back-translation candidates (useful):
#       Union of tagged pairs + short dict pairs where en_words >= 5,
#       so the back-translation produces a real sentence rather than a fragment.
#   - Remaining candidates after subtracting already-back-translated pairs (~10,928).
# Use this to gauge how many new lun→en pairs a back-translation run can yield
# before deciding whether to run back_translate.py again.
```

**Features:**
- Monitors `feedback.jsonl` for approved pairs
- Auto-cleans and validates feedback (length, repetition, language detection)
- Triggers retraining when 100+ new clean pairs collected (configurable via `--threshold`)
- Runs as background service or scheduled task
- Logs to `auto_retrain.log`

**Expected improvements:** +5-10 BLEU after full pipeline

### 11f. Analyze Back-Translation Coverage Across All Sources
```bash
python backend/analyze_bt_coverage.py
# Scans every CSV in data/cleaned/ and the training set to identify which
# English sentences have NOT been back-translated yet.
#
# Reports:
#   - Already back-translated: count from back_translated_lun2en.csv
#   - Per-source breakdown: total rows, BT-able (en_words >= 5, not in training),
#     already done, and remaining — printed as an aligned table
#   - Tagged training pairs (en2lun-only format) not yet back-translated
#   - Grand total remaining candidates
#   - Top 10 sources by remaining candidate count
#
# Output:
#   data/cleaned/bt_remaining_candidates.csv
#     Columns: source (filename), english (sentence)
#     Contains all remaining candidates, deduplicated.
#
# Suggested next step printed at the end:
#   python back_translate_lun2en.py --max-sentences N --merge
```

**When to run:**
- Before a back-translation run to gauge how many new lun→en pairs are available
- After `merge_untrained_data.py` to see which newly merged sources still need back-translation
- To prioritise which source files to target in the next `back_translate_lun2en.py` run

---

## Project Structure

```
lunyoro-translator/
├── backend/
│   ├── main.py                      # FastAPI server
│   ├── translate.py                 # Translation logic (MT + retrieval)
│   ├── language_rules.py            # Runyoro grammar rules (3200+ lines)
│   ├── language_rules_gr4.py        # Grammar Rules 4: copula, kinship, enumeratives, ka particle, demonstratives, dara presentative, verb-noun derivation
│   ├── language_rules_gr5.py        # Grammar Rules 5: locatives, demonstratives, noun classes 1a/2a/9a/10a, colours, augmentatives
│   ├── build_index.py               # Build semantic search index from dictionary
│   ├── clean_training_data.py       # Data cleaning script
│   ├── clean_ocr_pairs.py           # Remove noisy/truncated rows from ocr_pairs_extracted.csv
│   ├── back_translate.py            # Back-translation augmentation
│   ├── retrain_tokenizer.py         # SentencePiece retraining
│   ├── train_all.py                 # Unified pipeline: MarianMT + NLLB sequentially, then HF push
│   ├── run_full_training.py         # New-only data pipeline: MarianMT (initial) + NLLB + MarianMT retrain on full val → HF Hub + HF Space + git push; supports --retrain-marian-only to run only the retrain step
│   ├── train_marian.py              # MarianMT fine-tuning
│   ├── train_nllb.py                # NLLB-200 fine-tuning
│   ├── extract_gr4_training_pairs.py # Extract GR4 training pairs
│   ├── extract_gr5_training_pairs.py # Extract GR5 training pairs (locatives, sentences, noun classes)
│   ├── generate_grammar_pairs.py    # Generate 8,000+ grammar pairs from GR4/GR5 rule tables → data/cleaned/gr_grammar_pairs.csv
│   ├── gr4_full_pipeline.py         # Complete GR4 training pipeline (automated)
│   ├── upload_models_to_hf.py       # Upload models to HuggingFace Hub
│   ├── feedback_store.py            # Human feedback storage + auto-export
│   ├── retrain_from_feedback.py     # End-to-end feedback retraining
│   ├── auto_retrain.py              # Automated retraining service
│   ├── view_analytics.py            # View feedback analytics in terminal
│   ├── export_analytics.py          # Export analytics to Excel/CSV
│   ├── merge_untrained_data.py      # Merge all clean data not yet in train/val into training splits
│   ├── check_weights.py             # Inspect training data composition (pair counts by source)
│   ├── check_lun2en_data.py         # Analyse lun→en data quality: word-count distribution, sentence vs dict-entry ratio, [DOMAIN]-tag count
│   ├── check_bt_candidates.py       # Identify useful back-translation candidates: tagged pairs + short dict pairs with en_words >= 5
│   ├── check_dict_pos.py            # Audit POS coverage in domain dictionary and training set
│   ├── feedback/                    # Auto-exported feedback files
│   │   ├── all_feedback.csv         # Raw feedback data (auto-updated)
│   │   ├── feedback_analytics.xlsx  # Multi-sheet analytics (auto-updated)
│   │   ├── benchmark_scores.csv     # Benchmark entries with SQS scores (GitHub-synced)
│   │   └── benchmark_scores.json    # Same benchmark data in JSON (GitHub-synced)
│   ├── model/
│   │   ├── en2lun/                  # MarianMT English→Lunyoro
│   │   ├── lun2en/                  # MarianMT Lunyoro→English
│   │   ├── nllb_en2lun/             # NLLB-200 English→Lunyoro
│   │   ├── nllb_lun2en/             # NLLB-200 Lunyoro→English
│   │   └── translation_index.pkl    # Semantic search index (80k pairs)
│   └── data/
│       ├── training/
│       │   ├── train.csv            # 80k training pairs
│       │   ├── val.csv              # 4.5k validation pairs
│       │   ├── test.csv             # 4.5k test pairs
│       │   ├── new_only_train.csv   # Pairs not yet trained on (train split, generated by merge_untrained_data.py)
│       │   └── new_only_val.csv     # Pairs not yet trained on (val split, generated by merge_untrained_data.py)
│       ├── cleaned/                 # Cleaned dictionary/corpus
│       └── raw/                     # Raw seed vocabulary
├── frontend/
│   ├── components/Translator.tsx    # Main translation UI
│   ├── components/ChatPage.tsx      # Chat assistant UI
│   ├── components/RunyoroEditor.tsx # Runyoro-Rutooro writing editor (spellcheck, grammar hints, AI review, formatting)
│   ├── components/TopBar.tsx        # Top navigation bar
│   ├── components/BottomNav.tsx     # Fixed bottom navigation bar (Home, Translate, Chat, Editor)
│   └── app/                         # Next.js app router
├── TRAINING_GUIDE.md                # Model improvement guide
├── PIPELINE_GUIDE.md                # Data pipeline guide
├── show_benchmarks.py               # Print benchmark_scores.csv + .json to terminal
└── push_benchmark_files.py          # Push benchmark_scores.csv + .json to GitHub repos
```

---

## API Endpoints

### Translation
- `POST /translate` — English → Lunyoro
  - Parameters: `text` (required), `context` (optional, previous sentence for coherence), `refine` (optional bool, default `false` — when `true` and `HF_TOKEN` is set, runs a Qwen 2.5 7B pass to improve grammar, noun-class agreement, R/L rule, apostrophe elision, and kinship terms before returning the result)
- `POST /translate-reverse` — Lunyoro → English
  - Parameters: `text` (required), `context` (optional), `refine` (optional bool, default `false` — when `true` and `HF_TOKEN` is set, runs a Qwen 2.5 7B pass to improve fluency, accuracy, and natural phrasing of the English output before returning the result)
- `POST /lookup` — Dictionary word lookup
- `POST /spellcheck` — Lunyoro spellcheck

### Chat
- `POST /chat` — AI language assistant (Qwen 2.5 7B). Replies in English only, plain prose, 2–4 paragraphs. System prompt includes the first 3000 chars of grammar rules and up to 2 corpus examples retrieved by semantic similarity. Rate-limited to 5 requests per 60 seconds per IP.

### Feedback
- `POST /feedback` — Submit translation rating with optional error categorization and corrections
  - Parameters: `source_text`, `translation`, `direction`, `rating` (1/-1), `correction` (optional), `error_type` (optional - comma-separated list for multiple error types), `model_used` (optional - "marian", "nllb", "both", "none"), `refined` (optional boolean - whether AI refinement was applied to the translation)
  - **Auto-export:** Automatically exports feedback to `backend/feedback/` folder after each submission
    - `all_feedback.csv` — Complete feedback log in CSV format
    - `feedback_analytics.xlsx` — Multi-sheet Excel workbook with analytics
- `GET /feedback/stats` — Feedback statistics
- `GET /feedback/export` — Export approved (thumbs-up) pairs to `backend/feedback/approved_pairs.csv`
  - Returns: `count`, `files`, `path` to exported CSV

### Analytics
Feedback is automatically exported to `backend/feedback/` after each submission. You can also generate comprehensive reports on-demand:

```bash
# View analytics in terminal
python backend/view_analytics.py

# Export to Excel (single file with multiple sheets)
python backend/export_analytics.py

# Export to CSV files (separate files per report)
python backend/export_analytics.py --csv

# Custom output path
python backend/export_analytics.py --output reports/feedback_report.xlsx
python backend/export_analytics.py --csv --output reports/csv_export/
```

**Auto-exported files** (in `backend/feedback/`):
- `all_feedback.csv` — Raw feedback data with all fields
- `benchmark_scores.csv` — Benchmark entries with SQS scores (synced to GitHub via `push_benchmark_files_to_github()`)
- `benchmark_scores.json` — Same benchmark data in JSON format (synced to GitHub alongside the CSV)
- `feedback_analytics.xlsx` — Excel workbook with up to 6 sheets:
  - **All Feedback:** Complete feedback log with readable labels
  - **Summary:** Total feedback, approval rates, unique users
  - **Model Usage:** Usage statistics by model (MarianMT, NLLB-200, both, none)
  - **Error Types:** Breakdown of reported error categories
  - **Daily Activity:** Feedback timeline by date
  - **Refined vs Unrefined:** Approval rates comparing AI-refined translations against unrefined MT output (only present when `refined` field is available in feedback data)
- `approved_pairs.csv` — Approved (thumbs-up) translation pairs ready for retraining (exported via `/feedback/export` endpoint)

**On-demand reports** (via `export_analytics.py`):
- **Summary Statistics:** Total feedback, approval rates, correction rates, unique users
- **Model Performance:** MarianMT vs NLLB-200 comparison with winner determination
- **Error Analysis:** Breakdown of error types (grammar, spelling, context, vocabulary, etc.)
- **Direction Statistics:** Performance by translation direction (en→lun vs lun→en)
- **Daily Activity:** Feedback timeline with day-of-week analysis
- **User Engagement:** Anonymized user activity and engagement scores
- **Raw Feedback Data:** Complete feedback log with all fields

### Knowledge Graph
A structured graph of Runyoro-Rutooro grammar knowledge (noun classes, tenses, derivations, rules) that powers explainable AI translation and grammar tutoring.

- `GET /knowledge-graph/stats` — Node and edge counts by type
- `GET /knowledge-graph/noun-class/{class_num}` — Full info for a noun class (concords, plural class, example words). Accepts integers 1–15 or string keys `1a`, `2a`, `9a`, `10a`
- `GET /knowledge-graph/explain/{word}` — Explain a word: its noun class, derivation chain, plural/singular forms, and applicable grammar rules (explainable AI)
- `GET /knowledge-graph/related/{word}` — Find nodes related to a word. Optional query params: `rel` (relationship filter, e.g. `DERIVES_FROM`, `PLURAL_IS`, `BELONGS_TO`) and `direction` (`out`, `in`, or `both`)
- `GET /knowledge-graph/path?word_a=X&word_b=Y` — Find the grammatical relationship path between two words (e.g. `okulima` → `omulimi` → `nc_1`)
- `GET /knowledge-graph/correct?word=X&target=Y` — Get the correct grammatical form of a word. `target`: `plural`, `singular`, `agent_noun`, `action_noun`, `source_verb`
- `POST /knowledge-graph/tutor` — Answer a natural-language grammar question. Body: `{ "question": "..." }`. Supports questions like *"What is the plural of omuntu?"*, *"What class is ekitabu?"*, *"What is the agent noun of okulima?"*
- `GET /knowledge-graph/search?q=X` — Search nodes by label (case-insensitive substring). Optional `node_type` filter (`WORD`, `NOUN_CLASS`, `TENSE`, `RULE`, `DERIVATION`, etc.). Returns up to 50 results
- `GET /knowledge-graph/export` — Export the full knowledge graph as JSON (all nodes and edges — for frontend graph visualisation)
- `GET /knowledge-graph/tenses` — All tense nodes with their markers and examples
- `GET /knowledge-graph/derivations` — All verb derivation types with their suffixes

### Utilities
- `POST /summarize-pdf` — Extract + translate + summarize documents. When a Lunyoro document is detected, grammar rules (nasal assimilation, particle elision, kinship correction, copula normalization) are applied to each sentence before translation. Qwen 2.5 7B (if `HF_TOKEN` is set) refines **both** the MarianMT and NLLB-200 drafts independently, with Grammar Rules 4 post-processing applied to each refined output. The best result (NLLB-refined preferred, Marian-refined as fallback) is returned as `summary_lunyoro`. All four variants are included in the response: `summary_lunyoro` (best), `summary_lunyoro_marian` (Marian-refined), `summary_lunyoro_nllb` (NLLB-refined). Falls back to the MT draft per model if Qwen is unavailable.
- `GET /language-rules` — Full grammar rules JSON
- `POST /language-rules/apply` — Apply specific grammar rule
- `GET /history` — Translation history
- `GET /health` — Health check

---

## Models

All models are automatically loaded from HuggingFace Hub on first use and cached locally:

- **MarianMT en2lun:** [keithtwesigye/lunyoro-en2lun](https://huggingface.co/keithtwesigye/lunyoro-en2lun)
- **MarianMT lun2en:** [keithtwesigye/lunyoro-lun2en](https://huggingface.co/keithtwesigye/lunyoro-lun2en)
- **NLLB en2lun:** [keithtwesigye/lunyoro-nllb_en2lun](https://huggingface.co/keithtwesigye/lunyoro-nllb_en2lun)
- **NLLB lun2en:** [keithtwesigye/lunyoro-nllb_lun2en](https://huggingface.co/keithtwesigye/lunyoro-nllb_lun2en)
- **Semantic search:** [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- **Chat:** [Qwen/Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) via HF Router

**Note:** Models are downloaded automatically on first translation request. To pre-download all models, run `python backend/download_models.py`.

---

## Grammar Rules

Comprehensive Runyoro-Rutooro grammar implementation (3200+ lines):

- **R/L Rule:** L → R except adjacent to e/i
- **Nasal assimilation:** nb→mb, np→mp, nr→nd, nl→nd
- **Apostrophe elision:** na ente → n'ente, habwa okugonza → habw'okugonza; also corrects merged model outputs — both cases where the particle vowel is retained but not elided (e.g. `nomuntu` → `n'omuntu`) and cases where it is dropped entirely (e.g. `nente` → `n'ente`)
- **Consonant+suffix mutations:** r/t/j + -ire → z/s/z + -ire
- **Noun class system:** 15 classes with concordial agreement
- **Verb conjugation:** 10+ tenses, derivative suffixes (causative, passive, etc.)
- **Pronominal system:** Subject/object concords, demonstratives, possessives
- **Numbers & ordinals:** Cardinals 1-1M, ordinal formation rules
- **Particles:** Genitive, copula, conditional, coordinating
- **Grammar Rules 4** (`language_rules_gr4.py`): copula constructions, kinship terms, enumeratives, and the *ka* diminutive/adverbial particle; also corrects split demonstrative forms (`o nu` → `onu`, `ba li` → `bali`, etc.), merges split *dara* presentative constructions (`dara nyowe` → `daranyowe`, `dara bo` → `darabo`, etc.), and fixes space-separated verb-derived nouns (`omu limi` → `omulimi`, `en dima` → `endima`, etc.) — applied as a final post-processing pass on en→lun output via `apply_gr4_rules()`
- **Grammar Rules 5** (`language_rules_gr5.py`): locative adverbial prefixes (omu-/ha-/ku-/owa-/omba), locative demonstratives (munu/muli/hanu/hali/kunu/kuli), self-standing adverbials (-o of reference), adverbial suffixes (-mu/-ho/-yo), locative possessives, copula ni- + locatives, *dara* + locative, *ho* + enumerative roots, objectival concord, noun classes 1a/2a/9a/10a (names, foreign words, colours), negative nouns (omu-ta-), class 9 professional nouns, and augmentative/pejorative forms — wired into `translate.py` post-processing via `apply_gr5_rules()`

See `backend/language_rules.py`, `backend/language_rules_gr4.py`, and `backend/language_rules_gr5.py` for full implementation.

---

## Data Sources

- **Dictionary:** Runyoro-Rutooro Dictionary (OCR + manual entry)
- **Corpus:** 80k+ sentence pairs from:
  - Bible translations
  - Seed vocabulary (medical, agriculture, education, daily life)
  - Community submissions
  - Grammar examples
- **Grammar:** *A Grammar of Runyoro-Rutooro* + Orthography Guide (1995)

---

## Deployment

### Upload Models to HuggingFace Hub
```bash
# Set your HuggingFace token
export HF_TOKEN=hf_...

# Upload all models
python backend/upload_models_to_hf.py --token $HF_TOKEN

# Or use environment variable
python backend/upload_models_to_hf.py
```

This uploads models to HuggingFace Hub, removing the need for Git LFS storage. Models are then downloaded on-demand via `download_models.py`.

### HuggingFace Space (Backend)
```bash
python backend/push_to_hf_space.py
# Pushes to: keithtwesigye-runyoro-translator-api.hf.space
```

### Push Benchmark Files to GitHub
```bash
python push_benchmark_files.py
# Pushes backend/feedback/benchmark_scores.csv and benchmark_scores.json
# to both GitHub repos (chriskagenda/TRANSLATOR and K227-arch/TRANSLATOR).
# Reads GITHUB_TOKEN from backend/.env.
# Creates the file if it doesn't exist in the repo; updates it (with SHA) if it does.
# Run from the lunyoro-translator/ root directory.
```

### Vercel (Frontend)
```bash
cd frontend
vercel --prod
# Deployed to: frontend-six-phi-25.vercel.app
```

---

## Environment Variables

### Backend (.env)
```bash
HF_TOKEN=hf_...                    # HuggingFace API token (optional, for private models)
HF_USERNAME=keithtwesigye          # HuggingFace username for model repositories
HF_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
CORS_ORIGINS=http://localhost:3002,https://frontend-six-phi-25.vercel.app
FEEDBACK_FILE=feedback.jsonl       # Feedback storage path
AUTO_RETRAIN_THRESHOLD=100         # Min new pairs to trigger auto-retrain
GITHUB_TOKEN=ghp_...               # GitHub token for sync_feedback.py (required)
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=https://keithtwesigye-runyoro-translator-api.hf.space
```

---

## Contributing

Contributions welcome! Priority areas:

1. **More training data** — native speaker corrections, domain-specific pairs
2. **Grammar rule refinements** — edge cases, dialect variations
3. **UI improvements** — mobile responsiveness, accessibility
4. **Model optimizations** — quantization, distillation, faster inference

---

## License

MIT License — see LICENSE file

---

## Citation

If you use this work, please cite:

```bibtex
@software{lunyoro_translator_2024,
  author = {Twesigye, Keith},
  title = {Lunyoro-Rutooro Neural Machine Translation System},
  year = {2024},
  url = {https://github.com/keithtwesigye/lunyoro-translator}
}
```

---

## Acknowledgments

- Runyoro-Rutooro Dictionary contributors
- Bible translation teams
- Grammar documentation authors
- HuggingFace for model hosting
- Vercel for frontend hosting

---

## Version History

### v2.9 - Grammar Rules 5: Adverbial Suffix, Objectival Concord, Negative Nouns, Class 9 Professional Nouns & Augmentatives (Current)
- **`train_nllb.py`:** Added multi-GPU support via `torch.nn.DataParallel` — when more than one CUDA GPU is available, the NLLB model is automatically wrapped and training is distributed across all GPUs. Device names are printed at startup. Mirrors the existing multi-GPU behaviour in `train_marian.py`.
- **`language_rules_gr5.py`:** Implemented `apply_adverbial_suffix(verb, locative_prefix)` — appends the correct locative suffix (`-mu`, `-ho`, or `-yo`) to a verb based on its accompanying locative prefix (`omu-`/`omw-` → `-mu`, `ha-` → `-ho`, `owa-`/`omba`/`ku-` → `-yo`).
- **`language_rules_gr5.py`:** Implemented `apply_adverbial_suffix_correction(text)` — regex-based post-processing pass that corrects common MT errors where adverbial suffixes are missing (e.g. `genda owaitu` → `gendayo owaitu`, `ikara hansi` → `ikaraho hansi`, `ikara omunsi` → `ikaramu omunsi`).
- **`language_rules_gr5.py`:** Added `OBJECTIVAL_CONCORDS` — mapping of noun classes 1–15 to their objectival concord prefixes (e.g. class 3 → `gu`, class 7 → `ki`), used when the object is fronted in a reversed-object sentence.
- **`language_rules_gr5.py`:** Implemented `get_objectival_concord(noun_class)` — returns the objectival concord string for a given noun class.
- **`language_rules_gr5.py`:** Implemented `build_reversed_object_sentence(subject, subject_class, object_noun, object_class, verb_stem, tense_prefix)` — constructs a reversed-object sentence by combining the subject concord, objectival concord, verb stem, and perfect suffix (e.g. `build_reversed_object_sentence('omukazi', 1, 'omusiri', 3, 'lima', 'a')` → `'omusiri omukazi agulimire'`).
- **`language_rules_gr5.py`:** Added `NEGATIVE_NOUNS` dictionary and `build_negative_noun(verb_stem)` — derives Class 1 negative nouns using the `omu-ta-` prefix pattern (e.g. `build_negative_noun('seka')` → `'omutaseka'`, meaning "one who does not laugh").
- **`language_rules_gr5.py`:** Added `CLASS9_PROFESSIONAL_NOUNS` dictionary and `derive_class9_professional(verb_stem)` — derives Class 9 professional/habitual nouns using `en-` before consonants and `em-` before bilabials (e.g. `derive_class9_professional('lima')` → `'endima'`; `derive_class9_professional('baza')` → `'embaza'`).
- **`language_rules_gr5.py`:** Added `AUGMENTATIVE_EXAMPLES` dictionary and `build_augmentative(base_noun, aug_class)` — builds augmentative/pejorative forms by substituting the noun class prefix: class `'5'` (eri-/i-) for magnitude/pejorative (e.g. `'omusaija'` → `'isaija'`), class `'7'` (eki-) for magnitude/affection/contempt (e.g. `'omusaija'` → `'ekisaija'`). Strips common class 1/3/5/7 prefixes before applying the substitution.
- **`extract_gr5_training_pairs.py`:** New script that extracts ~300 clean English ↔ Runyoro-Rutooro training pairs from grammar rules 5.docx (Chapters 5–7). Covers locative agreement, locative demonstratives, genitive/possessive locatives, adverbial suffixes (-mu/-ho/-yo), ho + enumerative roots, dara + locative, copula ni- + locatives, reversed-object sentences, noun class examples (1a/2a/9a/10a), colour names, augmentative/pejorative forms, negative nouns, class 9 professional nouns, twin names, and kinship terms. Writes to `data/cleaned/gr5_pairs.csv` and merges into `train.csv`/`val.csv` (90/10 split, deduplication-safe).

### v2.8 - Qwen Refinement for `/translate-reverse`
- **`/translate-reverse` improvement:** Added optional `refine: bool` parameter (default `false`). When `true` and `HF_TOKEN` is set, a Qwen 2.5 7B pass refines the lun→en MT draft for fluency, accuracy, and natural English phrasing before the response is returned. Falls back silently to the MT draft if Qwen is unavailable. The refined output is also recorded in translation history with a `+refined` method suffix.

### v2.7 - Qwen Refinement for `/translate`
- **`/translate` improvement:** Added optional `refine: bool` parameter (default `false`). When `true` and `HF_TOKEN` is set, a Qwen 2.5 7B pass refines the MT draft — fixing noun-class prefixes, concordial agreement, R/L rule, apostrophe elision, and kinship terms — before the response is returned. Grammar Rules 4 post-processing is applied on top of the LLM output. Falls back silently to the MT draft if Qwen is unavailable.

### v2.6 - Particle Elision Correction Fix
- **`language_rules.py` bugfix:** `_MERGED_ELISION` patterns for `no/zo/yo/wo + vowel-initial word` now correctly preserve the leading vowel in the replacement (e.g. `nomuntu` → `n'omuntu` instead of the previous incorrect `n'muntu`). The patterns are now word-specific rather than a generic vowel-class match, preventing false positives. Fully-merged forms where the particle vowel is dropped entirely (e.g. `nente` → `n'ente`, `zomuntu` → `z'omuntu`) are handled by a separate set of patterns covering common Runyoro-Rutooro nouns.

### v2.5 - Dual-Model Qwen Refinement for Document Summarization
- **`/summarize-pdf` improvement:** Qwen 2.5 7B (via HuggingFace Router) now refines the MarianMT and NLLB-200 summary drafts **independently** when `HF_TOKEN` is set. Each model's draft is sent to Qwen separately with the English source and grammar rules as context. Grammar Rules 4 post-processing is applied to each refined output. The response now includes `summary_lunyoro` (best output — NLLB-refined preferred), `summary_lunyoro_marian` (Marian-refined), and `summary_lunyoro_nllb` (NLLB-refined). Falls back silently to the respective MT draft per model if Qwen is unavailable or times out.

### v2.4 - Grammar Pre-Processing for Document Summarization
- **`/summarize-pdf` improvement:** When a Lunyoro document is detected, grammar rules (nasal assimilation, particle elision, kinship correction, copula normalization) are now applied to each sentence before Lunyoro→English translation, improving summary quality for Runyoro-Rutooro input documents

### v2.3 - Grammar Rules 4 Post-Processing
- **Grammar Rules 4** (`language_rules_gr4.py`) integrated as a final post-processing step in `translate.py` for en→lun output
- Covers copula constructions, kinship term agreement, enumerative patterns, and the *ka* diminutive/adverbial particle
- Applied after all existing rules (R/L, nasal assimilation, apostrophe elision) in the normalisation pipeline

### v2.2 - Document Editor Mobile Responsiveness (Current)
- **Document Editor toolbar removed** — the formatting toolbar (bold, italic, underline, lists, alignment, spellcheck, save) has been removed from `DocumentEditor.tsx`. Formatting controls remain available in the dedicated `RunyoroEditor.tsx` component. Sub-tabs in `DocumentEditor` are horizontally scrollable on mobile (`overflow-x-auto`).

### v2.1 - Rebranding & UI Refresh
- **App renamed** to "AI Stick — Runyoro / Rutooro Translator"
- **Theme color** updated to `#070235` (deep navy)
- **Typography:** Inter font (400/600/700/800) loaded via Google Fonts
- **Icons:** Material Symbols Outlined added via Google Fonts
- **PWA title** updated to "AI Stick"
- **Bottom navigation bar** (`BottomNav.tsx`) — fixed mobile nav with Home, Translate, Chat, and Editor tabs; active tab uses filled icon + secondary-container highlight
- **Chat UI redesign** — migrated to Material Design 3 tokens; input upgraded to multi-line textarea with mic button; language switcher (English / Runyoro-Rutooro) added at top; sector list consolidated to 8 domains

### v2.0 - Enhanced Feedback & Model Comparison
- **Enhanced feedback system:** Multi-select error categorization (grammar, spelling, context, vocabulary, other)
- **Model comparison interface:** 2x2 grid to choose between MarianMT, NLLB-200, both correct, or both wrong
- **Model preference learning:** Selected model becomes primary for future translations
- **Separate feedback flows:** Independent tracking for quality feedback and model comparison
- **Improved UX:** Immediate translation updates when model preference is selected

### v1.0 - Initial Release
- Dual neural models (MarianMT + NLLB-200)
- Semantic search fallback
- Grammar rule post-processing
- Basic feedback system
- Chat assistant integration
