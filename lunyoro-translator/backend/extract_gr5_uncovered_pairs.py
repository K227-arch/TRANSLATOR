"""
extract_gr5_uncovered_pairs.py
================================
Generates training pairs for the 8 gr5 rule groups that have data tables
but no active runtime correction (Step 2 of grammar rules implementation).

Covered here:
  1. Objectival concord (reversed-object sentences)
  2. Noun classes 1a / 2a (names, personified animals)
  3. Noun classes 9a / 10a (foreign words, colours, place names)
  4. Colour names (Class 9a) — sentence-level
  5. Negative nouns (omu-ta- prefix)
  6. Class 9 professional nouns (en-/em- prefix)
  7. Augmentative / pejorative (class prefix substitution)
  8. Locative possessives — class-based (cl.3-10)

Run:
    python extract_gr5_uncovered_pairs.py
"""

import csv
import re
import sys
from pathlib import Path

BACKEND_DIR  = Path(__file__).parent
DATA_DIR     = BACKEND_DIR / "data"
TRAINING_DIR = DATA_DIR / "training"
CLEANED_DIR  = DATA_DIR / "cleaned"
OUT_CSV      = CLEANED_DIR / "gr5_uncovered_pairs.csv"
TRAIN_CSV    = TRAINING_DIR / "train.csv"
VAL_CSV      = TRAINING_DIR / "val.csv"

sys.path.insert(0, str(BACKEND_DIR))
from language_rules_gr5 import (
    OBJECTIVAL_CONCORDS, build_reversed_object_sentence,
    CLASS_1A_EXAMPLES, build_class2a_plural,
    CLASS_9A_EXAMPLES, build_class10a_plural,
    get_colour_name,
    NEGATIVE_NOUNS, build_negative_noun,
    CLASS9_PROFESSIONAL_NOUNS, derive_class9_professional,
    AUGMENTATIVE_EXAMPLES, build_augmentative,
    LOCATIVE_CLASS_POSSESSIVES, get_class_locative_possessive,
)


def clean_text(text: str) -> str:
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ── 1. OBJECTIVAL CONCORD (reversed-object sentences) ────────────────────────

def pairs_objectival_concord() -> list[tuple[str, str]]:
    pairs = []
    # Programmatic: build reversed-object sentences for common noun pairs
    examples = [
        # (subject, subj_cl, object, obj_cl, verb_stem, english)
        ("omukazi",  1, "omusiri",  3, "lima",   "The woman dug the garden"),
        ("omukazi",  1, "omusiri",  3, "lima",   "The garden the woman dug"),
        ("abahuma",  2, "amata",    6, "nywa",   "The herdsmen drank the milk"),
        ("abaana",   2, "ebitabu",  8, "reeta",  "The children brought the books"),
        ("omwana",   1, "ente",     9, "linda",  "The child herded the cow"),
        ("omulimi",  1, "omuguwa", 11, "tema",   "The farmer cut the rope"),
        ("omukazi",  1, "omwana",   1, "reba",   "The woman saw the child"),
        ("abantu",   2, "embwa",    9, "bona",   "The people saw the dog"),
        ("omwana",   1, "ekitabu",  7, "soma",   "The child read the book"),
        ("omukazi",  1, "ebitooke", 8, "gula",   "The woman bought the bananas"),
    ]
    for subj, scl, obj, ocl, stem, eng in examples:
        # Normal order
        pairs.append((eng + ".", f"{subj} a{OBJECTIVAL_CONCORDS.get(ocl,'')}{stem}ire {obj}."))
        # Reversed (object fronted)
        rev = build_reversed_object_sentence(subj, scl, obj, ocl, stem)
        pairs.append((eng + " (object fronted).", rev + "."))

    # Hand-crafted sentence pairs from grammar rules 5.docx
    pairs += [
        ("The woman has dug the garden.", "Omusiri omukazi agulimire."),
        ("The woman has dug the garden.", "Omukazi omusiri agulimire."),
        ("The herdsmen have drunk the milk.", "Amata gabahuma baganywire."),
        ("The herdsmen have drunk the milk.", "Abahuma amata baganywire."),
        ("The children have brought the books.", "Ebitabu abaana babireesire."),
        ("The children have brought the books.", "Abaana ebitabu babireesire."),
        ("The child has bought his father a long tunic.", "Omwana aguliire ise ekanzu."),
        ("The tunic the child bought for his father.", "Ekanzu omwana agiguliire ise."),
        ("The tunic the father the child bought for him.", "Ekanzu ise omwana agimuguliire."),
        ("The dog bit the child.", "Omwana embwa yamukumira."),
        ("The child the dog bit.", "Omwana embwa yamukumira."),
        ("The farmer cut the banana tree.", "Omulimi atema omuti gw'ebitooke."),
        ("The teacher taught the children.", "Omwigisha yigisha abaana."),
        ("The children the teacher taught.", "Abaana omwigisha yabigishira."),
    ]
    return pairs


