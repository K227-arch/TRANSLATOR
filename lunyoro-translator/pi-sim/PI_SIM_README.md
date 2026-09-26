# Pi-Sim — Raspberry Pi 5 AI Stick Virtual Environment

A full Docker-based simulation of the AI Stick (Raspberry Pi 5) that runs the
actual ONNX INT8 / FP32 quantized models and exposes the same API surface as
the device's C++ backend — so every UI feature can be tested on your Windows
development machine before deploying to the physical Pi.

---

## What it simulates

| Real Pi component | Pi-Sim equivalent |
|---|---|
| C++ `translator_v2` binary (port 8080) | `pi-sim-backend` — Python ORT, greedy decode |
| Python sidecar (port 8001) | `pi-sim-sidecar` — identical `app.py` |
| Nginx reverse proxy (port 80) | `pi-sim-nginx` — same routing rules |
| Static Next.js frontend | `pi-sim-frontend` — same Docker build |
| NLLB-200 INT8 ONNX (~1.19 GB × 2) | Loaded from `backend/model/nllb_*_int8/` |

> **MarianMT removed (v2.0.0).** The pi-sim backend now runs NLLB-200 only.
> `translation_marian` is always `null` in API responses. The `/system-info`
> endpoint reports `marian_onnx: false` and `marian_mode: "disabled"`.

**Inference fidelity:** The NLLB path uses the exact same greedy decode loop as
`verify_pi_models.py` — two ORT sessions (encoder + decoder), no KV cache, no
`decoder_with_past_model.onnx`, sequence cap of 200 tokens. Output should be
token-identical to the real Pi C++ backend.

**en→lun input normalisation:** Before the English source is fed to NLLB, two
lightweight fixes run to match the casing and punctuation patterns the model
was fine-tuned on:
1. **Sentence-casing** — the first character is uppercased if it isn't already
   (e.g. `"how are you"` → `"How are you"`). All-lowercase input produces
   wrong-language output (`"muli kurungi"`) because it doesn't match any seen
   training pattern.
2. **Question-mark injection** — if the input starts with a question word
   (`how`, `what`, `where`, `when`, `who`, `why`, `which`, `is `, `are `,
   `do `, `does `, `can `, `will `, `have `) and has no terminal punctuation,
   a `?` is appended (e.g. `"How are you"` → `"How are you?"`).

These steps run inside `_nllb_translate()` in `pi-sim/backend/app.py`.

---

## Prerequisites

1. **Docker Desktop** running on Windows (with Linux containers)
2. **ONNX model files** already exported under `backend/model/`:
   - `nllb_en2lun_int8/` — `encoder_model.onnx`, `decoder_model.onnx` + tokenizer
   - `nllb_lun2en_int8/` — same
3. **Translation index** `backend/model/translation_index.pkl` (for retrieval/spellcheck)

### Export models if not already done

```powershell
cd lunyoro-translator\backend

# 1. Export PyTorch → ONNX FP32
python export_onnx_all.py

# 2. Quantize NLLB → INT8 (required for Pi-sim — ~1.19 GB each, was ~6.8 GB)
python export_onnx_int8.py

# 3. Verify output against the C++ greedy path
python verify_pi_models.py --all

# 4. Build the retrieval index (for spellcheck + RAG)
python build_index.py
```

---

## Quick Start

```powershell
cd lunyoro-translator\pi-sim

# First run — builds images (takes 5-10 minutes, downloads deps)
.\start-pi-sim.ps1 -Build

# Subsequent runs
.\start-pi-sim.ps1
```

The script:
- Checks all required model directories and files exist
- Builds Docker images if `–Build` is passed
- Waits up to 150 s for the backend to load models (NLLB INT8 takes ~60–90 s)
- Runs a live translation probe (`Good morning, my friend.` → Runyoro)
- Prints all service URLs

### Access

| URL | What it is |
|---|---|
| http://localhost:3090 | **Full UI** — identical to what runs on the Pi |
| http://localhost:8090 | API via nginx (same routing as Pi port 80) |
| http://localhost:8080 | Backend direct (bypass nginx) |
| http://localhost:8080/docs | FastAPI Swagger UI — all endpoints documented |
| http://localhost:8080/benchmark | Built-in probe suite with timings |
| http://localhost:8001 | Sidecar direct |

### Stop

```powershell
.\start-pi-sim.ps1 -Down
```

---

## Startup options

