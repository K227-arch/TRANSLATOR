"""
Extended Runyoro-Rutooro language rules from OCR grammar books.
This module extends language_rules.py with additional content from:
  - Chapter 2: Sound Change (y-insertion, reflexive verbs, conversive suffixes)
  - Chapter 12: Derivative Verbs (applied/prepositional, causative, passive, neuter, conversive, reciprocal)
  - Chapter 13: Moods and Tenses (imperative, subjunctive, indicative)
  - Chapter 7: Noun Classes (class 12-14 details, augmentative/pejorative)
  - Chapter 4: Numbers and Ordinals
  
To use: from language_rules_ocr_extension import *
"""

# ─────────────────────────────────────────────────────────────────────────────
# SOUND CHANGE RULES (Chapter 2) — Extended from OCR
# ─────────────────────────────────────────────────────────────────────────────

# Y-insertion examples (after tense prefixes a-, ra-, raa-)
Y_INSERTION_EXAMPLES = {
    "nayara": "just now I made the bed",
    "baayombeka": "just now they built",
    "ndaayara": "I shall make the bed",
    "turaayara": "we shall make the bed",
    "orayegere": "have you ever studied?",
    "barayombekere": "have they ever built?",
}

# Y-insertion NOT present after other tense particles
Y_INSERTION_COUNTEREXAMPLES = {
    "nkaara": "I made the bed (not nkayara)",
    "ndyara": "I shall make the bed (not ndiyara)",
    "tinkaazire": "I have not made the bed (not tinkayazire)",
}

# Y-insertion with i-initial stems (1st person singular only)
Y_INSERTION_I_STEMS = {
    "nyizire": "I have come",
    "nyikaliire": "I have sat down",
    # Compare with other persons:
    "twizire": "we have come",
    "oizire": "you have come",
    "mwizire": "you (pl.) have come",
    "aizire": "he/she has come",
    "baizire": "they have come",
}

# Reflexive verb imperatives (singular: wee- + long vowel + -e)
REFLEXIVE_IMPERATIVES = {
    "weesereke": ("okw-esereka", "hide yourself"),
    "weebundaaze": ("okw-ebundaaza", "humble yourself"),
    "weerekere": ("okw-erekera", "set yourself free"),
    "weebale": ("okw-ebara", "thank you (lit. count yourself)"),
    # Plural forms:
    "mwesereke": ("okw-esereka", "hide yourselves"),
    "mwebundaaze": ("okw-ebundaaza", "humble yourselves"),
    "mwerekere": ("okw-erekera", "set yourselves free"),
    "mwebale": ("okw-ebara", "thank you (plural)"),
}

# Reflexive verbs with no apparent reflexive meaning
REFLEXIVE_NON_REFLEXIVE = {
    "weesigege": ("okw-esiga", "trust (lit. trust yourself)"),
    "weetegereze": ("okw-etegereza", "understand"),
    "weebuge": ("okw-ebuga", "proclaim your bravery"),
    "weesize": ("okw-esiza", "stop crying"),
}

