"""
analyze_bt_coverage.py
======================
Analyzes all data sources and identifies what has NOT been back-translated yet.
Back-translation = taking English sentences and generating Runyoro via en2lun model.
"""
import re
import pandas as pd
from pathlib import Path

BASE      = Path(__file__).parent
DATA_DIR  = BASE / "data"
CLEAN_DIR = DATA_DIR / "cleaned"
TRAIN_DIR = DATA_DIR / "training"

def strip_tag(text: str) -> str:
    return re.sub(r'^\[[A-Za-z0-9_ ]+\]\s*', '', str(text)).strip()

print("=" * 70)
print("  BACK-TRANSLATION COVERAGE ANALYSIS")
print("=" * 70)

# ── Load already back-translated English sentences ────────────────────────────
bt_csv = CLEAN_DIR / "back_translated_lun2en.csv"
already_bt: set[str] = set()
if bt_csv.exists():
    bt_df = pd.read_csv(bt_csv)
    already_bt = set(bt_df["english"].astype(str).str.lower().str.strip())
    print(f"\nAlready back-translated: {len(already_bt):,} English sentences")
else:
    print("\nNo back_translated_lun2en.csv found yet")

# ── Load current training data ────────────────────────────────────────────────
train = pd.read_csv(TRAIN_DIR / "train.csv")
val   = pd.read_csv(TRAIN_DIR / "val.csv")
both  = pd.concat([train, val])
both["en_clean"]  = both["english"].astype(str).apply(strip_tag)
both["lun_words"] = both["lunyoro"].astype(str).str.split().str.len()
both["en_words"]  = both["en_clean"].str.split().str.len()
both["has_tag"]   = both["english"].astype(str).str.match(r"^\[")

print(f"Total training pairs:    {len(both):,}")
print(f"  - with domain tags:    {both['has_tag'].sum():,}  (en2lun-only format)")
print(f"  - sentence pairs:      {(both['lun_words'] >= 5).sum():,}  (lun_words >= 5)")
print(f"  - dict/short pairs:    {(both['lun_words'] < 3).sum():,}  (lun_words < 3)")

# ── Analyze each cleaned source file ─────────────────────────────────────────
print(f"\n{'-'*70}")
print(f"  SOURCE FILE ANALYSIS")
print(f"{'-'*70}")
print(f"  {'File':<45} {'Total':>7} {'BT-able':>8} {'Done':>7} {'Remaining':>10}")
print(f"  {'-'*45} {'-'*7} {'-'*8} {'-'*7} {'-'*10}")

total_remaining = 0
remaining_by_source: dict[str, list[str]] = {}

SOURCES = sorted(CLEAN_DIR.glob("*.csv"))
for src in SOURCES:
    if src.name in ("back_translated_lun2en.csv",):
        continue
    try:
        df = pd.read_csv(src)
        if "english" not in df.columns:
            continue
        df["en_clean"] = df["english"].astype(str).apply(strip_tag)
        df["en_words"] = df["en_clean"].str.split().str.len()

        # BT-able = English sentences with >= 5 words not already in training
        existing_en = set(both["en_clean"].str.lower().str.strip())
        bt_able = df[
            (df["en_words"] >= 5) &
            (~df["en_clean"].str.lower().str.strip().isin(existing_en))
        ]
        done = bt_able[bt_able["en_clean"].str.lower().str.strip().isin(already_bt)]
        remaining = bt_able[~bt_able["en_clean"].str.lower().str.strip().isin(already_bt)]

        if len(bt_able) > 0:
            remaining_sentences = remaining["en_clean"].tolist()
            remaining_by_source[src.name] = remaining_sentences
            total_remaining += len(remaining)
            print(f"  {src.name:<45} {len(df):>7,} {len(bt_able):>8,} {len(done):>7,} {len(remaining):>10,}")
    except Exception as e:
        print(f"  {src.name:<45} ERROR: {e}")

# ── Training data tagged pairs not yet BT'd ───────────────────────────────────
tagged_not_bt = both[
    both["has_tag"] &
    (both["en_words"] >= 5) &
    (~both["en_clean"].str.lower().str.strip().isin(already_bt))
]
print(f"\n  {'[training] tagged pairs (en2lun-only)':<45} {len(both[both['has_tag']]):>7,} {len(both[both['has_tag'] & (both['en_words']>=5)]):>8,} {len(both[both['has_tag'] & (both['en_words']>=5) & both['en_clean'].str.lower().str.strip().isin(already_bt)]):>7,} {len(tagged_not_bt):>10,}")

print(f"\n{'-'*70}")
print(f"  TOTAL remaining BT candidates: {total_remaining + len(tagged_not_bt):,}")
print(f"{'-'*70}")

# ── Summary by category ───────────────────────────────────────────────────────
print(f"\n  SUMMARY:")
print(f"  Already back-translated:          {len(already_bt):,}")
print(f"  Remaining in cleaned sources:     {total_remaining:,}")
print(f"  Remaining tagged training pairs:  {len(tagged_not_bt):,}")
print(f"  Grand total remaining:            {total_remaining + len(tagged_not_bt):,}")

# ── Top sources with most remaining ──────────────────────────────────────────
print(f"\n  TOP SOURCES BY REMAINING CANDIDATES:")
sorted_sources = sorted(remaining_by_source.items(), key=lambda x: -len(x[1]))
for name, sents in sorted_sources[:10]:
    print(f"    {name:<45} {len(sents):>8,}")

# ── Save remaining candidates to CSV for next BT run ─────────────────────────
all_remaining = []
for name, sents in remaining_by_source.items():
    for s in sents:
        all_remaining.append({"source": name, "english": s})
# Add tagged training pairs
for en in tagged_not_bt["en_clean"].tolist():
    all_remaining.append({"source": "training_tagged", "english": en})

remaining_df = pd.DataFrame(all_remaining).drop_duplicates(subset=["english"])
out_path = CLEAN_DIR / "bt_remaining_candidates.csv"
remaining_df.to_csv(out_path, index=False)
print(f"\n  Saved {len(remaining_df):,} remaining candidates to:")
print(f"  {out_path}")
print(f"\n  Run: python back_translate_lun2en.py --max-sentences {min(len(remaining_df), 50000)} --merge")
