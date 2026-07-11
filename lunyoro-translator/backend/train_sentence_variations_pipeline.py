"""
train_sentence_variations_pipeline.py
======================================
Training pipeline for 'sentence variations (2).xlsx':
  1. Load from raw Excel file and extract english-lunyoro pairs
  2. Clean the data (remove empty rows, normalize whitespace, deduplicate)
  3. Augment with domain tags
  4. Back-translate lun2en pairs using NLLB (optional)
  5. Merge all into training set
  6. Train both MarianMT and NLLB models

Usage:
    python train_sentence_variations_pipeline.py
    python train_sentence_variations_pipeline.py --skip-bt       # skip back-translation
    python train_sentence_variations_pipeline.py --skip-train    # only prep data
    python train_sentence_variations_pipeline.py --epochs 3      # fewer epochs
"""
import os
import sys
import argparse
import shutil
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
TRAINING_DIR = DATA_DIR / "training"

INPUT_FILE = RAW_DIR / "sentence variations (2).xlsx"
CLEAN_FILE = CLEANED_DIR / "sentence_variations_batch2_clean.csv"
AUG_FILE = CLEANED_DIR / "sentence_variations_batch2_augmented.csv"
BT_FILE = CLEANED_DIR / "sentence_variations_batch2_bt.csv"
MERGED_FILE = TRAINING_DIR / "sv_batch2_train.csv"
NEW_ONLY_FILE = TRAINING_DIR / "new_only_train.csv"


def step1_clean():
    """Load from Excel, extract pairs, clean: remove empty, normalize, deduplicate."""
    print("\n=== STEP 1: Load & Clean ===")
    print(f"  Source: {INPUT_FILE.name}")

    # Load Excel (no header row - first data row got used as columns)
    df_raw = pd.read_excel(INPUT_FILE, header=None)

    # Columns: 0=row_id, 1=group_id, 2=orig_en, 3=orig_tense, 4=orig_lun,
    #           5=target_tense, 6=varied_en, 7=varied_lun, 8=status
    # Extract the varied english-lunyoro pairs (cols 6 and 7)
    # Also include original pairs (cols 2 and 4) for more coverage
    varied_pairs = df_raw[[6, 7]].rename(columns={6: "english", 7: "lunyoro"})
    original_pairs = df_raw[[2, 4]].rename(columns={2: "english", 4: "lunyoro"})

    # Combine both original and varied pairs
    df = pd.concat([original_pairs, varied_pairs], ignore_index=True)
    print(f"  Raw pairs (original + varied): {len(df)}")

    # Remove empty
    df = df.dropna(subset=["english", "lunyoro"])
    df = df[df["english"].str.strip().astype(bool) & df["lunyoro"].str.strip().astype(bool)]

    # Normalize whitespace
    df["english"] = df["english"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["lunyoro"] = df["lunyoro"].str.strip().str.replace(r"\s+", " ", regex=True)

    # Lowercase normalization for lunyoro
    df["lunyoro"] = df["lunyoro"].str.lower()

    # Remove duplicates
    df = df.drop_duplicates(subset=["english", "lunyoro"])

    # Remove pairs where lunyoro is too short (< 3 words)
    df = df[df["lunyoro"].str.split().str.len() >= 3]

    df.to_csv(CLEAN_FILE, index=False)
    print(f"  Clean pairs: {len(df)} -> {CLEAN_FILE.name}")
    return df


def step2_augment(df: pd.DataFrame):
    """Augment with domain tag injection."""
    print("\n=== STEP 2: Augment ===")
    augmented = []

    # Domain tags relevant to the sentence content
    tags = ["[CULTURE]", "[DAILY_LIFE]", "[RELIGION]", "[GOVERNMENT]",
            "[AGRICULTURE]", "[HEALTH]", "[EDUCATION]", "[GENERAL]"]

    for _, row in df.iterrows():
        en, lun = row["english"], row["lunyoro"]
        augmented.append({"english": en, "lunyoro": lun})

        # Add 3 tagged versions per pair
        for tag in tags[:3]:
            augmented.append({"english": f"{tag} {en}", "lunyoro": lun})

    aug_df = pd.DataFrame(augmented).drop_duplicates(subset=["english", "lunyoro"])
    aug_df.to_csv(AUG_FILE, index=False)
    print(f"  Augmented pairs: {len(aug_df)} -> {AUG_FILE.name}")
    return aug_df


def step3_back_translate(df: pd.DataFrame):
    """Back-translate: translate lunyoro -> english using NLLB, create new pairs."""
    print("\n=== STEP 3: Back-translate ===")

    # Import NLLB directly to avoid sentence_transformers import issue
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
    except ImportError as e:
        print(f"  ✗ Cannot import transformers/torch: {e}")
        print("  Skipping back-translation.")
        return pd.DataFrame(columns=["english", "lunyoro"])

    # Load NLLB lun2en model
    MODEL_DIR = BASE / "model"
    model_path = MODEL_DIR / "nllb_lun2en_pre_nyo"

    if not model_path.exists():
        # Try HuggingFace Hub
        try:
            from huggingface_hub import snapshot_download
            print("  Downloading NLLB lun2en from HuggingFace...")
            model_path = snapshot_download(
                repo_id="keithtwesigye/lunyoro-nllb-lun2en",
                ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
            )
            print(f"  Cached at: {model_path}")
        except Exception as e:
            print(f"  ✗ Could not download NLLB model: {e}")
            print("  Skipping back-translation.")
            return pd.DataFrame(columns=["english", "lunyoro"])

    print(f"  Loading NLLB lun2en from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    load_dtype = torch.float16 if not torch.cuda.is_available() else torch.float32
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path), torch_dtype=load_dtype)
    model.eval()
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"  Model loaded on {device}")

    bt_pairs = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        lun = row["lunyoro"]
        try:
            inputs = tokenizer(lun, return_tensors="pt", max_length=256, truncation=True).to(device)
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_length=256,
                    num_beams=4,
                    early_stopping=True,
                )
            bt_en = tokenizer.decode(outputs[0], skip_special_tokens=True)
            if bt_en and bt_en.strip() and len(bt_en.split()) >= 3:
                bt_pairs.append({"english": bt_en, "lunyoro": lun})
        except Exception as e:
            if (i + 1) % 20 == 0:
                print(f"  Warning at row {i+1}: {e}")
            continue

        if (i + 1) % 20 == 0:
            print(f"  Back-translated {i+1}/{total} ({len(bt_pairs)} valid)")

    # Final progress
    print(f"  Back-translated {total}/{total} ({len(bt_pairs)} valid)")

    bt_df = pd.DataFrame(bt_pairs).drop_duplicates(subset=["english", "lunyoro"])
    bt_df.to_csv(BT_FILE, index=False)
    print(f"  Back-translated pairs: {len(bt_df)} -> {BT_FILE.name}")

    # Clean up GPU memory
    del model, tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return bt_df


