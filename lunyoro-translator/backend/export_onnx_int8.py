"""
export_onnx_int8.py
===================
INT8 dynamic quantization of the ONNX graphs produced by export_onnx_all.py,
for the Raspberry Pi C++ backend.

Only NLLB needs this. Unquantized NLLB is ~6.8 GB per direction, which cannot
load on the Pi's 8 GB of RAM; quantized it lands around 1.9 GB per direction,
matching what already runs there. MarianMT stays fp32 — at 886 MB per direction
it fits comfortably and keeps full precision.

Output file names match what the Pi's translator loads:
  model/<direction>_pi/encoder_model_quantized.onnx
  model/<direction>_pi/decoder_model_quantized.onnx
  + sentencepiece / vocab / config sidecars

The Pi decoder runs greedy with no KV cache, so decoder_with_past_model.onnx is
deliberately not quantized or shipped.

Usage:
    python export_onnx_int8.py --direction nllb_en2lun
    python export_onnx_int8.py                    # both NLLB directions
    python export_onnx_int8.py --prune-fp32       # delete the fp32 source after each
"""

import argparse
import shutil
import time
from pathlib import Path

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

NLLB_DIRECTIONS = ["nllb_en2lun", "nllb_lun2en"]

# The Pi loads exactly these two graphs per direction.
GRAPHS = {
    "encoder_model.onnx": "encoder_model_quantized.onnx",
    "decoder_model.onnx": "decoder_model_quantized.onnx",
}

SIDECAR_FILES = [
    "sentencepiece.bpe.model",
    "source.spm",
    "target.spm",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "config.json",
    "generation_config.json",
]


def dir_size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def quantize_direction(direction: str, prune_fp32: bool = False) -> Path | None:
    from onnxruntime.quantization import QuantType, quantize_dynamic

    src = MODEL_DIR / f"{direction}_onnx"
    dst = MODEL_DIR / f"{direction}_pi"

    if not src.is_dir():
        print(f"  [SKIP] no fp32 export at {src} — run export_onnx_all.py first")
        return None

    dst.mkdir(parents=True, exist_ok=True)

    for src_name, dst_name in GRAPHS.items():
        graph = src / src_name
        out = dst / dst_name
        if not graph.is_file():
            print(f"  [WARN] missing {src_name}")
            continue
        if out.exists():
            print(f"    [OK] {dst_name} already quantized")
            continue

        print(f"    Quantizing {src_name} -> {dst_name} ...", flush=True)
        t0 = time.time()
        quantize_dynamic(
            model_input=str(graph),
            model_output=str(out),
            weight_type=QuantType.QInt8,
            # Weights only; activations stay float so the greedy loop keeps its accuracy.
            extra_options={"MatMulConstBOnly": True},
            # NLLB decoder weights live in a sibling .onnx_data file (>2GB limit).
            use_external_data_format=True,
        )
        after = out.stat().st_size / 1e6
        extra = dst / f"{dst_name}_data"
        if extra.exists():
            after += extra.stat().st_size / 1e6
        print(f"    [OK] {dst_name}: {after:.0f}MB in {time.time() - t0:.1f}s", flush=True)

    # Tokenizer + config travel with the model.
    plain = MODEL_DIR / direction
    for name in SIDECAR_FILES:
        for candidate in (src / name, plain / name):
            if candidate.is_file():
                shutil.copy2(candidate, dst / name)
                break

    print(f"  [OK] {dst.name}: {dir_size_mb(dst):.0f}MB total", flush=True)

    if prune_fp32:
        freed = dir_size_mb(src)
        shutil.rmtree(src)
        print(f"  [CLEAN] removed {src.name}, freed {freed / 1000:.1f}GB", flush=True)

    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", help="Quantize a single direction only")
    ap.add_argument(
        "--prune-fp32",
        action="store_true",
        help="Delete the fp32 ONNX export once quantized (frees ~6.8GB per direction)",
    )
    args = ap.parse_args()

    directions = [args.direction] if args.direction else NLLB_DIRECTIONS

    print(f"=== INT8 quantization: {', '.join(directions)} ===")
    for d in directions:
        print(f"\n[{d}]")
        quantize_direction(d, prune_fp32=args.prune_fp32)

    print("\nDone.")
