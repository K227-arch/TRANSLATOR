"""
Runyoro-Rutooro language rules.
Sources:
  - A Grammar of Runyoro-Rutooro (Chapters 2, 4, 7, 13, 15, 16)
  - Runyoro-Rutooro Orthography Guide (Ministry of Gender, Uganda, 1995)
  - runyorodictionary.com
"""
import re as _re
try:
    from language_rules_extra import *  # noqa: F401,F403
except ImportError:
    pass  # extra rules not available in this environment

# ─────────────────────────────────────────────────────────────────────────────
# ALPHABET & ORTHOGRAPHY
# Source: Runyoro-Rutooro Orthography Guide (1995)
# ─────────────────────────────────────────────────────────────────────────────

ALPHABET = list("abcdefghijklmnoprstuwyz")
# Letters NOT in Runyoro-Rutooro: q, v, x
ABSENT_LETTERS = {"q", "v", "x"}

VOWELS = {"a", "e", "i", "o", "u"}

# Vowel length: doubled vowel = long vowel
# e.g. aa, ee, ii, oo, uu indicate long vowels
LONG_VOWEL_PATTERN = _re.compile(r'([aeiou])\1', _re.IGNORECASE)

# Diphthongs common in Runyoro-Rutooro
DIPHTHONGS = {"ai", "oi", "ei", "au", "ou"}

# Apostrophe rule: used when initial vowel of a word is swallowed in fast speech
# e.g.  n' + ente  -> n'ente,  z' + ente -> z'ente
APOSTROPHE_CONTEXTS = [
    ("n'", "with/and (before nouns starting with vowel)"),
    ("z'", "of (class 10, before vowel-initial nouns)"),
    ("k'", "it is (before vowel)"),
    ("y'", "of (class 9, before vowel)"),
    ("w'", "of (class 1, before vowel)"),
    ("g'", "of (class 3/6, before vowel)"),
    ("b'", "of (class 2, before vowel)"),
]

# ─────────────────────────────────────────────────────────────────────────────
# R / L RULE
# Source: Orthography Guide + Grammar Ch.2
# ─────────────────────────────────────────────────────────────────────────────

RL_RULE = (
    "R/L Rule: In Runyoro-Rutooro, 'R' is the dominant consonant. "
    "'L' is only used immediately before or after the vowels 'e' or 'i'. "
    "In all other positions 'R' is used instead of 'L'."
)

def apply_rl_rule(text: str) -> str:
    """Replace L with R except when adjacent to e or i."""
    if not text:
        return text
    chars = list(text)
    result = []
    for i, ch in enumerate(chars):
        if ch not in ('l', 'L'):
            result.append(ch)
            continue
        prev = chars[i - 1].lower() if i > 0 else ''
        nxt  = chars[i + 1].lower() if i < len(chars) - 1 else ''
        if prev in ('e', 'i') or nxt in ('e', 'i'):
            result.append(ch)
        else:
            result.append('R' if ch.isupper() else 'r')
    return ''.join(result)


# ─────────────────────────────────────────────────────────────────────────────
# SOUND CHANGE RULES
# Source: Grammar Ch.2 — Sound change in vowels and consonants
# ─────────────────────────────────────────────────────────────────────────────

# Consonant + suffix transformations (applied to verb stems)
# r/t/j + -ire/-ere/-i/-ya undergo the following changes:
CONSONANT_SUFFIX_CHANGES = {
    # (stem_final_consonant, suffix) -> result
    ("r",  "-ire"):  "-zire",
    ("r",  "-i"):    "-zi",
    ("r",  "-ya"):   "-za",
    ("t",  "-ire"):  "-sire",
    ("t",  "-i"):    "-si",
    ("t",  "-ya"):   "-sa",
    ("j",  "-ire"):  "-zire",
    ("j",  "-i"):    "-zi",
    ("nd", "-ire"):  "-nzire",
    ("nd", "-i"):    "-nzi",
    ("nd", "-ya"):   "-nza",
    ("nt", "-ire"):  "-nsire",
    ("nt", "-i"):    "-nsi",
    ("nt", "-ya"):   "-nsa",
}

# Nasal assimilation: n before bilabials b/p -> m
# n + b -> mb,  n + m -> mm
NASAL_ASSIMILATION = {
    "nb": "mb",
    "np": "mp",
    "nm": "mm",
    "nr": "nd",   # n + r -> nd (Meinhof's rule)
    "nl": "nd",
}

# Present imperfect prefix ni- vowel change before certain concords
# ni + u-class concord -> nu
# e.g. nimugenda -> numugenda, niguteera -> nuguteera
NI_PREFIX_CHANGE = {
    "nimu": "numu",
    "nigu": "nugu",
    "niru": "nuru",
    "nibu": "nubu",
    "nikw": "nukw",
}

# Y-insertion rule: after tense prefixes a-, ra-, raa- with subject prefixes,
# y is inserted before verb stems beginning with a vowel
# e.g. a + ira -> ayira,  ra + ira -> rayira
Y_INSERTION_PREFIXES = {"a", "ra", "raa", "daa"}

# Reflexive verb imperatives: stem begins with e but singular imperative uses w + long vowel
# e.g. okw-esereka -> weesereke (hide yourself)
REFLEXIVE_IMPERATIVE_PREFIX = "wee"
REFLEXIVE_PLURAL_PREFIX = "mwe"

# Conversive verb suffix rule:
# If simple stem vowel is a/e/i/o -> conversive suffix starts with u
# If simple stem vowel is o (long oo) -> conversive suffix starts with o
CONVERSIVE_SUFFIX = {
    "a": "ura", "e": "ura", "i": "ura", "u": "ura",
    "o": "ora",  # long o
}

# ─────────────────────────────────────────────────────────────────────────────
# NOUN CLASS SYSTEM  (Classes 1–15)
# Source: Grammar Ch.7 — The noun class system
# ─────────────────────────────────────────────────────────────────────────────

# Each entry: class_number -> {prefix, plural_class, plural_prefix, description}
NOUN_CLASSES = {
    1:  {"sg_prefix": "omu-",  "sg_prefix_v": "omw-",  "pl_class": 2,  "pl_prefix": "aba-",  "pl_prefix_v": "ab-",   "desc": "persons (singular)"},
    2:  {"sg_prefix": "aba-",  "sg_prefix_v": "ab-",   "pl_class": 1,  "pl_prefix": "omu-",  "pl_prefix_v": "omw-",  "desc": "persons (plural)"},
    "1a": {"sg_prefix": "",    "pl_prefix": "baa-",    "desc": "proper names, titles (no prefix)"},
    "2a": {"sg_prefix": "baa-","pl_prefix": "",         "desc": "plural of class 1a proper names"},
    3:  {"sg_prefix": "emi-",  "sg_prefix_v": "emy-",  "pl_class": 4,  "pl_prefix": "emi-",  "desc": "trees, plants, body parts (singular)"},
    4:  {"sg_prefix": "emi-",  "pl_class": 3,  "pl_prefix": "omu-", "desc": "plural of class 3"},
    5:  {"sg_prefix": "eri-",  "sg_prefix_v": "ery-",  "pl_class": 6,  "pl_prefix": "ama-",  "pl_prefix_e": "ame-", "pl_prefix_o": "amo-", "desc": "augmentatives, some body parts (singular)"},
    6:  {"sg_prefix": "ama-",  "sg_prefix_e": "ame-",  "sg_prefix_o": "amo-", "pl_class": 5, "desc": "plural of class 5; also plural of classes 9/11/14/15"},
    7:  {"sg_prefix": "eki-",  "sg_prefix_v": "eky-",  "pl_class": 8,  "pl_prefix": "ebi-",  "pl_prefix_v": "eby-",  "desc": "things, abstracts, diminutives (singular)"},
    8:  {"sg_prefix": "ebi-",  "sg_prefix_v": "eby-",  "pl_class": 7,  "pl_prefix": "eki-",  "pl_prefix_v": "eky-",  "desc": "plural of class 7"},
    9:  {"sg_prefix": "en-",   "sg_prefix_b": "em-",   "pl_class": 10, "pl_prefix": "en-",   "desc": "animals, foreign words (singular); prefix en- before consonants, em- before b/p"},
    10: {"sg_prefix": "en-",   "sg_prefix_b": "em-",   "pl_class": 9,  "desc": "plural of class 9; also plural of class 11"},
    "9a": {"sg_prefix": "",    "pl_class": "10a", "pl_prefix": "zaa-", "desc": "foreign words, colours, animal names, place names (no prefix, no initial vowel)"},
    "10a":{"sg_prefix": "zaa-","sg_prefix_a": "za-", "sg_prefix_e": "ze-", "sg_prefix_o": "zo-", "desc": "plural of class 9a"},
    11: {"sg_prefix": "oru-",  "sg_prefix_v": "orw-",  "pl_class": 10, "pl_prefix": "en-",   "desc": "long/thin objects, languages, abstract (singular)"},
    12: {"sg_prefix": "aka-",  "sg_prefix_v": "akw-",  "pl_class": 13, "pl_prefix": "utu-",  "desc": "diminutives (singular)"},
    13: {"sg_prefix": "utu-",  "sg_prefix_v": "utw-",  "pl_class": 12, "pl_prefix": "aka-",  "desc": "diminutives (plural) / small quantities"},
    14: {"sg_prefix": "obu-",  "sg_prefix_v": "obw-",  "pl_class": 6,  "pl_prefix": "ama-",  "desc": "abstract nouns, mass nouns"},
    15: {"sg_prefix": "oku-",  "sg_prefix_v": "okw-",  "pl_class": 6,  "pl_prefix": "ama-",  "desc": "verbal infinitives, body parts"},
}

