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
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# App code
COPY . .

RUN mkdir -p /app/model /app/history

EXPOSE 7860

ENV PORT=7860
# â”€â”€ Startup mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# COLAB_MODE=1  â†’ run proxy_main.py (thin proxy, forwards to Colab NLLB backend)
# COLAB_MODE=0  â†’ run main.py       (full backend with local Marian as primary)
#
# Set COLAB_MODE and COLAB_URL as HF Space secrets.
# All other secrets: DISABLE_NLLB, DISABLE_MARIAN, DISABLE_ONNX, CORS_ORIGINS.

CMD ["sh", "-c", \
     "if [ \"$COLAB_MODE\" = '1' ]; then \
        echo '=== Proxy mode â€” forwarding to Colab NLLB backend ===' && \
        echo \"COLAB_URL=$COLAB_URL\" && \
        exec uvicorn proxy_main:app --host 0.0.0.0 --port 7860 --workers 1; \
      else \
        echo '=== Full backend mode â€” Marian running locally ===' && \
        exec uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1; \
      fi"]

