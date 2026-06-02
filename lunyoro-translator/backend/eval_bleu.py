"""
eval_bleu.py
============
Evaluate BLEU + chrF scores for all four fine-tuned models using both GPUs in parallel:
  cuda:0  ->  MarianMT en→lun  +  MarianMT lun→en  (sequential on GPU 0)
  cuda:1  ->  NLLB     en→lun  +  NLLB     lun→en  (sequential on GPU 1)

Both GPU workers run concurrently via multiprocessing, then results are merged.

Usage:
    python eval_bleu.py                  # 500 samples (fast)
    python eval_bleu.py --samples 1000
    python eval_bleu.py --all            # full val set
    python eval_bleu.py --marian-only    # GPU 0 only
    python eval_bleu.py --nllb-only      # GPU 1 only
"""

import argparse
import os
import sys
import time
import multiprocessing as mp
from pathlib import Path

import pandas as pd
from sacrebleu.metrics import BLEU, CHRF

BACKEND_DIR = Path(__file__).parent
MODEL_DIR   = BACKEND_DIR / "model"
# Use val.csv as the evaluation set (same as training validation)
TEST_CSV    = BACKEND_DIR / "data" / "training" / "val.csv"

# Disable offline mode
for key in ("TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE"):
    os.environ.pop(key, None)


# ── Metrics helper ────────────────────────────────────────────────────────────

def compute_metrics(hypotheses: list, references: list) -> dict:
    bleu_metric = BLEU(effective_order=True)
    chrf_metric = CHRF()
    bleu_result = bleu_metric.corpus_score(hypotheses, [references])
    chrf_result = chrf_metric.corpus_score(hypotheses, [references])
    return {
        "bleu":       round(bleu_result.score, 2),
        "chrf":       round(chrf_result.score, 2),
        "bp":         round(bleu_result.bp, 4),
        "ratio":      round(bleu_result.sys_len / bleu_result.ref_len, 4) if bleu_result.ref_len else 0,
        "precisions": [round(p, 2) for p in bleu_result.precisions],
    }


# Keep backward-compatible alias
def compute_bleu(hypotheses: list, references: list) -> dict:
    return compute_metrics(hypotheses, references)


# ── Batch inference ───────────────────────────────────────────────────────────

