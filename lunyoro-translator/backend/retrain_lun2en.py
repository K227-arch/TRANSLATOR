"""
retrain_lun2en.py
=================
Retrain lun2en models after back-translation data is ready.

Waits for back_translate_full.log to show COMPLETE, then:
  1. Rebuilds new_only splits to include back-translated pairs
  2. Trains MarianMT lun2en (7 epochs, Fix1+Fix2+Fix3)
  3. Trains NLLB lun2en (5 epochs, Fix1+Fix2+Fix3)
  4. Pushes both lun2en models to HuggingFace Hub
  5. Pushes backend to HF Space
  6. Git push to both repos

Usage:
    python retrain_lun2en.py           # waits for back-translation then trains
    python retrain_lun2en.py --now     # skip wait, train immediately
"""
import sys
import subprocess
import argparse
import time
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE      = Path(__file__).parent
DATA_DIR  = BASE / "data" / "training"
TRAIN_CSV = DATA_DIR / "train.csv"
VAL_CSV   = DATA_DIR / "val.csv"
BT_LOG    = BASE / "logs" / "back_translate_full.log"
py        = sys.executable


def run(label: str, cmd: list) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=BASE)
    ok = result.returncode == 0
    print(f"\n  [{'OK' if ok else 'FAILED'}] {label}  ({datetime.now().strftime('%H:%M:%S')})")
    return ok


def wait_for_back_translation():
    """Poll the back-translation log until COMPLETE appears."""
    print("Waiting for back-translation to complete...")
    while True:
        if BT_LOG.exists():
            content = BT_LOG.read_text(encoding="utf-8", errors="ignore")
            if "BACK-TRANSLATION COMPLETE" in content:
                print("Back-translation complete. Starting lun2en retrain...")
                return
        time.sleep(30)
        print(f"  Still waiting... ({datetime.now().strftime('%H:%M:%S')})")


