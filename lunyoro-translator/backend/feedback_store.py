"""
feedback_store.py
=================
Lightweight feedback storage for translation ratings.
Stores feedback as JSON lines in feedback.jsonl.
Automatically exports to Excel/CSV in feedback folder.
"""
import os
import json
import threading
from datetime import datetime
from pathlib import Path

BASE          = Path(__file__).parent
FEEDBACK_FILE = os.getenv("FEEDBACK_FILE",
                           os.path.join(BASE, "feedback.jsonl"))
FEEDBACK_EXPORT_DIR = BASE / "feedback"

_lock = threading.Lock()


def save_feedback(entry: dict):
    """Append a feedback entry to the JSONL store and export to files (thread-safe)."""
    entry.setdefault("timestamp", datetime.utcnow().isoformat())
    with _lock:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Auto-export to Excel/CSV after each feedback (async)
    try:
        threading.Thread(target=auto_export_feedback, daemon=True).start()
    except:
        pass  # Don't fail if export fails


def auto_export_feedback():
    """Automatically export feedback to Excel and CSV files."""
    try:
        import pandas as pd
        
        # Create feedback directory
        FEEDBACK_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load all feedback
        entries = load_all_feedback()
        if not entries:
            return
        
        # Create DataFrame
        df = pd.DataFrame(entries)
        
        # Reorder columns
        column_order = [
            'timestamp', 'direction', 'rating', 'model_used',
            'source_text', 'translation', 'correction',
            'error_type', 'ip'
        ]
        column_order = [col for col in column_order if col in df.columns]
        df = df[column_order]
        
        # Add readable columns
        df['rating_label'] = df['rating'].map({1: 'Positive', -1: 'Negative', 0: 'Neutral'})
        df['has_correction'] = df['correction'].apply(lambda x: 'Yes' if str(x).strip() else 'No')
        
        # Export to CSV
        csv_path = FEEDBACK_EXPORT_DIR / "all_feedback.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        # Export to Excel with multiple sheets
        excel_path = FEEDBACK_EXPORT_DIR / "feedback_analytics.xlsx"
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Sheet 1: All Feedback
            df.to_excel(writer, sheet_name='All Feedback', index=False)
            
            # Sheet 2: Summary Stats
            summary_data = {
                'Metric': [
                    'Total Feedback',
                    'Positive (Thumbs Up)',
                    'Negative (Thumbs Down)',
                    'Neutral',
                    'Approval Rate (%)',
                    'Unique Users',
                ],
                'Value': [
                    len(df),
                    len(df[df['rating'] > 0]),
                    len(df[df['rating'] < 0]),
                    len(df[df['rating'] == 0]),
                    round(100 * len(df[df['rating'] > 0]) / len(df), 1) if len(df) > 0 else 0,
                    df['ip'].nunique(),
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 3: Model Usage
            if 'model_used' in df.columns:
                model_stats = df['model_used'].value_counts().reset_index()
                model_stats.columns = ['Model', 'Count']
                model_stats['Percentage'] = round(100 * model_stats['Count'] / len(df), 1)
                model_stats.to_excel(writer, sheet_name='Model Usage', index=False)
            
            # Sheet 4: Error Types
            if 'error_type' in df.columns:
                error_data = []
                for error_str in df['error_type'].dropna():
                    for error in str(error_str).split(','):
                        error = error.strip()
                        if error:
                            error_data.append(error)
                if error_data:
                    error_df = pd.DataFrame({'Error Type': error_data})
                    error_stats = error_df['Error Type'].value_counts().reset_index()
                    error_stats.columns = ['Error Type', 'Count']
                    error_stats.to_excel(writer, sheet_name='Error Types', index=False)
            
            # Sheet 5: Daily Activity
            df['date'] = pd.to_datetime(df['timestamp'], errors='coerce').dt.date
            daily = df.groupby('date').size().reset_index(name='Feedback Count')
            daily.to_excel(writer, sheet_name='Daily Activity', index=False)
        
    except Exception as e:
        # Silently fail - don't break feedback submission
        pass


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


def get_detailed_analytics() -> dict:
    """Return detailed analytics about feedback patterns."""
    from collections import Counter
    
    entries = load_all_feedback()
    
    if not entries:
        return {
            "total_feedback": 0,
            "model_usage": {},
            "model_ratings": {},
            "error_types": {},
            "direction_stats": {},
            "correction_rate": 0,
            "unique_users": 0,
            "feedback_over_time": {},
        }
    
    # Model usage tracking
    model_usage = Counter(e.get("model_used", "unknown") for e in entries if e.get("model_used"))
    
    # Model ratings (which model gets better ratings)
    model_ratings = {}
    for model in ["marian", "nllb", "both", "none"]:
        model_entries = [e for e in entries if e.get("model_used") == model]
        if model_entries:
            positive = sum(1 for e in model_entries if e.get("rating", 0) > 0)
            negative = sum(1 for e in model_entries if e.get("rating", 0) < 0)
            total_model = len(model_entries)
            model_ratings[model] = {
                "total": total_model,
                "positive": positive,
                "negative": negative,
                "approval_rate": round(100 * positive / total_model, 1) if total_model > 0 else 0,
            }
    
    # Error type analysis
    error_types = Counter()
    for e in entries:
        error_str = e.get("error_type", "")
        if error_str:
            # Split by comma for multiple error types
            for error in error_str.split(","):
                error = error.strip()
                if error:
                    error_types[error] += 1
    
    # Direction statistics
    direction_stats = {}
    for direction in ["en→lun", "lun→en"]:
        dir_entries = [e for e in entries if e.get("direction") == direction]
        if dir_entries:
            positive = sum(1 for e in dir_entries if e.get("rating", 0) > 0)
            total_dir = len(dir_entries)
            direction_stats[direction] = {
                "total": total_dir,
                "positive": positive,
                "approval_rate": round(100 * positive / total_dir, 1) if total_dir > 0 else 0,
            }
    
    # Correction rate (how often users provide corrections)
    corrections = sum(1 for e in entries if e.get("correction", "").strip())
    correction_rate = round(100 * corrections / len(entries), 1) if entries else 0
    
    # Unique users
    unique_users = len(set(e.get("ip", "unknown") for e in entries))
    
    # Feedback over time (by day)
    from datetime import datetime
    feedback_by_day = Counter()
    for e in entries:
        timestamp = e.get("timestamp", "")
        if timestamp:
            try:
                date = datetime.fromisoformat(timestamp).date().isoformat()
                feedback_by_day[date] += 1
            except:
                pass
    
    # Most recent feedback
    recent_entries = sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
    recent_feedback = [
        {
            "timestamp": e.get("timestamp", ""),
            "direction": e.get("direction", ""),
            "rating": e.get("rating", 0),
            "model_used": e.get("model_used", ""),
            "error_type": e.get("error_type", ""),
        }
        for e in recent_entries
    ]
    
    return {
        "total_feedback": len(entries),
        "model_usage": dict(model_usage),
        "model_ratings": model_ratings,
        "error_types": dict(error_types.most_common(10)),
        "direction_stats": direction_stats,
        "correction_rate": correction_rate,
        "unique_users": unique_users,
        "feedback_by_day": dict(sorted(feedback_by_day.items())[-30:]),  # Last 30 days
        "recent_feedback": recent_feedback,
    }


def get_model_comparison() -> dict:
    """Compare performance between MarianMT and NLLB models."""
    entries = load_all_feedback()
    
    marian_entries = [e for e in entries if e.get("model_used") == "marian"]
    nllb_entries = [e for e in entries if e.get("model_used") == "nllb"]
    
    def calculate_metrics(model_entries):
        if not model_entries:
            return {
                "total_uses": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "approval_rate": 0,
                "avg_rating": 0,
            }
        
        positive = sum(1 for e in model_entries if e.get("rating", 0) > 0)
        negative = sum(1 for e in model_entries if e.get("rating", 0) < 0)
        total = len(model_entries)
        avg_rating = sum(e.get("rating", 0) for e in model_entries) / total if total > 0 else 0
        
        return {
            "total_uses": total,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "approval_rate": round(100 * positive / total, 1) if total > 0 else 0,
            "avg_rating": round(avg_rating, 2),
        }
    
    marian_metrics = calculate_metrics(marian_entries)
    nllb_metrics = calculate_metrics(nllb_entries)
    
    # Determine winner
    winner = None
    if marian_metrics["approval_rate"] > nllb_metrics["approval_rate"]:
        winner = "marian"
    elif nllb_metrics["approval_rate"] > marian_metrics["approval_rate"]:
        winner = "nllb"
    else:
        winner = "tie"
    
    return {
        "marian": marian_metrics,
        "nllb": nllb_metrics,
        "winner": winner,
        "comparison": {
            "approval_rate_diff": round(marian_metrics["approval_rate"] - nllb_metrics["approval_rate"], 1),
            "usage_ratio": round(marian_metrics["total_uses"] / nllb_metrics["total_uses"], 2) if nllb_metrics["total_uses"] > 0 else 0,
        }
    }