def marian_batch(texts: list, tok, model, device: str, batch_size: int = 64) -> list:
    import torch
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        inputs = tok(batch, return_tensors="pt", padding=True,
                     truncation=True, max_length=256).to(device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                num_beams=4,
                max_length=256,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )
        results.extend(tok.batch_decode(out, skip_special_tokens=True))
        if (i // batch_size) % 5 == 0:
            done = min(i + batch_size, len(texts))
            print(f"    [{device}] {done}/{len(texts)}", flush=True)
    return results


def nllb_batch(texts: list, tok, model, device: str,
               src_lang: str, tgt_lang: str, batch_size: int = 16) -> list:
    import torch
    results = []
    tok.src_lang = src_lang
    forced_bos = tok.convert_tokens_to_ids(tgt_lang)
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        inputs = tok(batch, return_tensors="pt", padding=True,
                     truncation=True, max_length=256).to(device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos,
                num_beams=4,
                max_length=256,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )
        results.extend(tok.batch_decode(out, skip_special_tokens=True))
        if (i // batch_size) % 5 == 0:
            done = min(i + batch_size, len(texts))
            print(f"    [{device}] {done}/{len(texts)}", flush=True)
    return results


# ── Worker functions (run in separate processes) ──────────────────────────────

def worker_marian(en_texts, lun_texts, result_queue):
    """Runs on cuda:0 — evaluates both MarianMT directions."""
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    device = "cuda:0"
    results = {}

    # en → lun
    try:
        path = str(MODEL_DIR / "en2lun")
        print(f"[cuda:0] Loading MarianMT en2lun ...", flush=True)
        tok   = MarianTokenizer.from_pretrained(path)
        model = MarianMTModel.from_pretrained(path).eval().to(device)
        print(f"[cuda:0] Translating en→lun ({len(en_texts)} pairs) ...", flush=True)
        hyps = marian_batch(en_texts, tok, model, device)
        results["MarianMT en→lun"] = compute_bleu(hyps, lun_texts)
        results["MarianMT en→lun"]["samples"] = list(zip(en_texts[:5], hyps[:5], lun_texts[:5]))
        del model; torch.cuda.empty_cache()
        print(f"[cuda:0] MarianMT en→lun BLEU: {results['MarianMT en→lun']['bleu']}", flush=True)
    except Exception as e:
        results["MarianMT en→lun"] = {"error": str(e)}
        print(f"[cuda:0] MarianMT en→lun FAILED: {e}", flush=True)

    # lun → en
    try:
        path = str(MODEL_DIR / "lun2en")
        print(f"[cuda:0] Loading MarianMT lun2en ...", flush=True)
        tok   = MarianTokenizer.from_pretrained(path)
        model = MarianMTModel.from_pretrained(path).eval().to(device)
        print(f"[cuda:0] Translating lun→en ({len(lun_texts)} pairs) ...", flush=True)
        hyps = marian_batch(lun_texts, tok, model, device)
        results["MarianMT lun→en"] = compute_bleu(hyps, en_texts)
        results["MarianMT lun→en"]["samples"] = list(zip(lun_texts[:5], hyps[:5], en_texts[:5]))
        del model; torch.cuda.empty_cache()
        print(f"[cuda:0] MarianMT lun→en BLEU: {results['MarianMT lun→en']['bleu']}", flush=True)
    except Exception as e:
        results["MarianMT lun→en"] = {"error": str(e)}
        print(f"[cuda:0] MarianMT lun→en FAILED: {e}", flush=True)

    result_queue.put(("marian", results))


def worker_nllb(en_texts, lun_texts, result_queue):
    """Runs on cuda:1 — evaluates both NLLB directions."""
    import torch
    from transformers import NllbTokenizer, AutoModelForSeq2SeqLM
    device = "cuda:1"
    EN_LANG  = "eng_Latn"
    LUN_LANG = "run_Latn"
    results = {}

    # en → lun
    try:
        path = str(MODEL_DIR / "nllb_en2lun")
        print(f"[cuda:1] Loading NLLB en2lun ...", flush=True)
        tok   = NllbTokenizer.from_pretrained(path)
        model = AutoModelForSeq2SeqLM.from_pretrained(path).eval().to(device)
        print(f"[cuda:1] Translating en→lun ({len(en_texts)} pairs) ...", flush=True)
        hyps = nllb_batch(en_texts, tok, model, device, EN_LANG, LUN_LANG)
        results["NLLB en→lun"] = compute_bleu(hyps, lun_texts)
        results["NLLB en→lun"]["samples"] = list(zip(en_texts[:5], hyps[:5], lun_texts[:5]))
        del model; torch.cuda.empty_cache()
        print(f"[cuda:1] NLLB en→lun BLEU: {results['NLLB en→lun']['bleu']}", flush=True)
    except Exception as e:
        results["NLLB en→lun"] = {"error": str(e)}
        print(f"[cuda:1] NLLB en→lun FAILED: {e}", flush=True)

    # lun → en
    try:
        path = str(MODEL_DIR / "nllb_lun2en")
        print(f"[cuda:1] Loading NLLB lun2en ...", flush=True)
        tok   = NllbTokenizer.from_pretrained(path)
        model = AutoModelForSeq2SeqLM.from_pretrained(path).eval().to(device)
        print(f"[cuda:1] Translating lun→en ({len(lun_texts)} pairs) ...", flush=True)
        hyps = nllb_batch(lun_texts, tok, model, device, LUN_LANG, EN_LANG)
        results["NLLB lun→en"] = compute_bleu(hyps, en_texts)
        results["NLLB lun→en"]["samples"] = list(zip(lun_texts[:5], hyps[:5], en_texts[:5]))
        del model; torch.cuda.empty_cache()
        print(f"[cuda:1] NLLB lun→en BLEU: {results['NLLB lun→en']['bleu']}", flush=True)
    except Exception as e:
        results["NLLB lun→en"] = {"error": str(e)}
        print(f"[cuda:1] NLLB lun→en FAILED: {e}", flush=True)

    result_queue.put(("nllb", results))


# ── Print helpers ─────────────────────────────────────────────────────────────

def print_model_result(name: str, s: dict):
    if "error" in s:
        print(f"\n  ✗ {name}: {s['error']}")
        return
    print(f"\n{'─'*62}")
    print(f"  {name}")
    print(f"{'─'*62}")
    print(f"  BLEU score  : {s['bleu']}")
    print(f"  Brevity pen : {s['bp']}")
    print(f"  Length ratio: {s['ratio']}")
    print(f"  Precisions  : {s['precisions']}  (1-gram → 4-gram)")
    if "samples" in s:
        print(f"\n  Sample translations:")
        for src, hyp, ref in s["samples"]:
            print(f"    SRC : {src}")
            print(f"    HYP : {hyp}")
            print(f"    REF : {ref}")
            print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples",     type=int, default=500)
    parser.add_argument("--all",         action="store_true", help="Use full test set")
    parser.add_argument("--marian-only", action="store_true", help="GPU 0 only")
    parser.add_argument("--nllb-only",   action="store_true", help="GPU 1 only")
    args = parser.parse_args()

    # Load & sample test data
    df = pd.read_csv(TEST_CSV).dropna(subset=["english", "lunyoro"])
    df = df[df["english"].str.strip().ne("") & df["lunyoro"].str.strip().ne("")]
    n  = len(df) if (args.all or args.samples == 0) else min(args.samples, len(df))
    df = df.sample(n=n, random_state=42).reset_index(drop=True)

    en_texts  = df["english"].tolist()
    lun_texts = df["lunyoro"].tolist()

    print(f"\nEvaluating on {n} test pairs  (total available: {len(pd.read_csv(TEST_CSV))})")
    print(f"Strategy: MarianMT on cuda:0  ||  NLLB on cuda:1  (parallel)\n")

    t0 = time.time()
    result_queue = mp.Queue()
    processes = []

    # Spawn GPU workers
    if not args.nllb_only:
        p0 = mp.Process(target=worker_marian, args=(en_texts, lun_texts, result_queue))
        p0.start()
        processes.append(p0)

    if not args.marian_only:
        p1 = mp.Process(target=worker_nllb, args=(en_texts, lun_texts, result_queue))
        p1.start()
        processes.append(p1)

    # Collect results as workers finish
    all_scores = {}
    for _ in processes:
        tag, scores = result_queue.get()   # blocks until a worker puts something
        all_scores.update(scores)

    for p in processes:
        p.join()

    elapsed = time.time() - t0

    # Print per-model details
    ORDER = ["MarianMT en→lun", "MarianMT lun→en", "NLLB en→lun", "NLLB lun→en"]
    for name in ORDER:
        if name in all_scores:
            print_model_result(name, all_scores[name])

    # Summary table
    print(f"\n{'='*62}")
    print(f"  SCORE SUMMARY  ({n} pairs, {elapsed:.0f}s, both GPUs)")
    print(f"{'='*62}")
    print(f"  {'Model':<22} {'BLEU':>6}  {'chrF':>6}  {'BP':>6}  {'1g':>5} {'2g':>5} {'3g':>5} {'4g':>5}")
    print(f"  {'-'*22} {'-'*6}  {'-'*6}  {'-'*6}  {'-'*5} {'-'*5} {'-'*5} {'-'*5}")
    for name in ORDER:
        s = all_scores.get(name, {})
        if "error" in s:
            print(f"  {name:<22}  ERROR: {s['error'][:30]}")
        elif s:
            p = s["precisions"]
            chrf = s.get("chrf", 0.0)
            print(f"  {name:<22} {s['bleu']:>6.2f}  {chrf:>6.2f}  {s['bp']:>6.4f}  "
                  f"{p[0]:>5.1f} {p[1]:>5.1f} {p[2]:>5.1f} {p[3]:>5.1f}")
    print()


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
