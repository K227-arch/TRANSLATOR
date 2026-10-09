# Model Training Pipeline — Requirements

## Introduction

This document defines the requirements for the Runyoro-Rutooro neural machine
translation model training pipeline. The pipeline covers the complete lifecycle
of both translation models — **MarianMT** and **NLLB-200** — from raw bilingual
data through cleaning, augmentation, fine-tuning, evaluation, export, and
deployment.

The translator targets a low-resource Bantu language (Runyoro-Rutooro) with
limited parallel data. The pipeline is therefore designed to maximise data
coverage through augmentation and back-translation, and to prioritise human-
verified and domain-expert pairs during training.

---

## Requirements

### 1. Base Models

**REQ-1.1** The pipeline SHALL fine-tune two architectures independently for
both translation directions (English→Runyoro and Runyoro→English):

- **MarianMT** — initialised from a local checkpoint in `model/en2lun/` and
  `model/lun2en/`. Never trained from scratch.
- **NLLB-200 (600M)** — initialised from local checkpoints in
  `model/nllb_en2lun/` and `model/nllb_lun2en/`. Never trained from scratch.

**REQ-1.2** The NLLB model SHALL use a custom `nyo_Latn` language token for
Runyoro-Rutooro. This token's embedding SHALL be initialised from the average of
three related Bantu language embeddings: `run_Latn + lug_Latn + kin_Latn`.

**REQ-1.3** When the tokenizer vocabulary size changes (e.g. after adding
`nyo_Latn`), both trainers SHALL resize the model's embedding matrix accordingly
via `model.resize_token_embeddings(new_size)`.

---

### 2. Data Sources

**REQ-2.1** The pipeline SHALL ingest data from the following sources:

| Source | Location | Description |
|--------|----------|-------------|
| Sentence pair Excels | `data/raw/sentence pair*.xlsx` | 18 hand-curated bilingual files |
| Domain seed vocabularies | `data/raw/*_seed_vocabulary.csv` | 5 files: medical, education, daily life, agriculture, low-frequency |
| Domain dictionary | `data/cleaned/runyoro_domain_dictionary_clean.csv` | POS-tagged word entries |
| OCR pairs | `data/cleaned/ocr_pairs_extracted.csv` | Extracted from printed grammar books |
| Grammar rule pairs | `data/cleaned/gr4_pairs.csv`, `gr5_pairs.csv` | Grammar Rule 4 & 5 sentence pairs |
| Back-translated pairs | `data/training/back_translated.csv` | Synthetic en→lun→en round-trip pairs |
| BT lun2en pairs | `data/cleaned/augmented_bt_lun2en_clean.csv` | 62,922 synthetic lun→en pairs |
| User feedback | `feedback.jsonl` | Approved user corrections |
| Community submissions | `data/raw/sentence_submissions_rows.csv` | Crowdsourced pairs |

**REQ-2.2** Training data SHALL be split into `data/training/train.csv` (90%)
and `data/training/val.csv` (10%). The stable validation reference
`val.csv.bak` (original 14,260 pairs) SHALL be preserved for honest BLEU
measurement during incremental training to avoid "BLEU dip" from newly added
augmented pairs.

---

### 3. Data Cleaning

**REQ-3.1** All data SHALL pass through a cleaning pipeline before training.
The following SHALL be removed or corrected:

- Malformed domain tags (e.g. `[GENerAL]`, `[REERAL]`, `[AGRCULTURE)`) —
  corrected to canonical forms or stripped
- OCR notation artifacts: `n. cl. 11`, `(pl. nil)`, `(pf. -culeezi)`,
  `ekisisani`, `v.rejl.`
- Pairs where either side is fewer than 3 characters
- Pairs where source equals target (copy-through noise)
- Pairs exceeding 300 characters on either side (concatenated garbage)
- Lunyoro column containing >35% English stopwords (language-swap noise)
- English column containing >40% Runyoro prefixes (language-swap noise)
- Exact duplicate pairs

**REQ-3.2** Domain tags in the English column of `lun→en` training pairs SHALL
be stripped before training so the model produces clean English output (e.g.
`[GENERAL_NOUN] cultivator` → `cultivator`).

