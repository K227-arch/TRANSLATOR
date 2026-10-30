---
title: Runyoro Rutooro Translator API
emoji: 🌍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# Runyoro / Rutooro Translator API

FastAPI backend for the Runyoro-Rutooro translation app.

- MarianMT fine-tuned models (en↔lun) — loaded once into `_marian_models` / `_marian_available` module-level singletons; used as primary model and as fallback when NLLB is unavailable
- NLLB-200 fine-tuned models (en↔lun) — loaded once into `_nllb_models` / `_nllb_available` module-level singletons; primary for most translation paths; falls back to MarianMT on API timeout or when `DISABLE_NLLB=1`
- Semantic search index
- Language rules (R/L, nasal assimilation, apostrophe elision)
