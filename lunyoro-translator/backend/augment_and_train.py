"""
augment_and_train.py
====================
Full CI/CD pipeline:
  1. Generate augmented training pairs from the domain dictionary POS data
       - POS-tagged pairs        ([NOUN] / [VERB] / [ADJ] prefixed)
       - Plural augmentation     (noun class plural forms)
       - Verb infinitive pairs   (oku- forms + conjugations)
  2. Clean the generated data through the same pipeline as all other data
  3. Merge into train.csv / val.csv (deduplication)
  4. Train MarianMT  en2lun + lun2en
  5. Train NLLB      en2lun + lun2en
  6. Push models to HuggingFace Hub
  7. Push backend to HF Space
  8. Push code to GitHub (both repos)

Usage:
    python augment_and_train.py                    # full pipeline
    python augment_and_train.py --augment-only     # only generate + clean data
    python augment_and_train.py --train-only       # skip augmentation, just train
    python augment_and_train.py --no-push          # skip all pushes
    python augment_and_train.py --epochs 3         # set training epochs
    python augment_and_train.py --marian-only      # skip NLLB
    python augment_and_train.py --nllb-only        # skip MarianMT
"""

import argparse
import os
import re
import sys
import csv
import subprocess
import unicodedata
from pathlib import Path
from datetime import datetime

BASE      = Path(__file__).parent
DATA_DIR  = BASE / "data"
CLEAN_DIR = DATA_DIR / "cleaned"
TRAIN_DIR = DATA_DIR / "training"

DICT_CSV   = CLEAN_DIR / "runyoro_domain_dictionary_clean.csv"
AUG_CSV    = CLEAN_DIR / "augmented_pos_pairs.csv"
TRAIN_CSV  = TRAIN_DIR / "train.csv"
VAL_CSV    = TRAIN_DIR / "val.csv"

# ── Noun class plural rules ───────────────────────────────────────────────────
# Maps singular prefix → (plural prefix, english plural suffix hint)
NOUN_CLASS_PLURALS = {
    # Class 1 → Class 2
    "omu":  ("aba",  "people/persons"),
    "omw":  ("ab",   "people/persons"),
    # Class 3 → Class 4
    "omu":  ("emi",  "trees/plants"),   # overridden below by context
    # Class 5 → Class 6
    "eri":  ("ama",  ""),
    "ery":  ("ama",  ""),
    # Class 7 → Class 8
    "eki":  ("ebi",  "things"),
    "eky":  ("eby",  "things"),
    # Class 9 → Class 10 (same prefix, context-dependent)
    "en":   ("en",   ""),
    "em":   ("em",   ""),
    # Class 11 → Class 10
    "oru":  ("en",   ""),
    "orw":  ("en",   ""),
    # Class 12 → Class 13
    "aka":  ("utu",  "small things"),
    "akw":  ("utw",  "small things"),
    # Class 14 → Class 6 (abstract → instances)
    "obu":  ("ama",  ""),
    "obw":  ("ama",  ""),
}

# Class 1 (person) → Class 2 plural: most reliable
PERSON_PREFIXES = {"omu", "omw"}

# Verb infinitive prefix
VERB_PREFIXES = {"oku", "okw"}

# POS label → training tag
POS_TAG_MAP = {
    "noun":        "NOUN",
    "verb":        "VERB",
    "adjective":   "ADJ",
    "adverb":      "ADV",
    "pronoun":     "PRON",
    "conjunction": "CONJ",
    "preposition": "PREP",
    "interjection":"INTERJ",
    "numeral":     "NUM",
}


def normalise(text: str) -> str:
    """NFC normalise and strip extra whitespace."""
    return unicodedata.normalize("NFC", text.strip())


def apply_rl_rule(word: str) -> str:
    """Apply R/L rule: L→R except adjacent to e/i."""
    chars = list(word)
    result = []
    for i, ch in enumerate(chars):
        if ch not in ('l', 'L'):
            result.append(ch)
            continue
        prev = chars[i-1].lower() if i > 0 else ''
        nxt  = chars[i+1].lower() if i < len(chars)-1 else ''
        if prev in ('e','i') or nxt in ('e','i'):
            result.append(ch)
        else:
            result.append('R' if ch.isupper() else 'r')
    return ''.join(result)


