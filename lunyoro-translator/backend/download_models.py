"""
Downloads all fine-tuned Runyoro-Rutooro models from HuggingFace.
Run this once after cloning the repo:

    python download_models.py

Models pulled:
    keithtwesigye/lunyoro-en2lun      → model/en2lun/
    keithtwesigye/lunyoro-lun2en      → model/lun2en/
    keithtwesigye/lunyoro-nllb_en2lun → model/nllb_en2lun/
    keithtwesigye/lunyoro-nllb_lun2en → model/nllb_lun2en/
    sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 → model/sem_model/
"""
import os
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "model"

HF_MODELS = {
    "en2lun":      "keithtwesigye/lunyoro-en2lun",
    "lun2en":      "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun": "keithtwesigye/lunyoro-nllb_en2lun",
    "nllb_lun2en": "keithtwesigye/lunyoro-nllb_lun2en",
}

# Sentence-transformers semantic search model — downloaded to HF cache
SEM_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def download_all(force: bool = False):
    """
    Sync all models from HuggingFace.
    - Without --force: only downloads files that are new or changed (delta sync).
    - With --force: re-downloads everything regardless.
    Uses snapshot_download with local_dir, which compares file hashes and skips
    unchanged files automatically.
    """
    from huggingface_hub import snapshot_download

    for local_name, repo_id in HF_MODELS.items():
        dest = MODEL_DIR / local_name
        dest.mkdir(parents=True, exist_ok=True)

        if not force:
            has_weights = any(dest.glob("*.safetensors")) or any(dest.glob("*.bin"))
            if has_weights:
                print(f"  ↻ Checking {repo_id} for updates...")
            else:
                print(f"  ↓ Downloading {repo_id} → model/{local_name}/")
        else:
            print(f"  ↓ Force re-downloading {repo_id} → model/{local_name}/")

        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest),
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
        )
        print(f"  ✓ {local_name} up to date")

    # Semantic search model
    print(f"  ↻ Checking {SEM_MODEL_NAME} for updates...")
    try:
        snapshot_download(repo_id=SEM_MODEL_NAME)
        print(f"  ✓ sem model up to date")
    except Exception as e:
        print(f"  ✗ sem model sync failed: {e}")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-download even if model exists")
    args = parser.parse_args()

    print("=== Downloading Runyoro-Rutooro models from HuggingFace ===")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Installing huggingface_hub...")
        os.system("pip install huggingface_hub")
        from huggingface_hub import snapshot_download

    download_all(force=args.force)
    print("\nAll models ready.")
