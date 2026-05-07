"""
upload_models_to_hf.py
======================
Upload translation models to HuggingFace Hub.

This removes the need for Git LFS storage and allows models to be
downloaded on-demand from HuggingFace's CDN.

Usage:
    python upload_models_to_hf.py --token YOUR_HF_TOKEN
"""
import os
import argparse
from pathlib import Path
from huggingface_hub import HfApi, create_repo

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

# HuggingFace organization/username
HF_USERNAME = os.getenv("HF_USERNAME", "keithtwesigye")

MODELS_TO_UPLOAD = {
    "en2lun": {
        "local_path": MODEL_DIR / "en2lun",
        "repo_name": f"{HF_USERNAME}/lunyoro-en2lun",
        "description": "English to Runyoro/Rutooro translation model (MarianMT)",
    },
    "lun2en": {
        "local_path": MODEL_DIR / "lun2en",
        "repo_name": f"{HF_USERNAME}/lunyoro-lun2en",
        "description": "Runyoro/Rutooro to English translation model (MarianMT)",
    },
    "nllb_en2lun": {
        "local_path": MODEL_DIR / "nllb_en2lun",
        "repo_name": f"{HF_USERNAME}/lunyoro-nllb-en2lun",
        "description": "English to Runyoro/Rutooro translation model (NLLB-200)",
    },
    "nllb_lun2en": {
        "local_path": MODEL_DIR / "nllb_lun2en",
        "repo_name": f"{HF_USERNAME}/lunyoro-nllb-lun2en",
        "description": "Runyoro/Rutooro to English translation model (NLLB-200)",
    },
    "sem_model": {
        "local_path": MODEL_DIR / "sem_model",
        "repo_name": f"{HF_USERNAME}/lunyoro-sentence-embeddings",
        "description": "Sentence embeddings model for semantic search (all-MiniLM-L6-v2)",
    },
}


def upload_model(model_info: dict, token: str):
    """Upload a model to HuggingFace Hub."""
    local_path = model_info["local_path"]
    repo_name = model_info["repo_name"]
    description = model_info["description"]
    
    if not local_path.exists():
        print(f"⚠️  Skipping {repo_name} - local path not found: {local_path}")
        return False
    
    print(f"\n📤 Uploading {repo_name}...")
    print(f"   Local: {local_path}")
    print(f"   Description: {description}")
    
    try:
        # Create repository
        api = HfApi()
        
        try:
            create_repo(
                repo_id=repo_name,
                token=token,
                repo_type="model",
                exist_ok=True,
            )
            print(f"   ✅ Repository created/verified")
        except Exception as e:
            print(f"   ⚠️  Repository creation: {e}")
        
        # Upload all files in the model directory
        api.upload_folder(
            folder_path=str(local_path),
            repo_id=repo_name,
            repo_type="model",
            token=token,
        )
        
        print(f"   ✅ Upload complete: https://huggingface.co/{repo_name}")
        return True
        
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Upload models to HuggingFace Hub")
    parser.add_argument("--token", type=str, help="HuggingFace API token")
    parser.add_argument("--username", type=str, help="HuggingFace username/org")
    parser.add_argument("--models", type=str, nargs="+", 
                        choices=list(MODELS_TO_UPLOAD.keys()) + ["all"],
                        default=["all"],
                        help="Which models to upload")
    
    args = parser.parse_args()
    
    # Get token
    token = args.token or os.getenv("HF_TOKEN")
    if not token:
        print("❌ Error: HuggingFace token required")
        print("   Set HF_TOKEN environment variable or use --token")
        return
    
    # Update username if provided
    if args.username:
        global HF_USERNAME
        HF_USERNAME = args.username
        for model_info in MODELS_TO_UPLOAD.values():
            model_info["repo_name"] = model_info["repo_name"].replace(
                model_info["repo_name"].split("/")[0], 
                HF_USERNAME
            )
    
    print(f"\n🚀 Uploading models to HuggingFace Hub")
    print(f"   Username: {HF_USERNAME}")
    print(f"   Models: {args.models}")
    
    # Determine which models to upload
    if "all" in args.models:
        models_to_process = MODELS_TO_UPLOAD.items()
    else:
        models_to_process = [(k, v) for k, v in MODELS_TO_UPLOAD.items() if k in args.models]
    
    # Upload models
    success_count = 0
    for model_name, model_info in models_to_process:
        if upload_model(model_info, token):
            success_count += 1
    
    print(f"\n✨ Upload complete: {success_count}/{len(models_to_process)} models uploaded")
    
    if success_count > 0:
        print("\n📝 Next steps:")
        print("   1. Update translate.py to load models from HuggingFace")
        print("   2. Remove model files from Git LFS")
        print("   3. Add model/ to .gitignore")
        print("   4. Commit and push changes")


if __name__ == "__main__":
    main()