def apply_nasal_assimilation(word: str) -> str:
    """nb→mb, np→mp, nr→nd, nl→nd."""
    for src, tgt in [("nb","mb"),("np","mp"),("nr","nd"),("nl","nd")]:
        word = word.replace(src, tgt)
    return word


def fix_spelling(word: str) -> str:
    """Apply core orthographic rules to a Runyoro word."""
    word = normalise(word)
    word = apply_nasal_assimilation(word)
    word = apply_rl_rule(word)
    return word


def make_plural(singular: str, pos: str) -> tuple[str, str] | None:
    """
    Generate plural form of a Runyoro noun.
    Returns (plural_lunyoro, plural_hint) or None if not applicable.
    """
    if pos != "noun":
        return None
    w = singular.lower().strip()

    # Class 1 (omu-/omw-) → Class 2 (aba-/ab-)
    if w.startswith("omw"):
        stem = w[3:]
        plural = fix_spelling("ab" + stem)
        return plural, "plural of " + singular

    if w.startswith("omu"):
        stem = w[3:]
        # Distinguish class 1 (person) from class 3 (tree/plant)
        # Heuristic: if english contains person-related words → class 1
        plural = fix_spelling("aba" + stem)
        return plural, "plural of " + singular

    # Class 7 (eki-/eky-) → Class 8 (ebi-/eby-)
    if w.startswith("eky"):
        plural = fix_spelling("eby" + w[3:])
        return plural, "plural of " + singular
    if w.startswith("eki"):
        plural = fix_spelling("ebi" + w[3:])
        return plural, "plural of " + singular

    # Class 5 (eri-/ery-) → Class 6 (ama-)
    if w.startswith("ery"):
        plural = fix_spelling("ama" + w[3:])
        return plural, "plural of " + singular
    if w.startswith("eri"):
        plural = fix_spelling("ama" + w[3:])
        return plural, "plural of " + singular

    # Class 12 (aka-/akw-) → Class 13 (utu-/utw-)
    if w.startswith("akw"):
        plural = fix_spelling("utw" + w[3:])
        return plural, "plural of " + singular
    if w.startswith("aka"):
        plural = fix_spelling("utu" + w[3:])
        return plural, "plural of " + singular

    # Class 11 (oru-/orw-) → Class 10 (en-/em-)
    if w.startswith("orw"):
        stem = w[3:]
        prefix = "em" if stem and stem[0] in "bp" else "en"
        plural = fix_spelling(prefix + stem)
        return plural, "plural of " + singular
    if w.startswith("oru"):
        stem = w[3:]
        prefix = "em" if stem and stem[0] in "bp" else "en"
        plural = fix_spelling(prefix + stem)
        return plural, "plural of " + singular

    return None


def make_verb_forms(infinitive: str, english: str) -> list[tuple[str, str]]:
    """
    Generate useful verb training pairs from an infinitive.
    Returns list of (lunyoro, english) pairs.
    """
    pairs = []
    w = infinitive.lower().strip()

    # Strip oku-/okw- to get stem
    if w.startswith("okw"):
        stem = w[3:]
        inf_prefix = "okw"
    elif w.startswith("oku"):
        stem = w[3:]
        inf_prefix = "oku"
    else:
        return pairs

    if not stem:
        return pairs

    # Clean english: strip "to " prefix for base form
    eng_base = re.sub(r'^to\s+', '', english.strip().lower())

    # 1. Infinitive pair (already in base data, but add with [VERB] tag)
    # handled by POS tagging

    # 2. Present tense 1sg: n + stem (I do X)
    present_1sg = fix_spelling("n" + stem)
    pairs.append((present_1sg, f"I {eng_base}"))

    # 3. Present tense 3sg: a + stem (he/she does X)
    present_3sg = fix_spelling("a" + stem)
    # Correct 3sg English: avoid double-s
    if eng_base.endswith('s') or eng_base.endswith('sh') or eng_base.endswith('ch'):
        eng_3sg = f"he/she {eng_base}es"
    elif eng_base.endswith('y') and len(eng_base) > 1 and eng_base[-2] not in 'aeiou':
        eng_3sg = f"he/she {eng_base[:-1]}ies"
    else:
        eng_3sg = f"he/she {eng_base}s"
    pairs.append((present_3sg, eng_3sg))

    # 4. Perfect tense 1sg: n + stem_root + ire (I have done X)
    root = stem.rstrip("a")
    # Apply consonant mutations for perfect
    if root.endswith("r"):
        perfect_root = root[:-1] + "z"
    elif root.endswith("t"):
        perfect_root = root[:-1] + "s"
    elif root.endswith("j"):
        perfect_root = root[:-1] + "z"
    else:
        perfect_root = root
    perfect_1sg = fix_spelling("n" + perfect_root + "ire")
    # Correct perfect English
    if eng_base.endswith('e'):
        eng_perfect = f"I have {eng_base}d"
    elif eng_base.endswith('y') and len(eng_base) > 1 and eng_base[-2] not in 'aeiou':
        eng_perfect = f"I have {eng_base[:-1]}ied"
    else:
        eng_perfect = f"I have {eng_base}ed"
    pairs.append((perfect_1sg, eng_perfect))

    # 5. Imperative sg: stem (do X!)
    imperative = fix_spelling(stem)
    pairs.append((imperative, f"{eng_base}!"))

    # 6. Negative present: ti + n + stem (I don't do X)
    neg = fix_spelling("tin" + stem)
    pairs.append((neg, f"I don't {eng_base}"))

    return pairs