# ── 2. NOUN CLASSES 1a / 2a (names, personified animals) ─────────────────────

def pairs_noun_class_1a_2a() -> list[tuple[str, str]]:
    pairs = []
    # Class 1a — empaako names (concordial agreement same as Class 1)
    empaako = [
        ("Abbooki", "Abbooki (empaako name)"),
        ("Abwoli",  "Abwoli (empaako name)"),
        ("Acaali",  "Acaali (empaako name)"),
        ("Akiiki",  "Akiiki (empaako name)"),
        ("Amooti",  "Amooti (empaako name)"),
        ("Adyeri",  "Adyeri (empaako name)"),
        ("Apuuli",  "Apuuli (empaako name)"),
        ("Araali",  "Araali (empaako name)"),
        ("Ateenyi", "Ateenyi (empaako name)"),
        ("Atwoki",  "Atwoki (empaako name)"),
        ("Bbala",   "Bbala (empaako name)"),
    ]
    for eng, lun in empaako:
        pairs.append((eng, lun))

    # Relationship/title names (Class 1a)
    pairs += [
        ("my grandmother",          "mukaaka"),
        ("the chief",               "marumi"),
        ("the elder",               "rubuga"),
        ("Mr. Elephant",            "warujojo"),
        ("Mr. Rabbit",              "wakame"),
        ("Mr. Dog",                 "wambwa"),
        ("Mr. Hen",                 "wankoko"),
        ("Abbooki came.",           "Abbooki yajayo."),
        ("Abbooki is my friend.",   "Abbooki ni mukwangu."),
        ("Akiiki went to school.",  "Akiiki yagenda isomero."),
        ("Amooti is a good person.","Amooti ni muntu murungi."),
        ("Mr. Elephant is big.",    "Warujojo munene."),
        ("Mr. Rabbit is clever.",   "Wakame mwangu."),
    ]

    # Class 2a — plural of 1a (baa- prefix)
    for name in ["Abbooki", "Akiiki", "Amooti", "Adyeri", "mukaaka", "warujojo", "wakame"]:
        plural = build_class2a_plural(name)
        pairs.append((f"the {name}s (plural)", plural))
        pairs.append((f"all the {name}s", plural + " boona"))

    # Sentence pairs with Class 2a
    pairs += [
        ("The Abbooki people came.",        "Baabbooki bajayo."),
        ("All the grandmothers are wise.",  "Baamukaaka boona bakugu."),
        ("The Mr. Elephants are big.",      "Boowarujojo banene."),
        ("The Mr. Rabbits are clever.",     "Boowakame bwangu."),
    ]
    return pairs


# ── 3. NOUN CLASSES 9a / 10a (foreign words, colours, place names) ───────────

def pairs_noun_class_9a_10a() -> list[tuple[str, str]]:
    pairs = []
    # Class 9a — no prefix, concordial agreement same as Class 9
    for lun_word, eng_meaning in CLASS_9A_EXAMPLES.items():
        pairs.append((eng_meaning, lun_word))
        pairs.append((f"the {eng_meaning}", lun_word))

    # Class 10a — plural with zaa- prefix
    for lun_word in list(CLASS_9A_EXAMPLES.keys())[:15]:  # first 15 for variety
        plural = build_class10a_plural(lun_word)
        pairs.append((f"many {CLASS_9A_EXAMPLES[lun_word]}s", plural))

    # Sentence-level examples
    pairs += [
        ("The office is near the market.",      "Ofiisi eri haihi n'isoko."),
        ("The motor car is fast.",              "Motoka yanguha."),
        ("The bus has arrived.",                "Bbaasi ejayo."),
        ("The government built schools.",       "Gavumenti yabaka amasomero."),
        ("I have no money.",                    "Sente nzina."),
        ("The motorcycle is loud.",             "Pikipiki iguma."),
        ("Kaseese is near Kilembe.",            "Kaseese eri haihi na Kilembe."),
        ("There are more things at Kaseese.",   "Kaseese haliyo ebintu bingi."),
        ("Buganda is a big kingdom.",           "Buganda ni obwami bunene."),
        ("Tooro is in western Uganda.",         "Tooro eri oburengerezuba bwa Uganda."),
        ("Bunyoro is an ancient kingdom.",      "Bunyoro ni obwami bw'ekiro."),
        ("The offices are near the market.",    "Zaaofiisi ziri haihi n'isoko."),
        ("The motor cars are fast.",            "Zaamotoka ziyanguha."),
    ]
    return pairs