```powershell
.\start-pi-sim.ps1 -Build        # force rebuild Docker images
.\start-pi-sim.ps1 -Logs         # tail logs after starting
.\start-pi-sim.ps1 -NllbOnly     # NLLB-only mode (default; Marian is already removed)
.\start-pi-sim.ps1 -NoFrontend   # API-only mode, skip frontend build
.\start-pi-sim.ps1 -Down         # stop and remove containers
```

---

## Testing features

### Core translation (replaces C++ backend)

```powershell
# English → Runyoro (NLLB INT8 greedy)
Invoke-RestMethod -Uri http://localhost:8090/translate `
  -Method POST -ContentType application/json `
  -Body '{"text":"Good morning, my friend."}'

# Runyoro → English
Invoke-RestMethod -Uri http://localhost:8090/translate-reverse `
  -Method POST -ContentType application/json `
  -Body '{"text":"Webale muno"}'

# NLLB timing benchmark
Invoke-RestMethod -Uri http://localhost:8080/benchmark

# Model status
Invoke-RestMethod -Uri http://localhost:8080/system-info
```

Expected results matching the real Pi:
- `Good morning, my friend.` → `Oraire ota mugenziwe.` (NLLB)
- `Webale muno` → `Thank you very much` (NLLB)

### Sidecar features

```powershell
# Batch translation (10 sentences)
$body = '{"sentences":["Hello","Thank you","Good morning"],"direction":"en->lun"}'
Invoke-RestMethod -Uri http://localhost:8090/translate-batch `
  -Method POST -ContentType application/json -Body $body

# Language rules
Invoke-RestMethod -Uri http://localhost:8090/language-rules

# Random proverb
Invoke-RestMethod -Uri http://localhost:8090/language-rules/proverbs

# Offline chat assistant — translation
$body = '{"message":"translate good morning"}'
Invoke-RestMethod -Uri http://localhost:8090/chat `
  -Method POST -ContentType application/json -Body $body

# Offline chat — grammar topics
$body = '{"message":"noun classes"}'
Invoke-RestMethod -Uri http://localhost:8090/chat `
  -Method POST -ContentType application/json -Body $body

$body = '{"message":"proverb"}'
Invoke-RestMethod -Uri http://localhost:8090/chat `
  -Method POST -ContentType application/json -Body $body