def step4_merge(clean_df, aug_df, bt_df=None):
    """Merge all data into new_only_train.csv for --new-only training."""
    print("\n=== STEP 4: Merge ===")
    frames = [clean_df, aug_df]
    if bt_df is not None and len(bt_df) > 0:
        frames.append(bt_df)

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["english", "lunyoro"])
    merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save as new_only_train.csv (used by train scripts with --new-only flag)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_FILE, index=False)
    print(f"  Total merged: {len(merged)} -> {MERGED_FILE.name}")

    # Create a small val set (10% holdout)
    val_size = max(10, len(merged) // 10)
    val_df = merged.tail(val_size)
    train_df = merged.head(len(merged) - val_size)
    val_df.to_csv(TRAINING_DIR / "new_only_val.csv", index=False)
    train_df.to_csv(MERGED_FILE, index=False)
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}")
    return train_df


def step5_train(epochs: int):
    """Train both MarianMT and NLLB on the new data."""
    print("\n=== STEP 5: Train ===")

    # Copy our merged file to new_only_train.csv (what train scripts expect)
    try:
        if NEW_ONLY_FILE.exists():
            NEW_ONLY_FILE.unlink()
        shutil.copy2(MERGED_FILE, NEW_ONLY_FILE)
        print(f"  Copied {MERGED_FILE.name} -> {NEW_ONLY_FILE.name}")
    except PermissionError:
        try:
            # Try writing fresh content
            df = pd.read_csv(MERGED_FILE)
            df.to_csv(NEW_ONLY_FILE, index=False)
            print(f"  Overwrote {NEW_ONLY_FILE.name} with {len(df)} pairs")
        except PermissionError:
            # File is locked — train on the full dataset (which includes our new data appended)
            print(f"  ⚠ {NEW_ONLY_FILE.name} is locked by another process.")
            print(f"  Training directly on full dataset (train.csv) instead...")
            # Just run without --new-only to train on everything
            print(f"  Training MarianMT (both directions, {epochs} epochs)...")
            os.system(f'python "{BASE / "train_marian.py"}" --direction both --epochs {epochs}')
            print(f"\n  Training NLLB (en2lun, {epochs} epochs)...")
            os.system(f'python "{BASE / "train_nllb.py"}" --direction en2lun --epochs {epochs}')
            print(f"\n  Training NLLB (lun2en, {epochs} epochs)...")
            os.system(f'python "{BASE / "train_nllb.py"}" --direction lun2en --epochs {epochs} --min-lun-words 3')
            return

    print(f"  Training MarianMT (both directions, {epochs} epochs)...")
    os.system(f'python "{BASE / "train_marian.py"}" --direction both --epochs {epochs} --new-only')

    print(f"\n  Training NLLB (en2lun, {epochs} epochs)...")
    os.system(f'python "{BASE / "train_nllb.py"}" --direction en2lun --epochs {epochs} --new-only')

    print(f"\n  Training NLLB (lun2en, {epochs} epochs)...")
    os.system(f'python "{BASE / "train_nllb.py"}" --direction lun2en --epochs {epochs} --new-only --min-lun-words 3')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentence Variations Training Pipeline")
    parser.add_argument("--skip-bt", action="store_true", help="Skip back-translation step")
    parser.add_argument("--skip-train", action="store_true", help="Only prep data, skip training")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs (default: 5)")
    args = parser.parse_args()

    print("=" * 60)
    print("  SENTENCE VARIATIONS TRAINING PIPELINE")
    print(f"  Input: {INPUT_FILE.name}")
    print("=" * 60)

    # Step 1: Clean
    clean_df = step1_clean()

    # Step 2: Augment
    aug_df = step2_augment(clean_df)

    # Step 3: Back-translate (optional)
    bt_df = None
    if not args.skip_bt:
        bt_df = step3_back_translate(clean_df)
    else:
        print("\n=== STEP 3: Back-translate (SKIPPED) ===")

    # Step 4: Merge
    step4_merge(clean_df, aug_df, bt_df)

    # Step 5: Train
    if not args.skip_train:
        step5_train(args.epochs)
    else:
        print("\n=== STEP 5: Train (SKIPPED) ===")

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print(f"  Data saved to: {MERGED_FILE}")
    if not args.skip_train:
        print("  Models trained on cleaned + augmented + back-translated data")
    print("=" * 60)
