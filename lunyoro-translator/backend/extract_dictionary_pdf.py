"""
Extract all entries from runyoro-Rutooro-Dictionary.pdf into structured CSVs.

Outputs (saved to data/dictionary/):
  runyoro_english_dict.csv   — Runyoro headword → English definition + examples
  english_runyoro_dict.csv   — English headword → Runyoro equivalents
  dictionary_pairs.csv       — Flat (english, lunyoro) sentence/phrase pairs for training
"""

import re
import csv
import os
from PyPDF2 import PdfReader

PDF_PATH = os.path.join(os.path.dirname(__file__), "data", "dictionary", "runyoro-Rutooro-Dictionary.pdf")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "data", "dictionary")

# Page ranges (0-indexed)
RUNYORO_START = 13   # page 14
RUNYORO_END   = 445  # page 446 inclusive
ENGLISH_START = 446  # page 447
ENGLISH_END   = 626  # page 627 inclusive

# ── helpers ──────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Normalise whitespace and common OCR artefacts."""
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(' ,', ',').replace(' ;', ';').replace(' .', '.')
    text = text.replace('11-', 'n-').replace('1 ', 'l ')   # common OCR swaps
    return text.strip()


def extract_pages(reader, start, end):
    """Return concatenated text for a page range."""
    parts = []
    for i in range(start, end + 1):
        try:
            parts.append(reader.pages[i].extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)


# ── Section 1: Runyoro → English ─────────────────────────────────────────────

def parse_runyoro_section(text: str):
    """
    Parse entries of the form:
      headword, [prefix,] pos., (pf. ...); definition; example sentence.
    Also handles noun entries:
      headword, prefix, n., cl.N, (pl. ...); definition.
    Returns list of dicts.
    """
    entries = []

    # Split on likely entry boundaries: a line starting with a lowercase word
    # followed by comma or space then a grammatical marker
    # We join the full text first, then split on entry starts
    # Entry start pattern: word at beginning of a "paragraph" followed by grammar info
    entry_pattern = re.compile(
        r'(?:^|\n)'                          # start of line
        r'(-?[a-zA-Z][a-zA-Z\'\-]{0,30})'   # headword (may start with -)
        r'(?:,\s*[a-z\-]+\-?,?\s*)*'        # optional prefixes like ku-, okw-
        r',?\s*'
        r'(v\.[a-z\./ ]*|n\.|adj\.|adv\.|int\.|pron\.|num\.|prep\.|conj\.|part\.|'
        r'join\. word|tense prefix|subj\.|obj\.|gen\. part|poss\.|dem\.|rel\. cone\.|'
        r'ideoph\.|ideo\.|w\. of|foreg\.|undecl\.)',
        re.MULTILINE
    )

    # Find all entry start positions
    matches = list(entry_pattern.finditer(text))

    for idx, m in enumerate(matches):
        headword = m.group(1).strip().lstrip('-')
        pos      = m.group(2).strip()
        start    = m.start()
        end      = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body     = clean(text[start:end])

        # Extract definition (text after first semicolon)
        parts = body.split(';')
        definition = parts[1].strip() if len(parts) > 1 else ""
        # Example sentences: remaining parts that look like sentences
        examples = [p.strip() for p in parts[2:] if len(p.strip()) > 10]

        if not headword or len(headword) < 2:
            continue
        if not definition:
            continue

        entries.append({
            "runyoro_word": headword,
            "pos": pos,
            "definition_english": definition[:300],
            "example": "; ".join(examples)[:400],
            "raw": body[:500],
        })

    return entries


# ── Section 2: English → Runyoro ─────────────────────────────────────────────

