# Model Training Pipeline — Design

## Overview

The pipeline is a sequential data-to-deployment workflow with three logical
stages: **Data**, **Training**, and **Deployment**. Two independent model
families (MarianMT, NLLB-200) are trained in parallel where hardware allows,
and each is exported in multiple formats targeting different runtime environments
(GPU server, HF Space CPU, Raspberry Pi).

```
┌─────────────────────────────────────────────────────────────────────────┐
│  RAW DATA                                                               │
│  18× sentence pair Excels · 5× seed CSVs · Dictionary · OCR pairs      │
│  Grammar rules · Back-translated pairs · User feedback                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   CLEANING          │
                    │  clean_training_data│
                    │  clean_ocr_pairs    │
                    │  fix_malformed_tags │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────────┐
              │         AUGMENTATION                │
              │  POS tagging + plurals + verb forms │
              │  Back-translation (NLLB en→lun)     │
              │  Round-trip BT (BLEU ≥ 0.25 filter) │
              └────────────────┬────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
    ┌──────────▼──────────┐       ┌────────────▼────────────┐
    │  train_marian.py    │       │   train_nllb.py          │
    │  7ep · lr=3e-5      │       │   5ep · lr=8e-6          │
    │  batch=32 · fp32    │       │   batch=8 · fp32         │
    │  context window     │       │   nyo_Latn forced BOS    │
    │  SPM α=0.1          │       │   embedding resize       │
    └──────────┬──────────┘       └────────────┬────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   EVALUATION        │
                    │  BLEU + chrF        │
                    │  val.csv.bak stable │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────────┐
              │                │                    │
   ┌──────────▼──────┐  ┌──────▼───────┐  ┌────────▼────────┐
   │ MarianMT ONNX   │  │ NLLB ONNX    │  │ NLLB INT8       │
   │ FP32            │  │ FP32         │  │ Raspberry Pi     │
   │ HF Space/server │  │ HF Space     │  │ ~1.9 GB/dir      │
   └──────────┬──────┘  └──────┬───────┘  └────────┬────────┘
              └────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   DEPLOYMENT        │
                    │  push_models.py     │
                    │  push_to_hf_space   │
                    │  git push           │
                    └─────────────────────┘
```

---

## Data Layer

### Training Split Strategy

The dataset has two distinct val sets:

| File | Rows | Purpose |
|------|------|---------|
| `data/training/val.csv` | ~96,000 | Full val including all augmented/BT pairs |
| `data/training/val.csv.bak` | 14,260 | **Stable** — original human pairs only |

During incremental training (`--new-only` flag), the trainer validates on
`val.csv.bak` instead of the full `val.csv`. This avoids the "BLEU dip" problem:
when new augmented or back-translated pairs are added to val.csv, the model
hasn't trained on them yet, artificially lowering reported BLEU. The stable bak
file gives an honest signal.

When new-only training data (`new_only_train.csv`, ~795 pairs) is exhausted, the
full `train.csv` is used as fallback.

### Weighted Sampler

Both trainers use a `WeightedRandomSampler` that assigns each training pair a
priority weight at the start of each run. The weights are computed by checking
set membership in pre-loaded CSV files:

```
weight(pair) = base_weight × direction_multiplier

base_weight:
  (en, lun) ∈ seed_keys        → 8.0
  (en, lun) ∈ grammar_keys     → 6.0
  source = "back_translation"  → 2.0
  otherwise                    → 1.0

direction_multiplier (lun→en):
  lun_words ≥ 5  → ×3.0
  lun_words ≥ 3  → ×1.5
  lun_words ≤ 2  → ×0.3

direction_multiplier (en→lun):
  en_words ≥ 8   → ×1.5
```

This ensures domain expert translations and grammar rule pairs are seen far more
often than noisy or synthetic data, without discarding any pairs entirely.

---

## Augmentation Layer

### POS Augmentation (`augment_and_train.py`)

Generates three categories from `runyoro_domain_dictionary_clean.csv`:

**1. POS-tagged pairs** — Every entry becomes a tagged training sentence:
```
[HEALTH_AND_MEDICINE_NOUN] fever → omusujja
[AGRICULTURE_VERB] to harvest → okusarura
```
The domain tag conditions the model's vocabulary choice — medical terms should
be translated with medical precision.

**2. Plural augmentation** — Runyoro uses Bantu noun classes. The pipeline
applies Runyoro-specific plural rules and orthographic corrections:
```
omukazi  (woman)  → abakazi (women)     [Class 1→2: omu→aba]
ekitabo  (book)   → ebitabo (books)     [Class 7→8: eki→ebi]
eriiwe   (tooth)  → amaiwe  (teeth)     [Class 5→6: eri→ama]
```
After prefix substitution, `fix_spelling()` applies:
- Nasal assimilation: `nb→mb`, `np→mp`, `nr→nd`, `nl→nd`
- R/L rule: `L→R` except when adjacent to `e` or `i`

