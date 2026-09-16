import pandas as pd
import re

train = pd.read_csv('data/training/train.csv')
val   = pd.read_csv('data/training/val.csv')
both  = pd.concat([train, val])

both['lun_words'] = both['lunyoro'].astype(str).str.split().str.len()
both['has_tag']   = both['english'].astype(str).str.match(r'^\[')
both['en_clean']  = both['english'].astype(str).str.replace(
    r'^\[[A-Za-z0-9_ ]+\]\s*', '', regex=True).str.strip()
both['en_words']  = both['en_clean'].str.split().str.len()

# Category 1: Tagged pairs (en2lun-only format) — lun2en never saw these as source
tagged = both[both['has_tag']]
print(f"Tagged pairs (en2lun-only format):          {len(tagged):,}")
print(f"  -> lun2en model never saw these as source")
print(f"  -> Back-translating their English gives NEW lun2en data")
print()

# Category 2: Short dict pairs (lun_words <= 2) — filtered out of lun2en training
short = both[~both['has_tag'] & (both['lun_words'] <= 2)]
print(f"Short dict pairs (lun_words <= 2):          {len(short):,}")
print(f"  -> Filtered out of lun2en by min-lun-words=3")
print(f"  -> Their English is valid but Runyoro side is too short")
print()

# Category 3: Sentence pairs already in lun2en training (lun_words >= 3, no tag)
good = both[~both['has_tag'] & (both['lun_words'] >= 3)]
print(f"Good sentence pairs (already in lun2en):    {len(good):,}")
print(f"  -> Already trained on — back-translating these = redundant")
print()

# What we can back-translate: tagged English (after stripping tags) + short dict English
# that have >= 5 English words (so the back-translation produces a real sentence)
bt_candidates = both[
    (both['has_tag'] | (both['lun_words'] <= 2)) &
    (both['en_words'] >= 5)
]
print(f"Back-translation candidates (useful):       {len(bt_candidates):,}")
print(f"  = tagged pairs with en_words >= 5")
print(f"  + short dict pairs with en_words >= 5")
print()
print(f"Already back-translated (from previous run): ~10,928")
print(f"Remaining useful candidates:                 ~{len(bt_candidates)-10928:,}")
