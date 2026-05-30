"""
clean_new_training_data.py
==========================
Cleans the newly added pairs in train.csv and val.csv:
  1. Remove too-short pairs (< 3 chars either side)
  2. Remove English-in-lunyoro passthrough pairs
  3. Remove very long pairs (> 500 chars)
  4. Remove HTML/artifact pairs
  5. Fix malformed domain tags ([AGICAL], [REERAL], [GENICAL] etc.)
  6. Strip duplicate/stacked domain tags
"""
import re
import pandas as pd
from pathlib import Path

TRAIN_CSV = Path('data/training/train.csv')
VAL_CSV   = Path('data/training/val.csv')

COMMON_EN = {'the','a','an','is','are','was','were','have','has','do','does',
             'will','would','can','could','should','may','might','to','of',
             'in','on','at','for','with','and','or','but','not','this','that',
             'it','he','she','they','we','you','i','my','your','his','her',
             'their','its','our','be','been','being','had','did','said'}

# Valid domain tags — anything else gets stripped
VALID_TAGS = re.compile(
    r'^\[('
    r'GENERAL|NOUN|VERB|ADJ|ADV|PRON|CONJ|PREP|INTERJ|NUM|'
    r'NOUN_PLURAL|GENERAL_NOUN|GENERAL_VERB|GENERAL_ADJ|GENERAL_ADV|'
    r'GENERAL_NOUN_PLURAL|COMMON_ANIMALS|COMMON_ANIMALS_NOUN|'
    r'COMMON_ANIMALS_NOUN_PLURAL|COMMON_ANIMALS_VERB|'
    r'HEALTH_AND_MEDICINE|HEALTH_AND_MEDICINE_NOUN|HEALTH_AND_MEDICINE_VERB|'
    r'NATURE_AND_ENVIRONMENT|NATURE_AND_ENVIRONMENT_NOUN|'
    r'GOVERNANCE_AND_ADMINISTRATION|GOVERNANCE_AND_ADMINISTRATION_NOUN|'
    r'CULTURE_AND_TRADITION|CULTURE_AND_TRADITION_NOUN|'
    r'BIOLOGY|BIOLOGY_NOUN|EDUCATION_AND_LEARNING|EDUCATION_AND_LEARNING_NOUN|'
    r'MILITARY|MILITARY_NOUN|GEOGRAPHY|GEOGRAPHY_NOUN|'
    r'MATHEMATICS|MATHEMATICS_NOUN|LEGAL_AND_LAW_MATTERS|'
    r'TRANSPORT|ECONOMICS_AND_COMMERCE|POLITICS_AND_CURRENT_AFFAIRS|'
    r'STORYTELLING_AND_NARRATIVES|HISTORY_AND_HISTORICAL_ACCOUNTS|'
    r'ASTRONOMY_AND_THE_UNIVERSE|TOURISM|SPORTS|CHEMISTRY|TECHNOLOGY|PHYSICS|'
    r'DICTIONARY|RELIGIOUS|MEDICAL|AGRICULTURE|EDUCATION|DAILY_LIFE|'
    r'LOW_FREQ|GENERAL_NOUN_VERB|GENERAL_VERB_NOUN'
    r')\]',
    re.IGNORECASE
)

def fix_domain_tags(text: str) -> str:
    """Strip malformed/stacked domain tags, keep only valid ones."""
    # Remove all [TAG] prefixes
    cleaned = re.sub(r'^\s*(\[[^\]]+\]\s*)+', '', text).strip()
    # Re-extract the first valid tag if present in original
    m = re.match(r'^\s*(\[[^\]]+\])', text)
    if m:
        tag = m.group(1)
        if VALID_TAGS.match(tag):
            return tag + ' ' + cleaned
    return cleaned


def is_english_passthrough(lun: str) -> bool:
    words = re.findall(r'[a-z]+', str(lun).lower())
    if not words or len(words) < 3:
        return False
    return sum(1 for w in words if w in COMMON_EN) / len(words) > 0.5


def clean_df(df: pd.DataFrame, label: str) -> pd.DataFrame:
    original = len(df)
    removed = {}

    # Fix domain tags first
    df['english'] = df['english'].apply(fix_domain_tags)

    # Remove too short
    mask_short = (df['english'].str.len() < 3) | (df['lunyoro'].str.len() < 3)
    removed['too_short'] = mask_short.sum()
    df = df[~mask_short]

    # Remove identical
    mask_ident = df['english'].str.lower().str.strip() == df['lunyoro'].str.lower().str.strip()
    removed['identical'] = mask_ident.sum()
    df = df[~mask_ident]

    # Remove English passthrough in lunyoro
    mask_en = df['lunyoro'].apply(is_english_passthrough)
    removed['en_passthrough'] = mask_en.sum()
    df = df[~mask_en]

    # Remove very long
    mask_long = (df['english'].str.len() > 500) | (df['lunyoro'].str.len() > 500)
    removed['too_long'] = mask_long.sum()
    df = df[~mask_long]

    # Remove HTML artifacts
    mask_html = (df['english'].str.contains(r'<[^>]+>|&[a-z]+;', regex=True, na=False) |
                 df['lunyoro'].str.contains(r'<[^>]+>|&[a-z]+;', regex=True, na=False))
    removed['html_artifacts'] = mask_html.sum()
    df = df[~mask_html]

    # Remove NaN
    df = df.dropna(subset=['english', 'lunyoro'])
    df = df[df['english'].str.strip().ne('') & df['lunyoro'].str.strip().ne('')]

    total_removed = original - len(df)
    print(f"\n{label}: {original:,} → {len(df):,}  (removed {total_removed:,})")
    for k, v in removed.items():
        if v > 0:
            print(f"  {k}: {v:,}")

    return df.reset_index(drop=True)


def main():
    print("=== Cleaning training data ===")

    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)

    train_clean = clean_df(train, "train.csv")
    val_clean   = clean_df(val,   "val.csv")

    # Backup originals
    import shutil
    shutil.copy(TRAIN_CSV, str(TRAIN_CSV) + ".bak2")
    shutil.copy(VAL_CSV,   str(VAL_CSV)   + ".bak2")

    train_clean.to_csv(TRAIN_CSV, index=False)
    val_clean.to_csv(VAL_CSV,     index=False)

    print(f"\nFinal: train={len(train_clean):,}  val={len(val_clean):,}  total={len(train_clean)+len(val_clean):,}")
    print("Saved. Ready to train.")


if __name__ == "__main__":
    main()
