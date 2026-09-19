# pi-sim sidecar Dockerfile
# ─────────────────────────────────────────────────────────────────────────────
# Thin Python sidecar — identical to what runs on the Pi at port 8001.
# Handles: /classify-image, /translate-batch, /translate-batch-file,
#          /summarize-pdf, /language-rules/*, /chat
# All translation is delegated to the pi-sim-backend via HTTP (CPP_BACKEND_URL).
#
# Volumes expected at runtime:
#   /sidecar/models/mobilenet_v2  ← MobileNetV2 model files (optional)

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch (for MobileNetV2 classifier)
RUN pip install --no-cache-dir --timeout=300 --retries=5 \
        torch==2.3.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# App files — app.py + bundled language_rules_data.py
COPY app.py .
COPY language_rules_data.py .

RUN mkdir -p /app/models/mobilenet_v2

EXPOSE 8001

ENV CPP_BACKEND_URL=http://pi-sim-backend:8080
ENV TRANSFORMERS_OFFLINE=1
ENV LOG_LEVEL=INFO

HEALTHCHECK --interval=20s --timeout=8s --start-period=30s --retries=5 \
    CMD curl -sf http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
