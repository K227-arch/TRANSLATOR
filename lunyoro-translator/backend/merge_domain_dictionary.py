"""
merge_domain_dictionary.py
==========================
Merges runyoro_domain_dictionary_clean.csv into train.csv and val.csv
using a 90/10 split. Domain tags are added as [DOMAIN] prefixes.

Usage:
    python merge_domain_dictionary.py
"""
import pandas as pd
from pathlib import Path

DICT_CSV  = Path('data/cleaned/runyoro_domain_dictionary_clean.csv')
TRAIN_CSV = Path('data/training/train.csv')
VAL_CSV   = Path('data/training/val.csv')

def main():
    dict_df = pd.read_csv(DICT_CSV)
    train   = pd.read_csv(TRAIN_CSV)
    val     = pd.read_csv(VAL_CSV)

    print(f"Clean dictionary  : {len(dict_df):,} entries")
    print(f"Existing train.csv: {len(train):,} pairs")
    print(f"Existing val.csv  : {len(val):,} pairs")

    # Build tagged pairs
    rows = []
    for _, r in dict_df.iterrows():
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

    print(f"New unique pairs  : {len(new_df):,}")

    # 90/10 split
    split = int(len(new_df) * 0.9)
    new_train = new_df.iloc[:split]
    new_val   = new_df.iloc[split:]

    # Backup originals
    train.to_csv(TRAIN_CSV.with_suffix('.csv.bak'), index=False)
    val.to_csv(VAL_CSV.with_suffix('.csv.bak'), index=False)

    # Append and save
    updated_train = pd.concat([train, new_train], ignore_index=True)
    updated_val   = pd.concat([val,   new_val],   ignore_index=True)

    updated_train.to_csv(TRAIN_CSV, index=False)
    updated_val.to_csv(VAL_CSV,     index=False)

    print()
    print("=" * 50)
    print(f"  Added to train.csv : {len(new_train):,} pairs")
    print(f"  Added to val.csv   : {len(new_val):,} pairs")
    print(f"  New train.csv total: {len(updated_train):,} pairs")
    print(f"  New val.csv total  : {len(updated_val):,} pairs")
    print("=" * 50)

    # Domain breakdown of what was added
    print("\nDomain breakdown of added pairs:")
    domain_counts = new_df['english'].str.extract(r'^\[([^\]]+)\]')[0].value_counts()
    for domain, count in domain_counts.items():
        print(f"  {domain:<45} {count:>6,}")

if __name__ == '__main__':
    main()
