"""
run_bleu_via_api.py
===================
Compute BLEU scores for all 4 models by calling the live HF Space API
against the local test.csv — no GPU or local model weights needed.

Usage:
    python run_bleu_via_api.py [--samples 200]
"""
import argparse, json, os, sys, time
import pandas as pd
import requests
from sacrebleu.metrics import BLEU

API = os.getenv("NEXT_PUBLIC_API_URL", "https://keithtwesigye-runyoro-translator-api.hf.space")
TEST_CSV = os.path.join(os.path.dirname(__file__), "data", "training", "test.csv")


def translate_via_api(text: str, direction: str) -> dict:
    """Call /translate or /translate-reverse and return the full JSON response."""
    endpoint = "/translate" if direction == "en2lun" else "/translate-reverse"
    try:
        r = requests.post(f"{API}{endpoint}", json={"text": text}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def evaluate(en_texts, lun_texts, direction: str, model_key: str, samples: int):
    """Translate `samples` pairs and compute BLEU for one model/direction."""
    bleu = BLEU(effective_order=True)
    hypotheses, references = [], []
    errors = 0

    src_texts = en_texts[:samples] if direction == "en2lun" else lun_texts[:samples]
    ref_texts = lun_texts[:samples] if direction == "en2lun" else en_texts[:samples]

    for i, (src, ref) in enumerate(zip(src_texts, ref_texts)):
        resp = translate_via_api(src, direction)
        if "error" in resp:
            errors += 1
            hypotheses.append("")
        else:
            hyp = resp.get(model_key) or resp.get("translation") or ""
            hypotheses.append(hyp)
        references.append(ref)

        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{samples} translated ...", flush=True)
        time.sleep(0.05)   # be polite to the API

    score = bleu.corpus_score(hypotheses, [references])
    return {
        "bleu":       round(score.score, 2),
        "bp":         round(score.bp, 4),
        "precisions": [round(p, 2) for p in score.precisions],
        "errors":     errors,
        "samples":    samples,
        # 5 example translations
        "examples": [
            {"src": src_texts[i], "hyp": hypotheses[i], "ref": ref_texts[i]}
            for i in range(min(5, len(hypotheses)))
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=200,
                        help="Number of test pairs to evaluate (default 200)")
    args = parser.parse_args()

    # Load test set
    if not os.path.exists(TEST_CSV):
        print(f"ERROR: test.csv not found at {TEST_CSV}")
        sys.exit(1)

    df = pd.read_csv(TEST_CSV).dropna(subset=["english", "lunyoro"])
    df = df[df["english"].str.strip().ne("") & df["lunyoro"].str.strip().ne("")]
    df = df.sample(n=min(args.samples, len(df)), random_state=42).reset_index(drop=True)

    en_texts  = df["english"].tolist()
    lun_texts = df["lunyoro"].tolist()

    print(f"\n{'='*62}")
    print(f"  BLEU Evaluation via HF Space API")
    print(f"  API: {API}")
    print(f"  Test pairs: {len(df)}")
    print(f"{'='*62}\n")

    results = {}

    # Each API call returns both marian and nllb translations in one shot
    # translation_marian / translation_nllb keys
    MODELS = [
        ("MarianMT en→lun", "en2lun", "translation_marian"),
        ("NLLB    en→lun",  "en2lun", "translation_nllb"),
        ("MarianMT lun→en", "lun2en", "translation_marian"),
        ("NLLB    lun→en",  "lun2en", "translation_nllb"),
    ]

    for label, direction, key in MODELS:
        print(f"Evaluating {label} ...")
        r = evaluate(en_texts, lun_texts, direction, key, len(df))
        results[label] = r
        print(f"  → BLEU: {r['bleu']}  (BP={r['bp']}, errors={r['errors']})\n")

    # ── Summary table ─────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  BLEU SCORE SUMMARY  ({len(df)} test pairs)")
    print(f"{'='*62}")
    print(f"  {'Model':<22} {'BLEU':>6}  {'BP':>6}  {'1g':>5} {'2g':>5} {'3g':>5} {'4g':>5}")
    print(f"  {'-'*22} {'-'*6}  {'-'*6}  {'-'*5} {'-'*5} {'-'*5} {'-'*5}")
    for label, r in results.items():
        p = r["precisions"]
        print(f"  {label:<22} {r['bleu']:>6.2f}  {r['bp']:>6.4f}  "
              f"{p[0]:>5.1f} {p[1]:>5.1f} {p[2]:>5.1f} {p[3]:>5.1f}")

    # ── Sample translations ────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print("  SAMPLE TRANSLATIONS")
    print(f"{'='*62}")
    for label, r in results.items():
        print(f"\n  {label}")
        print(f"  {'─'*58}")
        for ex in r["examples"]:
            print(f"    SRC : {ex['src']}")
            print(f"    HYP : {ex['hyp']}")
            print(f"    REF : {ex['ref']}")
            print()

    # Save JSON
    out_path = os.path.join(os.path.dirname(__file__), "bleu_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Full results saved to: {out_path}\n")


if __name__ == "__main__":
    main()
