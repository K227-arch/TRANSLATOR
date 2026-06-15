"""
export_to_onnx.py
=================
Exports MarianMT models to ONNX format for faster CPU/GPU inference.

ONNX benefits for this project:
  - 2-5x faster inference vs PyTorch (especially CPU)
  - Lower memory footprint
  - Works on HF Space CPU tier without OOM

Only MarianMT is exported (en2lun + lun2en).
NLLB is too large and the autoregressive loop bottleneck means less benefit.

Output:
  model/en2lun_onnx/   -- ONNX version of en2lun
  model/lun2en_onnx/   -- ONNX version of lun2en

Usage:
    python export_to_onnx.py
    python export_to_onnx.py --direction en2lun   # one direction only
    python export_to_onnx.py --verify              # export + test inference
"""

import argparse
import time
from pathlib import Path

BASE      = Path(__file__).parent
MODEL_DIR = BASE / "model"


def export_direction(direction: str, verify: bool = False):
    from optimum.onnxruntime import ORTModelForSeq2SeqLM
    from transformers import MarianTokenizer

    src_path  = MODEL_DIR / direction
    onnx_path = MODEL_DIR / f"{direction}_onnx"

    if not src_path.is_dir():
        print(f"  Source model not found: {src_path}")
        return False

    print(f"\n  Exporting {direction} -> {onnx_path.name}...")
    t0 = time.time()

    try:
        # Export using optimum — handles the encoder/decoder split automatically
        model = ORTModelForSeq2SeqLM.from_pretrained(
            str(src_path),
            export=True,
            provider="CPUExecutionProvider",  # CPU is safe; GPU needs onnxruntime-gpu with CUDA
        )
        model.save_pretrained(str(onnx_path))

        # Copy tokenizer
        import shutil
        for f in src_path.iterdir():
            if f.suffix in (".json", ".spm", ".model", ".txt") and f.is_file():
                shutil.copy2(str(f), str(onnx_path / f.name))

        elapsed = time.time() - t0
        print(f"  Exported in {elapsed:.1f}s -> {onnx_path}")

        # Check sizes
        total_mb = sum(f.stat().st_size for f in onnx_path.rglob("*") if f.is_file()) / 1e6
        print(f"  ONNX model size: {total_mb:.1f} MB")

    except Exception as e:
        print(f"  Export failed: {e}")
        return False

    if verify:
        _verify_onnx(direction, onnx_path)

    return True


def _verify_onnx(direction: str, onnx_path: Path):
    """Compare PyTorch vs ONNX output and speed."""
    from optimum.onnxruntime import ORTModelForSeq2SeqLM
    from transformers import MarianTokenizer, MarianMTModel
    import torch
    import time

    test_sentences = {
        "en2lun": ["I love my family", "The child is going to school", "God is good"],
        "lun2en": ["Ningonza eka yange", "Omwana agenda omusomero", "Ruhanga murungi"],
    }
    tests = test_sentences.get(direction, [])

    print(f"\n  Verifying {direction} ONNX vs PyTorch...")
    src_path = MODEL_DIR / direction

    # Load tokenizer
    tokenizer = MarianTokenizer.from_pretrained(str(src_path))

    # Load ONNX model
    ort_model = ORTModelForSeq2SeqLM.from_pretrained(
        str(onnx_path),
        provider="CPUExecutionProvider",
    )

    # Load PyTorch model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pt_model = MarianMTModel.from_pretrained(str(src_path)).eval().to(device)

    print(f"  {'Input':<35} {'PyTorch':<35} {'ONNX':<35}")
    print(f"  {'-'*35} {'-'*35} {'-'*35}")

    for text in tests:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)

        # PyTorch
        t0 = time.time()
        with torch.no_grad():
            pt_out = pt_model.generate(**inputs.to(device), num_beams=4, max_length=256)
        pt_time = (time.time() - t0) * 1000
        pt_text = tokenizer.decode(pt_out[0], skip_special_tokens=True)

        # ONNX
        t0 = time.time()
        ort_out = ort_model.generate(**inputs, num_beams=4, max_length=256)
        ort_time = (time.time() - t0) * 1000
        ort_text = tokenizer.decode(ort_out[0], skip_special_tokens=True)

        print(f"  {text[:33]:<35} {pt_text[:33]:<35} {ort_text[:33]:<35}")
        print(f"  {'':35} {pt_time:>5.0f}ms{'':<27} {ort_time:>5.0f}ms")

    # Speedup
    print(f"\n  ONNX speedup: {pt_time/max(ort_time,1):.1f}x faster than PyTorch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--verify",   action="store_true",
                        help="Test ONNX inference after export")
    args = parser.parse_args()

    print("="*60)
    print("  ONNX EXPORT PIPELINE")
    print("  Exporting MarianMT models to ONNX format")
    print("="*60)

    directions = ["en2lun", "lun2en"] if args.direction == "both" else [args.direction]
    for direction in directions:
        export_direction(direction, verify=args.verify)

    print("\nDone. ONNX models saved to model/en2lun_onnx/ and model/lun2en_onnx/")
    print("Update translate.py to use ORTModelForSeq2SeqLM for faster inference.")


if __name__ == "__main__":
    main()
