"""
Full pipeline for the dictionary data:
  Step 1 — Clean:          Fix OCR noise, apply orthographic rules
  Step 2 — Augment:        Generate verb form pairs from structured entries
  Step 3 — Back-translate: Run Runyoro examples through lun2en model
  Step 4 — Merge:          Combine with existing training data, rebuild splits
  Step 5 — Retrain:        Fine-tune MarianMT en2lun + lun2en from checkpoint
  Step 6 — Push to Hub:    Upload retrained MarianMT models to HuggingFace
  Step 7 — Retrain NLLB:   Fine-tune NLLB en2lun + lun2en from checkpoint
  Step 8 — Rebuild index:  Regenerate semantic search index

Usage:
  python dictionary_pipeline.py
  python dictionary_pipeline.py --skip-train      # steps 1-4 only
  python dictionary_pipeline.py --skip-backtrans  # skip back-translation (faster)
  python dictionary_pipeline.py --skip-nllb       # skip NLLB retraining
"""

import os, re, csv, sys, argparse, random, logging
import pandas as pd
import numpy as np

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables being set externally

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_DIR  = os.path.dirname(__file__)
DICT_DIR  = os.path.join(BASE_DIR, "data", "dictionary")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
TRAIN_DIR = os.path.join(BASE_DIR, "data", "training")
MODEL_DIR = os.path.join(BASE_DIR, "model")

# ── Orthographic normalisation (mirrors prepare_training_data.py logic) ──────

_APOSTROPHE_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201C": '"', "\u201D": '"',
    "\u02BC": "'", "\u0060": "'",
})

def _norm_apostrophe(text: str) -> str:
    return text.translate(_APOSTROPHE_MAP)

def _nasal_assimilation(text: str) -> str:
    for src, tgt in [("nb","mb"),("np","mp"),("nr","nd"),("nl","nd"),("nm","mm")]:
        text = re.sub(src, tgt, text, flags=re.IGNORECASE)
    return text

def _ni_prefix(text: str) -> str:
    for src, tgt in [("nimu","numu"),("nigu","nugu"),("niru","nuru"),
                     ("nibu","nubu"),("nikw","nukw")]:
        text = re.sub(r'\b' + src, tgt, text, flags=re.IGNORECASE)
    return text

def _rl_rule(text: str) -> str:
    chars = list(text)
    out = []
    for i, ch in enumerate(chars):
        if ch not in ('l','L'):
            out.append(ch); continue
        prev = chars[i-1].lower() if i > 0 else ''
        nxt  = chars[i+1].lower() if i < len(chars)-1 else ''
        if prev in ('e','i') or nxt in ('e','i'):
            out.append(ch)
        else:
            out.append('R' if ch.isupper() else 'r')
    return ''.join(out)

