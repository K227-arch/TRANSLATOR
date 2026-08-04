"""
export_nllb_onnx.py
====================
Export the fine-tuned NLLB models to ONNX format for faster CPU inference.
Uses optimum's ONNX export which handles seq2seq models correctly.

Usage:
    python export_nllb_onnx.py

Output dirs:
    model/nllb_en2lun_onnx/   (replaces old export)
    model/nllb_lun2en_onnx/   (new)
"""
import os
import shutil
from pathlib import Path

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"


def export_model(src_dir: Path, out_dir: Path, label: str):
    print(f"\n{'='*60}")
    print(f"Exporting {label}")
    print(f"  Source : {src_dir}")
    print(f"  Output : {out_dir}")
    print(f"{'='*60}")

    if not src_dir.exists():
        print(f"  ERROR: Source not found — {src_dir}")
        return False

    # Check source has weights
    has_weights = any(f.suffix in (".safetensors", ".bin") for f in src_dir.iterdir())
    if not has_weights:
        print(f"  ERROR: No model weights in {src_dir}")
        return False

    # Clean old ONNX output if it exists
    if out_dir.exists():
        print(f"  Removing old ONNX dir: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    try:
        import subprocess, sys
        print(f"  Running optimum ONNX export via CLI (--no-post-process)...")
        cmd = [
            sys.executable, "-m", "optimum.exporters.onnx",
            "--model", str(src_dir),
            "--task", "text2text-generation-with-past",
            "--opset", "14",
            "--no-post-process",
            str(out_dir),
        ]
        print(f"  CMD: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"  ERROR: export exited with code {result.returncode}")
            return False
        onnx_files = list(out_dir.glob("*.onnx"))
        print(f"  ✅ Export complete. ONNX files: {[f.name for f in onnx_files]}")
        return True

    except ImportError:
        print("  ERROR: optimum not installed. Run: pip install optimum[onnxruntime]")
        return False
    except Exception as e:
        print(f"  ERROR during export: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_onnx(out_dir: Path, label: str):
    """Quick smoke test — load and run one inference."""
    print(f"\nVerifying {label} ONNX model...")
    try:
        from optimum.onnxruntime import ORTModelForSeq2SeqLM
        from transformers import AutoTokenizer
        import onnxruntime as ort

        tokenizer = AutoTokenizer.from_pretrained(str(out_dir))
        providers = ort.get_available_providers()
        provider = "CUDAExecutionProvider" if "CUDAExecutionProvider" in providers else "CPUExecutionProvider"

        model = ORTModelForSeq2SeqLM.from_pretrained(
            str(out_dir),
            provider=provider,
            use_cache=True,
        )

        # Short test translation
        src_lang = "eng_Latn" if "en2lun" in label else "run_Latn"
        tgt_lang = "run_Latn" if "en2lun" in label else "eng_Latn"
        tokenizer.src_lang = src_lang
        test_text = "Hello" if "en2lun" in label else "ningenda"
        inputs = tokenizer(test_text, return_tensors="pt")
        forced_bos = tokenizer.convert_tokens_to_ids(tgt_lang)
        out = model.generate(**inputs, forced_bos_token_id=forced_bos, max_length=50)
        result = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"  ✅ Smoke test passed on {provider}: '{test_text}' → '{result}'")
        return True
    except Exception as e:
        print(f"  ⚠️  Verification failed: {e}")
        return False


if __name__ == "__main__":
    results = {}

    for direction in ["en2lun", "lun2en"]:
        src = MODEL_DIR / f"nllb_{direction}"
        out = MODEL_DIR / f"nllb_{direction}_onnx"
        label = f"nllb_{direction}"

        ok = export_model(src, out, label)
        if ok:
            verify_onnx(out, label)
        results[label] = ok

    print("\n" + "="*60)
    print("EXPORT SUMMARY")
    for k, v in results.items():
        status = "✅ done" if v else "❌ failed"
        print(f"  {k}: {status}")
    print("="*60)
    print("\nNext: restart the backend — it will auto-detect and load ONNX models.")
