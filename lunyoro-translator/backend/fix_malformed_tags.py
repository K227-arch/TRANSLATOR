"""
fix_malformed_tags.py
=====================
Fixes malformed domain tags in train.csv and val.csv:
  [AGRCULTURE) -> [AGRICULTURE]
  [MIDICAL) -> [MEDICAL]
  [en do not... -> strip the malformed prefix
  [AGICAL] -> [AGRICULTURE]
  etc.

Also strips pairs where the English side is clearly garbage after stripping the tag.
"""
import re
import pandas as pd
from pathlib import Path

BASE      = Path(__file__).parent
TRAIN_CSV = BASE / "data" / "training" / "train.csv"
VAL_CSV   = BASE / "data" / "training" / "val.csv"

# Known malformed → correct mappings
TAG_FIXES = {
    r'AGRCULTURE':   'AGRICULTURE',
    r'AGICULTURE':   'AGRICULTURE',
    r'AGRICAL':      'AGRICULTURE',
    r'AGICAL':       'AGRICULTURE',
    r'MIDICAL':      'MEDICAL',
    r'MEDCAL':       'MEDICAL',
    r'MEDICALL':     'MEDICAL',
    r'REERAL':       'GENERAL',
    r'GENICAL':      'GENERAL',
    r'AGRICAL':      'AGRICULTURE',
    r'EDUCAION':     'EDUCATION',
    r'EDUCATON':     'EDUCATION',
    r'GOVERMENT':    'GOVERNANCE',
    r'GOVERNMET':    'GOVERNANCE',
    r'ENVIROMENT':   'NATURE_AND_ENVIRONMENT',
    r'ENVIROMENTAL': 'NATURE_AND_ENVIRONMENT',
}

# Regex to detect malformed tags: bracket not closed, wrong bracket type, etc.
MALFORMED_TAG_RE = re.compile(
    r'^\s*\[([A-Za-z0-9_ ]+)[)\]]\s*',  # [TAG] or [TAG) 
)
VALID_TAG_RE = re.compile(r'^\[[A-Z][A-Z0-9_]+\]\s')


def fix_tag(text: str) -> str:
    """Fix malformed domain tag in an English entry."""
    text = str(text).strip()
    
    # Match malformed opening bracket patterns
    m = MALFORMED_TAG_RE.match(text)
    if not m:
        return text
    
    tag_content = m.group(1).strip().upper().replace(' ', '_')
    rest = text[m.end():].strip()
    
    # Apply known fixes
    for wrong, correct in TAG_FIXES.items():
        tag_content = tag_content.replace(wrong.upper(), correct)
    
    # If rest is too short or looks like garbage, return just the rest
    if len(rest) < 4:
        return rest
    
    # Reconstruct with proper bracket format
    return f"[{tag_content}] {rest}"


def clean_df(df: pd.DataFrame, label: str) -> tuple[pd.DataFrame, dict]:
    stats = {'fixed_tags': 0, 'removed_garbage': 0}
    df = df.copy()
    
    # Fix malformed tags
    fixed_mask = df['english'].astype(str).str.contains(r'^\[[A-Za-z0-9_ ]+[)\]]', regex=True, na=False)
    if fixed_mask.any():
        df.loc[fixed_mask, 'english'] = df.loc[fixed_mask, 'english'].apply(fix_tag)
        stats['fixed_tags'] = fixed_mask.sum()
    
    # Remove pairs where English looks like garbage after stripping tag
    def strip_tag_for_check(t):
        return re.sub(r'^\[[A-Za-z0-9_ ]+\]\s*', '', str(t)).strip()
    
    en_clean = df['english'].apply(strip_tag_for_check)
    
    # Remove pairs where cleaned English starts with a lowercase letter and is < 10 chars
    # e.g. "[en do not weep" -> "do not weep" is valid, but "[en xyz" -> "xyz" is garbage
    garbage_mask = (
        (en_clean.str.len() < 4) |
        (en_clean.str.match(r'^[a-z]{1,2}\s+') & (en_clean.str.len() < 15))  # artifact like "en do..."
    )
    stats['removed_garbage'] = garbage_mask.sum()
    df = df[~garbage_mask]
    
    print(f"  {label}: fixed {stats['fixed_tags']:,} tags, removed {stats['removed_garbage']:,} garbage pairs")
    return df.reset_index(drop=True), stats


def main():
    print("=== Fixing malformed tags in training data ===\n")
    
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)
    print(f"Before: train={len(train):,}  val={len(val):,}")
    
    train_fixed, t_stats = clean_df(train, "train.csv")
    val_fixed,   v_stats = clean_df(val,   "val.csv")
    
    # Save backups
    import shutil
    shutil.copy(TRAIN_CSV, str(TRAIN_CSV) + ".bak_tagfix")
    shutil.copy(VAL_CSV,   str(VAL_CSV)   + ".bak_tagfix")
    
    train_fixed.to_csv(TRAIN_CSV, index=False)
    val_fixed.to_csv(VAL_CSV,     index=False)
    
    print(f"\nAfter:  train={len(train_fixed):,}  val={len(val_fixed):,}")
    print(f"Total fixed: {t_stats['fixed_tags'] + v_stats['fixed_tags']:,} tags")
    print(f"Total removed: {t_stats['removed_garbage'] + v_stats['removed_garbage']:,} garbage pairs")
    print("\nDone. Run analyze_bt_coverage.py to see updated candidates.")


if __name__ == "__main__":
    main()
