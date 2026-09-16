FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (200MB vs 1.3GB for CUDA torch)
# This avoids the multi-GB CUDA wheel download that keeps timing out
RUN pip install --no-cache-dir --timeout=300 --retries=5 \
        torch==2.3.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu

# Install remaining deps (torch already satisfied above, so pip skips it)
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 \
        -r requirements.txt

# App code
COPY . .

RUN mkdir -p /app/model /app/history

EXPOSE 7860

ENV PORT=7860
ENV TRANSFORMERS_OFFLINE=0
ENV HF_DATASETS_OFFLINE=0
ENV HF_HUB_OFFLINE=0
ENV DOWNLOAD_MODELS_ON_START=1
ENV CORS_ORIGINS=https://frontend-six-phi-25.vercel.app,http://localhost:3002,https://horizonx.kathay.tech
ENV DISABLE_NLLB=0

CMD ["sh", "-c", "python download_models.py --marian-only && \
    uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1"]
