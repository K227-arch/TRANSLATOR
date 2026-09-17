"""
_pull_all.py
=============
Downloads all model weights from HF Hub model repos
and pulls source/data files from the HF Space.

Models downloaded to:  backend/model/<name>/
Space files pulled to: backend/  (skipping large logs, .env, etc.)
"""
import os, sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

TOKEN      = os.environ.get("HF_TOKEN", "").strip()
TOKEN_READ = os.environ.get("HF_TOKEN_READ", TOKEN).strip()
if not TOKEN_READ:
    sys.exit("HF_TOKEN / HF_TOKEN_READ not set")

from huggingface_hub import snapshot_download, hf_hub_download, list_repo_files, HfApi

BASE      = Path(__file__).parent
MODEL_DIR = BASE / "model"

# ── 1. Model repos ─────────────────────────────────────────────────────────────
MODEL_REPOS = {
    "en2lun":               "keithtwesigye/lunyoro-en2lun",
    "lun2en":               "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun":          "keithtwesigye/lunyoro-nllb-en2lun",
    "nllb_lun2en":          "keithtwesigye/lunyoro-nllb-lun2en",
    "nllb_en2lun_underscore":"keithtwesigye/lunyoro-nllb_en2lun",
    "nllb_lun2en_underscore":"keithtwesigye/lunyoro-nllb_lun2en",
    "sem_model":            "keithtwesigye/lunyoro-sentence-embeddings",
}

IGNORE = ["*.msgpack", "flax_model*", "tf_model*", "rust_model*"]

print("=" * 60)
print("  PULLING MODELS FROM HF HUB")
print("=" * 60)

for local_name, repo_id in MODEL_REPOS.items():
    dest = MODEL_DIR / local_name
    dest.mkdir(parents=True, exist_ok=True)
    # Check if already has weights
    existing = list(dest.glob("*.safetensors")) + list(dest.glob("*.bin"))
    if existing:
        print(f"\n  [SKIP] {local_name} — already has weights ({existing[0].name})")
        continue
    print(f"\n  Downloading {repo_id} → model/{local_name}/")
    try:
        snapshot_download(
            repo_id=repo_id,
            repo_type="model",
            local_dir=str(dest),
            token=TOKEN_READ,
            ignore_patterns=IGNORE,
        )
        weights = list(dest.glob("*.safetensors")) + list(dest.glob("*.bin"))
        print(f"  [OK] {len(weights)} weight file(s) saved")
    except Exception as e:
        print(f"  [FAIL] {e}")

# ── 2. Space source + data files ───────────────────────────────────────────────
SPACE_ID = "keithtwesigye/runyoro-translator-api"

# Patterns to skip (large training files, secrets, logs, model weights)
SKIP_PREFIXES = (
    "model/en2lun", "model/lun2en", "model/nllb",
    "data/training/train.csv", "data/training/val.csv",
    "data/training/test.csv",
    ".env",
)
SKIP_EXTENSIONS = {".bak", ".bak2", ".log"}
SKIP_NAMES = {
    "auto_retrain.log", "backend.log", "feedback.jsonl",
    "nllb_training.log", "full_training.log",
}

def should_skip_space_file(path: str) -> bool:
    p = path.replace("\\", "/")
    for prefix in SKIP_PREFIXES:
        if p.startswith(prefix):
            return True
    name = Path(p).name
    if name in SKIP_NAMES:
        return True
    if Path(p).suffix in SKIP_EXTENSIONS:
        return True
    return False

print("\n\n" + "=" * 60)
print("  PULLING SPACE FILES")
print("=" * 60)

try:
    api = HfApi(token=TOKEN_READ)
    all_files = list(list_repo_files(SPACE_ID, repo_type="space", token=TOKEN_READ))
    to_pull = [f for f in all_files if not should_skip_space_file(f)]
    print(f"\n  {len(to_pull)} files to pull (skipping {len(all_files)-len(to_pull)} large/secret files)")

    for i, repo_path in enumerate(sorted(to_pull), 1):
        clean = repo_path.replace("\\", "/")
        local_path = BASE / clean
        local_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  [{i}/{len(to_pull)}] {clean} ... ", end="", flush=True)
        try:
            hf_hub_download(
                repo_id=SPACE_ID,
                repo_type="space",
                filename=repo_path,
                local_dir=str(BASE),
                token=TOKEN_READ,
            )
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")
except Exception as e:
    print(f"  [FAIL] Could not list Space files: {e}")

print("\n" + "=" * 60)
print("  PULL COMPLETE")
print("=" * 60)
