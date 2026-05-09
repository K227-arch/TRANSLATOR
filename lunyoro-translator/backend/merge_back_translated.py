"""
merge_back_translated.py
========================
Merges back-translated synthetic pairs into train.csv.
Deduplicates against existing pairs before merging.

Usage:
    python merge_back_translated.py [--input data/training/back_translated.csv]
"""
import os
import sys
import argparse
import pandas as pd

BASE     = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data", "training")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str,
                        default=os.path.join(DATA_DIR, "back_translated.csv"),
                        help="Source CSV with back-translated pairs to merge")
    parser.add_argument("--train", type=str,
                        default=os.path.join(DATA_DIR, "train.csv"))
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Source not found: {args.source}")
        sys.exit(1)

    train = pd.read_csv(args.train)
    synth = pd.read_csv(args.source)

    # Keep only english/lunyoro columns
    synth = synth[['english', 'lunyoro']].copy()

    before = len(train)
    merged = pd.concat([train, synth], ignore_index=True)
    merged = merged.drop_duplicates(subset=['english', 'lunyoro']).reset_index(drop=True)
    added  = len(merged) - before

    import shutil
    shutil.copy(args.train, args.train + ".bak")
    merged.to_csv(args.train, index=False, encoding='utf-8')

    print(f"train.csv: {before:,} → {len(merged):,} (+{added:,} synthetic pairs)")
    print(f"Backup saved to {args.train}.bak")


if __name__ == "__main__":
    main()
