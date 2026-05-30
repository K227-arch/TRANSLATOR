"""
run_full_training.py
====================
Chains MarianMT + NLLB training (both directions, new-only data),
then pushes all models to HuggingFace Hub and HF Space,
then pushes code to both GitHub repos.

Usage:
    python run_full_training.py                          # full pipeline
    python run_full_training.py --skip-marian            # NLLB only, then retrain MarianMT
    python run_full_training.py --skip-nllb              # MarianMT only
    python run_full_training.py --no-push                # skip all pushes
    python run_full_training.py --retrain-marian-only    # just retrain MarianMT on full val
"""
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent


def run(label: str, cmd: list, cwd: Path = BASE) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=cwd)
    ok = result.returncode == 0
    status = "OK" if ok else f"FAILED (exit {result.returncode})"
    print(f"\n  [{status}] {label}  ({datetime.now().strftime('%H:%M:%S')})")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-marian",          action="store_true",
                        help="Skip initial MarianMT training (still retrains after NLLB)")
    parser.add_argument("--skip-nllb",            action="store_true")
    parser.add_argument("--no-push",              action="store_true")
    parser.add_argument("--retrain-marian-only",  action="store_true",
                        help="Only run the MarianMT retrain step on full val set")
    parser.add_argument("--marian-en2lun-epochs", type=int, default=5)
    parser.add_argument("--marian-lun2en-epochs", type=int, default=5)
    parser.add_argument("--nllb-en2lun-epochs",   type=int, default=5)
    parser.add_argument("--nllb-lun2en-epochs",   type=int, default=5)
    # Retrain epochs (used after NLLB, on full val set)
    parser.add_argument("--retrain-en2lun-epochs", type=int, default=5)
    parser.add_argument("--retrain-lun2en-epochs", type=int, default=5)
    args = parser.parse_args()

    py = sys.executable
    failed = []

    print(f"\n{'='*60}")
    print(f"  FULL TRAINING PIPELINE")
    if not args.retrain_marian_only:
        if not args.skip_marian:
            print(f"  MarianMT en2lun : {args.marian_en2lun_epochs} epochs (new-only)")
            print(f"  MarianMT lun2en : {args.marian_lun2en_epochs} epochs (new-only)")
        if not args.skip_nllb:
            print(f"  NLLB    en2lun  : {args.nllb_en2lun_epochs} epochs (new-only)")
            print(f"  NLLB    lun2en  : {args.nllb_lun2en_epochs} epochs (new-only)")
    print(f"  MarianMT retrain en2lun : {args.retrain_en2lun_epochs} epochs (full val)")
    print(f"  MarianMT retrain lun2en : {args.retrain_lun2en_epochs} epochs (full val)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # ── MarianMT initial (new-only) ───────────────────────────────────────────
    if not args.skip_marian and not args.retrain_marian_only:
        ok = run(
            f"MarianMT en2lun -- {args.marian_en2lun_epochs} epochs (new-only)",
            [py, "train_marian.py",
             "--direction", "en2lun",
             "--epochs", str(args.marian_en2lun_epochs),
             "--new-only"],
        )
        if not ok:
            failed.append("MarianMT-en2lun")

        ok = run(
            f"MarianMT lun2en -- {args.marian_lun2en_epochs} epochs (new-only)",
            [py, "train_marian.py",
             "--direction", "lun2en",
             "--epochs", str(args.marian_lun2en_epochs),
             "--new-only"],
        )
        if not ok:
            failed.append("MarianMT-lun2en")

    # ── NLLB ─────────────────────────────────────────────────────────────────
    if not args.skip_nllb and not args.retrain_marian_only:
        ok = run(
            f"NLLB en2lun -- {args.nllb_en2lun_epochs} epochs (new-only)",
            [py, "train_nllb.py",
             "--direction", "en2lun",
             "--epochs", str(args.nllb_en2lun_epochs),
             "--new-only"],
        )
        if not ok:
            failed.append("NLLB-en2lun")

        ok = run(
            f"NLLB lun2en -- {args.nllb_lun2en_epochs} epochs (new-only)",
            [py, "train_nllb.py",
             "--direction", "lun2en",
             "--epochs", str(args.nllb_lun2en_epochs),
             "--new-only"],
        )
        if not ok:
            failed.append("NLLB-lun2en")

    # ── MarianMT RETRAIN on full val set ──────────────────────────────────────
    # Always runs after NLLB (or standalone with --retrain-marian-only)
    # Uses new-only training data but validates on full val.csv (16,952 pairs)
    print(f"\n{'='*60}")
    print(f"  MarianMT RETRAIN on full val set")
    print(f"{'='*60}")

    ok = run(
        f"MarianMT en2lun RETRAIN -- {args.retrain_en2lun_epochs} epochs (full val)",
        [py, "train_marian.py",
         "--direction", "en2lun",
         "--epochs", str(args.retrain_en2lun_epochs),
         "--new-only"],   # trains on new data, validates on full val.csv
    )
    if not ok:
        failed.append("MarianMT-en2lun-retrain")

    ok = run(
        f"MarianMT lun2en RETRAIN -- {args.retrain_lun2en_epochs} epochs (full val)",
        [py, "train_marian.py",
         "--direction", "lun2en",
         "--epochs", str(args.retrain_lun2en_epochs),
         "--new-only"],   # trains on new data, validates on full val.csv
    )
    if not ok:
        failed.append("MarianMT-lun2en-retrain")

    # ── Push ──────────────────────────────────────────────────────────────────
    if not args.no_push:
        if failed:
            print(f"\n[WARN] Skipping push -- failed steps: {failed}")
        else:
            run("Push all models to HuggingFace Hub",
                [py, "push_models.py", "--all"])

            run("Push backend to HF Space",
                [py, "push_to_hf_space.py"])

            repo_root = BASE.parent
            for cmd in [
                ["git", "add",
                 "backend/data/training/train.csv",
                 "backend/data/training/val.csv",
                 "backend/data/training/new_only_train.csv",
                 "backend/data/training/new_only_val.csv",
                 "backend/train_marian.py",
                 "backend/train_nllb.py",
                 "backend/clean_new_training_data.py",
                 "backend/run_full_training.py",
                 "backend/generate_grammar_pairs.py",
                 "backend/language_rules_gr4.py",
                 "backend/language_rules_gr5.py",
                 "backend/translate.py"],
                ["git", "commit", "-m",
                 f"train: MarianMT+NLLB 5ep each + MarianMT retrain on full val ({datetime.now().strftime('%Y-%m-%d')})"],
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
        print(f"  Failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("  All steps completed successfully.")


if __name__ == "__main__":
    main()
