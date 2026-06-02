import pandas as pd

train = pd.read_csv('data/training/train.csv')
val   = pd.read_csv('data/training/val.csv')
both  = pd.concat([train, val])

both['lun_words'] = both['lunyoro'].astype(str).str.split().str.len()
both['en_words']  = both['english'].astype(str).str.split().str.len()

print('=== Lunyoro side word count distribution ===')
print(both['lun_words'].describe())
print()

short  = (both['lun_words'] <= 2).sum()
medium = ((both['lun_words'] >= 3) & (both['lun_words'] <= 4)).sum()
long_  = (both['lun_words'] >= 5).sum()
tagged = both['english'].str.match(r'^\[').sum()

print(f'lun_words <= 2  (dict entries, hurt lun2en):  {short:,}')
print(f'lun_words 3-4   (short phrases):              {medium:,}')
print(f'lun_words >= 5  (sentences, gold for lun2en): {long_:,}')
print(f'Total pairs:                                   {len(both):,}')
print()
print(f'Pairs with [DOMAIN] tags (en2lun format only): {tagged:,}')
print(f'  -> These are useless for lun2en (Runyoro side is the source)')
print()
pct_sentence = round(100 * long_ / len(both), 1)
print(f'Only {pct_sentence}% of data is sentence-level (lun_words >= 5)')
print(f'lun2en model sees {long_:,} useful sentence pairs vs {len(both):,} total')