# Prefix -> class lookup (for morphological analysis)
PREFIX_TO_CLASS: dict[str, list] = {
    "omu": [1], "omw": [1], "aba": [2], "ab": [2],
    "emi": [3, 4], "emy": [3],
    "eri": [5], "ery": [5], "ama": [6], "ame": [6], "amo": [6],
    "eki": [7], "eky": [7], "ebi": [8], "eby": [8],
    "en":  [9, 10], "em": [9, 10],
    "oru": [11], "orw": [11],
    "aka": [12], "akw": [12],
    "utu": [13], "utw": [13],
    "obu": [14], "obw": [14],
    "oku": [15], "okw": [15],
    "zaa": ["10a"], "za": ["10a"], "ze": ["10a"], "zo": ["10a"],
    "baa": ["2a"],
}

def get_noun_class(word: str) -> list[int | str]:
    """Return probable noun class(es) for a Runyoro-Rutooro word based on prefix."""
    w = word.lower().strip()
    # Try matching with initial vowel first, then without
    for candidate in [w, w[1:] if w and w[0] in ('a', 'e', 'o') else w]:
        for prefix in sorted(PREFIX_TO_CLASS.keys(), key=len, reverse=True):
            if candidate.startswith(prefix):
                return PREFIX_TO_CLASS[prefix]
    return []

# ─────────────────────────────────────────────────────────────────────────────
# CONCORDIAL AGREEMENT
# Source: Grammar Ch.7 — noun class concordial prefixes
# Each noun class has its own subject concord, object concord, adjective concord
# ─────────────────────────────────────────────────────────────────────────────

# class -> (subject_concord, object_concord, adjective_concord, demonstrative)
CONCORDIAL_AGREEMENT = {
    1:    ("a-",   "-mu-",  "omu-",  "uyu"),
    2:    ("ba-",  "-ba-",  "aba-",  "aba"),
    "1a": ("a-",   "-mu-",  "",      "uyu"),
    "2a": ("ba-",  "-ba-",  "baa-",  "aba"),
    3:    ("gu-",  "-gu-",  "omu-",  "ogwo"),
    4:    ("gi-",  "-gi-",  "emi-",  "egi"),
    5:    ("li-",  "-li-",  "eri-",  "eryo"),
    6:    ("ga-",  "-ga-",  "ama-",  "ago"),
    7:    ("ki-",  "-ki-",  "eki-",  "ekyo"),
    8:    ("bi-",  "-bi-",  "ebi-",  "ebyo"),
    9:    ("i-",   "-i-",   "en-",   "eno"),
    10:   ("zi-",  "-zi-",  "en-",   "ezo"),
    "9a": ("i-",   "-i-",   "",      "eno"),
    "10a":("zi-",  "-zi-",  "",      "ezo"),
    11:   ("ru-",  "-ru-",  "oru-",  "orwo"),
    12:   ("ka-",  "-ka-",  "aka-",  "ako"),
    13:   ("tu-",  "-tu-",  "utu-",  "utu"),
    14:   ("bu-",  "-bu-",  "obu-",  "obwo"),
    15:   ("ku-",  "-ku-",  "oku-",  "okwo"),
}

def get_subject_concord(noun_class: int | str) -> str:
    entry = CONCORDIAL_AGREEMENT.get(noun_class)
    return entry[0] if entry else ""

def get_object_concord(noun_class: int | str) -> str:
    entry = CONCORDIAL_AGREEMENT.get(noun_class)
    return entry[1] if entry else ""


# ─────────────────────────────────────────────────────────────────────────────
# PLURAL FORMATION
# Source: Grammar Ch.7
# ─────────────────────────────────────────────────────────────────────────────

# Common sound changes in plural formation (class 11 -> class 10)
# oru- prefix drops, nasal prefix en-/em- added, with internal sound changes
PLURAL_SOUND_CHANGES = {
    "orubengo":  "emengo",   # lower millstone
    "orulimi":   "endimi",   # tongue/language
    "orugoye":   "engoye",   # cloth
    "orubabi":   "embabi",   # plantain leaf
    "orubaju":   "embaju",   # side/rib
    "orupapura": "empapura", # paper
    "oruseke":   "enseke",   # tube/pipe
    "orubango":  "emango",   # shaft of spear
    "oruhara":   "empara",   # baldness
    "orumuli":   "emuli",    # reed torch
    "orunwa":    "enwa",     # beak/bill
    "orunaku":   "enaku",    # stinging centipede
    "orunumbu":  "enumbu",   # edible tuber
    "orunyaanya":"enyaanya", # tomato
}

# Class 5 -> Class 6 plural prefix rules
# ama- before consonant and vowels a/i
# ame- before e,  amo- before o
def get_class6_prefix(stem: str) -> str:
    if not stem:
        return "ama"
    first = stem[0].lower()
    if first == 'e':
        return "ame"
    if first == 'o':
        return "amo"
    return "ama"

# ─────────────────────────────────────────────────────────────────────────────
# VERB STRUCTURE
# Source: Grammar Ch.4, Ch.13
# ─────────────────────────────────────────────────────────────────────────────

# Infinitive prefix: oku- (before consonant), okw- (before vowel)
INFINITIVE_PREFIX = "oku"
INFINITIVE_PREFIX_V = "okw"

# Subject prefixes (personal pronouns as verb prefixes)
SUBJECT_PREFIXES = {
    "1sg":  "n-",    # I
    "2sg":  "o-",    # you (sg)
    "3sg":  "a-",    # he/she
    "1pl":  "tu-",   # we
    "2pl":  "mu-",   # you (pl)
    "3pl":  "ba-",   # they
}

# Tense/aspect markers (inserted between subject prefix and verb stem)
TENSE_MARKERS = {
    "present_imperfect":  "ni-",   # ongoing action: nigenda = is going
    "recent_past":        "a-",    # just now: nayara = I just made the bed
    "remote_past":        "ka-",   # past: nkaara = I made the bed
    "future":             "ra-",   # future: ndaayara = I shall make the bed
    "perfect":            "i-",    # present perfect: nkozire = I have done
    "negative":           "ti-",   # negation prefix
    "habitual":           "mara-", # habitual/always
}

# Negative tense forms
NEGATIVE_MARKERS = {
    "present":      "ti-",
    "past":         "tinka-",
    "future":       "tinda-",
    "perfect":      "tinka-...-ire",
}

# Common verb suffixes
VERB_SUFFIXES = {
    "-ire / -ere":  "perfect tense",
    "-a":           "simple present / infinitive base",
    "-aho":         "completive (action done at a place)",
    "-anga":        "habitual/frequentative",
    "-isa / -esa":  "causative",
    "-ibwa / -ebwa":"passive",
    "-ana":         "reciprocal (each other)",
    "-ura / -ora":  "conversive/reversive (undo the action)",
    "-uka / -oka":  "intransitive conversive",
    "-rra":         "intensive/completive",
}

# Derivative verb suffixes
# Source: Grammar Ch.12 — Derivative verbs
DERIVATIVE_SUFFIXES = {
    "causative":      ["-isa", "-esa", "-ya"],
    "passive":        ["-ibwa", "-ebwa", "-wa"],
    "reciprocal":     ["-ana"],
    "reversive":      ["-ura", "-ora", "-ula", "-ola"],
    "neuter":         ["-uka", "-oka"],
    "intensive":      ["-rra", "-rruka", "-rrura"],
    "applied":        ["-era", "-ira"],   # action done for/at
    "positional":     ["-ama"],           # be in a position
}


