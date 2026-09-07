"""
gr4_full_pipeline.py
====================
Complete pipeline for Grammar Rules 4 training data:
1. Extract clean pairs from language_rules_gr4.py
2. Back-translate for data augmentation
3. Clean and deduplicate
4. Merge into training data
5. Rebuild index
6. Fine-tune MarianMT (en2lun + lun2en) from existing checkpoint
7. Fine-tune NLLB (en2lun + lun2en) from existing checkpoint

Run:
    python gr4_full_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent


def run_step(step_name: str, command: list[str], cwd=None):
    print(f"\n{'='*70}")
    print(f"STEP: {step_name}")
    print(f"{'='*70}")
    try:
        subprocess.run(command, cwd=cwd or BACKEND_DIR, check=True)
        print(f"✓ {step_name} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {step_name} failed (exit {e.returncode})")
        return False
    except Exception as e:
        print(f"✗ {step_name} failed: {e}")
        return False


def main():
    print("="*70)
    print("GRAMMAR RULES 4 FULL TRAINING PIPELINE")
    print("="*70)
    print("\nSteps:")
    print("  1. Extract grammar 4 training pairs")
    print("  2. Back-translate gr4 pairs for augmentation")
    print("  3. Merge back-translations into train.csv")
    print("  4. Clean training data")
    print("  5. Rebuild semantic index")
    print("  6. Fine-tune MarianMT en2lun + lun2en (from existing checkpoint)")
    print("  7. Fine-tune NLLB en2lun + lun2en (from existing checkpoint)")
    print("\nNOTE: Models are fine-tuned from existing checkpoints, not from scratch.")

    # Auto-confirm when run non-interactively

    steps = [
        (
            "1. Extract GR4 pairs",
            [sys.executable, "extract_gr4_training_pairs.py"],
        ),
        (
            "2. Back-translate GR4 pairs",
            [sys.executable, "back_translate.py",
             "--input",  "data/cleaned/gr4_pairs.csv",
             "--output", "data/training/gr4_back_translated.csv",
             "--max", "500", "--batch", "8"],
        ),
        (
            "3. Merge back-translations",
            [sys.executable, "merge_back_translated.py",
             "--source", "data/training/gr4_back_translated.csv"],
        ),
        (
            "4. Clean training data",
            [sys.executable, "clean_training_data.py"],
        ),
        (
            "5. Rebuild semantic index",
            [sys.executable, "build_index.py"],
        ),
        (
            "6. Fine-tune MarianMT (both directions)",
            [sys.executable, "train_marian.py",
             "--direction", "both", "--epochs", "5", "--batch-size", "32"],
        ),
        (
            "7. Fine-tune NLLB (both directions)",
            [sys.executable, "train_nllb.py",
             "--direction", "both", "--epochs", "5", "--batch-size", "8"],
        ),
    ]

    failed = []
    for step_name, command in steps:
        ok = run_step(step_name, command)
        if not ok:
            failed.append(step_name)
            print(f"\n{step_name} failed. Continuing to next step...")
            continue

    print("\n" + "="*70)
    print("PIPELINE SUMMARY")
    print("="*70)
    if failed:
        print(f"✗ {len(failed)} step(s) failed:")
        for s in failed:
            print(f"  - {s}")
    else:
        print("✓ All steps completed successfully!")
        print("\nNext:")
        print("  Push models:  python upload_models_to_hf.py")
        print("  Deploy:       python push_to_hf_space.py")


if __name__ == "__main__":
    main()
