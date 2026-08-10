"""
export_marian_tokenizer.py
==========================
Emits the SentencePiece Unigram data the Raspberry Pi C++ backend needs to
tokenize for MarianMT.

Why this exists: the C++ Tokenizer does BPE merges driven by an NLLB-style
tokenizer.json. Marian is a Unigram model with no merges at all, so that code
path segments Marian input character-by-character and produces garbage. The C++
therefore needs a Viterbi Unigram encoder, which needs (piece, log_prob) pairs —
and those live inside the .spm protobuf, which is impractical to parse in C++
without linking libsentencepiece (not installed on the Pi).

So we pre-extract them here into plain JSON:

  model/<direction>_onnx/unigram_source.json
      { "pieces": [[piece, score], ...],   # for Viterbi segmentation
        "vocab":  { piece: id, ... },      # piece -> token id (shared vocab)
        "unk_id": int, "eos_id": int, "pad_id": int,
        "decoder_start_token_id": int }

Usage:
    python export_marian_tokenizer.py
    python export_marian_tokenizer.py --direction en2lun
"""

import argparse
import json
from pathlib import Path

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

DIRECTIONS = ["en2lun", "lun2en"]


def export(direction: str) -> bool:
    src = MODEL_DIR / direction
    onnx_dir = MODEL_DIR / f"{direction}_onnx"

    spm_path = src / "source.spm"
    vocab_path = src / "vocab.json"
    config_path = src / "config.json"

    if not spm_path.is_file() or not vocab_path.is_file():
        print(f"  [SKIP] {direction}: missing source.spm or vocab.json")
        return False

    import sentencepiece as spm

    sp = spm.SentencePieceProcessor()
    sp.Load(str(spm_path))

    pieces = [[sp.IdToPiece(i), sp.GetScore(i)] for i in range(sp.GetPieceSize())]

    with open(vocab_path, encoding="utf-8") as f:
        vocab = json.load(f)

    cfg = {}
    if config_path.is_file():
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)

    out = {
        "pieces": pieces,
        "vocab": vocab,
        "unk_id": vocab.get("<unk>", 1),
        "eos_id": cfg.get("eos_token_id", 0),
        "pad_id": cfg.get("pad_token_id", 64109),
        "decoder_start_token_id": cfg.get("decoder_start_token_id", cfg.get("pad_token_id", 64109)),
    }

    onnx_dir.mkdir(parents=True, exist_ok=True)
    dest = onnx_dir / "unigram_source.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    size_mb = dest.stat().st_size / 1e6
    print(
        f"  [OK] {direction}: {len(pieces):,} pieces, {len(vocab):,} vocab entries, "
        f"start={out['decoder_start_token_id']} eos={out['eos_id']} -> {dest.name} ({size_mb:.1f}MB)"
    )
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", help="Export a single direction only")
    args = ap.parse_args()

    directions = [args.direction] if args.direction else DIRECTIONS
    print("=== Marian Unigram tokenizer export ===")
    for d in directions:
        export(d)
    print("\nDone.")