# ─────────────────────────────────────────────────────────────────────────────
# TENSE SYSTEM SUMMARY
# Source: Grammar Ch.13, Ch.15
# ─────────────────────────────────────────────────────────────────────────────

TENSES = {
    "present_imperfect":    {"marker": "ni-",    "example": "nigenda",      "meaning": "is going"},
    "present_perfect":      {"marker": "-ire",   "example": "agenzire",     "meaning": "has gone"},
    "recent_past":          {"marker": "a-",     "example": "nayara",       "meaning": "just now I made the bed"},
    "remote_past":          {"marker": "ka-",    "example": "nkaara",       "meaning": "I made the bed (remote)"},
    "future_immediate":     {"marker": "ra-",    "example": "ndaayara",     "meaning": "I shall make the bed"},
    "future_remote":        {"marker": "raa-",   "example": "turaayara",    "meaning": "we shall make the bed"},
    "conditional":          {"marker": "-ku-",   "example": "obaire okukora","meaning": "if/when (conditional)"},
    "imperative_sg":        {"marker": "stem-a", "example": "genda",        "meaning": "go! (singular)"},
    "imperative_pl":        {"marker": "mu-stem-e","example": "mugende",    "meaning": "go! (plural)"},
    "negative_present":     {"marker": "ti-ni-", "example": "tinigenda",    "meaning": "is not going"},
    "negative_perfect":     {"marker": "tinka-", "example": "tinkagenzire", "meaning": "has not gone"},
}

# Conditional tense: obu/kuba + -ku- prefix
CONDITIONAL_PARTICLES = ["obu", "kuba", "kakuba", "kusangwa", "kakusangwa"]

# ─────────────────────────────────────────────────────────────────────────────
# ADJECTIVES & ADVERBS
# Source: Grammar Ch.16
# ─────────────────────────────────────────────────────────────────────────────

# Adjectives agree with noun class via adjectival concord
# Comparison uses the verb "okusinga" (to surpass/exceed)
COMPARISON = {
    "positive":     "adjective alone — e.g. omukazi omurungi (a good woman)",
    "comparative":  "verb + okusinga — e.g. asinga omurungi (she is better)",
    "superlative":  "verb + okusinga + bose/byona — e.g. asinga bose omurungi (she is the best)",
}

# Common adjective stems (take adjectival concord prefix per noun class)
ADJECTIVE_STEMS = {
    "-rungi":    "good",
    "-bi":       "bad",
    "-raira":    "tall/long",
    "-to":       "small/young",
    "-nene":     "big/fat",
    "-gu":       "heavy",
    "-eri":      "two",
    "-satu":     "three",
    "-na":       "four",
    "-taano":    "five",
    "-ingi":     "many",
    "-eke":      "few/little",
    "-iza":      "good/beautiful (alternative)",
    "-ire":      "old (of things)",
    "-kuru":     "old (of persons)",
}

# Adverbs of manner: formed with ki- prefix or standalone
ADVERBS_OF_MANNER = {
    "kijungu":      "in a European fashion",
    "kiserukali":   "like a soldier",
    "kinyoro":      "like a chief / in Runyoro fashion",
    "kizaana":      "like a maid-servant",
    "masaija":      "in a manly way",
    "mate":         "in a cow-like fashion",
    "matale":       "in a leonine fashion",
    "bwangu":       "quickly, rapidly",
    "mpola":        "slowly, gently",
    "nkoomu":       "together",
    "hamwe":        "together",
}


# ─────────────────────────────────────────────────────────────────────────────
# NUMBERS (Okubara)
# Source: Grammar Ch.4 + Grammar numbers chapter
# ─────────────────────────────────────────────────────────────────────────────

NUMBERS = {
    1: "emu",    2: "ibiri",   3: "isatu",  4: "ina",    5: "itaano",
    6: "mukaaga",7: "musanju", 8: "munaana",9: "mwenda", 10: "ikumi",
    11: "ikumi nemu",          20: "abiri",  30: "asatu",
    40: "ana",   50: "atano",  60: "nkaaga", 70: "nsanju",
    80: "kinaana", 90: "kyenda",
    100: "kikumi", 200: "bibiri", 300: "bisatu", 400: "bina",
    1000: "rukumi", 1_000_000: "akakaikuru", 1_000_000_000: "akasirira",
}

# Hundreds/thousands connected by "mu" and "na"
# e.g. 235 cows = ente bibiri mu asatu na itaano
# Ordinals formed by adding numeral concord to stem
ORDINAL_NOTE = (
    "Ordinals are formed by bringing the numeral into concordial agreement "
    "with the noun it qualifies, using the numeral concord for that class."
)

# Numbers 1-5 must agree with noun class via numeral concord
NUMERAL_CONCORDS = {
    # class: concord_prefix
    1:    "omu",  2:  "aba",
    3:    "omu",  4:  "emi",
    5:    "eri",  6:  "ama",
    7:    "eki",  8:  "ebi",
    9:    "en",   10: "en",
    11:   "oru",  12: "aka",
    13:   "utu",  14: "obu",
    15:   "oku",
}

# ─────────────────────────────────────────────────────────────────────────────
# PARTICLES, CONJUNCTIONS & PREPOSITIONS
# Source: Grammar Ch.4
# ─────────────────────────────────────────────────────────────────────────────

CONJUNCTIONS = {
    "na":           "and / with",
    "hamwe na":     "together with",
    "rundi":        "or / either...or",
    "kandi":        "and / but / in addition",
    "ekindi":       "in addition to",
    "kuba":         "because / that / if",
    "kakuba":       "if (negative conditional)",
    "ngu":          "that (reported speech)",
    "obu":          "if / when",
    "noobwa":       "even if / though / although",
    "kyonka":       "but",
    "baitwa":       "but / whereas",
    "nikyo kinu":   "all the same",
}

PREPOSITIONS = {
    "mu":       "in / into / at",
    "ha":       "at / on / near",
    "ku":       "to / at / on",
    "aha":      "at / there",
    "hanyuma":  "after",
    "nka":      "like / as",
    "okuhikya": "till / until",
    "nkoomu":   "as / like",
    "okuna":    "with / by",
}

NEGATION_WORDS = {
    "ti-":      "negative prefix (verb)",
    "tindi":    "I will not",
    "tinka":    "I did not / have not",
    "aha":      "not there (declinable negation)",
    "busa":     "no / not at all",
    "nga":      "no / not",
}

# Relative particle -nya- / nya-
# Placed before noun prefix to indicate something already known to both speaker and listener
NYA_PARTICLE = {
    "rule": "nya- placed before noun prefix indicates definiteness / already known referent",
    "examples": {
        "nyamotoka": "those (specific) cars",
        "nyastookingi": "those (specific) stockings",
    },
    "similar_to": "zaa-/za-/ze-/zo- prefixes of class 10a",
}


# ─────────────────────────────────────────────────────────────────────────────
# PRONOUNS
# Source: Grammar Ch.4
# ─────────────────────────────────────────────────────────────────────────────

PERSONAL_PRONOUNS = {
    "nyowe":  "I (emphatic)",
    "itwe":   "we (emphatic)",
    "iwe":    "you (singular)",
    "inywe":  "you (plural)",
    "uwe":    "he / she",
}

# Object pronouns (as suffixes/infixes in verb)
OBJECT_PRONOUNS = {
    "1sg": "-ndi- / -m-",
    "2sg": "-ku-",
    "3sg": "-mu-",
    "1pl": "-tu-",
    "2pl": "-ba- (mu-)",
    "3pl": "-ba-",
}


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE NAMES (oru- prefix)
# Source: Grammar Ch.7 — Class 11 semantic properties
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_NAMES = {
    "Orunyoro":     "language of Bunyoro",
    "Orutooro":     "language of Tooro",
    "Oruganda":     "language of Buganda (Luganda)",
    "Orunyankole":  "language of Nkole (Ankole)",
    "Orungereza":   "language of England (English)",
    "Orufuransa":   "language of France (French)",
    "Oruswahili":   "Swahili",
    "Oruarabu":     "Arabic",
}


# ─────────────────────────────────────────────────────────────────────────────
# AUGMENTATIVE / PEJORATIVE PREFIX SUBSTITUTION
# Source: Grammar Ch.7
# ─────────────────────────────────────────────────────────────────────────────

