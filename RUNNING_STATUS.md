# Lunyoro-Rutooro Translator - Running Status

## ✅ Application is Now Running!

### Frontend
- **Status**: ✅ Running
- **Local URL**: http://localhost:3002
- **Network URL**: http://192.168.100.218:3002
- **Configuration**: Using remote HuggingFace Space backend

### Backend
- **Status**: ✅ Running (HuggingFace Space)
- **API URL**: https://keithtwesigye-runyoro-translator-api.hf.space
- **Health Check**: ✅ Healthy
- **Models**: Loaded from HuggingFace Hub automatically

---

## Architecture Overview

### Current Setup
```
┌─────────────────────────────────────┐
│  Frontend (Next.js)                 │
│  http://localhost:3002              │
│  - Translation UI                   │
│  - Dictionary                       │
│  - Chat Assistant                   │
│  - Document Translator              │
│  - Runyoro Editor                   │
└──────────────┬──────────────────────┘
               │
               │ API Calls
               ▼
┌─────────────────────────────────────┐
│  Backend (FastAPI)                  │
│  HuggingFace Space                  │
│  keithtwesigye-runyoro-translator-  │
│  api.hf.space                       │
│  - Translation Engine               │
│  - 4 Neural Models (auto-loaded)   │
│  - Dictionary Lookup                │
│  - Semantic Search                  │
│  - AI Chat (Qwen 2.5 7B)           │
└──────────────┬──────────────────────┘
               │
               │ Model Loading
               ▼
┌─────────────────────────────────────┐
│  HuggingFace Model Hub              │
│  - MarianMT en2lun                  │
│  - MarianMT lun2en                  │
│  - NLLB-200 en2lun                  │
│  - NLLB-200 lun2en                  │
│  - Sentence Transformers            │
└─────────────────────────────────────┘
```

---

## Model Loading Details

### ✅ Models are Automatically Downloaded from HuggingFace

The backend automatically downloads models from HuggingFace Hub on first use:

1. **MarianMT Models** (Fine-tuned for Runyoro-Rutooro)
   - `keithtwesigye/lunyoro-en2lun` - English → Lunyoro
   - `keithtwesigye/lunyoro-lun2en` - Lunyoro → English

2. **NLLB-200 Models** (Meta's multilingual model, fine-tuned)
   - `keithtwesigye/lunyoro-nllb_en2lun` - English → Lunyoro
   - `keithtwesigye/lunyoro-nllb_lun2en` - Lunyoro → English

3. **Semantic Search Model**
   - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

### Model Loading Process
- Models are cached locally after first download (~6 GB total)
- Subsequent requests use cached models (offline mode)
- No manual model setup required

---

## Features Available

### 1. Translation
- ✅ Bidirectional (English ↔ Lunyoro/Rutooro)
- ✅ Dual models (MarianMT + NLLB-200)
- ✅ Context-aware translation
- ✅ Grammar rule post-processing
- ✅ Semantic search fallback

### 2. Dictionary
- ✅ 80,000+ sentence pairs
- ✅ Word lookup with examples
- ✅ Fuzzy matching
- ✅ Neural MT fallback

### 3. AI Chat Assistant
- ✅ Qwen 2.5 7B LLM
- ✅ Grammar rules context
- ✅ Bilingual responses
- ✅ Domain-aware (8 sectors)

### 4. Document Translation
- ✅ PDF, DOCX, TXT support
- ✅ Extractive summarization
- ✅ Sentence-by-sentence translation
- ✅ Grammar rule application

### 5. Runyoro Editor
- ✅ Real-time spellcheck
- ✅ Grammar hints
- ✅ AI grammar review
- ✅ Rich text formatting

### 6. Human Feedback Loop
- ✅ Translation ratings
- ✅ Error categorization
- ✅ Model comparison
- ✅ Continuous improvement

---

## Access the Application

### Open in Browser
1. **Local**: http://localhost:3002
2. **Network**: http://192.168.100.218:3002

### Test the Translation
1. Go to the Translator tab
2. Enter English text: "Hello, how are you?"
3. Click Translate
4. See Lunyoro translation with both MarianMT and NLLB results

### Test the Chat
1. Go to the Chat tab
2. Ask: "How do I say 'thank you' in Runyoro?"
3. Get AI-powered response with grammar context

---

## Configuration Files

### Frontend Environment (.env.local)
```env
NEXT_PUBLIC_API_URL=https://keithtwesigye-runyoro-translator-api.hf.space
```

### Backend Environment (on HF Space)
- Models auto-download from HuggingFace Hub
- CORS configured for frontend access
- Qwen 2.5 7B for chat via HF Router

---

## Why This Setup?

### Problem
- Python 3.14/3.13 on your system
- PyTorch doesn't support Python 3.13+
- Docker not installed

### Solution
- Use deployed HuggingFace Space backend
- Models already loaded and cached
- No local Python/PyTorch setup needed
- Full functionality available immediately

---

## Alternative: Run Backend Locally (Future)

If you want to run the backend locally later:

### Option 1: Install Python 3.12
```bash
# Wait for Python 3.12 installation to complete
cd lunyoro-translator/backend
/usr/local/bin/python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Option 2: Install Docker
```bash
# Install Docker Desktop for Mac
# Then:
cd lunyoro-translator/backend
docker build -t lunyoro-backend .
docker run -p 8000:8000 lunyoro-backend
```

### Option 3: Use Conda
```bash
conda create -n lunyoro python=3.12
conda activate lunyoro
cd lunyoro-translator/backend
pip install -r requirements.txt
python main.py
```

Then update `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Troubleshooting

### Frontend shows connection errors
- Check that backend is accessible: `curl https://keithtwesigye-runyoro-translator-api.hf.space/health`
- Verify `.env.local` exists in frontend directory
- Restart frontend: Stop and run `npm run dev` again

### Translations not working
- Backend may be cold-starting (HF Spaces sleep after inactivity)
- Wait 30-60 seconds for models to load
- Try again

### Chat not responding
- Rate limited to 5 requests per 60 seconds per IP
- Wait a minute and try again

---

## Dataset & Training

### Data Sources
- ~54,000 English-Lunyoro sentence pairs
- Runyoro-Rutooro Dictionary (OCR + manual)
- Bible translations
- Community submissions
- Grammar examples from textbooks

### Models
- Fine-tuned from Helsinki-NLP/opus-mt-en-rw (MarianMT)
- Fine-tuned from facebook/nllb-200-distilled-600M (NLLB)
- Trained on 80k+ pairs with back-translation augmentation

---

## Next Steps

1. ✅ **Test the application** - Open http://localhost:3002
2. ✅ **Try translations** - Test English ↔ Lunyoro
3. ✅ **Explore features** - Dictionary, Chat, Editor
4. 📝 **Provide feedback** - Use thumbs up/down on translations
5. 🔧 **Optional**: Set up local backend when Python 3.12 is ready

---

## Support

- **Documentation**: See README.md in lunyoro-translator/
- **Training Guide**: TRAINING_GUIDE.md
- **Pipeline Guide**: PIPELINE_GUIDE.md
- **HuggingFace Models**: https://huggingface.co/keithtwesigye

---

**Status**: ✅ Fully Operational
**Last Updated**: 2026-05-18
