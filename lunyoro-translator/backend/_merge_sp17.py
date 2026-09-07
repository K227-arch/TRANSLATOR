"""Re-merge SP17 clean pairs into new_only_train/val — idempotent."""
import shutil, pandas as pd
from pathlib import Path

TRAINING = Path("data/training")
CLEANED  = Path("data/cleaned")

TRAIN    = TRAINING / "new_only_train.csv"
VAL      = TRAINING / "new_only_val.csv"
CLEAN_SP17 = CLEANED / "sentence_pair_17_clean.csv"

if not CLEAN_SP17.exists():
    raise SystemExit(f"ERROR: {CLEAN_SP17} not found — run process_sentence_pair_17.py first")

base_train = pd.read_csv(TRAIN)
base_val   = pd.read_csv(VAL)
existing_keys = set(
    zip(pd.concat([base_train, base_val])["english"].str.lower().str.strip(),
        pd.concat([base_train, base_val])["lunyoro"].str.lower().str.strip())
)
print(f"Existing: train={len(base_train)}  val={len(base_val)}")

sp17 = pd.read_csv(CLEAN_SP17)
new = sp17[~sp17.apply(
    lambda r: (r["english"].lower().strip(), r["lunyoro"].lower().strip()) in existing_keys,
    axis=1
)]
print(f"SP17 clean pairs: {len(sp17)}  genuinely new: {len(new)}")

if len(new) == 0:
    print("Already merged — nothing to do.")
else:
    split = int(len(new) * 0.9)
    shutil.copy(TRAIN, str(TRAIN) + ".bak")
    shutil.copy(VAL,   str(VAL)   + ".bak")
    new.iloc[:split][["english","lunyoro"]].to_csv(TRAIN, mode="a", index=False, header=False)
    new.iloc[split:][["english","lunyoro"]].to_csv(VAL,   mode="a", index=False, header=False)
    t2 = pd.read_csv(TRAIN); v2 = pd.read_csv(VAL)
    print(f"After merge: train={len(t2)}  val={len(v2)}  (+{len(new.iloc[:split])} train / +{len(new.iloc[split:])} val)")
