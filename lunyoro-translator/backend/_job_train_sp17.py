"""
_job_train_sp17.py
==================
HF Jobs entrypoint — runs inside a GPU container.

Steps:
  1. Install all Python dependencies
  2. Download current model weights from HF Hub into /app/model/
  3. Run MarianMT --new-only  (both directions, 5 epochs)
  4. Run NLLB     --new-only  (both directions, 3 epochs)
  5. Push updated weights to all 4 HF repos (hyphen + underscore variants)

The Space repo is mounted read-only at /app — we copy it to /workspace
so we can write model checkpoints alongside the source.

Environment variables expected:
  HF_TOKEN  — write token (passed via --secrets HF_TOKEN)
"""
import os, sys, shutil, subprocess
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    sys.exit("ERROR: HF_TOKEN not set")

# ── Working directory setup ───────────────────────────────────────────────────
# Space is mounted read-only at /app — copy to writable /workspace
SRC  = Path("/app")
WORK = Path("/workspace")

print("=" * 60)
print("  SP17 CONTINUAL TRAINING JOB")
print("=" * 60)

print(f"\n[Setup] Copying Space source {SRC} → {WORK} ...")
if WORK.exists():
    shutil.rmtree(WORK)
shutil.copytree(SRC, WORK)
os.chdir(WORK)
print("  Done.")

# ── 1. Install dependencies ───────────────────────────────────────────────────
print("\n[1/5] Installing dependencies...")
subprocess.run([
    sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers>=4.41.0,<4.52.0",
    "sentencepiece", "sacrebleu", "pandas",
    "huggingface_hub", "accelerate", "protobuf",
    "rapidfuzz", "sentence-transformers",
], check=True)
print("  Done.")

# ── 2. Download model weights from HF Hub ────────────────────────────────────
print("\n[2/5] Downloading model weights from HF Hub...")
from huggingface_hub import snapshot_download

MODEL_DIR = WORK / "model"
MODEL_DIR.mkdir(exist_ok=True)

REPOS = {
    "en2lun":      "keithtwesigye/lunyoro-en2lun",
    "lun2en":      "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun": "keithtwesigye/lunyoro-nllb-en2lun",
    "nllb_lun2en": "keithtwesigye/lunyoro-nllb-lun2en",
}
IGNORE = ["*.msgpack", "flax_model*", "tf_model*", "rust_model*", "best_checkpoint/*"]

for local_name, repo_id in REPOS.items():
    dest = MODEL_DIR / local_name
    dest.mkdir(exist_ok=True)
    existing = list(dest.glob("*.safetensors")) + list(dest.glob("*.bin"))
    if existing:
        print(f"  [SKIP] {local_name} already present")
        continue
    print(f"  Downloading {repo_id} → model/{local_name}/ ...")
    snapshot_download(
        repo_id=repo_id,
        repo_type="model",
        local_dir=str(dest),
        token=HF_TOKEN,
        ignore_patterns=IGNORE,
    )
    print(f"  [OK] {local_name}")

# ── 3. Train MarianMT (both directions, --new-only) ──────────────────────────
print("\n[3/5] Training MarianMT --new-only (both directions, 5 epochs)...")
subprocess.run([
    sys.executable, "train_marian.py",
    "--new-only",
    "--direction", "both",
    "--epochs",    "5",
    "--batch-size","32",
    "--lr",        "3e-5",
], check=True, cwd=str(WORK))
print("  MarianMT training complete.")

# ── 4. Train NLLB (both directions, --new-only) ──────────────────────────────
print("\n[4/5] Training NLLB --new-only (both directions, 3 epochs)...")
subprocess.run([
    sys.executable, "train_nllb.py",
    "--new-only",
    "--direction", "both",
    "--epochs",    "3",
    "--batch-size","8",
    "--lr",        "8e-6",
], check=True, cwd=str(WORK))
print("  NLLB training complete.")

# ── 5. Push all updated models to HF Hub ─────────────────────────────────────
print("\n[5/5] Pushing updated models to HF Hub...")
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)

# Each trained model dir pushed to both hyphen and underscore repos
PUSH_MAP = {
    "en2lun": [
        "keithtwesigye/lunyoro-en2lun",
    ],
    "lun2en": [
        "keithtwesigye/lunyoro-lun2en",
    ],
    "nllb_en2lun": [
        "keithtwesigye/lunyoro-nllb-en2lun",
        "keithtwesigye/lunyoro-nllb_en2lun",
    ],
    "nllb_lun2en": [
        "keithtwesigye/lunyoro-nllb-lun2en",
        "keithtwesigye/lunyoro-nllb_lun2en",
    ],
}

for local_name, repo_ids in PUSH_MAP.items():
    model_path = MODEL_DIR / local_name
    if not model_path.is_dir():
        print(f"  [SKIP] {local_name} — dir not found")
        continue
    for repo_id in repo_ids:
        print(f"  Pushing {local_name} → {repo_id} ...", end=" ", flush=True)
        try:
            api.upload_folder(
                folder_path=str(model_path),
                repo_id=repo_id,
                repo_type="model",
                commit_message="Continual training on sentence pair 17 dataset",
            )
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")

print("\n" + "=" * 60)
print("  JOB COMPLETE")
print("=" * 60)
