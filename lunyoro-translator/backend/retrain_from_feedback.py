"""
retrain_from_feedback.py
========================
End-to-end retraining pipeline using collected human feedback.

Steps:
  1. Export approved (thumbs-up) feedback pairs
  2. Merge into train.csv
  3. Fine-tune models for N epochs
  4. Optionally push to HuggingFace

Usage:
    # Retrain with feedback (5 epochs)
    python retrain_from_feedback.py --epochs 5

    # Retrain and push to HuggingFace
    python retrain_from_feedback.py --epochs 5 --push

    # Dry run (show stats, don't train)
    python retrain_from_feedback.py --dry-run
"""
import os
import sys
import argparse
import subprocess

BASE = os.path.dirname(__file__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",    type=int, default=5)
    parser.add_argument("--direction", type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--push",      action="store_true",
                        help="Push updated models to HuggingFace after training")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Show stats without training")
    args = parser.parse_args()

    print("=== Retrain from Human Feedback ===\n")

    # 1. Check feedback stats
    from feedback_store import get_stats, export_for_retraining
    stats = get_stats()
    print(f"Feedback collected:")
    print(f"  Total:       {stats['total']:,}")
    print(f"  Thumbs up:   {stats['thumbs_up']:,}")
    print(f"  Thumbs down: {stats['thumbs_down']:,}")
    print(f"  Exportable:  {stats['exportable']:,}\n")

    if stats['exportable'] == 0:
        print("No approved feedback to train on. Exiting.")
        return

    if stats['exportable'] < 100:
        print(f"Warning: Only {stats['exportable']} approved pairs. "
              f"Recommend collecting 500+ for meaningful improvement.")
        if not args.dry_run:
            confirm = input("Continue anyway? [y/N] ")
            if confirm.lower() != 'y':
                return

    if args.dry_run:
        print("Dry run complete.")
        return

    # 2. Export feedback
    print("Exporting approved pairs...")
    feedback_csv = export_for_retraining()
    print(f"  Saved to: {feedback_csv}\n")

    # 3. Merge into train.csv
    print("Merging into train.csv...")
    result = subprocess.run(
        [sys.executable, "merge_back_translated.py", "--input", feedback_csv],
        cwd=BASE,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error merging: {result.stderr}")
        return

    # 4. Fine-tune models
    print(f"Fine-tuning models ({args.direction}, {args.epochs} epochs)...")
    print("This may take 1-3 hours on GPU.\n")
    result = subprocess.run(
        [sys.executable, "train_marian.py",
         "--direction", args.direction,
         "--epochs", str(args.epochs),
         "--context-window",
         "--subword-reg"],
        cwd=BASE,
    )
    if result.returncode != 0:
        print("Training failed.")
        return

    print("\nTraining complete.")

    # 5. Optionally push to HuggingFace
    if args.push:
        print("\nPushing updated models to HuggingFace...")
        result = subprocess.run(
            [sys.executable, "push_models.py", "--direction", args.direction],
            cwd=BASE,
        )
        if result.returncode == 0:
            print("Models pushed successfully.")
        else:
            print("Push failed. Run manually: python push_models.py")

    print("\nDone. Updated models ready in model/{direction}/")


if __name__ == "__main__":
    main()