**3. Verb conjugation** — From each `oku-` infinitive, five forms are generated:
```
okulima (to cultivate) →
  nkulima     I cultivate          (present 1sg: n + stem)
  akulima     he/she cultivates    (present 3sg: a + stem)
  nkulimize   I have cultivated    (perfect: n + root_mutation + ire)
  kulima!     Cultivate!           (imperative: stem)
  tinkulima   I don't cultivate    (negative: tin + stem)
```
Perfect tense applies consonant mutations: r→z, t→s, j→z to the verb root.

### Back-Translation (`back_translate_lun2en.py`)

The main purpose is to synthetically expand the lun→en training set, which is
sparse because most human data was collected with English as the source.

**Strategy**: Use the NLLB en→lun model (strongest model, described in code as
reaching BLEU=73.97) as a teacher to generate synthetic Runyoro sentences from
English originals. The original English becomes the reference translation.

**Priority ordering for English source sentences**:
1. Tagged pairs (`[TAG] English`) — strip tag, use clean English. These were
   stored as en→lun-format pairs, so lun→en never saw them as input. Highest
   value because the model has zero exposure to these as lun→en source.
2. Short dictionary entries with long English (lun_words ≤ 2, en_words ≥ 5)
3. External cleaned sources

**Quality filter** on the generated Runyoro:
- ≥ 5 Runyoro words
- Not identical to the English input (passthrough rejection)
- ≤ 30% common English function words in the Runyoro output

Result: 62,922 clean synthetic lun→en pairs in `augmented_bt_lun2en_clean.csv`,
weighted at 2× during training (lower priority than human data).

---

## Training Layer

### MarianMT (`train_marian.py`)

```
TranslationDataset
  ├── context_window: prepend prev sentence as "prev ||| current"
  │   (only if prev < 100 chars; teaches discourse coherence)
  └── subword_regularization: SPM sampling with alpha=0.1

DataLoader
  └── WeightedRandomSampler (see Data Layer)

Optimizer: AdamW(lr=3e-5, weight_decay=0.01)
Scheduler: LinearWarmup (warmup=10% of total steps)
Loss: cross-entropy on target tokens (standard seq2seq)
Gradient clipping: 1.0

Per-epoch evaluation:
  500-pair sample from val.csv.bak
  → BLEU + chrF + val_loss
  → Save best checkpoint if BLEU improved

End of training:
  Promote best_checkpoint/ → model/en2lun/ (or lun2en/)
  Back up previous model to model/en2lun_backup/
```

**lun→en preprocessing** (applied before training, not at inference):
- Strip domain tags from English column
- Filter `lun_words < min_lun_words` (default 3)

This is critical because en→lun training data was formatted with domain prefix
tags (`[GENERAL_NOUN] cultivator`). For lun→en, the model must produce clean
English — the tags must be stripped first.

### NLLB-200 (`train_nllb.py`)

NLLB uses a lower learning rate (`8e-6` vs `3e-5`) and smaller batch size (`8`
vs `32`) because the model is 7× larger (600M parameters). All other logic —
weighted sampler, lun→en preprocessing, best-BLEU checkpoint — is identical.

The only NLLB-specific detail is `forced_bos_token_id = nyo_Latn token ID`.
NLLB-200 is a multi-lingual model; the forced BOS tells the decoder which
language to generate. Without this, the model defaults to the nearest Bantu
language (Rundi, Kinyarwanda, Luganda) and produces fluent but wrong output.

### New-Only vs Full Training

The `--new-only` flag controls which data subset is trained on:

```
--new-only=True:
  train_df = new_only_train.csv  (795 new pairs)
  val_df   = val.csv.bak         (14,260 stable pairs for honest BLEU)

--new-only=False:
  train_df = train.csv           (all ~80k+ pairs)
  val_df   = val.csv             (full val)
```

New-only training is faster (minutes vs hours) and avoids catastrophic
forgetting — it applies only the new knowledge while relying on the existing
model weights for everything already learned.

### Full Pipeline Orchestration (`run_full_training.py`)

The canonical training run for a new data batch:

```
Step 1: MarianMT en→lun  (5 ep, new-only, lr=3e-5)
Step 2: MarianMT lun→en  (5 ep, new-only, min_lun_words=3)
Step 3: NLLB    en→lun   (5 ep, new-only, lr=8e-6)
Step 4: NLLB    lun→en   (5 ep, new-only, min_lun_words=3)
Step 5: MarianMT RETRAIN en→lun  (5 ep, new-only, full val)
Step 6: MarianMT RETRAIN lun→en  (5 ep, new-only, full val)
Step 7: push_models.py --all
Step 8: push_to_hf_space.py
Step 9: git push origin main && git push k227 main
```

