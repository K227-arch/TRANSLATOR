"""
download_mobilenet.py
=====================
Download and cache MobileNetV2 for offline use by the image classifier.

Run once before setting TRANSFORMERS_OFFLINE=1:
    python download_mobilenet.py

The model will be saved to model/mobilenet_v2/
"""
import os
from pathlib import Path

BASE = Path(__file__).parent
OUTPUT_DIR = BASE / "model" / "mobilenet_v2"

def main():
    # Temporarily allow downloads
    for key in ["TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE"]:
        if key in os.environ:
            del os.environ[key]

    from transformers import MobileNetV2ForImageClassification, MobileNetV2ImageProcessor

    model_name = "google/mobilenet_v2_1.0_224"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {model_name} to {OUTPUT_DIR} ...")
    processor = MobileNetV2ImageProcessor.from_pretrained(model_name)
    model = MobileNetV2ForImageClassification.from_pretrained(model_name)

    processor.save_pretrained(str(OUTPUT_DIR))
    model.save_pretrained(str(OUTPUT_DIR))

    print(f"✅ Saved to {OUTPUT_DIR}")
    files = list(OUTPUT_DIR.iterdir())
    total_mb = sum(f.stat().st_size for f in files if f.is_file()) / 1e6
    print(f"   {len(files)} files, {total_mb:.1f} MB total")

if __name__ == "__main__":
    main()
