"""Check quality of the newly added training pairs."""
import pandas as pd, re, random

train = pd.read_csv('data/training/train.csv')
val   = pd.read_csv('data/training/val.csv')

# The new pairs are the last 77,139 rows of train + last 8,572 of val
new_train = train.tail(77139)
new_val   = val.tail(8572)
new_all   = pd.concat([new_train, new_val]).reset_index(drop=True)

print(f"New pairs to check: {len(new_all):,}")
print()

issues = {}

# 1. Empty/NaN
empty = new_all[new_all['english'].isna() | new_all['lunyoro'].isna() |
                (new_all['english'].str.strip() == '') |
                (new_all['lunyoro'].str.strip() == '')]
issues['Empty/NaN'] = len(empty)

# 2. Identical src=tgt
identical = new_all[new_all['english'].str.lower().str.strip() == new_all['lunyoro'].str.lower().str.strip()]
issues['Identical src=tgt'] = len(identical)

# 3. Very short (< 3 chars)
short = new_all[(new_all['english'].str.len() < 3) | (new_all['lunyoro'].str.len() < 3)]
issues['Too short (< 3 chars)'] = len(short)

# 4. English in lunyoro column (passthrough)
common_en = {'the','a','an','is','are','was','were','have','has','do','does','will','would','can','could','should','may','might','to','of','in','on','at','for','with','and','or','but','not','this','that','it','he','she','they','we','you','i','my','your','his','her','their','its','our'}
def is_english(text):
    words = re.findall(r'[a-z]+', str(text).lower())
    if not words: return False
    return sum(1 for w in words if w in common_en) / len(words) > 0.5
en_in_lun = new_all[new_all['lunyoro'].apply(is_english)]
issues['English in lunyoro column'] = len(en_in_lun)

# 5. Very long (> 500 chars)
long_pairs = new_all[(new_all['english'].str.len() > 500) | (new_all['lunyoro'].str.len() > 500)]
issues['Very long (> 500 chars)'] = len(long_pairs)

# 6. Contains HTML/special artifacts
artifacts = new_all[new_all['english'].str.contains(r'<[^>]+>|&[a-z]+;|\{|\}', regex=True, na=False) |
                    new_all['lunyoro'].str.contains(r'<[^>]+>|&[a-z]+;|\{|\}', regex=True, na=False)]
issues['HTML/artifact chars'] = len(artifacts)

print("=== QUALITY ISSUES ===")
total_issues = 0
for k, v in issues.items():
    pct = 100 * v / len(new_all)
    print(f"  {k:<35}: {v:>6,}  ({pct:.2f}%)")
    total_issues += v

print(f"\n  Total flagged (may overlap): {total_issues:,}")
print(f"  Clean estimate: {len(new_all) - len(empty) - len(identical) - len(short):,} / {len(new_all):,}")

print()
print("=== SAMPLE: english_nyoro_clean.csv (largest source) ===")
# Show 10 random samples from the new data
sample = new_all.sample(15, random_state=42)
for _, r in sample.iterrows():
    en  = str(r['english'])[:70]
    lun = str(r['lunyoro'])[:60]
    print(f"  EN:  {en}")
    print(f"  LUN: {lun}")
    print()
