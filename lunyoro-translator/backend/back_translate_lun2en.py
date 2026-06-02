"""
back_translate_lun2en.py
========================
Fix 3: Back-translation to improve lun2en training data.

Strategy:
  1. Take English sentences from existing cleaned data that have NO Runyoro pair
     (or whose Runyoro pair is a single word / dict entry)
  2. Use the best en2lun model (NLLB en2lun, BLEU=73.97) to translate them
     to Runyoro — this generates synthetic Runyoro source sentences
  3. The original English becomes the reference translation
  4. Filter: only keep back-translations where the Runyoro output is >= 5 words
     (ensures sentence-level quality, not word-level noise)
  5. Save to data/cleaned/back_translated_lun2en.csv
  6. Merge into train.csv / val.csv

This effectively doubles the sentence-level lun2en training data using the
en2lun model as a teacher.

Usage:
    python back_translate_lun2en.py                    # default 10k sentences
    python back_translate_lun2en.py --max-sentences 20000
    python back_translate_lun2en.py --batch-size 32
    python back_translate_lun2en.py --merge             # also merge into train/val
"""

import argparse
import os
import re
import csv
import unicodedata
import pandas as pd
import torch
from pathlib import Path
from datetime import datetime

BASE      = Path(__file__).parent
DATA_DIR  = BASE / "data"
CLEAN_DIR = DATA_DIR / "cleaned"
TRAIN_DIR = DATA_DIR / "training"
MODEL_DIR = BASE / "model"

OUT_CSV   = CLEAN_DIR / "back_translated_lun2en.csv"
TRAIN_CSV = TRAIN_DIR / "train.csv"
VAL_CSV   = TRAIN_DIR / "val.csv"


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text.strip())


def strip_domain_tag(text: str) -> str:
    return re.sub(r'^\[[A-Za-z0-9_ ]+\]\s*', '', text).strip()


def load_english_sentences(max_sentences: int) -> list[str]:
    """
    Collect English sentences for back-translation.

    Priority order:
      1. Tagged pairs [DOMAIN_TAG] english -> lunyoro
         The lun2en model NEVER saw these as source (they were en2lun-only format).
         Strip the tag and use the clean English — this is the highest-value source.
      2. Short dict pairs (lun_words <= 2) with en_words >= 5
         The lun2en model filtered these out — their English is valid sentence-level.
      3. External cleaned sources not yet in training

    Deduplicates against already back-translated pairs.
    """
    seen: set[str] = set()
    sentences: list[str] = []

    # Load already back-translated to avoid re-doing them
    already_bt: set[str] = set()
    if OUT_CSV.exists():
        try:
            bt_df = pd.read_csv(OUT_CSV)
            already_bt = set(bt_df["english"].astype(str).str.lower().str.strip())
            print(f"  Already back-translated: {len(already_bt):,} (will skip)")
        except Exception:
            pass

    # Load full training data
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)
    both  = pd.concat([train, val])

    both["lun_words"] = both["lunyoro"].astype(str).str.split().str.len()
    both["has_tag"]   = both["english"].astype(str).str.match(r"^\[")
    both["en_clean"]  = both["english"].astype(str).str.replace(
        r"^\[[A-Za-z0-9_ ]+\]\s*", "", regex=True).str.strip()
    both["en_words"]  = both["en_clean"].str.split().str.len()

    # ── Priority 0: Use pre-computed remaining candidates file if available ──
    BT_REMAINING = CLEAN_DIR / "bt_remaining_candidates.csv"
    if BT_REMAINING.exists():
        try:
            remaining_df = pd.read_csv(BT_REMAINING)
            print(f"  Using pre-computed remaining candidates: {len(remaining_df):,}")
            for en in remaining_df["english"].astype(str):
                en = normalise(strip_domain_tag(en))
                en_lower = en.lower()
                if (len(en.split()) >= 5
                        and en_lower not in seen
                        and en_lower not in already_bt):
                    seen.add(en_lower)
                    sentences.append(en)
                    if len(sentences) >= max_sentences:
                        break
            if sentences:
                print(f"  Collected {len(sentences):,} from remaining candidates file")
                return sentences[:max_sentences]
        except Exception as e:
            print(f"  Could not read remaining candidates: {e}")

    # ── Priority 1: Tagged pairs (en2lun-only, lun2en never saw as source) ───
    tagged = both[both["has_tag"] & (both["en_words"] >= 5)]
    print(f"  Tagged pairs with en_words>=5: {len(tagged):,}")
    for en_clean in tagged["en_clean"].astype(str):
        en = normalise(en_clean)
        en_lower = en.lower()
        if (en_lower not in seen
                and en_lower not in already_bt
                and len(en.split()) >= 5):
            seen.add(en_lower)
            sentences.append(en)
            if len(sentences) >= max_sentences:
                break

    # ── Priority 2: Short dict pairs with long English ────────────────────────
    if len(sentences) < max_sentences:
        short = both[~both["has_tag"] & (both["lun_words"] <= 2) & (both["en_words"] >= 5)]
        print(f"  Short dict pairs with en_words>=5: {len(short):,}")
        for en in short["english"].astype(str):
            en = normalise(strip_domain_tag(en))
            en_lower = en.lower()
            if (en_lower not in seen
                    and en_lower not in already_bt
                    and len(en.split()) >= 5):
                seen.add(en_lower)
                sentences.append(en)
                if len(sentences) >= max_sentences:
                    break

    # ── Priority 3: External cleaned sources ─────────────────────────────────
    if len(sentences) < max_sentences:
        SOURCES = [
            CLEAN_DIR / "runyoro_english_sentences_clean.csv",
            CLEAN_DIR / "english_nyoro_clean.csv",
            CLEAN_DIR / "ocr_pairs_extracted.csv",
            CLEAN_DIR / "proverbs_pairs_clean.csv",
            CLEAN_DIR / "idioms_pairs.csv",
        ]
        existing_en = set(both["en_clean"].astype(str).str.lower().str.strip())
        for src in SOURCES:
            if not src.exists():
                continue
            try:
                df = pd.read_csv(src)
                if "english" not in df.columns:
                    continue
                for en in df["english"].astype(str):
                    en = normalise(strip_domain_tag(en))
                    en_lower = en.lower()
                    if (len(en.split()) >= 5
                            and en_lower not in seen
                            and en_lower not in already_bt
                            and en_lower not in existing_en):
                        seen.add(en_lower)
                        sentences.append(en)
                        if len(sentences) >= max_sentences:
                            break
            except Exception as e:
                print(f"  SKIP {src.name}: {e}")
            if len(sentences) >= max_sentences:
                break

    print(f"  Collected {len(sentences):,} English sentences for back-translation")
    return sentences[:max_sentences]


