"""
clean_domain_dictionary.py
==========================
Extracts, cleans and saves runyoro_dictionary_with_domains.xlsx
→ data/cleaned/runyoro_domain_dictionary_clean.csv

Cleaning steps applied (with counts reported):
  1. Remove leaked header rows (Word / English Definition / SPEECH etc.)
  2. Remove morpheme fragments  (word starts or ends with '-')
  3. Remove single-char and 2-char prefix/particle entries
  4. Remove grammar-notation definitions (pronom. prefix, Possess. particle, etc.)
  5. Remove abbreviation-only definitions (n. cl. / v. / adj. only)
  6. Remove definitions shorter than 4 characters
  7. Remove duplicate word+definition pairs (keep first)
  8. Fix OCR/typo artifacts in definitions
  9. Strip leading grammar-label prefixes from definitions
     (e.g. "n. first letter..." → "first letter...")
 10. Strip trailing punctuation noise (extra dots, spaces)
 11. Fix multi-word 'words' that are actually phrases with spaces
     → keep as-is (valid idioms) but flag them
 12. Assign domain = 'General' where domain is missing/NaN
 13. Capitalise domain labels consistently
"""

import re
import pandas as pd
from pathlib import Path

SRC  = Path('data/raw/runyoro_dictionary_with_domains.xlsx')
OUT  = Path('data/cleaned/runyoro_domain_dictionary_clean.csv')

# ── Grammar notation patterns to drop ────────────────────────────────────────
RE_GRAMMAR_NOTATION = re.compile(
    r'Possess\.\s*particle|pronom\.\s*prefix|subj\.\s*pronom|'
    r'tense\s+prefix|formative|concord\s+in\s+use|'
    r'nominal\s+prefix|enclitic|prepositional|'
    r'co-ordinate\s+rank|adverbial\s+formative|'
    r'monosyllabic\s+stem|introductory\s+word',
    re.IGNORECASE
)

# Leading grammar label prefixes to strip from definitions
# e.g. "n. first letter..." → "first letter..."
RE_LEADING_LABEL = re.compile(
    r'^(?:n\.|v\.|adj\.|adv\.|pron\.|prep\.|conj\.|int\.|nt\.|j\.|'
    r'part\.|interj\.|num\.|art\.)\s+',
    re.IGNORECASE
)

# OCR artifact fixes: (pattern, replacement)
OCR_FIXES = [
    (r'RunyoroRutooro',      'Runyoro-Rutooro'),
    (r'wh ich',              'which'),
    (r'poessor',             'possessor'),
    (r'cone\.',              'concord.'),
    (r'perfonn',             'perform'),
    (r'\bro\s+which\s+obj\b','to which obj'),
    (r'\s{2,}',              ' '),
]


