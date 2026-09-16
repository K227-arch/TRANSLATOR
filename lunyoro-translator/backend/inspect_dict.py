import pandas as pd, re

xl = pd.ExcelFile('data/raw/runyoro_dictionary_with_domains.xlsx')

all_rows = []
for sheet in xl.sheet_names[1:]:
    df = pd.read_excel(xl, sheet_name=sheet, header=None)
    header_row = None
    for i, row in df.iterrows():
        vals = [str(v).strip().lower() for v in row.values]
        if 'word' in vals and any('definition' in v or 'meaning' in v for v in vals):
            header_row = i
            break
    if header_row is None:
        continue
    df.columns = df.iloc[header_row]
    df = df.iloc[header_row+1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if 'word' in cl and 'count' not in cl: col_map['word'] = c
        elif 'definition' in cl or 'meaning' in cl: col_map['definition'] = c
        elif 'domain' in cl: col_map['domain'] = c
        elif 'part' in cl or 'speech' in cl: col_map['pos'] = c
    if 'word' not in col_map or 'definition' not in col_map:
        continue
    cols = [col_map['word'], col_map['definition']]
    if 'domain' in col_map: cols.append(col_map['domain'])
    if 'pos' in col_map: cols.append(col_map['pos'])
    sub = df[cols].copy()
    rename = {'word': col_map['word'], 'definition': col_map['definition']}
    sub.columns = ['word', 'definition'] + (['domain'] if 'domain' in col_map else []) + (['pos'] if 'pos' in col_map else [])
    sub['sheet'] = sheet
    all_rows.append(sub)

raw = pd.concat(all_rows, ignore_index=True)
raw['word'] = raw['word'].astype(str).str.strip()
raw['definition'] = raw['definition'].astype(str).str.strip()

# Remove header rows that leaked through
raw = raw[~raw['word'].str.lower().isin(['word', 'speech', 'nan', ''])]
raw = raw[~raw['definition'].str.lower().isin(['english definition', 'meaning/definition', 'nan', ''])]
raw = raw[raw['definition'].notna() & raw['word'].notna()]

print(f"Raw entries after header removal: {len(raw):,}")
print()

issues = {}

# 1. Very short words <= 2 chars (prefixes/particles)
short_words = raw[raw['word'].str.len() <= 2]
issues['words <= 2 chars (prefixes/particles)'] = len(short_words)
print("Sample short words:", short_words['word'].head(10).tolist())

# 2. Morpheme fragments (start or end with -)
fragments = raw[raw['word'].str.startswith('-') | raw['word'].str.endswith('-')]
issues['morpheme fragments (starts/ends with -)'] = len(fragments)
print("Sample fragments:", fragments['word'].head(10).tolist())

# 3. Grammar notation definitions
notation = raw[raw['definition'].str.contains(
    r'Possess\.\s*particle|pronom\.\s*prefix|subj\.\s*pronom|tense prefix|formative|concord',
    regex=True, na=False)]
issues['grammar notation definitions'] = len(notation)
print("Sample notation defs:", notation['definition'].head(3).tolist())

# 4. Definitions too short < 5 chars
short_defs = raw[raw['definition'].str.len() < 5]
issues['definitions < 5 chars'] = len(short_defs)
print("Sample short defs:", short_defs[['word','definition']].head(5).values.tolist())

# 5. Definitions starting lowercase (truncated continuations)
lower_defs = raw[raw['definition'].str.match(r'^[a-z]') & (raw['definition'].str.len() > 5)]
issues['definitions starting lowercase (truncated)'] = len(lower_defs)
print("Sample lowercase defs:", lower_defs['definition'].head(5).tolist())

# 6. Duplicate word+definition
dupes = raw.duplicated(subset=['word', 'definition'], keep=False)
issues['duplicate word+definition pairs'] = int(dupes.sum())

# 7. Words with unexpected characters (not letters, apostrophe, hyphen, !)
noise_words = raw[raw['word'].str.contains(r'[^a-zA-Z\'\-\!]', regex=True)]
issues['words with unexpected characters'] = len(noise_words)
print("Sample noise words:", noise_words['word'].head(10).tolist())

# 8. Definitions that are just notation abbreviations
abbrev_only = raw[raw['definition'].str.match(r'^[a-z]{1,4}\.\s*(cl\.|v\.|adj\.|n\.)', na=False)]
issues['abbreviation-only definitions'] = len(abbrev_only)

# 9. Definitions containing raw OCR artifacts
ocr_noise = raw[raw['definition'].str.contains(r'wh ich|poessor|RunyoroRutooro|cone\.', regex=True, na=False)]
issues['OCR/typo artifacts in definitions'] = len(ocr_noise)
print("Sample OCR artifacts:", ocr_noise['definition'].head(3).tolist())

print()
print("=== QUALITY ISSUES SUMMARY ===")
for k, v in issues.items():
    pct = 100 * v / len(raw)
    print(f"  {k:<52}: {v:>5}  ({pct:.1f}%)")
print(f"  {'Total raw entries':<52}: {len(raw):>5}")
