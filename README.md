# Lunyoro-Rutooro Translator

An AI-powered translation system for the Runyoro-Rutooro language of the Bunyoro-Kitara and Tooro kingdoms in Uganda.

## Live Demo
- **Frontend**: https://frontend-six-phi-25.vercel.app/
- **Backend API**: https://huggingface.co/spaces/keithtwesigye/runyoro-translator-api

## Features

- English ↔ Lunyoro/Rutooro translation (MarianMT + NLLB-200)
- **Selective RAG** — high-confidence corpus retrieval (score >= 0.92) before neural MT
- **Linguistic Knowledge Graph** — explainable AI, grammar tutoring, intelligent correction
- Dictionary lookup with example sentences
- AI chat assistant powered by Qwen 2.5 7B (via HuggingFace Inference API)
- PDF/DOCX document summarization and translation
- Spellcheck
- Domain-aware translation (Medical, Education, Agriculture, Governance, etc.)
- Dual neural models (MarianMT + NLLB-200) with unified single-output display
- Grammar post-processing pipeline (gr4 + gr5 rules: locatives, copula, kinship, colours, verb conjugations)
- Human feedback loop with 8-dimension benchmark scoring (SQS)
- Auto-retrain from approved feedback pairs

## Models

| Model | Direction | Best BLEU | chrF | Notes |
|---|---|---|---|---|
| MarianMT | en→lun | 68.15 | 78.55 | 7 epochs, fp32 |
| MarianMT | lun→en | 54.39+ | 67.08+ | Fix1+Fix2+Fix3, 57k sentence pairs |
| NLLB-200 | en→lun | 73.97 | — | nyn_Latn language code |
| NLLB-200 | lun→en | 42.30 | — | Improving with back-translation |

## Dataset

- **246,280** English-Lunyoro training pairs (train + val)
- **51,202** back-translated lun2en sentence pairs (Fix 3)
- Sources:
  - `english_nyoro_clean.csv` — 89,703 sentence pairs with domain tagging
  - `runyoro_english_sentences_clean.csv` — crowd-sourced sentence submissions
  - `rutooro_dictionary_clean.csv` — Rutooro dictionary word/definition pairs
  - `word_entries_clean.csv` — dictionary example sentences
  - `runyoro_domain_dictionary_clean.csv` — domain-tagged vocabulary
  - `back_translated_lun2en.csv` — 51,202 synthetic lun2en pairs (Fix 3)
  - `gr4_pairs.csv`, `gr5_pairs.csv`, `gr_grammar_pairs.csv` — grammar rule pairs
  - `empaako_pairs.csv`, `idioms_pairs.csv`, `numbers_pairs.csv`, `proverbs_pairs_clean.csv`

## lun2en Improvements (Fix 1 + Fix 2 + Fix 3)

The lun2en direction was previously underperforming because:
1. **Fix 1**: 104k tagged pairs `[DOMAIN] english → runyoro` had domain tags in English targets — stripped for lun2en training
2. **Fix 2**: 69k single-word dictionary entries filtered out (min-lun-words=3) — lun2en needs sentences not word pairs
3. **Fix 3**: Back-translation — 51,202 new lun2en sentence pairs generated using NLLB en2lun (BLEU 73.97)

Result: lun2en training data grew from 22,729 → 57,134 quality sentence pairs (+2.5x)

## Architecture

```
User Input
    ↓
Preprocessing (normalisation, tokenisation)
    ↓
Grammar Rule Engine (noun classes, R/L, suffix mutations, tense)
    ↓
Selective RAG (score >= 0.92 → direct retrieval, 0.70-0.91 → hint)
    ↓
Neural MT (MarianMT + NLLB-200, ensemble)
    ↓
Post-Processing (gr4 + gr5 grammar rules, dialect normalisation)
    ↓
Final Translation
```

## Knowledge Graph API

The Linguistic Knowledge Graph models Runyoro-Rutooro grammar as a directed graph:

- `GET /knowledge-graph/stats` — node/edge counts
- `GET /knowledge-graph/noun-class/{1-15}` — full noun class info with concords
- `GET /knowledge-graph/explain/{word}` — explainable AI: class, derivation, rules
- `GET /knowledge-graph/related/{word}` — related words by relationship type
- `GET /knowledge-graph/path?word_a=X&word_b=Y` — grammatical path between words
- `GET /knowledge-graph/correct?word=X&target=plural` — correct grammatical form
- `POST /knowledge-graph/tutor` — natural language grammar questions
- `GET /knowledge-graph/export` — full graph as JSON for visualisation

## Training

```bash
# Full pipeline (MarianMT + NLLB, both directions)
python run_full_training.py --marian-en2lun-epochs 7 --marian-lun2en-epochs 7 \
                            --nllb-en2lun-epochs 5  --nllb-lun2en-epochs 5

# lun2en retrain with all fixes
python retrain_lun2en.py --now

# Skip the initial MarianMT+NLLB retrain and go straight to back-translation + final pass
# Useful when models are already up-to-date and only new BT data needs to be incorporated
python retrain_lun2en.py --now --skip-initial-train

# Back-translate remaining candidates
python back_translate_lun2en.py --max-sentences 23000 --merge

# Evaluate all models (BLEU + chrF)
python eval_bleu.py --samples 1000
```

## Metrics

Training now logs per epoch:
- **BLEU** (corpus BLEU, sacrebleu)
- **chrF** (character F-score — better for morphologically rich languages)
- **Validation loss** (cross-entropy)
- **Training loss**

## Feedback System

- 86 human feedback entries (52 thumbs up, 34 thumbs down, 22 corrections)
- 8-dimension benchmark scoring: Meaning (25%), Grammar (15%), Tense (12%), Vocabulary (12%), Context (10%), Fluency (10%), Orthography (8%), Cultural (8%)
- SQS (Sentence Quality Score) computed per submission
- Auto-sync to GitHub on every submission
- Auto-retrain triggered when 50+ approved corrections accumulate

## Setup

```bash
cd lunyoro-translator/backend
pip install -r requirements.txt
python download_models.py   # downloads models + dataset CSVs from HuggingFace
python build_index.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Repositories

- **Primary**: https://github.com/chriskagenda/TRANSLATOR
- **Mirror**: https://github.com/K227-arch/TRANSLATOR
- **HF Space**: https://huggingface.co/spaces/keithtwesigye/runyoro-translator-api
- **Models**: https://huggingface.co/keithtwesigye
