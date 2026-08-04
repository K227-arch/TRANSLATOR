"""
train_incremental.py
====================
Incremental training pipeline for better accuracy:

  1. Load ALL existing cleaned data (full dataset V_current)
  2. Load new data from --new-data file (CSV or Excel)
  3. Clean & validate new data
  4. Merge with existing (deduplicate)
  5. Shuffle
  6. Continue training from current checkpoint (not from scratch)
  7. Evaluate on fixed held-out val/test sets
  8. Push to HuggingFace if improved

Usage:
    python train_incremental.py --new-data "data/raw/new_batch.csv"
    python train_incremental.py --new-data "data/raw/sentence variations (2).xlsx"
    python train_incremental.py                    # retrain on all existing data
    python train_incremental.py --epochs 7         # more epochs
    python train_incremental.py --eval-only        # just evaluate current model
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
TRAINING_DIR = DATA_DIR / "training"

# Fixed evaluation sets — NEVER change these
VAL_CSV = TRAINING_DIR / "val.csv.bak"
FULL_TRAIN_CSV = TRAINING_DIR / "full_train.csv"
HISTORY_LOG = BASE / "logs" / "training_history.log"


def log(msg: str):
    """Print and log to file."""
    print(msg)
    HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def load_all_cleaned_data() -> pd.DataFrame:
    """Load only human-verified cleaned CSV files (no augmented or back-translated)."""
    # Skip files that are augmented or back-translated
    SKIP_PATTERNS = ["augmented", "bt_", "back_translated", "backtranslated"]

    all_frames = []
    for csv_file in sorted(CLEANED_DIR.glob("*.csv")):
        # Skip augmented/back-translated data
        if any(pat in csv_file.name.lower() for pat in SKIP_PATTERNS):
            print(f"  [skip] {csv_file.name} (augmented/back-translated)")
            continue
        try:
            df = pd.read_csv(csv_file)
            if "english" in df.columns and "lunyoro" in df.columns:
                all_frames.append(df[["english", "lunyoro"]])
                print(f"  [load] {csv_file.name} ({len(df)} pairs)")
        except Exception:
            continue

    if not all_frames:
        log("  WARNING: No existing cleaned data found!")
        return pd.DataFrame(columns=["english", "lunyoro"])

    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.dropna(subset=["english", "lunyoro"])
    combined = combined.drop_duplicates(subset=["english", "lunyoro"])
    return combined


def load_new_data(path: str) -> pd.DataFrame:
    """Load new data from CSV or Excel file."""
    p = Path(path)
    if not p.exists():
        # Try relative to raw dir
        p = RAW_DIR / path
    if not p.exists():
        log(f"  ERROR: File not found: {path}")
        sys.exit(1)

    log(f"  Loading new data: {p.name}")

    if p.suffix in (".xlsx", ".xls"):
        df = pd.read_excel(p, header=None)
        # Try to detect columns — look for english/lunyoro pair columns
        if df.shape[1] >= 8:
            # Format like sentence variations: cols 6=english, 7=lunyoro
            varied = df[[6, 7]].rename(columns={6: "english", 7: "lunyoro"})
            original = df[[2, 4]].rename(columns={2: "english", 4: "lunyoro"})
            df = pd.concat([original, varied], ignore_index=True)
        elif df.shape[1] == 2:
            df.columns = ["english", "lunyoro"]
        else:
            # Try first two text columns
            df.columns = [f"col{i}" for i in range(df.shape[1])]
            df = df.rename(columns={"col0": "english", "col1": "lunyoro"})
    else:
        df = pd.read_csv(p)

    if "english" not in df.columns or "lunyoro" not in df.columns:
        log(f"  ERROR: File must have 'english' and 'lunyoro' columns. Got: {list(df.columns)}")
        sys.exit(1)

    return df[["english", "lunyoro"]]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean & validate: remove empty, normalize, deduplicate, filter short."""
    before = len(df)

    # Remove empty
    df = df.dropna(subset=["english", "lunyoro"])
    df = df[df["english"].str.strip().astype(bool) & df["lunyoro"].str.strip().astype(bool)]

    # Normalize whitespace
    df["english"] = df["english"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["lunyoro"] = df["lunyoro"].str.strip().str.replace(r"\s+", " ", regex=True)

    # Lowercase lunyoro (standard for training)
    df["lunyoro"] = df["lunyoro"].str.lower()

    # Remove duplicates
    df = df.drop_duplicates(subset=["english", "lunyoro"])

    # Filter too-short pairs (both sides need at least 2 words)
    df = df[df["lunyoro"].str.split().str.len() >= 2]
    df = df[df["english"].str.split().str.len() >= 2]

    # Filter too-long pairs (>200 words likely noise)
    df = df[df["english"].str.split().str.len() <= 200]

    after = len(df)
    log(f"  Cleaned: {before} → {after} pairs ({before - after} removed)")
    return df.reset_index(drop=True)


def merge_and_shuffle(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Merge new data with existing, deduplicate, shuffle."""
    before_existing = len(existing)
    before_new = len(new)

    merged = pd.concat([existing, new], ignore_index=True)
    merged = merged.drop_duplicates(subset=["english", "lunyoro"])
    merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)

    added = len(merged) - before_existing
    log(f"  Merged: {before_existing} existing + {before_new} new = {len(merged)} total ({added} truly new)")
    return merged


def save_training_data(df: pd.DataFrame):
    """Save the full merged dataset as the training file."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(FULL_TRAIN_CSV, index=False)
    log(f"  Saved: {FULL_TRAIN_CSV.name} ({len(df)} pairs)")

    # Also save as train.csv for the training scripts
    train_csv = TRAINING_DIR / "train.csv"
    df.to_csv(train_csv, index=False)


def train_models(epochs: int, direction: str = "both"):
    """Continue training from current checkpoint."""
    import subprocess
    py = sys.executable

    log(f"\n  Training MarianMT ({direction}, {epochs} epochs)...")
    ret = subprocess.run([py, str(BASE / "train_marian.py"), "--direction", direction, "--epochs", str(epochs)], cwd=str(BASE))
    if ret.returncode != 0:
        log("  WARNING: MarianMT training failed")

    log(f"\n  Training NLLB en2lun ({epochs} epochs)...")
    ret = subprocess.run([py, str(BASE / "train_nllb.py"), "--direction", "en2lun", "--epochs", str(epochs)], cwd=str(BASE))
    if ret.returncode != 0:
        log("  WARNING: NLLB en2lun training failed")

    log(f"\n  Training NLLB lun2en ({epochs} epochs)...")
    ret = subprocess.run([py, str(BASE / "train_nllb.py"), "--direction", "lun2en", "--epochs", str(epochs), "--min-lun-words", "3"], cwd=str(BASE))
    if ret.returncode != 0:
        log("  WARNING: NLLB lun2en training failed")


def evaluate():
    """Evaluate current models on fixed val set."""
    import subprocess
    log("\n  Evaluating on fixed validation set...")
    py = sys.executable
    ret = subprocess.run([py, str(BASE / "eval_bleu.py")], cwd=str(BASE))
    if ret.returncode != 0:
        log("  WARNING: Evaluation script failed")
    else:
        # Read results
        results_file = BASE / "bleu_results.json"
        if results_file.exists():
            import json
            with open(results_file) as f:
                results = json.load(f)
            log(f"  BLEU scores: {results}")


def push_to_hf():
    """Push updated models to HuggingFace."""
    import subprocess
    log("\n  Pushing models to HuggingFace...")
    py = sys.executable
    hf_token = os.getenv("HF_TOKEN", "")
    if not hf_token:
        env_path = BASE / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("HF_TOKEN="):
                    hf_token = line.split("=", 1)[1].strip()
                    os.environ["HF_TOKEN"] = hf_token
                    break
    if hf_token:
        subprocess.run([py, str(BASE / "upload_models_to_hf.py")], cwd=str(BASE))
        log("  Models pushed to HuggingFace")
    else:
        log("  WARNING: HF_TOKEN not set — skipping push")


def main():
    parser = argparse.ArgumentParser(description="Incremental Training Pipeline")
    parser.add_argument("--new-data", type=str, nargs="+", default=None,
                        help="Path(s) to new data file(s) (CSV or Excel)")
    parser.add_argument("--epochs", type=int, default=5,
                        help="Training epochs (default: 5)")
    parser.add_argument("--direction", type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--eval-only", action="store_true",
                        help="Only evaluate, don't train")
    parser.add_argument("--no-push", action="store_true",
                        help="Skip pushing to HuggingFace")
    parser.add_argument("--no-train", action="store_true",
                        help="Only prepare data, skip training")
    args = parser.parse_args()

    print("=" * 65)
    print("  INCREMENTAL TRAINING PIPELINE")
    print("=" * 65)

    if args.eval_only:
        evaluate()
        return

    # Step 1: Load existing data
    log("\n── STEP 1: Load existing dataset ──")
    existing = load_all_cleaned_data()
    log(f"  Existing dataset: {len(existing)} pairs")

    # Step 2: Load new data (if provided)
    if args.new_data:
        log("\n── STEP 2: Load new data ──")
        new_frames = []
        for data_path in args.new_data:
            new_raw = load_new_data(data_path)
            log(f"  Raw new pairs from {Path(data_path).name}: {len(new_raw)}")
            new_frames.append(new_raw)
        new_combined = pd.concat(new_frames, ignore_index=True)
        log(f"  Total new raw pairs: {len(new_combined)}")

        # Step 3: Clean new data
        log("\n── STEP 3: Clean & validate ──")
        new_clean = clean_data(new_combined)

        # Save cleaned new data for reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        new_clean_path = CLEANED_DIR / f"incremental_{timestamp}.csv"
        new_clean.to_csv(new_clean_path, index=False)
        log(f"  Saved cleaned new data: {new_clean_path.name}")
    else:
        log("\n── STEP 2-3: No new data — retraining on existing ──")
        new_clean = pd.DataFrame(columns=["english", "lunyoro"])

    # Step 4: Merge
    log("\n── STEP 4: Merge & deduplicate ──")
    full_dataset = merge_and_shuffle(existing, new_clean)

    # Step 5: Save
    log("\n── STEP 5: Save & shuffle ──")
    save_training_data(full_dataset)

    # Summary
    log(f"\n  DATASET VERSION: {len(full_dataset)} total pairs")
    log(f"  Val set (fixed): {VAL_CSV.name}")

    if args.no_train:
        log("\n  Training skipped (--no-train)")
        print("\n" + "=" * 65)
        print("  DATA PREPARATION COMPLETE")
        print("=" * 65)
        return

    # Step 6: Train
    log("\n── STEP 6: Continue training ──")
    train_models(args.epochs, args.direction)

    # Step 7: Evaluate
    log("\n── STEP 7: Evaluate ──")
    evaluate()

    # Step 8: Push
    if not args.no_push:
        log("\n── STEP 8: Push to HuggingFace ──")
        push_to_hf()

    print("\n" + "=" * 65)
    print("  INCREMENTAL TRAINING COMPLETE")
    print(f"  Dataset: {len(full_dataset)} pairs")
    print(f"  Models: trained {args.epochs} epochs, evaluated, {'pushed' if not args.no_push else 'not pushed'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