# ── 4. COLOUR NAMES — sentence level ─────────────────────────────────────────

def pairs_colour_names() -> list[tuple[str, str]]:
    pairs = []
    colour_sentences = [
        ("The cow is white.",               "Ente kyeru."),
        ("The cow is black.",               "Ente kikara."),
        ("The cow is reddish brown.",       "Ente kigaaja."),
        ("The cow is brown.",               "Ente kitaka."),
        ("The cow is grey.",                "Ente kibuubi."),
        ("The cow is dark brown.",          "Ente kisiina."),
        ("The grass is green.",             "Obuheesi kinyansi."),
        ("The banana is yellow.",           "Egitooke kyenju."),
        ("The sky is blue.",                "Eggulu bbururu."),
        ("The cloth is purple.",            "Orugoye kihuukya."),
        ("All their cattle are reddish brown.", "Ente zaabo zoona bigaaju bisa."),
        ("Count each group of cows of the same colour.", "Buli nte ez'erangi emu muzibale zonka."),
        ("The white cow is mine.",          "Ente kyeru ni yange."),
        ("I want a black cow.",             "Nkunda ente kikara."),
        ("The green grass is fresh.",       "Obuheesi kinyansi busha."),
        ("What colour is the cow?",         "Ente erangi ki?"),
        ("The cow is light brown.",         "Ente kataiki."),
        ("The cloth is dark blue.",         "Orugoye kaneke."),
        ("The flower is purple.",           "Ekimuli kihuukya."),
        ("white", "kyeru"),
        ("black", "kikara"),
        ("green", "kinyansi"),
        ("yellow", "kyenju"),
        ("blue", "bbururu"),
        ("brown", "kitaka"),
        ("grey", "kibuubi"),
        ("red", "kigaaja"),
        ("purple", "kihuukya"),
        ("dark blue", "kaneke"),
        ("dark brown", "kisiina"),
        ("light brown", "kataiki"),
    ]
    pairs.extend(colour_sentences)
    return pairs


# ── 5. NEGATIVE NOUNS (omu-ta- prefix) ───────────────────────────────────────

def pairs_negative_nouns() -> list[tuple[str, str]]:
    pairs = []
    # From the data table
    for lun_form, (eng_label, eng_desc) in NEGATIVE_NOUNS.items():
        pairs.append((eng_label, lun_form))
        pairs.append((eng_desc, lun_form))

    # Programmatic: build from common verb stems
    verb_stems = [
        ("seka",    "laugh",    "one who does not laugh",    "gloomy person"),
        ("tooga",   "bathe",    "one who does not bathe",    "dirty person"),
        ("rya",     "eat",      "one who does not eat",      "person who refuses food"),
        ("gamba",   "speak",    "one who does not speak",    "silent person"),
        ("genda",   "go",       "one who does not go",       "stay-at-home person"),
        ("soma",    "study",    "one who does not study",    "person who refuses school"),
        ("zina",    "dance",    "one who does not dance",    "person who refuses to dance"),
        ("lya",     "eat",      "one who does not eat",      "person who refuses food"),
        ("baza",    "ask",      "one who does not ask",      "proud person"),
        ("rora",    "look",     "one who does not look",     "inattentive person"),
        ("kora",    "work",     "one who does not work",     "lazy person"),
        ("nywa",    "drink",    "one who does not drink",    "teetotaller"),
        ("ija",     "come",     "one who does not come",     "absent person"),
        ("hika",    "arrive",   "one who does not arrive",   "person who is always late"),
        ("leeta",   "bring",    "one who does not bring",    "person who never brings anything"),
    ]
    for stem, eng_verb, eng_desc1, eng_desc2 in verb_stems:
        form = build_negative_noun(stem)
        pairs.append((eng_desc1, form))
        pairs.append((eng_desc2, form))
        pairs.append((f"person who never {eng_verb}s", form))

    # Sentence-level examples
    pairs += [
        ("He is a gloomy person who never laughs.",     "Nuwe omutaseka."),
        ("She is a dirty person who never bathes.",     "Nuwe omutooga."),
        ("He is a touchy person.",                      "Nuwe omutagambwaho."),
        ("The gloomy person sat alone.",                "Omutaseka yaikara wenka."),
        ("A dirty person is not welcome.",              "Omutooga takiribwa."),
        ("He is a lazy person who never works.",        "Nuwe omutakora."),
        ("She is a silent person.",                     "Nuwe omutagamba."),
        ("A person who never eats is sick.",            "Omutarya arwaire."),
    ]
    return pairs


