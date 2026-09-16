"""
_hf_job_train.py
=================
Runs inside an HF Jobs container.
Mounts the Space repo at /app, installs deps, runs MarianMT --new-only training,
then pushes the updated models back to HF Hub.

Invoked via:
    hf jobs run ... python:3.12 python _hf_job_train.py
"""
import os, subprocess, sys
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN", "")
WORKDIR  = Path("/app")          # mounted Space repo

print("=" * 60)
print("  HF JOB: SP17 Incremental Training")
print(f"  Working dir: {WORKDIR}")
print("=" * 60)

os.chdir(WORKDIR)

# ── 1. Install dependencies ───────────────────────────────────────────────────
print("\n[1/4] Installing dependencies...")
subprocess.run([
    sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers", "sentencepiece",
    "sacrebleu", "pandas", "huggingface_hub",
    "accelerate",
], check=True)
print("  Done.")

# ── 2. Train MarianMT on the 558 new_only pairs ───────────────────────────────
print("\n[2/4] Training MarianMT (--new-only, both directions, 5 epochs)...")
subprocess.run([
    sys.executable, "train_marian.py",
    "--new-only",
    "--direction", "both",
    "--epochs",    "5",
    "--batch-size","32",
    "--lr",        "3e-5",
], check=True)
print("  Training complete.")

# ── 3. Push updated models to HF Hub ─────────────────────────────────────────
print("\n[3/4] Pushing updated models to HF Hub...")
for model in ["en2lun", "lun2en"]:
    subprocess.run([sys.executable, "push_models.py", "--model", model], check=True)
print("  Models pushed.")

# ── 4. Push updated new_only CSVs back to the Space ──────────────────────────
print("\n[4/4] Syncing updated training data back to Space...")
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
for rel in ["data/training/new_only_train.csv", "data/training/new_only_val.csv"]:
    p = WORKDIR / rel
    if p.exists():
        api.upload_file(
            path_or_fileobj=str(p),
            path_in_repo=rel,
            repo_id="keithtwesigye/runyoro-translator-api",
            repo_type="space",
            commit_message="Update training data after SP17 incremental run",
        )
        print(f"  Synced {rel}")

print("\n" + "=" * 60)
print("  DONE — models retrained and pushed.")
print("=" * 60)
