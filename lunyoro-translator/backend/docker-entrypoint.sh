#!/bin/bash
set -e

# Download models from HuggingFace if DOWNLOAD_MODELS_ON_START=1
# and models are not already present on the mounted volume
if [ "$DOWNLOAD_MODELS_ON_START" = "1" ]; then
    echo "=== Checking models ==="
    python download_models.py
fi

# Set offline mode after download so inference never hits the network
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export HF_HUB_OFFLINE=1

echo "=== Starting backend ==="
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
