import pandas as pd
import os

train = pd.read_csv('data/training/train.csv')
print('Total pairs:', len(train))

# Domain-tagged pairs (seed vocabulary added with [DOMAIN] prefix)
tagged = train[train['english'].str.match(r'^\[[A-Z]', na=False)]
print('Domain-tagged pairs:', len(tagged))
if len(tagged):
    tags = tagged['english'].str.extract(r'^\[([^\]]+)\]')[0].value_counts()
    print(tags)

# Seed file sizes
seed_files = [
    ('medical_seed_vocabulary.csv',    'data/raw/medical_seed_vocabulary.csv'),
    ('education_seed_vocabulary.csv',  'data/raw/education_seed_vocabulary.csv'),
    ('daily_life_seed_vocabulary.csv', 'data/raw/daily_life_seed_vocabulary.csv'),
    ('low_freq_seed_vocabulary.csv',   'data/raw/low_freq_seed_vocabulary.csv'),
    ('agriculture_seed_vocabulary.csv','data/raw/agriculture_seed_vocabulary.csv'),
]
print()
total_seed = 0
for name, path in seed_files:
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f'{name}: {len(df)} pairs')
        total_seed += len(df)
print(f'Total seed pairs: {total_seed}')

# gr4/gr5 pairs
print()
for name, path in [('gr4_pairs', 'data/cleaned/gr4_pairs.csv'), ('gr5_pairs', 'data/cleaned/gr5_pairs.csv')]:
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f'{name}: {len(df)} pairs')

# back_translated
for name, path in [('back_translated', 'data/training/back_translated.csv'), ('gr4_back_translated', 'data/training/gr4_back_translated.csv')]:
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f'{name}: {len(df)} pairs')

# english_nyoro_clean (main corpus)
path = 'data/cleaned/english_nyoro_clean.csv'
if os.path.exists(path):
    df = pd.read_csv(path)
    print(f'english_nyoro_clean: {len(df)} pairs')
