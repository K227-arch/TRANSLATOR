#!/bin/bash
# ── docker-entrypoint.aws.sh ──────────────────────────────────────────────────
# AWS-optimised startup script for the Runyoro Translator backend.
#
# Cost strategy:
#   1. Check EBS volume first  → zero network cost on warm restart
#   2. Check S3 bucket second  → ~$0.09/GB transfer within same region (cheap)
#   3. Fall back to HF Hub     → free but slow (~5 min for all models)
#
# After download, models are written to the EBS-backed /app/model volume so
# subsequent restarts (e.g. after a container update) skip the download entirely.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/app/model}"
S3_BUCKET="${S3_MODEL_BUCKET:-}"
S3_PREFIX="${S3_MODEL_PREFIX:-models/latest}"
AWS_REGION="${AWS_REGION:-eu-north-1}"
PORT="${PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-1}"

# ── Colours for readable log output ──────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[entrypoint]${NC} $*"; }
ok()   { echo -e "${GREEN}[entrypoint]${NC} $*"; }
warn() { echo -e "${YELLOW}[entrypoint]${NC} $*"; }
err()  { echo -e "${RED}[entrypoint]${NC} $*" >&2; }

log "=== Runyoro Translator AWS startup ==="
log "MODEL_DIR   : ${MODEL_DIR}"
log "S3_BUCKET   : ${S3_BUCKET:-<not set — will use HF Hub>}"
log "AWS_REGION  : ${AWS_REGION}"
log "WORKERS     : ${WORKERS}"

mkdir -p "${MODEL_DIR}"

# ── Helper: check if a directory has actual model weights (not empty/stubs) ──
dir_has_weights() {
    local d="$1"
    [[ -d "$d" ]] && \
    find "$d" -maxdepth 1 \( -name "*.safetensors" -o -name "*.bin" -o -name "*.onnx" \) \
              -size +1M -print -quit 2>/dev/null | grep -q .
}

# ── Helper: download a single model dir from S3 ──────────────────────────────
s3_sync_model() {
    local model_name="$1"
    local local_path="${MODEL_DIR}/${model_name}"
    local s3_path="s3://${S3_BUCKET}/${S3_PREFIX}/${model_name}/"

    if dir_has_weights "${local_path}"; then
        ok "  [cache-hit]  ${model_name} already on EBS — skipping"
        return 0
    fi

    log "  [s3-sync]    Downloading ${model_name} from ${s3_path} ..."
    mkdir -p "${local_path}"
    if aws s3 sync "${s3_path}" "${local_path}" \
            --region "${AWS_REGION}" \
            --no-progress \
            --exclude "*.msgpack" \
            --exclude "flax_model*" \
            --exclude "tf_model*" 2>&1; then
        if dir_has_weights "${local_path}"; then
            ok "  [s3-sync]    ${model_name} downloaded from S3 ✓"
            return 0
        fi
    fi
    warn "  [s3-sync]    S3 sync failed or empty for ${model_name} — will try HF Hub"
    return 1
}

# ── Helper: upload a model dir to S3 (run after HF download to warm S3 cache) ─
s3_upload_model() {
    local model_name="$1"
    local local_path="${MODEL_DIR}/${model_name}"
    local s3_path="s3://${S3_BUCKET}/${S3_PREFIX}/${model_name}/"

    if [[ -z "${S3_BUCKET}" ]]; then return 0; fi
    if ! dir_has_weights "${local_path}"; then return 0; fi

    log "  [s3-upload]  Caching ${model_name} to S3 for future starts..."
    aws s3 sync "${local_path}" "${s3_path}" \
        --region "${AWS_REGION}" \
        --no-progress \
        --exclude "*.msgpack" \
        --exclude "flax_model*" \
        --exclude "tf_model*" \
        --storage-class STANDARD_IA 2>&1 || \
        warn "  [s3-upload]  Upload failed — will re-download from HF Hub next time"
}

# ── Step 1: Resolve models ────────────────────────────────────────────────────
log "--- Step 1: Resolving model weights ---"

# Models we need (in priority order — smaller ones first)
MODELS_MARIAN=("en2lun" "lun2en" "en2lun_onnx" "lun2en_onnx")
MODELS_NLLB=("nllb_en2lun_int8" "nllb_lun2en_int8")
MODELS_EXTRA=("sem_model")