**REQ-3.3** For `lun→en` training, pairs where the Lunyoro side has fewer than
`min_lun_words` (default 3) words SHALL be excluded, to prevent single-word
dictionary entries degrading sentence-level BLEU.

---

### 4. Data Augmentation

**REQ-4.1** The pipeline SHALL generate augmented training pairs from the domain
dictionary via `augment_and_train.py`, producing three types:

1. **POS-tagged pairs**: `[DOMAIN_POS] english` → `runyoro` for every
   dictionary entry (e.g. `[HEALTH_AND_MEDICINE_NOUN] fever` → `omusujja`)
2. **Plural augmentation**: Noun class plural forms using Runyoro noun class
   rules (omu-→aba-, eki-→ebi-, eri-→ama-, aka-→utu-, oru-→en-/em-)
3. **Verb conjugation pairs**: From each `oku-` infinitive, generates: present
   1sg, present 3sg, perfect 1sg (with consonant mutations r→z, t→s, j→z),
   imperative, and negative present

**REQ-4.2** All augmented Runyoro forms SHALL have orthographic rules applied:
nasal assimilation (nb→mb, np→mp, nr→nd, nl→nd) and the R/L rule
(L→R except when adjacent to e or i).

**REQ-4.3** The pipeline SHALL perform back-translation via NLLB en→lun
(`back_translate_lun2en.py`) to generate synthetic lun→en training pairs:

- Priority 1: Tagged pairs (`[TAG] English`) — strip tag, use English as
  source; these were en2lun-only format so lun2en never saw them as input
- Priority 2: Short dictionary pairs (lun_words ≤ 2, en_words ≥ 5)
- Filter: keep only if Runyoro output ≥ 5 words, not a passthrough,
  and <30% common English words appear in the Runyoro output

**REQ-4.4** Round-trip back-translation (`back_translate.py`) SHALL filter
synthetic pairs by round-trip BLEU ≥ 0.25 before adding to training data.

---

### 5. Training — MarianMT

**REQ-5.1** MarianMT SHALL be fine-tuned with these default hyperparameters:

| Parameter | Default |
|-----------|---------|
| Epochs | 7 |
| Batch size | 32 |
| Learning rate | 3e-5 (AdamW) |
| Weight decay | 0.01 |
| Max token length | 256 |
| Precision | fp32 |
| Warmup steps | 10% of total steps |
| Gradient clipping | 1.0 |

**REQ-5.2** Training SHALL use a **context window** (default enabled): the
previous sentence is prepended as context (`"prev ||| current"`) when it is
fewer than 100 characters. This teaches the model discourse-level coherence.

**REQ-5.3** Training SHALL use **subword regularisation** (SentencePiece
sampling, `alpha=0.1`) by default to improve robustness to different
segmentation patterns.

**REQ-5.4** The trainer SHALL save a best checkpoint by validation BLEU at the
end of each epoch and promote it to the model root when training completes.

---

### 6. Training — NLLB-200

**REQ-6.1** NLLB-200 SHALL be fine-tuned with these default hyperparameters:

| Parameter | Default |
|-----------|---------|
| Epochs | 5 |
| Batch size | 8 |
| Learning rate | 8e-6 (AdamW) |
| Weight decay | 0.01 |
| Max token length | 256 |
| Precision | fp32 |
| Warmup steps | 10% of total steps |
| Gradient clipping | 1.0 |
| Decoder BOS | `nyo_Latn` token ID (forced BOS) |

**REQ-6.2** NLLB training SHALL use the same weighted sampler, lun2en
preprocessing (tag stripping + minimum word filter), and best-BLEU checkpoint
promotion as MarianMT.

**REQ-6.3** Both trainers SHALL support multi-GPU training via
`torch.nn.DataParallel` when multiple CUDA devices are detected.

---

### 7. Weighted Sampling

**REQ-7.1** Both trainers SHALL use a direction-aware weighted random sampler
with the following base weights:

| Pair type | Weight |
|-----------|--------|
| Domain seed vocabulary | 8× |
| Grammar rule pairs (gr4 + gr5) | 6× |
| Back-translated pairs | 2× |
| All other pairs | 1× |

**REQ-7.2** For `lun→en`, the sampler SHALL apply these length-based
multipliers to the base weight:

