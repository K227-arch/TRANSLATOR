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
}

def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_PATTERNS:
            return True
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
        print(f"  ✓ {rel}")
        uploaded += 1
    except Exception as e:
        print(f"  ✗ {rel}: {e}")

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
        print(f"  ✓ {fpath.name}")

print(f"\nDone! Uploaded {uploaded} files.")
print(f"Space URL: https://huggingface.co/spaces/{SPACE_ID}")
print(f"API URL:   https://{SPACE_ID.replace('/', '-')}.hf.space")
