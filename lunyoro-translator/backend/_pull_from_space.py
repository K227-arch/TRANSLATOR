"""
Pull backend source files from HuggingFace Space back to local repo.
Skips: model weights, large training data, .env, logs, temp files.

Usage:
    python _pull_from_space.py           # dry run (preview only)
    python _pull_from_space.py --apply   # actually download files
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

SPACE_ID = "keithtwesigye/runyoro-translator-api"
TOKEN = os.environ.get("HF_TOKEN", "")
LOCAL_DIR = Path(__file__).parent

# Files/patterns to SKIP (large data, secrets, temp files, logs)
SKIP_PATTERNS = {
    # model weights
    "model/en2lun", "model/lun2en", "model/nllb_en2lun", "model/nllb_lun2en",
    "model/nllb_en2lun_pre_nyo", "model/nllb_lun2en_pre_nyo",
    # training data (large)
    "data/training/train.csv", "data/training/val.csv", "data/training/test.csv",
    "data/training/new_only_train.csv", "data/training/new_only_val.csv",
    "data/training/back_translated.csv", "data/training/gr4_back_translated.csv",
    # augmented large files
    "data/cleaned/augmented_en2lun.csv", "data/cleaned/augmented_bt_lun2en.csv",
    "data/cleaned/augmented_bt_lun2en_clean.csv", "data/cleaned/back_translated_lun2en.csv",
    # secrets
    ".env",
    # logs
    "auto_retrain.log", "backend.log", "backend_out.log", "backend_run.log",
    "backend_run2.log", "backend_stdout.log", "feedback.jsonl",
}

SKIP_EXTENSIONS = {".bak", ".bak2", ".bak_bt", ".bak_en2lun_aug"}
SKIP_PREFIXES = ("logs/", "logs\\", "data\\training\\", "data/training/")
SKIP_SUFFIXES_IN_NAME = (".bak", ".bak2", "~$")

# Files to always include (source code + key assets)
INCLUDE_EXTENSIONS = {
    ".py", ".json", ".txt", ".md", ".sh", ".pkl",
    ".csv",  # small data files
}

# Specific files to always pull regardless of extension
ALWAYS_INCLUDE = {
    "model/translation_index.pkl",
    "model/sem_model/config.json",
    "model/sem_model/config_sentence_transformers.json",
    "model/sem_model/modules.json",
    "model/sem_model/sentence_bert_config.json",
    "model/sem_model/tokenizer.json",
    "model/sem_model/tokenizer_config.json",
    "requirements.txt",
    "docker-entrypoint.sh",
    "Dockerfile",
}


def should_skip(repo_path: str) -> bool:
    p = repo_path.replace("\\", "/")
    # Skip backslash-path duplicates (windows artifacts in the space)
    if "\\" in repo_path and repo_path.replace("\\", "/") != repo_path:
        return True
    for pat in SKIP_PATTERNS:
        if p.startswith(pat):
            return True
    for prefix in SKIP_PREFIXES:
        if p.startswith(prefix.replace("\\", "/")):
            return True
    name = Path(p).name
    for s in SKIP_SUFFIXES_IN_NAME:
        if s in name:
            return True
    ext = Path(p).suffix
    if ext in SKIP_EXTENSIONS:
        return False  # allowed
    if repo_path in ALWAYS_INCLUDE:
        return False
    # Skip unknown extensions (xlsx, docx, pdf, etc.)
    return True


def pull(apply: bool = False):
    from huggingface_hub import HfApi, hf_hub_download, list_repo_files

    api = HfApi(token=TOKEN)
    all_files = list(list_repo_files(SPACE_ID, repo_type="space", token=TOKEN))

    to_download = []
    for repo_path in sorted(all_files):
        clean = repo_path.replace("\\", "/")
        if should_skip(repo_path):
            continue
        to_download.append((repo_path, clean))

    print(f"{'[DRY RUN] ' if not apply else ''}Pulling {len(to_download)} files from {SPACE_ID}\n")

    failed = []
    for i, (repo_path, clean_path) in enumerate(to_download, 1):
        local_path = LOCAL_DIR / clean_path
        print(f"  [{i}/{len(to_download)}] {clean_path}", end=" ... ", flush=True)

        if not apply:
            print("(dry run)")
            continue

        for attempt in range(3):
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                hf_hub_download(
                    repo_id=SPACE_ID,
                    repo_type="space",
                    filename=repo_path,
                    local_dir=str(LOCAL_DIR),
                    token=TOKEN,
                )
                print("OK")
                break
            except Exception as e:
                if attempt < 2:
                    print(f"retry...", end=" ", flush=True)
                else:
                    print(f"FAILED: {e}")
                    failed.append(clean_path)

    print(f"\n{'='*60}")
    if not apply:
        print("Dry run complete. Run with --apply to download files.")
    elif failed:
        print(f"Done with {len(failed)} failures: {failed}")
    else:
        print(f"All {len(to_download)} files pulled successfully.")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    pull(apply=apply)
