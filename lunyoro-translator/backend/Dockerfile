FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Create directories
RUN mkdir -p /app/model /app/history

# HuggingFace Spaces uses port 7860
EXPOSE 7860

ENV PORT=7860
ENV TRANSFORMERS_OFFLINE=0
ENV HF_DATASETS_OFFLINE=0
ENV HF_HUB_OFFLINE=0
ENV DOWNLOAD_MODELS_ON_START=1
ENV CORS_ORIGINS=https://frontend-six-phi-25.vercel.app,http://localhost:3002,https://horizonx.kathay.tech

# NLLB-200 loads from HF Hub cache (/root/.cache) — separate from 1GB Space repo storage.
# cpu-basic has 16GB RAM which fits one NLLB model (2.3GB).
# Models download to HF Hub cache on first request, not to /app/model.
ENV DISABLE_NLLB=0
# HF_TOKEN is injected as a Space Secret for authenticated HF Hub downloads

# Download MarianMT + sem_model only (they're small).
# NLLB downloads lazily on first use via HF Hub cache.
CMD ["sh", "-c", "python download_models.py --marian-only && \
    uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1"]
