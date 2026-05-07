"""
auto_retrain.py
===============
Automated retraining system that triggers when sufficient clean feedback is collected.

Features:
- Monitors feedback.jsonl for approved pairs
- Applies cleaning/preprocessing pipeline
- Auto-approves pairs meeting quality criteria
- Triggers retraining at 100+ clean pairs
- Runs as background service or scheduled task
"""
import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
FEEDBACK_FILE = os.getenv("FEEDBACK_FILE", BASE / "feedback.jsonl")
RETRAIN_THRESHOLD = int(os.getenv("AUTO_RETRAIN_THRESHOLD", "100"))
LAST_RETRAIN_FILE = BASE / ".last_retrain"
LOG_FILE = BASE / "auto_retrain.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean and normalize text for training."""
    import re
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove special characters that shouldn't be in training data
    text = re.sub(r'[^\w\s\'\-.,!?;:()\[\]{}]', '', text)
    
    # Remove repeated punctuation
    text = re.sub(r'([.,!?;:])\1+', r'\1', text)
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
    
    return text.strip()


def is_valid_pair(source: str, translation: str, direction: str) -> bool:
    """
    Validate if a translation pair meets quality criteria for auto-approval.
    
    Criteria:
    - Both texts are non-empty after cleaning
    - Length is reasonable (3-500 chars)
    - No excessive repetition
    - Contains actual words (not just punctuation)
    - Source and translation are different
    """
    import re
    
    if not source or not translation:
        return False
    
    # Length checks
    if len(source) < 3 or len(translation) < 3:
        return False
    if len(source) > 500 or len(translation) > 500:
        return False
    
    # Must contain letters
    if not re.search(r'[a-zA-Z]', source) or not re.search(r'[a-zA-Z]', translation):
        return False
    
    # Check for excessive repetition (same word 4+ times)
    words_src = source.lower().split()
    words_tgt = translation.lower().split()
    if words_src and max(words_src.count(w) for w in set(words_src)) >= 4:
        return False
    if words_tgt and max(words_tgt.count(w) for w in set(words_tgt)) >= 4:
        return False
    
    # Source and translation shouldn't be identical
    if source.lower().strip() == translation.lower().strip():
        return False
    
    # Check for minimum word count
    if len(words_src) < 2 or len(words_tgt) < 2:
        return False
    
    return True


def preprocess_feedback_entry(entry: dict) -> dict | None:
    """
    Preprocess a feedback entry through cleaning pipeline.
    Returns cleaned entry if it passes validation, None otherwise.
    """
    source = clean_text(entry.get("source_text", ""))
    translation = clean_text(entry.get("translation", ""))
    direction = entry.get("direction", "en→lun")
    rating = entry.get("rating", 0)
    
    # Only process positive ratings
    if rating < 1:
        return None
    
    # If user provided a correction, use that instead
    correction = clean_text(entry.get("correction", ""))
    if correction:
        translation = correction
    
    # Validate the pair
    if not is_valid_pair(source, translation, direction):
        return None
    
    return {
        "source_text": source,
        "translation": translation,
        "direction": direction,
        "rating": rating,
        "timestamp": entry.get("timestamp", datetime.utcnow().isoformat()),
        "approved": True,
        "cleaned": True,
    }


def get_clean_approved_pairs() -> list[dict]:
    """
    Load all feedback, apply cleaning pipeline, and return approved pairs.
    """
    if not FEEDBACK_FILE.exists():
        return []
    
    approved_pairs = []
    seen_pairs = set()  # Deduplicate
    
    with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                cleaned = preprocess_feedback_entry(entry)
                
                if cleaned:
                    # Create unique key for deduplication
                    pair_key = (
                        cleaned["source_text"].lower(),
                        cleaned["translation"].lower(),
                        cleaned["direction"]
                    )
                    
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        approved_pairs.append(cleaned)
            
            except json.JSONDecodeError:
                logger.warning(f"Skipping invalid JSON line: {line[:50]}...")
                continue
    
    return approved_pairs


def get_last_retrain_count() -> int:
    """Get the number of pairs used in the last retraining."""
    if not LAST_RETRAIN_FILE.exists():
        return 0
    
    try:
        with open(LAST_RETRAIN_FILE, 'r') as f:
            data = json.load(f)
            return data.get("pair_count", 0)
    except:
        return 0


def save_retrain_record(pair_count: int):
    """Save record of retraining."""
    with open(LAST_RETRAIN_FILE, 'w') as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "pair_count": pair_count,
        }, f, indent=2)


