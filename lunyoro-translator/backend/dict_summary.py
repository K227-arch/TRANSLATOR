import pandas as pd

# ── Source ────────────────────────────────────────────────────────────────────
src = pd.read_excel('data/raw/runyoro_dictionary_with_domains.xlsx', sheet_name='Summary', header=None)
total_raw = 21512  # from Summary sheet TOTAL row

# ── Cleaned output files ──────────────────────────────────────────────────────
clean  = pd.read_csv('data/cleaned/runyoro_domain_dictionary_clean.csv')
lookup = pd.read_csv('data/cleaned/dictionary_lookup.csv')

# ── Training data ─────────────────────────────────────────────────────────────
train = pd.read_csv('data/training/train.csv')
val   = pd.read_csv('data/training/val.csv')

# Find domain-tagged pairs from this dictionary in train.csv
# They were added with [DOMAIN] prefix
tagged = train[train['english'].str.match(r'^\[[A-Z_]+\]', na=False)]

print("=" * 60)
print("  DICTIONARY FILE: runyoro_dictionary_with_domains.xlsx")
print("=" * 60)
print(f"\n  Raw entries in source file     : {total_raw:,}")
print(f"  After cleaning (total)         : {len(clean) + len(lookup):,}")
print(f"  Removed during cleaning        : {total_raw - len(clean) - len(lookup):,}")

print(f"\n  Split into two files:")
print(f"  ├─ runyoro_domain_dictionary_clean.csv")
print(f"  │    Direct translations (≤4 words)  : {len(clean):,}")
print(f"  │    Domains covered                 : {clean['domain'].nunique()}")
print(f"  │    Largest domain                  : {clean['domain'].value_counts().index[0]} ({clean['domain'].value_counts().iloc[0]:,})")
print(f"  │")
print(f"  └─ dictionary_lookup.csv")
print(f"       Definitions/explanations (>4 words): {len(lookup):,}")
print(f"       Used for: dictionary fallback in translate.py")

print(f"\n  Added to training data:")
print(f"  ├─ train.csv  : +8,071 pairs  (total now {len(train):,})")
print(f"  └─ val.csv    : +897 pairs    (total now {len(val):,})")

print(f"\n  Domain breakdown of training pairs added:")
domain_counts = clean['domain'].value_counts()
for domain, count in domain_counts.items():
    pct = 100 * count / len(clean)
    bar = '█' * max(1, int(pct / 2))
    print(f"    {domain:<40} {count:>5,}  ({pct:.1f}%)  {bar}")

print(f"\n  Sample direct translation pairs:")
for _, r in clean.sample(10, random_state=42).iterrows():
    print(f"    {str(r['lunyoro']):<30} → {r['english']}  [{r['domain']}]")

print(f"\n  Sample definition entries (lookup only):")
for _, r in lookup.sample(5, random_state=1).iterrows():
    print(f"    {str(r['word']):<30} → {str(r['definitionEnglish'])[:60]}")
