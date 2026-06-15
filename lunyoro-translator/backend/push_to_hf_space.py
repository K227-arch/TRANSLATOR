"""
Push the backend to HuggingFace Spaces.
Creates the space if it doesn't exist, then uploads all backend files.
"""
import os
import shutil
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise SystemExit("Error: HF_TOKEN environment variable is not set.")
SPACE_ID = "keithtwesigye/runyoro-translator-api"
BACKEND_DIR = Path(__file__).parent
SPACE_DIR = BACKEND_DIR.parent / "hf-space"

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "huggingface_hub"], check=True)
    from huggingface_hub import HfApi, create_repo

api = HfApi(token=HF_TOKEN)

# Create space if it doesn't exist
print(f"Creating/checking space: {SPACE_ID}")
try:
    create_repo(
        repo_id=SPACE_ID,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
        token=HF_TOKEN,
    )
    print("Space ready.")
except Exception as e:
    print(f"Space creation note: {e}")

# Files to upload from backend
SKIP_PATTERNS = {
    "__pycache__", ".env", "history.json",
    "model", "data/training", "data/cleaned",
    "data/OCR", ".dockerignore",
    "push_to_hf_space.py",
    "venv", ".git", "feedback",
    "bleu_results.json",
    "evaluate_current_models.py",
}

# Also skip large log files and backup files to stay under 1GB Space limit
SKIP_EXTENSIONS = {".bak", ".bak2", ".bak_bt", ".bak_aug", ".bak_tagfix"}
SKIP_LARGE_LOGS = {"nllb_training.log", "full_training.log", "k227_pipeline.log",
                   "push_models.log", "retrain_augmented.log", "retrain_lun2en.log",
                   "retrain_lun2en_final.log", "back_translate_full.log",
                   "back_translate_min4.log", "marian_retrain.log"}

def should_skip(path: Path) -> bool:
    parts_str = str(path)
    for part in path.parts:
        if part in SKIP_PATTERNS:
            return True
    # Skip backup file extensions
    if path.suffix in SKIP_EXTENSIONS or any(parts_str.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    # Skip large training logs
    if path.name in SKIP_LARGE_LOGS:
        return True
    # Skip files over 50MB (large CSV training data, model files accidentally included)
    try:
        if path.stat().st_size > 50 * 1024 * 1024:
            return True
    except Exception:
        pass
    return False

print("\nUploading backend files to Space...")
uploaded = 0
for fpath in BACKEND_DIR.rglob("*"):
    if fpath.is_dir():
        continue
    rel = fpath.relative_to(BACKEND_DIR)
    if should_skip(rel):
        continue
    try:
        api.upload_file(
            path_or_fileobj=str(fpath),
            path_in_repo=str(rel),
            repo_id=SPACE_ID,
            repo_type="space",
        )
        print(f"  [OK] {rel}")
        uploaded += 1
    except Exception as e:
        print(f"  [FAIL] {rel}: {e}")

# Upload Space-specific files (README + Dockerfile override)
print("\nUploading Space config files...")
for fpath in SPACE_DIR.iterdir():
    if fpath.is_file():
        api.upload_file(
            path_or_fileobj=str(fpath),
            path_in_repo=fpath.name,
            repo_id=SPACE_ID,
            repo_type="space",
        )
        print(f"  [OK] {fpath.name}")

print(f"\nDone! Uploaded {uploaded} files.")
print(f"Space URL: https://huggingface.co/spaces/{SPACE_ID}")
print(f"API URL:   https://{SPACE_ID.replace('/', '-')}.hf.space")
