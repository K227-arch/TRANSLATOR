"""
extract_gr4_training_pairs.py
==============================
Extracts clean English ↔ Runyoro-Rutooro training pairs from Grammar Rules 4
data (language_rules_gr4.py) and merges them into the training CSV files.

Run:
    python extract_gr4_training_pairs.py
"""

import csv
import os
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).parent
DATA_DIR     = BACKEND_DIR / "data"
TRAINING_DIR = DATA_DIR / "training"
CLEANED_DIR  = DATA_DIR / "cleaned"
GR4_CSV      = CLEANED_DIR / "gr4_pairs.csv"
TRAIN_CSV    = TRAINING_DIR / "train.csv"
VAL_CSV      = TRAINING_DIR / "val.csv"

sys.path.insert(0, str(BACKEND_DIR))

# ── Import all gr4 data ───────────────────────────────────────────────────────
from language_rules_gr4 import (
    ENUMERATIVE_PRONOUNS,
    DEMONSTRATIVES_NEAR_FULL, DEMONSTRATIVES_FAR_FULL, DEMONSTRATIVES_IN_MIND_FULL,
    SUBJECT_RELATIVE_CONCORDS_FULL, OBJECT_RELATIVE_CONCORDS_FULL,
    MODAL_TA_PATTERNS,
    DARA_PRONOUNS, DARA_NOUN_CLASSES,
    COPULA_NI_PRONOUNS, COPULA_N_NEAR, COPULA_N_FAR,
    KA_EMPHATIC_PATTERNS, KA_PERMISSIVE_EXAMPLES,
    VERB_NOUN_EXAMPLES,
    KINSHIP_TERMS,
    build_fraction, build_distributive,
    build_ka_permissive, build_relative_clause,
    derive_agent_noun, derive_action_noun, derive_method_noun,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
_NOUN_CLASS_LABELS = {
    1: "person/cl.1", 2: "people/cl.2", 3: "tree/cl.3", 4: "trees/cl.4",
    5: "fruit/cl.5",  6: "fruits/cl.6", 7: "thing/cl.7", 8: "things/cl.8",
    9: "animal/cl.9", 10: "animals/cl.10", 11: "rope/cl.11",
    12: "small thing/cl.12", 13: "small things/cl.13",
    14: "abstract/cl.14", 15: "infinitive/cl.15",
}

_PERSON_LABELS = {
    "1sg": "I", "2sg": "you (sg)", "3sg": "he/she",
    "1pl": "we", "2pl": "you (pl)", "3pl": "they",
}

_RELATION_LABELS = {
    "father": "father", "mother": "mother",
    "grandfather": "grandfather", "grandmother": "grandmother",
    "paternal_aunt": "paternal aunt", "maternal_aunt": "maternal aunt",
    "maternal_uncle": "maternal uncle", "paternal_uncle": "paternal uncle",
    "father_in_law": "father-in-law", "mother_in_law": "mother-in-law",
    "husband": "husband",
}

_PERSON_POSS = {
    "1sg": "my", "2sg": "your", "3sg": "his/her",
    "1pl": "our", "2pl": "your (pl)", "3pl": "their",
}


def pairs_from_enumerative() -> list[tuple[str, str]]:
    pairs = []
    labels = {
        "exclusive": ("alone", "only"),
        "inclusive": ("all of", "all"),
        "selective": ("himself/herself", "themselves", "myself", "yourself"),
        "both":      ("both of",),
    }
    for person, types in ENUMERATIVE_PRONOUNS.items():
        p = _PERSON_LABELS[person]
        for etype, form in types.items():
            if etype == "exclusive":
                pairs.append((f"{p} alone", form))
                pairs.append((f"only {p}", form))
            elif etype == "inclusive":
                pairs.append((f"all of {p}", form))
                pairs.append((f"all {p}", form))
            elif etype == "selective":
                if "sg" in person:
                    pairs.append((f"{p} himself" if person == "3sg" else f"{p} myself" if person == "1sg" else f"{p} yourself", form))
                else:
                    pairs.append((f"{p} themselves" if person == "3pl" else f"{p} ourselves" if person == "1pl" else f"{p} yourselves", form))
            elif etype == "both":
                pairs.append((f"both of {p}", form))
    return pairs


def pairs_from_demonstratives() -> list[tuple[str, str]]:
    pairs = []
    for cl, form in DEMONSTRATIVES_NEAR_FULL.items():
        label = _NOUN_CLASS_LABELS.get(cl, f"cl.{cl}")
        pairs.append((f"this {label} (near)", form))
        pairs.append((f"this one here (cl.{cl})", form))
    for cl, form in DEMONSTRATIVES_FAR_FULL.items():
        label = _NOUN_CLASS_LABELS.get(cl, f"cl.{cl}")
        pairs.append((f"that {label} (far)", form))
        pairs.append((f"that one over there (cl.{cl})", form))
    for cl, form in DEMONSTRATIVES_IN_MIND_FULL.items():
        label = _NOUN_CLASS_LABELS.get(cl, f"cl.{cl}")
        pairs.append((f"that {label} (already mentioned)", form))
    return pairs


def pairs_from_modal_ta() -> list[tuple[str, str]]:
    pairs = []
    for key, (runyoro, english) in MODAL_TA_PATTERNS.items():
        pairs.append((english, runyoro))
        # Also add reverse
        pairs.append((runyoro, english))
    # Extra greeting patterns
    extras = [
        ("Good morning", "Oraire ota?"),
        ("How did you sleep?", "Oraire ota?"),
        ("How are you?", "Oroho ota?"),
        ("I am fine!", "Ndooho nti!"),
        ("They dig like this", "Balima bati"),
        ("How do women dig?", "Abakazi balima bata?"),
        ("How do cows moo?", "Ente zijuga zita?"),
        ("They moo like this", "Zijuga ziti"),
    ]
    pairs.extend(extras)
    return pairs


def pairs_from_dara() -> list[tuple[str, str]]:
    pairs = []
    for person, form in DARA_PRONOUNS.items():
        p = _PERSON_LABELS[person]
        pairs.append((f"here {p} am/is/are", form))
        pairs.append((f"there {p} is", form))
    for cl, form in DARA_NOUN_CLASSES.items():
        label = _NOUN_CLASS_LABELS.get(cl, f"cl.{cl}")
        pairs.append((f"here is the {label}", form))
        pairs.append((f"there it is (cl.{cl})", form))
    return pairs


def pairs_from_copula() -> list[tuple[str, str]]:
    pairs = []
    person_be = {
        "1sg": "I am", "2sg": "you are", "3sg": "he/she is",
        "1pl": "we are", "2pl": "you (pl) are", "3pl": "they are",
    }
    for person, form in COPULA_NI_PRONOUNS.items():
        pairs.append((person_be[person], form))
    # n- before near demonstratives
    for cl, form in COPULA_N_NEAR.items():
        label = _NOUN_CLASS_LABELS.get(cl, f"cl.{cl}")
        pairs.append((f"it is this {label} (near)", form))
    # n- before far demonstratives
    for cl, form in COPULA_N_FAR.items():
        label = _NOUN_CLASS_LABELS.get(cl, f"cl.{cl}")
        pairs.append((f"it is that {label} (far)", form))
    # Elision examples
    elision = [
        ("it is a person", "n'omuntu"),
        ("it is a cow", "n'ente"),
        ("it is a child", "n'omwana"),
        ("it is water", "n'amazzi"),
        ("it is food", "n'ebyokurya"),
        ("it is a house", "n'enju"),
        ("it is a book", "n'ekitabo"),
        ("it is a tree", "n'omuti"),
        ("it is a dog", "n'embwa"),
        ("it is a cat", "n'ekipaka"),
        ("who are you?", "niiwe oha?"),
        ("who is he?", "nuwe oha?"),
        ("who are they?", "nubo oha?"),
    ]
    pairs.extend(elision)
    return pairs


def pairs_from_ka() -> list[tuple[str, str]]:
    pairs = []
    for key, (runyoro, english) in KA_EMPHATIC_PATTERNS.items():
        pairs.append((english, runyoro))
    for person, (runyoro, english) in KA_PERMISSIVE_EXAMPLES.items():
        pairs.append((english, runyoro))
    # Build more permissive forms
    verbs = [
        ("genda", "go"), ("rya", "eat"), ("nywa", "drink"),
        ("lya", "eat"), ("soma", "read"), ("zina", "dance"),
        ("baza", "ask"), ("rora", "look"), ("gamba", "speak"),
    ]
    persons = ["1sg", "1pl", "3sg", "3pl"]
    for stem, eng in verbs:
        for person in persons:
            form = build_ka_permissive(person, stem)
            p = _PERSON_LABELS[person]
            pairs.append((f"let {p} {eng}", form))
    return pairs


def pairs_from_kinship() -> list[tuple[str, str]]:
    pairs = []
    for relation, persons in KINSHIP_TERMS.items():
        rel_label = _RELATION_LABELS.get(relation, relation)
        for person, form in persons.items():
            poss = _PERSON_POSS[person]
            pairs.append((f"my {rel_label}" if person == "1sg" else
                          f"your {rel_label}" if person == "2sg" else
                          f"his/her {rel_label}" if person == "3sg" else
                          f"our {rel_label}" if person == "1pl" else
                          f"your (pl) {rel_label}" if person == "2pl" else
                          f"their {rel_label}", form))
    # Sentence-level kinship examples
    sentence_pairs = [
        ("My father went to the market.", "Isange yagenda omu isoko."),
        ("Your mother is cooking.", "Nyinawe ateteka."),
        ("His father is a teacher.", "Ise ye omwigisha."),
        ("Our grandfather is old.", "Isenkurwitwe amaze emyaka."),
        ("Her mother called her.", "Nyina yamwita."),
        ("Their father is coming.", "Isabo ajayo."),
        ("My grandfather told me a story.", "Isenkurwange yangambira engero."),
        ("Your grandmother is wise.", "Nyinenkurwawe ni omukugu."),
    ]
    pairs.extend(sentence_pairs)
    return pairs


def pairs_from_verb_nouns() -> list[tuple[str, str]]:
    pairs = []
    for infinitive, forms in VERB_NOUN_EXAMPLES.items():
        if "agent" in forms:
            pairs.append((f"one who does {infinitive[3:]}", forms["agent"]))
        if "action" in forms:
            pairs.append((f"the act of {infinitive[3:]}", forms["action"]))
        if "method" in forms:
            pairs.append((f"method of {infinitive[3:]}", forms["method"]))
    # Derived forms from common verbs
    common_verbs = [
        ("okulima", "dig/cultivate"),
        ("okugenda", "go"),
        ("okusoma", "read/study"),
        ("okugamba", "speak"),
        ("okuzina", "dance"),
        ("okurya", "eat"),
        ("okubaza", "ask"),
        ("okurora", "see/look"),
        ("okwogera", "speak"),
        ("okukora", "work"),
        ("okwiga", "learn"),
        ("okubaka", "build"),
        ("okuhiija", "pant"),
        ("okubara", "count/carpenter"),
        ("okuzaana", "play"),
    ]
    for inf, eng_stem in common_verbs:
        agent  = derive_agent_noun(inf)
        action = derive_action_noun(inf)
        method = derive_method_noun(inf)
        stem   = eng_stem.split("/")[0]
        pairs.append((f"one who {stem}s", agent))
        pairs.append((f"the work of {stem}ing", action))
        pairs.append((f"method of {stem}ing", method))
    return pairs


def pairs_from_fractions_distributives() -> list[tuple[str, str]]:
    pairs = []
    # Fractions
    frac_map = [
        (1, 2, "one half", "a half"),
        (1, 3, "one third", "a third"),
        (1, 4, "one quarter", "a quarter"),
        (2, 3, "two thirds", None),
        (3, 4, "three quarters", None),
        (1, 5, "one fifth", None),
        (2, 5, "two fifths", None),
    ]
    for num, den, eng1, eng2 in frac_map:
        form = build_fraction(num, den)
        pairs.append((eng1, form))
        if eng2:
            pairs.append((eng2, form))
    # Distributives
    dist_map = [
        ("babiri", "two by two", "in twos"),
        ("basatu", "three by three", "in threes"),
        ("bana", "four by four", "in fours"),
        ("bataano", "five by five", "in fives"),
    ]
    for word, eng1, eng2 in dist_map:
        form = build_distributive(word)
        pairs.append((eng1, form))
        pairs.append((eng2, form))
    return pairs


def pairs_from_relative_clauses() -> list[tuple[str, str]]:
    pairs = []
    # Subject relative clauses for common noun classes
    examples = [
        (1, "genda", "ni", "the person who is going"),
        (1, "rya",   "ni", "the person who is eating"),
        (2, "genda", "ni", "the people who are going"),
        (7, "genda", "ni", "the thing that is going"),
        (9, "genda", "ni", "the animal that is going"),
    ]
    for cl, stem, tense, english in examples:
        form = build_relative_clause(cl, stem, tense, "subject")
        pairs.append((english, form))
    return pairs


def pairs_from_sentences() -> list[tuple[str, str]]:
    """Hand-crafted sentence pairs covering gr4 grammar patterns."""
    return [
        # Enumerative
        ("I alone went to the market.", "Nyenka nagenda omu isoko."),
        ("They all came.", "Boona bajayo."),
        ("Both of us are going.", "Twembi tugenda."),
        ("She herself cooked the food.", "Weenyini yateka ebyokurya."),
        ("We ourselves built the house.", "Tweenyini twabaka enju."),
        ("You alone know the answer.", "Wenka omanye okusubiza."),
        # Demonstratives
        ("This person is my friend.", "Omuntu onu ni mukwangu."),
        ("That person over there is a teacher.", "Omuntu oli ni omwigisha."),
        ("Those people are coming.", "Abantu bali bajayo."),
        ("This thing is good.", "Ekintu kinu kirungi."),
        # Copula
        ("It is a person.", "N'omuntu."),
        ("It is a cow.", "N'ente."),
        ("It is water.", "N'amazzi."),
        ("I am a teacher.", "Niinyowe omwigisha."),
        ("You are a student.", "Niiwe omwigishwa."),
        ("He is a farmer.", "Nuwe omulimi."),
        ("We are people.", "Niitwe abantu."),
        ("They are children.", "Nubo abaana."),
        # Ka permissive
        ("Let us go.", "Ka tugende."),
        ("Let me eat.", "Ka nrye."),
        ("Let him speak.", "Ka agambe."),
        ("Let them dance.", "Ka bazine."),
        ("Let us pray.", "Ka tuseenge."),
        # Ka emphatic
        ("The very person I was looking for.", "Ka muntu nkaba nkora."),
        ("It is really you.", "Ka niiwe."),
        # Modal -ta / -ti
        ("Good morning, how did you sleep?", "Oraire ota?"),
        ("How are you?", "Oroho ota?"),
        ("I am fine.", "Ndooho nti."),
        ("He said like this:", "Agamba ati:"),
        ("She said to them:", "Yabagambira ati:"),
        # Dara
        ("Here I am.", "Daranyowe."),
        ("Here he is.", "Darawe."),
        ("Here they are.", "Darabo."),
        ("Here is the tree.", "Daragwo."),
        # Kinship in sentences
        ("My father is a good man.", "Isange ni muntu murungi."),
        ("Your mother is cooking.", "Nyinawe ateteka."),
        ("His grandfather told a story.", "Isenkuru yagamba engero."),
        ("Our grandmother is wise.", "Nyinenkurwitwe ni omukugu."),
        ("Their father came home.", "Isabo yajayo omu rugo."),
        # Verb-noun derivation
        ("The cultivator works hard.", "Omulimi akora nkakiiko."),
        ("Farming is important.", "Omulimo gwa kulima gurikurungi."),
        ("The carpenter made a chair.", "Omubazi yakora entebe."),
        ("The player danced well.", "Omuzaani yazina kirungi."),
        # Fractions
        ("Give me half.", "Mpere kimu kya kabiri."),
        ("He ate a quarter.", "Yarya kimu kya kana."),
        ("Two thirds of the people came.", "Bibiri bya kasatu by'abantu bajayo."),
        # Distributives
        ("They came two by two.", "Bajayo babiri babiri."),
        ("The children sat three by three.", "Abaana baicara basatu basatu."),
        # Relative clauses
        ("The person who is going is my friend.", "Omuntu anigenda ni mukwangu."),
        ("The people who came are teachers.", "Abantu ababajayo ni abawigisha."),
        # Mixed
        ("Both of them are my friends.", "Bombi ni bakwangu."),
        ("All of you are welcome.", "Mweena mwakiriwe."),
        ("Let us all go together.", "Ka tugende tweena hamwe."),
        ("Here is the person you were looking for.", "Daroonu omuntu owakaba okora."),
        ("It is really my father.", "Ka isange."),
        ("My father alone knows.", "Isange wenka omanye."),
    ]


# ── Main extraction ───────────────────────────────────────────────────────────

def extract_all_pairs() -> list[tuple[str, str]]:
    all_pairs: list[tuple[str, str]] = []
    all_pairs.extend(pairs_from_enumerative())
    all_pairs.extend(pairs_from_demonstratives())
    all_pairs.extend(pairs_from_modal_ta())
    all_pairs.extend(pairs_from_dara())
    all_pairs.extend(pairs_from_copula())
    all_pairs.extend(pairs_from_ka())
    all_pairs.extend(pairs_from_kinship())
    all_pairs.extend(pairs_from_verb_nouns())
    all_pairs.extend(pairs_from_fractions_distributives())
    all_pairs.extend(pairs_from_relative_clauses())
    all_pairs.extend(pairs_from_sentences())
    return all_pairs


def clean_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Deduplicate, strip whitespace, drop empty or too-short pairs."""
    seen = set()
    cleaned = []
    for en, lun in pairs:
        en  = en.strip()
        lun = lun.strip()
        if not en or not lun:
            continue
        if len(en) < 2 or len(lun) < 2:
            continue
        key = (en.lower(), lun.lower())
        if key in seen:
            continue
        seen.add(key)
        cleaned.append((en, lun))
    return cleaned


def load_existing_csv(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    existing = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            en  = (row.get("english") or "").strip().lower()
            lun = (row.get("lunyoro") or "").strip().lower()
            if en and lun:
                existing.add((en, lun))
    return existing


def append_to_csv(path: Path, new_pairs: list[tuple[str, str]]):
    """Append new pairs to an existing CSV, skipping duplicates."""
    existing = load_existing_csv(path)
    to_add = [(en, lun) for en, lun in new_pairs
              if (en.lower(), lun.lower()) not in existing]
    if not to_add:
        print(f"  No new pairs to add to {path.name}")
        return 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for en, lun in to_add:
            writer.writerow([en, lun])
    return len(to_add)


def write_gr4_csv(path: Path, pairs: list[tuple[str, str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "lunyoro"])
        for en, lun in pairs:
            writer.writerow([en, lun])
    print(f"  Wrote {len(pairs)} pairs → {path}")


def main():
    print("=== Grammar Rules 4 Training Pair Extraction ===\n")

    raw_pairs = extract_all_pairs()
    print(f"Raw pairs extracted:  {len(raw_pairs)}")

    clean = clean_pairs(raw_pairs)
    print(f"After deduplication:  {len(clean)}")

    # Save standalone gr4 CSV
    write_gr4_csv(GR4_CSV, clean)

    # Split: 90% train, 10% val
    split = int(len(clean) * 0.9)
    train_pairs = clean[:split]
    val_pairs   = clean[split:]

    # Merge into training CSVs
    print(f"\nMerging into training data...")
    n_train = append_to_csv(TRAIN_CSV, train_pairs)
    n_val   = append_to_csv(VAL_CSV,   val_pairs)

    print(f"  Added {n_train} new pairs to train.csv")
    print(f"  Added {n_val}   new pairs to val.csv")
    print(f"\nDone. Total gr4 pairs: {len(clean)}")
    print(f"Run `python train_marian.py --epochs 3 --direction both` to retrain.")


if __name__ == "__main__":
    main()
