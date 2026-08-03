"""
benchmark_onnx.py — Compare ONNX FP32 vs INT8 translation speed and quality
"""
import time
import requests

API = "http://localhost:8000"

TESTS = [
    ("translate",         "I am going to the market"),
    ("translate",         "God loves all people"),
    ("translate",         "The child eats food at school"),
    ("translate",         "What is your name"),
    ("translate-reverse", "ningenda omu isoko"),
    ("translate-reverse", "Ruhanga akunda abantu bona"),
    ("translate-reverse", "Omwana alya ebyokulya"),
    ("translate-reverse", "ninkugonza"),
]


def run_benchmark(label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    times = []
    for endpoint, text in TESTS:
        t0 = time.time()
        try:
            r = requests.post(
                f"{API}/{endpoint}",
                json={"text": text, "context": "", "refine": False},
                timeout=60,
            )
            elapsed = time.time() - t0
            d = r.json()
            translation = d.get("translation", "ERROR")
            method = d.get("method", "?")
            times.append(elapsed)
            direction = "EN→LUN" if endpoint == "translate" else "LUN→EN"
            print(f"  {direction} {elapsed:.2f}s")
            print(f"    IN : {text}")
            print(f"    OUT: {translation} [{method}]")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ERROR ({elapsed:.2f}s): {e}")
            times.append(elapsed)

    avg = sum(times) / len(times)
    total = sum(times)
    print(f"\n  Total: {total:.2f}s  |  Avg per call: {avg:.2f}s")
    return times


if __name__ == "__main__":
    times = run_benchmark("ONNX FP32 (current)")
    avg = sum(times) / len(times)
    print(f"\n{'='*60}")
    print(f"SUMMARY: avg {avg:.2f}s/call on ONNX FP32")
    print(f"{'='*60}")
    print("""
To compare with INT8:
  1. Run: python quantize_onnx_int8.py
  2. Restart backend
  3. Run this benchmark again
""")
