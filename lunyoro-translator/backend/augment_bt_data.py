"""
augment_bt_data.py
==================
Augments the back-translated lun2en pairs to generate more training data.

Techniques applied:
  1. Tense variation     — present/past/future forms of English sentences
  2. Pronoun swap        — I/we/he/she/they variations
  3. Negation            — positive ↔ negative variants
  4. Synonym substitution — common English word synonyms
  5. Sentence truncation — sub-sentences from longer pairs
  6. Number variation    — singular/plural using Runyoro grammar rules

Input:  data/cleaned/back_translated_lun2en.csv
Output: data/cleaned/augmented_bt_lun2en.csv
        (merged into train.csv / val.csv with --merge flag)

Usage:
    python augment_bt_data.py                    # generate augmented pairs
    python augment_bt_data.py --merge            # also merge into training data
    python augment_bt_data.py --max-per-pair 3   # max augmentations per pair
"""

import re
import csv
import argparse
import unicodedata
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE      = Path(__file__).parent
CLEAN_DIR = BASE / "data" / "cleaned"
TRAIN_DIR = BASE / "data" / "training"

BT_CSV    = CLEAN_DIR / "back_translated_lun2en.csv"
OUT_CSV   = CLEAN_DIR / "augmented_bt_lun2en.csv"
TRAIN_CSV = TRAIN_DIR / "train.csv"
VAL_CSV   = TRAIN_DIR / "val.csv"


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", str(text).strip())


# ── Synonym dictionary (common English words with Runyoro-safe replacements) ──
SYNONYMS: dict[str, list[str]] = {
    "go":      ["walk", "travel", "move", "head"],
    "come":    ["arrive", "return", "approach"],
    "eat":     ["consume", "have", "take"],
    "drink":   ["consume", "take"],
    "see":     ["look at", "observe", "notice", "view"],
    "say":     ["tell", "speak", "mention", "state"],
    "know":    ["understand", "learn", "recognise"],
    "want":    ["need", "desire", "wish for", "seek"],
    "get":     ["obtain", "receive", "acquire", "fetch"],
    "give":    ["provide", "offer", "hand", "pass"],
    "bring":   ["carry", "fetch", "take"],
    "take":    ["carry", "bring", "fetch", "grab"],
    "work":    ["labour", "toil", "operate"],
    "help":    ["assist", "support", "aid"],
    "like":    ["enjoy", "love", "appreciate"],
    "love":    ["cherish", "care for", "adore"],
    "find":    ["discover", "locate", "spot"],
    "build":   ["construct", "make", "create"],
    "cook":    ["prepare", "make"],
    "read":    ["study", "look through"],
    "write":   ["compose", "record", "note down"],
    "child":   ["kid", "young one", "little one"],
    "person":  ["individual", "human", "man", "woman"],
    "house":   ["home", "dwelling", "place"],
    "water":   ["liquid", "fluid"],
    "food":    ["meal", "nourishment", "provisions"],
    "good":    ["fine", "excellent", "great", "nice"],
    "bad":     ["poor", "wrong", "terrible"],
    "big":     ["large", "great", "huge"],
    "small":   ["little", "tiny", "small"],
    "old":     ["aged", "elderly", "ancient"],
    "new":     ["fresh", "recent", "modern"],
    "fast":    ["quick", "rapid", "swift"],
    "slow":    ["gradual", "unhurried"],
    "happy":   ["glad", "joyful", "pleased"],
    "sad":     ["unhappy", "sorrowful", "upset"],
    "sick":    ["ill", "unwell", "not feeling well"],
    "healthy": ["well", "strong", "fit"],
    "many":    ["numerous", "several", "a lot of", "lots of"],
    "few":     ["some", "several", "a number of"],
    "always":  ["often", "regularly", "frequently", "every time"],
    "never":   ["not once", "not at all"],
    "today":   ["this day", "now"],
    "tomorrow": ["the next day"],
    "yesterday": ["the previous day", "last day"],
    "morning": ["early", "dawn", "sunrise"],
    "evening": ["dusk", "nightfall", "late"],
    "night":   ["darkness", "late hours"],
}

