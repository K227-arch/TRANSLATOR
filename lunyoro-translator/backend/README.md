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

- MarianMT fine-tuned models (en↔lun)
- NLLB-200 fine-tuned models (en↔lun)
- Semantic search index
- Language rules (R/L rule — L→R except adjacent to e/i/y, nasal assimilation, apostrophe elision)
- Image classification (MobileNetV2) for object recognition and translation
