"""
analyze_data_augmentation.py
============================
Analyzes all training data to find:
1. Data gaps by domain/type
2. Under-represented categories
3. What augmentation is still needed
4. Quality issues per source
"""
import re
import pandas as pd
from pathlib import Path
from collections import Counter

BASE  = Path(__file__).parent
DATA  = BASE / "data" / "training"
CLEAN = BASE / "data" / "cleaned"

def strip_tag(t):
    m = re.match(r'^\[([A-Z][A-Z0-9_ ]+)\]\s*', str(t))
    return (m.group(1), str(t)[m.end():].strip()) if m else ("NONE", str(t).strip())

print("=" * 70)
print("  DATA AUGMENTATION ANALYSIS")
print("=" * 70)

# Load training data
train = pd.read_csv(DATA / "train.csv")
val   = pd.read_csv(DATA / "val.csv")
both  = pd.concat([train, val])
print(f"\nTotal training pairs: {len(both):,}")

# Parse domain tags
both["domain"], both["en_clean"] = zip(*both["english"].astype(str).apply(strip_tag))
both["lun_words"] = both["lunyoro"].astype(str).str.split().str.len()
both["en_words"]  = both["en_clean"].str.split().str.len()

# -- 1. Domain distribution ----------------------------------------------------
print(f"\n{'-'*70}")
print("  DOMAIN DISTRIBUTION")
print(f"{'-'*70}")
domain_counts = both["domain"].value_counts()
total = len(both)
for domain, count in domain_counts.head(30).items():
    pct = round(100 * count / total, 1)
    bar = "#" * min(int(pct * 2), 40)
    print(f"  {domain:<35} {count:>7,}  ({pct:>5.1f}%)  {bar}")

# -- 2. Sentence length distribution ------------------------------------------
print(f"\n{'-'*70}")
print("  SENTENCE LENGTH ANALYSIS")
print(f"{'-'*70}")
print(f"  English word counts:")
for n in [1, 2, 3, 4, 5, 10, 15, 20, 30]:
    count = int((both["en_words"] == n).sum()) if n <= 5 else int(((both["en_words"] > n-5) & (both["en_words"] <= n)).sum())
    print(f"    {n:>3} words: {count:>7,}")
gt30 = int((both["en_words"] > 30).sum())
print(f"    >30 words: {gt30:>7,}")
print(f"  Runyoro word counts:")
for threshold, label in [(1, "single word"), (2, "2 words"), (3, "short phrase"), (5, "sentence"), (10, "long sentence")]:
    count = int((both["lun_words"] == threshold).sum())
    print(f"    {label:<20} ({threshold} words): {count:>7,}")
gt10 = int((both["lun_words"] > 10).sum())
print(f"    very long (>10):                    {gt10:>7,}")

# -- 3. Data gaps analysis -----------------------------------------------------
print(f"\n{'-'*70}")
print("  DATA GAPS & AUGMENTATION NEEDS")
print(f"{'-'*70}")

# Check underrepresented domains (< 500 pairs)
small_domains = [(d, c) for d, c in domain_counts.items() if c < 500 and d != "NONE"]
print(f"\n  Under-represented domains (< 500 pairs):")
for domain, count in sorted(small_domains, key=lambda x: x[1]):
    print(f"    {domain:<40} {count:>5,} pairs  <- NEEDS AUGMENTATION")

# Check domains with no augmented pairs yet
aug_pos = pd.read_csv(CLEAN / "augmented_pos_pairs.csv") if (CLEAN / "augmented_pos_pairs.csv").exists() else pd.DataFrame()
aug_bt  = pd.read_csv(CLEAN / "augmented_bt_lun2en_clean.csv") if (CLEAN / "augmented_bt_lun2en_clean.csv").exists() else pd.DataFrame()

if not aug_pos.empty:
    aug_pos["domain"], _ = zip(*aug_pos["english"].astype(str).apply(strip_tag))
    aug_domains = set(aug_pos["domain"].unique())
    print(f"\n  Domains with POS augmentation: {len(aug_domains)}")
    not_augmented = set(domain_counts.index) - aug_domains - {"NONE"}
    print(f"  Domains WITHOUT any augmentation ({len(not_augmented)}):")
    for d in sorted(not_augmented):
        count = domain_counts.get(d, 0)
        if count > 0:
            print(f"    {d:<40} {count:>5,} pairs")