# Disable NLLB loading when DISABLE_NLLB=1 (saves 2.5 GB RAM — use on t3.large)
if [[ "${DISABLE_NLLB:-0}" == "1" ]]; then
    warn "DISABLE_NLLB=1 — skipping NLLB models (saves ~2.5 GB RAM)"
    MODELS_NLLB=()
fi

# Combine all model dirs to check
ALL_MODELS=("${MODELS_MARIAN[@]}" "${MODELS_NLLB[@]}" "${MODELS_EXTRA[@]}")

NEED_HF_DOWNLOAD=()

for model in "${ALL_MODELS[@]}"; do
    local_path="${MODEL_DIR}/${model}"
    if dir_has_weights "${local_path}"; then
        ok "  [ebs-hit]    ${model} found on EBS volume ✓"
        continue
    fi

    # Try S3 if bucket is configured
    if [[ -n "${S3_BUCKET}" ]]; then
        if s3_sync_model "${model}"; then
            continue
        fi
    fi

    # Mark for HF Hub download
    NEED_HF_DOWNLOAD+=("${model}")
done

# ── Step 2: HF Hub downloads for any missing models ──────────────────────────
if [[ ${#NEED_HF_DOWNLOAD[@]} -gt 0 ]]; then
    log "--- Step 2: HF Hub download for ${#NEED_HF_DOWNLOAD[@]} missing models ---"
    log "  Models: ${NEED_HF_DOWNLOAD[*]}"

    # Build --models argument for download_models.py
    MODEL_ARGS=""
    for m in "${NEED_HF_DOWNLOAD[@]}"; do
        MODEL_ARGS="${MODEL_ARGS} --model ${m}"
    done

    python download_models.py ${MODEL_ARGS} || {
        warn "download_models.py reported errors — some models may be missing"
    }

    # ── Step 2b: Upload newly downloaded models to S3 for future starts ──────
    if [[ -n "${S3_BUCKET}" ]]; then
        log "--- Step 2b: Warming S3 cache ---"
        for model in "${NEED_HF_DOWNLOAD[@]}"; do
            s3_upload_model "${model}"
        done
    fi
else
    ok "--- Step 2: All models resolved — skipping HF Hub download ---"
fi

# ── Step 3: Set offline mode now that models are on disk ─────────────────────
# Prevents the app from making outbound HF Hub requests on every startup,
# which saves both time and potential data transfer costs.
log "--- Step 3: Switching to offline mode (models are local) ---"
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export HF_HUB_OFFLINE=1
ok "  Offline mode enabled ✓"

# ── Step 4: Verify index file ─────────────────────────────────────────────────
log "--- Step 4: Checking translation index ---"
INDEX_PATH="${MODEL_DIR}/translation_index.pkl"
if [[ ! -f "${INDEX_PATH}" ]]; then
    warn "  translation_index.pkl missing — rebuilding from training data..."
    python -c "
from translate import _load_retrieval
try:
    _load_retrieval()
    print('[entrypoint] Index rebuilt successfully')
except Exception as e:
    print(f'[entrypoint] Index rebuild failed: {e}')
" || warn "  Index rebuild failed — semantic search will be unavailable"
else
    ok "  translation_index.pkl found ✓"
fi

# ── Step 5: Restore feedback from GitHub (non-fatal) ─────────────────────────
log "--- Step 5: Restoring feedback state ---"
python -c "
try:
    from feedback_store import restore_from_github
    restore_from_github()
    print('[entrypoint] Feedback restored ✓')
except Exception as e:
    print(f'[entrypoint] Feedback restore skipped: {e}')
" || true

# ── Step 6: Start uvicorn ─────────────────────────────────────────────────────
log "--- Step 6: Starting uvicorn ---"
ok "  PORT=${PORT}  WORKERS=${WORKERS}"
ok "  Access log → /app/logs/access.log"
ok "  Error log  → /app/logs/error.log"

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --log-level info \
    --access-log \
    --use-colors \
    --timeout-keep-alive 30 \
    --timeout-graceful-shutdown 30
