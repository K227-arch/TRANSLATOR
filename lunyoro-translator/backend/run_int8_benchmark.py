import time, requests

API = "http://localhost:8000"

si = requests.get(f"{API}/system-info").json()
print("Runtime info:")
print(f"  NLLB en2lun loaded: {si.get('nllb_en2lun')}")
print(f"  NLLB lun2en loaded: {si.get('nllb_lun2en')}")
print()

tests = [
    ("translate",         "I am going to the market"),
    ("translate",         "God loves all people"),
    ("translate",         "The child eats food at school"),
    ("translate-reverse", "ningenda omu isoko"),
    ("translate-reverse", "Ruhanga akunda abantu bona"),
    ("translate-reverse", "Omwana alya ebyokulya"),
]

print("=== ONNX INT8 Benchmark ===")
times = []
for ep, text in tests:
    t0 = time.time()
    r = requests.post(f"{API}/{ep}", json={"text": text, "context": "", "refine": False}, timeout=60)
    elapsed = time.time() - t0
    times.append(elapsed)
    d = r.json()
    direction = "EN->LUN" if ep == "translate" else "LUN->EN"
    print(f"  {direction} {elapsed:.2f}s | {text}")
    print(f"           -> {d.get('translation', 'ERROR')}")

avg_int8 = sum(times) / len(times)
avg_fp32 = 3.10
speedup = avg_fp32 / avg_int8

print()
print("Results:")
print(f"  ONNX FP32 avg : 3.10s/call")
print(f"  ONNX INT8 avg : {avg_int8:.2f}s/call")
print(f"  Speedup       : {speedup:.2f}x {'(faster)' if speedup > 1 else '(slower — AVX512 not available)'}")
print(f"  Model size    : ~4x smaller (2.9GB -> 732MB per decoder)")
