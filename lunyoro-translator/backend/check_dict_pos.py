import pandas as pd

# Check what POS data exists in the clean dictionary
clean = pd.read_csv('data/cleaned/runyoro_domain_dictionary_clean.csv')
lookup = pd.read_csv('data/cleaned/dictionary_lookup.csv')

print("=== runyoro_domain_dictionary_clean.csv ===")
print(f"Columns: {clean.columns.tolist()}")
print(f"Total entries: {len(clean):,}")
print()

# POS distribution
if 'pos' in clean.columns:
    pos_counts = clean['pos'].value_counts(dropna=False)
    print(f"POS values (top 20):")
    for pos, count in pos_counts.head(20).items():
        print(f"  {str(pos):<30} {count:>5,}")
    print(f"  Entries WITH pos data: {clean['pos'].notna().sum():,}")
    print(f"  Entries WITHOUT pos:   {clean['pos'].isna().sum():,}")
else:
    print("  No 'pos' column found")

print()
print("=== Sample entries with POS ===")
if 'pos' in clean.columns:
    sample = clean[clean['pos'].notna()].sample(15, random_state=1)
    for _, r in sample.iterrows():
        print(f"  {str(r['lunyoro']):<28} | {str(r['pos']):<20} | {r['english']}")

print()
print("=== What was added to train.csv ===")
train = pd.read_csv('data/training/train.csv')
# Domain-tagged pairs from this dictionary
tagged = train[train['english'].str.match(r'^\[[A-Z_]+\]', na=False)]
print(f"Domain-tagged pairs in train.csv: {len(tagged):,}")
print(f"Sample tagged pairs:")
for _, r in tagged.sample(10, random_state=42).iterrows():
    print(f"  EN: {r['english'][:60]}")
    print(f"  LUN: {r['lunyoro']}")
    print()

print()
print("=== Were prefixes/plurals extracted? ===")
# Check if any plural forms were generated
print("Checking for plural pairs in training data...")
plural_pairs = train[
    train['english'].str.contains(r'\bplural\b|\bpl\.\b', case=False, na=False) |
    train['lunyoro'].str.match(r'^(aba|ebi|emi|ama|en|em|utu|zaa)', na=False)
]
print(f"Pairs with plural indicators: {len(plural_pairs):,}")

# Check if POS was used in training format
pos_tagged = train[train['english'].str.contains(r'\[.*NOUN\]|\[.*VERB\]|\[.*ADJ\]', case=False, na=False)]
print(f"POS-tagged training pairs: {len(pos_tagged):,}")
