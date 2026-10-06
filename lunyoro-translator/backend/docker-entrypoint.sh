#!/bin/bash
set -e

# Download models from HuggingFace if DOWNLOAD_MODELS_ON_START=1
if [ "$DOWNLOAD_MODELS_ON_START" = "1" ]; then
    echo "=== Checking models ==="
    # Choose download mode based on which models are enabled.
    # --nllb-only: download NLLB + sem_model only (skips Marian + datasets).
    # --marian-only: download Marian + sem_model only (skips NLLB + datasets).
    # Both modes stay well under the 50 GB Space storage limit.
    if [ "$DISABLE_MARIAN" = "1" ]; then
        python download_models.py --nllb-only
    elif [ "$DISABLE_NLLB" = "1" ]; then
        python download_models.py --marian-only
    else
        python download_models.py --nllb-only
    fi
fi

echo "=== Starting backend ==="
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
