# Lunyoro Translator — Colab Backend

Runs the full FastAPI backend on a **free Google Colab GPU (T4)**.
Models load from **HuggingFace Hub**. A public HTTPS URL is created automatically
via **Cloudflare Tunnel** (built into Colab — no account or token needed).
The **Vercel frontend** at `horizonx.kathay.tech` points at that URL.

## Architecture

```
Browser / Phone
    └─ Vercel  (horizonx.kathay.tech)
           NEXT_PUBLIC_API_URL = https://xxxx.trycloudflare.com
                └─ Cloudflare Tunnel (auto — no sign-up)
                       └─ FastAPI  port 7860  (this notebook)
                              │
                              ├─ POST /translate          ─┐
                              ├─ POST /translate-reverse    │  NLLB-200 FP32
                              ├─ POST /translate-batch      │  on Colab GPU
                              ├─ POST /translate-batch-file ┘
                              │
                              ├─ POST /classify-image     ─┐  MobileNetV2
                              ├─ POST /ocr-translate        │  + EasyOCR
                              ├─ POST /ocr-translate-base64 ┘  + NLLB
                              │
                              ├─ POST /chat               HF Router (Llama/Qwen)
                              │                           + NLLB translation
                              │
                              └─ GET  /health  /system-info  /history  /config …
                                     (17 endpoints total)
                                          │
                              HuggingFace Hub (model weights, loaded once at startup)
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

### 6 — Connect to Vercel

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard) → your project
2. **Settings → Environment Variables**
3. Change `NEXT_PUBLIC_API_URL` to the Cloudflare URL
4. **Save** → **Redeploy** (or push a commit)

Done — the live site now runs NLLB on the Colab GPU.

## Switching back to HF Space

When the Colab session ends, revert `NEXT_PUBLIC_API_URL` to:
```
https://keithtwesigye-runyoro-translator-api.hf.space
```

## Notes

- The Cloudflare URL **changes each time** the notebook is restarted
  — update Vercel each time you start a new session.
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
