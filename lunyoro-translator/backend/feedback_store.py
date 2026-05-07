"""
feedback_store.py
=================
Lightweight feedback storage for translation ratings.
Stores feedback as JSON lines in feedback.jsonl.
Provides helpers to export approved pairs for retraining.
"""
import os
import json
import threading
from datetime import datetime

BASE          = os.path.dirname(__file__)
FEEDBACK_FILE = os.getenv("FEEDBACK_FILE",
                           os.path.join(BASE, "feedback.jsonl"))

_lock = threading.Lock()


def save_feedback(entry: dict):
    """Append a feedback entry to the JSONL store (thread-safe)."""
    entry.setdefault("timestamp", datetime.utcnow().isoformat())
    with _lock:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_all_feedback() -> list[dict]:
    """Load all feedback entries."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    entries = []
    with open(FEEDBACK_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def get_approved_pairs(min_rating: int = 1) -> list[dict]:
    """
    Return feedback entries with rating >= min_rating.
    rating: 1 = thumbs up, -1 = thumbs down, 0 = neutral
    """
    return [e for e in load_all_feedback()
            if e.get("rating", 0) >= min_rating]


def export_for_retraining(output_path: str | None = None,
                           min_rating: int = 1) -> str:
    """
    Export approved pairs as a CSV suitable for merging into train.csv.
    Returns the path to the exported file.
    """
    import pandas as pd

    approved = get_approved_pairs(min_rating)
    if not approved:
        return ""

    rows = []
    for e in approved:
        src = e.get("source_text", "").strip()
        tgt = e.get("translation", "").strip()
        direction = e.get("direction", "en→lun")
        if not src or not tgt:
            continue
        if direction == "en→lun":
            rows.append({"english": src, "lunyoro": tgt})
        else:
            rows.append({"english": tgt, "lunyoro": src})

    if not rows:
        return ""

    df = pd.DataFrame(rows).drop_duplicates(subset=["english", "lunyoro"])
    if output_path is None:
        output_path = os.path.join(BASE, "data", "training", "feedback_approved.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def get_stats() -> dict:
    """Return summary statistics about collected feedback."""
    entries = load_all_feedback()
    total     = len(entries)
    thumbs_up = sum(1 for e in entries if e.get("rating", 0) > 0)
    thumbs_dn = sum(1 for e in entries if e.get("rating", 0) < 0)
    neutral   = total - thumbs_up - thumbs_dn
    return {
        "total":      total,
        "thumbs_up":  thumbs_up,
        "thumbs_down": thumbs_dn,
        "neutral":    neutral,
        "exportable": thumbs_up,
    }
