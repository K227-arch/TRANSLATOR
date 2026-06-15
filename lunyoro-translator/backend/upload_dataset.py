"""
Uploads all training/data CSVs to HuggingFace dataset repo:
    keithtwesigye/lunyoro-dataset

Usage:
    python upload_dataset.py           # upload all
    python upload_dataset.py --dry-run # list files without uploading

Requires HF_TOKEN env var with write access to the dataset repo.
"""

import os
import sys
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

DATASET_REPO = "keithtwesigye/lunyoro-dataset"
BACKEND_DIR = Path(__file__).parent

# Files/folders to upload and their destination path in the repo
UPLOAD_PATHS = [
    # (local_path, repo_subfolder)
    (BACKEND_DIR / "data" / "cleaned",  "data/cleaned"),
    (BACKEND_DIR / "data" / "training", "data/training"),
    (BACKEND_DIR / "data" / "raw",      "data/raw"),
]

# Patterns to skip
SKIP_SUFFIXES = {".xlsx", ".xls", ".pdf"}
SKIP_NAMES = {"~$dictionary_pairs.xlsx"}


def collect_files():
    """Collect all CSV files to upload."""
    files = []
    for local_dir, repo_prefix in UPLOAD_PATHS:
        if not local_dir.exists():
            print(f"  [SKIP] {local_dir} does not exist")
            continue
        for f in sorted(local_dir.rglob("*.csv")):
            if f.name in SKIP_NAMES:
                continue
            repo_path = repo_prefix + "/" + f.name
            files.append((f, repo_path))
    return files


def upload(dry_run=False):
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("ERROR: HF_TOKEN environment variable not set.")
        sys.exit(1)

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("Installing huggingface_hub...")
        os.system("pip install huggingface_hub")
        from huggingface_hub import HfApi, create_repo

    api = HfApi(token=hf_token)

    # Create dataset repo if it doesn't exist
    if not dry_run:
        try:
            create_repo(
                repo_id=DATASET_REPO,
                repo_type="dataset",
                exist_ok=True,
                token=hf_token,
                private=False,
            )
            print(f"  [OK] Dataset repo ready: {DATASET_REPO}")
        except Exception as e:
            print(f"  [WARN] Could not create repo (may already exist): {e}")

    files = collect_files()
    print(f"\nFound {len(files)} CSV files to upload:\n")

    total_size = 0
    for local_path, repo_path in files:
        size_kb = local_path.stat().st_size // 1024
        total_size += size_kb
        print(f"  {'[DRY]' if dry_run else '→'} {local_path.name:50s}  {size_kb:>8,} KB  →  {repo_path}")

    print(f"\nTotal: {total_size:,} KB ({total_size/1024:.1f} MB)")

    if dry_run:
        print("\nDry run complete. No files uploaded.")
        return

    print(f"\nUploading to {DATASET_REPO}...\n")
    failed = []
    for i, (local_path, repo_path) in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {local_path.name} ...", end=" ", flush=True)
        for attempt in range(3):
            try:
                api.upload_file(
                    path_or_fileobj=str(local_path),
                    path_in_repo=repo_path,
                    repo_id=DATASET_REPO,
                    repo_type="dataset",
                    token=hf_token,
                )
                print("OK")
                break
            except Exception as e:
                if attempt < 2:
                    print(f"retry ({attempt+1})...", end=" ", flush=True)
                else:
                    print(f"FAILED: {e}")
                    failed.append((local_path.name, str(e)))

    print(f"\n{'='*60}")
    if failed:
        print(f"Upload complete with {len(failed)} failures:")
        for name, err in failed:
            print(f"  FAILED: {name} — {err}")
    else:
        print(f"All {len(files)} files uploaded successfully to:")
        print(f"  https://huggingface.co/datasets/{DATASET_REPO}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    args = parser.parse_args()
    upload(dry_run=args.dry_run)