Steps 5–6 re-run MarianMT training after NLLB has been trained — this
regularises MarianMT against NLLB's outputs and validates on the full val set,
giving the final published BLEU score.

---

## Export Layer

### Runtime Environments and Model Formats

| Environment | MarianMT format | NLLB format | Notes |
|-------------|-----------------|-------------|-------|
| GPU server (local) | PyTorch FP32 | PyTorch FP32 | Full quality, fastest GPU |
| HF Space (cpu-basic) | ONNX FP32 | PyTorch FP16 | Space has 16 GB RAM; ONNX 2-5× faster on CPU |
| Raspberry Pi 5 | ONNX FP32 | ONNX INT8 | NLLB FP32 = 6.8 GB; INT8 = 1.9 GB |

### NLLB INT8 Quantization Design

INT8 quantization uses `quantize_dynamic` (weight-only, post-training):

```python
quantize_dynamic(
    model_input  = "encoder_model.onnx",
    model_output = "encoder_model_quantized.onnx",
    weight_type  = QInt8,
    extra_options = {"MatMulConstBOnly": True},  # weights only
    use_external_data_format = True,             # NLLB decoder > 2 GB protobuf limit
)
```

`MatMulConstBOnly=True` quantizes only the constant weight matrices (not
activations or dynamic tensors). This means the greedy decode loop runs with
float activations — full numerical range — while the model weights use 8-bit
storage. The quality impact is negligible (4/5 output parity vs FP32 on probes).

The Pi C++ backend (`translator_v2`) loads exactly **two** ONNX sessions per
direction: `encoder_model_quantized.onnx` and `decoder_model_quantized.onnx`.
`decoder_with_past_model.onnx` is deliberately NOT quantized or shipped — the
Pi uses greedy decoding with no KV cache.

---

## Deployment Layer

### HuggingFace Hub

Models are versioned in HF Hub repositories. `push_models.py` supports:

```bash
push_models.py --model en2lun           # single base PyTorch model
push_models.py --all                    # all 4 base PyTorch models
push_models.py --all-variants           # PyTorch + ONNX FP32 + ONNX INT8
```

ONNX variants are stored as subfolders within the same repo
(e.g. `keithtwesigye/lunyoro-nllb-en2lun/onnx/`) rather than separate repos.
This reduces the number of repos and keeps the base model and its optimized
variants co-located.

### HF Space (Docker)

The HF Space (`keithtwesigye/runyoro-translator-api`) runs a Docker container.
At startup (`docker-entrypoint.sh`):

```bash
if DISABLE_MARIAN=1: python download_models.py --nllb-only
elif DISABLE_NLLB=1: python download_models.py --marian-only
else:                python download_models.py --nllb-only
```

The `--nllb-only` flag downloads NLLB models + sem_model but skips MarianMT and
datasets, keeping startup well under the 50 GB Space storage limit.

### Auto-Retraining

```
User submits feedback  →  feedback.jsonl
                             ↓
auto_retrain.py polls  →  count clean approved pairs
                             ↓ (≥ 100 new pairs)
retrain_from_feedback.py   →  3 epochs, both directions
                             ↓
.last_retrain file updated  →  reset counter
```

The retrain runs in a background thread launched from the FastAPI `/feedback`
endpoint — it does not block the HTTP response.

---

## Key File Reference

| File | Role |
|------|------|
| `train_marian.py` | MarianMT fine-tuning (hyperparams, sampler, eval, checkpoint) |
| `train_nllb.py` | NLLB-200 fine-tuning (identical structure, lower LR/batch) |
| `run_full_training.py` | Orchestrates full pipeline: clean → train → push |
| `augment_and_train.py` | POS augmentation + plural + verb forms + full pipeline |
| `back_translate_lun2en.py` | Generates synthetic lun→en pairs via NLLB |
| `back_translate.py` | Round-trip BT with BLEU filter for en→lun |
| `clean_training_data.py` | Primary cleaner (9 steps) for all splits |
| `clean_new_training_data.py` | Cleaner for newly added data |
| `fix_malformed_tags.py` | Corrects misspelled domain tags |
| `clean_ocr_pairs.py` | Removes OCR dictionary notation artifacts |
| `eval_bleu.py` | Parallel GPU BLEU+chrF evaluation |
| `export_to_onnx.py` | MarianMT → ONNX FP32 |
| `export_nllb_onnx.py` | NLLB → ONNX FP32 |
| `export_onnx_int8.py` | NLLB ONNX FP32 → INT8 for Raspberry Pi |
| `push_models.py` | Uploads models to HF Hub |
| `push_to_hf_space.py` | Uploads backend to HF Space |
| `auto_retrain.py` | Feedback-triggered retraining service |
| `download_models.py` | Downloads models at container startup |
| `add_runyoro_token.py` | Adds `nyo_Latn` token to NLLB tokenizer |
