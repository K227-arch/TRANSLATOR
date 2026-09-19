# pi-sim backend Dockerfile
# ─────────────────────────────────────────────────────────────────────────────
# Simulates the Raspberry Pi 5 AI Stick C++ backend inference path using
# Python + ONNX Runtime on CPU.
#
# Key design decisions that match the Pi environment:
#   - CPU-only torch (no CUDA) — Pi has no GPU
#   - onnxruntime (not onnxruntime-gpu) — Pi uses CPUExecutionProvider
#   - Python 3.11 — matches Pi's Bookworm default and easyocr constraint
#   - optimum[onnxruntime] — for Marian beam-search path
#   - Models are NOT baked into the image; they are mounted as a volume
#     so you use your existing model/ directory directly
#
# Volumes expected at runtime (see docker-compose.pi-sim.yml):
#   /models   ← backend/model/   (all ONNX model dirs)
#   /backend  ← backend/         (translate.py, language_rules_data.py, etc.)
#   /tmp      ← writable history / feedback scratch

FROM python:3.11-slim

WORKDIR /app

# ── System packages ────────────────────────────────────────────────────────
# tesseract-ocr: required by pytesseract (OCR fallback engine)
# libgomp1:      required by onnxruntime for OpenMP parallelism on Linux
# curl:          healthcheck inside container
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ────────────────────────────────────────────────────────────
# Install CPU-only torch first — avoids pulling the 1.3 GB CUDA wheel
RUN pip install --no-cache-dir --timeout=300 --retries=5 \
        torch==2.3.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# ── App code ───────────────────────────────────────────────────────────────
COPY app.py .

# Mount points (populated at runtime by docker-compose volumes)
RUN mkdir -p /models /backend /tmp/pisim

EXPOSE 8080

# Environment defaults — all overridable via docker-compose environment:
ENV PORT=8080
ENV MODEL_DIR=/models
ENV BACKEND_DIR=/backend
ENV HISTORY_FILE=/tmp/pisim/history.json
ENV NLLB_THREADS=4
ENV MARIAN_THREADS=2
ENV MARIAN_GREEDY=0
ENV CORS_ORIGINS=http://localhost:3090,http://localhost:3002
ENV LOG_LEVEL=INFO
# Keep transformers offline after model files are mounted — no HF downloads
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

HEALTHCHECK --interval=20s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -sf http://localhost:8080/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