def rebuild_new_only_splits():
    """
    Rebuild new_only_train.csv and new_only_val.csv to include
    back-translated pairs. Uses the .bak files as the baseline
    (what was trained before this session).
    """
    print("\nRebuilding new_only splits with back-translated data...")

    # Find the oldest backup = pre-session baseline
    bak_train = DATA_DIR / "train.csv.bak"
    bak_val   = DATA_DIR / "val.csv.bak"

    if not bak_train.exists():
        print("  No backup found — using full train.csv as new_only")
        import shutil
        shutil.copy(TRAIN_CSV, DATA_DIR / "new_only_train.csv")
        shutil.copy(VAL_CSV,   DATA_DIR / "new_only_val.csv")
        return

    old_t = pd.read_csv(bak_train)
    old_v = pd.read_csv(bak_val)
    trained_keys = set(zip(
        pd.concat([old_t, old_v])["english"].str.lower().str.strip(),
        pd.concat([old_t, old_v])["lunyoro"].str.lower().str.strip(),
    ))
    print(f"  Baseline (pre-session): {len(trained_keys):,} pairs")

    cur_t = pd.read_csv(TRAIN_CSV)
    cur_v = pd.read_csv(VAL_CSV)

    new_t = cur_t[~cur_t.apply(
        lambda r: (str(r["english"]).lower().strip(),
                   str(r["lunyoro"]).lower().strip()) in trained_keys, axis=1)]
    new_v = cur_v[~cur_v.apply(
        lambda r: (str(r["english"]).lower().strip(),
                   str(r["lunyoro"]).lower().strip()) in trained_keys, axis=1)]

    new_t.to_csv(DATA_DIR / "new_only_train.csv", index=False)
    new_v.to_csv(DATA_DIR / "new_only_val.csv",   index=False)
    print(f"  new_only_train: {len(new_t):,}  new_only_val: {len(new_v):,}")
    print(f"  (includes back-translated pairs)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now",              action="store_true",
                        help="Skip wait, train immediately")
    parser.add_argument("--skip-initial-train", action="store_true",
                        help="Skip steps 1+2 (MarianMT+NLLB retrain), go straight to BT+final pass")
    parser.add_argument("--no-push",          action="store_true")
    parser.add_argument("--marian-epochs", type=int, default=7)
    parser.add_argument("--nllb-epochs",   type=int, default=5)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  LUN2EN RETRAIN PIPELINE (Fix1 + Fix2 + Fix3)")
    print(f"  MarianMT lun2en: {args.marian_epochs} epochs")
    print(f"  NLLB    lun2en: {args.nllb_epochs} epochs")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    if not args.now:
        wait_for_back_translation()

    # Rebuild new_only splits to include back-translated pairs
    rebuild_new_only_splits()

    failed = []

    # MarianMT lun2en — Fix1 (tag strip) + Fix2 (min-lun-words) + Fix3 (back-trans)
    if not args.skip_initial_train:
        ok = run(
            f"MarianMT lun2en -- {args.marian_epochs} epochs (Fix1+Fix2+Fix3)",
            [py, "train_marian.py",
             "--direction", "lun2en",
             "--epochs", str(args.marian_epochs),
             "--lr", "3e-5",
             "--min-lun-words", "3",
             "--new-only"],
        )
        if not ok:
            failed.append("MarianMT-lun2en")

        # NLLB lun2en — same fixes
        ok = run(
            f"NLLB lun2en -- {args.nllb_epochs} epochs (Fix1+Fix2+Fix3)",
            [py, "train_nllb.py",
             "--direction", "lun2en",
             "--epochs", str(args.nllb_epochs),
             "--lr", "8e-6",
             "--min-lun-words", "3",
             "--new-only"],
        )
        if not ok:
            failed.append("NLLB-lun2en")
    else:
        print("  [SKIP] Initial MarianMT+NLLB retrain (--skip-initial-train)")

    # ── Step: Back-translate remaining 23k candidates ────────────────────────
    # Run after training so the GPU is free, then do a final retrain pass
    if not failed:
        print(f"\n{'='*60}")
        print(f"  BACK-TRANSLATING REMAINING CANDIDATES")
        print(f"{'='*60}")
        bt_remaining = BASE / "data" / "cleaned" / "bt_remaining_candidates.csv"
        if bt_remaining.exists():
            import pandas as _pd
            n_remaining = len(_pd.read_csv(bt_remaining))
            print(f"  Found {n_remaining:,} remaining candidates")
            ok = run(
                f"Back-translate remaining {n_remaining:,} candidates",
                [py, "back_translate_lun2en.py",
                 "--max-sentences", str(n_remaining),
                 "--batch-size", "32",
                 "--min-lun-words", "5",
                 "--merge"],
            )
            if ok:
                print("\n  Remaining BT done. Running final lun2en retrain pass...")
                # Rebuild new_only splits to include the new BT pairs
                rebuild_new_only_splits()
                # Final retrain pass on all accumulated BT data
                run(
                    "MarianMT lun2en FINAL PASS -- 5 epochs (all BT data)",
                    [py, "train_marian.py",
                     "--direction", "lun2en",
                     "--epochs", "5",
                     "--lr", "2e-5",
                     "--min-lun-words", "3",
                     "--new-only"],
                )
                run(
                    "NLLB lun2en FINAL PASS -- 3 epochs (all BT data)",
                    [py, "train_nllb.py",
                     "--direction", "lun2en",
                     "--epochs", "3",
                     "--lr", "5e-6",
                     "--min-lun-words", "3",
                     "--new-only"],
                )
        else:
            print("  No remaining candidates file found — skipping")

    # Push
    if not args.no_push and not failed:
        run("Push lun2en models to HuggingFace Hub",
            [py, "push_models.py", "--model", "lun2en"])
        run("Push nllb_lun2en to HuggingFace Hub",
            [py, "push_models.py", "--model", "nllb_lun2en"])
        run("Push backend to HF Space",
            [py, "push_to_hf_space.py"])

        repo_root = BASE.parent
        for cmd in [
            ["git", "add",
             "backend/data/training/train.csv",
             "backend/data/training/val.csv",
             "backend/data/training/new_only_train.csv",
             "backend/data/training/new_only_val.csv",
             "backend/data/cleaned/back_translated_lun2en.csv",
             "backend/data/cleaned/bt_remaining_candidates.csv",
             "backend/train_marian.py",
             "backend/train_nllb.py",
             "backend/back_translate_lun2en.py",
             "backend/analyze_bt_coverage.py",
             "backend/knowledge_graph.py",
             "backend/translate.py",
             "backend/main.py",
             "backend/eval_bleu.py",
             "backend/run_full_training.py",
             "backend/run_k227_pipeline.py",
             "backend/retrain_lun2en.py",
             "backend/language_rules_gr4.py",
             "backend/language_rules_gr5.py"],
            ["git", "commit", "-m",
             f"feat: Fix1+2+3 lun2en; full BT coverage; selective RAG; knowledge graph; chrF+val_loss; fp32 ({datetime.now().strftime('%Y-%m-%d')})"],
            ["git", "push", "origin", "main"],
            ["git", "push", "k227", "main"],
        ]:
            result = subprocess.run(cmd, cwd=repo_root)
            if result.returncode != 0:
                print(f"[WARN] git command failed: {' '.join(cmd)}")

    print(f"\n{'='*60}")
    print(f"  LUN2EN RETRAIN COMPLETE -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("  All steps completed successfully.")


if __name__ == "__main__":
    main()