def load_all_sheets(xl: pd.ExcelFile) -> pd.DataFrame:
    frames = []
    for sheet in xl.sheet_names[1:]:   # skip Summary
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        # Find header row
        header_row = None
        for i, row in df.iterrows():
            vals = [str(v).strip().lower() for v in row.values]
            if 'word' in vals and any('definition' in v or 'meaning' in v for v in vals):
                header_row = i
                break
        if header_row is None:
            continue
        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        df.columns = [str(c).strip() for c in df.columns]

        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if 'word' in cl and 'count' not in cl and 'col' not in cl:
                col_map.setdefault('word', c)
            elif 'definition' in cl or 'meaning' in cl:
                col_map.setdefault('definition', c)
            elif 'domain' in cl:
                col_map.setdefault('domain', c)
            elif ('part' in cl and 'speech' in cl) or cl == 'speech':
                col_map.setdefault('pos', c)

        if 'word' not in col_map or 'definition' not in col_map:
            continue

        cols = [col_map['word'], col_map['definition']]
        if 'domain' in col_map: cols.append(col_map['domain'])
        if 'pos'    in col_map: cols.append(col_map['pos'])
        sub = df[cols].copy()
        sub.columns = (
            ['word', 'definition']
            + (['domain'] if 'domain' in col_map else [])
            + (['pos']    if 'pos'    in col_map else [])
        )
        sub['letter'] = sheet
        frames.append(sub)

    return pd.concat(frames, ignore_index=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {}
    n0 = len(df)

    df['word']       = df['word'].astype(str).str.strip()
    df['definition'] = df['definition'].astype(str).str.strip()
    if 'domain' not in df.columns:
        df['domain'] = ''
    df['domain'] = df['domain'].astype(str).str.strip()

    # ── Step 1: Remove leaked header rows ────────────────────────────────────
    header_words = {'word', 'speech', 'nan', '', 'word count', 'total'}
    header_defs  = {'english definition', 'meaning/definition', 'nan', '',
                    'definition', 'meaning'}
    mask = (
        df['word'].str.lower().isin(header_words) |
        df['definition'].str.lower().isin(header_defs)
    )
    removed = mask.sum()
    df = df[~mask].copy()
    stats['1. Leaked header rows removed'] = int(removed)

    # ── Step 2: Remove morpheme fragments (starts/ends with -) ───────────────
    mask = df['word'].str.startswith('-') | df['word'].str.endswith('-')
    removed = mask.sum()
    df = df[~mask].copy()
    stats['2. Morpheme fragments removed (starts/ends with -)'] = int(removed)

    # ── Step 3: Remove single/two-char prefix entries ────────────────────────
    mask = df['word'].str.len() <= 2
    removed = mask.sum()
    df = df[~mask].copy()
    stats['3. Single/two-char prefix entries removed'] = int(removed)

    # ── Step 4: Remove grammar-notation definitions ───────────────────────────
    mask = df['definition'].str.contains(RE_GRAMMAR_NOTATION, na=False)
    removed = mask.sum()
    df = df[~mask].copy()
    stats['4. Grammar-notation definitions removed'] = int(removed)

    # ── Step 5: Remove abbreviation-only definitions ─────────────────────────
    mask = df['definition'].str.match(
        r'^[a-z]{1,5}\.\s*(cl\.|v\.|adj\.|n\.)', na=False)
    removed = mask.sum()
    df = df[~mask].copy()
    stats['5. Abbreviation-only definitions removed'] = int(removed)

    # ── Step 6: Remove definitions shorter than 4 chars ──────────────────────
    mask = df['definition'].str.len() < 4
    removed = mask.sum()
    df = df[~mask].copy()
    stats['6. Definitions < 4 chars removed'] = int(removed)

    # ── Step 7: Fix OCR/typo artifacts ───────────────────────────────────────
    ocr_fixed = 0
    for pattern, replacement in OCR_FIXES:
        before = df['definition'].copy()
        df['definition'] = df['definition'].str.replace(
            pattern, replacement, regex=True)
        ocr_fixed += int((df['definition'] != before).sum())
    stats['7. OCR/typo artifacts fixed in definitions'] = ocr_fixed

    # ── Step 8: Strip leading grammar-label prefixes ─────────────────────────
    before = df['definition'].copy()
    df['definition'] = df['definition'].str.replace(
        RE_LEADING_LABEL, '', regex=True).str.strip()
    label_stripped = int((df['definition'] != before).sum())
    stats['8. Leading grammar labels stripped from definitions'] = label_stripped

    # ── Step 9: Strip trailing punctuation noise ─────────────────────────────
    before = df['definition'].copy()
    df['definition'] = (
        df['definition']
        .str.rstrip(' .,;:')
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )
    punct_fixed = int((df['definition'] != before).sum())
    stats['9. Trailing punctuation noise fixed'] = punct_fixed

    # ── Step 10: Assign General domain where missing ──────────────────────────
    no_domain_mask = (
        df['domain'].str.lower().isin(['nan', '', 'none']) |
        df['domain'].isna()
    )
    no_domain_count = int(no_domain_mask.sum())
    df.loc[no_domain_mask, 'domain'] = 'General'
    stats['10. Entries assigned General domain'] = no_domain_count

    # ── Step 11: Capitalise domain labels consistently ────────────────────────
    df['domain'] = df['domain'].str.strip().str.title()

    # ── Step 12: Remove duplicate word+definition pairs ──────────────────────
    before_len = len(df)
    df = df.drop_duplicates(subset=['word', 'definition'], keep='first')
    stats['12. Duplicate word+definition pairs removed'] = before_len - len(df)

    # ── Step 13: Final empty-row cleanup ─────────────────────────────────────
    df = df[
        df['word'].str.strip().ne('') &
        df['definition'].str.strip().ne('') &
        df['word'].str.lower().ne('nan') &
        df['definition'].str.lower().ne('nan')
    ]

    stats['TOTAL removed/modified'] = n0 - len(df)
    stats['FINAL clean entries'] = len(df)
    return df.reset_index(drop=True), stats


def main():
    print("Loading sheets...")
    xl  = pd.ExcelFile(SRC)
    raw = load_all_sheets(xl)
    print(f"Raw entries loaded: {len(raw):,}")

    print("Cleaning...")
    clean_df, stats = clean(raw)

    # Build output: english (definition) | lunyoro (word) | domain | pos
    out = pd.DataFrame({
        'lunyoro':    clean_df['word'],
        'english':    clean_df['definition'],
        'domain':     clean_df['domain'],
        'pos':        clean_df.get('pos', pd.Series([''] * len(clean_df))),
        'letter':     clean_df.get('letter', pd.Series([''] * len(clean_df))),
    })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding='utf-8')

    # ── Report ────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  CLEANING REPORT")
    print("=" * 60)
    for step, count in stats.items():
        marker = ">>>" if step.startswith(('TOTAL', 'FINAL')) else "   "
        print(f"  {marker} {step:<52}: {count:>6,}")

    print()
    print(f"Domain distribution in clean data:")
    domain_counts = out['domain'].value_counts()
    for domain, count in domain_counts.items():
        pct = 100 * count / len(out)
        print(f"  {domain:<45} {count:>6,}  ({pct:.1f}%)")

    print()
    print(f"Saved to: {OUT}")
    print(f"Total clean pairs: {len(out):,}")


if __name__ == '__main__':
    main()
