"""
clean_training_data.py
======================
Cleans all training/val/test CSV splits:
  1. Strip malformed domain tags  ([GENerAL], [GEDICAL], [REGOVERNMENT], etc.)
  2. Remove OCR notation garbage  (n. cl. 11, (pl. nil), ", o-, n.", etc.)
  3. Remove mixed-language sentences (English words in Lunyoro column, vice versa)
  4. Deduplicate exact pairs
  5. Filter pairs that are too short, too long, or identical src==tgt
  6. Normalise whitespace and apostrophes

Writes cleaned files to data/training/  (overwrites in-place, keeps originals as .bak)

Usage:
    python clean_training_data.py [--dry-run]
"""
import re
import os
import sys
import shutil
import unicodedata
import pandas as pd

BASE = os.path.dirname(__file__)
SPLITS = {
    "train": os.path.join(BASE, "data", "training", "train.csv"),
    "val":   os.path.join(BASE, "data", "training", "val.csv"),
    "test":  os.path.join(BASE, "data", "training", "test.csv"),
}

# ── Patterns to strip / reject ────────────────────────────────────────────────

# Domain tags: [GENERAL], [GENerAL], [MEDICAL], [REGOVERNMENT], etc.
_TAG_RE = re.compile(r'\[[A-Za-z][A-Za-z _]{0,20}\]\s*', re.IGNORECASE)

# OCR dictionary notation artifacts
_OCR_PATTERNS = [
    re.compile(r',\s*[a-z]-\s*,\s*n\.\s*cl\.\s*\d+.*', re.IGNORECASE),  # ", o-, n. cl. 11..."
    re.compile(r'\(pl\.\s*(nil|same|\w{1,20})\)', re.IGNORECASE),         # (pl. nil)
    re.compile(r'\bn\.\s*cl\.\s*\d+', re.IGNORECASE),                     # "n. cl. 11"
    re.compile(r',\s*[a-z]{1,3}\.\s*,', re.IGNORECASE),                   # ", n. ," ", v. ,"
    re.compile(r'\(pf\.\s*-\w+\)', re.IGNORECASE),                        # (pf. -culeezi)
    re.compile(r';\s*q\.prace\b', re.IGNORECASE),                         # "; q.prace"
    re.compile(r'\bpr\.\s*form\b', re.IGNORECASE),                        # "pr. form"
    re.compile(r',\s*ekisisani\b.*', re.IGNORECASE),                      # ", ekisisani..."
    re.compile(r'\bv\.rejl\b', re.IGNORECASE),                            # "v.rejl."
    re.compile(r'kw-\s*,\s*okw-\s*,', re.IGNORECASE),                    # "kw-, okw-,"
]

# Apostrophe normalisation
_APOS_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"',
    "\u02BC": "'", "\u0060": "'",
})

# Common English function words — if Lunyoro column has many of these it's likely English
_EN_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "not", "no", "yes", "so",
    "and", "or", "but", "if", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "through", "he", "she", "it",
    "we", "they", "me", "him", "her", "us", "them", "this", "that",
    "these", "those", "i", "you", "my", "your", "his", "its", "our",
    "their", "what", "how", "when", "where", "who", "which", "all",
    "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "too", "very", "just", "then",
}

# Runyoro-Rutooro common prefixes — if English column has many of these it's likely Lunyoro
_LUN_PREFIXES = ("omu", "aba", "eki", "ebi", "ama", "obu", "oku", "oru",
                 "aka", "utu", "emi", "eri", "en", "em", "ni", "ba", "ka",
                 "tu", "mu", "nk", "ng", "mb", "nd")