def parse_english_section(text: str):
    """
    Parse entries of the form:
      english_word, [pos.,] runyoro1, runyoro2, ...; see also ...
    Returns list of dicts.
    """
    entries = []

    # Entry start: English word (capitalised or lowercase) at line start, followed by comma
    entry_pattern = re.compile(
        r'(?:^|\n)'
        r'([A-Za-z][a-zA-Z \-]{0,30})'   # English headword (may be multi-word)
        r',\s*'
        r'(v\.[a-z\./ ]*|n\.|adj\.|adv\.|int\.|pron\.|num\.|prep\.|conj\.|'
        r'v\.i\.|v\.tr\.|v\.c\.|v\.pass\.|v\.refl\.|v\.rec\.|'
        r'[a-z]+\.,?\s*)?',              # optional POS
        re.MULTILINE
    )

    matches = list(entry_pattern.finditer(text))

    for idx, m in enumerate(matches):
        headword = m.group(1).strip()
        pos      = (m.group(2) or "").strip().rstrip(',')
        start    = m.start()
        end      = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body     = clean(text[start:end])

        # Runyoro equivalents: everything after the POS, split by comma/semicolon
        after_pos = body[len(m.group(0).strip()):].strip().lstrip(',').strip()
        # Split on commas and semicolons, take tokens that look like Runyoro words
        tokens = re.split(r'[,;]', after_pos)
        runyoro_words = []
        for tok in tokens:
            tok = tok.strip().rstrip('.')
            # Runyoro words are typically lowercase, no spaces (or short phrases)
            if tok and len(tok) > 1 and not tok.startswith('see ') and len(tok) < 40:
                runyoro_words.append(tok)

        if not headword or len(headword) < 2:
            continue
        if not runyoro_words:
            continue

        entries.append({
            "english_word": headword,
            "pos": pos,
            "runyoro_equivalents": ", ".join(runyoro_words[:8]),
            "raw": body[:400],
        })

    return entries


# ── Build training pairs ──────────────────────────────────────────────────────

ENGLISH_STOPWORDS = re.compile(
    r'\b(the|a|an|is|are|was|were|to|of|in|on|at|he|she|it|they|we|you|'
    r'his|her|their|this|that|which|who|when|where|how|what|will|would|'
    r'have|has|had|be|been|being|do|does|did|not|and|or|but|if|so)\b',
    re.I
)
# Runyoro words typically contain these common prefixes/patterns
RUNYORO_PATTERN = re.compile(r'\b(oku|okw|ku-|kw-|aba|omu|emi|ebi|eki|aka|ama|obu|oru|en|em)\w+', re.I)
GRAMMAR_NOISE   = re.compile(
    r'\b(pf\.|pr\. form|c\. form|pass\. form|v\.i\.|v\.tr\.|v\.c\.|'
    r'cl\.\d|pl\.|sg\.|obj\.|subj\.|gen\. part|p\.c\.|r\.c\.|'
    r'see also|see below|see above|form,|okw-|kw-)\b', re.I
)


def is_english_sentence(text: str) -> bool:
    """True if text looks like a real English sentence (not grammar notation)."""
    if len(text) < 8 or len(text) > 300:
        return False
    if GRAMMAR_NOISE.search(text):
        return False
    words = text.split()
    if len(words) < 2:
        return False
    # Must contain at least one English stopword
    return bool(ENGLISH_STOPWORDS.search(text))


def is_runyoro_phrase(text: str) -> bool:
    """True if text looks like a Runyoro word or phrase."""
    if len(text) < 2 or len(text) > 150:
        return False
    if GRAMMAR_NOISE.search(text):
        return False
    # Should not be mostly English
    if ENGLISH_STOPWORDS.search(text) and len(text.split()) > 3:
        return False
    return True


def build_pairs_from_runyoro(entries):
    """Generate (english, lunyoro) pairs from Runyoro→English entries."""
    pairs = []
    for e in entries:
        word = e["runyoro_word"]
        defn = e["definition_english"]
        example = e["example"]

        # 1. Definition pair: English definition → Runyoro headword
        if defn and is_english_sentence(defn) and is_runyoro_phrase(word):
            # Keep only clean short definitions (not ones that bleed into next entry)
            clean_defn = defn.split('.')[0].strip()  # first sentence only
            if len(clean_defn) > 5:
                pairs.append({
                    "english": clean_defn,
                    "lunyoro": word,
                    "source": "dict_runyoro_defn",
                })

        # 2. Example sentence pairs: "runyoro sentence, english translation"
        if example:
            sents = re.split(r';\s*', example)
            for sent in sents:
                sent = sent.strip()
                if not sent or len(sent) < 15:
                    continue
                # Split on comma — Runyoro sentence first, English after
                parts = sent.split(',', 1)
                if len(parts) == 2:
                    lun_part = parts[0].strip()
                    eng_part = parts[1].strip()
                    if is_runyoro_phrase(lun_part) and is_english_sentence(eng_part):
                        pairs.append({
                            "english": eng_part,
                            "lunyoro": lun_part,
                            "source": "dict_runyoro_example",
                        })

    return pairs


