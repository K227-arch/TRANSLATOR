"""
_run_sp17_training.py  —  Run once on HF Space to train on sentence pair 17 data.
Execute from /app:  python _run_sp17_training.py
"""
import subprocess, sys
print("=== SP17 Incremental Training ===")
print("Step 1: MarianMT --new-only both directions 5 epochs")
subprocess.run([
    sys.executable, "train_marian.py",
    "--new-only",
    "--direction", "both",
    "--epochs", "5",
    "--batch-size", "32",
    "--lr", "3e-5",
], check=True)
print("\nStep 2: Push updated MarianMT models to HF Hub")
subprocess.run([sys.executable, "push_models.py", "--model", "en2lun"], check=True)
subprocess.run([sys.executable, "push_models.py", "--model", "lun2en"], check=True)
print("\nDone.")
