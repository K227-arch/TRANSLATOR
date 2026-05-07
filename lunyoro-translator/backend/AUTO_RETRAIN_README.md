# Automatic Retraining System

## Overview

The automatic retraining system monitors user feedback and triggers model retraining when sufficient high-quality translation pairs are collected.

## How It Works

### 1. Feedback Collection
- Users provide feedback through the web interface
- Each feedback includes:
  - Source text and translation
  - Rating (thumbs up/down)
  - Optional correction
  - Error type categorization

### 2. Cleaning & Preprocessing Pipeline

Every feedback entry goes through automatic validation:

**Quality Checks:**
- ✓ Non-empty text after cleaning
- ✓ Reasonable length (3-500 characters)
- ✓ Contains actual words (not just punctuation)
- ✓ No excessive repetition
- ✓ Source and translation are different
- ✓ Minimum 2 words in each text
- ✓ Proper character encoding

**Cleaning Steps:**
- Remove extra whitespace
- Normalize punctuation
- Remove special characters
- Deduplicate identical pairs
- Use user corrections when provided

### 3. Auto-Approval

Pairs are automatically approved if they:
- Have positive rating (thumbs up)
- Pass all quality checks
- Are unique (not duplicates)

### 4. Automatic Retraining

**Trigger:** When 100+ new clean pairs are collected since last retrain

**Process:**
1. Export clean approved pairs to CSV
2. Merge into training dataset
3. Fine-tune both MarianMT and NLLB-200 models (3 epochs)
4. Save updated models
5. Record retrain timestamp

**Duration:** 1-3 hours on GPU

## Usage

### Check Status

```bash
# View statistics
python auto_retrain.py --stats

# Output:
# === Auto-Retrain Statistics ===
# Total clean approved pairs: 245
# Pairs used in last retrain: 150
# New pairs since last retrain: 95
# Threshold for next retrain: 100
# Progress: 95/100 (95.0%)
# Last retrain: 2026-05-07T14:30:00
```

### Manual Check

```bash
# Check once and trigger retrain if threshold met
python auto_retrain.py --check
```

### Run as Service

```bash
# Monitor continuously (checks every hour)
python auto_retrain.py --monitor

# Custom check interval (every 30 minutes)
python auto_retrain.py --monitor --interval 1800

# Custom threshold (retrain at 50 pairs instead of default 100)
python auto_retrain.py --monitor --threshold 50

# Check once with custom threshold
python auto_retrain.py --check --threshold 200
```

### API Endpoints

**Get auto-retrain status:**
```bash
curl http://localhost:8000/feedback/auto-retrain-status
```

Response:
```json
{
  "total_clean_pairs": 245,
  "pairs_in_last_retrain": 150,
  "new_pairs_since_retrain": 95,
  "threshold": 100,
  "progress_percentage": 95.0,
  "ready_for_retrain": false,
  "last_retrain_timestamp": "2026-05-07T14:30:00"
}
```

## Configuration

Environment variables:

```bash
# Threshold for triggering retrain (default: 100)
export AUTO_RETRAIN_THRESHOLD=100

# Feedback file location
export FEEDBACK_FILE=/path/to/feedback.jsonl
```

**Note:** The `--threshold` command-line argument overrides the `AUTO_RETRAIN_THRESHOLD` environment variable when specified. If not provided via command line, the system uses the environment variable value or defaults to 100.

## Automatic Triggering

The system automatically checks for retraining after each feedback submission:
- Non-blocking background check
- Doesn't slow down user feedback
- Logs all activities to `auto_retrain.log`

## Monitoring

Check logs:
```bash
tail -f backend/auto_retrain.log
```

Log entries include:
- Feedback collection stats
- Cleaning pipeline results
- Retrain trigger events
- Training progress
- Success/failure status

## Quality Metrics

The system tracks:
- **Total feedback:** All submissions
- **Clean pairs:** Passed validation
- **Approval rate:** % passing quality checks
- **Deduplication:** Unique pairs only
- **Training impact:** Pairs per retrain cycle

## Best Practices

1. **Let it run automatically** - The system handles everything
2. **Monitor logs** - Check for any issues
3. **Review stats periodically** - Ensure quality remains high
4. **Adjust threshold** - Based on feedback volume
5. **GPU recommended** - For faster retraining

## Troubleshooting

**Retraining not triggering:**
- Check `auto_retrain.log` for errors
- Verify threshold setting
- Ensure feedback file exists
- Check disk space for model storage

**Low approval rate:**
- Review quality criteria
- Check for spam/invalid submissions
- Adjust validation rules if needed

**Training failures:**
- Ensure GPU is available
- Check memory requirements
- Verify training data format
- Review `retrain_from_feedback.py` logs

## Files

- `auto_retrain.py` - Main automation script
- `feedback.jsonl` - Raw feedback storage
- `.last_retrain` - Retrain tracking
- `auto_retrain.log` - Activity logs
- `data/training/feedback_clean_approved.csv` - Exported clean pairs
