"""
Downloads all fine-tuned Runyoro-Rutooro models AND training dataset from HuggingFace.
Run this once after cloning the repo:

    python download_models.py

Models pulled:
    keithtwesigye/lunyoro-en2lun      → model/en2lun/
    keithtwesigye/lunyoro-lun2en      → model/lun2en/
    keithtwesigye/lunyoro-nllb_en2lun → model/nllb_en2lun/
    keithtwesigye/lunyoro-nllb_lun2en → model/nllb_lun2en/
    sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 → model/sem_model/

Dataset pulled:
    keithtwesigye/lunyoro-dataset     → data/cleaned/, data/training/, data/raw/
"""

import os
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "model"
DATA_DIR = Path(__file__).parent / "data"
DATASET_REPO = "keithtwesigye/lunyoro-dataset"

HF_MODELS = {
    "en2lun": "keithtwesigye/lunyoro-en2lun",
    "lun2en": "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun": "keithtwesigye/lunyoro-nllb_en2lun",
    "nllb_lun2en": "keithtwesigye/lunyoro-nllb_lun2en",
    "nllb_en2lun_pre_nyo": "keithtwesigye/lunyoro-nllb_en2lun",
    "nllb_lun2en_pre_nyo": "keithtwesigye/lunyoro-nllb_lun2en",
}

# Sentence-transformers semantic search model — downloaded to HF cache
SEM_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def download_all(force: bool = False):
    from huggingface_hub import snapshot_download

    for local_name, repo_id in HF_MODELS.items():
        dest = MODEL_DIR / local_name
        if dest.exists() and not force:
            has_weights = any(dest.glob("*.safetensors")) or any(dest.glob("*.bin"))
            if has_weights:
                print(
                    f"  [OK] {local_name} already exists - skipping (use --force to re-download)"
                )
                continue

        print(f"  ↓ Downloading {repo_id} → model/{local_name}/")
        dest.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest),
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
        )
        print(f"  [OK] {local_name} downloaded")

    # Download sem model into HF cache so it's available in offline mode
    print(f"  ↓ Downloading {SEM_MODEL_NAME} (semantic search)...")
    try:
        snapshot_download(repo_id=SEM_MODEL_NAME)
        print(f"  [OK] sem model cached")
    except Exception as e:
        print(f"  [FAIL] sem model download failed: {e}")


def download_dataset(force: bool = False):
    """Download training dataset CSVs from HuggingFace dataset repo."""
    from huggingface_hub import hf_hub_download, list_repo_files

    print(f"\n=== Downloading dataset from {DATASET_REPO} ===")

    try:
        repo_files = list(list_repo_files(DATASET_REPO, repo_type="dataset"))
    except Exception as e:
        print(f"  [FAIL] Could not list dataset repo files: {e}")
        return

    csv_files = [f for f in repo_files if f.endswith(".csv")]
    print(f"  Found {len(csv_files)} CSV files in dataset repo")

    for repo_path in sorted(csv_files):
        # repo_path is like "data/cleaned/english_nyoro_clean.csv"
        local_path = DATA_DIR / "/".join(repo_path.split("/")[1:]) if repo_path.startswith("data/") else DATA_DIR / repo_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        if local_path.exists() and not force:
            print(f"  [OK] {local_path.relative_to(DATA_DIR.parent)} already exists — skipping")
            continue

        print(f"  ↓ {repo_path} → {local_path.relative_to(DATA_DIR.parent)}")
        try:
            hf_hub_download(
                repo_id=DATASET_REPO,
                repo_type="dataset",
                filename=repo_path,
                local_dir=str(DATA_DIR.parent),
            )
            print(f"  [OK] {local_path.name}")
        except Exception as e:
            print(f"  [FAIL] {repo_path}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if model exists"
    )
    args = parser.parse_args()

    print("=== Downloading Runyoro-Rutooro models from HuggingFace ===")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Installing huggingface_hub...")
        os.system("pip install huggingface_hub")
        from huggingface_hub import snapshot_download

    download_all(force=args.force)
    download_dataset(force=args.force)
    print("\nAll models and data ready.")
