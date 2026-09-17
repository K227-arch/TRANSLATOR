"""
Standalone script to push any model to HuggingFace.
Usage:
    python push_models.py --model nllb_en2lun
    python push_models.py --model nllb_lun2en
    python push_models.py --model en2lun
    python push_models.py --model lun2en
    python push_models.py --all          # PyTorch base models only
    python push_models.py --all-variants # PyTorch + ONNX FP32 + ONNX INT8

ONNX/INT8 variants are uploaded as subfolders within the same HF repo:
    keithtwesigye/lunyoro-nllb-en2lun/onnx/      ← FP32 ONNX
    keithtwesigye/lunyoro-nllb-en2lun/onnx_int8/ ← INT8 ONNX
    keithtwesigye/lunyoro-en2lun/onnx/            ← MarianMT ONNX
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

# Base PyTorch model dirs → HF repos
HF_REPOS = {
    "en2lun":      "keithtwesigye/lunyoro-en2lun",
    "lun2en":      "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun": "keithtwesigye/lunyoro-nllb-en2lun",
    "nllb_lun2en": "keithtwesigye/lunyoro-nllb-lun2en",
}

# ONNX/INT8 variants: (local_dir, repo_id, path_in_repo, commit_message)
HF_VARIANT_UPLOADS = [
    # MarianMT ONNX FP32
    ("en2lun_onnx",       "keithtwesigye/lunyoro-en2lun",       "onnx",       "Add ONNX FP32 export (en2lun)"),
    ("lun2en_onnx",       "keithtwesigye/lunyoro-lun2en",       "onnx",       "Add ONNX FP32 export (lun2en)"),
    # NLLB ONNX FP32
    ("nllb_en2lun_onnx",  "keithtwesigye/lunyoro-nllb-en2lun",  "onnx",       "Add ONNX FP32 export (nllb_en2lun)"),
    ("nllb_lun2en_onnx",  "keithtwesigye/lunyoro-nllb-lun2en",  "onnx",       "Add ONNX FP32 export (nllb_lun2en)"),
    # NLLB ONNX INT8
    ("nllb_en2lun_int8",  "keithtwesigye/lunyoro-nllb-en2lun",  "onnx_int8",  "Add ONNX INT8 quantized model (nllb_en2lun)"),
    ("nllb_lun2en_int8",  "keithtwesigye/lunyoro-nllb-lun2en",  "onnx_int8",  "Add ONNX INT8 quantized model (nllb_lun2en)"),
]


def _hf_api():
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        raise RuntimeError("HF_TOKEN not set in .env")
    # Ensure offline mode is disabled for uploads
    for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
        os.environ.pop(key, None)
        os.environ[key] = "0"
    from huggingface_hub import HfApi
    return HfApi(token=hf_token)


def push(model_name: str):
    repo_id = HF_REPOS.get(model_name)
    if not repo_id:
        log.error(f"Unknown model: {model_name}. Valid: {list(HF_REPOS.keys())}")
        return False

    model_path = MODEL_DIR / model_name
    if not model_path.is_dir():
        log.error(f"Model folder not found: {model_path}")
        return False

    try:
        api = _hf_api()
        log.info(f"Pushing {model_name} → {repo_id} ...")
        api.upload_folder(
            folder_path=str(model_path),
            repo_id=repo_id,
            repo_type="model",
            commit_message=f"Retrained {model_name} on cleaned+augmented+backtranslated data",
        )
        log.info(f"✓ {model_name} pushed to {repo_id}")
        return True
    except Exception as e:
        log.error(f"Push failed: {e}")
        return False


def push_variant(local_dir: str, repo_id: str, path_in_repo: str, commit_msg: str):
    model_path = MODEL_DIR / local_dir
    if not model_path.is_dir():
        log.error(f"Variant folder not found: {model_path}")
        return False

    try:
        api = _hf_api()
        log.info(f"Pushing {local_dir} → {repo_id}/{path_in_repo} ...")
        api.upload_folder(
            folder_path=str(model_path),
            repo_id=repo_id,
            path_in_repo=path_in_repo,
            repo_type="model",
            commit_message=commit_msg,
        )
        log.info(f"✓ {local_dir} pushed to {repo_id}/{path_in_repo}")
        return True
    except Exception as e:
        log.error(f"Push failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Base PyTorch model to push (en2lun, lun2en, nllb_en2lun, nllb_lun2en)")
    parser.add_argument("--all",          action="store_true", help="Push all base PyTorch models")
    parser.add_argument("--all-variants", action="store_true", help="Push all base models + ONNX FP32 + ONNX INT8")
    args = parser.parse_args()

    if args.all_variants:
        log.info("=== Pushing base PyTorch models ===")
        for name in HF_REPOS:
            push(name)
        log.info("=== Pushing ONNX/INT8 variants ===")
        for local_dir, repo_id, path_in_repo, commit_msg in HF_VARIANT_UPLOADS:
            push_variant(local_dir, repo_id, path_in_repo, commit_msg)
    elif args.all:
        for name in HF_REPOS:
            push(name)
    elif args.model:
        push(args.model)
    else:
        parser.print_help()
