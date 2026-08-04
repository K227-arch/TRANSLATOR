FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Python deps — install torch CPU-only (no torchvision needed for translation)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y torchvision torchaudio 2>/dev/null || true

# App code (models are NOT baked in — mounted as volume or downloaded at startup)
COPY . .

# Create model and history directories
RUN mkdir -p /app/model /app/history

# The sem_model loads from HuggingFace Hub at runtime (translate.py handles this)
# No need to pre-download — avoids build timeout on free tier

EXPOSE 8000

# Startup script — downloads models if not present, then starts server
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["/docker-entrypoint.sh"]
