"""
augment_en2lun.py
=================
Augments en2lun training pairs using the same techniques as augment_bt_data.py
but applied to the existing en2lun pairs in training data.

Also generates domain-specific pairs for under-represented domains using
domain vocabulary from the dictionary.

Key differences from augment_bt_data.py:
  - Works on en2lun direction (English -> Runyoro)
  - Synonym substitution: change English input, keep same Runyoro output
  - Domain expansion: generate new domain-tagged pairs from dictionary
  - Tense/pronoun changes in English, matching Runyoro form stays

Output: data/cleaned/augmented_en2lun.csv
"""

import re
import csv
import argparse
import unicodedata
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE      = Path(__file__).parent
CLEAN_DIR = BASE / "data" / "cleaned"
TRAIN_DIR = BASE / "data" / "training"
OUT_CSV   = CLEAN_DIR / "augmented_en2lun.csv"
TRAIN_CSV = TRAIN_DIR / "train.csv"
VAL_CSV   = TRAIN_DIR / "val.csv"


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", str(text).strip())


def strip_tag(text: str) -> tuple[str, str]:
    m = re.match(r'^\[([A-Z][A-Z0-9_ ]+)\]\s*', str(text))
    return (m.group(1), str(text)[m.end():].strip()) if m else ("NONE", str(text).strip())


# ── Synonym substitution (English side only) ─────────────────────────────────
SYNONYMS = {
    "go": ["walk", "travel", "move", "head"],
    "come": ["arrive", "return"],
    "eat": ["consume", "have"],
    "see": ["look at", "observe", "view"],
    "say": ["tell", "state", "mention"],
    "know": ["understand", "recognise"],
    "want": ["need", "desire", "seek"],
    "give": ["provide", "offer", "hand"],
    "take": ["carry", "grab", "fetch"],
    "work": ["labour", "operate", "toil"],
    "help": ["assist", "support", "aid"],
    "cook": ["prepare", "make"],
    "read": ["study", "look through"],
    "good": ["fine", "excellent", "nice"],
    "bad": ["poor", "wrong"],
    "big": ["large", "great"],
    "small": ["little", "tiny"],
    "fast": ["quick", "rapid"],
    "slow": ["gradual", "unhurried"],
    "happy": ["glad", "joyful", "pleased"],
    "sick": ["ill", "unwell"],
    "many": ["numerous", "several", "a lot of"],
    "child": ["kid", "young one"],
    "person": ["individual", "human"],
    "house": ["home", "dwelling"],
    "water": ["liquid"],
    "food": ["meal", "nourishment"],
    "school": ["institution", "learning centre"],
    "hospital": ["clinic", "medical centre", "health facility"],
    "church": ["place of worship", "chapel"],
    "market": ["trading place", "bazaar"],
    "road": ["path", "route", "way"],
    "village": ["community", "settlement"],
    "farm": ["garden", "field", "plantation"],
    "farmer": ["cultivator", "grower", "agriculturalist"],
    "teacher": ["educator", "instructor", "trainer"],
    "doctor": ["physician", "medical officer", "clinician"],
    "student": ["learner", "pupil", "scholar"],
    "leader": ["head", "chief", "official"],
    "king": ["ruler", "monarch", "sovereign"],
    "law": ["rule", "regulation", "ordinance"],
    "money": ["funds", "payment", "currency"],
    "trade": ["commerce", "business", "exchange"],
    "animal": ["creature", "beast", "wildlife"],
    "plant": ["vegetation", "crop", "herb"],
    "river": ["stream", "waterway", "body of water"],
    "mountain": ["hill", "highland", "peak"],
    "sky": ["heavens", "atmosphere"],
    "sun": ["star", "daylight"],
    "moon": ["lunar body", "night light"],
    "star": ["celestial body"],
    "rain": ["precipitation", "downpour"],
    "wind": ["breeze", "air current"],
    "fire": ["flame", "blaze"],
    "stone": ["rock", "pebble"],
    "tree": ["plant", "shrub", "woody plant"],
    "bird": ["fowl", "avian creature"],
    "fish": ["aquatic animal"],
    "cow": ["cattle", "bovine", "livestock"],
    "goat": ["livestock", "small ruminant"],
}

