# Pi Sidecar Service

Lightweight Python FastAPI service that runs alongside the C++ translator on the Raspberry Pi, implementing the 5 endpoints the C++ backend doesn't support.

## Endpoints Added

| Endpoint | Description |
|----------|-------------|
| `POST /classify-image` | Image classification (MobileNetV2) + label translation |
| `GET /classify-image/status` | Classifier readiness check |
| `POST /translate-batch` | Bulk translate up to 100 sentences |
| `POST /translate-batch-file` | Upload CSV/TXT, translate each line |
| `POST /summarize-pdf` | Extract + summarize PDF/DOCX/TXT, translate to Lunyoro (returns per-model outputs: `summary_lunyoro`, `summary_lunyoro_nllb`, `summary_lunyoro_marian`) |
| `POST /chat` | Offline retrieval-based chat assistant (no LLM required) |
| `GET /language-rules` | Full Runyoro grammar data (noun classes, tenses, etc.) |
| `GET /language-rules/interjections` | Interjections only |
| `GET /language-rules/idioms` | Idioms only |
| `GET /language-rules/proverbs` | Proverbs with random selection |
| `POST /language-rules/apply` | Apply grammar rules programmatically |

### Chat Endpoint Details

`POST /chat` provides a fully offline language assistant using pattern-matching and retrieval from `language_rules_data.py` — no LLM or internet connection needed.

**Request body:**
```json
{
  "message": "tell me about noun classes",
  "history": [],
  "sector": null,
  "conversation_mode": false
}
```

**Supported topics:**
- Translation requests (checked first — proxied to C++ backend)
- Greetings and introductions

Translation matching is prioritised over greetings so that inputs like "translate hi" or "what is hello" are routed to the translation pipeline rather than the greeting response.

**Response schema:**
```json
{
  "reply": "...",
  "reply_marian": null,
  "reply_nllb": null
}
```

## Architecture

```
Phone/Browser
     │
     ▼ (port 80)
   Nginx
     ├── /classify-image, /translate-batch, /summarize-pdf, /language-rules, /chat
     │         ▼
     │   Python Sidecar (port 8001)
     │         │ proxies translate calls to ──▶ C++ Backend (port 8080)
     │
     └── everything else
              ▼
        C++ Backend (port 8080)
```

## Resource Budget

- MobileNetV2: ~14MB model weights + ~50MB runtime
- pdfplumber: ~30MB peak during PDF extraction
- Total steady-state: ~150-200MB additional RAM
- Pi has ~4GB free after C++ backend loads — plenty of headroom

## Deployment

```bash
./deploy.sh 192.168.4.1
```

Then follow the manual steps printed at the end (need sudo on the Pi).

## Local Development

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python download_model.py
uvicorn app:app --port 8001 --reload
```