# oru- substituted for normal class prefix = augmentative or pejorative
AUGMENTATIVE_EXAMPLES = {
    "orusaija":  ("omusaija",  "man",    "clumsy/big man (pejorative)"),
    "orukazi":   ("omukazi",   "woman",  "clumsy woman"),
    "orwisiki":  ("omwisiki",  "girl",   "clumsy girl"),
    "orute":     ("ente",      "cow",    "clumsy cow"),
    "oruti":     ("omuti",     "tree",   "long stick"),
    "orunyonyi": ("enyonyi",   "bird",   "big long bird"),
}

# eki-/eky- substituted = magnitude, affection, or contempt
MAGNITUDE_EXAMPLES = {
    "ekisaija":  ("omusaija",  "man",    "that clumsy/big man (contempt)"),
    "ekiiru":    ("omwiru",    "servant","dear poor man (affection) / sturdy peasant"),
    "ekintu":    ("okintu",    "thing",  "monster-like thing"),
}

# eri-/ery- substituted = magnitude
MAGNITUDE_ERI_EXAMPLES = {
    "eriiru":    ("omwiru",    "servant","that sturdy peasant"),
    "erintu":    ("okintu",    "thing",  "monster-like thing"),
    "eryana":    ("omwana",    "child",  "insolent child"),
}

# ─────────────────────────────────────────────────────────────────────────────
# EMPAAKO (Honorific Names)
# ─────────────────────────────────────────────────────────────────────────────

EMPAAKO = {
    "Atwooki":  "From Atwok — shining star. Given to a child born on a night with stars.",
    "Ateenyi":  "From Ateng — beautiful. Given if parents believe the child is beautiful.",
    "Apuuli":   "From Apul/Rapuli — a very lovely girl, center of attraction and love in the family.",
    "Amooti":   "From Amot — princely, a sign of royalty. Mostly for sons and daughters of kings and chiefs.",
    "Akiiki":   "From Ochii/Achii — the one who follows twins. Mostly for firstborns who bear responsibility for siblings.",
    "Adyeeri":  "From adyee/odee — parents had failed to get a child and only got one after spiritual intervention.",
    "Acaali":   "From Ochal — replica. Given to a child who resembled someone in the family or ancestors.",
    "Abaala":   "From Obal/Abal — destroyer/warrior. Usually for sons of chiefs.",
    "Abbooki":  "From Obok/Abok — beloved. Child born out of strong love between parents.",
    "Araali":   "From Arali/Olal/Alal — lost. Given to the only surviving child after mother lost many children.",
    "Abwooli":  "From Abwolo — 'I lied to you'. A woman who conceives but continues having periods.",
    "Okaali":   "From 'kal' — royalty. Only for the King in Kitara customs.",
}


# ─────────────────────────────────────────────────────────────────────────────
# INTERJECTIONS (Ebihunaazo)
# ─────────────────────────────────────────────────────────────────────────────

INTERJECTIONS = {
    "mawe":             "expression of surprise, shock, admiration",
    "hai":              "expression of surprise",
    "awe":              "expression of surprise, shock",
    "bambi":            "expression of sympathy, appreciation",
    "ai bambi":         "expression of sympathy",
    "ee":               "expression of surprise, admiration",
    "haakiri":          "expression of satisfaction",
    "cucu":             "expression of surprise",
    "mpora":            "expression of sympathy",
    "leero":            "expression of surprise, anger, fear, pleasure",
    "nyaburaiwe":       "expression of appealing, pity for oneself",
    "nyaaburanyowe":    "expression of pity, sadness",
    "mahano":           "expression of surprise, shock, disappointment",
    "caali":            "expression of kindness, appealing, admiration",
    "ndayaawe":         "appealing to someone or swearing by mother's clan",
    "nyaaburoogu":      "expression showing pity or admiration",
    "boojo":            "expression of admiration, pity, appeal, disappointment or pain",
    "mara boojo":       "expression of appealing",
    "ego":              "expression of assurance, satisfaction",
    "nukwo":            "expression of assurance, satisfaction, dissatisfaction",
    "manyeki":          "expression of doubt",
    "nga":              "expression of surprise, doubt, negation",
    "busa":             "expression of negation",
    "nangwa":           "expression of surprise, doubt, negation",
    "taata we":         "expression of surprise, shock, pity",
    "Ruhanga wange":    "my God — expression of surprise, shock, displeasure",
    "Weza":             "indeed",
    "Weebale":          "thank you",
    "hee":              "expression of surprise, shock",
    "gamba":            "expression of surprise",
    "dahira":           "expression of surprise, disbelief — literally 'swear!'",
    "ka mahano":        "expression of surprise, shock, disappointment",
    "ka kibi":          "expression of surprise, pity — literally 'it is bad!'",
    "bbaasi":           "enough!",
    "kooboine":         "expression of pity",
}


# ─────────────────────────────────────────────────────────────────────────────
# IDIOMATIC EXPRESSIONS (Ebidikizo)
# ─────────────────────────────────────────────────────────────────────────────

IDIOMS = {
    "kuburorra mu rwigi":           "leaving very early in the morning",
    "baroleriire ha liiso":         "watching over a dying person",
    "kucweke nteho ekiti":          "running as fast as possible",
    "kurubata atakincwa":           "walking hurriedly and excitedly",
    "kugenda obutarora nyuma":      "walking very fast and in a concentrated manner",
    "omutima guli enyuma":          "dissatisfied, worried",
    "omutima guramaire":            "dissatisfied, worried",
    "omutima gwezire":              "satisfied, contented",
    "amaiso kugahanga enkiro":      "waiting for somebody/something with anxiety",
    "kukwata ogwa timbabaine":      "disappear quietly",
    "kwija naamaga":                "arrive in panic and anxiety",
    "kutarorwa izooba":             "too beautiful to be exposed",
    "kuteera akahuno":              "effect of great surprise",
    "garama nkwigate":              "talk carelessly",
    "amaiso ga kimpenkirye":        "shamelessness",
    "maguru nkakwimaki":            "as fast as possible",
    "kuseka ekihiinihiini":         "laughing with great happiness",
}


# ─────────────────────────────────────────────────────────────────────────────
# PROVERBS (Enfumo)
# ─────────────────────────────────────────────────────────────────────────────

PROVERBS = [
    "Ababiri bagamba kamu, abasatu basatura",
    "Amagezi macande bakaranga nibanena",
    "Amazima obu'gaija, ebisuba biruka",
    "Buli kasozi nengo yako",
    "Ekigambo ky'omukuru mukaro, obw'ijuka onenaho",
    "Ekibi tikibura akireeta",
    "Enjara etemesa emigimba ebiri",
    "Mpora, mpora, ekahikya omunyongorozi haiziba",
    "Kamu kamu nugwo muganda",
    "Omutima guli enyuma",
    "Amaizi tigebwa owabugo mbeho",
    "Engaro ibiri kunaabisa ngana",
]

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_grammar_context() -> str:
    """Concise grammar context string for use in chat/translation prompts."""
    return (
        "Runyoro-Rutooro Grammar Rules:\n"
        "1. R/L Rule: R is dominant. L only before/after 'e' or 'i' vowels.\n"
        "2. Verb infinitives start with 'oku-' (e.g. okugenda = to go).\n"
        "3. Noun classes: omu-/aba- (people), en-/em- (animals/things), "
        "ama- (cl.6 plurals), obu- (abstract), oku- (infinitives/body parts).\n"
        "4. Tense markers: ni- (present imperfect), ka- (past), ra-/raa- (future), "
        "-ire/-ere (perfect).\n"
        "5. Subject prefixes: n- (I), o- (you sg), a- (he/she), tu- (we), "
        "mu- (you pl), ba- (they).\n"
        "6. Adjectives and numerals agree with noun class via concordial prefixes.\n"
        "7. Comparison uses okusinga (to surpass): asinga omurungi = she is better.\n"
        "8. Negation: ti- prefix on verb, e.g. tinigenda = is not going.\n"
        "9. Apostrophe marks swallowed initial vowel in fast speech: n'ente, z'ente.\n"
        "10. Long vowels written double: aa, ee, ii, oo, uu.\n"
    )


def lookup_interjection(word: str) -> str | None:
    return INTERJECTIONS.get(word.lower().strip())


def lookup_idiom(phrase: str) -> str | None:
    return IDIOMS.get(phrase.lower().strip())


def is_verb_infinitive(word: str) -> bool:
    """Return True if word looks like a Runyoro-Rutooro verb infinitive."""
    w = word.lower().strip()
    return w.startswith("oku") or w.startswith("okw")


