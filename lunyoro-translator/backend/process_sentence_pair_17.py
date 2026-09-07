"""
process_sentence_pair_17.py
============================
Pipeline for 'sentence pair 17.xlsx':
  1. Load from raw Excel file and extract english-lunyoro pairs
  2. Clean the data (remove empty rows, normalize whitespace, deduplicate)
  3. Augment with domain tags
  4. Save cleaned CSV to data/cleaned/ so merge_untrained_data.py picks it up

Column layout (no header row):
  0: row_id
  1: group_id
  2: original english sentence
  3: original tense label
  4: original lunyoro sentence
  5: target tense label
  6: varied english sentence
  7: varied lunyoro sentence

Both original (cols 2,4) and varied (cols 6,7) pairs are extracted.

Usage:
    python process_sentence_pair_17.py
    python process_sentence_pair_17.py --skip-augment   # only clean, no tag augmentation
    python process_sentence_pair_17.py --merge          # also run merge_untrained_data.py
"""
import argparse
import re
import sys
import pandas as pd
from pathlib import Path

BASE        = Path(__file__).parent
DATA_DIR    = BASE / "data"
RAW_DIR     = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
TRAINING_DIR = DATA_DIR / "training"

INPUT_FILE = RAW_DIR / "sentence pair 17.xlsx"
CLEAN_FILE = CLEANED_DIR / "sentence_pair_17_clean.csv"
AUG_FILE   = CLEANED_DIR / "sentence_pair_17_augmented.csv"


# ── Domain tags injected during augmentation ──────────────────────────────────
# Kept to the most relevant ones for this tense-variation dataset
DOMAIN_TAGS = [
    "[GENERAL]",
    "[DAILY_LIFE]",
    "[EDUCATION]",
    "[AGRICULTURE]",
    "[ENVIRONMENT]",
    "[CULTURE]",
]


def _normalise(text: str) -> str:
    """Strip, collapse whitespace, normalise curly quotes."""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    # Normalise curly apostrophes / quotes to straight ones
    text = (text
            .replace("\u2018", "'").replace("\u2019", "'")
            .replace("\u201c", '"').replace("\u201d", '"')
            .replace("\u02bc", "'"))
    return text


def step1_clean() -> pd.DataFrame:
    """Load Excel, extract both original and varied pairs, clean and deduplicate."""
    print("\n=== STEP 1: Load & Clean ===")
    print(f"  Source: {INPUT_FILE.name}")

    if not INPUT_FILE.exists():
        print(f"  ERROR: {INPUT_FILE} not found.")
        sys.exit(1)

    # No header row — first row is data
    df_raw = pd.read_excel(INPUT_FILE, header=None)
    print(f"  Raw rows: {len(df_raw)}")

    # Columns: 0=row_id, 1=group_id, 2=orig_en, 3=orig_tense,
    #          4=orig_lun, 5=target_tense, 6=varied_en, 7=varied_lun
    original_pairs = df_raw[[2, 4]].rename(columns={2: "english", 4: "lunyoro"})
    varied_pairs   = df_raw[[6, 7]].rename(columns={6: "english", 7: "lunyoro"})

    df = pd.concat([original_pairs, varied_pairs], ignore_index=True)
    print(f"  Combined pairs (original + varied): {len(df)}")

    # Drop rows where either column is empty / NaN
    df = df.dropna(subset=["english", "lunyoro"])
    df = df[
        df["english"].str.strip().astype(bool) &
        df["lunyoro"].str.strip().astype(bool)
    ]

    # Normalise
    df["english"] = df["english"].apply(_normalise)
    df["lunyoro"] = df["lunyoro"].apply(_normalise)

    # Lowercase lunyoro (consistent with existing pipeline)
    df["lunyoro"] = df["lunyoro"].str.lower()

    # Drop identical en==lun pairs (passthrough noise)
    df = df[df["english"].str.lower() != df["lunyoro"].str.lower()]

    # Deduplicate
    df = df.drop_duplicates(subset=["english", "lunyoro"])

    # Require at least 3 Lunyoro tokens (single-word entries are not useful)
    df = df[df["lunyoro"].str.split().str.len() >= 3]

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_FILE, index=False)
    print(f"  Clean pairs: {len(df)} -> {CLEAN_FILE.name}")
    return df


def step2_augment(df: pd.DataFrame) -> pd.DataFrame:
    """Inject domain tags to create additional training variants."""
    print("\n=== STEP 2: Augment with domain tags ===")

    augmented = df.to_dict("records")  # start with the originals

    for row in df.itertuples(index=False):
        en, lun = row.english, row.lunyoro
        for tag in DOMAIN_TAGS[:3]:  # 3 tags per pair keeps the set manageable
            augmented.append({"english": f"{tag} {en}", "lunyoro": lun})

    aug_df = pd.DataFrame(augmented).drop_duplicates(subset=["english", "lunyoro"])
    aug_df.to_csv(AUG_FILE, index=False)
    print(f"  Augmented pairs: {len(aug_df)} -> {AUG_FILE.name}")
    return aug_df


def step3_merge():
    """Run merge_untrained_data.py to fold new CSVs into train.csv / val.csv."""
    print("\n=== STEP 3: Merge into training set ===")
    import subprocess
    result = subprocess.run(
        [sys.executable, str(BASE / "merge_untrained_data.py")],
        capture_output=False,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Process sentence pair 17.xlsx")
    parser.add_argument("--skip-augment", action="store_true",
                        help="Skip domain-tag augmentation step")
    parser.add_argument("--merge", action="store_true",
                        help="Run merge_untrained_data.py after processing")
    args = parser.parse_args()

    print("=" * 60)
    print("  SENTENCE PAIR 17 — INGESTION PIPELINE")
    print(f"  Input: {INPUT_FILE.name}")
    print("=" * 60)

    clean_df = step1_clean()

    if not args.skip_augment:
        step2_augment(clean_df)

    if args.merge:
        ok = step3_merge()
        if not ok:
            print("\n  WARNING: merge step returned a non-zero exit code.")

    print("\n" + "=" * 60)
    print("  DONE")
    print(f"  Cleaned CSV : {CLEAN_FILE}")
    if not args.skip_augment:
        print(f"  Augmented   : {AUG_FILE}")
    print()
    print("  Next steps:")
    print("    1. Review the CSVs above for quality")
    print("    2. Run:  python merge_untrained_data.py")
    print("    3. Run:  python augment_and_train.py --train-only")
    print("=" * 60)


if __name__ == "__main__":
    main()
