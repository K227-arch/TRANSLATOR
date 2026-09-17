"""
_prep_sp17_clean.py
====================
Resets new_only_train.csv / new_only_val.csv to contain ONLY the 132 clean
pairs from sentence_pair_17_clean.csv (no domain-tag augmentation).

Restores from the .bak files written during the earlier merge, then appends
the clean pairs only.
"""
import shutil, csv
import pandas as pd
from pathlib import Path

BASE         = Path(__file__).parent
TRAINING_DIR = BASE / "data" / "training"
CLEANED_DIR  = BASE / "data" / "cleaned"

TRAIN    = TRAINING_DIR / "new_only_train.csv"
VAL      = TRAINING_DIR / "new_only_val.csv"
TRAIN_BAK = Path(str(TRAIN) + ".bak")
VAL_BAK   = Path(str(VAL)   + ".bak")
CLEAN_CSV = CLEANED_DIR / "sentence_pair_17_clean.csv"

# ── Restore backups (state before any sp17 data was added) ───────────────────
print("Restoring backups...")
shutil.copy(TRAIN_BAK, TRAIN)
shutil.copy(VAL_BAK,   VAL)

base_train = pd.read_csv(TRAIN)
base_val   = pd.read_csv(VAL)
print(f"  Restored: new_only_train={len(base_train)}  new_only_val={len(base_val)}")

# ── Load existing keys to deduplicate ────────────────────────────────────────
existing_keys = set(
    zip(pd.concat([base_train, base_val])["english"].str.lower().str.strip(),
        pd.concat([base_train, base_val])["lunyoro"].str.lower().str.strip())
)

# ── Load clean pairs only ─────────────────────────────────────────────────────
clean = pd.read_csv(CLEAN_CSV)
new_pairs = clean[~clean.apply(
    lambda r: (r["english"].lower().strip(), r["lunyoro"].lower().strip()) in existing_keys,
    axis=1
)]
print(f"  Clean pairs from sp17: {len(clean)} total, {len(new_pairs)} genuinely new")

# ── 90/10 split ───────────────────────────────────────────────────────────────
split    = int(len(new_pairs) * 0.9)
to_train = new_pairs.iloc[:split]
to_val   = new_pairs.iloc[split:]

# ── Append clean pairs only ───────────────────────────────────────────────────
to_train[["english", "lunyoro"]].to_csv(TRAIN, mode="a", index=False, header=False)
to_val[["english", "lunyoro"]].to_csv(  VAL,   mode="a", index=False, header=False)

t2 = pd.read_csv(TRAIN)
v2 = pd.read_csv(VAL)
print(f"\nFinal counts:")
print(f"  new_only_train.csv : {len(t2):>5} pairs  (+{len(to_train)} from sp17)")
print(f"  new_only_val.csv   : {len(v2):>5} pairs  (+{len(to_val)} from sp17)")
print("\nReady. Run: python augment_and_train.py --train-only --no-push")
