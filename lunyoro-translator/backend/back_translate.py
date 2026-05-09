"""
back_translate.py
=================
Back-translation data augmentation:
  1. Takes English monolingual sentences (from existing corpus English side)
  2. Translates them to Lunyoro using the current en2lun model
  3. Then translates those back to English using lun2en (round-trip filter)
  4. Keeps pairs where round-trip BLEU >= threshold (quality filter)
  5. Writes synthetic pairs to data/training/back_translated.csv

These synthetic pairs can then be merged into train.csv for retraining.

Usage:
    python back_translate.py [--max 5000] [--bleu-threshold 0.3] [--batch 32]
"""
import os
import sys
import re
import argparse
import pandas as pd
import torch
from transformers import MarianMTModel, MarianTokenizer
from sacrebleu.metrics import BLEU

BASE      = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "model")
DATA_DIR  = os.path.join(BASE, "data", "training")

# ── Load models ───────────────────────────────────────────────────────────────

def load_model(direction: str):
    path = os.path.join(MODEL_DIR, direction)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Model not found: {path}. Run download_models.py first.")
    print(f"  Loading {direction}...")
    tokenizer = MarianTokenizer.from_pretrained(path)
    model     = MarianMTModel.from_pretrained(path)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return tokenizer, model, device


def translate_batch(texts: list[str], tokenizer, model, device: str,
                    num_beams: int = 4, max_length: int = 256) -> list[str]:
    """Translate a batch of texts."""
    inputs = tokenizer(
        texts, return_tensors="pt", padding=True,
        truncation=True, max_length=256
    ).to(device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            num_beams=num_beams,
            max_length=max_length,
            early_stopping=True,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2,
        )
    results = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
    # Strip domain tags the model may reproduce
    results = [re.sub(r'^\s*\[[A-Za-z _]+\]\s*', '', r).strip() for r in results]
    return results


def sentence_bleu(hypothesis: str, reference: str) -> float:
    """Compute sentence-level BLEU (0-1 scale)."""
    bleu = BLEU(effective_order=True)
    score = bleu.sentence_score(hypothesis, [reference])
    return score.score / 100.0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",          type=str,
                        default=os.path.join(DATA_DIR, "train.csv"),
                        help="Input CSV with english/lunyoro columns")
    parser.add_argument("--max",            type=int,   default=5000,
                        help="Max English sentences to back-translate")
    parser.add_argument("--bleu-threshold", type=float, default=0.25,
                        help="Min round-trip BLEU to keep a pair (0-1)")
    parser.add_argument("--batch",          type=int,   default=16,
                        help="Batch size for translation")
    parser.add_argument("--output",         type=str,
                        default=os.path.join(DATA_DIR, "back_translated.csv"),
                        help="Output CSV path")
    args = parser.parse_args()

    print("=== Back-Translation Data Augmentation ===\n")

    # Load source sentences from input CSV
    print(f"Loading from: {args.input}")
    df = pd.read_csv(args.input)

    # Use English side — deduplicate, filter short/long
    english_sentences = (
        df['english']
        .dropna()
        .drop_duplicates()
        .apply(lambda x: re.sub(r'\[[A-Za-z _]+\]\s*', '', str(x)).strip())
        .pipe(lambda s: s[s.str.len().between(10, 200)])
        .sample(frac=1, random_state=42)  # shuffle
        .head(args.max)
        .tolist()
    )
    print(f"Source sentences: {len(english_sentences):,}")

    # Load models
    print("\nLoading models...")
    en2lun_tok, en2lun_model, device = load_model("en2lun")
    lun2en_tok, lun2en_model, _      = load_model("lun2en")
    print(f"  Device: {device}\n")

    # Translate in batches
    batch_size = args.batch
    synthetic_pairs = []
    kept = dropped = 0

    print(f"Translating {len(english_sentences):,} sentences (batch={batch_size})...")
    for i in range(0, len(english_sentences), batch_size):
        batch_en = english_sentences[i:i + batch_size]

        # en → lun
        batch_lun = translate_batch(batch_en, en2lun_tok, en2lun_model, device)

        # lun → en (round-trip)
        batch_en_back = translate_batch(batch_lun, lun2en_tok, lun2en_model, device)

        for orig_en, lun, back_en in zip(batch_en, batch_lun, batch_en_back):
            if not lun or not back_en:
                dropped += 1
                continue
            # Quality filter: round-trip BLEU
            score = sentence_bleu(back_en, orig_en)
            if score >= args.bleu_threshold:
                synthetic_pairs.append({
                    "english": orig_en,
                    "lunyoro": lun,
                    "round_trip_bleu": round(score, 4),
                    "source": "back_translation",
                })
                kept += 1
            else:
                dropped += 1

        if (i // batch_size + 1) % 10 == 0:
            print(f"  [{i + batch_size:,}/{len(english_sentences):,}] "
                  f"kept={kept:,} dropped={dropped:,}")

    print(f"\nResults: kept={kept:,}  dropped={dropped:,}")

    if not synthetic_pairs:
        print("No pairs passed the quality filter. Try lowering --bleu-threshold.")
        return

    out_df = pd.DataFrame(synthetic_pairs)
    out_df = out_df.drop_duplicates(subset=['english', 'lunyoro'])
    out_df.to_csv(args.output, index=False, encoding='utf-8')
    print(f"Saved {len(out_df):,} synthetic pairs → {args.output}")

    # Optionally merge into train.csv
    print("\nTo merge into train.csv, run:")
    print(f"  python merge_back_translated.py --input {args.output}")


if __name__ == "__main__":
    main()
