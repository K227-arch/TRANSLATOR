# Lunyoro-Rutooro Translator

**Version 2.0** - Enhanced Feedback & Model Comparison

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
- **HuggingFace Hub integration:** Models loaded automatically from HF Hub on first use and cached locally
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
# Builds semantic search index from cleaned dictionary data
# Loads word_entries_clean.csv and rutooro_dictionary_clean.csv
# Creates model/translation_index.pkl for retrieval fallback
```

### 2. Clean Training Data
```bash
python backend/clean_training_data.py
# Removes 13,899 noisy rows (domain tags, OCR garbage, duplicates)
# 80,733 → 66,834 clean pairs
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
#   - BLEU-based checkpoint selection
```

### 6. Upload Models to HuggingFace Hub
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

### 7. Retrain from Human Feedback
```bash
python backend/retrain_from_feedback.py --epochs 5 --push
# Exports thumbs-up pairs → merges into train.csv → fine-tunes → pushes to HF
```

### 8. Automated Retraining (Background Service)
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

**Features:**
- Monitors `feedback.jsonl` for approved pairs
- Auto-cleans and validates feedback (length, repetition, language detection)
- Triggers retraining when 100+ new clean pairs collected (configurable via `--threshold`)
- Runs as background service or scheduled task
- Logs to `auto_retrain.log`

**Expected improvements:** +5-10 BLEU after full pipeline

---

## Project Structure

```
lunyoro-translator/
├── backend/
│   ├── main.py                      # FastAPI server
│   ├── translate.py                 # Translation logic (MT + retrieval)
│   ├── language_rules.py            # Runyoro grammar rules (3200+ lines)
│   ├── build_index.py               # Build semantic search index from dictionary
│   ├── clean_training_data.py       # Data cleaning script
│   ├── back_translate.py            # Back-translation augmentation
│   ├── retrain_tokenizer.py         # SentencePiece retraining
│   ├── train_marian.py              # MarianMT fine-tuning
│   ├── upload_models_to_hf.py       # Upload models to HuggingFace Hub
│   ├── feedback_store.py            # Human feedback storage + auto-export
│   ├── retrain_from_feedback.py     # End-to-end feedback retraining
│   ├── auto_retrain.py              # Automated retraining service
│   ├── view_analytics.py            # View feedback analytics in terminal
│   ├── export_analytics.py          # Export analytics to Excel/CSV
│   ├── feedback/                    # Auto-exported feedback files
│   │   ├── all_feedback.csv         # Raw feedback data (auto-updated)
│   │   └── feedback_analytics.xlsx  # Multi-sheet analytics (auto-updated)
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
  - Parameters: `source_text`, `translation`, `direction`, `rating` (1/-1), `correction` (optional), `error_type` (optional - comma-separated list for multiple error types), `model_used` (optional - "marian", "nllb", "both", "none")
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
- `feedback_analytics.xlsx` — Excel workbook with 5 sheets:
  - **All Feedback:** Complete feedback log with readable labels
  - **Summary:** Total feedback, approval rates, unique users
  - **Model Usage:** Usage statistics by model (MarianMT, NLLB-200, both, none)
  - **Error Types:** Breakdown of reported error categories
  - **Daily Activity:** Feedback timeline by date
- `approved_pairs.csv` — Approved (thumbs-up) translation pairs ready for retraining (exported via `/feedback/export` endpoint)

**On-demand reports** (via `export_analytics.py`):
- **Summary Statistics:** Total feedback, approval rates, correction rates, unique users
- **Model Performance:** MarianMT vs NLLB-200 comparison with winner determination
- **Error Analysis:** Breakdown of error types (grammar, spelling, context, vocabulary, etc.)
- **Direction Statistics:** Performance by translation direction (en→lun vs lun→en)
- **Daily Activity:** Feedback timeline with day-of-week analysis
- **User Engagement:** Anonymized user activity and engagement scores
- **Raw Feedback Data:** Complete feedback log with all fields

### Utilities
- `POST /summarize-pdf` — Extract + translate + summarize documents
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

### v2.0 - Enhanced Feedback & Model Comparison (Current)
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
