"""
Image Classification module for the Lunyoro/Runyoro Translator.

Uses MobileNetV2 (google/mobilenet_v2_1.0_224) for lightweight image classification.
Identified English labels are passed to the existing translation pipeline.
"""

import io
import logging
from datetime import datetime

logger = logging.getLogger("image_translation")

# Supported image MIME types and their file signatures (magic bytes)
SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

# Magic byte signatures for format detection
_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
}


def _detect_mime_from_bytes(data: bytes) -> str | None:
    """Detect image MIME type from magic bytes."""
    if not data:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and len(data) > 11 and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class ImageClassifier:
    """Singleton image classification service using MobileNetV2."""

    def __init__(self):
        self._model = None
        self._processor = None
        self._loaded = False
        self._loading = False
        self._load_error: str | None = None
        self._load_start_time: float | None = None

    def is_ready(self) -> bool:
        """Check if the model has finished loading."""
        return self._loaded and self._model is not None

    def get_load_error(self) -> str | None:
        """Get the model loading error message, if any."""
        return self._load_error

    def load_model(self) -> None:
        """
        Load MobileNetV2 from local cache or HuggingFace Hub.
        Falls back gracefully if model is not available (offline mode).
        """
        import time, os

        if self._loaded or self._loading:
            return

        self._loading = True
        self._load_start_time = time.time()

        try:
            from transformers import MobileNetV2ForImageClassification, MobileNetV2ImageProcessor

            model_name = "google/mobilenet_v2_1.0_224"

            # Try local model directory first
            local_path = os.path.join(os.path.dirname(__file__), "model", "mobilenet_v2")

            if os.path.isdir(local_path) and any(
                f.endswith((".safetensors", ".bin", ".json")) for f in os.listdir(local_path)
            ):
                load_path = local_path
                print(f"[image_classifier] Loading {model_name} from local cache...")
            else:
                # Check if we're in offline mode
                offline = os.getenv("TRANSFORMERS_OFFLINE", "0").strip() in ("1", "true")
                if offline:
                    self._loading = False
                    self._load_error = (
                        f"Offline mode is enabled and no local cache found at {local_path}. "
                        f"Run: python download_mobilenet.py to cache the model."
                    )
                    print(f"[image_classifier] Skipping — offline mode, no local model")
                    return
                load_path = model_name
                print(f"[image_classifier] Loading {model_name} from HuggingFace Hub...")

            self._processor = MobileNetV2ImageProcessor.from_pretrained(load_path)
            self._model = MobileNetV2ForImageClassification.from_pretrained(load_path)
            self._model.eval()

            self._loaded = True
            self._loading = False
            elapsed = time.time() - self._load_start_time
            print(f"[image_classifier] Model loaded in {elapsed:.1f}s")

        except Exception as e:
            self._loading = False
            self._load_error = str(e)
            logger.error(
                f"[image_classifier] Model load failed at "
                f"{datetime.utcnow().isoformat()}: {type(e).__name__}: {str(e)[:200]}"
            )
            print(f"[image_classifier] FAILED to load model: {e}")

    def classify(self, image_bytes: bytes, top_k: int = 5) -> list[dict]:
        """
        Classify an image and return top-K results.

        Args:
            image_bytes: Raw image file bytes (JPEG, PNG, or WebP)
            top_k: Number of top predictions to return (default 5)

        Returns:
            List of dicts: [{"label": str, "confidence": float}, ...]
            Sorted by confidence descending.

        Raises:
            RuntimeError: If model not loaded
            ValueError: If image cannot be decoded
        """
        if not self._loaded or self._model is None:
            raise RuntimeError("Image classifier model is not loaded")

        import torch
        from PIL import Image

        # Decode image
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise ValueError(f"Cannot decode image: {e}")

        # Preprocess and run inference
        inputs = self._processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits

        # Apply softmax to get probabilities
        probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        # Get top-k predictions
        top_probs, top_indices = torch.topk(probs, min(top_k, len(probs)))

        results = []
        for prob, idx in zip(top_probs, top_indices):
            label = self._model.config.id2label[idx.item()]
            # Clean up ImageNet labels (they can have commas for synonyms)
            label = label.split(",")[0].strip().lower()
            results.append({
                "label": label,
                "confidence": round(prob.item(), 4),
            })

        return results


# Module-level singleton
image_classifier = ImageClassifier()


def validate_image_upload(content_type: str | None, filename: str | None, file_bytes: bytes) -> bytes:
    """
    Validate an uploaded image file for format and size.

    Checks (in order):
    1. File is not empty (0 bytes)
    2. File format is supported (JPEG, PNG, WebP) — checked via magic bytes
    3. File size does not exceed 10 MB

    Args:
        content_type: The Content-Type/MIME from the upload
        filename: Original filename from the upload
        file_bytes: The raw file bytes

    Returns:
        The validated image bytes

    Raises:
        ValueError with appropriate error message on validation failure
    """
    # 1. Check empty file
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("File is empty. Please upload a valid image file.")

    # 2. Check format (magic bytes take priority over Content-Type header)
    detected_mime = _detect_mime_from_bytes(file_bytes)
    if detected_mime is None or detected_mime not in SUPPORTED_IMAGE_MIMES:
        raise ValueError(
            "Unsupported file format. Accepted formats: JPEG, PNG, WebP."
        )

    # 3. Check size
    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(
            f"File too large. Maximum allowed size is 10 MB. "
            f"Your file is {len(file_bytes) / (1024*1024):.1f} MB."
        )

    return file_bytes