def export_clean_pairs(pairs: list[dict], output_path: Path) -> int:
    """Export clean pairs to CSV for training."""
    import pandas as pd
    
    rows = []
    for pair in pairs:
        src = pair["source_text"]
        tgt = pair["translation"]
        direction = pair["direction"]
        
        if direction == "en→lun":
            rows.append({"english": src, "lunyoro": tgt})
        else:
            rows.append({"english": tgt, "lunyoro": src})
    
    if not rows:
        return 0
    
    df = pd.DataFrame(rows).drop_duplicates(subset=["english", "lunyoro"])
    df.to_csv(output_path, index=False, encoding="utf-8")
    return len(df)


def trigger_retraining(pair_count: int, epochs: int = 3):
    """Trigger the retraining pipeline."""
    logger.info(f"Starting retraining with {pair_count} clean pairs...")
    
    try:
        # Run retrain_from_feedback.py
        result = subprocess.run(
            [sys.executable, "retrain_from_feedback.py", 
             "--epochs", str(epochs),
             "--direction", "both"],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hour timeout
        )
        
        if result.returncode == 0:
            logger.info("Retraining completed successfully")
            logger.info(result.stdout)
            save_retrain_record(pair_count)
            return True
        else:
            logger.error(f"Retraining failed: {result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        logger.error("Retraining timed out after 2 hours")
        return False
    except Exception as e:
        logger.error(f"Retraining error: {e}")
        return False


def check_and_retrain():
    """
    Check if retraining should be triggered and execute if needed.
    Returns True if retraining was triggered, False otherwise.
    """
    logger.info("Checking feedback for auto-retraining...")
    
    # Get clean approved pairs
    clean_pairs = get_clean_approved_pairs()
    clean_count = len(clean_pairs)
    
    logger.info(f"Found {clean_count} clean, approved feedback pairs")
    
    # Check if we have enough new pairs since last retrain
    last_count = get_last_retrain_count()
    new_pairs = clean_count - last_count
    
    logger.info(f"New pairs since last retrain: {new_pairs}")
    
    if new_pairs >= RETRAIN_THRESHOLD:
        logger.info(f"Threshold reached ({new_pairs} >= {RETRAIN_THRESHOLD}). Triggering retraining...")
        
        # Export clean pairs
        export_path = BASE / "data" / "training" / "feedback_clean_approved.csv"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        exported = export_clean_pairs(clean_pairs, export_path)
        
        logger.info(f"Exported {exported} unique pairs to {export_path}")
        
        # Trigger retraining
        success = trigger_retraining(clean_count, epochs=3)
        
        if success:
            logger.info("Auto-retraining completed successfully")
            return True
        else:
            logger.error("Auto-retraining failed")
            return False
    else:
        logger.info(f"Not enough new pairs yet ({new_pairs}/{RETRAIN_THRESHOLD})")
        return False


def run_monitor(check_interval: int = 3600):
    """
    Run continuous monitoring service.
    Checks every check_interval seconds (default: 1 hour).
    """
    logger.info(f"Starting auto-retrain monitor (checking every {check_interval}s)")
    logger.info(f"Threshold: {RETRAIN_THRESHOLD} new clean pairs")
    
    while True:
        try:
            check_and_retrain()
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        
        logger.info(f"Sleeping for {check_interval} seconds...")
        time.sleep(check_interval)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated retraining system")
    parser.add_argument("--check", action="store_true",
                        help="Check once and exit (don't run as service)")
    parser.add_argument("--monitor", action="store_true",
                        help="Run as continuous monitoring service")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Check interval in seconds (default: 3600 = 1 hour)")
    parser.add_argument("--threshold", type=int, default=None,
                        help=f"Minimum new pairs to trigger retrain (default: {RETRAIN_THRESHOLD})")
    parser.add_argument("--stats", action="store_true",
                        help="Show statistics only")
    
    args = parser.parse_args()
    
    # Update threshold if specified
    threshold = args.threshold if args.threshold is not None else RETRAIN_THRESHOLD
    
    if args.stats:
        # Show statistics
        clean_pairs = get_clean_approved_pairs()
        last_count = get_last_retrain_count()
        new_pairs = len(clean_pairs) - last_count
        
        print(f"\n=== Auto-Retrain Statistics ===")
        print(f"Total clean approved pairs: {len(clean_pairs)}")
        print(f"Pairs used in last retrain: {last_count}")
        print(f"New pairs since last retrain: {new_pairs}")
        print(f"Threshold for next retrain: {threshold}")
        print(f"Progress: {new_pairs}/{threshold} ({100*new_pairs/threshold:.1f}%)" if threshold > 0 else "Progress: N/A")
        
        if LAST_RETRAIN_FILE.exists():
            with open(LAST_RETRAIN_FILE, 'r') as f:
                data = json.load(f)
                print(f"Last retrain: {data.get('timestamp', 'Unknown')}")
        else:
            print("Last retrain: Never")
        print()
    
    elif args.monitor:
        # Run as continuous service
        run_monitor(args.interval)
    
    else:
        # Single check (default)
        check_and_retrain()


if __name__ == "__main__":
    main()