# Conversive verb suffix vowel rules (extended examples)
CONVERSIVE_EXAMPLES = {
    "okubamba": {
        "meaning": "to peg out",
        "conversive": {
            "okubambura": "to unpeg",
            "okubambuurra": "to completely unpeg",
            "okubambuka": "to break away",
            "okubamburuka": "to come unpegged",
            "okubamburruuka": "to completely come unpegged",
        },
    },
    "okuleega": {
        "meaning": "to tighten",
        "conversive": {
            "okuleegura": "to loosen tight string",
            "okuleeguurra": "to remove band round neck of cow after being bleeded",
            "okuleeguka": "to get loose",
            "okuleeguruka": "to become untightened string",
            "okuleegurruuka": "to come unstrung (bow)",
        },
    },
    "okuboha": {
        "meaning": "to fasten",
        "conversive": {
            "okubohoorra": "to unfasten",
            "okubohoroka": "to go down (constipated stomach)",
            "okubohorrooka": "to come unfastened",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DERIVATIVE VERBS (Chapter 12) — from OCR
# ─────────────────────────────────────────────────────────────────────────────

# Applied/Prepositional verb meanings
APPLIED_VERB_MEANINGS = {
    "place": "place where action was/will be completed or motion is directed",
    "time": "time one takes to do something or time by which one does something",
    "cause": "cause, reason, purpose or motive",
    "completeness": "completeness or thoroughness of the action",
}

APPLIED_VERB_EXAMPLES = {
    "place": [
        ("Omukazi tabohera bintu mukisiika.", "A woman does not pack up things in the inner sitting room."),
        ("Enyama bagitematemera hakiti.", "People cut meat into pieces on a piece of wood."),
        ("Bakairukira omukibira.", "They took refuge in the forest."),
    ],
    "time": [
        ("Oruhanda orw'okuruga Kyaka okuhika Butiiti twarulibatiraga ebiro bibiri.",
         "It took us two days to travel from Kyaka to Butiiti."),
        ("Omusiri gunu akagulimira okwezi kumu.", "It took her one month to cultivate this garden."),
    ],
}

# New meanings imparted by prepositional suffix
PREPOSITIONAL_NEW_MEANINGS = {
    "okuboha": ("to tie", {
        "okubohera": "to tie cow's legs with strip of hide when milking",
        "okuboheza": "to make use of strip of hide in tying cow's legs",
    }),
    "okutema": ("to cut", {
        "okutemera": "to plant beans one by one with a hoe",
        "okutemeza": "to make use of hoe in planting beans one by one",
    }),
}

# Double prepositional verbs (V.Pr.2)
DOUBLE_PREPOSITIONAL = {
    "okubohera": {
        "meaning": "to tie for",
        "extended": "okuboheerra (V.Pr.2: to fasten up for, as food for journey)",
        "double": "okubohereerra (to tie for/fasten up for with reference to place)",
    },
    "okutemera": {
        "meaning": "to cut for",
        "extended": "okutemeerra (to cut grass with a knife)",
        "double": "okutemereerra (to cut grass for/on behalf of one with reference to place)",
    },
}

# Causative verb formation rules
CAUSATIVE_FORMATION = {
    "monosyllabic": {
        "rule": "add -isa to simple stem",
        "examples": {
            "ba": "baisa (put in a state)",
            "ha": "haisa (cause one to give)",
            "ta": "taisa (cause one to put or leave)",
        },
        "exceptions": {
            "sa": "siisa (grind with)",
            "fa": "fiisa (be bereaved of, especially children)",
        },
    },
    "verbs_in_ra": {
        "rule": "change -ra into -za",
        "examples": {
            "okubara": "okubaza (help one count)",
            "okuhaarra": "okuharuza (scrape out with)",
        },
    },
    "verbs_in_ta": {
        "rule": "change -ta into -sa",
        "examples": {
            "okucumita": "okucumisa (stab with)",
            "okurubata": "okurubasa (tread with)",
        },
    },
    "intransitive_verbs": {
        "rule": "replace final a by -ya",
        "examples": {
            "okuhaba": "okuhabya (make one lose one's way)",
            "okwoga": "okwogya (wash)",
            "okwaka": "okwakya (light, blaze, blow up fire)",
            "okubyama": "okubyamya (lay down, put to bed)",
        },
    },
}

# Passive verb formation
PASSIVE_FORMATION = {
    "monosyllabic_simple": {
        "rule": "add -ibwa or -ebwa with sound change",
        "examples": {
            "ha": "heebwa (be given)",
            "ta": "teebwa (be put)",
            "sa": "siibwa (be ground)",
        },
    },
    "monosyllabic_labialised": {
        "rule": "replace final vowel by -ibwa or -ebwa",
        "examples": {
            "cwa": "cwibwa (be broken)",
            "lya": "liibwa (be eaten)",
        },
    },
    "other_verbs": {
        "rule": "insert w before final a",
        "examples": {
            "gaba": "gabwa (be given)",
            "diida": "diidwa (be criticised)",
            "leha": "lehwa (be paid)",
        },
    },
}

# Neuter/Stative verb formation
NEUTER_FORMATION = {
    "rule_1": {
        "description": "replace final vowel by -ika, -eka, -ooka, -uuka",
        "examples": {
            "okwata": "okwatika (be smashed)",
            "okuewa": "okucweka (be broken)",
            "okugoorra": "okugoorrooka (be stretched out)",
            "okuhuuha": "okuhuuhuuka (be blown off)",
        },
    },
    "rule_2": {
        "description": "replace last syllable of verbs in -ra by -ka",
        "examples": {
            "okusobora": "okusoboka (be manageable)",
            "okutaagura": "okutaaguka (get torn)",
            "okujumbura": "okujumbuka (dash out, rush out)",
        },
    },
}

# Reciprocal/Associative verb formation
RECIPROCAL_FORMATION = {
    "suffix_ngana": {
        "description": "add -ngana for reciprocal action",
        "examples": {
            "okujuma": "okujumangana (scold each other)",
            "okuseka": "okusekangana (laugh at each other)",
            "okugonza": "okugonzangana (love each other)",
        },
    },
    "suffix_na": {
        "description": "add -na for associative concept",
        "examples": {
            "okuganja": "okuganjana (make friends, be friendly)",
            "okuliira": "okuliirana (share, be partners)",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# MOODS AND TENSES (Chapter 13) — from OCR
# ─────────────────────────────────────────────────────────────────────────────

# Imperative mood tenses
IMPERATIVE_TENSES = {
    "present": {
        "singular": "verb stem ending in -a (e.g. Genda 'Go!')",
        "plural": "subjunctive form with -e (e.g. Mugende 'Go!')",
        "negative_sg": "Otagenda 'Don't go!'",
        "negative_pl": "Mutagenda 'Do not go!'",
    },
    "continuous_present": {
        "singular": "suffix -ga (e.g. Ikarraga 'Sit for a while')",
        "plural": "subjunctive with -ge (e.g. Mwikaarreege 'Sit for a while')",
        "negative_sg": "totemaga 'do not habitually cut'",
        "negative_pl": "timutemaga 'do not habitually cut'",
    },
    "near_future": {
        "description": "commands to be obeyed within a few hours",
        "positive": "subjunctive form (e.g. Nyenkya oije kara 'Come early tomorrow')",
        "negative": "present tense form (e.g. Nyenkya otaija 'Don't come tomorrow')",
    },
    "far_future": {
        "description": "commands beyond near future limit",
        "positive": "subjunctive form (e.g. Obu olimubona omunsabire 'When you see him ask him')",
        "negative": "inverted -ta + -li- (e.g. Obu olimubona otalimusaba 'When you see him don't ask')",
    },
    "continuous_future": {
        "description": "command to be obeyed continuously from moment of speaking",
        "positive": "subjunctive with -ge (e.g. Otiineege so 'Fear your father')",
        "negative": "Otalihangiirra 'Never bear false witness'",
    },
}

# Subjunctive mood functions
SUBJUNCTIVE_FUNCTIONS = {
    "purpose": "express purpose or reason for command",
    "thought": "express a thought or suggestion",
    "permission": "express a question of permissive nature",
    "wish": "express wish (often with particle ka)",
}

SUBJUNCTIVE_EXAMPLES = {
    "purpose": [
        ("Genda omwirwarro bakuhe omubazi.", "Go to hospital and get medicine."),
        ("Mwege kusoma bwino mubinge butamanya.", "Learn to read so you may overcome ignorance."),
    ],
    "thought": [
        ("Ka ngende (Leka ngende).", "Let me go; allow me to go."),
        ("Butwiriirre tugoonye.", "If sun sets before we complete journey, we shall lodge."),
    ],
    "permission": [
        ("Boojo ngende nandiki nyeerekere?", "May I go or may I just abandon the journey?"),
        ("Ndeete amaizi?", "May I bring the water?"),
    ],
    "wish": [
        ("Kaije!", "Welcome!"),
        ("Kasangwe!", "Well found!"),
    ],
}

# Indicative mood tenses
INDICATIVE_TENSES = {
    "present_indefinite": {
        "description": "expresses customary action",
        "formation": "no tense prefix, only pronominal prefixes/concords",
        "examples": {
            "positive": "Abahuma banywa amata (Cattle keepers drink milk)",
            "negative": "Abaana barungi tibanya maarwa (Good children do not drink beer)",
        },
    },
    "present_imperfect": {
        "description": "action still continuing or imperfect in present time",
        "tense_prefix": "ni- (before consonant/i), na- (before a), ne- (before e), no- (before o)",
        "negative_prefix": "ruku-",
        "examples": {
            "positive": "Engoma niigamba (Drums are sounding)",
            "negative": "Engoma tiirukugamba (Drums are not sounding)",
        },
    },
    "present_perfect": {
        "description": "action or state complete at moment of speaking",
        "formation": "tense suffixes according to verb ending",
        "examples": {
            "positive": "Omugurusi amwire omuleju (The old man has shaved the beard)",
            "negative": "Omusaija onu tamwire muleju gwe (This man has not shaved his beard)",
        },
    },
    "virtual_present": {
        "description": "something just happened or in danger of happening",
        "tense_prefix": "-a- after pronominal prefix",
        "examples": {
            "positive": "Enjura yagwa (It is starting to rain / about to rain)",
            "negative": "Enjura emazire tiyagwa (Fortunately it did not rain)",
        },
    },
}

# Special verbs -ina (to have) and -li (to be)
VERB_INA_CONJUGATION = {
    "present_positive": {
        "1sg": "nyina", "2sg": "oina", "3sg": "aina",
        "1pl": "tuina", "2pl": "muina", "3pl": "baina",
    },
    "present_negative": {
        "1sg": "tiinyina", "2sg": "toina", "3sg": "taina",
        "1pl": "titwina", "2pl": "timwina", "3pl": "tibaina",
    },
}

VERB_LI_CONJUGATION = {
    "present_positive": {
        "1sg": "ndi", "2sg": "oli", "3sg": "ali",
        "1pl": "tuli", "2pl": "muli", "3pl": "bali",
    },
    "present_negative": {
        "1sg": "tindi", "2sg": "toli", "3sg": "tali",
        "1pl": "tituli", "2pl": "timuli", "3pl": "tibali",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# NOUN CLASSES (Chapter 7) — Extended details from OCR
# ─────────────────────────────────────────────────────────────────────────────

# Class 12/13/14 formation details
CLASS_12_13_14_DETAILS = {
    "class_12": {
        "prefix": "aka- (akw- before vowel)",
        "description": "diminutives (singular)",
        "examples": [
            ("akajuma", "grain, pill"),
            ("akanono", "tiny nail, claw"),
            ("akaara", "tiny finger, toe"),
            ("akanyamunkogoto", "tortoise"),
        ],
    },
    "class_13": {
        "prefix": "utu- (utw- before vowel)",
        "description": "diminutives (plural) / small quantities",
        "formation": "substituted for normal class prefixes to indicate diminution",
        "examples": [
            ("otuta", "a little milk (never akata)"),
            ("otwarwa", "a little beer, dregs of beer (never akaarwa)"),
            ("otwizi", "a little water, a drop of water (never akaizi)"),
        ],
        "function": "functions as plural of Class 12, though normal plural is Class 14",
    },
    "class_14": {
        "prefix": "obu- (obw- before vowel)",
        "description": "abstract nouns, mass nouns",
        "examples": [
            ("obujuma", "grains (pl. of akajuma)"),
            ("obunono", "tiny nails (pl. of akanono)"),
            ("obwara", "tiny fingers (pl. of akaara)"),
        ],
    },
}

# Augmentative/Pejorative prefix substitution (extended)
AUGMENTATIVE_PEJORATIVE_EXTENDED = {
    "oru_substitution": {
        "description": "oru- substituted for normal class prefix = augmentative or pejorative",
        "examples": [
            ("orusaija", "omusaija", "man", "clumsy/big man (pejorative)"),
            ("orukazi", "omukazi", "woman", "clumsy woman"),
            ("orwisiki", "omwisiki", "girl", "clumsy girl"),
            ("orute", "ente", "cow", "clumsy cow"),
            ("oruti", "omuti", "tree", "long stick"),
            ("orunyonyi", "enyonyi", "bird", "big long bird"),
        ],
    },
    "eki_substitution": {
        "description": "eki-/eky- substituted = magnitude, affection, or contempt",
        "examples": [
            ("ekisaija", "omusaija", "man", "that clumsy/big man (contempt)"),
            ("ekiiru", "omwiru", "servant", "dear poor man (affection) / sturdy peasant"),
            ("ekintu", "okintu", "thing", "monster-like thing"),
        ],
    },
    "eri_substitution": {
        "description": "eri-/ery- substituted = magnitude",
        "examples": [
            ("eriiru", "omwiru", "servant", "that sturdy peasant"),
            ("erintu", "okintu", "thing", "monster-like thing"),
            ("eryana", "omwana", "child", "insolent child"),
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# NUMBERS AND ORDINALS (Chapter 4) — Extended from OCR
# ─────────────────────────────────────────────────────────────────────────────

# Ordinal formation
ORDINAL_FORMATION = {
    "first": {
        "rule": "okubanza 'to begin, come first' preceded by genitive particle",
        "examples": [
            ("omwana (o)w'okubanza", "the first child"),
            ("abantu (a)b'okubanza", "the first men"),
            ("ibara lye ery'okubanza", "his first name"),
            ("ekigambo (e)ky'okubanza", "the first word"),
        ],
    },
    "second_to_fifth": {
        "rule": "adverbial prefix ka- + numeral stem + genitive particle",
        "examples": [
            ("omwaka (o)gwa kabiri", "(the) second year"),
            ("ekitebe (e)kya kasatu", "(the) third class"),
            ("orukumo (o)rwa kataano", "(the) fifth finger"),
        ],
    },
}

# Hundreds/thousands connection
NUMBER_CONNECTION = {
    "rule": "hundreds/thousands connected by 'mu' and 'na'",
    "examples": [
        ("ente bibiri mu asatu na itaano", "235 cows"),
        ("emiti rukumi bina n'ataano", "1450 trees"),
    ],
    "note": "'mu' may be dropped in some cases",
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_derivative_verb_type(verb: str) -> str | None:
    """Identify derivative verb type based on suffix."""
    v = verb.lower().strip()
    if v.endswith(("ira", "era")):
        return "applied/prepositional"
    elif v.endswith(("isa", "esa", "ya")):
        return "causative"
    elif v.endswith(("ibwa", "ebwa", "wa")):
        return "passive"
    elif v.endswith(("ika", "eka", "oka", "uka")):
        return "neuter/stative"
    elif v.endswith(("ura", "ora", "uurra", "oorra")):
        return "conversive/reversive"
    elif v.endswith(("ngana", "na")):
        return "reciprocal/associative"
    return None


def get_imperative_form(verb_stem: str, number: str = "singular", tense: str = "present") -> str:
    """Generate imperative form for a verb stem."""
    if tense == "present":
        if number == "singular":
            return verb_stem  # ends in -a
        else:  # plural
            return "mu" + verb_stem[:-1] + "e"  # subjunctive
    elif tense == "continuous_present":
        if number == "singular":
            return verb_stem[:-1] + "ga"
        else:
            return "mw" + verb_stem[:-1] + "eege"
    return verb_stem


def is_reflexive_verb(verb: str) -> bool:
    """Check if verb is reflexive (starts with okw-e)."""
    v = verb.lower().strip()
    return v.startswith("okwe") or v.startswith("okw-e")


def get_full_grammar_context() -> str:
    """Complete grammar context including all OCR-derived rules."""
    from language_rules import get_extended_grammar_context
    
    base = get_extended_grammar_context()
    
    additional = (
        "\n--- Additional OCR Grammar Rules ---\n"
        "DERIVATIVE VERBS:\n"
        "  Applied/Prepositional (-ira/-era): action done for/at/with reference to place/time/cause\n"
        "    e.g. okubohera (tie cow's legs when milking), okutemera (plant beans with hoe)\n"
        "  Causative (-isa/-esa/-ya): cause action to happen, primary/secondary agent\n"
        "    e.g. okuhabya (make one lose way), okubazisa (help one speak)\n"
        "  Passive (-ibwa/-ebwa/-wa): subject receives/suffers action\n"
        "    e.g. heebwa (be given), cwibwa (be broken), gabwa (be given)\n"
        "  Neuter/Stative (-ika/-eka/-oka/-uka): possibility/capability/state after action\n"
        "    e.g. okwatika (be smashed), okucweka (be broken), okusoboka (be manageable)\n"
        "  Conversive/Reversive (-ura/-ora/-uka/-oka): opposite/change from verb root meaning\n"
        "    e.g. okubambura (unpeg), okubambuka (come unpegged)\n"
        "  Reciprocal/Associative (-ngana/-na): action done simultaneously/reciprocally\n"
        "    e.g. okugonzangana (love each other), okuganjana (make friends)\n"
        "\nMOODS AND TENSES:\n"
        "  Imperative: Present (Genda!), Continuous (Ikarraga), Near Future (Nyenkya oije),\n"
        "              Far Future (Obu olimubona), Continuous Future (Otiineege)\n"
        "  Subjunctive: purpose, thought, permission, wish (often with ka-)\n"
        "  Indicative: Present Indefinite (customary), Present Imperfect (ni-/na-/ne-/no-),\n"
        "              Present Perfect (tense suffixes), Virtual Present (-a- just happened)\n"
        "\nSPECIAL VERBS:\n"
        "  -ina (to have): nyina/oina/aina/tuina/muina/baina\n"
        "  -li (to be): ndi/oli/ali/tuli/muli/bali\n"
        "\nNOUN CLASSES (extended):\n"
        "  Class 12 (aka-): diminutives singular (akajuma 'grain', akanono 'tiny nail')\n"
        "  Class 13 (utu-/otw-): diminutives plural/small quantities (otuta 'little milk')\n"
        "  Class 14 (obu-/obw-): abstract/mass nouns, also plural of class 12\n"
        "  Augmentative: oru- substitution = pejorative (orusaija 'clumsy man')\n"
        "  Magnitude: eki- substitution = contempt/affection (ekisaija 'that clumsy man')\n"
        "\nORDINALS:\n"
        "  1st: genitive + okubanza (omwana w'okubanza 'first child')\n"
        "  2nd-5th: genitive + ka- + numeral (omwaka gwa kabiri 'second year')\n"
    )
    
    return base + additional


# ─────────────────────────────────────────────────────────────────────────────
# NOUN FORMATION (Chapters 9 & 10) — from OCR grammar2_noun_formation
# ─────────────────────────────────────────────────────────────────────────────

# Deverbative noun suffixes
DEVERBATIVE_SUFFIXES = {
    "-u": {
        "description": "forms nouns denoting state or noun agents",
        "examples": {
            "fu": ("okufa", "dead person", "to die"),
            "kuru": ("okukura", "old person", "to grow old"),
            "zigu": ("okuziga", "enemy", "to track, surround in hunting"),
        },
    },
    "-zi": {
        "description": "forms noun agents (one who does the action)",
        "examples": {
            "omurozi": ("okurora", "looker on", "to see"),
            "omubaizi": ("okubaija", "carpenter", "to do carpentry"),
            "omusengiizi": ("okusengiija", "one who filters", "to filter"),
            "omuhiizi": ("okuhiija", "one who pants", "to pant"),
        },
    },
    "-gu": {
        "description": "forms nouns from verb roots (less common)",
        "examples": {},
    },
}

# Noun functions in sentences
NOUN_FUNCTIONS = {
    "subject": {
        "description": "noun as subject of verb",
        "examples": [
            ("Omunyoro alina omwigo.", "The chief has a walking stick."),
            ("Omusomesa naarora engoma.", "The catechist is looking at the drum."),
            ("Omwegesa akahandiika ebigambo harubbaaho.", "The teacher wrote some words on the blackboard."),
        ],
    },
    "object": {
        "description": "noun as object of verb",
        "examples": [
            ("Embwa ekwasire omusu.", "The dog has killed an edible rat."),
            ("Omukazi azaire omwana.", "A woman has given birth to a child."),
            ("Byakisaka aguzire ente.", "Byakisaka has bought a cow."),
        ],
    },
    "apposition": {
        "description": "noun as apposition or attribute to another noun",
        "examples": [
            ("Kiiza, omurongo, ninkuligira.", "I am in love with you Kiiza the child who comes next to twins."),
        ],
    },
}

# Kinds of nouns
NOUN_KINDS = {
    "proper": {
        "description": "names for individual persons, things, places, countries",
        "rule": "proper nouns begin with a capital letter",
        "examples": {
            "people": ["Rwakaikara", "Kaikara", "Kaaheeru", "Peetero", "Yohaana"],
            "places": ["Butiiti", "Bujumbura", "Mparo", "Kyegeegwa"],
            "countries": ["Bunyoro", "Tooro", "Nkole", "Kigezi", "Rwanda"],
            "towns": ["Kaseese", "Masindi", "Kabarole", "Hoima", "Mbarara"],
        },
    },
    "common": {
        "description": "names used for any member of a class",
        "examples": ["omuntu (person)", "ekisoro (animal, beast)", "orusozi (mountain)"],
    },
}

# Verbal nouns (class 5 eri-/ery-)
VERBAL_NOUNS_CLASS5 = {
    "igesa": ("okugesa", "harvest, reaping time", "to reap, harvest"),
    "izaara": ("okuzaara", "time when a woman gives birth", "to give birth, produce, bear"),
    "igenda": ("okugenda", "the going (verbal idea)", "to go"),
    "ihiisa": ("okuhiisa", "the brewing (verbal idea)", "to brew"),
}

# ─────────────────────────────────────────────────────────────────────────────
# NOUN CLASS 6 DETAILS (Chapter 7) — from OCR grammar_noun_classes
# ─────────────────────────────────────────────────────────────────────────────

# Class 6 as plural of class 5 — prefix rules
CLASS6_PLURAL_RULES = {
    "ama_before_consonant_a_i": {
        "rule": "ama- before consonant and vowels a, i",
        "examples": [
            ("amabara", "ibara", "name"),
            ("amaato", "eryato", "boat, canoe"),
            ("amaiba", "eriiba", "dove, pigeon"),
        ],
    },
    "ame_before_e": {
        "rule": "ame- before e",
        "examples": [
            ("ameegero", "eryegero", "school"),
            ("ameegesezo", "eryegesezo", "classroom"),
        ],
    },
    "amo_before_o": {
        "rule": "amo- before o",
        "examples": [
            ("amoozi", "eryozi", "edible gourd"),
            ("amooga", "eryoga", "time of bathing"),
        ],
    },
}

# Class 6 as plural of other classes
CLASS6_OTHER_PLURALS = {
    "amaju": ("enju", "house", "class 9"),
    "amara": ("orura", "intestine", "class 11"),
    "amahyo": ("obuhyo", "flock, herd", "class 14"),
    "amaguru": ("okuguru", "leg", "class 15"),
}

# ─────────────────────────────────────────────────────────────────────────────
# WORDS, AFFIXES & NEGATION (Chapter 4) — from OCR grammar_words_affixes_1/2
# ─────────────────────────────────────────────────────────────────────────────

# Extended negation words with full sentence examples
NEGATION_EXTENDED = {
    "declinable": {
        "description": "built on root -aha + genitive particle; answers questions about presence",
        "examples": [
            ("Waaha, taroho.", "No, he is not there."),
            ("Ente zaaha, tiziizire.", "No, cows have not come."),
            ("Karamoja ebyokulya byahayo.", "There is no food in Karamoja."),
            ("Kwaha, tagenzire.", "No, he has not gone. (blunt no, with class 15 kwa)"),
        ],
    },
    "undeclinable": {
        "A'a": "Refrain from troubling the people, I do not want it.",
        "Nangwa": "No, I am not going there!",
        "Nga": "No, come here, I am not going to beat you.",
        "Naakataito": "He does not at all know how to read.",
        "Naakake": "same use as Naakataito",
        "Busa": "He does not know anything at all.",
        "Nangwa busa": "He has done nothing wrong.",
        "Busaho": "No, he will not come this way.",
        "Ntai": "God forbid, where did I meet him!",
    },
}

# Affirmation words
AFFIRMATION_WORDS = {
    "Ke": "Yes (simple affirmation)",
    "Mi": "Yes, you may",
    "Ego": "Yes (formal affirmation)",
    "Nukwo": "Yes, that's it / isn't it?",
    "Ego kwo": "Yes indeed / truly yes",
}

# Possessive pronouns — genitive particle + self-standing pronoun
POSSESSIVE_PRONOUNS = {
    # class: (genitive_particle, self_standing_pronoun, example)
    1:  ("wa-/waa-/w-",  "-nge",  "omwana wange (my child)"),
    2:  ("ba-/baa-/b-",  "-itu",  "abaana baitu (our children)"),
    3:  ("gwa-/gw-",     "-gwo",  "omutwe gwange (my head)"),
    4:  ("ya-/yaa-/y-",  "-yo",   "emitaano yaitu (our boundaries)"),
    5:  ("lya-/ly-",     "-lyo",  "eryato lyange (my boat)"),
    6:  ("ga-/gaa-/g-",  "-go",   "amagezi gaabo (their wisdom)"),
    7:  ("kya-/ky-",     "-kyo",  "ekitiinisa kyawe (your honour)"),
    8:  ("bya-/by-",     "-byo",  "ebitabu byanyu (your books)"),
    9:  ("ya-/yaa-/y-",  "-yo",   "ente yaitu (our cow)"),
    10: ("za-/zaa-/z-",  "-zo",   "ente zaitu (our cattle)"),
    11: ("rwa-/rw-",     "-rwo",  "orugoye rwe (her cloth)"),
    12: ("ka-/kaa-/k-",  "-ko",   "akasozi kange (my hill)"),
    13: ("twa-/tw-",     "-two",  "otwizi twange (my little water)"),
    14: ("bwa-/bw-",     "-bwo",  "obwana bwange (my little children)"),
    15: ("kwa-/kw-",     "-kwo",  "okuguru kwange (my leg)"),
}

# Genitive particle elision rules
GENITIVE_ELISION_RULES = {
    "rule": "The -a of relationship is always elided before another vowel; marked by apostrophe",
    "contexts": [
        ("between two nouns", "omwana wa Byaruhanga → omwana w'Omuhangi"),
        ("between noun and interrogative", "Omukazi onu w'oha? (Whose woman is this?)"),
        ("between noun and ki?", "Ebitabu binu byaki? (For what purpose are these books?)"),
        ("between noun and ordinal numeral", "ekitabu ky'okubanza (the first book)"),
        ("between noun and possessive pronoun", "omwana wange (my child)"),
    ],
    "pronunciation_note": (
        "Though -a is not written before vowels, particles must be pronounced long: "
        "aba → abaa, aga → agaa, eza → ezaa, aka → akaa"
    ),
}

# Interrogative particles
INTERROGATIVE_PARTICLES = {
    "ki?": {
        "meaning": "What?",
        "examples": [
            ("Ruhanga kintu ki?", "What is God?"),
            ("Mbaire ndeesire ki?", "What had I brought?"),
            ("Ogambire ki?", "What have you said?"),
        ],
    },
    "di? / li?": {
        "meaning": "When?",
        "examples": [
            ("Okaija di?", "When did you come?"),
            ("Oliija di owaitu?", "When will you come to our home?"),
        ],
    },
    "nkaha? / -ha?": {
        "meaning": "Where?",
        "examples": [
            ("Ruhanga ali nkaha?", "Where is God?"),
            ("Banu bantu ba nkaha?", "From where are these people?"),
        ],
    },
    "habwaki?": {
        "meaning": "Why?",
        "examples": [
            ("Habwaki ongarukamu oti?", "Why do you answer me like that?"),
        ],
    },
}

# Parts of speech summary
PARTS_OF_SPEECH = {
    "nouns": "names of things concrete or abstract (e.g. ente 'cow', amagezi 'intelligence')",
    "verbs": "words signifying actions connected with nouns, in concordial agreement (e.g. Omuhuma naakama ente)",
    "adjectives": "words qualifying nouns, in concordial agreement (e.g. omukazi omurungi 'a good woman')",
    "pronouns": "words signifying things without being their names (e.g. nyowe 'I', itwe 'we', uwe 'he/she')",
    "numerals": "qualify nouns in terms of quantity; 1-5 take numeral concords (e.g. omuntu omu 'one person')",
    "adverbs": "describe verbs/adjectives re manner, place, time (e.g. Ohandiikire kurungi 'You have written well')",
    "ideophones": "adverbs describing intensity of manner/sound/smell/action (e.g. okwera tiitiiti 'intensely white')",
    "interjections": "express pity, surprise, joy, anger etc.; no grammatical bearing on sentence",
    "joining_words": "particles expressing relation between persons/objects or joining words/phrases/sentences",
}

# Ideophones (intensity words)
IDEOPHONES = {
    "cuucuucu": "intensity with smell (okununka cuucuucu)",
    "siisiisi": "intensity with being black (okwiragura siisiisi)",
    "tiitiiti": "intensity with being white (okwera tiitiiti)",
    "nulinuli": "tasting very sweet (okunuliirra nulinuli)",
    "peepeepe": "tasting very bitter (okusaarra peepeepe)",
    "begebege": "intensity with being hot (okwokya begebege)",
    "tukutuku": "intensity with being red (okutukura tukutuku)",
}

# ─────────────────────────────────────────────────────────────────────────────
# NUMBERS & ORDINALS EXTENDED (Chapter 4) — from OCR grammar_numbers_ordinals
# ─────────────────────────────────────────────────────────────────────────────

# Ordinals 6th-10th and above 10th
ORDINALS_EXTENDED = {
    "6th_to_10th": {
        "rule": "cardinals (without initial vowel) preceded by genitive particle",
        "examples": [
            ("ekiragiro kya mukaaga", "the sixth commandment"),
            ("omwaka gwa musanju", "the seventh year"),
        ],
    },
    "above_10th": {
        "rule": "cardinals preceded by genitive particle; units connected by na; 2-5 take plural numeral concord",
        "examples": [
            ("okwezi kwa ikumi na kumu", "the eleventh month"),
            ("omumwaka gwa ikumi ne'taano", "in the fifteenth year"),
            ("omurundi ogwa nsanju na musanju", "the seventy seventh time"),
        ],
    },
    "fractions": {
        "rule": "numerator first (class 7 prefix for 1, class 8 for 2-5) + genitive + denominator with ka-",
        "examples": [
            ("kimu kya kabiri", "1/2 (one half)"),
            ("bibiri bya kataano", "2/5 (two fifths)"),
        ],
    },
}

# Adverbial use of ka- prefix with numerals
NUMERAL_ADVERBIAL_KA = {
    "rule": "prefix ka- on numeral = how many times / nth occurrence",
    "examples": [
        ("Wakamurora kaingaha?", "How many times have you seen him?"),
        ("Yakazaara kasatu.", "She has given birth three times."),
        ("Twakagyayo kabiri.", "We have been there twice."),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# ORTHOGRAPHY RULES (1995 Guide) — from OCR runyoro_rutooro_orthography_guide
# ─────────────────────────────────────────────────────────────────────────────

ORTHOGRAPHY_RULES = {
    "alphabet": {
        "vowels": ["a", "e", "i", "o", "u"],
        "consonants": ["b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s", "t", "v", "w", "y", "z"],
        "note": "19 consonants total; q, v, x absent from native vocabulary",
    },
    "rule_c": "c shall always be used without h (e.g. icumu 'spear', omuceeri 'rice')",
    "rule_l": {
        "use_l_before": ["ya", "ye", "yo", "-e", "-i (unless e or i precedes)"],
        "examples_l": ["okulya (to eat)", "okuleka (to leave)", "okulima (to cultivate)"],
    },
    "rule_r": "r used in all cases where l is not used (e.g. omuceeri, okumira, omusiri)",
    "double_consonants": {
        "b_doubled": "indicates non-bilabial fricative b (e.g. ibbango 'hump', ekibbira 'royal court')",
        "m_doubled": "used in nasal compounds (e.g. emmango 'shafts of spears')",
        "n_doubled": "used in nasal compounds before nasals",
        "c_doubled": "for certain phonological reasons",
    },
    "long_vowels": "doubled vowel indicates long vowel (e.g. aa, ee, ii, oo, uu)",
    "apostrophe": "marks elision of initial vowel in fast speech (e.g. n'ente, z'ente, k'oboine)",
    "source": "Ministry of Gender and Community Development, Uganda, 1st Edition 1995",
}
