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
| MarianMT FP32 ONNX (~550 MB × 2) | Loaded from `backend/model/{en,lun}2{lun,en}_onnx/` |

**Inference fidelity:** The NLLB path uses the exact same greedy decode loop as
`verify_pi_models.py` — two ORT sessions (encoder + decoder), no KV cache, no
`decoder_with_past_model.onnx`, sequence cap of 200 tokens. Output should be
token-identical to the real Pi C++ backend.

---

## Prerequisites

1. **Docker Desktop** running on Windows (with Linux containers)
2. **ONNX model files** already exported under `backend/model/`:
   - `nllb_en2lun_int8/` — `encoder_model.onnx`, `decoder_model.onnx` + tokenizer
   - `nllb_lun2en_int8/` — same
   - `en2lun_onnx/` — `encoder_model.onnx`, `decoder_model.onnx` + tokenizer
   - `lun2en_onnx/` — same
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
.\start-pi-sim.ps1 -NllbOnly     # disable Marian, faster boot (~45 s)
.\start-pi-sim.ps1 -NoFrontend   # API-only mode, skip frontend build
.\start-pi-sim.ps1 -Down         # stop and remove containers
```

---

## Testing features

### Core translation (replaces C++ backend)

```powershell
# English → Runyoro (NLLB INT8 greedy + Marian FP32 ONNX beam-search)
Invoke-RestMethod -Uri http://localhost:8090/translate `
  -Method POST -ContentType application/json `
  -Body '{"text":"Good morning, my friend."}'

# Runyoro → English
Invoke-RestMethod -Uri http://localhost:8090/translate-reverse `
  -Method POST -ContentType application/json `
  -Body '{"text":"Webale muno"}'

# Both models + timing benchmark
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

# Offline chat assistant
$body = '{"message":"translate hello"}'
Invoke-RestMethod -Uri http://localhost:8090/chat `
  -Method POST -ContentType application/json -Body $body
```

### UI tabs to test manually

| Tab | What to test | Pi-Sim behaviour |
|---|---|---|
| **Translate** | Type English, hit translate | NLLB INT8 greedy output shown as NLLB badge |
| **Translate** | Swap to Runyoro → English | NLLB + Marian outputs, dual display if they differ |
| **Translate** | Thumbs up/down | Feedback stored in `pisim_history` Docker volume |
| **Translate** | Spellcheck (type Runyoro) | Uses real backend retrieval if index mounted |
| **Camera → OCR** | Upload a text image | Routes through nginx to backend OCR endpoints |
| **Camera → Identify** | Upload a photo | MobileNetV2 via sidecar (if model mounted) |
| **Editor** | Type and translate | Same as Translate tab, full grammar rules panel |
| **Editor → PDF** | Upload a PDF | Sidecar `/summarize-pdf` via nginx |
| **Chat** | Type grammar question | Offline retrieval-based assistant |
| **Dictionary** | Look up a word | Retrieval index (if translation_index.pkl present) |
| **Batch (Editor)** | Upload .csv file | Sidecar `/translate-batch-file` via nginx |

### Known Pi behaviour differences

| Behaviour | Real Pi | Pi-Sim |
|---|---|---|
| NLLB decoding | C++ greedy, 4 threads | Python ORT greedy, same 4-thread config |
| Marian decoding | C++ greedy (no KV cache) | Python optimum beam-search (set `MARIAN_GREEDY=1` to match) |
| Live camera | Not possible (no HTTPS on Pi) | Not possible (same browser constraint on localhost) |
| Chat assistant | Offline retrieval only | Offline retrieval only (no LLM) |
| Image classify | MobileNetV2 on Pi sidecar | MobileNetV2 on pi-sim-sidecar (needs model download) |
| CORS | `horizonx.kathay.tech` etc. | `localhost:3090, localhost:8090` |

---

## Configuration

Environment variables (set in `docker-compose.pi-sim.yml` or override with a `.env` file):

| Variable | Default | Effect |
|---|---|---|
| `NLLB_THREADS` | `4` | ORT intra-op threads for NLLB encoder/decoder |
| `MARIAN_THREADS` | `2` | ORT threads for Marian |
| `MARIAN_GREEDY` | `0` | `1` = use two-session greedy decode for Marian (Pi-exact); `0` = optimum beam-search (higher quality) |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose model loading output |
| `NLLB_INT8_DIR` | `nllb_{d}_int8` | Directory template for NLLB INT8 models |
| `NLLB_ONNX_DIR` | `nllb_{d}_onnx` | Fallback FP32 ONNX directory |
| `MARIAN_ONNX_DIR` | `{d}_onnx` | MarianMT ONNX directory template |

### Enabling Marian greedy mode (Pi-exact)

Set `MARIAN_GREEDY=1` in the backend environment to match the C++ greedy decode path for Marian too — outputs will be identical to what the Pi produces but slightly lower quality than beam-search:

```yaml
# in docker-compose.pi-sim.yml under pi-sim-backend environment:
MARIAN_GREEDY: "1"
```

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
| Marian en→lun | ~550 MB | FP32 ONNX |
| Marian lun→en | ~550 MB | FP32 ONNX |
| Semantic search (retrieval) | ~90 MB | Safetensors |
| **Total** | **~3.6 GB** | — |

This matches the real Pi 5 (8 GB) steady-state footprint. The `mem_limit: 8g`
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
- Reduce input length or use beam-search (the Marian path is faster).

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
