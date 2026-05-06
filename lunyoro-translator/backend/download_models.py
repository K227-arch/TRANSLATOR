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
    from huggingface_hub import snapshot_download

    for local_name, repo_id in HF_MODELS.items():
        dest = MODEL_DIR / local_name
        if dest.exists() and not force:
            has_weights = any(dest.glob("*.safetensors")) or any(dest.glob("*.bin"))
            if has_weights:
                print(f"  ✓ {local_name} already exists — skipping (use --force to re-download)")
                continue

        print(f"  ↓ Downloading {repo_id} → model/{local_name}/")
        dest.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest),
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
        )
        print(f"  ✓ {local_name} downloaded")

    # Download sem model into HF cache so it's available in offline mode
    print(f"  ↓ Downloading {SEM_MODEL_NAME} (semantic search)...")
    try:
        snapshot_download(repo_id=SEM_MODEL_NAME)
        print(f"  ✓ sem model cached")
    except Exception as e:
        print(f"  ✗ sem model download failed: {e}")


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
