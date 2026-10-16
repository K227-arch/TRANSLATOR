# Lunyoro Translator — Colab Backend

Runs the full FastAPI backend on a **free Google Colab GPU (T4)**.
Models load from **HuggingFace Hub**. A public HTTPS URL is created automatically
via **Cloudflare Tunnel** (built into Colab — no account or token needed).

The **Cloudflare Worker** (`cloudflare-worker/`) acts as the permanent API gateway.
When the notebook starts it calls `POST /update-colab-url` on the Worker to register
its tunnel URL — no Vercel environment variable update is needed.

## Architecture

```
Browser / Phone
    └─ Vercel frontend (horizonx.kathay.tech)
           NEXT_PUBLIC_API_URL = Cloudflare Worker (permanent URL)
                └─ Cloudflare Worker  (routes each request)
                       │
                       ├─ Colab T4  https://xxxx.trycloudflare.com  (priority 1 — live probe)
                       │       └─ FastAPI  port 7860  (this notebook)
                       │              ├─ POST /translate          ─┐
                       │              ├─ POST /translate-reverse    │  NLLB-200 FP32 GPU
                       │              ├─ POST /translate-batch      │
                       │              ├─ POST /translate-batch-file ┘
                       │              ├─ POST /classify-image     ─┐  MobileNetV2
                       │              ├─ POST /ocr-translate        │  + EasyOCR
                       │              ├─ POST /ocr-translate-base64 ┘  + NLLB
                       │              ├─ POST /chat               HF Router (Llama/Qwen)
                       │              └─ GET  /health  /system-info  /history  /config …
                       │
                       └─ HF Space  (permanent fallback when no live Colab session)
                              keithtwesigye-runyoro-translator-api.hf.space

                              HuggingFace Hub (model weights)
                                keithtwesigye/lunyoro-nllb-en2lun  (~2.3 GB)
                                keithtwesigye/lunyoro-nllb-lun2en  (~2.3 GB)
                                google/mobilenet_v2_1.0_224         (~14 MB)
```

## How to use

### 1 — Open the notebook

Upload `lunyoro_backend.ipynb` to [colab.research.google.com](https://colab.research.google.com),
or click the badge below if the repo is public:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/chriskagenda/TRANSLATOR/blob/main/lunyoro-translator/colab/lunyoro_backend.ipynb)

### 2 — Set GPU runtime

`Runtime → Change runtime type → T4 GPU`

### 3 — Set your HF token (Cell 1)

```python
HF_TOKEN = "hf_..."   # https://huggingface.co/settings/tokens
```

The token is needed to:
- Load the fine-tuned NLLB models from `keithtwesigye/` (private or rate-limited)
- Call the HF Inference Router for Qwen refinement and chat

### 4 — Run All

`Runtime → Run all`

Model loading takes ~3 minutes on the first run (downloads ~4.6 GB).
Subsequent runs reuse the Colab cache and load in ~30 seconds.

### 5 — Copy the public URL

Cell 7 prints:
```
============================================================
  Backend is LIVE at:
  https://abc12345.trycloudflare.com
============================================================
```

The notebook automatically calls `POST /update-colab-url` on the Cloudflare Worker
to register this URL. The Worker will start routing requests to Colab (verified via a
live probe) instead of the HF Space — no manual Vercel update needed.

To verify the Worker picked it up:
```bash
curl https://<your-worker>.workers.dev/colab-status
# → { "colab_url": "https://abc12345.trycloudflare.com", "has_colab": true }
```

### 6 — Nothing else to do

The Cloudflare Worker handles routing automatically. When the Colab session ends
(or the notebook is idle long enough for the tunnel to close), the Worker's liveness
probe fails and it falls back to the HF Space on the next request.

## Switching back to HF Space

When the Colab session ends the Worker automatically falls back to the HF Space
on the next request (the liveness probe to Colab times out within 4 seconds).
No manual action is needed.

## Automated launch via colab_manager.py

Instead of the manual steps above, you can launch and manage the Colab backend directly from your local machine using `colab_manager.py`. It handles Drive upload, session execution, URL polling, and `.env` wiring automatically.

### One-time Google OAuth setup

Before using `colab_manager.py`, run `colab_auth_setup.py` once to authenticate with Google:

```bash
# Download an OAuth client JSON from Google Cloud Console first:
# 1. https://console.cloud.google.com/apis/credentials
# 2. Enable Google Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com
# 3. Create credentials → OAuth client ID → Desktop app → Download JSON

python colab_auth_setup.py --client-json "C:\path\to\client_secret.json"
```

The script opens a browser for the Google sign-in, then caches the token at
`~/.lunyoro_colab_credentials.json` (valid ~6 months). Subsequent runs reuse the cached token automatically.

**Flags:**

| Flag | Description |
|------|-------------|
| `--client-json PATH` | Path to the OAuth client JSON. Copied to `~/.lunyoro_colab_oauth_client.json` and reused on future runs. |
| `--check` | Check if credentials are valid without re-authenticating (exits 1 if no valid token found). |

### Launch the backend

```bash
python colab_manager.py              # start Colab and wire COLAB_URL into backend/.env
python colab_manager.py --status     # show last known URL + health check
python colab_manager.py --url-only   # print last known URL from colab_config.json
```

---

## Notes

- The Cloudflare URL **changes each time** the notebook is restarted, but the notebook
  registers the new URL automatically via `POST /update-colab-url` — no manual step needed.
- Free Colab sessions run for up to **12 hours** on GPU, ~90 min idle.
- No ngrok, no Pi, no local server needed.

## What runs vs what doesn't

| Feature | Colab backend | HF Space (`app.py`) |
|---|---|---|
| Translation (NLLB FP32 GPU) | ✅ fast (~0.5 s) | ✅ slow (~5-15 s CPU) |
| Lens — Identify | ✅ MobileNetV2 | ✅ |
| Lens — OCR | ✅ EasyOCR | ✅ |
| Chat | ✅ HF Router + NLLB | ❌ no /chat |
| Batch translate | ✅ | ❌ |
| Dictionary lookup | ✅ NLLB fallback | ❌ |
| Spell check | ❌ stub | ❌ |
| PDF summarize | ❌ returns 501 | ❌ |