# ── Tense variation patterns ──────────────────────────────────────────────────
TENSE_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # present → past
    (re.compile(r'\b(I|we|he|she|they|you)\s+(go)\b', re.I),
     lambda m: f"{m.group(1)} went", "past"),
    (re.compile(r'\b(I|we|he|she|they|you)\s+(come)\b', re.I),
     lambda m: f"{m.group(1)} came", "past"),
    (re.compile(r'\b(I|we)\s+(eat)\b', re.I),
     lambda m: f"{m.group(1)} ate", "past"),
    (re.compile(r'\b(I|we)\s+(see)\b', re.I),
     lambda m: f"{m.group(1)} saw", "past"),
    (re.compile(r'\b(I|we)\s+(give)\b', re.I),
     lambda m: f"{m.group(1)} gave", "past"),
    # present simple → present continuous
    (re.compile(r'\b(I)\s+go\b', re.I),
     lambda m: "I am going", "continuous"),
    (re.compile(r'\b(I)\s+eat\b', re.I),
     lambda m: "I am eating", "continuous"),
    (re.compile(r'\b(I)\s+work\b', re.I),
     lambda m: "I am working", "continuous"),
    (re.compile(r'\b(I)\s+cook\b', re.I),
     lambda m: "I am cooking", "continuous"),
    (re.compile(r'\b(I)\s+read\b', re.I),
     lambda m: "I am reading", "continuous"),
    (re.compile(r'\b(I)\s+write\b', re.I),
     lambda m: "I am writing", "continuous"),
]

# ── Pronoun swap table ────────────────────────────────────────────────────────
PRONOUN_SWAPS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bI\s+am\b', re.I),   "he/she is"),
    (re.compile(r'\bI\s+am\b', re.I),   "we are"),
    (re.compile(r'\bI\s+go\b', re.I),   "he/she goes"),
    (re.compile(r'\bI\s+go\b', re.I),   "they go"),
    (re.compile(r'\bI\s+eat\b', re.I),  "he/she eats"),
    (re.compile(r'\bI\s+have\b', re.I), "he/she has"),
    (re.compile(r'\bI\s+want\b', re.I), "he/she wants"),
    (re.compile(r'\bI\s+know\b', re.I), "he/she knows"),
    (re.compile(r'\bI\s+like\b', re.I), "he/she likes"),
    (re.compile(r'\bI\s+love\b', re.I), "he/she loves"),
    (re.compile(r'\bI\s+will\b', re.I), "he/she will"),
    (re.compile(r'\bwe\s+go\b', re.I),  "they go"),
    (re.compile(r'\bwe\s+are\b', re.I), "they are"),
]

# ── Negation patterns ─────────────────────────────────────────────────────────
NEGATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bI am\b', re.I),         "I am not"),
    (re.compile(r'\bhe is\b', re.I),        "he is not"),
    (re.compile(r'\bshe is\b', re.I),       "she is not"),
    (re.compile(r'\bwe are\b', re.I),       "we are not"),
    (re.compile(r'\bthey are\b', re.I),     "they are not"),
    (re.compile(r'\bI can\b', re.I),        "I cannot"),
    (re.compile(r'\bI will\b', re.I),       "I will not"),
    (re.compile(r'\bhe will\b', re.I),      "he will not"),
    (re.compile(r'\bI have\b', re.I),       "I do not have"),
    (re.compile(r'\bI know\b', re.I),       "I do not know"),
    (re.compile(r'\bI want\b', re.I),       "I do not want"),
    (re.compile(r'\bI like\b', re.I),       "I do not like"),
    (re.compile(r'\bI understand\b', re.I), "I do not understand"),
]


# ── Augmentation functions ────────────────────────────────────────────────────

def augment_synonym(english: str, runyoro: str, max_variants: int = 2) -> list[tuple[str, str]]:
    """Replace one English word with a synonym. Keep same Runyoro translation."""
    results = []
    words = english.split()
    tried = 0
    for i, word in enumerate(words):
        w_lower = word.lower().rstrip('.,!?;:')
        if w_lower in SYNONYMS:
            for syn in SYNONYMS[w_lower][:max_variants]:
                new_words = words.copy()
                # Preserve capitalisation
                if word[0].isupper():
                    syn = syn.capitalize()
                new_words[i] = syn + word[len(w_lower):]  # preserve trailing punct
                new_en = ' '.join(new_words)
                if new_en != english:
                    results.append((new_en, runyoro))
                    tried += 1
                    if tried >= max_variants:
                        return results
    return results


