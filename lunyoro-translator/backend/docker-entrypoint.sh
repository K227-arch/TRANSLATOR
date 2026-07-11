#!/bin/bash
set -e

# Download models from HuggingFace if DOWNLOAD_MODELS_ON_START=1
# and models are not already present on the mounted volume
if [ "$DOWNLOAD_MODELS_ON_START" = "1" ]; then
    echo "=== Checking models ==="
    python download_models.py
fi

# NOTE: Do NOT set offline mode — sem_model may need to download from HF Hub
# if the local copy has corrupted tokenizer.json (LFS pointer issue)

echo "=== Starting backend ==="
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
