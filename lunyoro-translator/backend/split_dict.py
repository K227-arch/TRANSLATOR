import pandas as pd

CLEAN = 'data/cleaned/runyoro_domain_dictionary_clean.csv'
LOOKUP = 'data/cleaned/dictionary_lookup.csv'

d = pd.read_csv(CLEAN)
d['wc'] = d['english'].str.split().str.len()

direct = d[d['wc'] <= 4].drop(columns=['wc']).reset_index(drop=True)
defs   = d[d['wc'] >  4].drop(columns=['wc']).reset_index(drop=True)

print(f"Total entries       : {len(d):,}")
print(f"Direct translations : {len(direct):,}  (<=4 words)")
print(f"Definitions         : {len(defs):,}  (>4 words)")

# Overwrite clean file with direct translations only (write to tmp then replace)
tmp_clean = CLEAN + '.tmp'
direct.to_csv(tmp_clean, index=False)
import os, shutil
try:
    os.replace(tmp_clean, CLEAN)
except PermissionError:
    shutil.copy(tmp_clean, CLEAN + '.new')
    print(f"  NOTE: file locked — saved as runyoro_domain_dictionary_clean.csv.new instead")
    os.remove(tmp_clean)
print(f"\nSaved {len(direct):,} direct translations -> runyoro_domain_dictionary_clean.csv")

# Merge definitions into lookup
lookup_existing = pd.read_csv(LOOKUP)
print(f"Existing dictionary_lookup.csv: {len(lookup_existing):,} entries")

defs_fmt = pd.DataFrame({
    'word':              defs['lunyoro'],
    'definitionEnglish': defs['english'],
    'domain':            defs['domain'],
    'pos':               defs['pos'] if 'pos' in defs.columns else '',
})

existing_keys = set(zip(
    lookup_existing['word'].astype(str).str.lower(),
    lookup_existing['definitionEnglish'].astype(str).str.lower()
))
new_defs = defs_fmt[
    ~defs_fmt.apply(
        lambda r: (str(r['word']).lower(), str(r['definitionEnglish']).lower()) in existing_keys,
        axis=1
    )
].reset_index(drop=True)

print(f"New definitions (not already in lookup): {len(new_defs):,}")

updated = pd.concat([lookup_existing, new_defs], ignore_index=True)
updated.to_csv(LOOKUP, index=False)
print(f"Saved {len(updated):,} total entries -> dictionary_lookup.csv")

print()
print("=== FINAL STATE ===")
print(f"runyoro_domain_dictionary_clean.csv : {len(direct):,} direct translation pairs")
print(f"dictionary_lookup.csv               : {len(updated):,} definition entries")