def back_translate_batch(sentences: list[str], batch_size: int,
                          model, tokenizer, device: str) -> list[str]:
    """Translate English sentences to Runyoro using NLLB en2lun."""
    from transformers import NllbTokenizer
    results = []
    total = len(sentences)

    for i in range(0, total, batch_size):
        batch = sentences[i:i + batch_size]
        tokenizer.src_lang = "eng_Latn"
        inputs = tokenizer(batch, return_tensors="pt", padding=True,
                           truncation=True, max_length=256).to(device)
        forced_bos = tokenizer.convert_tokens_to_ids("nyn_Latn")
        with torch.no_grad():
            out = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos,
                num_beams=4,
                max_length=256,
                early_stopping=True,
                no_repeat_ngram_size=3,
                length_penalty=1.2,
            )
        decoded = tokenizer.batch_decode(out, skip_special_tokens=True)
        results.extend(decoded)

        done = min(i + batch_size, total)
        if (i // batch_size) % 10 == 0:
            print(f"  Back-translated {done:,}/{total:,} sentences...")

    return results


def filter_back_translations(english: list[str],
                              runyoro: list[str],
                              min_lun_words: int = 5) -> list[tuple[str, str]]:
    """
    Keep only high-quality back-translations:
    - Runyoro output >= min_lun_words words
    - Not identical to English input (passthrough rejection)
    - No obvious English words in Runyoro output (>30% common English = reject)
    """
    COMMON_EN = {"the","a","an","is","are","was","were","have","has","do","does",
                 "will","would","can","could","should","to","of","in","on","at",
                 "for","with","and","or","but","not","this","that","it","he",
                 "she","they","we","you","i","my","your","his","her","their"}

    kept = []
    rejected = {"too_short": 0, "passthrough": 0, "english_output": 0}

    for en, lun in zip(english, runyoro):
        lun = normalise(lun)
        lun_words = lun.split()

        if len(lun_words) < min_lun_words:
            rejected["too_short"] += 1
            continue

        if lun.lower().strip() == en.lower().strip():
            rejected["passthrough"] += 1
            continue

        # Reject if >30% of Runyoro output words are common English
        en_ratio = sum(1 for w in re.findall(r'[a-z]+', lun.lower())
                       if w in COMMON_EN) / max(len(lun_words), 1)
        if en_ratio > 0.3:
            rejected["english_output"] += 1
            continue

        kept.append((en, lun))

    print(f"  Kept: {len(kept):,}  Rejected: {rejected}")
    return kept


def merge_into_training(pairs: list[tuple[str, str]]) -> tuple[int, int]:
    """Merge back-translated pairs into train.csv / val.csv (90/10 split)."""
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)

    existing_keys = set(zip(
        pd.concat([train, val])["english"].str.lower().str.strip(),
        pd.concat([train, val])["lunyoro"].str.lower().str.strip(),
    ))

    new_pairs = [(en, lun) for en, lun in pairs
                 if (en.lower(), lun.lower()) not in existing_keys]

    if not new_pairs:
        print("  No new pairs to add (all already in training data)")
        return 0, 0

    split = int(len(new_pairs) * 0.9)
    new_train = new_pairs[:split]
    new_val   = new_pairs[split:]

    # Backup
    import shutil
    shutil.copy(TRAIN_CSV, str(TRAIN_CSV) + ".bak_bt")
    shutil.copy(VAL_CSV,   str(VAL_CSV)   + ".bak_bt")

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
        description="Back-translate English sentences to Runyoro for lun2en training"
    )
    parser.add_argument("--max-sentences", type=int, default=10000,
                        help="Max English sentences to back-translate (default: 10000)")
    parser.add_argument("--batch-size",    type=int, default=16,
                        help="Batch size for NLLB inference (default: 16)")
    parser.add_argument("--min-lun-words", type=int, default=5,
                        help="Min Runyoro words to keep a back-translation (default: 5)")
    parser.add_argument("--merge",         action="store_true",
                        help="Merge results into train.csv / val.csv after generation")
    parser.add_argument("--model",         type=str, default="nllb",
                        choices=["nllb", "marian"],
                        help="Which en2lun model to use for back-translation (default: nllb)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  BACK-TRANSLATION PIPELINE (Fix 3)")
    print(f"  Model: {args.model}_en2lun  |  Max sentences: {args.max_sentences:,}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── Step 1: Collect English sentences ────────────────────────────────────
    print("[Step 1] Collecting English sentences...")
    english_sentences = load_english_sentences(args.max_sentences)
    if not english_sentences:
        print("No sentences found. Check data/cleaned/ directory.")
        return

    # ── Step 2: Load en2lun model ─────────────────────────────────────────────
    print(f"\n[Step 2] Loading {args.model}_en2lun model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device}")

    if args.model == "nllb":
        from transformers import NllbTokenizer, AutoModelForSeq2SeqLM
        model_path = str(MODEL_DIR / "nllb_en2lun")
        tokenizer = NllbTokenizer.from_pretrained(model_path)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path).eval().to(device)
    else:
        from transformers import MarianMTModel, MarianTokenizer
        model_path = str(MODEL_DIR / "en2lun")
        tokenizer = MarianTokenizer.from_pretrained(model_path)
        model = MarianMTModel.from_pretrained(model_path).eval().to(device)

    print(f"  Loaded from: {model_path}")

    # ── Step 3: Back-translate ────────────────────────────────────────────────
    print(f"\n[Step 3] Back-translating {len(english_sentences):,} sentences...")
    if args.model == "nllb":
        runyoro_sentences = back_translate_batch(
            english_sentences, args.batch_size, model, tokenizer, device
        )
    else:
        # MarianMT batch translation
        runyoro_sentences = []
        for i in range(0, len(english_sentences), args.batch_size):
            batch = english_sentences[i:i + args.batch_size]
            inputs = tokenizer(batch, return_tensors="pt", padding=True,
                               truncation=True, max_length=256).to(device)
            with torch.no_grad():
                out = model.generate(**inputs, num_beams=4, max_length=256,
                                     early_stopping=True, length_penalty=1.2)
            decoded = tokenizer.batch_decode(out, skip_special_tokens=True)
            runyoro_sentences.extend(decoded)
            if (i // args.batch_size) % 10 == 0:
                done = min(i + args.batch_size, len(english_sentences))
                print(f"  Back-translated {done:,}/{len(english_sentences):,}...")

    # ── Step 4: Filter ────────────────────────────────────────────────────────
    print(f"\n[Step 4] Filtering back-translations...")
    kept_pairs = filter_back_translations(
        english_sentences, runyoro_sentences, args.min_lun_words
    )

    if not kept_pairs:
        print("No valid back-translations generated.")
        return

    # ── Step 5: Save ──────────────────────────────────────────────────────────
    print(f"\n[Step 5] Saving {len(kept_pairs):,} back-translated pairs...")
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    # Append to existing file if it exists, otherwise create new
    file_exists = OUT_CSV.exists()
    with open(OUT_CSV, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["english", "lunyoro"])
        for en, lun in kept_pairs:
            w.writerow([en, lun])
    total_bt = sum(1 for _ in open(OUT_CSV, encoding="utf-8")) - 1  # subtract header
    print(f"  Appended to: {OUT_CSV}  (total back-translated: {total_bt:,})")

    # ── Step 6: Merge (optional) ──────────────────────────────────────────────
    if args.merge:
        print(f"\n[Step 6] Merging into train.csv / val.csv...")
        n_train, n_val = merge_into_training(kept_pairs)
        print(f"  Added {n_train:,} to train, {n_val:,} to val")
    else:
        print(f"\n  Run with --merge to add these pairs to training data.")
        print(f"  Or run: python merge_untrained_data.py")

    print(f"\n{'='*60}")
    print(f"  BACK-TRANSLATION COMPLETE")
    print(f"  Generated: {len(kept_pairs):,} lun2en sentence pairs")
    print(f"  Saved to:  {OUT_CSV.name}")
    print(f"  Finished:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"\nNext step: retrain lun2en models with the new data:")
    print(f"  python train_marian.py --direction lun2en --epochs 7 --min-lun-words 3")
    print(f"  python train_nllb.py   --direction lun2en --epochs 5 --min-lun-words 3")


if __name__ == "__main__":
    main()
