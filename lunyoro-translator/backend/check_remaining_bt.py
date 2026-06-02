import re, pandas as pd
from pathlib import Path

train = pd.read_csv('data/training/train.csv')
val   = pd.read_csv('data/training/val.csv')
both  = pd.concat([train, val])

bt = pd.read_csv('data/cleaned/back_translated_lun2en.csv')
already_bt = set(bt['english'].astype(str).str.lower().str.strip())

def strip_tag(t): return re.sub(r'^\[[A-Za-z0-9_ ]+\]\s*', '', str(t)).strip()
both['en_clean']  = both['english'].astype(str).apply(strip_tag)
both['lun_words'] = both['lunyoro'].astype(str).str.split().str.len()
both['en_words']  = both['en_clean'].str.split().str.len()
both['has_tag']   = both['english'].astype(str).str.match(r'^\[')

remain = both[
    both['has_tag'] &
    (both['en_words'] >= 5) &
    (~both['en_clean'].str.lower().str.strip().isin(already_bt))
]
print(f'Remaining tagged pairs to BT: {len(remain):,}')
print()
print('English word length distribution:')
for n in [5,6,7,8,9,10,15,20]:
    count = int((remain['en_words'] == n).sum())
    print(f'  en_words={n}: {count:,}')
gt20 = int((remain['en_words'] > 20).sum())
print(f'  en_words>20: {gt20:,}')
print()

# Key question: what did BT produce for these? Too short or passthrough?
# Simulate: check what the Runyoro side (en2lun target) looks like
# These are en2lun pairs — Runyoro is already there, we want to BT the English
print('Sample remaining (5 random):')
for _, r in remain.sample(5, random_state=42).iterrows():
    print(f'  [{r["en_words"]}w EN] {r["en_clean"][:70]}')
    print(f'    -> existing LUN: {str(r["lunyoro"])[:60]}')
    print()

# How many would be captured with min-lun-words=4 vs 5?
# The en2lun model produces Runyoro — we check length of what it WOULD produce
# Proxy: look at the existing Runyoro side of these pairs (gold reference)
remain_lun4 = remain[remain['lun_words'] >= 4]
remain_lun5 = remain[remain['lun_words'] >= 5]
print(f'Pairs where gold Runyoro has >= 4 words: {len(remain_lun4):,}')
print(f'Pairs where gold Runyoro has >= 5 words: {len(remain_lun5):,}')
print()
print('If we lower --min-lun-words to 4, we could capture ~', 
      len(remain_lun4) - len(remain_lun5), 'additional pairs')
print()

# Save the top candidates sorted by English length (longer = richer sentence)
top_candidates = remain.sort_values('en_words', ascending=False).head(30000)
top_candidates[['en_clean', 'lun_words']].rename(columns={'en_clean': 'english'}).to_csv(
    'data/cleaned/bt_top_candidates.csv', index=False)
print(f'Saved top {len(top_candidates):,} candidates to bt_top_candidates.csv')
