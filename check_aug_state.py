import pandas as pd
from pathlib import Path

BASE  = Path('lunyoro-translator/backend')
DATA  = BASE / 'data' / 'training'
CLEAN = BASE / 'data' / 'cleaned'

train = pd.read_csv(DATA / 'train.csv')
val   = pd.read_csv(DATA / 'val.csv')
new_t = pd.read_csv(DATA / 'new_only_train.csv')
bt    = pd.read_csv(CLEAN / 'back_translated_lun2en.csv')
aug   = pd.read_csv(CLEAN / 'augmented_bt_lun2en_clean.csv')

print('=== CURRENT TRAINING DATA ===')
print(f'train.csv:               {len(train):,}')
print(f'val.csv:                 {len(val):,}')
print(f'new_only_train.csv:      {len(new_t):,}')
print()

print('=== AUGMENTED / BT FILES ===')
files = {
    'back_translated_lun2en.csv':       (CLEAN / 'back_translated_lun2en.csv',    'lun2en BT'),
    'augmented_bt_lun2en_clean.csv':    (CLEAN / 'augmented_bt_lun2en_clean.csv', 'lun2en augmented (clean)'),
    'augmented_pos_pairs.csv':          (CLEAN / 'augmented_pos_pairs.csv',        'en2lun POS/plural/verb'),
    'gr_grammar_pairs.csv':             (CLEAN / 'gr_grammar_pairs.csv',           'grammar rule pairs'),
    'gr4_pairs.csv':                    (CLEAN / 'gr4_pairs.csv',                  'grammar rules 4'),
    'gr5_pairs.csv':                    (CLEAN / 'gr5_pairs.csv',                  'grammar rules 5'),
    'gr5_uncovered_pairs.csv':          (CLEAN / 'gr5_uncovered_pairs.csv',        'gr5 uncovered'),
}
for name, (path, label) in files.items():
    if path.exists():
        df = pd.read_csv(path)
        print(f'  {name:<40} {len(df):>7,}  ({label})')
    else:
        print(f'  {name:<40} NOT FOUND')

print()
print('=== COVERAGE CHECK: what is in train.csv ===')
train_keys = set(zip(
    train['english'].astype(str).str.lower().str.strip(),
    train['lunyoro'].astype(str).str.lower().str.strip()
))
val_keys = set(zip(
    val['english'].astype(str).str.lower().str.strip(),
    val['lunyoro'].astype(str).str.lower().str.strip()
))
all_keys = train_keys | val_keys

def check_coverage(path, label):
    if not path.exists():
        return
    df = pd.read_csv(path)
    total = len(df)
    in_train = sum(1 for _, r in df.iterrows()
                   if (str(r.get('english','')).lower().strip(),
                       str(r.get('lunyoro','')).lower().strip()) in all_keys)
    pct = round(100 * in_train / max(total, 1))
    print(f'  {label:<45} {in_train:>6,}/{total:>6,}  ({pct}% in training)')

check_coverage(CLEAN / 'back_translated_lun2en.csv',    'back_translated_lun2en')
check_coverage(CLEAN / 'augmented_bt_lun2en_clean.csv', 'augmented_bt_lun2en_clean')
check_coverage(CLEAN / 'augmented_pos_pairs.csv',       'augmented_pos_pairs (en2lun)')
check_coverage(CLEAN / 'gr_grammar_pairs.csv',          'gr_grammar_pairs')

print()
print('=== MODELS TRAINED ON WHAT ===')
print('MarianMT en2lun: trained on full train.csv (308k pairs)')
print('MarianMT lun2en: trained on new_only (131k) = BT + augmented + fixes')
print('NLLB    en2lun:  trained on full train.csv (308k pairs)')
print('NLLB    lun2en:  trained on new_only (131k) = BT + augmented + fixes')
print()
print('=== UNTRAINED AUGMENTED DATA ===')
bt_df = pd.read_csv(CLEAN / 'back_translated_lun2en.csv')
aug_df = pd.read_csv(CLEAN / 'augmented_bt_lun2en_clean.csv')
not_in_train_bt  = sum(1 for _, r in bt_df.iterrows()
    if (str(r['english']).lower().strip(), str(r['lunyoro']).lower().strip()) not in all_keys)
not_in_train_aug = sum(1 for _, r in aug_df.iterrows()
    if (str(r['english']).lower().strip(), str(r['lunyoro']).lower().strip()) not in all_keys)
print(f'BT pairs NOT yet in training:          {not_in_train_bt:,}')
print(f'Augmented pairs NOT yet in training:   {not_in_train_aug:,}')