# ── Step 1: Generate augmented pairs ─────────────────────────────────────────

def generate_augmented_pairs() -> list[tuple[str, str]]:
    """
    Generate augmented training pairs from the domain dictionary.
    Returns list of (english, lunyoro) pairs.
    """
    import pandas as pd

    if not DICT_CSV.exists():
        print(f"[augment] Dictionary not found: {DICT_CSV}")
        return []

    df = pd.read_csv(DICT_CSV)
    print(f"[augment] Loaded {len(df):,} dictionary entries")

    pairs = []
    stats = {
        "pos_tagged":    0,
        "plural":        0,
        "verb_forms":    0,
        "skipped":       0,
    }

    for _, row in df.iterrows():
        lunyoro = normalise(str(row.get("lunyoro", "") or ""))
        english = normalise(str(row.get("english", "") or ""))
        pos     = str(row.get("pos", "") or "").strip().lower()
        domain  = str(row.get("domain", "General") or "General").strip()

        if not lunyoro or not english or lunyoro == "nan" or english == "nan":
            stats["skipped"] += 1
            continue

        # Apply spelling corrections to the Runyoro word
        lunyoro_fixed = fix_spelling(lunyoro)

        # ── A. POS-tagged pair ────────────────────────────────────────────────
        pos_tag = POS_TAG_MAP.get(pos, "")
        domain_tag = domain.upper().replace(" ", "_").replace("&", "AND")
        if pos_tag:
            # Format: [DOMAIN_POS] english → lunyoro
            tagged_en = f"[{domain_tag}_{pos_tag}] {english}"
            pairs.append((tagged_en, lunyoro_fixed))
            stats["pos_tagged"] += 1

        # ── B. Plural augmentation (nouns only) ───────────────────────────────
        if pos == "noun":
            plural_result = make_plural(lunyoro_fixed, pos)
            if plural_result:
                plural_lun, plural_hint = plural_result
                # English plural: proper pluralisation
                eng_words = english.split()
                if eng_words:
                    last = eng_words[-1]
                    # Remove leading article "a/an" if present
                    base_words = eng_words[:]
                    if base_words[0].lower() in ('a', 'an', 'the'):
                        base_words = base_words[1:]
                    base_eng = ' '.join(base_words)
                    last = base_words[-1] if base_words else last
                    if last.endswith('s') or last.endswith('x') or last.endswith('z'):
                        eng_plural = base_eng + "es"
                    elif last.endswith('sh') or last.endswith('ch'):
                        eng_plural = base_eng + "es"
                    elif last.endswith('y') and len(last) > 1 and last[-2] not in 'aeiou':
                        eng_plural = base_eng[:-1] + "ies"
                    else:
                        eng_plural = base_eng + "s"
                else:
                    eng_plural = english + "s"

                tagged_plural_en = f"[{domain_tag}_NOUN_PLURAL] {eng_plural}"
                pairs.append((tagged_plural_en, plural_lun))
                stats["plural"] += 1

        # ── C. Verb infinitive + conjugation pairs ────────────────────────────
        if pos == "verb":
            w = lunyoro_fixed.lower()
            if w.startswith("oku") or w.startswith("okw"):
                verb_pairs = make_verb_forms(lunyoro_fixed, english)
                for lun_form, eng_form in verb_pairs:
                    tagged_en = f"[{domain_tag}_VERB] {eng_form}"
                    pairs.append((tagged_en, lun_form))
                stats["verb_forms"] += len(verb_pairs)

    print(f"[augment] Generated pairs:")
    print(f"  POS-tagged:   {stats['pos_tagged']:,}")
    print(f"  Plural forms: {stats['plural']:,}")
    print(f"  Verb forms:   {stats['verb_forms']:,}")
    print(f"  Skipped:      {stats['skipped']:,}")
    print(f"  Total:        {len(pairs):,}")
    return pairs


