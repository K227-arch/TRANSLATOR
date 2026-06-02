"""
check_augmented_quality.py
===========================
Checks quality of augmented BT pairs and removes problematic ones.
"""
import re
import pandas as pd
from pathlib import Path

BASE     = Path(__file__).parent
AUG_CSV  = BASE / "data" / "cleaned" / "augmented_bt_lun2en.csv"
TRAIN    = BASE / "data" / "training" / "train.csv"
VAL      = BASE / "data" / "training" / "val.csv"

df = pd.read_csv(AUG_CSV)
print(f"Loaded {len(df):,} augmented pairs")
print()

# ── Problem 1: Negation mismatch ──────────────────────────────────────────────
# English says "not" but Runyoro doesn't contain a negation marker
RUNYORO_NEG = re.compile(r'\b(ti|nta|ta|timw|titi|tobw|toba|totu|toka|toku|tobw|timu)\w*\b', re.I)
EN_NEG = re.compile(r"\b(not|never|cannot|don't|doesn't|didn't|won't|no one|nobody|nothing)\b", re.I)

neg_mismatch = df[
    df["english"].str.contains(EN_NEG.pattern, regex=True, na=False, flags=re.I) &
    ~df["lunyoro"].str.contains(RUNYORO_NEG.pattern, regex=True, na=False, flags=re.I)
]
print(f"Negation mismatches (EN=negative, LUN=positive): {len(neg_mismatch):,}")
if len(neg_mismatch) > 0:
    print("  Samples:")
    for _, r in neg_mismatch.head(3).iterrows():
        print(f"    EN: {r['english'][:60]}")
        print(f"    LUN: {str(r['lunyoro'])[:60]}")
        print()

# ── Problem 2: Very short Runyoro (< 3 words after augmentation) ─────────────
short_lun = df[df["lunyoro"].astype(str).str.split().str.len() < 3]
print(f"Short Runyoro (< 3 words): {len(short_lun):,}")

# ── Problem 3: Identical EN and LUN ──────────────────────────────────────────
identical = df[df["english"].str.lower().str.strip() == df["lunyoro"].str.lower().str.strip()]
print(f"Identical EN=LUN: {len(identical):,}")

# ── Problem 4: English passthrough in Runyoro ─────────────────────────────────
COMMON_EN = {"the","a","an","is","are","was","were","have","has","do","does",
             "will","would","can","could","to","of","in","on","for","and","or","not"}
def en_ratio(text):
    words = re.findall(r'[a-z]+', str(text).lower())
    if not words: return 0
    return sum(1 for w in words if w in COMMON_EN) / len(words)

passthrough = df[df["lunyoro"].apply(en_ratio) > 0.4]
print(f"English passthrough in Runyoro: {len(passthrough):,}")

# ── What to keep ─────────────────────────────────────────────────────────────
print()
print("Cleaning decision:")
# Keep synonym, truncation, pronoun variants (Runyoro still valid)
# Remove negation mismatches (English negated but Runyoro isn't)
# Keep all non-negation variants

# Safe: synonym substitution and truncation — same meaning, Runyoro still correct
# Risky: negation variants where Runyoro lacks negation marker
# Acceptable: pronoun swap — Runyoro conjugation might differ but model learns from context

to_remove = set()
to_remove.update(neg_mismatch.index)
to_remove.update(short_lun.index)
to_remove.update(identical.index)
to_remove.update(passthrough.index)

df_clean = df[~df.index.isin(to_remove)]
print(f"  Remove negation mismatches:     {len(neg_mismatch):,}")
print(f"  Remove short Runyoro:           {len(short_lun):,}")
print(f"  Remove identical:               {len(identical):,}")
print(f"  Remove EN passthrough in LUN:   {len(passthrough):,}")
print(f"  Total removed:                  {len(to_remove):,}")
print(f"  Clean pairs remaining:          {len(df_clean):,}")
print(f"  Retention rate:                 {100*len(df_clean)/len(df):.1f}%")

# Save cleaned version
clean_path = BASE / "data" / "cleaned" / "augmented_bt_lun2en_clean.csv"
df_clean.to_csv(clean_path, index=False)
print(f"\nSaved cleaned to: {clean_path.name}")