# ── 6. CLASS 9 PROFESSIONAL NOUNS (en-/em- prefix) ───────────────────────────

def pairs_class9_professional() -> list[tuple[str, str]]:
    pairs = []
    # From the data table
    for lun_form, (eng_label, eng_note) in CLASS9_PROFESSIONAL_NOUNS.items():
        pairs.append((eng_label, lun_form))
        if eng_note:
            pairs.append((eng_note, lun_form))

    # Programmatic: derive from common verb stems
    verb_stems = [
        ("lima",     "cultivate",  "professional cultivator",   "farmer"),
        ("suubuza",  "trade",      "professional trader",       "merchant"),
        ("baza",     "ask",        "one who always asks",       "inquisitive person"),
        ("genda",    "go",         "one who is always going",   "wanderer"),
        ("rya",      "eat",        "one who always eats",       "glutton"),
        ("soma",     "study",      "one who always studies",    "bookworm"),
        ("zina",     "dance",      "one who always dances",     "dancer"),
        ("baka",     "build",      "professional builder",      "builder"),
        ("higa",     "hunt",       "professional hunter",       "hunter"),
        ("bura",     "judge",      "professional judge",        "judge"),
        ("gamba",    "speak",      "one who always speaks",     "talkative person"),
        ("kora",     "work",       "one who always works",      "hard worker"),
        ("panga",    "plan",       "professional planner",      "planner"),
        ("bona",     "see",        "one who sees everything",   "observer"),
    ]
    for stem, eng_verb, eng_desc1, eng_desc2 in verb_stems:
        form = derive_class9_professional(stem)
        pairs.append((eng_desc1, form))
        pairs.append((eng_desc2, form))
        pairs.append((f"habitual {eng_verb}r", form))

    # Sentence-level examples
    pairs += [
        ("The professional cultivator works hard.",     "Endimi ikora nkakiiko."),
        ("The professional trader sells many things.",  "Ensuubuzi itunda ebintu bingi."),
        ("The incurable liar is not trusted.",          "Encwangya tikirwa."),
        ("The permanent widow lives alone.",            "Enfaakati yaikara yeka."),
        ("The professional builder built the house.",   "Enbaka yabaka enju."),
        ("The professional hunter caught a lion.",      "Enhiga yafumba empologoma."),
        ("The glutton ate all the food.",               "Enrya yarya ebyokurya byoona."),
    ]
    return pairs


# ── 7. AUGMENTATIVE / PEJORATIVE ─────────────────────────────────────────────

def pairs_augmentative() -> list[tuple[str, str]]:
    pairs = []
    # From the data table
    for lun_aug, (base, base_eng, aug_meaning) in AUGMENTATIVE_EXAMPLES.items():
        pairs.append((aug_meaning, lun_aug))
        pairs.append((f"augmentative of {base_eng}", lun_aug))

    # Programmatic: build augmentatives for common nouns
    nouns = [
        ("omusaija",  "man",    "big/bad man",          "clumsy man"),
        ("omwana",    "child",  "insolent child",       "funny-looking child"),
        ("omwisiki",  "girl",   "girl of great beauty", "bold girl"),
        ("omwiru",    "serf",   "sturdy peasant",       "dear poor man"),
        ("omuntu",    "person", "monster-like person",  "huge person"),
        ("omukazi",   "woman",  "big/bold woman",       "contemptible woman"),
        ("omusigazi", "youth",  "youth acting badly",   "troublesome youth"),
    ]
    for base, eng, cl5_meaning, cl7_meaning in nouns:
        cl5 = build_augmentative(base, "5")
        cl7 = build_augmentative(base, "7")
        pairs.append((cl5_meaning, cl5))
        pairs.append((cl7_meaning, cl7))
        pairs.append((f"big {eng} (pejorative)", cl5))
        pairs.append((f"contemptible {eng}", cl7))

    # Sentence-level examples
    pairs += [
        ("That big disrespectful man came.",        "Isaija yajayo."),
        ("The insolent child broke the cup.",       "Eryana yasya ekikopo."),
        ("That clumsy man fell down.",              "Ekisaija yaguwa."),
        ("The dear poor man is my friend.",         "Ekiiru ni mukwangu."),
        ("That bold girl is clever.",               "Eriisiki mwangu."),
        ("The troublesome youth ran away.",         "Isigazi yabba."),
        ("That huge person ate all the food.",      "Erintu yarya ebyokurya byoona."),
        ("The contemptible woman laughed.",         "Ekikazi yaseka."),
    ]
    return pairs