# ── Step 2: Clean the generated data ─────────────────────────────────────────

def clean_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Apply the same cleaning rules used across all training data.
    Removes: empty, too short, duplicates, identical src/tgt.
    """
    seen = set()
    cleaned = []
    removed = {"empty": 0, "too_short": 0, "identical": 0, "duplicate": 0}

    for en, lun in pairs:
        en  = normalise(en)
        lun = normalise(lun)

        if not en or not lun:
            removed["empty"] += 1
            continue

        # Strip domain/pos tag for length check
        en_bare = re.sub(r'^\[[^\]]+\]\s*', '', en).strip()
        if len(en_bare) < 2 or len(lun) < 2:
            removed["too_short"] += 1
            continue

        if en_bare.lower() == lun.lower():
            removed["identical"] += 1
            continue

        key = (en.lower(), lun.lower())
        if key in seen:
            removed["duplicate"] += 1
            continue

        seen.add(key)
        cleaned.append((en, lun))

    print(f"[clean] Removed: {removed}")
    print(f"[clean] Clean pairs: {len(cleaned):,}")
    return cleaned


# ── Step 3: Merge into training data ─────────────────────────────────────────

def merge_into_training(pairs: list[tuple[str, str]]) -> tuple[int, int]:
    """
    Merge new pairs into train.csv and val.csv.
    Returns (n_train_added, n_val_added).
    """
    import pandas as pd

    # Load existing
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)

    existing_keys = set(zip(
        pd.concat([train, val])['english'].str.lower(),
        pd.concat([train, val])['lunyoro'].str.lower(),
    ))

    new_pairs = [
        (en, lun) for en, lun in pairs
        if (en.lower(), lun.lower()) not in existing_keys
    ]

    if not new_pairs:
        print("[merge] No new pairs to add (all already in training data)")
        return 0, 0

    # 90/10 split
    split = int(len(new_pairs) * 0.9)
    new_train = new_pairs[:split]
    new_val   = new_pairs[split:]

    # Backup
    train.to_csv(TRAIN_CSV.with_suffix('.csv.bak'), index=False)
    val.to_csv(VAL_CSV.with_suffix('.csv.bak'),     index=False)

    # Append
    import csv as _csv
    with open(TRAIN_CSV, 'a', newline='', encoding='utf-8') as f:
        w = _csv.writer(f)
        for en, lun in new_train:
            w.writerow([en, lun])

    with open(VAL_CSV, 'a', newline='', encoding='utf-8') as f:
        w = _csv.writer(f)
        for en, lun in new_val:
            w.writerow([en, lun])

    # Save augmented pairs CSV for reference
    with open(AUG_CSV, 'w', newline='', encoding='utf-8') as f:
        w = _csv.writer(f)
        w.writerow(['english', 'lunyoro'])
        for en, lun in new_pairs:
            w.writerow([en, lun])

    print(f"[merge] Added {len(new_train):,} to train.csv, {len(new_val):,} to val.csv")
    print(f"[merge] Saved augmented pairs → {AUG_CSV.name}")

    new_train_total = len(train) + len(new_train)
    new_val_total   = len(val)   + len(new_val)
    print(f"[merge] New totals: train={new_train_total:,}  val={new_val_total:,}")
    return len(new_train), len(new_val)


# ── Step 4 & 5: Train models ──────────────────────────────────────────────────

def run(step: str, cmd: list[str], cwd: Path = BASE) -> bool:
    print(f"\n{'='*60}")
    print(f"  {step}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n[FAIL] {step} (exit {result.returncode})")
        return False
    print(f"\n[OK] {step}")
    return True


def train_models(args) -> list[str]:
    """Train MarianMT and/or NLLB. Returns list of failed steps."""
    py = sys.executable
    failed = []

    if not args.nllb_only:
        ok = run(
            f"MarianMT fine-tuning ({args.direction}, {args.epochs} epochs)",
            [py, "train_marian.py",
             "--direction", args.direction,
             "--epochs",    str(args.epochs),
             "--batch-size", str(args.batch_marian)],
        )
        if not ok:
            failed.append("MarianMT")

    if not args.marian_only:
        ok = run(
            f"NLLB fine-tuning ({args.direction}, {args.epochs} epochs)",
            [py, "train_nllb.py",
             "--direction", args.direction,
             "--epochs",    str(args.epochs),
             "--batch-size", str(args.batch_nllb)],
        )
        if not ok:
            failed.append("NLLB")

    return failed


# ── Step 6 & 7 & 8: Push ─────────────────────────────────────────────────────

def push_all(args, failed_steps: list[str]):
    """Push models to HF Hub, backend to HF Space, code to GitHub."""
    py = sys.executable

    if failed_steps:
        print(f"\n[WARN] Skipping push — failed steps: {failed_steps}")
        return

    # Load HF token
    hf_token = os.getenv("HF_TOKEN", "")
    if not hf_token:
        env_path = BASE / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("HF_TOKEN="):
                    hf_token = line.split("=", 1)[1].strip()
                    os.environ["HF_TOKEN"] = hf_token
                    break

    if not hf_token:
        print("[WARN] HF_TOKEN not set — skipping HuggingFace push")
    else:
        # Push models to HF Hub
        run("Push models to HuggingFace Hub", [py, "upload_models_to_hf.py"])

        # Push backend to HF Space
        run("Push backend to HF Space", [py, "push_to_hf_space.py"])

    # Push code to GitHub
    git_cmds = [
        ["git", "add", "data/training/train.csv", "data/training/val.csv",
         "data/cleaned/augmented_pos_pairs.csv"],
        ["git", "commit", "-m",
         f"augment: add POS/plural/verb pairs from domain dictionary ({datetime.now().strftime('%Y-%m-%d')})"],
        ["git", "push", "origin", "main"],
        ["git", "push", "k227", "main"],
    ]
    for cmd in git_cmds:
        result = subprocess.run(cmd, cwd=BASE.parent)
        if result.returncode != 0 and "nothing to commit" not in str(result.stdout):
            print(f"[WARN] git command failed: {' '.join(cmd)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Augment data + full training pipeline")
    parser.add_argument("--augment-only",  action="store_true", help="Only generate + clean data, skip training")
    parser.add_argument("--train-only",    action="store_true", help="Skip augmentation, just train")
    parser.add_argument("--no-push",       action="store_true", help="Skip all pushes")
    parser.add_argument("--epochs",        type=int, default=3)
    parser.add_argument("--direction",     type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--marian-only",   action="store_true")
    parser.add_argument("--nllb-only",     action="store_true")
    parser.add_argument("--batch-marian",  type=int, default=64)
    parser.add_argument("--batch-nllb",    type=int, default=8)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  AUGMENT + TRAIN PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── Step 1–3: Augment ─────────────────────────────────────────────────────
    if not args.train_only:
        print("\n[STEP 1] Generating augmented pairs from dictionary POS data...")
        raw_pairs = generate_augmented_pairs()

        print("\n[STEP 2] Cleaning generated pairs...")
        clean = clean_pairs(raw_pairs)

        print("\n[STEP 3] Merging into training data...")
        n_train, n_val = merge_into_training(clean)

        if args.augment_only:
            print(f"\n[DONE] Augmentation complete. Added {n_train+n_val:,} new pairs.")
            print(f"  Run with --train-only to train on the new data.")
            return

    # ── Step 4–5: Train ───────────────────────────────────────────────────────
    print("\n[STEP 4-5] Training models...")
    failed = train_models(args)

    # ── Step 6–8: Push ────────────────────────────────────────────────────────
    if not args.no_push:
        print("\n[STEP 6-8] Pushing to HuggingFace + GitHub...")
        push_all(args, failed)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    if failed:
        print(f"  Failed steps: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("  All steps completed successfully.")


if __name__ == "__main__":
    main()