```

#### Sidecar `/chat` topic coverage

The sidecar chat assistant (`pi-sim/sidecar/app.py`) handles quick-chip topics directly and routes all other messages through an Ollama LLM + NLLB translation pipeline.

**Quick-chip topics (handled inline, no LLM)**

| Trigger | Response |
|---|---|
| `"food"`, `"greetings"`, `"directions"`, `"emergency"`, `"numbers"` chip phrases — matched when the topic name appears in quotes **or** alongside `phrases`, `words`, `vocabulary`, or `say` | Returns a curated English vocabulary/phrase list that is then translated to Runyoro sentence-by-sentence via `_translate_to_runyoro()`. These are matched **before** the LLM branch so chip-button taps (e.g. *How do I say "food" phrases in Runyoro-Rutooro?*) always get a structured vocabulary reply. |

**Rule-based shortcuts (handled inline, before LLM)**

| Trigger keywords | Response |
|---|---|
| `translate`, `how do you say`, `how do i say`, `how to say`, `say ` — **or** `what is` when the message does *not* contain a culture/grammar keyword (`empaako`, `rl rule`, `noun class`, `runyoro`, `proverb`, `tense`, `interjection`, `idiom`, `conjunction`, `preposition`, `pronoun`) | Forwards extracted text to the C++ backend `/translate`; applies `_sentence_case()` normalisation before forwarding so NLLB sees properly-cased input. |
| `hello`, `hi`, `hey`, `agandi`, `oraire ota`, `oirirwe`, `good morning/evening/afternoon/night` | Common Runyoro greetings with translations |
| `rl rule`, `r/l`, `l rule`, `r rule` | R/L rule explanation with an example |
| `empaako`, `honorific`, `tooro name` | First 8 entries from the `EMPAAKO` dict |
| `proverb`, `enfumo`, `saying` | Random entry from the `PROVERBS` list |
| `noun class`, `omuntu`, `noun` | First 5 entries from `NOUN_CLASSES` dict |
| `tense`, `past tense`, `future`, `present tense` | First 6 entries from `TENSES` dict |
| `number`, `count`, `namba`, `counting`, `one`, `two`, `three`, `emu`, `ibiri` | First 15 entries from `NUMBERS` |
| `interjection`, `expression`, `exclamation`, `mawe`, `bambi`, `weebale` | First 10 entries from `INTERJECTIONS` dict |
| `idiom` | First 6 entries from `IDIOMS` dict |
| `conjunction` | First 8 entries from `CONJUNCTIONS` dict |
| `preposition` | First 8 entries from `PREPOSITIONS` dict |
| `pronoun` | First 10 entries from `PERSONAL_PRONOUNS` dict |

**Default handler — Ollama LLM + NLLB translation**

All messages that don't match a keyword above are processed in two stages:

1. **`_ollama_chat(message, history)`** — sends the message to Ollama (model `OLLAMA_MODEL`, default `qwen2.5:1.5b`) at `OLLAMA_URL/api/chat` with `stream: false` and a 30-second timeout. The `SYSTEM_PROMPT` instructs the model to reply in clear, simple English (2–4 sentences), provide short vocabulary lists for phrase requests, and produce no Runyoro words itself — making its output a clean translation target. Up to the last 4 conversation turns from `req.history` are prepended as context. After receiving a reply, `_is_english_reply()` checks that the response is actually English; if the model has replied in another language (e.g. Swahili or Runyoro — a known failure mode of `qwen2.5:1.5b` on short greetings), the reply is discarded and an empty string is returned instead.

2. **`_translate_to_runyoro(english_reply)`** — splits the English reply on sentence-terminal punctuation (`[.!?]`) and translates each sentence via `POST /translate` on the C++ backend. `_sentence_case()` is applied to each sentence before the call. Preferred field order: `translation_nllb` → `translation` → original sentence as fallback.

If Ollama is unavailable, returns a non-200 status, or replies in a non-English language, `_ollama_chat()` returns an empty string and the handler substitutes a static help message that is still translated to Runyoro before returning.

**Response format (all paths)**

```json
{
  "reply": "<Runyoro reply>\n\n(English: <English reply>)",
  "reply_nllb": "<Runyoro reply>",
  "reply_marian": null
}
```

**Environment variables**

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Base URL of the Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Ollama model name to use for chat |

**Input normalisation for chat-triggered translations:** When the `/chat` endpoint forwards a translation request to the backend, the extracted text is passed through `_sentence_case()` before the HTTP call. This mirrors the normalisation applied inside `_nllb_translate()` in the backend so the NLLB INT8 model (which uses the `run_Latn` token) receives correctly-formed input:
1. First character is uppercased if it isn't already.
2. A question mark is appended when the input starts with a question word and has no terminal punctuation; otherwise a period is appended (unless the last character is a digit).

The response always includes `reply_nllb` (the NLLB translation string or `null`) and `reply_marian` (always `null` in Pi-Sim, since MarianMT is removed).

### UI tabs to test manually

| Tab | What to test | Pi-Sim behaviour |
|---|---|---|
| **Translate** | Type English, hit translate | NLLB INT8 greedy output shown as NLLB badge |
| **Translate** | Swap to Runyoro → English | NLLB output; `translation_marian` is always null |
| **Translate** | Thumbs up/down | Feedback stored in `pisim_history` Docker volume |
| **Translate** | Spellcheck (type Runyoro) | Uses real backend retrieval if index mounted |
| **Camera → OCR** | Upload a text image | Routes through nginx to backend OCR endpoints |
| **Camera → Identify** | Upload a photo | MobileNetV2 via sidecar (if model mounted) |
| **Editor** | Type and translate | Same as Translate tab, full grammar rules panel |
| **Editor → PDF** | Upload a PDF | Sidecar `/summarize-pdf` via nginx |
| **Chat** | Type `translate good morning`, `noun classes`, `proverb`, `tenses`, `numbers`, `empaako`, `pronouns`, `idioms` | Offline rule-based assistant; no LLM — see topic coverage table above |
| **Dictionary** | Look up a word | Retrieval index (if translation_index.pkl present) |
| **Batch (Editor)** | Upload .csv file | Sidecar `/translate-batch-file` via nginx |

### Known Pi behaviour differences

| Behaviour | Real Pi | Pi-Sim |
|---|---|---|
| NLLB decoding | C++ greedy, 4 threads | Python ORT greedy, same 4-thread config |
| Marian decoding | C++ greedy (no KV cache) | **Removed** — Marian is not loaded; `translation_marian` is always `null` |
| Live camera | Not possible (no HTTPS on Pi) | Not possible (same browser constraint on localhost) |
| Chat assistant | Offline retrieval only | Ollama LLM (`qwen2.5:1.5b`) → NLLB translation pipeline for general messages; rule-based shortcuts for greetings/grammar/chip topics (see `/chat` topic table) |
| Image classify | MobileNetV2 on Pi sidecar | MobileNetV2 on pi-sim-sidecar (needs model download) |
| CORS | `horizonx.kathay.tech` etc. | `localhost:3090, localhost:8090` |

---

## Configuration

Environment variables (set in `docker-compose.pi-sim.yml` or override with a `.env` file):

| Variable | Default | Effect |
|---|---|---|
| `NLLB_THREADS` | `4` | ORT intra-op threads for NLLB encoder/decoder |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose model loading output |
| `NLLB_INT8_DIR` | `nllb_{d}_int8` | Directory name template for NLLB INT8 models (`{d}` = `en2lun` / `lun2en`) |
| `NLLB_ONNX_DIR` | `nllb_{d}_onnx` | Fallback FP32 ONNX directory template |
| `CORS_ORIGINS` | `localhost:3090,localhost:3002,...` | Comma-separated allowed origins |
| `HISTORY_FILE` | `/tmp/pisim/history.json` | Path for translation/feedback history |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama server base URL used by `_ollama_chat()` in the sidecar `/chat` default handler |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Ollama model tag passed to `POST /api/chat`; swap to any model served by your Ollama instance |

> `MARIAN_THREADS`, `MARIAN_GREEDY`, and `MARIAN_ONNX_DIR` have been removed. Setting them has no effect.

### MobileNetV2 for /classify-image

The Identify tab needs MobileNetV2. Mount it into the sidecar:

```powershell
# Download the model files into pi-sim/sidecar/models/mobilenet_v2/
# (or point the volume to your existing model directory)
# Then rebuild the sidecar image:
docker compose -f docker-compose.pi-sim.yml build pi-sim-sidecar
docker compose -f docker-compose.pi-sim.yml up -d pi-sim-sidecar
```

---

## Memory budget

| Model | Size | Format |
|---|---|---|
| NLLB en→lun | ~1.19 GB | INT8 ONNX |
| NLLB lun→en | ~1.19 GB | INT8 ONNX |
| Semantic search (retrieval) | ~90 MB | Safetensors |
| **Total** | **~2.5 GB** | — |

This is well within the real Pi 5 (8 GB) footprint. The `mem_limit: 8g`
in docker-compose.pi-sim.yml enforces the same cap.

---

## File layout

```
pi-sim/
├── backend/
│   ├── app.py            ← Pi-sim backend (Python ORT greedy inference)
│   ├── Dockerfile
│   └── requirements.txt
├── sidecar/
│   ├── app.py            ← Pi sidecar (batch/PDF/classify/chat/language-rules)
│   ├── language_rules_data.py  ← bundled grammar data (copied from pi-sidecar/)
│   ├── Dockerfile
│   └── requirements.txt
├── nginx/
│   └── nginx.conf        ← mirrors pi-sidecar/nginx-translator.conf exactly
├── docker-compose.pi-sim.yml
├── start-pi-sim.ps1      ← Windows launcher with pre-flight checks
└── PI_SIM_README.md      ← this file
```

---

## Troubleshooting

**Backend exits immediately on startup**
- Check logs: `docker compose -f docker-compose.pi-sim.yml logs pi-sim-backend`
- Most common cause: ONNX model file missing or corrupt. Re-run `export_onnx_int8.py`.

**Translations are very slow (> 60 s per sentence)**
- NLLB greedy decode on CPU is O(n²) in sequence length. For long inputs, NLLB
  on a modern x86 CPU takes 5–30 s. This is expected — the Pi takes 10–60 s.
- Reduce input length or break the sentence into shorter chunks.

**`Could not import translate.py`**
- The backend volume `../backend:/backend:ro` must be correct relative to the
  `docker-compose.pi-sim.yml` file location. Run from inside `pi-sim/`.

**Frontend can't reach API**
- The frontend is built with `NEXT_PUBLIC_API_URL=http://localhost:8090`.
  Make sure you access the UI at **http://localhost:3090** (not 3002).
  The browser sends API requests to localhost:8090 (nginx), not inside Docker.

**Sidecar `/classify-image` returns 503**
- MobileNetV2 model not mounted. See "MobileNetV2 for /classify-image" above.

**Spellcheck / dictionary returns empty**
- `translation_index.pkl` must exist in `backend/model/`. Run `python build_index.py`.
