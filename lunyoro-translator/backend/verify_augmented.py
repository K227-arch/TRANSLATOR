import pandas as pd, random

df = pd.read_csv('data/cleaned/augmented_pos_pairs.csv')
print(f"Total augmented pairs: {len(df):,}")
print()

# Show samples by type
for tag, label in [
    ('_NOUN]',        'POS-tagged nouns'),
    ('_VERB]',        'POS-tagged verbs'),
    ('_ADJ]',         'POS-tagged adjectives'),
    ('_NOUN_PLURAL]', 'Plural nouns'),
    ('_VERB] I ',     'Verb 1sg present'),
    ('_VERB] he/she', 'Verb 3sg present'),
    ('_VERB] I have', 'Verb perfect'),
    ('_VERB] I don',  'Verb negative'),
]:
    subset = df[df['english'].str.contains(tag, regex=False, na=False)]
    print(f"--- {label}: {len(subset):,} pairs ---")
    for _, r in subset.sample(min(4, len(subset)), random_state=42).iterrows():
        print(f"  EN:  {r['english']}")
        print(f"  LUN: {r['lunyoro']}")
    print()
