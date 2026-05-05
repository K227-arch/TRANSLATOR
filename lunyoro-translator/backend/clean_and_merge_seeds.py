"""
Clean and merge seed vocabulary files into the training corpus.
Applies orthographic normalisation, filters noise, deduplicates.
"""
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from dictionary_pipeline import normalise_lunyoro, fix_ocr

SEED_FILES = [
    ("data/raw/medical_seed_vocabulary.csv",    "MEDICAL"),
    ("data/raw/education_seed_vocabulary.csv",  "EDUCATION"),
    ("data/raw/daily_life_seed_vocabulary.csv", "GENERAL"),
    ("data/raw/low_freq_seed_vocabulary.csv",   "GENERAL"),
    ("data/raw/agriculture_seed_vocabulary.csv","AGRICULTURE"),
]

BASE = os.path.dirname(__file__)
CORPUS_PATH = os.path.join(BASE, "data", "cleaned", "english_nyoro_clean.csv")

all_new = []
for fname, default_domain in SEED_FILES:
    fpath = os.path.join(BASE, fname)
    if not os.path.exists(fpath):
        print(f"  Skipping (not found): {fname}")
        continue
    df = pd.read_csv(fpath)
    # Use domain column if present, else default
    if 'domain' not in df.columns:
        df['domain'] = default_domain
    df = df[['english', 'lunyoro', 'domain']].copy()
    # Apply OCR fix and orthographic normalisation
    df['english'] = df['english'].apply(
        lambda x: fix_ocr(str(x)).strip() if pd.notna(x) else '')
    df['lunyoro'] = df['lunyoro'].apply(
        lambda x: normalise_lunyoro(fix_ocr(str(x))) if pd.notna(x) else '')
    # Filter too-short pairs
    df = df[(df['english'].str.len() >= 2) & (df['lunyoro'].str.len() >= 2)]
    # Deduplicate within file
    df = df.drop_duplicates(subset=['english', 'lunyoro']).reset_index(drop=True)
    short = fname.split("/")[-1]
    print(f"  {short}: {len(df)} clean pairs")
    all_new.append(df)

if not all_new:
    print("No seed files found.")
    sys.exit(0)

combined_new = pd.concat(all_new, ignore_index=True)
combined_new = combined_new.drop_duplicates(subset=['english', 'lunyoro']).reset_index(drop=True)
print(f"\nTotal new clean pairs: {len(combined_new)}")

# Add domain tag prefix
combined_new['english'] = '[' + combined_new['domain'] + '] ' + combined_new['english']
combined_new = combined_new[['english', 'lunyoro']]

# Merge into corpus
corpus = pd.read_csv(CORPUS_PATH)
before = len(corpus)
final = pd.concat([corpus, combined_new], ignore_index=True)
final = final.drop_duplicates(subset=['english', 'lunyoro']).reset_index(drop=True)
final.to_csv(CORPUS_PATH, index=False, encoding='utf-8')
print(f"Corpus: {before:,} → {len(final):,} (+{len(final)-before} new pairs)")
