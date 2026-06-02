"""
analyze_bt_quality.py
=====================
Deep analysis of why BT candidates are being rejected and
whether there are other data sources we haven't explored.
"""
import re
import pandas as pd
from pathlib import Path

BASE      = Path(__file__).parent
DATA_DIR  = BASE / "data"
CLEAN_DIR = DATA_DIR / "cleaned"
TRAIN_DIR = DATA_DIR / "training"
RAW_DIR   = DATA_DIR / "raw"

def strip_tag(t): return re.sub(r'^\[[A-Za-z0-9_ ]+\]\s*', '', str(t)).strip()

# Load BT history
bt_df = pd.read_csv(CLEAN_DIR / "back_translated_lun2en.csv")
already_bt = set(bt_df["english"].astype(str).str.lower().str.strip())
print(f"Already back-translated: {len(already_bt):,}")

# Load training data
train = pd.read_csv(TRAIN_DIR / "train.csv")
val   = pd.read_csv(TRAIN_DIR / "val.csv")
both  = pd.concat([train, val])
both["en_clean"]  = both["english"].astype(str).apply(strip_tag)
both["lun_words"] = both["lunyoro"].astype(str).str.split().str.len()
both["en_words"]  = both["en_clean"].str.split().str.len()
both["has_tag"]   = both["english"].astype(str).str.match(r"^\[")
existing_en = set(both["en_clean"].str.lower().str.strip())

print(f"\n{'='*65}")
print("  ANALYSIS OF REMAINING 22,865 TAGGED PAIRS")
print(f"{'='*65}")
tagged = both[both["has_tag"] & (both["en_words"] >= 5)]
already = tagged[tagged["en_clean"].str.lower().str.strip().isin(already_bt)]
remain  = tagged[~tagged["en_clean"].str.lower().str.strip().isin(already_bt)]
print(f"Tagged pairs with en_words>=5:  {len(tagged):,}")
print(f"  Already BT'd:                 {len(already):,}")
print(f"  Remaining:                    {len(remain):,}")
print(f"\nWord length distribution of remaining tagged pairs:")
print(remain["en_words"].describe())
print(f"\nSample remaining tagged pair English (first 5):")
for _, r in remain.head(5).iterrows():
    print(f"  [{r['en_words']}w] {r['en_clean'][:80]}")

print(f"\n{'='*65}")
print("  UNEXPLORED DATA SOURCES")
print(f"{'='*65}")

# Check raw data files
print("\nRaw data files:")
raw_sources = []
for f in sorted(RAW_DIR.glob("*.csv")):
    try:
        df = pd.read_csv(f)
        en_col = next((c for c in df.columns if "english" in c.lower()), None)
        if not en_col:
            continue
        df["en_clean"] = df[en_col].astype(str).apply(strip_tag)
        df["en_words"] = df["en_clean"].str.split().str.len()
        bt_able = df[
            (df["en_words"] >= 5) &
            (~df["en_clean"].str.lower().str.strip().isin(existing_en)) &
            (~df["en_clean"].str.lower().str.strip().isin(already_bt))
        ]
        if len(bt_able) > 0:
            raw_sources.append((f.name, len(df), len(bt_able)))
            print(f"  {f.name:<45} total={len(df):>6,}  new BT-able={len(bt_able):>6,}")
    except Exception as e:
        pass

print(f"\nAll cleaned data files:")
clean_sources = []
for f in sorted(CLEAN_DIR.glob("*.csv")):
    if f.name in ("back_translated_lun2en.csv", "bt_remaining_candidates.csv",
                  "dictionary_lookup.csv"):
        continue
    try:
        df = pd.read_csv(f)
        en_col = next((c for c in df.columns if "english" in c.lower()), None)
        if not en_col:
            continue
        df["en_clean"] = df[en_col].astype(str).apply(strip_tag)
        df["en_words"] = df["en_clean"].str.split().str.len()
        bt_able = df[
            (df["en_words"] >= 5) &
            (~df["en_clean"].str.lower().str.strip().isin(existing_en)) &
            (~df["en_clean"].str.lower().str.strip().isin(already_bt))
        ]
        if len(bt_able) > 0:
            clean_sources.append((f.name, len(df), len(bt_able)))
            print(f"  {f.name:<45} total={len(df):>6,}  new BT-able={len(bt_able):>6,}")
    except Exception:
        pass

# Check dictionary_lookup separately (has longer definitions)
lookup = pd.read_csv(CLEAN_DIR / "dictionary_lookup.csv")
print(f"\ndictionary_lookup.csv columns: {list(lookup.columns)}")
if "english" in lookup.columns:
    lookup["en_words"] = lookup["english"].astype(str).str.split().str.len()
    lookup_bt = lookup[
        (lookup["en_words"] >= 5) &
        (~lookup["english"].astype(str).str.lower().str.strip().isin(existing_en)) &
        (~lookup["english"].astype(str).str.lower().str.strip().isin(already_bt))
    ]
    print(f"  dictionary_lookup.csv BT-able (en_words>=5): {len(lookup_bt):,}")
    print(f"  Sample entries:")
    for _, r in lookup_bt.head(3).iterrows():
        print(f"    [{r['en_words']}w] {str(r['english'])[:80]}")

total_new = sum(x[2] for x in raw_sources + clean_sources)
print(f"\n{'='*65}")
print(f"  TOTAL NEW UNTAPPED BT CANDIDATES: {total_new:,}")
print(f"{'='*65}")
print("\nConclusion:")
if total_new < 1000:
    print("  All major sources are already covered.")
    print("  The 22,865 remaining tagged pairs are the main untapped source.")
    print("  They were tried before but most failed quality filter.")
    print("  RECOMMENDATION: Lower --min-lun-words to 4 to capture more pairs,")
    print("  or use a larger en2lun model (NLLB BLEU=73.97) with more beams.")
else:
    print(f"  {total_new:,} new sentences found in unexplored sources.")
    print(f"  Run: python back_translate_lun2en.py --max-sentences {min(total_new,30000)} --merge")
