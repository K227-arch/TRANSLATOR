import pandas as pd, json
from pathlib import Path

print("=== benchmark_scores.csv ===")
df = pd.read_csv("backend/feedback/benchmark_scores.csv")
print(f"Entries: {len(df)}")
print(df.to_string())

print()
print("=== benchmark_scores.json ===")
data = json.loads(Path("backend/feedback/benchmark_scores.json").read_text(encoding="utf-8"))
print(f"Entries: {len(data)}")
for e in data:
    src  = str(e.get("source_text", ""))[:45]
    sqs  = e.get("sqs")
    band = e.get("sqs_band", "")
    mng  = e.get("score_mng")
    grm  = e.get("score_grm")
    tns  = e.get("score_tns")
    vcb  = e.get("score_vcb")
    ort  = e.get("score_ort")
    ctx  = e.get("score_ctx")
    flu  = e.get("score_flu")
    cul  = e.get("score_cul")
    dom  = e.get("domain", "")
    print(f"  Source : {src}")
    print(f"  Domain : {dom}")
    print(f"  SQS    : {sqs}  ({band})")
    print(f"  Scores : MNG={mng} GRM={grm} TNS={tns} VCB={vcb} ORT={ort} CTX={ctx} FLU={flu} CUL={cul}")
    print()