def build_pairs_from_english(entries):
    """Generate (english, lunyoro) pairs from English→Runyoro entries."""
    pairs = []
    for e in entries:
        eng       = e["english_word"].strip()
        lun_equiv = e["runyoro_equivalents"]

        if not eng or len(eng) < 2 or not lun_equiv:
            continue
        # Skip entries where English word looks like noise
        if re.search(r'\d|[,;]', eng):
            continue

        # Each Runyoro equivalent becomes a pair
        for equiv in lun_equiv.split(','):
            equiv = equiv.strip().rstrip('.')
            if equiv and len(equiv) > 1 and is_runyoro_phrase(equiv):
                pairs.append({
                    "english": eng,
                    "lunyoro": equiv,
                    "source": "dict_english_equiv",
                })
                break  # one primary equivalent per English entry is enough

    return pairs


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"Reading {PDF_PATH} ...")
    reader = PdfReader(PDF_PATH)
    print(f"Total pages: {len(reader.pages)}")

    # --- Runyoro → English section ---
    print("\nExtracting Runyoro-English section (pages 14–446)...")
    runyoro_text = extract_pages(reader, RUNYORO_START, RUNYORO_END)
    runyoro_entries = parse_runyoro_section(runyoro_text)
    print(f"  Parsed {len(runyoro_entries)} Runyoro entries")

    out_path = os.path.join(OUT_DIR, "runyoro_english_dict.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["runyoro_word", "pos", "definition_english", "example", "raw"])
        writer.writeheader()
        writer.writerows(runyoro_entries)
    print(f"  Saved → {out_path}")

    # --- English → Runyoro section ---
    print("\nExtracting English-Runyoro section (pages 447–627)...")
    english_text = extract_pages(reader, ENGLISH_START, ENGLISH_END)
    english_entries = parse_english_section(english_text)
    print(f"  Parsed {len(english_entries)} English entries")

    out_path = os.path.join(OUT_DIR, "english_runyoro_dict.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["english_word", "pos", "runyoro_equivalents", "raw"])
        writer.writeheader()
        writer.writerows(english_entries)
    print(f"  Saved → {out_path}")

    # --- Training pairs ---
    print("\nBuilding training pairs...")
    pairs  = build_pairs_from_runyoro(runyoro_entries)
    pairs += build_pairs_from_english(english_entries)

    # Deduplicate and quality filter
    seen = set()
    unique_pairs = []
    for p in pairs:
        eng = p["english"].strip()
        lun = p["lunyoro"].strip()

        # Skip if too short or too long
        if len(eng) < 3 or len(lun) < 2:
            continue
        if len(eng) > 250 or len(lun) > 150:
            continue

        # Skip if English looks like Runyoro (contains typical Runyoro prefixes)
        if re.search(r'\b(oku|okw|omu|emi|ebi|eki|aka|ama|obu|oru)\w{2,}', eng):
            continue

        # Skip if Lunyoro looks like English grammar notation
        if re.search(r'\b(to |the |is |are |was |were |a |an )\b', lun, re.I):
            if len(lun.split()) > 3:
                continue

        # Skip obvious noise
        if re.search(r'pf\.|pr\. form|c\. form|pass\. form|cl\.\d', eng + lun):
            continue

        key = (eng.lower(), lun.lower())
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)

    print(f"  Total unique pairs: {len(unique_pairs)}")

    out_path = os.path.join(OUT_DIR, "dictionary_pairs.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["english", "lunyoro", "source"])
        writer.writeheader()
        writer.writerows(unique_pairs)
    print(f"  Saved → {out_path}")

    # Summary
    print("\n=== SUMMARY ===")
    print(f"  runyoro_english_dict.csv : {len(runyoro_entries):,} entries")
    print(f"  english_runyoro_dict.csv : {len(english_entries):,} entries")
    print(f"  dictionary_pairs.csv     : {len(unique_pairs):,} training pairs")

    # Sample
    print("\nSample Runyoro entries:")
    for e in runyoro_entries[:3]:
        print(f"  [{e['runyoro_word']}] ({e['pos']}) → {e['definition_english'][:80]}")

    print("\nSample English entries:")
    for e in english_entries[:3]:
        print(f"  [{e['english_word']}] → {e['runyoro_equivalents'][:80]}")

    print("\nSample training pairs:")
    for p in unique_pairs[:5]:
        print(f"  EN: {p['english'][:60]}  |  LUN: {p['lunyoro'][:40]}  ({p['source']})")


if __name__ == "__main__":
    main()