| Runyoro side word count | Multiplier |
|------------------------|------------|
| ≥ 5 words | 3× |
| 3–4 words | 1.5× |
| ≤ 2 words | 0.3× |

**REQ-7.3** For `en→lun`, English inputs with ≥ 8 words SHALL receive a 1.5×
multiplier (longer sentences contain more morphology for the model to learn).

---

### 8. Evaluation

**REQ-8.1** The pipeline SHALL evaluate every model at the end of each training
epoch using BLEU (`sacrebleu`, `effective_order=True`) and chrF (character-level
F-score) on up to 500 validation pairs.

**REQ-8.2** `eval_bleu.py` SHALL run full evaluation for all four models in
parallel using both GPUs: MarianMT on `cuda:0`, NLLB on `cuda:1`.

**REQ-8.3** Evaluation results SHALL be persisted to `bleu_results.json`.

---

### 9. Export and Quantization

**REQ-9.1** MarianMT SHALL be exported to ONNX FP32 format via
`optimum.onnxruntime.ORTModelForSeq2SeqLM` for 2–5× faster CPU inference:
- Output: `model/en2lun_onnx/` and `model/lun2en_onnx/`

**REQ-9.2** NLLB SHALL be exported to ONNX FP32 via the optimum CLI:
- Output: `model/nllb_en2lun_onnx/` and `model/nllb_lun2en_onnx/`

**REQ-9.3** NLLB SHALL additionally be quantized to INT8 for Raspberry Pi
deployment (`export_onnx_int8.py`):
- Method: `onnxruntime.quantization.quantize_dynamic`, `weight_type=QInt8`,
  `MatMulConstBOnly=True` (weights only; activations stay float)
- Only `encoder_model.onnx` and `decoder_model.onnx` are quantized.
  `decoder_with_past_model.onnx` is NOT quantized (Pi uses greedy without
  KV cache)
- Output: `model/nllb_en2lun_pi/encoder_model_quantized.onnx` + `decoder_model_quantized.onnx`
- Target size: ~1.9 GB per direction (down from ~6.8 GB unquantized)

**REQ-9.4** MarianMT SHALL remain fp32 for the Pi — at ~886 MB per direction
it fits within the 8 GB RAM budget without quantization.

---

### 10. Model Push and Deployment

**REQ-10.1** Trained models SHALL be pushed to HuggingFace Hub under the
`keithtwesigye` account:

| Model | HF Repo |
|-------|---------|
| MarianMT en→lun | `keithtwesigye/lunyoro-en2lun` |
| MarianMT lun→en | `keithtwesigye/lunyoro-lun2en` |
| NLLB en→lun | `keithtwesigye/lunyoro-nllb-en2lun` |
| NLLB lun→en | `keithtwesigye/lunyoro-nllb-lun2en` |
| Semantic search | `keithtwesigye/lunyoro-sentence-embeddings` |

**REQ-10.2** ONNX and INT8 variants SHALL be uploaded as subfolders within the
same HF repo (not separate repos). `push_models.py --all-variants` handles this.

**REQ-10.3** The backend source code SHALL be pushed to the HuggingFace Docker
Space (`keithtwesigye/runyoro-translator-api`) via `push_to_hf_space.py`.

---

### 11. Auto-Retraining from Feedback

**REQ-11.1** The system SHALL automatically trigger retraining when 100 or more
new clean feedback pairs have been collected since the last retrain (threshold
configurable via `AUTO_RETRAIN_THRESHOLD` environment variable).

**REQ-11.2** Auto-approval criteria for feedback pairs:
- Both source and translation are non-empty after cleaning
- Length 3–500 characters
- Contains at least one letter
- No word repeated 4+ times
- Source ≠ translation
- At least 2 words on each side

**REQ-11.3** Auto-retraining SHALL run `retrain_from_feedback.py` for 3 epochs
in both directions with a 2-hour timeout.

---

## Out of Scope

- Training from scratch (always fine-tunes from existing checkpoints)
- GPU-specific builds (training uses fp32 for stability; INT8 is for CPU
  inference only)
- Parallel sentence mining from monolingual data (back-translation is used
  instead)
- Model architecture changes (MarianMT and NLLB architectures are fixed)
