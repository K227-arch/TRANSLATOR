"""
train_all.py
============
Unified training pipeline — runs MarianMT + NLLB fine-tuning sequentially,
then pushes both to HuggingFace automatically.

Usage:
    python train_all.py                          # 3 epochs each, both directions
    python train_all.py --epochs 5               # 5 epochs each
    python train_all.py --marian-only            # skip NLLB
    python train_all.py --nllb-only              # skip MarianMT
    python train_all.py --no-push                # skip HF push
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

BASE = Path(__file__).parent


def run(step: str, cmd: list[str]) -> bool:
    print(f"\n{'='*65}")
    print(f"  {step}")
    print(f"{'='*65}")
    result = subprocess.run(cmd, cwd=BASE)
    if result.returncode != 0:
        print(f"\n✗ {step} failed (exit {result.returncode})")
        return False
    print(f"\n✓ {step} complete")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",       type=int, default=3)
    parser.add_argument("--batch-marian", type=int, default=64)
    parser.add_argument("--batch-nllb",   type=int, default=8)
    parser.add_argument("--direction",    type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--marian-only",  action="store_true")
    parser.add_argument("--nllb-only",    action="store_true")
    parser.add_argument("--no-push",      action="store_true")
    args = parser.parse_args()

    py = sys.executable
    failed = []

    # ── 1. MarianMT ───────────────────────────────────────────────────────────
    if not args.nllb_only:
        ok = run(
            f"MarianMT fine-tuning ({args.direction}, {args.epochs} epochs)",
            [py, "train_marian.py",
             "--direction", args.direction,
             "--epochs",    str(args.epochs),
             "--batch-size", str(args.batch_marian)],
        )
        if not ok:
            failed.append("MarianMT")

    # ── 2. NLLB ───────────────────────────────────────────────────────────────
    if not args.marian_only:
        ok = run(
            f"NLLB fine-tuning ({args.direction}, {args.epochs} epochs)",
            [py, "train_nllb.py",
             "--direction", args.direction,
             "--epochs",    str(args.epochs),
             "--batch-size", str(args.batch_nllb)],
        )
        if not ok:
            failed.append("NLLB")

    # ── 3. Push to HuggingFace ────────────────────────────────────────────────
    if not args.no_push and not failed:
        hf_token = os.getenv("HF_TOKEN", "")
        if not hf_token:
            # Try loading from .env
            env_path = BASE / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("HF_TOKEN="):
                        hf_token = line.split("=", 1)[1].strip()
                        os.environ["HF_TOKEN"] = hf_token
                        break

        if hf_token:
            ok = run(
                "Pushing MarianMT models to HuggingFace",
                [py, "upload_models_to_hf.py"],
            )
            if not ok:
                failed.append("HF push (MarianMT)")

            ok = run(
                "Pushing backend to HF Space",
                [py, "push_to_hf_space.py"],
            )
            if not ok:
                failed.append("HF Space push")
        else:
            print("\n⚠ HF_TOKEN not set — skipping HuggingFace push.")
            print("  Set HF_TOKEN in .env or as an environment variable.")
    elif failed:
        print(f"\n⚠ Skipping HF push due to failed steps: {failed}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  TRAINING PIPELINE SUMMARY")
    print(f"{'='*65}")
    if failed:
        print(f"✗ Failed steps: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("✓ All steps completed successfully.")
        print("  Models saved locally and pushed to HuggingFace.")


if __name__ == "__main__":
    main()
