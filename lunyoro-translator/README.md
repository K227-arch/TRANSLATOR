# Lunyoro-Rutooro Translator

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
- **Dual neural models:** MarianMT (primary) + NLLB-200 (comparison)
- **Context-aware:** Uses previous sentence for better coherence
- **Grammar rules:** Automatic R/L rule, apostrophe elision, nasal assimilation
- **Fallback chain:** Neural MT → Semantic search → Dictionary lookup
- **Spellcheck:** Real-time Lunyoro spellcheck with suggestions

### Chat Assistant
- **LLM-powered:** Qwen 2.5 7B via HuggingFace Router
- **Domain-aware:** Sector-specific vocabulary (medical, agriculture, education, etc.)
- **Bilingual output:** Replies in English + Lunyoro (MarianMT + NLLB)
- **Grammar context:** Full Runyoro-Rutooro grammar rules in system prompt

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
python download_models.py  # Downloads models from HuggingFace (~2GB)
python main.py
# → http://localhost:8000
```

---

## Model Improvement Pipeline

See **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** for full details.

### 1. Clean Training Data
```bash
python backend/clean_training_data.py
# Removes 13,899 noisy rows (domain tags, OCR garbage, duplicates)
# 80,733 → 66,834 clean pairs
```

### 2. Back-Translation (Data Augmentation)
```bash
python backend/back_translate.py --max 5000 --bleu-threshold 0.25
# Generates 2,000-3,000 synthetic pairs via round-trip translation
python backend/merge_back_translated.py
```

### 3. Retrain Tokenizer (Better OOV Handling)
```bash
python backend/retrain_tokenizer.py --vocab-size 65000 --direction both
# Expands vocab from 64k → 65k tokens with subword regularization
```

### 4. Fine-Tune Models
```bash
python backend/train_marian.py --direction both --epochs 5 --resize-embeddings
# Features:
#   - Subword regularization (SPM sampling, alpha=0.1)
#   - Longer context window (prepends previous sentence)
#   - Mixed precision (fp16) on GPU
#   - BLEU-based checkpoint selection
```

### 5. Retrain from Human Feedback
```bash
python backend/retrain_from_feedback.py --epochs 5 --push
# Exports thumbs-up pairs → merges into train.csv → fine-tunes → pushes to HF
```

**Expected improvements:** +5-10 BLEU after full pipeline

---

## Project Structure

```
lunyoro-translator/
├── backend/
│   ├── main.py                      # FastAPI server
│   ├── translate.py                 # Translation logic (MT + retrieval)
│   ├── language_rules.py            # Runyoro grammar rules (3200+ lines)
│   ├── clean_training_data.py       # Data cleaning script
│   ├── back_translate.py            # Back-translation augmentation
│   ├── retrain_tokenizer.py         # SentencePiece retraining
│   ├── train_marian.py              # MarianMT fine-tuning
│   ├── feedback_store.py            # Human feedback storage
│   ├── retrain_from_feedback.py     # End-to-end feedback retraining
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
│       │   └── test.csv             # 4.5k test pairs
│       ├── cleaned/                 # Cleaned dictionary/corpus
│       └── raw/                     # Raw seed vocabulary
├── frontend/
│   ├── components/Translator.tsx    # Main translation UI
│   ├── components/Chat.tsx          # Chat assistant UI
│   └── app/                         # Next.js app router
├── TRAINING_GUIDE.md                # Model improvement guide
└── PIPELINE_GUIDE.md                # Data pipeline guide
```

---

## API Endpoints

### Translation
- `POST /translate` — English → Lunyoro
- `POST /translate-reverse` — Lunyoro → English
- `POST /lookup` — Dictionary word lookup
- `POST /spellcheck` — Lunyoro spellcheck

### Chat
- `POST /chat` — AI language assistant (Qwen 2.5 7B)

### Feedback
- `POST /feedback` — Submit translation rating with optional error categorization and corrections
  - Parameters: `source_text`, `translation`, `direction`, `rating` (1/-1), `correction` (optional), `error_type` (optional - comma-separated list for multiple error types)
- `GET /feedback/stats` — Feedback statistics
- `GET /feedback/export` — Export approved pairs

### Utilities
- `POST /summarize-pdf` — Extract + translate + summarize documents
- `GET /language-rules` — Full grammar rules JSON
- `POST /language-rules/apply` — Apply specific grammar rule
- `GET /history` — Translation history
- `GET /health` — Health check

---

## Models

All models hosted on HuggingFace:

- **MarianMT en2lun:** [keithtwesigye/lunyoro-en2lun](https://huggingface.co/keithtwesigye/lunyoro-en2lun)
- **MarianMT lun2en:** [keithtwesigye/lunyoro-lun2en](https://huggingface.co/keithtwesigye/lunyoro-lun2en)
- **NLLB en2lun:** [keithtwesigye/lunyoro-nllb_en2lun](https://huggingface.co/keithtwesigye/lunyoro-nllb_en2lun)
- **NLLB lun2en:** [keithtwesigye/lunyoro-nllb_lun2en](https://huggingface.co/keithtwesigye/lunyoro-nllb_lun2en)
- **Semantic search:** [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- **Chat:** [Qwen/Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) via HF Router

---

## Grammar Rules

Comprehensive Runyoro-Rutooro grammar implementation (3200+ lines):

- **R/L Rule:** L → R except adjacent to e/i
- **Nasal assimilation:** nb→mb, np→mp, nr→nd, nl→nd
- **Apostrophe elision:** na ente → n'ente, habwa okugonza → habw'okugonza
- **Consonant+suffix mutations:** r/t/j + -ire → z/s/z + -ire
- **Noun class system:** 15 classes with concordial agreement
- **Verb conjugation:** 10+ tenses, derivative suffixes (causative, passive, etc.)
- **Pronominal system:** Subject/object concords, demonstratives, possessives
- **Numbers & ordinals:** Cardinals 1-1M, ordinal formation rules
- **Particles:** Genitive, copula, conditional, coordinating

See `backend/language_rules.py` for full implementation.

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

### HuggingFace Space (Backend)
```bash
python backend/push_to_hf_space.py
# Pushes to: keithtwesigye-runyoro-translator-api.hf.space
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
HF_TOKEN=hf_...                    # HuggingFace API token (read access)
HF_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
CORS_ORIGINS=http://localhost:3002,https://frontend-six-phi-25.vercel.app
TRANSFORMERS_OFFLINE=1             # Force offline mode
FEEDBACK_FILE=feedback.jsonl       # Feedback storage path
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
