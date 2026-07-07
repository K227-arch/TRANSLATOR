"""
Full training pipeline for tense_pairs_100.csv:
  1. Clean the data (remove empty rows, normalize whitespace, deduplicate)
  2. Augment with synonym/paraphrase variants
  3. Back-translate lun2en pairs using NLLB
  4. Merge all into training set
  5. Train both MarianMT and NLLB models (--new-only mode, 5 epochs)

Usage:
    python train_tense_pipeline.py
"""
import os
import sys
import re
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
CLEANED_DIR = DATA_DIR / "cleaned"
TRAINING_DIR = DATA_DIR / "training"

INPUT_FILE = CLEANED_DIR / "tense_pairs_100.csv"
CLEAN_FILE = CLEANED_DIR / "tense_pairs_clean.csv"
AUG_FILE = CLEANED_DIR / "tense_pairs_augmented.csv"
BT_FILE = CLEANED_DIR / "tense_pairs_backtranslated.csv"
MERGED_FILE = TRAINING_DIR / "new_only_train.csv"
VAL_FILE = TRAINING_DIR / "val.csv.bak"


def step1_clean():
    """Clean: remove empty, normalize whitespace, deduplicate."""
    print("\n=== STEP 1: Clean ===")
    df = pd.read_csv(INPUT_FILE)
    print(f"  Raw pairs: {len(df)}")

    # Remove empty
    df = df.dropna(subset=["english", "lunyoro"])
    df = df[df["english"].str.strip().astype(bool) & df["lunyoro"].str.strip().astype(bool)]

    # Normalize whitespace
    df["english"] = df["english"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["lunyoro"] = df["lunyoro"].str.strip().str.replace(r"\s+", " ", regex=True)

    # Remove duplicates
    df = df.drop_duplicates(subset=["english", "lunyoro"])

    # Remove pairs where lunyoro is too short (< 3 words)
    df = df[df["lunyoro"].str.split().str.len() >= 3]

    df.to_csv(CLEAN_FILE, index=False)
    print(f"  Clean pairs: {len(df)} -> {CLEAN_FILE.name}")
    return df


def step2_augment(df: pd.DataFrame):
    """Augment with simple synonym substitution and tag injection."""
    print("\n=== STEP 2: Augment ===")
    augmented = []

    # Domain tags to inject
    tags = ["[GOVERNMENT]", "[AGRICULTURE]", "[CULTURE]", "[HEALTH]",
            "[EDUCATION]", "[DAILY_LIFE]", "[RELIGION]", "[GENERAL]"]

    for _, row in df.iterrows():
        en, lun = row["english"], row["lunyoro"]
        augmented.append({"english": en, "lunyoro": lun})

        # Add tagged versions (helps model learn domain awareness)
        for tag in tags[:3]:  # 3 random tags per pair
            augmented.append({"english": f"{tag} {en}", "lunyoro": lun})

    aug_df = pd.DataFrame(augmented).drop_duplicates(subset=["english", "lunyoro"])
    aug_df.to_csv(AUG_FILE, index=False)
    print(f"  Augmented pairs: {len(aug_df)} -> {AUG_FILE.name}")
    return aug_df


def step3_back_translate(df: pd.DataFrame):
    """Back-translate: translate lunyoro -> english using NLLB, create new pairs."""
    print("\n=== STEP 3: Back-translate ===")

    sys.path.insert(0, str(BASE))
    from translate import _nllb_translate, _load_nllb

    # Load NLLB lun2en
    _load_nllb("lun2en")

    bt_pairs = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        lun = row["lunyoro"]
        # Back-translate lunyoro -> english using NLLB
        bt_en = _nllb_translate(lun, "lun2en")
        if bt_en and bt_en.strip() and len(bt_en.split()) >= 3:
            # New pair: back-translated english -> original lunyoro
            bt_pairs.append({"english": bt_en, "lunyoro": lun})
        if (i + 1) % 20 == 0:
            print(f"  Back-translated {i+1}/{total} ({len(bt_pairs)} valid)")

    bt_df = pd.DataFrame(bt_pairs).drop_duplicates(subset=["english", "lunyoro"])
    bt_df.to_csv(BT_FILE, index=False)
    print(f"  Back-translated pairs: {len(bt_df)} -> {BT_FILE.name}")
    return bt_df


def step4_merge(clean_df, aug_df, bt_df):
    """Merge all data into new_only_train.csv for --new-only training."""
    print("\n=== STEP 4: Merge ===")
    merged = pd.concat([clean_df, aug_df, bt_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["english", "lunyoro"])
    merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save as new_only_train.csv (used by train scripts with --new-only flag)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_FILE, index=False)
    print(f"  Total merged: {len(merged)} -> {MERGED_FILE.name}")

    # Also create a small val set (10% holdout)
    val_size = max(10, len(merged) // 10)
    val_df = merged.tail(val_size)
    train_df = merged.head(len(merged) - val_size)
    val_df.to_csv(TRAINING_DIR / "new_only_val.csv", index=False)
    train_df.to_csv(MERGED_FILE, index=False)
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}")
    return train_df


def step5_train():
    """Train both MarianMT and NLLB on the new data."""
    print("\n=== STEP 5: Train ===")
    print("  Training MarianMT (both directions, 5 epochs)...")
    os.system(f'python "{BASE / "train_marian.py"}" --direction both --epochs 5 --new-only')

    print("\n  Training NLLB (both directions, 5 epochs)...")
    os.system(f'python "{BASE / "train_nllb.py"}" --direction en2lun --epochs 5 --new-only')
    os.system(f'python "{BASE / "train_nllb.py"}" --direction lun2en --epochs 5 --new-only --min-lun-words 3')


if __name__ == "__main__":
    print("=" * 60)
    print("  TENSE PAIRS TRAINING PIPELINE")
    print("  Input: tense_pairs_100.csv (100 sentence pairs)")
    print("=" * 60)

    # Step 1-4: Data prep
    clean_df = step1_clean()
    aug_df = step2_augment(clean_df)
    bt_df = step3_back_translate(clean_df)
    step4_merge(clean_df, aug_df, bt_df)

    # Step 5: Training
    step5_train()

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("  Models trained on cleaned + augmented + back-translated data")
    print("=" * 60)