def get_plural(singular: str) -> str | None:
    """Return known plural for a class 11 noun, or None."""
    return PLURAL_SOUND_CHANGES.get(singular.lower().strip())


def detect_noun_class_from_prefix(word: str) -> list:
    """Wrapper around get_noun_class for external use."""
    return get_noun_class(word)


def number_to_runyoro(n: int) -> str | None:
    """Return Runyoro-Rutooro word for a number if known."""
    return NUMBERS.get(n)


# ─────────────────────────────────────────────────────────────────────────────
# DERIVATIVE VERB FORMATION RULES (DETAILED)
# Source: Grammar Ch.12 — Derivative verbs in particular
# ─────────────────────────────────────────────────────────────────────────────

# Prepositional/Applied verb formation (-ira/-era)
# Exceptions to the general -ira/-era rule:

PREPOSITIONAL_FORMATION = {
    "verbs_ending_ra": {
        "rule": "prefix r to last syllable, causing long vowel before it",
        "examples": {
            "okusara": "okusaarra",   # to cut -> to cut for
            "okukora": "okukoorra",   # to work -> to work within time
        }
    },
    "verbs_ending_rra": {
        "rule": "restore dropped vowel, then prefix r to last syllable",
        "examples": {
            "okukoorra": "okukoroorra",  # to cough -> to cough at
            "okuseerra": "okuseruurra",  # to look for -> to look for somewhere
        }
    },
    "verbs_ending_ja": {
        "rule": "follow general rule but undergo sound change (j->z before -ire/-i)",
        "note": "see consonant suffix changes"
    },
    "verbs_ending_za": {
        "rule": "change -za into -liza/-leza",
        "examples": {
            "okuguza": "okuguliza",  # to sell -> to sell in/at a place
            "okubaza": "okubaliza",  # to speak -> to speak while at
        }
    },
    "causative_verbs_ending_ya": {
        "rule": "change -ya into -iza/-eza",
        "examples": {
            "okubya": "okubiza",     # causative forms
        }
    },
}

# Passive verb formation (-ibwa/-ebwa)
PASSIVE_FORMATION = {
    "monosyllabic_simple": {
        "rule": "add -ibwa/-ebwa with sound change",
        "examples": {
            "ha": "heebwa",   # give -> be given
            "ta": "teebwa",   # put -> be put
            "sa": "siibwa",   # grind -> be ground
        }
    },
    "monosyllabic_labial_palatal": {
        "rule": "replace final vowel with -ibwa/-ebwa",
        "examples": {
            "cwa": "cwibwa",      # break -> be broken
            "lya": "liibwa",      # eat -> be eaten
            "byamya": "byamibwa", # lay down -> be laid down
        }
    },
    "causative_ya_sa_za": {
        "rule": "replace final vowel with -ibwa/-ebwa",
        "examples": {
            "yegesa": "yegesebwa",  # teach -> be taught
            "guza": "guzibwa",      # sell -> be sold
        }
    },
    "other_verbs": {
        "rule": "replace -a with -wa",
        "examples": {
            "genda": "gendwa",   # go -> be gone to
            "kora": "korwa",     # work -> be worked
        }
    },
}

# Causative verb formation (-isa/-esa/-ya)
CAUSATIVE_FORMATION = {
    "monosyllabic_simple": {
        "rule": "add -isa/-esa",
        "examples": {
            "ba": "baisa",   # be -> put in a state
            "ha": "haisa",   # give -> cause to give
            "ta": "taisa",   # put -> cause to put
        }
    },
    "monosyllabic_labial_palatal": {
        "rule": "change final a to -isa, restore original vowel if replaced",
        "examples": {
            "cwa": "cwisa",   # break -> help to break
            "hwa": "hoisa",   # finish -> cause to finish
            "hya": "hiisa",   # cook -> finish cooking
        }
    },
    "verbs_ending_ra_rra": {
        "rule": "change -ra into -za",
        "examples": {
            "okubara": "okubaza",     # count -> help count
            "okuhaarra": "okuharuza", # scrape -> scrape out with
        }
    },
    "verbs_ending_ta": {
        "rule": "change -ta into -sa",
        "examples": {
            "okucumita": "okucumisa",  # stab -> stab with
            "okurubata": "okurubasa",  # tread -> tread with
        }
    },
    "intransitive_verbs": {
        "rule": "replace final a with -ya",
        "examples": {
            "okuhaba": "okuhabya",   # go astray -> make lose way
            "okwoga": "okwogya",     # bathe -> wash
            "okwaka": "okwakya",     # burn -> light/blow up fire
            "okubya": "okubyamya",   # lie down -> lay down
        }
    },
}

# Neuter/stative verb formation (-ika/-eka/-ooka/-uuka)
NEUTER_FORMATION = {
    "rule": "replace final vowel with -ika/-eka/-ooka/-uuka per sound change",
    "examples": {
        "okwata": "okwatika",      # smash -> be smashed
        "okucwa": "okucweka",      # break -> be broken
        "okugoorra": "okugoorrooka", # stretch -> be stretched out
        "okuhuuha": "okuhuuhuuka",   # blow -> be blown off
    },
    "verbs_ending_ra": {
        "rule": "replace last syllable with -ka",
        "examples": {
            "okusobora": "okusoboka",  # manage -> be manageable
            "okutaagura": "okutaaguka", # tear -> get torn
        }
    },
}

