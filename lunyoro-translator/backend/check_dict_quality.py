import pandas as pd

df = pd.read_csv('data/cleaned/runyoro_domain_dictionary_clean.csv')
print(f"Total entries: {len(df):,}\n")

# Show 40 random samples
sample = df.sample(40, random_state=7)[['lunyoro','english','domain']]
print("=== 40 RANDOM SAMPLES ===")
for _, r in sample.iterrows():
    lun = str(r['lunyoro'])[:28].ljust(28)
    eng = str(r['english'])[:80]
    print(f"  {lun} | {eng}")

print()

# Classify: short english (<=4 words) = likely direct translation
# Long english (>4 words) = likely definition/explanation
df['word_count'] = df['english'].str.split().str.len()
direct   = df[df['word_count'] <= 4]
defs     = df[df['word_count'] >  4]
print(f"Short english (<=4 words, likely direct translation): {len(direct):,}  ({100*len(direct)/len(df):.1f}%)")
print(f"Long english  (>4 words, likely definition):          {len(defs):,}  ({100*len(defs)/len(df):.1f}%)")
print()

# Show examples of each
print("=== SHORT (likely direct translations) ===")
for _, r in direct.sample(15, random_state=1).iterrows():
    print(f"  {str(r['lunyoro']):<28} -> {r['english']}")

print()
print("=== LONG (definitions/explanations) ===")
for _, r in defs.sample(15, random_state=1).iterrows():
    print(f"  {str(r['lunyoro']):<28} -> {r['english']}")
