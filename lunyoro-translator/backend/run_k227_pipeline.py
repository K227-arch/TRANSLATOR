"""
run_k227_pipeline.py
====================
Executes the full k227 training pipeline in the correct order:

  1. MarianMT en2lun retrain  (5 epochs, full val, lr=3e-5, new-only data)
  2. MarianMT lun2en retrain  (5 epochs, full val, lr=3e-5, min-lun-words=3)
  3. NLLB en2lun              (5 epochs, full val, lr=8e-6)
  4. NLLB lun2en              (5 epochs, full val, lr=8e-6, min-lun-words=3)
  5. MarianMT both directions (7 epochs, full val, lr=3e-5, min-lun-words=3)
     -- final polish pass with more epochs and direction-aware sampler
  6. Push all 4 models to HuggingFace Hub
  7. Push backend to HF Space
  8. Git push to origin + k227

All steps use:
  - new-only training data (26,916 pairs)
  - full val.csv (16,952 pairs) for BLEU evaluation
  - direction-aware weighted sampler
  - min-lun-words=3 filter for lun2en (removes dict entries that hurt BLEU)
"""
import sys
import subprocess
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
py   = sys.executable


def run(label: str, cmd: list) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=BASE)
    ok = result.returncode == 0
    print(f"\n  [{'OK' if ok else 'FAILED'}] {label}  ({datetime.now().strftime('%H:%M:%S')})")
    return ok


def main():
    failed = []

    print(f"\n{'='*60}")
    print(f"  K227 FULL TRAINING PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Data: 26,916 new pairs | Val: 16,952 pairs")
    print(f"{'='*60}")

    # ── Step 1: MarianMT en2lun retrain (missed auto-trigger) ────────────────
    ok = run("MarianMT en2lun retrain -- 5 epochs (lr=3e-5, full val)",
             [py, "train_marian.py",
              "--direction", "en2lun",
              "--epochs", "5",
              "--lr", "3e-5",
              "--new-only"])
    if not ok: failed.append("marian-en2lun-retrain")

    # ── Step 2: MarianMT lun2en retrain ──────────────────────────────────────
    ok = run("MarianMT lun2en retrain -- 5 epochs (lr=3e-5, min-lun-words=3)",
             [py, "train_marian.py",
              "--direction", "lun2en",
              "--epochs", "5",
              "--lr", "3e-5",
              "--min-lun-words", "3",
              "--new-only"])
    if not ok: failed.append("marian-lun2en-retrain")

    # ── Step 3: NLLB en2lun ──────────────────────────────────────────────────
    ok = run("NLLB en2lun -- 5 epochs (lr=8e-6, full val)",
             [py, "train_nllb.py",
              "--direction", "en2lun",
              "--epochs", "5",
              "--lr", "8e-6",
              "--new-only"])
    if not ok: failed.append("nllb-en2lun")

    # ── Step 4: NLLB lun2en ──────────────────────────────────────────────────
    ok = run("NLLB lun2en -- 5 epochs (lr=8e-6, min-lun-words=3)",
             [py, "train_nllb.py",
              "--direction", "lun2en",
              "--epochs", "5",
              "--lr", "8e-6",
              "--min-lun-words", "3",
              "--new-only"])
    if not ok: failed.append("nllb-lun2en")

    # ── Step 5: MarianMT final polish (7 epochs, both directions) ────────────
    ok = run("MarianMT both -- 7 epochs final polish (lr=3e-5, min-lun-words=3)",
             [py, "train_marian.py",
              "--direction", "both",
              "--epochs", "7",
              "--lr", "3e-5",
              "--min-lun-words", "3",
              "--new-only"])
    if not ok: failed.append("marian-both-final")

    # ── Step 6-8: Push ────────────────────────────────────────────────────────
    if failed:
        print(f"\n[WARN] Some steps failed: {failed}")
        print("[WARN] Pushing anyway with whatever completed successfully...")

    run("Push all models to HuggingFace Hub",
        [py, "push_models.py", "--all"])

    run("Push backend to HF Space",
        [py, "push_to_hf_space.py"])

    repo_root = BASE.parent
    for cmd in [
        ["git", "add",
         "backend/train_marian.py",
         "backend/train_nllb.py",
         "backend/run_full_training.py",
         "backend/run_k227_pipeline.py",
         "backend/data/training/train.csv",
         "backend/data/training/val.csv",
         "backend/data/training/new_only_train.csv",
         "backend/data/training/new_only_val.csv"],
        ["git", "commit", "-m",
         f"train: k227 pipeline complete - MarianMT 5+5+7ep, NLLB 5+5ep, direction-aware sampler ({datetime.now().strftime('%Y-%m-%d')})"],
        ["git", "push", "origin", "main"],
        ["git", "push", "k227", "main"],
    ]:
        result = subprocess.run(cmd, cwd=repo_root)
        if result.returncode != 0:
            print(f"[WARN] git command failed: {' '.join(cmd)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    if failed:
        print(f"  Failed steps: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("  All steps completed successfully.")


if __name__ == "__main__":
    main()