def _normalise(text: str) -> str:
    """NFC + apostrophe normalisation + collapse whitespace."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_APOS_MAP)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _strip_tags(text: str) -> str:
    """Remove all domain tags from text."""
    return _TAG_RE.sub('', text).strip()


def _strip_ocr(text: str) -> str:
    """Remove OCR notation artifacts."""
    for pat in _OCR_PATTERNS:
        text = pat.sub('', text)
    return text.strip(' .,;')


def _is_ocr_garbage(text: str) -> bool:
    """Return True if the text looks like raw OCR dictionary notation."""
    t = text.strip()
    # Starts with lowercase abbreviation pattern
    if re.match(r'^[a-z]{1,3}\.\s*\(', t):
        return True
    # Contains "(pl. X)" or "n. cl." heavily
    if re.search(r'\(pl\.\s*(nil|same)\)', t, re.IGNORECASE):
        return True
    if re.search(r'\bn\.\s*cl\.\s*\d+', t, re.IGNORECASE):
        return True
    # Mostly punctuation/abbreviations
    real_words = re.findall(r'[a-zA-Z]{4,}', t)
    tokens = t.split()
    if tokens and len(real_words) / len(tokens) < 0.25:
        return True
    return False


def _is_likely_english(text: str) -> bool:
    """Heuristic: return True if text looks like English (for Lunyoro column check)."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    if not words:
        return False
    en_hits = sum(1 for w in words if w in _EN_STOPWORDS)
    return en_hits / len(words) > 0.35


def _is_likely_lunyoro(text: str) -> bool:
    """Heuristic: return True if text looks like Lunyoro (for English column check)."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    if not words:
        return False
    lun_hits = sum(1 for w in words if w.startswith(_LUN_PREFIXES))
    return lun_hits / len(words) > 0.4


def clean_row(en: str, lun: str) -> tuple[str | None, str | None]:
    """
    Clean a single (english, lunyoro) pair.
    Returns (cleaned_en, cleaned_lun) or (None, None) if the pair should be dropped.
    """
    if not isinstance(en, str) or not isinstance(lun, str):
        return None, None

    # 1. Strip domain tags
    en  = _strip_tags(en)
    lun = _strip_tags(lun)

    # 2. Strip OCR notation
    en  = _strip_ocr(en)
    lun = _strip_ocr(lun)

    # 3. Normalise
    en  = _normalise(en)
    lun = _normalise(lun)

    # 4. Drop if either side is empty or too short
    if len(en) < 3 or len(lun) < 3:
        return None, None

    # 5. Drop if either side is OCR garbage
    if _is_ocr_garbage(en) or _is_ocr_garbage(lun):
        return None, None

    # 6. Drop if src == tgt (copy pairs)
    if en.lower().strip() == lun.lower().strip():
        return None, None

    # 7. Drop if too long (> 300 chars — likely concatenated noise)
    if len(en) > 300 or len(lun) > 300:
        return None, None

    # 8. Drop if Lunyoro column looks like English
    if _is_likely_english(lun):
        return None, None

    # 9. Drop if English column looks like Lunyoro
    if _is_likely_lunyoro(en):
        return None, None

    return en, lun


def clean_split(path: str, dry_run: bool = False) -> dict:
    df = pd.read_csv(path)
    original_count = len(df)

    cleaned_en, cleaned_lun = [], []
    dropped = 0

    for _, row in df.iterrows():
        en, lun = clean_row(row.get('english', ''), row.get('lunyoro', ''))
        if en is None:
            dropped += 1
        else:
            cleaned_en.append(en)
            cleaned_lun.append(lun)

    result = pd.DataFrame({'english': cleaned_en, 'lunyoro': cleaned_lun})

    # Deduplicate
    before_dedup = len(result)
    result = result.drop_duplicates(subset=['english', 'lunyoro']).reset_index(drop=True)
    deduped = before_dedup - len(result)

    stats = {
        "original":  original_count,
        "dropped":   dropped,
        "deduped":   deduped,
        "final":     len(result),
    }

    if not dry_run:
        # Backup original
        shutil.copy(path, path + ".bak")
        result.to_csv(path, index=False, encoding='utf-8')

    return stats


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN — no files will be modified ===\n")

    for split, path in SPLITS.items():
        if not os.path.exists(path):
            print(f"  Skipping {split} (not found)")
            continue
        print(f"Cleaning {split}...")
        stats = clean_split(path, dry_run=dry_run)
        print(f"  original: {stats['original']:,}")
        print(f"  dropped:  {stats['dropped']:,}  (noise/garbage)")
        print(f"  deduped:  {stats['deduped']:,}  (exact duplicates)")
        print(f"  final:    {stats['final']:,}")
        if not dry_run:
            print(f"  → saved to {path}  (backup: {path}.bak)")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
