"""
merge_untrained_data.py
=======================
Finds all clean data not yet in train.csv/val.csv and merges it in.
Sources checked:
  - data/cleaned/*.csv  (english + lunyoro columns)
  - data/raw/proverbs_pairs.csv
  - data/raw/english_nyoro.csv / english_nyoro_root.csv
  - feedback/approved_pairs.csv
"""
import re
import csv
import pandas as pd
from pathlib import Path

BASE      = Path(__file__).parent / "data"
TRAIN_CSV = BASE / "training" / "train.csv"
VAL_CSV   = BASE / "training" / "val.csv"

def clean_text(t: str) -> str:
    t = str(t).strip()
    t = re.sub(r'\s+', ' ', t)
    return t

def load_existing_keys():
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)
    both  = pd.concat([train, val])
    return set(zip(
        both['english'].str.lower().str.strip(),
        both['lunyoro'].str.lower().str.strip()
    )), len(train), len(val)

def collect_new_pairs(existing_keys):
    new_pairs = []
    seen = set(existing_keys)
    stats = {}

    def add(source, en, lun):
        en  = clean_text(en)
        lun = clean_text(lun)
        if not en or not lun or len(en) < 2 or len(lun) < 2:
            return
        if en.lower() == lun.lower():
            return
        key = (en.lower(), lun.lower())
        if key in seen:
            return
        seen.add(key)
        new_pairs.append((en, lun))
        stats[source] = stats.get(source, 0) + 1

    # ── 1. Cleaned CSVs ───────────────────────────────────────────────────────
    for f in sorted((BASE / "cleaned").glob("*.csv")):
        try:
            df = pd.read_csv(f)
            if 'english' not in df.columns or 'lunyoro' not in df.columns:
                continue
            for _, r in df.iterrows():
                add(f.name, r['english'], r['lunyoro'])
        except Exception as e:
            print(f"  SKIP {f.name}: {e}")

    # ── 2. Raw proverbs ───────────────────────────────────────────────────────
    proverbs = BASE / "raw" / "proverbs_pairs.csv"
    if proverbs.exists():
        try:
            df = pd.read_csv(proverbs)
            en_col  = next((c for c in df.columns if 'english' in c.lower()), None)
            lun_col = next((c for c in df.columns if any(x in c.lower() for x in ['lunyoro','rutooro','runyoro','nyoro'])), None)
            if en_col and lun_col:
                for _, r in df.iterrows():
                    add("proverbs_pairs.csv", r[en_col], r[lun_col])
        except Exception as e:
            print(f"  SKIP proverbs_pairs.csv: {e}")

    # ── 3. Raw english_nyoro CSVs ─────────────────────────────────────────────
    for fname in ["english_nyoro.csv", "english_nyoro_root.csv"]:
        f = BASE / "raw" / fname
        if not f.exists():
            continue
        try:
            df = pd.read_csv(f)
            en_col  = next((c for c in df.columns if 'english' in c.lower()), None)
            lun_col = next((c for c in df.columns if any(x in c.lower() for x in ['lunyoro','rutooro','runyoro','nyoro'])), None)
            if en_col and lun_col:
                for _, r in df.iterrows():
                    add(fname, r[en_col], r[lun_col])
        except Exception as e:
            print(f"  SKIP {fname}: {e}")

    # ── 4. Feedback approved pairs ────────────────────────────────────────────
    fb = Path(__file__).parent / "feedback" / "approved_pairs.csv"
    if fb.exists():
        try:
            df = pd.read_csv(fb)
            if 'english' in df.columns and 'lunyoro' in df.columns:
                for _, r in df.iterrows():
                    add("approved_pairs.csv", r['english'], r['lunyoro'])
        except Exception as e:
            print(f"  SKIP approved_pairs.csv: {e}")

    return new_pairs, stats


def main():
    print("=== Merging untrained data into train.csv / val.csv ===\n")

    existing_keys, n_train, n_val = load_existing_keys()
    print(f"Current: train={n_train:,}  val={n_val:,}  total={n_train+n_val:,}")
    print(f"Existing keys: {len(existing_keys):,}\n")

    print("Scanning for new pairs...")
    new_pairs, stats = collect_new_pairs(existing_keys)

    print(f"\nNew pairs found by source:")
    for src, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {src:<50} {count:>7,}")
    print(f"\n  TOTAL new pairs: {len(new_pairs):,}")

    if not new_pairs:
        print("\nNothing new to add.")
        return

    # Backup
    import shutil
    shutil.copy(TRAIN_CSV, str(TRAIN_CSV) + ".bak")
    shutil.copy(VAL_CSV,   str(VAL_CSV)   + ".bak")

    # 90/10 split
    split     = int(len(new_pairs) * 0.9)
    new_train = new_pairs[:split]
    new_val   = new_pairs[split:]

    # Append
    with open(TRAIN_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        for en, lun in new_train:
            w.writerow([en, lun])

    with open(VAL_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        for en, lun in new_val:
            w.writerow([en, lun])

    # Verify
    t2 = pd.read_csv(TRAIN_CSV)
    v2 = pd.read_csv(VAL_CSV)
    print(f"\nNew totals: train={len(t2):,}  val={len(v2):,}  total={len(t2)+len(v2):,}")
    print(f"Added:      +{len(new_train):,} to train  +{len(new_val):,} to val")
    print("\nDone. Run augment_and_train.py --train-only to retrain on the new data.")


if __name__ == "__main__":
    main()