# -- 4. Source file analysis ---------------------------------------------------
print(f"\n{'-'*70}")
print("  CLEANED SOURCE FILES — AUGMENTATION STATUS")
print(f"{'-'*70}")

all_training_keys = set(zip(
    both["english"].astype(str).str.lower().str.strip(),
    both["lunyoro"].astype(str).str.lower().str.strip()
))

sources = sorted(CLEAN.glob("*.csv"))
needs_aug = []
for src in sources:
    if src.name.startswith(("augmented", "back_translated", "bt_", "dictionary_lookup")):
        continue
    try:
        df = pd.read_csv(src)
        if "english" not in df.columns or "lunyoro" not in df.columns:
            continue
        total_src = len(df)
        in_train = sum(1 for _, r in df.iterrows()
                      if (str(r["english"]).lower().strip(),
                          str(r["lunyoro"]).lower().strip()) in all_training_keys)
        pct = round(100 * in_train / max(total_src, 1))
        df["lun_words"] = df["lunyoro"].astype(str).str.split().str.len()
        avg_lun = round(df["lun_words"].mean(), 1)
        needs = "OK" if pct >= 80 else "PARTIAL" if pct >= 50 else "LOW COVERAGE"
        print(f"  {src.name:<40} {in_train:>6,}/{total_src:>6,} ({pct:>3}%)  avg_lun={avg_lun}  {needs}")
        if pct < 90 and total_src > 100:
            needs_aug.append((src.name, total_src - in_train, avg_lun))
    except Exception as e:
        pass

# -- 5. Augmentation recommendations ------------------------------------------
print(f"\n{'-'*70}")
print("  AUGMENTATION RECOMMENDATIONS")
print(f"{'-'*70}")

print("\n  HIGH PRIORITY (needs more data):")
for domain, count in sorted(small_domains, key=lambda x: x[1])[:10]:
    if count < 200:
        print(f"    {domain}: only {count} pairs — generate more domain-specific pairs")

print("\n  MEDIUM PRIORITY (partial coverage):")
for name, missing, avg_lun in sorted(needs_aug, key=lambda x: -x[1])[:5]:
    print(f"    {name}: {missing} pairs not in training (avg lun words: {avg_lun})")

print("\n  LOW PRIORITY (already well covered):")
print("    - en2lun: 281k pairs, strong domain coverage")
print("    - lun2en: 131k new pairs with BT + augmentation")
print("    - Grammar pairs: 864 pairs weighted 6x in sampler")

# -- 6. What augmentation to generate next ------------------------------------
print(f"\n{'-'*70}")
print("  NEXT AUGMENTATION ACTIONS")
print(f"{'-'*70}")
print("""
  1. DOMAIN EXPANSION for small domains (< 200 pairs):
     - Generate more pairs for under-represented domains using dictionary + grammar rules
     - Run: python generate_grammar_pairs.py  (already covers grammar)
     - Consider: domain-specific sentence templates

  2. EN2LUN AUGMENTATION (synonym/paraphrase on existing en2lun pairs):
     - augment_bt_data.py only covers lun2en (BT pairs)
     - Need equivalent augmentation for en2lun direction
     - Can run augment_bt_data.py with en2lun flag if modified

  3. RUNYORO MORPHOLOGY AUGMENTATION:
     - Verb conjugation tables (all 6 persons x tenses) already in gr_grammar_pairs
     - Noun class plural forms covered in augmented_pos_pairs
     - Missing: conversive, causative, passive verb forms in training sentences

  4. NLLB RETRAIN with lug_Latn (just changed from nyn_Latn/UNK):
     - The language code fix is critical — NLLB was using UNK token as target
     - Retrain both NLLB directions with lug_Latn for proper language guidance
     - Expected significant BLEU improvement on en2lun especially
""")
