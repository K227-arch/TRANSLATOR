"""
clean_ocr_pairs.py
==================
Removes truncated/noisy rows from ocr_pairs_extracted.csv.

A row is considered bad if:
  1. English side starts with a lowercase letter (truncated left margin)
  2. English side starts with punctuation like ', >, \, "
  3. English side is a grammar notation line (contains 'e.g.', 'apodosis',
     'protasis', 'formative', 'tense prefix', 'introductory word', etc.)
  4. Either side is empty or too short (< 4 chars)
  5. Either side contains raw LaTeX/notation artifacts (\varphi, c/.14, etc.)
  6. English side is a page header like "Conditions expressed by verbs 279"
  7. Lunyoro side starts with a grammar label like "ru ya:", "ti ya:", "aba:", etc.
"""

import csv
import re
from pathlib import Path

INPUT  = Path(__file__).parent / "data/cleaned/ocr_pairs_extracted.csv.bak"
OUTPUT = Path(__file__).parent / "data/cleaned/ocr_pairs_extracted.csv"
BACKUP = Path(__file__).parent / "data/cleaned/ocr_pairs_extracted.csv.bak"

# ── Patterns that mark a bad row ─────────────────────────────────────────────

# English starts with lowercase (truncated margin)
RE_STARTS_LOWERCASE = re.compile(r'^[a-z]')

# Starts with punctuation/apostrophe that indicates truncation
RE_STARTS_PUNCT = re.compile("^['>\\\\<\\*\\+\\-\\|\"'\u2018\u2019\u201C\u201D]")

# Grammar/meta notation in English side
GRAMMAR_KEYWORDS = [
    "e.g.", "apodosis", "protasis", "formative", "tense prefix",
    "introductory word", "conditional tense", "present-imperfect",
    "present-indefinite", "far-future", "near-future", "subordinate clause",
    "grammatical function", "adverbial formative", "monosyllabic stem",
    "enclitic", "prepositional", "concord in use", "negative form",
    "positive form", "expressed by verbs", "participle", "compound tense",
    "shortened form", "interjectionally", "co-ordinate rank",
    "according to their function", "adverbs may be divided",
    "suffix -ge is added", "nominal prefix", "introductory word",
    "obu as an introductory", "kakuba or kuba", "with kakuba",
    "with obu", "(1) with", "(2) words with", "(3) to express",
    "(4) cause, reason", "by the use of verbs", "note the double",
    "relative conditional", "direct phrases", "not-yet", "not-still",
    "joining two words", "merely state the condition",
]

# Page header pattern: "Word word word NNN"
RE_PAGE_HEADER = re.compile(r'^[A-Z][a-z].*\d{2,3}$')

# LaTeX / notation artifacts
RE_NOTATION = re.compile(r'\\[a-zA-Z]+|c/\.\d+|\bpl\.\s*nil\b|\bn\.\s*cl\b')

# Lunyoro side starts with a grammar label like "ru ya:", "aba:", "na:", etc.
RE_LUN_LABEL = re.compile(r'^[a-z]{1,6}\s+(ya|na|nka|oku|obu|ti|ru|aba|hamu)?\s*:')

# ── Filter function ───────────────────────────────────────────────────────────

def is_bad_row(en: str, lun: str) -> bool:
    en  = en.strip()
    lun = lun.strip()

    # Empty or too short
    if len(en) < 4 or len(lun) < 4:
        return True

    # English starts with lowercase (truncated)
    if RE_STARTS_LOWERCASE.match(en):
        return True

    # Starts with truncation punctuation
    if RE_STARTS_PUNCT.match(en):
        return True

    # Grammar/meta notation keywords
    en_lower = en.lower()
    if any(kw in en_lower for kw in GRAMMAR_KEYWORDS):
        return True

    # Page header (e.g. "Conditions expressed by verbs 279")
    if RE_PAGE_HEADER.match(en):
        return True

    # LaTeX / notation artifacts in either side
    if RE_NOTATION.search(en) or RE_NOTATION.search(lun):
        return True

    # Lunyoro side is a grammar label
    if RE_LUN_LABEL.match(lun):
        return True

    # Catch any remaining "word:" or "word word:" grammar labels in lunyoro
    if re.match(r'^[a-z]{1,10}(\s+[a-z]{1,4})?\s*:', lun):
        return True

    # Catch lunyoro labels with dots/ellipsis like "okuruga ... okuhikya:"
    if re.search(r':\s*[A-Z][a-z]', lun) and re.match(r'^[a-z]', lun):
        return True

    # Catch in'ekindi: style labels
    if re.match(r"^[a-z']{1,15}:", lun):
        return True

    # Lunyoro side starts with lowercase and looks like a fragment
    if lun[0].islower() and len(lun.split()) <= 3:
        return True

    return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    rows = []
    with open(INPUT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    total = len(rows)
    kept  = [(r["english"], r["lunyoro"]) for r in rows
             if not is_bad_row(r.get("english",""), r.get("lunyoro",""))]
    removed = total - len(kept)

    # Backup original
    import shutil
    print(f"Reading from backup: {INPUT.name}")

    # Write cleaned file
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "lunyoro"])
        for en, lun in kept:
            writer.writerow([en, lun])

    print(f"Total rows:   {total}")
    print(f"Removed:      {removed}")
    print(f"Kept:         {len(kept)}")
    print(f"Saved to:     {OUTPUT.name}")


if __name__ == "__main__":
    main()
