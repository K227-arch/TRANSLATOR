import pandas as pd

d = pd.read_csv('data/cleaned/runyoro_domain_dictionary_clean.csv')
l = pd.read_csv('data/cleaned/dictionary_lookup.csv')

print('=== runyoro_domain_dictionary_clean.csv ===')
print(f'  Entries       : {len(d):,}')
print(f'  Columns       : {d.columns.tolist()}')
wc = d['english'].str.split().str.len()
print(f'  Max word count: {wc.max()}')
print(f'  All <=4 words : {(wc <= 4).all()}')
print('  Sample:')
for _, r in d.sample(5, random_state=1).iterrows():
    print(f'    {str(r["lunyoro"]):<28} -> {r["english"]}')

print()
print('=== dictionary_lookup.csv ===')
print(f'  Entries       : {len(l):,}')
print(f'  Columns       : {l.columns.tolist()}')
wc2 = l['definitionEnglish'].str.split().str.len()
print(f'  Min word count: {wc2.min()}')
print(f'  All >4 words  : {(wc2 > 4).all()}')
print('  Sample:')
for _, r in l.sample(5, random_state=1).iterrows():
    print(f'    {str(r["word"]):<28} -> {str(r["definitionEnglish"])[:70]}')
