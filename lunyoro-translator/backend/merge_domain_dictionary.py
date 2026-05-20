"""
merge_domain_dictionary.py
==========================
Merges runyoro_domain_dictionary_clean.csv into training data.

Strategy:
  - Short english (<=4 words): direct translation pairs → train.csv / val.csv
  - Long english  (>4 words):  definitions/explanations → dictionary_lookup.csv
    (used by the retrieval fallback, NOT as MT training pairs)

Usage:
    python merge_domain_dictionary.py
"""
import pandas as pd
from pathlib import Path

DICT_CSV    = Path('data/cleaned/runyoro_domain_dictionary_clean.csv')
TRAIN_CSV   = Path('data/training/train.csv')
VAL_CSV     = Path('data/training/val.csv')
LOOKUP_CSV  = Path('data/cleaned/dictionary_lookup.csv')

# Max words in english side to be considered a direct translation
DIRECT_TRANSLATION_MAX_WORDS = 4


def main():
    dict_df = pd.read_csv(DICT_CSV)
    train   = pd.read_csv(TRAIN_CSV)
    val     = pd.read_csv(VAL_CSV)

    print(f"Clean dictionary  : {len(dict_df):,} entries")
    print(f"Existing train.csv: {len(train):,} pairs")
    print(f"Existing val.csv  : {len(val):,} pairs")

    # Split by word count
    dict_df['word_count'] = dict_df['english'].str.split().str.len()
    direct_df = dict_df[dict_df['word_count'] <= DIRECT_TRANSLATION_MAX_WORDS].copy()
    defn_df   = dict_df[dict_df['word_count'] >  DIRECT_TRANSLATION_MAX_WORDS].copy()

    print(f"\nDirect translations (<=4 words): {len(direct_df):,}")
    print(f"Definitions        (>4 words) : {len(defn_df):,}  → dictionary_lookup.csv only")

    # ── 1. Build tagged training pairs from direct translations only ──────────
    rows = []
    for _, r in direct_df.iterrows():
        domain  = str(r['domain']).strip().upper().replace(' ', '_').replace('&', 'AND')
        english = str(r['english']).strip()
        lunyoro = str(r['lunyoro']).strip()
        if not english or not lunyoro or english == 'nan' or lunyoro == 'nan':
            continue
        rows.append({'english': f'[{domain}] {english}', 'lunyoro': lunyoro})

    new_df = pd.DataFrame(rows)

    # Deduplicate against existing train + val
    existing_keys = set(
        zip(
            pd.concat([train, val])['english'].str.lower(),
            pd.concat([train, val])['lunyoro'].str.lower(),
        )
    )
    new_df = new_df[
        ~new_df.apply(
            lambda r: (r['english'].lower(), r['lunyoro'].lower()) in existing_keys,
            axis=1
        )
    ].reset_index(drop=True)

    print(f"New unique training pairs     : {len(new_df):,}")

    # 90/10 split
    split     = int(len(new_df) * 0.9)
    new_train = new_df.iloc[:split]
    new_val   = new_df.iloc[split:]

    # Backup originals
    train.to_csv(TRAIN_CSV.with_suffix('.csv.bak'), index=False)
    val.to_csv(VAL_CSV.with_suffix('.csv.bak'),     index=False)

    # Append and save
    updated_train = pd.concat([train, new_train], ignore_index=True)
    updated_val   = pd.concat([val,   new_val],   ignore_index=True)
    updated_train.to_csv(TRAIN_CSV, index=False)
    updated_val.to_csv(VAL_CSV,     index=False)

    # ── 2. Save definitions to dictionary_lookup.csv ─────────────────────────
    lookup = defn_df[['lunyoro', 'english', 'domain', 'pos']].copy()
    lookup.columns = ['word', 'definitionEnglish', 'domain', 'pos']
    lookup.to_csv(LOOKUP_CSV, index=False)

    # ── Report ────────────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("  MERGE REPORT")
    print("=" * 55)
    print(f"  Direct translation pairs added to train.csv : {len(new_train):,}")
    print(f"  Direct translation pairs added to val.csv   : {len(new_val):,}")
    print(f"  New train.csv total                         : {len(updated_train):,}")
    print(f"  New val.csv total                           : {len(updated_val):,}")
    print(f"  Definitions saved to dictionary_lookup.csv  : {len(lookup):,}")
    print("=" * 55)

    print("\nDomain breakdown of training pairs added:")
    domain_counts = new_df['english'].str.extract(r'^\[([^\]]+)\]')[0].value_counts()
    for domain, count in domain_counts.items():
        print(f"  {domain:<45} {count:>5,}")


if __name__ == '__main__':
    main()
