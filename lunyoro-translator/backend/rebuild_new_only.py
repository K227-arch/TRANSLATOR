"""
Rebuilds new_only_train.csv and new_only_val.csv to include all augmented data
(en2lun augmentation + BT + lun2en augmentation).

Baseline = train.csv.bak_en2lun_aug (state before en2lun augmentation)
New      = everything in current train/val not in the baseline
"""
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data" / "training"

# Baseline: before en2lun augmentation (but after BT + lun2en aug)
bak_t = pd.read_csv(DATA / "train.csv.bak_en2lun_aug")
bak_v = pd.read_csv(DATA / "val.csv.bak_en2lun_aug")
baseline = set(zip(
    pd.concat([bak_t, bak_v])["english"].str.lower().str.strip(),
    pd.concat([bak_t, bak_v])["lunyoro"].str.lower().str.strip()
))
print(f"Baseline (pre en2lun aug): {len(baseline):,} pairs")

cur_t = pd.read_csv(DATA / "train.csv")
cur_v = pd.read_csv(DATA / "val.csv")
print(f"Current: train={len(cur_t):,} val={len(cur_v):,} total={len(cur_t)+len(cur_v):,}")

new_t = cur_t[~cur_t.apply(
    lambda r: (str(r["english"]).lower().strip(),
               str(r["lunyoro"]).lower().strip()) in baseline, axis=1)]
new_v = cur_v[~cur_v.apply(
    lambda r: (str(r["english"]).lower().strip(),
               str(r["lunyoro"]).lower().strip()) in baseline, axis=1)]

new_t.to_csv(DATA / "new_only_train.csv", index=False)
new_v.to_csv(DATA / "new_only_val.csv",   index=False)

print(f"new_only_train: {len(new_t):,}")
print(f"new_only_val:   {len(new_v):,}")
print(f"Total new pairs: {len(new_t)+len(new_v):,}")
print()
# Breakdown by type
new_t["has_tag"] = new_t["english"].astype(str).str.match(r"^\[")
new_t["lun_words"] = new_t["lunyoro"].astype(str).str.split().str.len()
tagged    = new_t["has_tag"].sum()
sentences = (~new_t["has_tag"] & (new_t["lun_words"] >= 3)).sum()
short     = (~new_t["has_tag"] & (new_t["lun_words"] < 3)).sum()
print(f"  Tagged en2lun pairs:    {tagged:,}")
print(f"  Sentence pairs (lun>=3): {sentences:,}")
print(f"  Short/dict pairs:       {short:,}")