def normalise_lunyoro(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = _norm_apostrophe(text.strip())
    text = _nasal_assimilation(text)
    text = _ni_prefix(text)
    text = _rl_rule(text)
    return text

# OCR noise patterns
_OCR_FIXES = [
    (r'\b11-', 'n-'),          # 11- -> n-
    (r'\b1 ', 'l '),           # 1 word -> l word
    (r'(?<=[a-z])1(?=[a-z])', 'l'),  # mid-word 1 -> l
    (r'\bI(?=[a-z])', 'l'),    # capital I mid-word -> l
    (r'\bIi\b', 'li'),
    (r'\s+', ' '),             # collapse whitespace
    (r'\{', '('), (r'\}', ')'),# curly braces -> parens
    (r'(?<=[a-z])11(?=[a-z])', 'll'),  # double 1 -> ll
]

def fix_ocr(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    for pattern, repl in _OCR_FIXES:
        text = re.sub(pattern, repl, text)
    return text.strip()

# ── STEP 1: CLEAN ─────────────────────────────────────────────────────────────

def step_clean():
    log.info("=== STEP 1: Cleaning dictionary Excel files ===")

    # Load all three Excel files
    pairs_df   = pd.read_excel(os.path.join(DICT_DIR, "dictionary_pairs.xlsx"))
    en_rn_df   = pd.read_excel(os.path.join(DICT_DIR, "english_runyoro_dict.xlsx"))
    rn_en_df   = pd.read_excel(os.path.join(DICT_DIR, "runyoro_english_dict.xlsx"))

    log.info(f"  Loaded: pairs={len(pairs_df)}, en_rn={len(en_rn_df)}, rn_en={len(rn_en_df)}")

    # --- Clean dictionary_pairs ---
    pairs_df["english"] = pairs_df["english"].apply(lambda x: fix_ocr(str(x)) if pd.notna(x) else "")
    pairs_df["lunyoro"] = pairs_df["lunyoro"].apply(lambda x: normalise_lunyoro(fix_ocr(str(x))) if pd.notna(x) else "")

    # Filter: remove rows where either side is too short, too long, or looks like noise
    def is_valid_pair(row):
        en = str(row.get("english","")).strip()
        lu = str(row.get("lunyoro","")).strip()
        if len(en) < 2 or len(lu) < 2:
            return False
        if len(en) > 300 or len(lu) > 200:
            return False
        # English side should not be all Runyoro
        if re.search(r'\b(oku|okw|omu|aba|obu|ema|emi|ebi|eki|aka|ama|oru|en|em)\w{2,}', en):
            if not re.search(r'\b(the|a|an|is|are|to|of|in|he|she|it|they|we|you)\b', en, re.I):
                return False
        # Lunyoro side should not be pure English
        if re.search(r'\b(the|a|an|is|are|was|were|to|of|in|he|she|it|they|we)\b', lu, re.I):
            if len(lu.split()) > 3:
                return False
        # Remove grammar notation leakage
        if re.search(r'\b(pf\.|pr\. form|c\. form|pass\. form|cl\.\d|v\.i\.|v\.tr\.)\b', en+lu):
            return False
        return True

    before = len(pairs_df)
    pairs_df = pairs_df[pairs_df.apply(is_valid_pair, axis=1)].reset_index(drop=True)
    log.info(f"  Pairs after cleaning: {len(pairs_df)} (removed {before - len(pairs_df)})")

    # Deduplicate
    pairs_df = pairs_df.drop_duplicates(subset=["english","lunyoro"]).reset_index(drop=True)
    log.info(f"  Pairs after dedup: {len(pairs_df)}")

    # --- Clean english_runyoro_dict ---
    en_rn_df["english_word"]        = en_rn_df["english_word"].apply(lambda x: fix_ocr(str(x)).strip() if pd.notna(x) else "")
    en_rn_df["runyoro_equivalents"] = en_rn_df["runyoro_equivalents"].apply(
        lambda x: normalise_lunyoro(fix_ocr(str(x))) if pd.notna(x) else "")
    en_rn_df = en_rn_df[en_rn_df["english_word"].str.len() > 1].reset_index(drop=True)

    # --- Clean runyoro_english_dict ---
    rn_en_df["runyoro_word"]        = rn_en_df["runyoro_word"].apply(
        lambda x: normalise_lunyoro(fix_ocr(str(x))) if pd.notna(x) else "")
    rn_en_df["definition_english"]  = rn_en_df["definition_english"].apply(
        lambda x: fix_ocr(str(x)).strip() if pd.notna(x) else "")
    rn_en_df["example"]             = rn_en_df["example"].apply(
        lambda x: fix_ocr(str(x)).strip() if pd.notna(x) else "")
    rn_en_df = rn_en_df[rn_en_df["runyoro_word"].str.len() > 1].reset_index(drop=True)

    # Save cleaned versions
    pairs_df.to_excel(os.path.join(DICT_DIR, "dictionary_pairs_clean.xlsx"), index=False)
    en_rn_df.to_excel(os.path.join(DICT_DIR, "english_runyoro_dict_clean.xlsx"), index=False)
    rn_en_df.to_excel(os.path.join(DICT_DIR, "runyoro_english_dict_clean.xlsx"), index=False)

    log.info(f"  Saved cleaned files to {DICT_DIR}")
    return pairs_df, en_rn_df, rn_en_df


# ── POST-STEP CLEANING ────────────────────────────────────────────────────────

# Quality thresholds
MIN_EN_LEN  = 3
MAX_EN_LEN  = 300
MIN_LUN_LEN = 2
MAX_LUN_LEN = 200

# Patterns that indicate the pair is noise
_NOISE_PATTERNS = re.compile(
    r'\b(pf\.|pr\. form|c\. form|pass\. form|cl\.\d|v\.i\.|v\.tr\.|v\.c\.|'
    r'v\.pass\.|v\.refl\.|n\. cl\.|pl\. nil|pl\. same|okw-|kw-|oku-\s*,)\b',
    re.I
)
_ENGLISH_MARKERS = re.compile(
    r'\b(the|a|an|is|are|was|were|to|of|in|he|she|it|they|we|you|I|'
    r'his|her|their|this|that|which|who|when|where|how|what|will|would|'
    r'have|has|had|be|been|being|do|does|did|not|and|or|but|if|so)\b',
    re.I
)
_RUNYORO_MARKERS = re.compile(
    r'\b(oku|okw|omu|aba|obu|ema|emi|ebi|eki|aka|ama|oru|en|em)\w{2,}', re.I
)

def clean_pairs_df(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Quality-filter a DataFrame with 'english' and 'lunyoro' columns.
    Applied after augmentation and back-translation.
    """
    before = len(df)

    def is_valid(row):
        en = str(row.get("english", "")).strip()
        lu = str(row.get("lunyoro", "")).strip()

        # Length checks
        if len(en) < MIN_EN_LEN or len(lu) < MIN_LUN_LEN:
            return False
        if len(en) > MAX_EN_LEN or len(lu) > MAX_LUN_LEN:
            return False

        # Grammar notation leakage
        if _NOISE_PATTERNS.search(en) or _NOISE_PATTERNS.search(lu):
            return False

        # English side must look like English (contain at least one English word)
        if not _ENGLISH_MARKERS.search(en):
            # Allow short single-word English entries (e.g. "abandon")
            if len(en.split()) > 2:
                return False

        # Lunyoro side must not be pure English prose
        if _ENGLISH_MARKERS.search(lu) and len(lu.split()) > 3:
            # Allow if it also has Runyoro markers
            if not _RUNYORO_MARKERS.search(lu):
                return False

        # English side should not be all Runyoro (swapped pair)
        if _RUNYORO_MARKERS.search(en) and not _ENGLISH_MARKERS.search(en):
            return False

        # Round-trip sanity: English and Lunyoro should not be identical
        if en.lower().strip() == lu.lower().strip():
            return False

        # Reject if either side is just punctuation/numbers
        if not re.search(r'[a-zA-Z]{2,}', en):
            return False
        if not re.search(r'[a-zA-Z]{2,}', lu):
            return False

        return True

    df = df[df.apply(is_valid, axis=1)].reset_index(drop=True)

    # Apply orthographic normalisation to Lunyoro side
    df["lunyoro"] = df["lunyoro"].apply(normalise_lunyoro)

    # Deduplicate
    df = df.drop_duplicates(subset=["english", "lunyoro"]).reset_index(drop=True)

    log.info(f"  [{label}] cleaned: {before} → {len(df)} pairs (removed {before - len(df)})")
    return df


# ── STEP 2: AUGMENT ───────────────────────────────────────────────────────────

# Verb derivative suffixes for augmentation
_DERIV = {
    "causative":  [("a","isa"), ("a","esa"), ("a","ya")],
    "passive":    [("a","ibwa"), ("a","ebwa")],
    "reciprocal": [("a","ana")],
    "reversive":  [("a","ura"), ("a","ora")],
}

_DERIV_LABELS = {
    "causative":  "to cause to {}",
    "passive":    "to be {}ed",
    "reciprocal": "to {} each other",
    "reversive":  "to undo/reverse {}ing",
}

def _make_derivative(stem: str, form: str) -> str | None:
    """Build a derivative verb form from a Runyoro verb stem."""
    stem = stem.strip().rstrip('a')  # strip trailing -a
    if not stem:
        return None
    for src_end, tgt_end in _DERIV.get(form, []):
        return f"oku{stem}{tgt_end}"
    return None

def step_augment(rn_en_df: pd.DataFrame) -> pd.DataFrame:
    log.info("=== STEP 2: Augmenting with derivative verb forms ===")
    new_pairs = []

    for _, row in rn_en_df.iterrows():
        word = str(row.get("runyoro_word","")).strip()
        defn = str(row.get("definition_english","")).strip()
        pos  = str(row.get("pos","")).strip().lower()

        if not word or not defn or len(defn) < 5:
            continue

        # Only augment verbs (infinitive form starts with oku/okw)
        if not (word.startswith("oku") or word.startswith("okw") or "v." in pos):
            continue

        # Base pair: definition → word
        base_en = defn.split('.')[0].strip()
        if len(base_en) > 5:
            new_pairs.append({"english": base_en, "lunyoro": word, "source": "dict_augment_base"})

        # Stem = word without oku/okw prefix and trailing -a
        stem = re.sub(r'^(oku|okw)', '', word).rstrip('a')
        if len(stem) < 2:
            continue

        # Generate derivative forms
        for form, label in _DERIV_LABELS.items():
            deriv_word = f"oku{stem}"
            if form == "causative":
                deriv_word = f"oku{stem}isa"
                deriv_en   = label.format(base_en.lower().lstrip("to "))
            elif form == "passive":
                deriv_word = f"oku{stem}ibwa"
                deriv_en   = label.format(base_en.lower().lstrip("to "))
            elif form == "reciprocal":
                deriv_word = f"oku{stem}ana"
                deriv_en   = label.format(base_en.lower().lstrip("to "))
            elif form == "reversive":
                deriv_word = f"oku{stem}ura"
                deriv_en   = label.format(base_en.lower().lstrip("to "))
            else:
                continue

            deriv_word = normalise_lunyoro(deriv_word)
            if len(deriv_word) > 4 and len(deriv_en) > 5:
                new_pairs.append({
                    "english": deriv_en,
                    "lunyoro": deriv_word,
                    "source":  f"dict_augment_{form}",
                })

    aug_df = pd.DataFrame(new_pairs).drop_duplicates(subset=["english","lunyoro"])
    log.info(f"  Generated {len(aug_df)} augmented pairs (before cleaning)")

    # Clean augmented pairs
    aug_df = clean_pairs_df(aug_df, "augmented")

    aug_df.to_excel(os.path.join(DICT_DIR, "dictionary_augmented.xlsx"), index=False)
    return aug_df


# ── STEP 3: BACK-TRANSLATE ────────────────────────────────────────────────────

def step_backtranslate(rn_en_df: pd.DataFrame) -> pd.DataFrame:
    log.info("=== STEP 3: Back-translating Runyoro examples via lun2en model ===")

    # Load the lun2en model
    try:
        from transformers import MarianMTModel, MarianTokenizer
        import torch
        lun2en_path = os.path.join(MODEL_DIR, "lun2en")
        tokenizer = MarianTokenizer.from_pretrained(lun2en_path)
        model     = MarianMTModel.from_pretrained(lun2en_path)
        model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        log.info(f"  Loaded lun2en model on {device}")
    except Exception as e:
        log.warning(f"  Could not load lun2en model: {e}. Skipping back-translation.")
        return pd.DataFrame(columns=["english","lunyoro","source"])

    def translate_batch(texts, batch_size=32):
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            inputs = tokenizer(batch, return_tensors="pt", truncation=True,
                               max_length=256, padding=True).to(device)
            with torch.no_grad():
                out = model.generate(**inputs, num_beams=4, max_length=256,
                                     early_stopping=True, no_repeat_ngram_size=3)
            decoded = [tokenizer.decode(o, skip_special_tokens=True) for o in out]
            results.extend(decoded)
        return results

    # Collect Runyoro example sentences from the dictionary
    runyoro_examples = []
    for _, row in rn_en_df.iterrows():
        example = str(row.get("example","")).strip()
        if not example or example == "nan" or len(example) < 10:
            continue
        # Split on semicolons to get individual sentences
        for sent in example.split(';'):
            sent = sent.strip()
            if len(sent) > 8 and len(sent) < 200:
                # Take the Runyoro part (before comma if it's a pair)
                parts = sent.split(',', 1)
                lun_sent = parts[0].strip()
                if len(lun_sent) > 8:
                    runyoro_examples.append(lun_sent)

    # Deduplicate
    runyoro_examples = list(dict.fromkeys(runyoro_examples))
    log.info(f"  Found {len(runyoro_examples)} Runyoro example sentences to back-translate")

    if not runyoro_examples:
        return pd.DataFrame(columns=["english","lunyoro","source"])

    # Translate in batches
    log.info("  Translating...")
    english_translations = translate_batch(runyoro_examples)

    # Build pairs — filter out bad translations
    bt_pairs = []
    for lun, eng in zip(runyoro_examples, english_translations):
        if not eng or len(eng) < 5:
            continue
        # Basic quality check: English translation should look like English
        if not re.search(r'\b(the|a|an|is|are|to|of|in|he|she|it|they|we|you|I)\b', eng, re.I):
            continue
        # Normalise Runyoro
        lun_norm = normalise_lunyoro(lun)
        bt_pairs.append({
            "english": eng.strip(),
            "lunyoro": lun_norm,
            "source":  "dict_backtranslated",
        })

    bt_df = pd.DataFrame(bt_pairs).drop_duplicates(subset=["english","lunyoro"])
    log.info(f"  Back-translated {len(bt_df)} pairs (before cleaning)")

    # Clean back-translated pairs — stricter than augmented since model can hallucinate
    bt_df = clean_pairs_df(bt_df, "back-translated")

    # Additional back-translation specific checks:
    # 1. Reject if English translation is too similar to the Runyoro input (model copied input)
    # 2. Reject if English output is suspiciously short relative to Runyoro input
    def bt_quality(row):
        en = str(row.get("english","")).strip().lower()
        lu = str(row.get("lunyoro","")).strip().lower()
        # Reject if >60% of Runyoro tokens appear verbatim in English (copy failure)
        lu_tokens = set(re.findall(r'[a-z]{3,}', lu))
        en_tokens = set(re.findall(r'[a-z]{3,}', en))
        if lu_tokens and len(lu_tokens & en_tokens) / len(lu_tokens) > 0.6:
            return False
        # Reject very short English for long Runyoro (likely truncated)
        if len(lu.split()) > 6 and len(en.split()) < 3:
            return False
        return True

    before_bt = len(bt_df)
    bt_df = bt_df[bt_df.apply(bt_quality, axis=1)].reset_index(drop=True)
    log.info(f"  [back-translated] after quality filter: {len(bt_df)} (removed {before_bt - len(bt_df)})")

    bt_df.to_excel(os.path.join(DICT_DIR, "dictionary_backtranslated.xlsx"), index=False)
    return bt_df


# ── STEP 4: MERGE & REBUILD SPLITS ───────────────────────────────────────────

def step_merge(pairs_df, aug_df, bt_df):
    log.info("=== STEP 4: Merging with existing training data ===")

    # Load existing training corpus
    existing_path = os.path.join(CLEAN_DIR, "english_nyoro_clean.csv")
    existing_df   = pd.read_csv(existing_path, encoding="utf-8")
    log.info(f"  Existing corpus: {len(existing_df)} pairs")

    # Combine all new pairs
    all_new = pd.concat([pairs_df, aug_df, bt_df], ignore_index=True)
    all_new = all_new[["english","lunyoro"]].rename(columns={"lunyoro":"lunyoro"})

    # Add domain tag [DICTIONARY] to new pairs for traceability in the CSV
    # but strip it before training so the model never sees it
    all_new["english"] = "[DICTIONARY] " + all_new["english"].astype(str)

    # Rename to match existing schema (english, lunyoro)
    all_new.columns = ["english", "lunyoro"]

    # Merge with existing
    combined = pd.concat([existing_df, all_new], ignore_index=True)

    # Deduplicate on (english, lunyoro)
    combined = combined.drop_duplicates(subset=["english","lunyoro"]).reset_index(drop=True)
    log.info(f"  Combined corpus: {len(combined)} pairs (+{len(combined)-len(existing_df)} new)")

    # Save updated corpus
    combined.to_csv(existing_path, index=False, encoding="utf-8")
    log.info(f"  Saved updated corpus → {existing_path}")

    # Rebuild train/val/test splits (90/5/5)
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    n = len(combined)
    n_val  = max(500, int(n * 0.05))
    n_test = max(500, int(n * 0.05))
    n_train = n - n_val - n_test

    train_df = combined.iloc[:n_train]
    val_df   = combined.iloc[n_train:n_train+n_val]
    test_df  = combined.iloc[n_train+n_val:]

    train_df.to_csv(os.path.join(TRAIN_DIR, "train.csv"), index=False, encoding="utf-8")
    val_df.to_csv(os.path.join(TRAIN_DIR, "val.csv"),   index=False, encoding="utf-8")
    test_df.to_csv(os.path.join(TRAIN_DIR, "test.csv"), index=False, encoding="utf-8")

    log.info(f"  Rebuilt splits: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")
    return len(combined)


# ── STEP 5: RETRAIN (from checkpoint, not from scratch) ──────────────────────

def step_retrain(direction: str, epochs: int = 5, batch_size: int = 32, lr: float = 1e-5):
    """Fine-tune a MarianMT model from its existing checkpoint."""
    log.info(f"=== STEP 5: Retraining MarianMT {direction} (from checkpoint) ===")

    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import MarianMTModel, MarianTokenizer
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import CosineAnnealingLR

    model_path = os.path.join(MODEL_DIR, direction)
    if not os.path.isdir(model_path):
        log.error(f"  Model not found at {model_path}. Cannot retrain.")
        return

    # Load tokenizer and model from existing checkpoint
    tokenizer = MarianTokenizer.from_pretrained(model_path)
    model     = MarianMTModel.from_pretrained(model_path)
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    log.info(f"  Loaded checkpoint from {model_path} on {device}")

    # Load training data
    train_df = pd.read_csv(os.path.join(TRAIN_DIR, "train.csv"), encoding="utf-8")
    val_df   = pd.read_csv(os.path.join(TRAIN_DIR, "val.csv"),   encoding="utf-8")

    # Strip domain tags for training
    def strip_tag(text):
        return re.sub(r'^\[.*?\]\s*', '', str(text)).strip()

    if direction == "en2lun":
        src_col, tgt_col = "english", "lunyoro"
    else:
        src_col, tgt_col = "lunyoro", "english"

    train_src = [strip_tag(x) for x in train_df[src_col].fillna("").tolist()]
    train_tgt = [strip_tag(x) for x in train_df[tgt_col].fillna("").tolist()]
    val_src   = [strip_tag(x) for x in val_df[src_col].fillna("").tolist()]
    val_tgt   = [strip_tag(x) for x in val_df[tgt_col].fillna("").tolist()]

    # Filter empty pairs
    train_pairs = [(s,t) for s,t in zip(train_src, train_tgt) if s.strip() and t.strip()]
    val_pairs   = [(s,t) for s,t in zip(val_src,   val_tgt)   if s.strip() and t.strip()]
    log.info(f"  Training pairs: {len(train_pairs)}, Val pairs: {len(val_pairs)}")

    class TranslationDataset(Dataset):
        def __init__(self, pairs):
            self.pairs = pairs
        def __len__(self):
            return len(self.pairs)
        def __getitem__(self, idx):
            return self.pairs[idx]

    def collate(batch):
        srcs, tgts = zip(*batch)
        enc = tokenizer(list(srcs), return_tensors="pt", truncation=True,
                        max_length=256, padding=True)
        dec = tokenizer(text_target=list(tgts), return_tensors="pt", truncation=True,
                        max_length=256, padding=True)
        labels = dec["input_ids"].clone()
        labels[labels == tokenizer.pad_token_id] = -100
        return {**enc, "labels": labels}

    train_loader = DataLoader(TranslationDataset(train_pairs), batch_size=batch_size,
                              shuffle=True, collate_fn=collate)
    val_loader   = DataLoader(TranslationDataset(val_pairs),   batch_size=batch_size,
                              shuffle=False, collate_fn=collate)

    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs * len(train_loader))

    # Save checkpoints to a temp dir so the live model is never touched mid-training
    import shutil, tempfile
    tmp_ckpt = os.path.join(MODEL_DIR, f"_{direction}_training_tmp")
    os.makedirs(tmp_ckpt, exist_ok=True)
    log.info(f"  Checkpoints will be saved to {tmp_ckpt} (live model untouched until done)")

    best_val_loss = float("inf")
    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        total_loss = 0
        for step, batch in enumerate(train_loader):
            batch = {k: v.to(device) for k, v in batch.items()}
            out   = model(**batch)
            loss  = out.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            total_loss += loss.item()
            if step % 200 == 0:
                log.info(f"  Epoch {epoch}/{epochs} step {step}/{len(train_loader)} "
                         f"loss={loss.item():.4f}")

        avg_train = total_loss / len(train_loader)

        # Validate
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                val_loss += model(**batch).loss.item()
        avg_val = val_loss / len(val_loader)
        log.info(f"  Epoch {epoch}: train_loss={avg_train:.4f}  val_loss={avg_val:.4f}")

        # Save best checkpoint to temp dir only
        if avg_val < best_val_loss:
            best_val_loss = avg_val
            model.save_pretrained(tmp_ckpt)
            tokenizer.save_pretrained(tmp_ckpt)
            log.info(f"  Saved best checkpoint to tmp (val_loss={best_val_loss:.4f})")

    # Training done — atomically replace live model with best checkpoint
    log.info(f"  Copying best checkpoint → {model_path} (replacing live model now)")
    shutil.copytree(tmp_ckpt, model_path, dirs_exist_ok=True)
    shutil.rmtree(tmp_ckpt, ignore_errors=True)
    log.info(f"  Retraining complete for {direction}. Best val_loss={best_val_loss:.4f}")

    # Push to HuggingFace in a background thread so GPU is free for next model
    repo_id = HF_REPOS.get(direction)
    if repo_id:
        hf_token = os.environ.get("HF_TOKEN", "").strip()
        if not hf_token:
            log.warning(f"  HF_TOKEN not set — skipping push for {direction}")
        else:
            import threading
            def _push(dir_=direction, repo_=repo_id, path_=model_path, loss_=best_val_loss, tok_=hf_token):
                try:
                    from huggingface_hub import HfApi
                    log.info(f"  [bg] Pushing {dir_} → {repo_} (CPU, background) ...")
                    HfApi(token=tok_).upload_folder(
                        folder_path=path_,
                        repo_id=repo_,
                        repo_type="model",
                        commit_message=f"Retrained {dir_} on cleaned + augmented + back-translated data (val_loss={loss_:.4f})",
                    )
                    log.info(f"  [bg] ✓ {dir_} pushed to {repo_}")
                except Exception as e:
                    log.error(f"  [bg] Push failed for {dir_}: {e}")
            t = threading.Thread(target=_push, daemon=True)
            t.start()
            log.info(f"  Push for {direction} started in background — continuing to next model")


# ── STEP 6: PUSH TO HUGGING FACE ─────────────────────────────────────────────

HF_REPOS = {
    "en2lun":      "keithtwesigye/lunyoro-en2lun",
    "lun2en":      "keithtwesigye/lunyoro-lun2en",
    "nllb_en2lun": "keithtwesigye/lunyoro-nllb_en2lun",
    "nllb_lun2en": "keithtwesigye/lunyoro-nllb_lun2en",
}

def step_push_to_hub():
    log.info("=== STEP 6: Pushing models to HuggingFace Hub ===")

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        log.error("  HF_TOKEN not set in environment. Skipping push.")
        return

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
    except ImportError:
        log.error("  huggingface_hub not installed. Run: pip install huggingface_hub")
        return

    for direction, repo_id in HF_REPOS.items():
        model_path = os.path.join(MODEL_DIR, direction)
        if not os.path.isdir(model_path):
            log.warning(f"  Model dir not found: {model_path} — skipping {direction}")
            continue

        log.info(f"  Uploading {direction} → {repo_id} (via Git LFS) ...")
        try:
            api.upload_folder(
                folder_path=model_path,
                repo_id=repo_id,
                repo_type="model",
                commit_message="Retrained on cleaned + augmented + back-translated dictionary data",
            )
            log.info(f"  ✓ {direction} pushed to {repo_id}")
        except Exception as e:
            log.error(f"  Failed to push {direction}: {e}")


# ── STEP 7: RETRAIN NLLB ─────────────────────────────────────────────────────

# NLLB uses run_Latn (Rundi) as the closest proxy for Runyoro-Rutooro
NLLB_SRC_LANG = {"en2lun": "eng_Latn", "lun2en": "run_Latn"}
NLLB_TGT_LANG = {"en2lun": "run_Latn", "lun2en": "eng_Latn"}

def step_retrain_nllb(direction: str, epochs: int = 5, batch_size: int = 16, lr: float = 5e-6):
    """Fine-tune an NLLB-200 model from its existing checkpoint."""
    log.info(f"=== STEP 7: Retraining NLLB {direction} (from checkpoint) ===")

    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import NllbTokenizer, AutoModelForSeq2SeqLM
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import CosineAnnealingLR

    model_path = os.path.join(MODEL_DIR, f"nllb_{direction}")
    if not os.path.isdir(model_path):
        log.error(f"  Model not found at {model_path}. Cannot retrain.")
        return

    src_lang = NLLB_SRC_LANG[direction]
    tgt_lang = NLLB_TGT_LANG[direction]

    tokenizer = NllbTokenizer.from_pretrained(model_path, src_lang=src_lang)
    model     = AutoModelForSeq2SeqLM.from_pretrained(model_path)
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    log.info(f"  Loaded NLLB checkpoint from {model_path} on {device}")
    log.info(f"  src_lang={src_lang}  tgt_lang={tgt_lang}")

    # Load training data
    train_df = pd.read_csv(os.path.join(TRAIN_DIR, "train.csv"), encoding="utf-8")
    val_df   = pd.read_csv(os.path.join(TRAIN_DIR, "val.csv"),   encoding="utf-8")

    def strip_tag(text):
        return re.sub(r'^\[.*?\]\s*', '', str(text)).strip()

    if direction == "en2lun":
        src_col, tgt_col = "english", "lunyoro"
    else:
        src_col, tgt_col = "lunyoro", "english"

    train_src = [strip_tag(x) for x in train_df[src_col].fillna("").tolist()]
    train_tgt = [strip_tag(x) for x in train_df[tgt_col].fillna("").tolist()]
    val_src   = [strip_tag(x) for x in val_df[src_col].fillna("").tolist()]
    val_tgt   = [strip_tag(x) for x in val_df[tgt_col].fillna("").tolist()]

    train_pairs = [(s, t) for s, t in zip(train_src, train_tgt) if s.strip() and t.strip()]
    val_pairs   = [(s, t) for s, t in zip(val_src,   val_tgt)   if s.strip() and t.strip()]
    log.info(f"  Training pairs: {len(train_pairs)}, Val pairs: {len(val_pairs)}")

    tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang)

    class TranslationDataset(Dataset):
        def __init__(self, pairs): self.pairs = pairs
        def __len__(self):         return len(self.pairs)
        def __getitem__(self, idx): return self.pairs[idx]

    def collate(batch):
        srcs, tgts = zip(*batch)
        tokenizer.src_lang = src_lang
        enc = tokenizer(list(srcs), return_tensors="pt", truncation=True,
                        max_length=256, padding=True)
        tokenizer.src_lang = tgt_lang
        dec = tokenizer(list(tgts), return_tensors="pt", truncation=True,
                        max_length=256, padding=True)
        labels = dec["input_ids"].clone()
        labels[labels == tokenizer.pad_token_id] = -100
        return {**enc, "labels": labels}

    train_loader = DataLoader(TranslationDataset(train_pairs), batch_size=batch_size,
                              shuffle=True, collate_fn=collate)
    val_loader   = DataLoader(TranslationDataset(val_pairs),   batch_size=batch_size,
                              shuffle=False, collate_fn=collate)

    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs * len(train_loader))

    # Save to temp dir — never touch live model during training
    import shutil
    tmp_ckpt = os.path.join(MODEL_DIR, f"_nllb_{direction}_training_tmp")
    os.makedirs(tmp_ckpt, exist_ok=True)
    log.info(f"  Checkpoints → {tmp_ckpt} (live model untouched until done)")

    best_val_loss = float("inf")
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0
        for step, batch in enumerate(train_loader):
            batch = {k: v.to(device) for k, v in batch.items()}
            out   = model(**batch)
            loss  = out.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            total_loss += loss.item()
            if step % 200 == 0:
                log.info(f"  Epoch {epoch}/{epochs} step {step}/{len(train_loader)} "
                         f"loss={loss.item():.4f}")

        avg_train = total_loss / len(train_loader)

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                val_loss += model(**batch).loss.item()
        avg_val = val_loss / len(val_loader)
        log.info(f"  Epoch {epoch}: train_loss={avg_train:.4f}  val_loss={avg_val:.4f}")

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            model.save_pretrained(tmp_ckpt)
            tokenizer.save_pretrained(tmp_ckpt)
            log.info(f"  Saved best checkpoint to tmp (val_loss={best_val_loss:.4f})")

    # Atomically replace live model
    log.info(f"  Copying best checkpoint → {model_path}")
    shutil.copytree(tmp_ckpt, model_path, dirs_exist_ok=True)
    shutil.rmtree(tmp_ckpt, ignore_errors=True)
    log.info(f"  NLLB {direction} retraining complete. Best val_loss={best_val_loss:.4f}")

    # Push in background thread
    repo_id  = HF_REPOS.get(f"nllb_{direction}")
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if repo_id and hf_token:
        import threading
        def _push(dir_=direction, repo_=repo_id, path_=model_path, loss_=best_val_loss, tok_=hf_token):
            try:
                from huggingface_hub import HfApi
                log.info(f"  [bg] Pushing nllb_{dir_} → {repo_} ...")
                HfApi(token=tok_).upload_folder(
                    folder_path=path_,
                    repo_id=repo_,
                    repo_type="model",
                    commit_message=f"Retrained NLLB {dir_} on cleaned + augmented + back-translated data (val_loss={loss_:.4f})",
                )
                log.info(f"  [bg] ✓ nllb_{dir_} pushed to {repo_}")
            except Exception as e:
                log.error(f"  [bg] Push failed for nllb_{dir_}: {e}")
        t = threading.Thread(target=_push, daemon=True)
        t.start()
        log.info(f"  Push for nllb_{direction} started in background")


# ── STEP 8: REBUILD SEMANTIC INDEX ───────────────────────────────────────────

def step_rebuild_index():  # step 8
    log.info("=== STEP 7: Rebuilding semantic search index ===")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "train.py")],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0:
            log.info("  Index rebuilt successfully.")
        else:
            log.warning(f"  train.py exited with code {result.returncode}")
            log.warning(result.stderr[-2000:] if result.stderr else "")
    except FileNotFoundError:
        log.warning("  train.py not found — skipping index rebuild.")
    except Exception as e:
        log.warning(f"  Index rebuild failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train",      action="store_true", help="Skip retraining (steps 1-4 only)")
    parser.add_argument("--skip-backtrans",  action="store_true", help="Skip back-translation")
    parser.add_argument("--skip-nllb",       action="store_true", help="Skip NLLB retraining")
    parser.add_argument("--only-nllb",       action="store_true", help="Skip MarianMT, only train NLLB")
    parser.add_argument("--epochs",          type=int, default=5,    help="Training epochs for MarianMT (default 5)")
    parser.add_argument("--nllb-epochs",     type=int, default=3,    help="Training epochs for NLLB (default 3)")
    parser.add_argument("--batch-size",      type=int, default=32,   help="Batch size for MarianMT (default 32)")
    parser.add_argument("--nllb-batch-size", type=int, default=16,   help="Batch size for NLLB (default 16)")
    parser.add_argument("--lr",              type=float, default=1e-5, help="Learning rate MarianMT (default 1e-5)")
    parser.add_argument("--nllb-lr",         type=float, default=5e-6, help="Learning rate NLLB (default 5e-6)")
    args = parser.parse_args()

    # Step 1: Clean
    pairs_df, en_rn_df, rn_en_df = step_clean()

    # Step 2: Augment
    aug_df = step_augment(rn_en_df)

    # Step 3: Back-translate
    if args.skip_backtrans:
        log.info("=== STEP 3: Skipping back-translation ===")
        bt_df = pd.DataFrame(columns=["english","lunyoro","source"])
    else:
        bt_df = step_backtranslate(rn_en_df)

    # Step 4: Merge
    total = step_merge(pairs_df, aug_df, bt_df)

    if args.skip_train:
        log.info("=== Skipping training (--skip-train) ===")
        log.info(f"Pipeline complete. {total} total training pairs ready.")
        return

    # Step 5: Retrain both MarianMT models from checkpoint
    if args.only_nllb:
        log.info("=== Skipping MarianMT retraining (--only-nllb) ===")
    else:
        step_retrain("en2lun", epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
        step_retrain("lun2en", epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    # Step 7: Retrain NLLB models
    if args.skip_nllb:
        log.info("=== Skipping NLLB retraining (--skip-nllb) ===")
    else:
        step_retrain_nllb("en2lun", epochs=args.nllb_epochs, batch_size=args.nllb_batch_size, lr=args.nllb_lr)
        step_retrain_nllb("lun2en", epochs=args.nllb_epochs, batch_size=args.nllb_batch_size, lr=args.nllb_lr)

    # Wait for any background push threads to finish
    import threading
    for t in threading.enumerate():
        if t != threading.main_thread() and t.is_alive():
            log.info(f"  Waiting for background thread: {t.name}")
            t.join()

    # Step 6: Push to HuggingFace Hub
    step_push_to_hub()

    # Step 7: Rebuild index
    step_rebuild_index()

    log.info("=== Pipeline complete ===")
    log.info(f"  Total training pairs: {total}")
    log.info("  Models retrained from checkpoint (not from scratch)")
    log.info("  Restart the backend to load the updated models.")


if __name__ == "__main__":
    main()