# Conversive/reversive verb formation (-ura/-ora/-uka/-oka)
CONVERSIVE_FORMATION = {
    "rule": "indicates undoing or reversing the action",
    "transitive_ura_ora": {
        "examples": {
            "okubamba": "okubambura",   # peg -> unpeg
            "okuleega": "okulegura",    # tighten -> loosen
            "okusimba": "okusimbura",   # stick upright -> uproot
        }
    },
    "intransitive_uka_oka": {
        "examples": {
            "okubamba": "okubambuka",   # peg -> break away
            "okuleega": "okuleguka",    # tighten -> get loose
            "okusimba": "okusimbuka",   # stick -> get uprooted
        }
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# COMPOUND TENSE CONDITIONAL CONSTRUCTIONS
# Source: Grammar Ch.15 — Compound tenses with conditional mood
# ─────────────────────────────────────────────────────────────────────────────

# Conditional constructions with kakuba/kuba/kakusangwa/kusangwa
# These introduce conditional sentences with various tense combinations

CONDITIONAL_CONSTRUCTIONS = {
    "kakuba": {
        "meaning": "if (conditional marker)",
        "usage": "introduces conditional protasis",
        "examples": {
            "near_past": "Kakuba obaire ompaireomulimo nkugukozire (If you had given me work I should have done it)",
            "present": "Kakuba omuha omulimo naagukora (If you give him work he will do it)",
        }
    },
    "kuba": {
        "meaning": "if (conditional marker, variant of kakuba)",
        "usage": "interchangeable with kakuba in most contexts",
        "examples": {
            "Kuba obaire ompaireomulimo nkugukozire",
            "Kuba okaba ompaireomulimo naakugukozire",
        }
    },
    "kakusangwa": {
        "meaning": "if it happens that (conditional marker)",
        "usage": "emphasizes contingency or happenstance",
        "examples": {
            "Kakusangwa omulimo tinkukozire (If work happens, I have not done anything)",
        }
    },
    "kusangwa": {
        "meaning": "if it happens that (variant)",
        "usage": "variant of kakusangwa",
    },
    "obu": {
        "meaning": "if/when (conditional marker)",
        "usage": "introduces conditional clauses, often with okubaire",
        "examples": {
            "positive": "Obu okubaire ompaireomulimo nkugukozire (If you had given me work I should have done it)",
            "negative": "Obu okubaire otampaireomulimo tinkukozire kantu (If you had not given me work I should not have done anything)",
            "with_verb_ina": "Obu nkubaire nyina enju naakumuraize (If I had had a house I should have put him up)",
            "with_verb_li": "Obu nkubaire ndi mwomeezi naakukusendekeriize (If I had been healthy I should have seen you off)",
        }
    },
}

# Conditional tense patterns by time reference
CONDITIONAL_TENSE_PATTERNS = {
    "near_past": {
        "protasis": "obaire(ge) + verb-ire",
        "apodosis": "subject + -ku- + verb-ire",
        "example": "Obu okubaire ompaireomulimo nkugukozire",
    },
    "far_past": {
        "protasis": "okaba / waakubaire + verb",
        "apodosis": "subject + naa- + verb-ire",
        "example": "Obu waakubaire ompaireomulimo naakugukozire",
    },
    "present_imperfect": {
        "protasis": "verb with ni- prefix or relative form",
        "apodosis": "noo- + verb / naa- + verb",
        "example": "Kakuba noomuhairemulimo naagukora",
    },
    "near_future": {
        "protasis": "oraa- + verb",
        "apodosis": "araa- + verb / taa- + verb-e (negative)",
        "example": "Obu oraamuhairemulimo araagukora",
    },
    "far_future": {
        "protasis": "oliba + verb",
        "apodosis": "aligukora / talikora",
        "example": "Obu oliba omuhairemulimo aligukora",
    },
}

# Conditional marker -ku- (doubt/uncertainty in consequence)
CONDITIONAL_KU_MARKER = {
    "usage": "inserted in apodosis when consequence is doubted",
    "examples": {
        "positive": "Omuhairemulimo akugukora (If you gave him work he would do it)",
        "negative": "Omuhairemulimo taakugukora? (If you gave him work, wouldn't he do it?)",
    },
    "note": "May be omitted in reduced forms: Nkutiire okora ki? (What would you do if I beat you?)",
}

# Infinitive as conditional introducer
INFINITIVE_CONDITIONAL = {
    "usage": "infinitive with nominal prefix acts as conditional introducer",
    "examples": {
        "simple": "Kumuha omulimo naagukora (If you gave him work he would do it)",
        "compound": "Obaire kumuha omulimo naagukora (If you gave him work he would do it)",
    },
    "note": "No negative form exists for this construction",
}

# Relative form conditional
RELATIVE_CONDITIONAL = {
    "usage": "relative form in protasis with obu as introducer",
    "examples": {
        "positive": "Obu arukugumpa ningukora (If he gave it to me I should do it)",
        "negative": "Obu atarukumpa mulimo tindikukora (If he did not give me work I should be idle)",
    },
    "note": "Often used to answer questions made with infinitive conditional forms",
}


# ─────────────────────────────────────────────────────────────────────────────
# GENITIVE PARTICLES (Possessive Connectives)
# Source: Grammar Ch.7, Ch.9 — Genitive/possessive constructions
# ─────────────────────────────────────────────────────────────────────────────

# Genitive particles connect possessor to possessed noun
# Form: class concord + -a
GENITIVE_PARTICLES = {
    1:  {"particle": "wa",   "variant_v": "w'",   "example": "omusaija wa Petero (Peter's man)"},
    2:  {"particle": "ba",   "variant_v": "b'",   "example": "abasaija ba Petero (Peter's men)"},
    3:  {"particle": "gwa",  "variant_v": "gw'",  "example": "omuti gwa Petero (Peter's tree)"},
    4:  {"particle": "gya",  "variant_v": "gy'",  "example": "emiti gya Petero (Peter's trees)"},
    5:  {"particle": "lya",  "variant_v": "ly'",  "example": "eriiso lya Petero (Peter's eye)"},
    6:  {"particle": "ga",   "variant_v": "g'",   "example": "amaiso ga Petero (Peter's eyes)"},
    7:  {"particle": "kya",  "variant_v": "ky'",  "example": "ekintu kya Petero (Peter's thing)"},
    8:  {"particle": "bya",  "variant_v": "by'",  "example": "ebintu bya Petero (Peter's things)"},
    9:  {"particle": "ya",   "variant_v": "y'",   "example": "ente ya Petero (Peter's cow)"},
    10: {"particle": "za",   "variant_v": "z'",   "example": "ente za Petero (Peter's cows)"},
    11: {"particle": "rwa",  "variant_v": "rw'",  "example": "orulimi rwa Petero (Peter's tongue)"},
    12: {"particle": "ka",   "variant_v": "k'",   "example": "akana ka Petero (Peter's small child)"},
    13: {"particle": "twa",  "variant_v": "tw'",  "example": "ututo twa Petero (Peter's small things)"},
    14: {"particle": "bwa",  "variant_v": "bw'",  "example": "obwire bwa Petero (Peter's millet)"},
    15: {"particle": "kwa",  "variant_v": "kw'",  "example": "okuguru kwa Petero (Peter's leg)"},
}

def get_genitive_particle(noun_class: int | str) -> str:
    """Return genitive particle for a noun class."""
    entry = GENITIVE_PARTICLES.get(noun_class)
    return entry["particle"] if entry else ""


# ─────────────────────────────────────────────────────────────────────────────
# RELATIVE CONCORDS AND PARTICLES
# Source: Grammar Ch.9 — Relative constructions
# ─────────────────────────────────────────────────────────────────────────────

# Relative concords mark relative clauses (who, which, that)
RELATIVE_CONCORDS = {
    1:  {"concord": "-a-",   "example": "omusaija agenze (the man who went)"},
    2:  {"concord": "-ba-",  "example": "abasaija bagenze (the men who went)"},
    3:  {"concord": "-gu-",  "example": "omuti gugenze (the tree that fell)"},
    4:  {"concord": "-gi-",  "example": "emiti gigenze (the trees that fell)"},
    5:  {"concord": "-li-",  "example": "eriiso lirungi (the eye that is good)"},
    6:  {"concord": "-ga-",  "example": "amaiso garungi (the eyes that are good)"},
    7:  {"concord": "-ki-",  "example": "ekintu kirungi (the thing that is good)"},
    8:  {"concord": "-bi-",  "example": "ebintu birungi (the things that are good)"},
    9:  {"concord": "-i-",   "example": "ente irungi (the cow that is good)"},
    10: {"concord": "-zi-",  "example": "ente zirungi (the cows that are good)"},
    11: {"concord": "-ru-",  "example": "orulimi rurungi (the tongue that is good)"},
    12: {"concord": "-ka-",  "example": "akana karungi (the small child that is good)"},
    13: {"concord": "-tu-",  "example": "ututo turungi (the small things that are good)"},
    14: {"concord": "-bu-",  "example": "obwire burungi (the millet that is good)"},
    15: {"concord": "-ku-",  "example": "okuguru kurungi (the leg that is good)"},
}

# Relative particles -nyaku-, -owa-, -eya-
# These mark definiteness or specificity in relative constructions
RELATIVE_PARTICLES = {
    "-nyaku-": {
        "meaning": "that specific one (definite relative)",
        "usage": "inserted before noun prefix to mark known referent",
        "example": "nyakumotoka (that specific car we know)",
    },
    "-owa-": {
        "meaning": "the one of/belonging to",
        "usage": "possessive relative marker",
        "example": "owaKabale (the one from/of Kabale)",
    },
    "-eya-": {
        "meaning": "the one that/which",
        "usage": "relative marker for specific reference",
    },
    "nya-": {
        "meaning": "that/those (definite marker)",
        "usage": "placed before noun prefix for definiteness",
        "examples": {
            "nyamotoka": "those (specific) cars",
            "nyastookingi": "those (specific) stockings",
        },
        "note": "Similar to zaa-/za-/ze-/zo- prefixes of class 10a",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# NOUN DERIVATION SUFFIXES
# Source: Grammar Ch.7, Ch.8 — Noun formation from verbs and other nouns
# ─────────────────────────────────────────────────────────────────────────────

# Nouns can be derived from verbs using specific suffixes and class prefixes
NOUN_DERIVATION = {
    "agent_nouns_class1": {
        "pattern": "omu- + verb_stem + -i",
        "meaning": "person who does the action",
        "examples": {
            "okukora": "omukozi (worker)",
            "okugenda": "omugenzi (traveler)",
            "okusoma": "omusomi (reader)",
            "okwigisha": "omwigisha (teacher)",
        }
    },
    "instrument_nouns_class7": {
        "pattern": "eki- + verb_stem + -o",
        "meaning": "instrument/tool for doing action",
        "examples": {
            "okusala": "ekisalo (cutting tool)",
            "okufumba": "ekifumbo (cooking pot)",
            "okubaza": "ekibazo (question)",
        }
    },
    "abstract_nouns_class14": {
        "pattern": "obu- + adjective_stem / verb_stem + -i/-o",
        "meaning": "abstract quality or state",
        "examples": {
            "omurungi": "oburungi (goodness)",
            "omubi": "obubi (badness)",
            "omukuru": "obukuru (old age)",
            "okukora": "obukozi (work/labor as concept)",
        }
    },
    "diminutive_nouns_class12": {
        "pattern": "aka- + noun_stem",
        "meaning": "small version of noun",
        "examples": {
            "omwana": "akana (small child)",
            "enju": "akaju (small house)",
        }
    },
    "augmentative_pejorative": {
        "pattern": "oru-/eki-/eri- substituted for normal prefix",
        "meaning": "large/clumsy/pejorative version",
        "note": "See AUGMENTATIVE_EXAMPLES section above",
    },
}

# Suffix patterns for noun derivation
NOUN_DERIVATION_SUFFIXES = {
    "-i": {
        "usage": "agent nouns (class 1), abstract nouns (class 14)",
        "examples": ["omukozi", "obukozi"],
    },
    "-o": {
        "usage": "instrument nouns (class 7), result nouns",
        "examples": ["ekisalo", "ekifumbo"],
    },
    "-zi": {
        "usage": "plural agent nouns (class 2 from class 1)",
        "examples": ["abakozi (workers)"],
    },
    "-u": {
        "usage": "abstract/quality nouns",
        "examples": ["obuntu (humanity)", "obukulu (greatness)"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# COMPLETE ORTHOGRAPHY RULES
# Source: Runyoro-Rutooro Orthography Guide (1995)
# ─────────────────────────────────────────────────────────────────────────────

# Prenasalization rules
PRENASALIZATION_RULES = {
    "mb": {
        "rule": "nasal m + b always written as mb",
        "examples": ["embwa (dog)", "omubiri (body)", "kumbira (to beg)"],
    },
    "mp": {
        "rule": "nasal m + p always written as mp",
        "examples": ["empanga (horn)", "kumpa (to give me)"],
    },
    "nd": {
        "rule": "nasal n + d/r always written as nd",
        "examples": ["enda (stomach)", "kunda (to love)", "okwendera (to visit)"],
        "note": "n + r -> nd (Meinhof's rule)",
    },
    "nt": {
        "rule": "nasal n + t always written as nt",
        "examples": ["ente (cow)", "kunta (to beat me)"],
    },
    "ng": {
        "rule": "nasal n + g written as ng",
        "examples": ["engoma (drum)", "kunguza (to shake)"],
    },
    "nk": {
        "rule": "nasal n + k written as nk",
        "examples": ["enka (cow - variant)", "kunkuba (to beat me)"],
    },
    "nj": {
        "rule": "nasal n + j written as nj",
        "examples": ["enju (house)", "kunjura (to untie for me)"],
    },
    "nc": {
        "rule": "nasal n + c written as nc",
        "examples": ["enca (hunger)", "kuncumbagira (to kneel for me)"],
    },
}

# Double consonant rules
DOUBLE_CONSONANT_RULES = {
    "rr": {
        "rule": "double r indicates intensive/completive action or specific verb forms",
        "examples": ["okukoorra (to cough)", "okuseerra (to look for)", "okusaarra (to cut for)"],
    },
    "tt": {
        "rule": "double t rare, occurs in some borrowed words",
        "examples": ["omuttaka (chief - variant spelling)"],
    },
    "kk": {
        "rule": "double k rare, occurs in emphasis or specific dialects",
    },
    "long_vowel_before_consonant": {
        "rule": "long vowel (doubled) before single consonant indicates vowel length",
        "examples": ["kubaasa (to be able)", "kuhaamba (to give generously)"],
    },
}

# Syllabification rules
SYLLABIFICATION_RULES = {
    "cv_structure": {
        "rule": "Runyoro-Rutooro prefers open syllables (CV pattern)",
        "examples": ["o-mu-sa-i-ja", "e-ki-ta-bu", "o-ku-ge-n-da"],
    },
    "nasal_syllabic": {
        "rule": "Prenasals (mb, nd, nt, etc.) form single onset with following consonant",
        "examples": ["e-mbu-zi (goat) = e-mbu-zi not e-m-bu-zi"],
    },
    "vowel_sequences": {
        "rule": "Vowel sequences are separate syllables unless forming diphthong",
        "examples": ["o-ku-i-ta (to call) = o-ku-i-ta", "mai (water) = single syllable with diphthong"],
    },
}

# Initial vowel (augment) rules
INITIAL_VOWEL_RULES = {
    "presence": {
        "rule": "Most nouns have initial vowel (augment) before class prefix",
        "examples": {
            "with_augment": "o-mu-ntu (person), e-ki-ntu (thing), a-ma-zi (water)",
            "without_augment": "proper names, some class 1a/2a nouns, class 9a/10a",
        },
    },
    "elision": {
        "rule": "Initial vowel may be dropped in fast speech, marked with apostrophe",
        "examples": ["n'ente (with cow)", "z'ente (of cows)", "k'ente (it is a cow)"],
    },
    "vowel_harmony": {
        "rule": "Initial vowel often harmonizes with prefix vowel",
        "patterns": {
            "o-": "omu-, obu-, oku-, oru-",
            "e-": "eki-, emi-, eri-, en-",
            "a-": "aba-, aka-, ama-",
            "u-": "utu-",
        },
    },
}

# Tone marking (not written in standard orthography)
TONE_RULES = {
    "note": "Runyoro-Rutooro is a tonal language but tone is not marked in standard orthography",
    "importance": "Tone distinguishes meaning: omukazi (woman) vs omukazi (belt) differ only in tone",
    "patterns": {
        "high_tone": "typically on penultimate syllable in isolation form",
        "low_tone": "other syllables typically low",
        "downstep": "high tone followed by lower high tone in some contexts",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# IMPERATIVE MOOD WITH OBJECT PREFIXES
# Source: Grammar Ch.13, Ch.16 — Imperative forms
# ─────────────────────────────────────────────────────────────────────────────

# Imperative forms with object prefixes
IMPERATIVE_WITH_OBJECTS = {
    "singular": {
        "pattern": "verb_stem + -a (or modified stem)",
        "with_object": "object_prefix + verb_stem + -a",
        "examples": {
            "no_object": "genda (go!)",
            "1sg_object": "nkunde (love me!)",
            "2sg_object": "kukunde (love you!)",
            "3sg_object": "mukunde (love him/her!)",
            "1pl_object": "tukunde (love us!)",
            "3pl_object": "bakunde (love them!)",
        },
    },
    "plural": {
        "pattern": "mu- + verb_stem + -e",
        "with_object": "mu- + object_prefix + verb_stem + -e",
        "examples": {
            "no_object": "mugende (go! [plural])",
            "1sg_object": "munkunde (love me! [plural])",
            "3sg_object": "mumukunde (love him/her! [plural])",
            "3pl_object": "mubakunde (love them! [plural])",
        },
    },
    "negative_singular": {
        "pattern": "ota- + verb_stem + -e",
        "examples": {
            "otagende (don't go!)",
            "otankunde (don't love me!)",
        },
    },
    "negative_plural": {
        "pattern": "muta- + verb_stem + -e",
        "examples": {
            "mutagende (don't go! [plural])",
            "mutankunde (don't love me! [plural])",
        },
    },
}

# Reflexive imperative forms
REFLEXIVE_IMPERATIVE = {
    "singular": {
        "pattern": "wee- + verb_stem + -e (with long vowel)",
        "examples": {
            "okwesereka": "weesereke (hide yourself!)",
            "okwetegyereza": "weetegyereze (understand yourself!)",
        },
    },
    "plural": {
        "pattern": "mwe- + verb_stem + -e",
        "examples": {
            "okwesereka": "mwesereke (hide yourselves!)",
            "okwetegyereza": "mweetegyereze (understand yourselves!)",
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS FOR NEW RULES
# ─────────────────────────────────────────────────────────────────────────────

def get_conditional_pattern(tense: str) -> dict | None:
    """Return conditional pattern for a given tense."""
    return CONDITIONAL_TENSE_PATTERNS.get(tense)

def get_relative_concord(noun_class: int | str) -> str:
    """Return relative concord for a noun class."""
    entry = RELATIVE_CONCORDS.get(noun_class)
    return entry["concord"] if entry else ""

def derive_agent_noun(verb_infinitive: str) -> str | None:
    """
    Derive agent noun (class 1) from verb infinitive.
    Example: okukora -> omukozi
    """
    if not verb_infinitive.startswith("oku"):
        return None
    stem = verb_infinitive[3:]  # remove oku-
    if stem.startswith("w"):
        stem = stem[1:]  # remove w- before vowel
    # Simple derivation: omu- + stem + -i
    return f"omu{stem}i"

def is_prenasalized(text: str) -> bool:
    """Check if text contains prenasalized consonants."""
    prenasals = ["mb", "mp", "nd", "nt", "ng", "nk", "nj", "nc"]
    return any(pn in text.lower() for pn in prenasals)

def has_initial_vowel(word: str) -> bool:
    """Check if word has initial vowel (augment)."""
    if not word:
        return False
    return word[0].lower() in VOWELS


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATION PIPELINE INTEGRATION
# These functions are called by translate.py and main.py
# ─────────────────────────────────────────────────────────────────────────────

def apply_rl_rule_to_text(text: str) -> str:
    """Apply R/L rule word-by-word across a full sentence/paragraph."""
    if not text:
        return text
    words = text.split(" ")
    return " ".join(apply_rl_rule(w) for w in words)


def _apply_nasal_assimilation(text: str) -> str:
    """Fix nasal assimilation errors: nb->mb, np->mp, nr->nd, nl->nd, nm->mm."""
    result = text
    for wrong, correct in NASAL_ASSIMILATION.items():
        result = _re.sub(_re.escape(wrong), correct, result, flags=_re.IGNORECASE)
    return result


def _fix_ni_prefix(text: str) -> str:
    """Apply ni- prefix vowel change: nimu->numu, nigu->nugu, niru->nuru, etc."""
    result = text
    for wrong, correct in NI_PREFIX_CHANGE.items():
        result = _re.sub(r'\b' + _re.escape(wrong), correct, result, flags=_re.IGNORECASE)
    return result


def _apply_consonant_suffix_changes(text: str) -> str:
    """
    Apply consonant+suffix sound changes from CONSONANT_SUFFIX_CHANGES.
    Source: Grammar Ch.2 — r/t/j + -ire/-i/-ya transformations.
    e.g. rora+ire -> rozire, roota+ire -> roosire
    These fix perfect tense and applied verb forms in model output.
    """
    result = text
    # r + -ire at word end -> -zire (only after vowel, avoids stem-internal r)
    result = _re.sub(r'(?<=[aeiou])r(ire)\b', r'z\1', result)
    # t + -ire at word end -> -sire (only after vowel)
    result = _re.sub(r'(?<=[aeiou])t(ire)\b', r's\1', result)
    # nd + -ire -> -nzire
    result = _re.sub(r'nd(ire)\b', r'nz\1', result)
    # nt + -ire -> -nsire
    result = _re.sub(r'nt(ire)\b', r'ns\1', result)
    # NOTE: r+-i and r+-ya NOT applied globally — too many false positives inside stems
    return result


def _apply_y_insertion(text: str) -> str:
    """
    Apply y-insertion rule: after tense prefixes a-, ra-, raa-, daa-
    insert y before verb stems beginning with a vowel.
    Source: Grammar Ch.2 — Y-insertion prefixes.
    e.g. a+ira -> ayira, ra+ira -> rayira
    """
    result = text
    # Only apply y-insertion for unambiguous tense prefixes (ra-, raa-, daa-)
    # Skip bare 'a-' — too many false positives inside noun prefixes like aba-, aka-
    safe_prefixes = {p for p in Y_INSERTION_PREFIXES if len(p) > 1}
    for prefix in safe_prefixes:
        pattern = r'(?<=[bcdfghjklmnprstwyz])(' + _re.escape(prefix) + r')([aeiou])'
        result = _re.sub(pattern, r'\1y\2', result, flags=_re.IGNORECASE)
    return result


def _apply_long_vowel_prefix_merge(text: str) -> str:
    """
    Apply orthography rule 7: when a class/tense/negative prefix ending in a vowel
    is joined to a stem beginning with the same vowel, they merge into one long vowel.
    e.g. aba+ana -> abaana, aka+ato -> akaato, ni+ija -> niija
    Source: Orthography Guide Rule 7.
    """
    result = text
    # Only fix cases where the merge is MISSING (single vowel where double is needed)
    # Do NOT touch already-correct doubled vowels
    merges = [
        (r'\b(ab)(ana)\b',   'abaana'),
        (r'\b(ak)(ato)\b',   'akaato'),
        (r'\b(ni)(ija)\b',   'niija'),
        (r'\b(ni)(ira)\b',   'niira'),
    ]
    for pattern, replacement in merges:
        result = _re.sub(pattern, replacement, result, flags=_re.IGNORECASE)
    return result


def _fix_absent_letters(text: str) -> str:
    """
    Remove or replace letters absent from Runyoro-Rutooro alphabet (q, v, x).
    Source: Orthography Guide Rule 1.
    These sometimes appear in model output due to training data noise.
    """
    # v -> b (closest bilabial), x -> ks, q -> k (rough approximations)
    result = text
    result = _re.sub(r'v', 'b', result)
    result = _re.sub(r'V', 'B', result)
    result = _re.sub(r'x', 'ks', result)
    result = _re.sub(r'X', 'Ks', result)
    result = _re.sub(r'q', 'k', result)
    result = _re.sub(r'Q', 'K', result)
    return result


def _fix_double_consonant_bb(text: str) -> str:
    """
    Orthography Rule 5: bb indicates non-bilabial fricative b.
    Fix cases where model outputs single b where bb is required
    for known words (ibbango, ekibbali, ibbano).
    """
    known_bb = {
        r'\bibango\b': 'ibbango',
        r'\bekibali\b': 'ekibbali',
        r'\bibano\b': 'ibbano',
    }
    result = text
    for pattern, correct in known_bb.items():
        result = _re.sub(pattern, correct, result, flags=_re.IGNORECASE)
    return result


def postprocess_lunyoro(text: str) -> str:
    """
    Post-process Runyoro-Rutooro model output by applying all grammar rules.
    Called after every neural MT en->lun translation.

    Rules applied (in order):
      1.  Absent letter removal (q/v/x) — Orthography Rule 1
      2.  R/L rule — l only before/after e/i, r elsewhere — Grammar Ch.2
      3.  Nasal assimilation — nb->mb, np->mp, nr->nd, nm->mm — Grammar Ch.2
      4.  ni- prefix vowel change — nimu->numu, nigu->nugu — Grammar Ch.2
      5.  Consonant+suffix changes — r/t/nd/nt + -ire/-i/-ya — Grammar Ch.2
      6.  Y-insertion — after a-/ra-/raa- before vowel stems — Grammar Ch.2
      7.  Long vowel prefix merging — aba+ana->abaana — Orthography Rule 7
      8.  bb double consonant fixes for known words — Orthography Rule 5
    """
    if not text:
        return text
    text = _fix_absent_letters(text)
    text = apply_rl_rule_to_text(text)
    text = _apply_nasal_assimilation(text)
    text = _fix_ni_prefix(text)
    text = _apply_consonant_suffix_changes(text)
    text = _apply_y_insertion(text)
    text = _apply_long_vowel_prefix_merge(text)
    text = _fix_double_consonant_bb(text)
    return text


def preprocess_english(text: str) -> str:
    """
    Pre-process English input before sending to the translation model.
    Currently a passthrough — reserved for future normalisation rules.
    """
    return text.strip()


def get_noun_class_hint(word: str) -> str:
    """
    Return a human-readable noun class hint for a Runyoro-Rutooro word.
    Used to enrich dictionary lookup results.
    """
    classes = get_noun_class(word)
    if not classes:
        return ""
    descs = []
    for c in classes:
        entry = NOUN_CLASSES.get(c)
        if entry:
            descs.append(f"Class {c}: {entry['desc']}")
    return "; ".join(descs)


def validate_runyoro_word(word: str) -> dict:
    """
    Validate a Runyoro-Rutooro word against all known grammar rules.
    Returns a dict with 'valid', 'warnings', 'noun_class', 'is_verb'.
    """
    w = word.lower().strip()
    warnings = []

    # Rule 1: absent letters
    for ch in w:
        if ch in ABSENT_LETTERS:
            warnings.append(f"Letter '{ch}' does not exist in Runyoro-Rutooro alphabet")

    # Rule 3/4: R/L rule
    corrected = apply_rl_rule(w)
    if corrected != w:
        warnings.append(f"R/L rule violation — should be '{corrected}'")

    # Rule 2: nasal assimilation
    for wrong, correct in NASAL_ASSIMILATION.items():
        if wrong in w:
            warnings.append(f"Nasal assimilation: '{wrong}' should be '{correct}'")

    # Orthography Rule 1: prenasals should be written as units
    for prenasal in ["mb", "mp", "nd", "nt", "ng", "nk", "nj", "nc"]:
        if prenasal in w:
            break  # valid — prenasals are correct
    # Check for absent-letter substitutions
    for absent in ABSENT_LETTERS:
        if absent in w:
            warnings.append(f"Absent letter '{absent}' — not in Runyoro-Rutooro alphabet")

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "noun_class": get_noun_class_hint(word),
        "is_verb": is_verb_infinitive(word),
    }
