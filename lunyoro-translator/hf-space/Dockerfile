FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential \
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
ENV CORS_ORIGINS=https://frontend-six-phi-25.vercel.app,http://localhost:3002

# Download all 5 models on cold start (skips any already present),
# then switch to offline mode and start the server
CMD ["sh", "-c", "python download_models.py && \
    export TRANSFORMERS_OFFLINE=1 && \
    export HF_DATASETS_OFFLINE=1 && \
    export HF_HUB_OFFLINE=1 && \
    uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1"]