# ── Domain expansion: templates for small domains ────────────────────────────
DOMAIN_TEMPLATES = {
    "TECHNOLOGY": [
        ("computer", "ekikoopo"),
        ("mobile phone", "telefoni ya ekibaro"),
        ("internet", "omukutu gw'eby'obukuumi"),
        ("electricity", "amasanyalaze"),
        ("machine", "omuzimu gw'obukorakora"),
        ("radio", "rediyo"),
        ("television", "terevisheni"),
        ("telephone", "telefoni"),
        ("camera", "kamera"),
        ("bicycle", "egaali"),
    ],
    "SPORTS": [
        ("football", "obupiira"),
        ("game", "omuzaano"),
        ("player", "omuzaani"),
        ("team", "ekikora hamwe"),
        ("competition", "okusiima"),
        ("win", "okuzunda"),
        ("lose", "okusiibwa"),
        ("run", "okuguruka"),
        ("jump", "okusimbuka"),
        ("throw", "okusarura"),
    ],
    "TOURISM": [
        ("tourism", "obuzinduka"),
        ("tourist", "omuzinduki"),
        ("hotel", "hoteli"),
        ("visit", "okuzinduka"),
        ("journey", "omugendo"),
        ("park", "ekibira ky'ensolo"),
        ("mountain", "orusozi"),
        ("lake", "ennyanja"),
        ("river", "omukka"),
        ("attraction", "ekintu ky'okusanyukirwa"),
    ],
    "ASTRONOMY": [
        ("star", "entungwa"),
        ("moon", "omwezi"),
        ("sun", "izooba"),
        ("sky", "iguru"),
        ("planet", "omupiira gw'iguru"),
        ("universe", "ensiku yoona"),
        ("space", "obutwaire"),
        ("eclipse", "okwoka kw'izooba"),
        ("cloud", "ekire"),
        ("rain", "enjura"),
    ],
    "MATHEMATICS": [
        ("number", "omubaro"),
        ("count", "okubara"),
        ("add", "okuteekamu"),
        ("subtract", "okugyamu"),
        ("multiply", "okuzimu"),
        ("divide", "okukahora"),
        ("equal", "okwingana"),
        ("fraction", "ekitundu"),
        ("total", "omubaro gwona"),
        ("calculator", "ekikoopo ky'okubara"),
    ],
    "MILITARY": [
        ("soldier", "omuserukali"),
        ("army", "abaserukali"),
        ("war", "entumwa"),
        ("fight", "okurwana"),
        ("peace", "emirembe"),
        ("weapon", "orunyuma"),
        ("defend", "okukinga"),
        ("attack", "okushoora"),
        ("guard", "omurinzi"),
        ("commander", "omukuru w'abaserukali"),
    ],
    "LEGAL": [
        ("law", "etegeko"),
        ("court", "entebe y'obwengye"),
        ("judge", "omulamuzi"),
        ("lawyer", "omwanditsi w'amateeka"),
        ("crime", "ekibi"),
        ("punishment", "okuhanibwa"),
        ("justice", "obutuukirivu"),
        ("rights", "amagara"),
        ("constitution", "etegeko nkuru"),
        ("contract", "endagaano"),
    ],
    "ECONOMICS": [
        ("market", "omubaaza"),
        ("trade", "okushubuza"),
        ("price", "omuwendo"),
        ("buy", "okugura"),
        ("sell", "okutunda"),
        ("money", "sente"),
        ("bank", "banki"),
        ("invest", "okuteeka omuhaniro"),
        ("profit", "inzigo"),
        ("business", "omuhaniro"),
    ],
    "GEOGRAPHY": [
        ("country", "ensi"),
        ("district", "egombolola"),
        ("village", "ekiika"),
        ("mountain", "orusozi"),
        ("river", "omugga"),
        ("lake", "ennyanja"),
        ("road", "oluguudo"),
        ("border", "omupaka"),
        ("map", "ekibiina ky'ensi"),
        ("capital", "kibuga ekikuru"),
    ],
    "CULTURE": [
        ("culture", "empisa"),
        ("tradition", "empisa za bakurusiga"),
        ("ceremony", "omukolo"),
        ("dance", "okusina"),
        ("song", "oluyimba"),
        ("story", "olugero"),
        ("proverb", "enfumo"),
        ("custom", "orukundo rw'empisa"),
        ("wedding", "olukiiko olw'okwenyana"),
        ("festival", "olukiiko olw'okusanyuka"),
    ],
}


def augment_synonym_en2lun(pairs: list[tuple[str, str]],
                            max_variants: int = 2) -> list[tuple[str, str]]:
    """Substitute synonyms in English input, keep same Runyoro output."""
    seen = set((e.lower(), l.lower()) for e, l in pairs)
    augmented = []
    for en, lun in pairs:
        domain, en_clean = strip_tag(en)
        words = en_clean.split()
        count = 0
        for i, word in enumerate(words):
            w = word.lower().rstrip('.,!?;:')
            if w in SYNONYMS:
                for syn in SYNONYMS[w][:max_variants]:
                    new_words = words.copy()
                    new_words[i] = syn
                    new_en_clean = ' '.join(new_words)
                    new_en = f"[{domain}] {new_en_clean}" if domain != "NONE" else new_en_clean
                    new_en = normalise(new_en)
                    key = (new_en.lower(), lun.lower())
                    if key not in seen and len(new_en_clean.split()) >= 3:
                        seen.add(key)
                        augmented.append((new_en, lun))
                        count += 1
                        if count >= max_variants:
                            break
            if count >= max_variants:
                break
    return augmented