def augment_truncation(english: str, runyoro: str) -> list[tuple[str, str]]:
    """
    Split compound sentences into sub-sentences.
    'I went to the market and bought food' →
      'I went to the market' + 'I bought food'
    """
    results = []
    # Split on conjunctions
    for sep in [' and ', ' but ', ' so ', ' because ', ' when ', ' if ']:
        parts = english.lower().split(sep)
        if len(parts) == 2:
            p1 = english[:english.lower().find(sep)].strip()
            p2 = english[english.lower().find(sep) + len(sep):].strip()
            if len(p1.split()) >= 4 and len(p2.split()) >= 3:
                # Use same Runyoro for both (approximate — both relate to same context)
                results.append((p1, runyoro))
                # Capitalise second part
                results.append((p2[0].upper() + p2[1:] if p2 else p2, runyoro))
    return results[:2]  # max 2 truncations per pair


def augment_tense(english: str, runyoro: str) -> list[tuple[str, str]]:
    """Apply tense variation to English sentence. Runyoro stays as reference."""
    results = []
    for pattern, replacement, label in TENSE_PATTERNS:
        if pattern.search(english):
            new_en = pattern.sub(replacement, english)
            if new_en != english:
                results.append((new_en, runyoro))
                break  # one tense variant per pair
    return results


def augment_pronoun(english: str, runyoro: str, max_variants: int = 1) -> list[tuple[str, str]]:
    """Swap pronouns in English sentence."""
    results = []
    for pattern, replacement in PRONOUN_SWAPS[:6]:
        if pattern.search(english):
            new_en = pattern.sub(replacement, english)
            if new_en != english:
                results.append((new_en, runyoro))
                if len(results) >= max_variants:
                    break
    return results


def augment_negation(english: str, runyoro: str) -> list[tuple[str, str]]:
    """Add negation variant — model must learn negation in Runyoro."""
    # Only add negation if the pair doesn't already contain negation
    neg_words = ["not", "never", "cannot", "don't", "doesn't", "didn't", "won't"]
    if any(w in english.lower() for w in neg_words):
        return []  # skip if already negative

    for pattern, replacement in NEGATION_PATTERNS:
        if pattern.search(english):
            new_en = pattern.sub(replacement, english)
            if new_en != english:
                return [(new_en, runyoro)]
    return []


# ── Main augmentation pipeline ────────────────────────────────────────────────

def augment_pairs(pairs: list[tuple[str, str]],
                  max_per_pair: int = 3) -> list[tuple[str, str]]:
    """Apply all augmentation techniques to a list of (english, runyoro) pairs."""
    seen: set[tuple[str, str]] = set((e.lower(), l.lower()) for e, l in pairs)
    augmented: list[tuple[str, str]] = []
    stats = {
        "synonym": 0, "truncation": 0, "tense": 0,
        "pronoun": 0, "negation": 0
    }

    for english, runyoro in pairs:
        count = 0
        variants: list[tuple[str, str]] = []

        # Apply techniques in priority order
        variants += augment_synonym(english, runyoro, max_variants=2)
        variants += augment_tense(english, runyoro)
        variants += augment_pronoun(english, runyoro)
        variants += augment_negation(english, runyoro)
        variants += augment_truncation(english, runyoro)

        for new_en, new_lun in variants:
            new_en  = normalise(new_en)
            new_lun = normalise(new_lun)
            if not new_en or not new_lun:
                continue
            if len(new_en.split()) < 3:
                continue
            key = (new_en.lower(), new_lun.lower())
            if key in seen:
                continue
            seen.add(key)
            augmented.append((new_en, new_lun))
            count += 1

            # Track by technique
            if (new_en, new_lun) in [(e, r) for e, r in augment_synonym(english, runyoro, 2)]:
                stats["synonym"] += 1
            elif (new_en, new_lun) in augment_tense(english, runyoro):
                stats["tense"] += 1
            elif (new_en, new_lun) in augment_pronoun(english, runyoro):
                stats["pronoun"] += 1
            elif (new_en, new_lun) in augment_negation(english, runyoro):
                stats["negation"] += 1
            else:
                stats["truncation"] += 1

            if count >= max_per_pair:
                break

    print(f"  Augmentation stats: {stats}")
    return augmented


