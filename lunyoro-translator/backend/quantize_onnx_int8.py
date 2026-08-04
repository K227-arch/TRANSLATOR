"""
quantize_onnx_int8.py
=====================
Quantize ONNX FP32 models to INT8 for faster CPU inference.
Uses onnxruntime's dynamic quantization (no calibration data needed).

Dynamic INT8 quantization:
  - Quantizes weights to INT8 at export time
  - Quantizes activations dynamically at runtime
  - No calibration dataset needed
  - ~2x speedup on modern CPUs with VNNI instructions
  - ~2x smaller model files
  - Minimal quality loss (typically < 1 BLEU point)

Usage:
    python quantize_onnx_int8.py

Output: model/nllb_en2lun_int8/ and model/nllb_lun2en_int8/
"""
import os
import shutil
from pathlib import Path

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"


def quantize_model(src_dir: Path, out_dir: Path, label: str):
    print(f"\n{'='*60}")
    print(f"Quantizing {label} to INT8")
    print(f"  Source : {src_dir}")
    print(f"  Output : {out_dir}")
    print(f"{'='*60}")

    if not src_dir.exists():
        print(f"  ERROR: Source ONNX dir not found — {src_dir}")
        print(f"  Run export_nllb_onnx.py first.")
        return False

    onnx_files = list(src_dir.glob("*.onnx"))
    if not onnx_files:
        print(f"  ERROR: No .onnx files in {src_dir}")
        return False

    # Create output dir — copy tokenizer/config files from source
    if out_dir.exists():
        print(f"  Removing old INT8 dir: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Copy all non-ONNX files (tokenizer, config, etc.)
    for f in src_dir.iterdir():
        if f.is_file() and not f.name.endswith(".onnx") and not f.name.endswith(".onnx_data"):
            shutil.copy2(f, out_dir / f.name)
    print(f"  Copied tokenizer/config files")

    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        import onnx

        for onnx_file in onnx_files:
            out_file = out_dir / onnx_file.name
            print(f"  Quantizing {onnx_file.name} ...")

            quantize_dynamic(
                model_input=str(onnx_file),
                model_output=str(out_file),
                weight_type=QuantType.QInt8,
                # Quantize all MatMul and Gemm ops — the compute-heavy ops
                per_channel=False,   # per-tensor is faster on most CPUs
                reduce_range=False,  # set True on older CPUs without AVX512
            )

            orig_mb = onnx_file.stat().st_size / 1e6
            # Also check .onnx_data file if it exists
            data_file = onnx_file.with_suffix(".onnx_data")
            if data_file.exists():
                orig_mb += data_file.stat().st_size / 1e6

            new_mb = out_file.stat().st_size / 1e6
            out_data = out_file.with_suffix(".onnx_data")
            if out_data.exists():
                new_mb += out_data.stat().st_size / 1e6

            ratio = orig_mb / new_mb if new_mb > 0 else 0
            print(f"    {onnx_file.name}: {orig_mb:.0f}MB → {new_mb:.0f}MB ({ratio:.1f}x smaller)")

        print(f"  ✅ INT8 quantization complete: {out_dir}")
        return True

    except ImportError:
        print("  ERROR: onnxruntime.quantization not available")
        print("  Run: pip install onnxruntime")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def smoke_test_int8(out_dir: Path, direction: str):
    """Quick smoke test — load INT8 model and run one translation."""
    print(f"\n  Smoke testing INT8 {direction}...")
    try:
        from optimum.onnxruntime import ORTModelForSeq2SeqLM
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(out_dir))
        model = ORTModelForSeq2SeqLM.from_pretrained(
            str(out_dir),
            provider="CPUExecutionProvider",
            decoder_file_name="decoder_model.onnx",
            use_cache=False,
        )
        src_lang = "eng_Latn" if "en2lun" in direction else "run_Latn"
        tgt_lang = "run_Latn" if "en2lun" in direction else "eng_Latn"
        tokenizer.src_lang = src_lang
        test_text = "Hello world" if "en2lun" in direction else "ningenda omu isoko"
        inputs = tokenizer(test_text, return_tensors="pt")
        forced_bos = tokenizer.convert_tokens_to_ids(tgt_lang)
        out = model.generate(**inputs, forced_bos_token_id=forced_bos, max_length=50)
        result = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"  ✅ '{test_text}' → '{result}'")
        return True
    except Exception as e:
        print(f"  ⚠️  Smoke test failed: {e}")
        return False


if __name__ == "__main__":
    results = {}

    for direction in ["en2lun", "lun2en"]:
        src = MODEL_DIR / f"nllb_{direction}_onnx"
        out = MODEL_DIR / f"nllb_{direction}_int8"
        ok = quantize_model(src, out, f"nllb_{direction}")
        if ok:
            smoke_test_int8(out, direction)
        results[direction] = ok

    print(f"\n{'='*60}")
    print("QUANTIZATION SUMMARY")
    for k, v in results.items():
        print(f"  nllb_{k}: {'✅ done' if v else '❌ failed'}")
    print(f"{'='*60}")
    print("""
Next steps:
  1. Update translate.py to check for nllb_*_int8 dirs first
  2. Restart backend: python -m uvicorn main:app --host 0.0.0.0 --port 8000
  3. Run benchmark_onnx.py to compare speed
""")
