"""
Standalone script to push any model to HuggingFace.
Usage:
    python push_models.py --model nllb_en2lun
    python push_models.py --model nllb_lun2en
    python push_models.py --model en2lun
    python push_models.py --model lun2en
    python push_models.py --all
"""
import os, argparse, logging
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "model"

HF_REPOS = {
    "en2lun":      "keithtwesigye/lunyoro-en2lun",
    "lun2en":      "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun": "keithtwesigye/lunyoro-nllb_en2lun",
    "nllb_lun2en": "keithtwesigye/lunyoro-nllb_lun2en",
}

def push(model_name: str):
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        log.error("HF_TOKEN not set in .env")
        return

    repo_id = HF_REPOS.get(model_name)
    if not repo_id:
        log.error(f"Unknown model: {model_name}. Valid: {list(HF_REPOS.keys())}")
        return

    model_path = MODEL_DIR / model_name
    if not model_path.is_dir():
        log.error(f"Model folder not found: {model_path}")
        return

    try:
        from huggingface_hub import HfApi
        log.info(f"Pushing {model_name} → {repo_id} ...")
        HfApi(token=hf_token).upload_folder(
            folder_path=str(model_path),
            repo_id=repo_id,
            repo_type="model",
            commit_message=f"Retrained {model_name} on cleaned+augmented+backtranslated data",
        )
        log.info(f"✓ {model_name} pushed to {repo_id}")
    except Exception as e:
        log.error(f"Push failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Model to push (en2lun, lun2en, nllb_en2lun, nllb_lun2en)")
    parser.add_argument("--all",   action="store_true", help="Push all models")
    args = parser.parse_args()

    if args.all:
        for name in HF_REPOS:
            push(name)
    elif args.model:
        push(args.model)
    else:
        parser.print_help()
