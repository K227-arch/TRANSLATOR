"""
export_onnx_all.py
==================
Exports every downloaded translation model to ONNX (fp32, no quantization) for
the C++/onnxruntime backend on the Raspberry Pi.

The repo's export_to_onnx.py only handles MarianMT; this covers NLLB too and
copies the tokenizer/config files the C++ runtime needs next to the graphs.

Output:
  model/<direction>_onnx/   -- encoder / decoder / decoder_with_past graphs
                               + sentencepiece models, vocab, configs

Usage:
    python export_onnx_all.py                    # all four directions
    python export_onnx_all.py --direction en2lun
    python export_onnx_all.py --marian-only
    python export_onnx_all.py --verify           # test translation after export
"""

import argparse
import shutil
import time
from pathlib import Path

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

MARIAN_DIRECTIONS = ["en2lun", "lun2en"]
NLLB_DIRECTIONS = ["nllb_en2lun", "nllb_lun2en"]

# Files the C++ runtime needs alongside the graphs: SentencePiece models for
# Marian (source/target.spm) and NLLB (sentencepiece.bpe.model), plus configs
# carrying the special-token ids and the forced BOS language token.
SIDECAR_FILES = [
    "source.spm",
    "target.spm",
    "sentencepiece.bpe.model",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "config.json",
    "generation_config.json",
]


def export(direction: str) -> Path | None:
    from optimum.onnxruntime import ORTModelForSeq2SeqLM

    src = MODEL_DIR / direction
    dst = MODEL_DIR / f"{direction}_onnx"

    if not src.is_dir():
        print(f"  [SKIP] source model not found: {src}")
        return None

    if any(dst.glob("*.onnx")):
        print(f"  [OK] {dst.name} already exported")
    else:
        print(f"  Exporting {direction} -> {dst.name} ...", flush=True)
        t0 = time.time()
        model = ORTModelForSeq2SeqLM.from_pretrained(str(src), export=True)
        model.save_pretrained(str(dst))
        total = sum(f.stat().st_size for f in dst.glob("*.onnx")) / 1e6
        print(f"  [OK] {dst.name}: {total:.0f}MB of graphs in {time.time() - t0:.1f}s", flush=True)

    for name in SIDECAR_FILES:
        f = src / name
        if f.is_file():
            shutil.copy2(f, dst / name)

    return dst


def verify(direction: str, onnx_dir: Path, text: str):
    from optimum.onnxruntime import ORTModelForSeq2SeqLM
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR / direction))
    model = ORTModelForSeq2SeqLM.from_pretrained(str(onnx_dir))
    t0 = time.time()
    ids = model.generate(**tok(text, return_tensors="pt"), max_new_tokens=64, num_beams=1)
    out = tok.batch_decode(ids, skip_special_tokens=True)[0]
    print(f"    [{direction}] {text!r} -> {out!r}  ({time.time() - t0:.2f}s)", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", help="Export a single direction only")
    ap.add_argument("--marian-only", action="store_true", help="Skip the NLLB directions")
    ap.add_argument("--verify", action="store_true", help="Run a test translation after export")
    args = ap.parse_args()

    if args.direction:
        directions = [args.direction]
    elif args.marian_only:
        directions = MARIAN_DIRECTIONS
    else:
        directions = MARIAN_DIRECTIONS + NLLB_DIRECTIONS

    print(f"=== ONNX export (fp32): {', '.join(directions)} ===")
    for d in directions:
        print(f"\n[{d}]")
        onnx_dir = export(d)
        if onnx_dir is not None and args.verify:
            probe = "Oli ota" if "lun2en" in d else "Good morning, my friend."
            verify(d, onnx_dir, probe)

    print("\nDone.")