def generate_domain_pairs() -> list[tuple[str, str]]:
    """Generate new domain-specific training pairs for under-represented domains."""
    pairs = []
    seen = set()
    for domain, vocab in DOMAIN_TEMPLATES.items():
        for english, runyoro in vocab:
            # Simple pair
            en = f"[{domain}] {english}"
            key = (en.lower(), runyoro.lower())
            if key not in seen:
                seen.add(key)
                pairs.append((en, runyoro))
            # With article
            en2 = f"[{domain}] the {english}"
            key2 = (en2.lower(), runyoro.lower())
            if key2 not in seen:
                seen.add(key2)
                pairs.append((en2, runyoro))
            # In a sentence context
            sentence_en = f"[{domain}] I know about {english}"
            sentence_lun = f"Nizi {runyoro}"
            key3 = (sentence_en.lower(), sentence_lun.lower())
            if key3 not in seen:
                seen.add(key3)
                pairs.append((sentence_en, sentence_lun))
    print(f"  Generated {len(pairs):,} domain expansion pairs")
    return pairs


def merge_into_training(pairs: list[tuple[str, str]]) -> tuple[int, int]:
    import shutil
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)
    existing = set(zip(
        pd.concat([train, val])["english"].str.lower().str.strip(),
        pd.concat([train, val])["lunyoro"].str.lower().str.strip(),
    ))
    new = [(e, l) for e, l in pairs if (e.lower(), l.lower()) not in existing]
    if not new:
        print("  No new pairs to add")
        return 0, 0
    split = int(len(new) * 0.9)
    shutil.copy(TRAIN_CSV, str(TRAIN_CSV) + ".bak_en2lun_aug")
    shutil.copy(VAL_CSV,   str(VAL_CSV)   + ".bak_en2lun_aug")
    with open(TRAIN_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for e, l in new[:split]:
            w.writerow([e, l])
    with open(VAL_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for e, l in new[split:]:
            w.writerow([e, l])
    t2 = pd.read_csv(TRAIN_CSV)
    v2 = pd.read_csv(VAL_CSV)
    print(f"  New totals: train={len(t2):,}  val={len(v2):,}")
    return len(new[:split]), len(new[split:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--max-per-pair", type=int, default=2)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  EN2LUN AUGMENTATION PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Load existing en2lun sentence pairs (lun_words >= 3 to avoid dict noise)
    print("[Step 1] Loading en2lun sentence pairs...")
    train = pd.read_csv(TRAIN_CSV)
    val   = pd.read_csv(VAL_CSV)
    both  = pd.concat([train, val])
    both["lun_words"] = both["lunyoro"].astype(str).str.split().str.len()
    both["en_words"]  = both["english"].astype(str).str.split().str.len()
    sentence_pairs_df = both[(both["lun_words"] >= 3) & (both["en_words"] >= 4)]
    pairs = list(zip(
        sentence_pairs_df["english"].astype(str),
        sentence_pairs_df["lunyoro"].astype(str)
    ))
    print(f"  Loaded {len(pairs):,} sentence-level en2lun pairs for augmentation")

    # Step 2: Synonym augmentation
    print(f"\n[Step 2] Synonym augmentation (max {args.max_per_pair} per pair)...")
    syn_pairs = augment_synonym_en2lun(pairs, max_variants=args.max_per_pair)
    print(f"  Generated {len(syn_pairs):,} synonym variants")

    # Step 3: Domain expansion
    print(f"\n[Step 3] Domain expansion for under-represented domains...")
    domain_pairs = generate_domain_pairs()

    # Combine
    all_aug = syn_pairs + domain_pairs
    print(f"\n  Total augmented pairs: {len(all_aug):,}")

    # Save
    print(f"\n[Step 4] Saving to {OUT_CSV.name}...")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    file_exists = OUT_CSV.exists()
    with open(OUT_CSV, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["english", "lunyoro"])
        for e, l in all_aug:
            w.writerow([e, l])
    print(f"  Saved {len(all_aug):,} pairs to {OUT_CSV.name}")

    if args.merge:
        print(f"\n[Step 5] Merging into train.csv / val.csv...")
        n_t, n_v = merge_into_training(all_aug)
        print(f"  Added {n_t:,} to train, {n_v:,} to val")

    print(f"\n{'='*60}")
    print(f"  EN2LUN AUGMENTATION COMPLETE")
    print(f"  Synonym variants:   {len(syn_pairs):,}")
    print(f"  Domain new pairs:   {len(domain_pairs):,}")
    print(f"  Total:              {len(all_aug):,}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