# ── 8. LOCATIVE POSSESSIVES — class-based (cl.3-10) ──────────────────────────

def pairs_class_locative_possessives() -> list[tuple[str, str]]:
    pairs = []
    class_nouns = {
        3:  ("mongoose",    "omusege"),
        4:  ("mongooses",   "emisege"),
        7:  ("thing",       "ekintu"),
        8:  ("things",      "ebintu"),
        9:  ("animal",      "enyamaishwa"),
        10: ("animals",     "enyamaishwa"),
    }
    for cl, (eng_noun, lun_noun) in class_nouns.items():
        omwa = get_class_locative_possessive(cl, "omwa")
        owa  = get_class_locative_possessive(cl, "owa")
        if omwa:
            pairs.append((f"in the {eng_noun}'s place", omwa))
            pairs.append((f"inside the {eng_noun}'s home", omwa))
        if owa:
            pairs.append((f"at the {eng_noun}'s place", owa))
            pairs.append((f"to the {eng_noun}'s home", owa))

    # Sentence-level examples from grammar rules 5.docx
    pairs += [
        ("A mosquito amongst its relatives is addressed as Rwakinumi.",
         "Omubu guli owabugwo bagweta Rwakinumi."),
        ("Go to your home.",                "Mugende owaabu-inywe."),
        ("For what reason have they had to leave their home?", "Owaabubo baihirweyo ki?"),
        ("At Nyakato's house.",             "Omwabu Nyakato."),
        ("At those women's house.",         "Omwabu abakazi abo."),
        ("At these people's house.",        "Omwabu banu."),
        ("At those people's house.",        "Omwabu bali."),
        ("The mongoose is in its place.",   "Omusege guli omwabugwo."),
        ("The animal is at its place.",     "Enyamaishwa iri owaabuyo."),
    ]
    return pairs


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = set()
    cleaned = []
    for en, lun in pairs:
        en  = clean_text(en).strip()
        lun = clean_text(lun).strip()
        if not en or not lun or len(en) < 2 or len(lun) < 2:
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


def write_csv(path: Path, pairs: list[tuple[str, str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "lunyoro"])
        for en, lun in pairs:
            writer.writerow([en, lun])
    print(f"  Wrote {len(pairs)} pairs -> {path.name}")


def append_to_csv(path: Path, new_pairs: list[tuple[str, str]]) -> int:
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


# ── Main ──────────────────────────────────────────────────────────────────────

def get_all_pairs() -> list[tuple[str, str]]:
    all_pairs = []
    all_pairs.extend(pairs_objectival_concord())
    all_pairs.extend(pairs_noun_class_1a_2a())
    all_pairs.extend(pairs_noun_class_9a_10a())
    all_pairs.extend(pairs_colour_names())
    all_pairs.extend(pairs_negative_nouns())
    all_pairs.extend(pairs_class9_professional())
    all_pairs.extend(pairs_augmentative())
    all_pairs.extend(pairs_class_locative_possessives())
    return all_pairs


def main():
    print("=== Grammar Rules 5 — Uncovered Rule Groups Training Pair Extraction ===\n")
    print("Rule groups covered:")
    print("  1. Objectival concord (reversed-object sentences)")
    print("  2. Noun classes 1a / 2a (names, personified animals)")
    print("  3. Noun classes 9a / 10a (foreign words, colours, place names)")
    print("  4. Colour names — sentence level")
    print("  5. Negative nouns (omu-ta- prefix)")
    print("  6. Class 9 professional nouns (en-/em- prefix)")
    print("  7. Augmentative / pejorative (class prefix substitution)")
    print("  8. Locative possessives — class-based (cl.3-10)")
    print()

    raw   = get_all_pairs()
    clean = clean_pairs(raw)
    print(f"Raw pairs:            {len(raw)}")
    print(f"After deduplication:  {len(clean)}")

    write_csv(OUT_CSV, clean)

    split       = int(len(clean) * 0.9)
    train_pairs = clean[:split]
    val_pairs   = clean[split:]

    print(f"\nMerging into training data...")
    n_train = append_to_csv(TRAIN_CSV, train_pairs)
    n_val   = append_to_csv(VAL_CSV,   val_pairs)

    print(f"  Added {n_train} new pairs to train.csv")
    print(f"  Added {n_val}   new pairs to val.csv")
    print(f"\nDone. Total gr5-uncovered pairs: {len(clean)}")
    print(f"NOTE: Training not run. Push files to GitHub, then run:")
    print(f"  python train_marian.py --direction both --epochs 5")
    print(f"  python train_nllb.py   --direction both --epochs 3")


if __name__ == "__main__":
    main()
