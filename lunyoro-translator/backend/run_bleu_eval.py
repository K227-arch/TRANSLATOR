"""
Compute BLEU scores for all 4 models by calling the live API.

Usage:
    python run_bleu_eval.py [--samples 200] [--api http://localhost:8000]
"""
import argparse
import csv
import json
import sys
import time
import urllib.request
import urllib.error

try:
    from sacrebleu.metrics import BLEU
except ImportError:
    print("Installing sacrebleu...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sacrebleu"])
    from sacrebleu.metrics import BLEU

import os

BASE    = os.path.dirname(__file__)
TEST_CSV = os.path.join(BASE, "data", "training", "test.csv")

def api_translate(text: str, direction: str, api_base: str) -> dict:
    """Call the translation API and return the full JSON response."""
    endpoint = f"{api_base}/translate" if direction == "en2lun" else f"{api_base}/translate-reverse"
    payload  = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {}


def evaluate(direction: str, sources: list, references: list, api_base: str):
    """Translate all sources and compute BLEU for marian + nllb."""
    bleu = BLEU(effective_order=True)

    hyp_marian, hyp_nllb = [], []
    errors = 0

    for i, src in enumerate(sources):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{direction}] {i+1}/{len(sources)} ...", flush=True)

        # Retry up to 2 times on failure
        result = {}
        for attempt in range(2):
            result = api_translate(src, direction, api_base)
            if result:
                break
            time.sleep(1.0)

        if not result:
            errors += 1
            hyp_marian.append("")
            hyp_nllb.append("")
            continue

        hyp_marian.append(result.get("translation_marian") or "")
        hyp_nllb.append(result.get("translation_nllb")   or "")
        time.sleep(0.3)   # be polite to the API

    score_marian = bleu.corpus_score(hyp_marian, [references]).score
    score_nllb   = bleu.corpus_score(hyp_nllb,   [references]).score

    return {
        "marian": round(score_marian, 2),
        "nllb":   round(score_nllb,   2),
        "errors": errors,
        "samples": len(sources),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=200,
                        help="Number of test pairs to evaluate (default 200)")
    parser.add_argument("--api", default="https://keithtwesigye-runyoro-translator-api.hf.space",
                        help="Backend API base URL")
    args = parser.parse_args()

    # ── Load test set ─────────────────────────────────────────────────────────
    rows = []
    with open(TEST_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            en = (row.get("english") or "").strip()
            lun = (row.get("lunyoro") or "").strip()
            if en and lun and len(en) > 5 and len(lun) > 5:
                rows.append((en, lun))

    # Use a fixed stride so we sample evenly across the test set
    stride = max(1, len(rows) // args.samples)
    sample = rows[::stride][: args.samples]
    en_list  = [r[0] for r in sample]
    lun_list = [r[1] for r in sample]

    print(f"\n{'='*60}")
    print(f"BLEU Evaluation — {args.samples} test pairs")
    print(f"API: {args.api}")
    print(f"{'='*60}\n")

    # ── en → lun ──────────────────────────────────────────────────────────────
    print("Direction: English → Lunyoro")
    en2lun = evaluate("en2lun", en_list, lun_list, args.api)

    # ── lun → en ──────────────────────────────────────────────────────────────
    print("\nDirection: Lunyoro → English")
    lun2en = evaluate("lun2en", lun_list, en_list, args.api)

    # ── Results ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"\n{'Model':<20} {'en→lun':>10} {'lun→en':>10}")
    print(f"{'-'*40}")
    print(f"{'MarianMT':<20} {en2lun['marian']:>10.2f} {lun2en['marian']:>10.2f}")
    print(f"{'NLLB-200':<20} {en2lun['nllb']:>10.2f} {lun2en['nllb']:>10.2f}")
    print(f"\nSamples evaluated : {args.samples}")
    print(f"API errors        : en2lun={en2lun['errors']}  lun2en={lun2en['errors']}")

    # Save JSON
    out = {
        "samples": args.samples,
        "api": args.api,
        "en2lun": {"marian_bleu": en2lun["marian"], "nllb_bleu": en2lun["nllb"]},
        "lun2en": {"marian_bleu": lun2en["marian"], "nllb_bleu": lun2en["nllb"]},
    }
    out_path = os.path.join(BASE, "bleu_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved → {out_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
