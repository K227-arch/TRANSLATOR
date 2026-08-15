"""
Download and cache MobileNetV2 for offline use on the Pi.
Run once with internet before deploying:
    python download_model.py
"""
import os
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "models" / "mobilenet_v2"


def main():
    # Ensure downloads are allowed
    for key in ["TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE"]:
        if key in os.environ:
            del os.environ[key]

    from transformers import MobileNetV2ForImageClassification, MobileNetV2ImageProcessor

    model_name = "google/mobilenet_v2_1.0_224"
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {model_name} to {MODEL_DIR} ...")
    processor = MobileNetV2ImageProcessor.from_pretrained(model_name)
    model = MobileNetV2ForImageClassification.from_pretrained(model_name)

    processor.save_pretrained(str(MODEL_DIR))
    model.save_pretrained(str(MODEL_DIR))

    files = list(MODEL_DIR.iterdir())
    total_mb = sum(f.stat().st_size for f in files if f.is_file()) / 1e6
    print(f"Done: {len(files)} files, {total_mb:.1f} MB total")


if __name__ == "__main__":
    main()