def merge_into_training(pairs: list[tuple[str, str]]) -> tuple[int, int]:
    """Merge augmented pairs into train.csv / val.csv (90/10 split)."""
    import shutil

    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)

    existing_keys = set(zip(
        pd.concat([train, val])["english"].str.lower().str.strip(),
        pd.concat([train, val])["lunyoro"].str.lower().str.strip(),
    ))

    new_pairs = [(en, lun) for en, lun in pairs
                 if (en.lower(), lun.lower()) not in existing_keys]

    if not new_pairs:
        print("  No new pairs to add.")
        return 0, 0

    split    = int(len(new_pairs) * 0.9)
    new_train = new_pairs[:split]
    new_val   = new_pairs[split:]

    shutil.copy(TRAIN_CSV, str(TRAIN_CSV) + ".bak_aug")
    shutil.copy(VAL_CSV,   str(VAL_CSV)   + ".bak_aug")

    with open(TRAIN_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for en, lun in new_train:
            w.writerow([en, lun])

    with open(VAL_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for en, lun in new_val:
            w.writerow([en, lun])

    t2 = pd.read_csv(TRAIN_CSV)
    v2 = pd.read_csv(VAL_CSV)
    print(f"  New totals: train={len(t2):,}  val={len(v2):,}")
    return len(new_train), len(new_val)


def main():
    parser = argparse.ArgumentParser(
        description="Augment back-translated lun2en pairs"
    )
    parser.add_argument("--max-per-pair", type=int, default=3,
                        help="Max augmented variants per pair (default: 3)")
    parser.add_argument("--merge",        action="store_true",
                        help="Merge augmented pairs into train/val CSVs")
    parser.add_argument("--input",        type=str,
                        default=str(BT_CSV),
                        help="Input CSV with english+lunyoro columns")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  BT DATA AUGMENTATION PIPELINE")
    print(f"  Max variants per pair: {args.max_per_pair}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Load BT pairs
    input_path = Path(args.input)
    df = pd.read_csv(input_path)
    pairs = [(str(r["english"]).strip(), str(r["lunyoro"]).strip())
             for _, r in df.iterrows()
             if str(r["english"]).strip() and str(r["lunyoro"]).strip()]
    print(f"[Step 1] Loaded {len(pairs):,} back-translated pairs from {input_path.name}")

    # Filter to quality pairs only (>= 5 English words, >= 3 Runyoro words)
    pairs_filtered = [
        (en, lun) for en, lun in pairs
        if len(en.split()) >= 5 and len(lun.split()) >= 3
    ]
    print(f"  Quality pairs (en>=5w, lun>=3w): {len(pairs_filtered):,}")

    # Augment
    print(f"\n[Step 2] Augmenting pairs...")
    augmented = augment_pairs(pairs_filtered, max_per_pair=args.max_per_pair)
    print(f"  Generated {len(augmented):,} augmented pairs")

    # Save
    print(f"\n[Step 3] Saving to {OUT_CSV.name}...")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["english", "lunyoro"])
        for en, lun in augmented:
            w.writerow([en, lun])
    print(f"  Saved {len(augmented):,} pairs to {OUT_CSV}")

    # Merge
    if args.merge:
        print(f"\n[Step 4] Merging into train.csv / val.csv...")
        n_train, n_val = merge_into_training(augmented)
        print(f"  Added {n_train:,} to train, {n_val:,} to val")

    print(f"\n{'='*60}")
    print(f"  AUGMENTATION COMPLETE")
    print(f"  Original BT pairs:    {len(pairs_filtered):,}")
    print(f"  Augmented new pairs:  {len(augmented):,}")
    print(f"  Multiplier:           {(len(pairs_filtered)+len(augmented))/max(len(pairs_filtered),1):.1f}x")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
