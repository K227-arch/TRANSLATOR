"""
Runyoro-Rutooro language rules.
Sources:
  - A Grammar of Runyoro-Rutooro (Chapters 2, 4, 7, 13, 15, 16)
  - Runyoro-Rutooro Orthography Guide (Ministry of Gender, Uganda, 1995)
  - runyorodictionary.com
"""
import re as _re

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
# IMPLEMENTED RULE FUNCTIONS
# All rules below are executable transformations, not just data constants.
# ─────────────────────────────────────────────────────────────────────────────

def _is_english_word(word: str) -> bool:
    """
    Heuristic: return True if the word looks like English and should NOT
    have Runyoro grammar rules applied to it.
    """
    import re
    # Strip punctuation for the check
    clean = re.sub(r"[^a-zA-Z]", "", word)
    if not clean:
        return False
    # All-caps acronyms (e.g. UNESCO, AI, API)
    if clean.isupper() and len(clean) >= 2:
        return True
    lower = clean.lower()
    # Common English-only digraphs/trigraphs absent in Runyoro
    english_patterns = re.compile(
        r'th|sh|wh|ck|ph|qu|gh|tch|dge|tion|sion|ness|ment|ful|less'
        r'|ing$|ed$|ly$|ous$|ive$|ble$|ity$|ate$|ize$|ise$|ify$|ent$|ant$|ance$|ence$'
        # English words ending in consonant clusters not found in Runyoro
        r'|ld$|nd$|nt$|st$|ft$|lt$|lk$|lp$|lm$|rk$|rn$|rp$|rm$|rt$|rd$'
        r'|nk$|ng$|mp$|mb$|sk$|sp$|sm$|sn$|sw$|sl$|sc$'
        # English vowel combos
        r'|oo|ee|ea|oa|ai|au|aw|ew|ow|ue|ui|ie|ei|ou'
        # English-only letter combos
        r'|[^aeiou]{3,}'  # 3+ consecutive consonants (rare in Runyoro)
    )
    if english_patterns.search(lower):
        return True
    # Very common short English words
    common_english = {
        'a','an','the','is','are','was','were','be','been','being',
        'have','has','had','do','does','did','will','would','could',
        'should','may','might','shall','can','need','dare','ought',
        'i','you','he','she','it','we','they','me','him','her','us',
        'them','my','your','his','its','our','their','this','that',
        'these','those','and','or','but','if','in','on','at','to',
        'for','of','with','by','from','up','about','into','through',
        'not','no','yes','so','as','than','then','when','where','who',
        'what','how','all','each','every','both','few','more','most',
        'other','some','such','only','own','same','too','very','just',
        'hello','hi','global','local','language','languages','translate',
        'translation','grammar','culture','word','words','sentence',
        'english','runyoro','rutooro','uganda','africa',
    }
    if lower in common_english:
        return True
    return False


def apply_rl_rule_to_text(text: str) -> str:
    """Apply the R/L rule to every word in a sentence, skipping English words."""
    if not text:
        return text
    return ' '.join(
        w if _is_english_word(w) else apply_rl_rule(w)
        for w in text.split(' ')
    )


def apply_nasal_assimilation(text: str) -> str:
    """
    Apply nasal assimilation rules across a word or text.
    nb→mb, np→mp, nm→mm, nr→nd, nl→nd  (Meinhof's rule).
    Source: Grammar Ch.2
    """
    result = text
    for src, tgt in sorted(NASAL_ASSIMILATION.items(), key=lambda x: -len(x[0])):
        result = result.replace(src, tgt)
    return result


def apply_ni_prefix_change(text: str) -> str:
    """
    Apply ni- → nu- vowel change before u-class concords in present imperfect.
    e.g. nimugenda → numugenda, niguteera → nuguteera
    Source: Grammar Ch.2
    """
    result = text
    for src, tgt in NI_PREFIX_CHANGE.items():
        result = result.replace(src, tgt)
    return result


# Apostrophe elision: particle + vowel-initial word → particle' + word
# e.g. "na ente" → "n'ente",  "za ente" → "z'ente"
# Source: Runyoro-Rutooro Orthography Guide (1995)
_ELISION_PARTICLES = [
    # (full_form, elided_prefix) — order matters: longer first
    ("na ",  "n'"),   # na + vowel-initial → n'
    ("za ",  "z'"),   # za + vowel-initial → z'
    ("ka ",  "k'"),   # ka + vowel-initial → k'
    ("ya ",  "y'"),   # ya + vowel-initial → y'
    ("wa ",  "w'"),   # wa + vowel-initial → w'
    ("ga ",  "g'"),   # ga + vowel-initial → g'
    ("ba ",  "b'"),   # ba + vowel-initial → b'
]

# Merged forms the model sometimes outputs (no space between particle and word)
# e.g. "nomukazi" → "n'omukazi", "nomwana" → "n'omwana"
_MERGED_ELISION = [
    (r'\bno([aeiou])', r"n'\1"),   # no + vowel → n' + vowel (na omukazi merged)
    (r'\bzo([aeiou])', r"z'\1"),   # zo + vowel → z' + vowel
    (r'\byo([aeiou])', r"y'\1"),   # yo + vowel → y' + vowel
    (r'\bwo([aeiou])', r"w'\1"),   # wo + vowel → w' + vowel
]

_VOWELS = set("aeiouAEIOU")

def apply_apostrophe_elision(text: str) -> str:
    """
    Apply vowel elision with apostrophe for Runyoro-Rutooro particles
    before vowel-initial words.

    e.g.  "na ente"   → "n'ente"
          "za ente"   → "z'ente"
          "na omuntu" → "n'omuntu"
          "nomukazi"  → "n'omukazi"  (merged form from model output)

    Source: Runyoro-Rutooro Orthography Guide (1995)
    """
    if not text:
        return text
    import re as _re

    # 1. Spaced forms: "na ente" → "n'ente"
    result = text
    for full, elided in _ELISION_PARTICLES:
        pattern = _re.compile(
            r'\b' + _re.escape(full.strip()) + r'\s+(?=[aeiouAEIOU])',
            _re.IGNORECASE
        )
        result = pattern.sub(elided, result)

    # 2. Merged forms: "nomukazi" → "n'omukazi"
    for pattern, repl in _MERGED_ELISION:
        result = _re.sub(pattern, repl, result, flags=_re.IGNORECASE)

    return result


def apply_y_insertion(subject_prefix: str, tense_prefix: str, verb_stem: str) -> str:
    """
    Insert 'y' between tense prefix and vowel-initial verb stem when required.
    Rule: after a-, ra-, raa-, daa- tense prefixes, y is inserted before vowel-initial stems.
    e.g. a + ira → ayira,  ra + ira → rayira
    Source: Grammar Ch.2
    """
    vowels = set('aeiou')
    if tense_prefix in Y_INSERTION_PREFIXES and verb_stem and verb_stem[0].lower() in vowels:
        return subject_prefix + tense_prefix + 'y' + verb_stem
    return subject_prefix + tense_prefix + verb_stem


def apply_consonant_suffix_change(stem: str, suffix: str) -> str:
    """
    Apply consonant + suffix sound changes to a verb stem.
    e.g. stem ending in 'r' + '-ire' → '-zire'
    Source: Grammar Ch.2
    """
    stem_lower = stem.lower()
    # Try two-consonant endings first (nd, nt), then single
    for length in (2, 1):
        final = stem_lower[-length:] if len(stem_lower) >= length else ""
        # Strip the final -a from the stem to get the true consonant ending
        # e.g. 'okubara' → stem consonant is 'r' (before final -a)
        stem_no_a = stem_lower.rstrip('a')
        final_cons = stem_no_a[-length:] if len(stem_no_a) >= length else ""
        key = (final_cons, suffix)
        if key in CONSONANT_SUFFIX_CHANGES:
            replacement = CONSONANT_SUFFIX_CHANGES[key]
            # Strip the matched consonant(s) and final -a, append new suffix
            return stem.rstrip('aA')[:-length] + replacement.lstrip('-')
    # No match — just append suffix to stem (strip leading dash)
    return stem + suffix.lstrip('-')


def apply_conversive_suffix(stem: str) -> str:
    """
    Build the conversive/reversive form of a verb stem.
    Rule: replace final -a with -ura (most stems) or -ora (long-o stems).
    Source: Grammar Ch.2
    """
    if not stem:
        return stem
    # Detect long-o stem (ends in -oora or -oo before final a)
    if stem.endswith('ooa') or stem.endswith('oorra'):
        return stem.rstrip('a') + 'ora'
    # Default: replace final -a with -ura
    if stem.endswith('a'):
        return stem[:-1] + 'ura'
    return stem + 'ura'


def apply_reflexive_imperative(verb_infinitive: str, number: str = "singular") -> str:
    """
    Build the reflexive imperative from an okw-e... infinitive.
    Singular: wee + stem-without-a + e
    Plural:   mwe + stem-without-a + e
    e.g. okw-esereka → weesereke (sg), mwesereke (pl)
    Source: Grammar Ch.2
    """
    v = verb_infinitive.lower().strip()
    # Strip infinitive prefix okwe- or okw-e-
    for pfx in ("okwe", "okw-e"):
        if v.startswith(pfx):
            stem = v[len(pfx):]
            break
    else:
        stem = v
    # Remove final -a, add -e
    base = stem.rstrip('a') + 'e'
    prefix = REFLEXIVE_IMPERATIVE_PREFIX if number == "singular" else REFLEXIVE_PLURAL_PREFIX
    return prefix + base


def apply_concordial_agreement(adjective_stem: str, noun_class: int | str) -> str:
    """
    Prefix an adjective stem with the correct adjectival concord for a noun class.
    e.g. apply_concordial_agreement('-rungi', 1) → 'omurungi'
    Source: Grammar Ch.7
    """
    entry = CONCORDIAL_AGREEMENT.get(noun_class)
    if not entry:
        return adjective_stem.lstrip('-')
    adj_prefix = entry[2]  # adjectival concord
    stem = adjective_stem.lstrip('-')
    return adj_prefix.rstrip('-') + stem


def build_plural(singular: str) -> str | None:
    """
    Return the plural of a Runyoro-Rutooro noun.
    Checks the known irregular class-11 plurals first, then applies
    prefix-substitution rules for regular nouns.
    Source: Grammar Ch.7
    """
    # 1. Known irregular plurals (class 11 → 10)
    known = PLURAL_SOUND_CHANGES.get(singular.lower().strip())
    if known:
        return known

    # 2. Regular prefix substitution
    w = singular.lower().strip()
    noun_classes_list = get_noun_class(w)
    if not noun_classes_list:
        return None
    nc = noun_classes_list[0]
    info = NOUN_CLASSES.get(nc)
    if not info:
        return None

    pl_class = info.get("pl_class")
    pl_info  = NOUN_CLASSES.get(pl_class) if pl_class else None
    if not pl_info:
        return None

    # Strip singular prefix, attach plural prefix
    sg_pfx = info.get("sg_prefix", "").rstrip('-')
    if sg_pfx and w.startswith(sg_pfx):
        stem = w[len(sg_pfx):]
    else:
        stem = w

    pl_pfx = pl_info.get("sg_prefix", "").rstrip('-')
    # Choose vowel-initial variant if stem starts with a vowel
    if stem and stem[0] in 'aeiou':
        pl_pfx = pl_info.get("sg_prefix_v", pl_pfx).rstrip('-')

    return pl_pfx + stem if pl_pfx else None


def apply_class9_nasal_prefix(stem: str) -> str:
    """
    Apply class 9 nasal prefix rule: en- before consonants, em- before b/p.
    e.g. 'boga' → 'emboga',  'taka' → 'entaka'
    Source: Grammar Ch.7
    """
    if not stem:
        return stem
    first = stem[0].lower()
    if first in ('b', 'p'):
        return 'em' + stem
    return 'en' + stem


def build_verb_form(
    verb_stem: str,
    person: str = "3sg",
    tense: str = "present_imperfect",
    negative: bool = False,
) -> str:
    """
    Assemble a full verb form from its components.
    person: '1sg','2sg','3sg','1pl','2pl','3pl'
    tense:  'present_imperfect','recent_past','remote_past','future','perfect',
            'present_indefinite'
    Source: Grammar Ch.4, Ch.13

    Examples:
        build_verb_form('genda', '1sg', 'present_imperfect') → 'nigenda'
        build_verb_form('genda', '3sg', 'future')            → 'araagenda'
        build_verb_form('genda', '1sg', 'present_imperfect', negative=True) → 'tinigenda'
    """
    # Subject prefix raw (e.g. "n-", "o-", "a-", "tu-", "mu-", "ba-")
    subj_raw = SUBJECT_PREFIXES.get(person, "n-")
    subj = subj_raw.rstrip('-')

    tense_map = {
        "present_imperfect":  "ni",
        "recent_past":        "a",
        "remote_past":        "ka",
        "future":             "raa",
        "perfect":            "",   # suffix -ire handles this
        "present_indefinite": "",
    }
    t_marker = tense_map.get(tense, TENSE_MARKERS.get(tense, "").rstrip('-'))

    # For present_imperfect: the tense marker 'ni' already encodes the subject
    # prefix for 1sg (n + ni → ni, not nni).  Fuse subject + tense correctly.
    if t_marker == "ni":
        # 1sg: n + ni → ni  (not nni)
        if subj == "n":
            prefix = "ni"
        # 2sg: o + ni → oni
        elif subj == "o":
            prefix = "oni"
        # 3sg: a + ni → ni (a is absorbed)
        elif subj == "a":
            prefix = "ni"
        # 1pl: tu + ni → tuni
        elif subj == "tu":
            prefix = "tuni"
        # 2pl: mu + ni → muni
        elif subj == "mu":
            prefix = "muni"
        # 3pl: ba + ni → bani
        elif subj == "ba":
            prefix = "bani"
        else:
            prefix = subj + t_marker
    else:
        prefix = subj + t_marker

    # Y-insertion: after a-/ra-/raa-/daa- tense prefix + vowel-initial stem
    if t_marker in Y_INSERTION_PREFIXES and verb_stem and verb_stem[0].lower() in 'aeiou':
        core = prefix + 'y' + verb_stem
    else:
        core = prefix + verb_stem

    # ni- prefix vowel harmony before u-class concords
    core = apply_ni_prefix_change(core)

    if negative:
        core = 'ti' + core

    return core


def apply_causative(verb_stem: str) -> str:
    """
    Build the causative form of a verb stem.
    Rules (Grammar Ch.12):
      - monosyllabic stems: add -isa
      - stems ending in -ra: change -ra → -za
      - stems ending in -ta: change -ta → -sa
      - intransitive stems: replace final -a with -ya
    """
    s = verb_stem.lower().strip()
    if len(s) <= 2:                          # monosyllabic
        return s + 'isa'
    if s.endswith('ra') and len(s) > 3:
        return s[:-2] + 'za'
    if s.endswith('ta') and len(s) > 3:
        return s[:-2] + 'sa'
    # Default intransitive: replace final -a with -ya
    if s.endswith('a'):
        return s[:-1] + 'ya'
    return s + 'isa'


def apply_passive(verb_stem: str) -> str:
    """
    Build the passive form of a verb stem.
    Rules (Grammar Ch.12):
      - monosyllabic (ha/ta/sa): vowel-lengthened + -bwa  (ha→heebwa, ta→teebwa, sa→siibwa)
      - monosyllabic labialised (cwa/lya): replace final vowel with -ibwa
      - other verbs: insert -w- before final -a
    """
    s = verb_stem.lower().strip()
    # Monosyllabic simple stems (single consonant + a)
    _mono_passive = {"ha": "heebwa", "ta": "teebwa", "sa": "siibwa",
                     "ba": "beebwa", "fa": "fiibwa"}
    if s in _mono_passive:
        return _mono_passive[s]
    # Monosyllabic labialised (cwa, lya, etc.)
    if len(s) <= 3 and s.endswith(('wa', 'ya')):
        return s.rstrip('awy') + 'ibwa'
    # General: insert w before final a
    if s.endswith('a'):
        return s[:-1] + 'wa'
    return s + 'ibwa'


def apply_neuter(verb_stem: str) -> str:
    """
    Build the neuter/stative form of a verb stem.
    Rules (Grammar Ch.12):
      - stems ending in -ra: replace -ra with -ka
      - other stems: replace final -a with -ika
    """
    s = verb_stem.lower().strip()
    if s.endswith('ra') and len(s) > 3:
        return s[:-2] + 'ka'
    if s.endswith('a'):
        return s[:-1] + 'ika'
    return s + 'ika'


def apply_reciprocal(verb_stem: str) -> str:
    """
    Build the reciprocal/associative form of a verb stem.
    Rule (Grammar Ch.12): add -ngana for reciprocal, -na for associative.
    Default returns the reciprocal (-ngana) form.
    """
    s = verb_stem.lower().strip()
    if s.endswith('a'):
        return s[:-1] + 'angana'
    return s + 'ngana'


def get_adjective_concord(noun_class: int | str) -> str:
    """Return the adjectival concord prefix for a noun class."""
    entry = CONCORDIAL_AGREEMENT.get(noun_class)
    return entry[2].rstrip('-') if entry else ""


def get_demonstrative(noun_class: int | str) -> str:
    """Return the demonstrative pronoun for a noun class."""
    entry = CONCORDIAL_AGREEMENT.get(noun_class)
    return entry[3] if entry else ""


def get_numeral_concord(noun_class: int | str) -> str:
    """Return the numeral concord prefix for a noun class (for numbers 1-5)."""
    return NUMERAL_CONCORDS.get(noun_class, "")


def build_ordinal(n: int, noun_class: int | str) -> str:
    """
    Build an ordinal numeral in concordial agreement with a noun class.
    1st: genitive_particle + okubanza
    2nd-5th: genitive_particle + ka- + numeral_stem
    6th+: genitive_particle + cardinal
    Source: Grammar Ch.4
    """
    # Genitive particle per noun class (from GENITIVE_PARTICLES)
    _gen = {
        1: "wa", "1a": "wa", 2: "ba", "2a": "ba",
        3: "gwa", 4: "ya", 5: "lya", 6: "ga",
        7: "kya", 8: "bya", 9: "ya", 10: "za",
        "9a": "ya", "10a": "za",
        11: "rwa", 12: "ka", 13: "twa", 14: "bwa", 15: "kwa",
    }
    gen = _gen.get(noun_class, "gwa")

    if n == 1:
        return f"{gen} okubanza"
    ordinal_stems = {2: "kabiri", 3: "kasatu", 4: "kana", 5: "kataano"}
    if n in ordinal_stems:
        return f"{gen} {ordinal_stems[n]}"
    # 6th+: use cardinal
    cardinal = NUMBERS.get(n, str(n))
    return f"{gen} {cardinal}"


# ─────────────────────────────────────────────────────────────────────────────
# OCR GRAMMAR RULES — loaded from data/OCR/combined/all_ocr_combined.json
# Sources: A Grammar of Runyoro-Rutooro, Chapters 15, 16, 17
# ─────────────────────────────────────────────────────────────────────────────

import json as _json
import os as _os

_OCR_PATH = _os.path.join(_os.path.dirname(__file__), "data", "OCR", "combined", "all_ocr_combined.json")

def _load_ocr() -> dict:
    try:
        with open(_OCR_PATH, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}

_OCR_DATA = _load_ocr()


# ─────────────────────────────────────────────────────────────────────────────
# COMPARISON RULES (Chapter 16 — Adjectives and Adverbs)
# ─────────────────────────────────────────────────────────────────────────────

# Positive degree — equality
COMPARISON_POSITIVE = {
    "nka": {
        "meaning": "as ... as (equality)",
        "rule": "Place 'nka' between the adjective/adverb and the noun being compared to.",
        "examples": [
            ("Omwana onu aliba muraira nka ise.", "This child will be as tall as his father."),
            ("Abaza kurungi nk'abahumakati.", "She speaks as sweetly as noble ladies do."),
            ("Okwera nk'ebirika", "to be as white as snow"),
            ("okwiragura nk'amakara", "to be as black as charcoal"),
            ("okusaarra nka kaamurali", "to be as bitter as pepper"),
        ],
    },
    "okwingana": {
        "meaning": "to be equal to (mainly negative sentences)",
        "rule": "Use 'okwingana' like 'nka' but mainly in negative constructions.",
        "examples": [
            ("Omwana onu taliba muraira okwingana ise.", "This child will not be so tall as his father."),
            ("Ombuzi ingana engabi obukooto.", "A goat is as big as a bush-buck."),
            ("Abaza kurungi okwingana Basaaliza.", "He does not speak so clearly as Basaaliza does."),
        ],
    },
    "nikyo_kimu_na": {
        "meaning": "it is the same as",
        "rule": "Use 'nikyo kimu na' when no need to mention quality explicitly.",
        "examples": [
            ("Ekitabu ekyange nikyo kimu n'ekyawe.", "My book is the same as yours."),
            ("Endubata ye nikyo kimu n'eya ise.", "His way of walking is the same as that of his father."),
        ],
    },
}

# Comparative degree — one exceeds another
COMPARISON_COMPARATIVE = {
    "okukira": {
        "meaning": "to surpass / exceed (comparative)",
        "rule": "Place 'okukira' between the adjective/adverb and the noun being surpassed.",
        "examples": [
            ("Muka Rwakaikara mukooto okukira muka Balinda.", "Rwakaikara's wife is bigger than Balinda's wife."),
            ("Entale ntaito okukira embogo.", "A lion is smaller than a buffalo."),
            ("Bagonza abaza kurungi okukira Balinda.", "Bagonza speaks more clearly than Balinda."),
            ("Motoka iruka okukira egaali y'omwika.", "A car travels faster than a train."),
            ("Abakazi barra muno okukira abasaija.", "Women weep more than men."),
        ],
        "causative_form": {
            "rule": "Causative form of okukira: quality expressed as abstract noun.",
            "examples": [
                ("Muka Rwakaikara naakiza muka Balinda obukooto.", "Rwakaikara's wife is bigger than Balinda's wife."),
                ("Bagonza akiza Balinda kubaza kurungi.", "Bagonza speaks more clearly than Balinda."),
            ],
        },
        "passive_form": {
            "rule": "Passive form rarely used; reverses subject/object.",
            "examples": [
                ("Muka Balinda naakirwa muka Rwakaikara kunyeeta.", "Rwakaikara's wife is bigger than Balinda's wife."),
                ("Balinda akirwa Bagonza kubaza kurungi.", "Bagonza speaks more clearly than Balinda."),
            ],
        },
    },
}

# Superlative degree — greatest of all
COMPARISON_SUPERLATIVE = {
    "okukira_bombi": {
        "meaning": "surpasses both / greatest of all",
        "rule": "Use okukira + bombi (both) or okubakira/okugikira bombi for superlative.",
        "examples": [
            ("Muka Baguma mukooto okubakira bombi.", "Baguma's wife is the biggest of all."),
            ("Enjojo neekira byombi obukooto.", "An elephant is the biggest of the two."),
            ("Kamuturaki abaza kurungi okubakira bombi.", "Kamuturaki speaks most clearly of all."),
        ],
    },
    "okukiirra_kimu": {
        "meaning": "surpasses beyond measure (absolute superlative)",
        "rule": "Use prepositional verb okukiirra + kimu (utterly) + bombi for absolute superlative.",
        "examples": [
            ("Owa Bagambaki naakiirra kimu bombi obukuru.", "Bagambaki's child is the oldest of all."),
            ("Enyonyi iruka okukiirra kimu byombi.", "An aeroplane runs fastest of all."),
            ("Ekitindinda nikyo kikira ebyekuurra ebindi byona kugenda mpora.",
             "It is the snail which travels most slowly of all creeping creatures."),
        ],
    },
}

# Similes (common comparison phrases)
SIMILES = {
    "okwera nk'ebirika":        "to be as white as snow",
    "okwera nk'enyange":        "to be as white as an egret",
    "okwiragura nk'amakara":    "to be as black as charcoal",
    "okusaarra nka kaamurali":  "to be as bitter as pepper",
}


# ─────────────────────────────────────────────────────────────────────────────
# GENITIVE PARTICLES (Chapter 17 — Joining Words)
# ─────────────────────────────────────────────────────────────────────────────

GENITIVE_PARTICLES = {
    "wa":  ("cl.1/3/11/14/15", "Omwana wa Byaruhanga — Byaruhanga's child"),
    "ba":  ("cl.2",            "Abaana ba Byaruhanga — Byaruhanga's children"),
    "gwa": ("cl.3",            "Omutwe gwa Kugonza — Kugonza's head"),
    "ya":  ("cl.4/9/10",       "Emitaano ya Uganda — Uganda's boundaries"),
    "lya": ("cl.5",            "Eryato ly'abasohi — The fishermen's boat"),
    "kya": ("cl.7",            "Ekigambo kya Ruhanga — God's word"),
    "ga":  ("cl.6",            "Amagezi g'abantu — People's wisdom"),
    "bya": ("cl.8",            "Ebitabu by'abeegi — the pupils' books"),
    "za":  ("cl.10",           "Embuzi za Byakutaaga — Byakutaaga's goats"),
    "rwa": ("cl.11",           "Orugoye rwa mutabani we — his son's cloth"),
    "ka":  ("cl.12",           "Akasozi ka nseeri hali — yonder hill"),
    "twa": ("cl.13",           "Otwizi twa Rulendera — Rulendera's little water"),
    "bwa": ("cl.14",           "Obwana bwa Ruyonga — Ruyonga's little children"),
    "kwa": ("cl.15",           "Okweta kwa Ruhanga — God's call"),
}

GENITIVE_NOTE = (
    "The -a of relationship is elided when followed by a word beginning with a vowel, "
    "e.g. g'abantu (not ga abantu), by'abeegi (not bya abeegi)."
)


# ─────────────────────────────────────────────────────────────────────────────
# ADVERBIAL PARTICLES (Chapter 17B)
# ─────────────────────────────────────────────────────────────────────────────

ADVERBIAL_PARTICLES = {
    "place_position_direction": {
        "omu":          ("in/into", "Ebikere biri omumaizi. — Frogs are in the water."),
        "ha":           ("at/on", "Omusaija aikaliire hantebe. — The man is sitting on the chair."),
        "omwa":         ("to (home of)", "Genda omwa so. — Go to your father's home."),
        "gwomba":       ("from the area of", "Abaire naaruga gwomba Bigirwenkya. — He was coming from the area where Bigirwenkya stays."),
        "haiguru ya":   ("over/above", "Etaara eri haiguru y'emeeza. — The lamp is over the table."),
        "omumaiso ga":  ("in front of", "Oruguudo ruli omumaiso g'enju yaitu. — The road is in front of our house."),
        "harubaju rwa": ("by the side of", "Yemeerra harubaju rwa mugenzi waawe. — Stand by the side of your partner."),
        "hagati ya":    ("between", "Mugisa ayemeriire hagati ya Birungi na Basemera. — Mugisa is standing between Birungi and Basemera."),
        "enyuma ya":    ("behind", "Nkitaire enyuma y'entebe. — I have put it behind the chair."),
        "omunda ya":    ("inside/into", "Abaana boona bakaba bamazire ira kuhika omunda y'isomero. — All the pupils had already got into the school compound."),
        "aheeru ya":    ("outside", "Nkamusanga aheeru y'enju yange. — I found him outside my house."),
    },
    "reason_cause": {
        "habwa":        ("because of", "Ayosire habwa nyina kurwara. — She is absent because her mother is ill."),
        "habwokuba":    ("because", "Taizire habwokuba ali wenka omuka. — He has not come because he is alone at home."),
        "habweki":      ("therefore", "Ombiihire nahabweki tindikwesiga. — You have lied to me therefore I shall not trust you."),
        "nkooku":       ("since/because", "Nkooku nyineeka ataroho ebigambo ka tubireke. — Since the householder is away let us stop the matter."),
    },
    "time": {
        "obu":          ("when", "Izooba obu lyagwire baagoonya. — When the sun set they got lodged."),
        "obwa":         ("during", "Babyesiza akazaarwa obwa Kabaleega. — Babyesiza was born during Kabaleega's reign."),
        "okuruga...okuhikya": ("from...till", "Bakasiiba nibakora okuruga nnyenkya okuhikya rwebagyo. — They worked from morning till evening."),
        "hanyuma ya":   ("after", "Byakutaaga akaija hanyuma ya Rwatooro. — Byakutaaga came after Rwatooro."),
    },
    "manner": {
        "nka":          ("like/as", "Abaza nka ise. — He speaks like his father."),
        "oku":          ("as (manner)", "Baza oku abasaija babaza. — Speak as men do."),
        "nkooku":       ("as/like (manner)", "Akozire nkooku agondeze. — He acted as he wished."),
        "na":           ("by means of", "Akaija na bbaasi. — He came by bus."),
        "hamu na":      ("together with", "Bakagenda hamu na nyina. — Both mother and child went."),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# CO-ORDINATING PARTICLES (Chapter 17C)
# ─────────────────────────────────────────────────────────────────────────────

COORDINATING_PARTICLES = {
    # Joining words of same grammatical function
    "na":               "and / with — Rwabudongo na Ireeta batamba kimu.",
    "hamu na":          "together with — Embuzi hamu n'ente bisoro by'omumaka.",
    "rundi":            "or / either...or — Mpa enyama rundi encu.",
    "kandi":            "and / but / in addition — Kateesigwa mugara kandi murofu.",
    "kandi n'ekindi":   "as well as — Muhoole kandi n'ekindi mudoma.",

    # Subordinating conjunctions
    "kakusangwa":       "if (conditional) — Kakusangwa obaireho taakukitwaire.",
    "kakuba / kuba":    "if (conditional) — Kakuba abantu baagizire amapapa baakuhaarruukire.",
    "obu":              "if / when — Obu araija turaamutangiirra.",
    "noobwakubaire":    "even if / although — Noobwakubaire uwe wenka aizire taakukimuhaire.",

    # Co-ordinate rank connectors
    "baitu":            "but — Nyowe nkamurora baitu uwe atandole.",
    "kyonka":           "but — Akandora kyonka ataammanyiirre.",
    "nikyo kinu":       "all the same — Akamuteera baitu nikyo kimu atazire.",
    "kandi kunu":       "though / even though — Amucumbira kandi kunu ebyokulya nuwe abigura.",
    "kunu obu nu":      "whereas — Naamugaya kunu obu nu nuwe yamwegeseze.",
    "ntamanya":         "without knowing — Akaba naaseerra kucwa ntamanya abaserukale bamuboine.",
    "obwolyaho":        "in case — Mugende mumurole obwolyaho murwaire.",
    "tomanya":          "for it is unlikely — Kangende tomanya onu obundi taije.",
    "osanga obundi":    "as he may not — Otabaza bingi osanga obundi tali nuwe akitwaire.",
    "ngu":              "that (reported speech) — Agizire ngu murwaire. (He said that he is ill.)",
    "noobwakubaire ngu":"although...that — Noobwakubaire ngu nuwe yabandize kwija atasobole kulya mukuru we.",
}


# ─────────────────────────────────────────────────────────────────────────────
# CONDITIONAL MOOD (Chapter 15 — Compound Tenses)
# ─────────────────────────────────────────────────────────────────────────────

CONDITIONAL_MOOD = {
    "particles": ["kakuba", "kuba", "kakusangwa", "kusangwa", "obu"],
    "description": (
        "The conditional mood expresses hypothetical situations. "
        "Introduced by kakuba/kuba/kakusangwa/kusangwa (if) or obu (if/when). "
        "The verb in the condition clause takes a special compound tense form."
    ),
    "positive_with_kakuba": {
        "rule": "kakuba/kuba/kakusangwa/kusangwa + past tense verb → result clause",
        "examples": [
            ("Kuba okubaire ompaire omulimo naakugukozire.",
             "If you had given me some work I should have done it."),
            ("Obu akubaire aina omulimo akugukuhaire.",
             "If he had had a job he would have given it to you."),
            ("Obu nkubaire ndi mwomeezi nkukusendekeriize.",
             "If I had been healthy I should have seen you off."),
        ],
    },
    "negative_with_kakuba": {
        "rule": "kakuba/kuba + negative past verb → negative result",
        "examples": [
            ("Kuba obaire(ge) otampaire omulimo tinkukozire kantu.",
             "If you had not given me some work I should not have done anything."),
            ("Obu akubaire ataina burwaire taakugiire mwirwarro.",
             "If he had had no illness he would not have gone to hospital."),
            ("Obu nkubaire ntali murwaire nkukusendekeriize.",
             "If I had not been ill I should have seen you off."),
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# OCR UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_ocr_grammar_text(section: str) -> str:
    """Return raw OCR text for a grammar section (e.g. 'grammar2_adjectives_adverbs')."""
    section_data = _OCR_DATA.get(section, {})
    return "\n\n".join(section_data.values())


def get_comparison_rule(degree: str) -> dict:
    """Return comparison rules for 'positive', 'comparative', or 'superlative'."""
    return {
        "positive":     COMPARISON_POSITIVE,
        "comparative":  COMPARISON_COMPARATIVE,
        "superlative":  COMPARISON_SUPERLATIVE,
    }.get(degree, {})


def lookup_genitive_particle(particle: str) -> str | None:
    """Return description for a genitive particle (e.g. 'wa', 'bya')."""
    entry = GENITIVE_PARTICLES.get(particle.lower().strip())
    return f"{entry[0]}: {entry[1]}" if entry else None


def lookup_coordinating_particle(word: str) -> str | None:
    """Return meaning/usage of a co-ordinating particle."""
    return COORDINATING_PARTICLES.get(word.lower().strip())


def get_extended_grammar_context() -> str:
    """Extended grammar context including OCR-derived rules for chat/translation prompts."""
    base = get_grammar_context()
    ocr_rules = (
        "\n--- OCR Grammar Rules (Chapters 15-17) ---\n"
        "COMPARISON:\n"
        "  Positive (equality): nka / okwingana — 'as...as'\n"
        "    e.g. Omwana onu aliba muraira nka ise. (This child will be as tall as his father.)\n"
        "  Comparative: okukira — 'more than / -er than'\n"
        "    e.g. Muka Rwakaikara mukooto okukira muka Balinda. (Rwakaikara's wife is bigger.)\n"
        "  Superlative: okukira bombi / okukiirra kimu bombi — 'most / -est of all'\n"
        "    e.g. Muka Baguma mukooto okubakira bombi. (Baguma's wife is the biggest of all.)\n"
        "\nGENITIVE PARTICLES (possession): wa/ba/gwa/ya/lya/kya/ga/bya/za/rwa/ka/twa/bwa/kwa\n"
        "  Elide -a before vowels: g'abantu, by'abeegi, ly'abasohi\n"
        "\nCONDITIONAL MOOD: kakuba / kuba / obu + past tense\n"
        "  e.g. Kuba okubaire ompaire omulimo naakugukozire.\n"
        "       (If you had given me work I should have done it.)\n"
        "\nCO-ORDINATING PARTICLES:\n"
        "  na (and), rundi (or), kandi (but/and), kyonka (but), ngu (that/reported speech),\n"
        "  obu (if/when), noobwakubaire (even if), obwolyaho (in case)\n"
        "\nADVERBIAL PARTICLES:\n"
        "  Place: omu (in), ha (at), haiguru ya (above), hagati ya (between), aheeru ya (outside)\n"
        "  Time: obu (when), obwa (during), hanyuma ya (after)\n"
        "  Reason: habwa (because of), habwokuba (because), habweki (therefore)\n"
        "  Manner: nka (like), oku (as), hamu na (together with)\n"
    )
    return base + ocr_rules






# ─────────────────────────────────────────────────────────────────────────────
# VOWEL LENGTH MINIMAL PAIRS
# Source: grammar rules 2 (1).docx — Vowel Rules
# ─────────────────────────────────────────────────────────────────────────────

VOWEL_LENGTH_MINIMAL_PAIRS = {
    "okubaga":  ("to weave into wattle",  "okubaaga",  "to skin"),
    "okuceba":  ("to pound, to crush",    "okuceeba",  "to wear many clothes"),
    "okusika":  ("to pull",               "okusiika",  "to fry"),
    "okugoba":  ("to steal milk from cow","okugooba",  "to interlace e.g. reeds"),
    "okujura":  ("to be homesick",        "okujuura",  "to undress"),
    "kora":     ("work",                  "koorra",    "cough"),
    "hara":     ("scrape",                "haarra",    "scrape together"),
    "omuro":    ("sleepiness",            "omuurro",   "fire"),
    "okusara":  ("to cut",                "okusaarra", "to be bitter"),
    "okusera":  ("to sing and dance at night", "okuseerra", "to look for"),
}

LONG_VOWEL_NOTE = (
    "Short vowels: single vowel graph (a, e, i, o, u). "
    "Long vowels: doubled vowel graph (aa, ee, ii, oo, uu). "
    "Vowel length changes meaning — see VOWEL_LENGTH_MINIMAL_PAIRS."
)

SHORT_VOWEL_EXAMPLES = {
    "a": ["amata (milk)", "okufa (to die)"],
    "e": ["ekikere (frog)", "oruseke (tube)"],
    "i": ["obutiti (cold)", "omutini (fig tree)"],
    "o": ["omusoga (castor oil tree)", "ekisole (puppy)"],
    "u": ["obuhuta (wound)", "ekijuma (fruit)"],
}

LONG_VOWEL_EXAMPLES = {
    "aa": ["abaana (children)", "omugaati (bread)"],
    "ee": ["abeegi (pupils)", "omukeeka (mat)"],
    "ii": ["eriiba (dove)", "ekiina (hole)"],
    "oo": ["aboojo (boys)", "ekicooli (maize)"],
    "uu": ["okuhanuura (to discuss)", "okuhuuna (to rumble)"],
}


# ─────────────────────────────────────────────────────────────────────────────
# GEMINATE R — words where double-r arose from dropped vowel
# Source: grammar rules 2 (1).docx — Consonants Rules §5b
# ─────────────────────────────────────────────────────────────────────────────

GEMINATE_R_WORDS = {
    "obuteerre":  ("obuterere",  "slipperiness"),
    "omuurro":    ("omuliro",    "fire"),
    "enkoorro":   ("enkororo",   "cough"),
    "koorra":     ("kora",       "cough (verb)"),
    "haarra":     ("hara",       "scrape together"),
    "okusaarra":  ("okusara",    "to be bitter"),
    "okuseerra":  ("okusera",    "to look for"),
}

GEMINATE_R_NOTE = (
    "Double-r (rr) in Runyoro-Rutooro arose from words that dropped the vowel "
    "originally between two r's. The rr is pronounced long (geminated). "
    "e.g. omuliro → omuurro (fire), enkororo → enkoorro (cough)."
)


# ─────────────────────────────────────────────────────────────────────────────
# LABIALISED CONSONANTS (w-Compounds)
# Source: grammar rules 2 (1).docx — Consonants Rules §2
# ─────────────────────────────────────────────────────────────────────────────

LABIALISED_CONSONANTS = [
    "bw", "cw", "dw", "gw", "hw", "jw", "kw", "mw", "nw", "nyw",
    "pw", "rw", "sw", "tw", "yw", "zw",
]

LABIALISED_PRENASALS = [
    "mbw", "ncw", "ndw", "ngw", "njw", "nkw", "mmw", "nnw", "nnyw",
    "mpw", "nsw", "ntw", "nzw",
]

W_COMPOUND_RULES = {
    "end_of_word":    "w-compounds at end of word are pronounced SHORT. e.g. akabwa, ihwa, akunywa",
    "elsewhere":      "w-compounds elsewhere in word are pronounced LONG. e.g. okubwagura, okunywana",
    "genitive":       "w-compounds in genitive particles without initial vowel are pronounced LONG. e.g. gwa, rwa, bwa, kwa",
    "no_double_vowel":"Vowel length after w-compounds is NEVER indicated by doubling the vowel.",
}

W_COMPOUND_EXAMPLES = {
    "short_end":  ["akabwa (small dog)", "ihwa (thorn)", "akunywa (to drink)", "okugwa (to fall)"],
    "long_mid":   ["okubwagura (to bear puppies)", "okuhwahwana (to wander)", "okunywana (to make blood brotherhood)"],
    "with_aa":    ["okubaagwa (to be skinned)", "okutaahwa (to be entered into)"],
    "with_ee":    ["okuheebwa (to be given)", "okuheekwa (to be carried pick-a-back)"],
    "with_ii":    ["okudiidwa (to be criticised)", "okuhiigwa (to be hunted)"],
    "with_oo":    ["okugoorwa (to be damaged)", "okuhoorwa (to be revenged)"],
    "with_uu":    ["okuduupwa (to be incited)", "okuhuuhwa (to be blown about)"],
    "diphthong_ai": ["okugaitwa (to be joined)", "okuhaigwa (to be dug up potatoes)"],
    "diphthong_ei": ["okujeijwa (of private affairs: to be talked about)"],
    "diphthong_oi": ["okuhoitwa (to be rebuked)", "okutoijwa (to be tilled)"],
}


# ─────────────────────────────────────────────────────────────────────────────
# PALATALISED CONSONANTS (y-Compounds)
# Source: grammar rules 2 (1).docx — Consonants Rules §3
# ─────────────────────────────────────────────────────────────────────────────

PALATALISED_CONSONANTS = [
    "by", "dy", "gy", "hy", "ky", "ly", "my", "ny", "py", "ry", "ty",
]

PALATALISED_PRENASALS = [
    "mby", "ndy", "ngy", "nky", "mmy", "nni", "mpy", "nty",
]

Y_COMPOUND_RULES = {
    "end_of_word":    "y-compounds at end of word are pronounced SHORT. e.g. engagya, omulyo, okukya",
    "elsewhere":      "y-compounds elsewhere in word are pronounced LONG. e.g. emyekuniko, ekyakyo, okubyama",
    "genitive":       "y-compounds in genitive particles without initial vowel are pronounced LONG. e.g. lya, kya, bya",
    "no_double_vowel":"Vowel length after y-compounds is NEVER indicated by doubling the vowel.",
}

Y_COMPOUND_EXAMPLES = {
    "short_end":  ["engagya (large spotted hyena)", "omulyo (right hand)", "okukya (of rain: to be over)"],
    "long_mid":   ["emyekuniko (arrogance)", "ekyakyo (flower)", "okubyama (to lie down)"],
    "with_aa":    ["okuhaagya (to finish milking)", "okusaagya (to exaggerate)"],
    "with_ee":    ["okukeehya (to diminish)", "okuseegya (to nearly kill)"],
    "with_ii":    ["okubiihya (to have an ugly thing about oneself)"],
    "with_oo":    ["aboohya (tempters)", "okuhookya (to cause domestic animal illness)"],
    "with_uu":    ["okufuuhya (to prevent evil)"],
    "diphthong_ai": ["obutaikya (without breathing)", "okuraihya (of a king: to go to bed)"],
    "diphthong_oi": ["okuhoigya (to cause to burn to ashes)", "okukogya (to make thin)"],
}


# ─────────────────────────────────────────────────────────────────────────────
# SOUND CHANGE — VOWEL MERGING & ELISION
# Source: grammar rules 2 (1).docx — Chapter Two: Sound Change
# ─────────────────────────────────────────────────────────────────────────────

VOWEL_MERGING_NOTE = (
    "When two words come together, the final vowel of the first merges with the "
    "initial vowel of the second to make a long vowel. This merging is NOT shown "
    "in orthography for regular words, but IS shown with an apostrophe when the "
    "first word is a particle. e.g. omwa omusaija → omw'omusaija."
)

VOWEL_MERGING_EXAMPLES = {
    "particle_elision": {
        "omwa omusaija":    "omw'omusaija (in the man's house)",
        "owa omunyoro":     "ow'omunyoro (to the Chief's)",
        "omba omunyoro":    "omb'omunyoro (at the Chief's)",
        "habwa okugonza":   "habw'okugonza (through love)",
        "muka omunyoro":    "muk'omunyoro (the chief's wife)",
        "entale na omuhiigi": "entale n'omuhiigi (the lion and the hunter)",
        "kubaza nka omwana":  "kubaza nk'omwana (to speak like a child)",
        "obwa okufa ngada":   "obw'okufa ngada (it is better for me to suffer than die)",
    },
    "two_similar_vowels": {
        "aba-ana":  "abaana (children)",
        "ti-izire": "tiizire (it has not come)",
        "nte-eyera":"nteeyera (white cow)",
        "eki-ibo":  "ekiibo (basket)",
    },
    "similar_before_nasal": {
        "bi-ingi":       "bingi (many, cl.8)",
        "ni-inganaha":   "ninganaha (how big is it?, cl.9)",
        "ba-angire":     "bangire (they have refused)",
    },
    "two_different_vowels_merger": {
        "ama-ezi":   "ameezi (months, moons)",
        "ti-alye":   "taalye (he/she will not eat)",
        "ama-oga":   "amooga (baths)",
        "ante-ire":  "antiire (he/she has beaten me)",
        "ti-okole":  "tookole (you will not work)",
        "ni-ekomba": "neekomba (it is eating, cl.9)",
    },
    "vowel_elision": {
        "ti-oyosa":     "toyosa (you never absent yourself)",
        "ti-ayosa":     "tayosa (he/she never absents himself)",
        "abaana ba-e":  "abaana be (his/her children)",
        "ente ya-e":    "ente ye (his/her cattle)",
    },
    "diphthongization": {
        "amaizi":   "water",
        "ataije":   "he/she did not come",
        "oibire":   "you have stolen",
        "okweita":  "to commit suicide",
    },
    "semi_vowel_substitution": {
        "eki-ererezi":      "ekyererezi (light) — i→y before vowel",
        "omu-ana":          "omwana (child) — u→w before vowel",
        "Isenkuru-itwe":    "Isenkurwitwe (our grandfather) — u→w",
        "Nyinenkuru-itwe":  "Nyinenkurwitwe (our grandmother) — u→w",
    },
}

# Particle elision patterns (extends apostrophe rule)
PARTICLE_ELISION_PATTERNS = {
    "omwa":  "omw'",   # omwa + vowel → omw'
    "owa":   "ow'",    # owa + vowel → ow'
    "omba":  "omb'",   # omba + vowel → omb'
    "habwa": "habw'",  # habwa + vowel → habw'
    "muka":  "muk'",   # muka + vowel → muk'
    "nka":   "nk'",    # nka + vowel → nk'
    "obwa":  "obw'",   # obwa + vowel → obw'
    "na":    "n'",     # na + vowel → n'
    "za":    "z'",     # za + vowel → z'
    "ka":    "k'",     # ka + vowel → k'
    "ya":    "y'",     # ya + vowel → y'
    "wa":    "w'",     # wa + vowel → w'
    "ga":    "g'",     # ga + vowel → g'
    "ba":    "b'",     # ba + vowel → b'
    "lya":   "ly'",    # lya + vowel → ly'
    "kya":   "ky'",    # kya + vowel → ky'
    "bya":   "by'",    # bya + vowel → by'
    "rwa":   "rw'",    # rwa + vowel → rw'
    "twa":   "tw'",    # twa + vowel → tw'
    "bwa":   "bw'",    # bwa + vowel → bw'
    "kwa":   "kw'",    # kwa + vowel → kw'
    "gwa":   "gw'",    # gwa + vowel → gw'
}


def apply_particle_elision(text: str) -> str:
    """
    Apply particle elision with apostrophe for ALL Runyoro-Rutooro particles
    before vowel-initial words. Extends apply_apostrophe_elision with the
    full set of particles from the grammar document.

    e.g. omwa omusaija → omw'omusaija
         habwa okugonza → habw'okugonza
         nka omwana    → nk'omwana
         na ente       → n'ente

    Source: grammar rules 2 (1).docx — Chapter Two: Sound Change
    """
    if not text:
        return text
    import re as _re

    result = text
    # Sort by length descending so longer particles match first
    for full, elided in sorted(PARTICLE_ELISION_PATTERNS.items(), key=lambda x: -len(x[0])):
        # Match particle + space + vowel-initial word
        pattern = _re.compile(
            r'\b' + _re.escape(full) + r'\s+(?=[aeiouAEIOU])',
            _re.IGNORECASE
        )
        result = pattern.sub(elided, result)
    return result


def apply_semi_vowel_substitution(text: str) -> str:
    """
    Apply semi-vowel substitution at morpheme boundaries:
    - i → y before another vowel (eki-ererezi → ekyererezi)
    - u → w before another vowel (omu-ana → omwana)

    This applies at prefix-stem boundaries in Runyoro-Rutooro.
    Source: grammar rules 2 (1).docx — Sound Change §Semi-vowels
    """
    if not text:
        return text
    import re as _re
    # i → y before vowel at common prefix boundaries
    result = _re.sub(r'\b(ek)i([aeiou])', r'\1y\2', text, flags=_re.IGNORECASE)
    result = _re.sub(r'\b(ob)i([aeiou])', r'\1y\2', result, flags=_re.IGNORECASE)
    # u → w before vowel at common prefix boundaries
    result = _re.sub(r'\b(om)u([aeiou])', r'\1w\2', result, flags=_re.IGNORECASE)
    result = _re.sub(r'\b(ob)u([aeiou])', r'\1w\2', result, flags=_re.IGNORECASE)
    result = _re.sub(r'\b(ok)u([aeiou])', r'\1w\2', result, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# DOUBLE NASAL CONJUGATION TABLES
# Source: grammar rules 2 (1).docx — Consonants Rules §2b
# ─────────────────────────────────────────────────────────────────────────────

DOUBLE_NASAL_NOTE = (
    "When the first-person singular prefix n- is added to a verb stem beginning "
    "with n or m, a double nasal (nn or mm) is formed. "
    "e.g. n + naabe → nnaabe (that I may wash), n + manya → mmanya (know me)."
)

DOUBLE_NASAL_EXAMPLES = {
    "subjunctive": {
        "ka nnaabe":    "let me wash",
        "nnaabe":       "that I may wash",
        "ka nnyegeerre":"let me accuse that man",
        "nnyegeerre":   "that I may accuse",
        "ka mmanye":    "let me know",
        "mmanye":       "that I may know",
    },
    "present_indefinite": {
        "nnaaba":       "I wash",
        "nnaabya omwana": "I wash the child",
        "nnyegeerra":   "I accuse",
        "mmanya":       "I know",
    },
    "present_imperfect": {
        "niinnaaba":    "I am washing",
        "niinnaabya omwana": "I am washing the child",
        "niinnyegeerra":"I am accusing",
        "niimmanya":    "I know (present imperfect)",
    },
    "present_perfect": {
        "nnaabire":     "I have washed",
        "nnyegeriirege":"I have accused Byenkya",
        "mmanyire":     "I know (perfect)",
    },
    "near_past": {
        "nnaabirege":   "I did wash",
        "nnaabizeege Kiiza": "I did wash Kiiza",
        "mmanyirege":   "I did know",
    },
}

DOUBLE_NASAL_EXCEPTIONS = [
    "emengo (lower millstones) — not *emmengo",
    "emuli (reed torches) — not *emmuli",
    "enwa (beaks) — not *ennwa",
    "enaku (stinging centipedes) — not *ennaku",
    "enumbu (edible tubers) — not *ennumbu",
    "enyaanya (tomatoes) — not *ennyaanya",
    "ente enungi (the good cow) — not *ente ennungi",
]


# ─────────────────────────────────────────────────────────────────────────────
# POST-PROCESSING: CONSONANT + SUFFIX MUTATIONS (text-level)
# Source: Grammar Rule 3 §B — Sound Change in Consonants
# Applies r→z, t→s, j→z before -ire/-ere/-i/-ya in MT output.
# ─────────────────────────────────────────────────────────────────────────────

import re as _re2

# Ordered list of (pattern, replacement) — longer/more-specific first
_CONSONANT_SUFFIX_PATTERNS = [
    # nd + -ire/-ere → -nzire
    (_re2.compile(r'nd(ire|ere)\b', _re2.IGNORECASE), r'nz\1'),
    # nt + -ire/-ere → -nsire
    (_re2.compile(r'nt(ire|ere)\b', _re2.IGNORECASE), r'ns\1'),
    # nd + -i (agent noun suffix) → -nzi
    (_re2.compile(r'nd(i)\b', _re2.IGNORECASE), r'nz\1'),
    # nt + -i → -nsi
    (_re2.compile(r'nt(i)\b', _re2.IGNORECASE), r'ns\1'),
    # r + -ire/-ere (short-vowel stem) → -zire/-zere
    # Guard: only when preceded by a short vowel (not rr, not already z)
    (_re2.compile(r'(?<![rz])r(ire|ere)\b', _re2.IGNORECASE), r'z\1'),
    # t + -ire/-ere → -sire/-sere
    (_re2.compile(r'(?<!s)t(ire|ere)\b', _re2.IGNORECASE), r's\1'),
    # j + -ire/-ere → -zire/-zere
    (_re2.compile(r'j(ire|ere)\b', _re2.IGNORECASE), r'z\1'),
    # r + -i (agent noun) → -zi
    (_re2.compile(r'(?<![rz])r(i)\b', _re2.IGNORECASE), r'z\1'),
    # t + -i → -si
    (_re2.compile(r'(?<!s)t(i)\b', _re2.IGNORECASE), r's\1'),
    # j + -i → -zi
    (_re2.compile(r'j(i)\b', _re2.IGNORECASE), r'z\1'),
    # r + -ya → -za
    (_re2.compile(r'(?<![rz])r(ya)\b', _re2.IGNORECASE), r'z\1'),
    # t + -ya → -sa
    (_re2.compile(r'(?<!s)t(ya)\b', _re2.IGNORECASE), r's\1'),
]

def apply_consonant_suffix_mutations(text: str) -> str:
    """
    Apply consonant + suffix sound changes across all words in MT output.

    Rules (Grammar Rule 3 §B.6):
      r  + -ire/-ere/-i/-ya  →  z + suffix   (e.g. rora → rozire, omurozi, roza)
      t  + -ire/-ere/-i/-ya  →  s + suffix   (e.g. leeta → leesire, omuleesi, leesa)
      j  + -ire/-ere/-i      →  z + suffix   (e.g. hiija → hiizire, omuhiizi)
      nd + -ire/-ere/-i/-ya  →  nz + suffix  (e.g. genda → genzire, omugenzi, genza)
      nt + -ire/-ere/-i/-ya  →  ns + suffix  (e.g. tenta → tensire, omutensi, tensa)

    Source: Grammar Rule 3 §B.5–6
    """
    if not text:
        return text
    result = text
    for pattern, replacement in _CONSONANT_SUFFIX_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# POST-PROCESSING: REFLEXIVE IMPERATIVE CORRECTION (text-level)
# Source: Grammar Rule 3 §4 — Reflexive Verbs
# Corrects okwesereka → weesereke (sg) / mwesereke (pl) in MT output.
# ─────────────────────────────────────────────────────────────────────────────

# Match infinitive forms the model may output: okwesereka, okw-esereka, okwebara, etc.
_REFLEXIVE_INF_RE = _re2.compile(
    r'\bokw[e\-]([a-z]+a)\b',
    _re2.IGNORECASE
)

def apply_reflexive_imperative_correction(text: str) -> str:
    """
    Convert reflexive infinitives that appear in imperative contexts to their
    correct imperative form.

    Singular imperative: okw-esereka → weesereke
    Plural imperative:   okw-esereka → mwesereke

    The model sometimes outputs the infinitive where an imperative is expected.
    This function detects standalone reflexive infinitives (not preceded by a
    tense/subject prefix) and converts them.

    Source: Grammar Rule 3 §4
    """
    if not text:
        return text

    def _replace(m: _re2.Match) -> str:
        stem = m.group(1)          # e.g. "sereka"
        base = stem.rstrip('aA')   # e.g. "serek"
        return 'wee' + base + 'e'  # e.g. "weesereke"

    # Only replace when the infinitive is not preceded by a subject/tense prefix
    # (i.e. it appears at the start of a clause or after punctuation/space)
    result = _re2.sub(
        r'(?<![a-z])' + _REFLEXIVE_INF_RE.pattern,
        _replace,
        text,
        flags=_re2.IGNORECASE
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# POST-PROCESSING: INITIAL VOWEL RULE (text-level)
# Source: Grammar Rule 3 §8 — The Initial Vowel
# Ensures nouns/adjectives carry the correct initial vowel for their class.
# ─────────────────────────────────────────────────────────────────────────────

# Prefix → expected initial vowel
# Rule: initial vowel is 'a' if prefix contains 'a', 'o' if prefix contains 'u',
#       'e' if prefix contains 'i'. Classes 9/10 always use 'e'.
_PREFIX_INITIAL_VOWEL: list[tuple[_re2.Pattern, str]] = [
    # Class 1/2 (omu-/aba-) → initial vowel 'a'
    (_re2.compile(r'\b(omu|aba|omw|ab)([aeiou])', _re2.IGNORECASE), 'a'),
    # Class 3/4 (omu-/emi-) → initial vowel 'a'/'e' already correct by prefix
    # Class 5 (eri-/ery-) → initial vowel 'e'
    (_re2.compile(r'\b(eri|ery)([aeiou])', _re2.IGNORECASE), 'e'),
    # Class 6 (ama-/ame-/amo-) → initial vowel 'a'
    (_re2.compile(r'\b(ama|ame|amo)([aeiou])', _re2.IGNORECASE), 'a'),
    # Class 7/8 (eki-/ebi-) → initial vowel 'e'
    (_re2.compile(r'\b(eki|ebi|eky|eby)([aeiou])', _re2.IGNORECASE), 'e'),
    # Class 9/10 (en-/em-) → initial vowel always 'e'
    (_re2.compile(r'\b(en|em)([aeiou])', _re2.IGNORECASE), 'e'),
    # Class 11 (oru-/orw-) → initial vowel 'o'
    (_re2.compile(r'\b(oru|orw)([aeiou])', _re2.IGNORECASE), 'o'),
    # Class 12/13 (aka-/utu-) → initial vowel 'a'/'o'
    (_re2.compile(r'\b(aka|akw)([aeiou])', _re2.IGNORECASE), 'a'),
    (_re2.compile(r'\b(utu|utw)([aeiou])', _re2.IGNORECASE), 'o'),
    # Class 14 (obu-/obw-) → initial vowel 'o'
    (_re2.compile(r'\b(obu|obw)([aeiou])', _re2.IGNORECASE), 'o'),
    # Class 15 (oku-/okw-) → initial vowel 'o'
    (_re2.compile(r'\b(oku|okw)([aeiou])', _re2.IGNORECASE), 'o'),
]

# Known exceptions where initial vowel rule does NOT apply
_INITIAL_VOWEL_EXCEPTIONS = frozenset({
    "icumu",   # spear — not *eicumu
})

def apply_initial_vowel_rule(text: str) -> str:
    """
    Ensure each noun/adjective carries the correct initial vowel for its class.

    Rules (Grammar Rule 3 §8):
      - Prefix contains 'a' (omu-, aba-, ama-)  → initial vowel 'a'
      - Prefix contains 'u' (oru-, obu-, oku-)  → initial vowel 'o'
      - Prefix contains 'i' (emi-, eki-, ebi-)  → initial vowel 'e'
      - Classes 9/10 (en-/em-)                  → initial vowel always 'e'

    Only corrects words not in the known exceptions list.

    Source: Grammar Rule 3 §8
    """
    if not text:
        return text

    words = text.split()
    corrected = []
    for word in words:
        if word.lower() in _INITIAL_VOWEL_EXCEPTIONS:
            corrected.append(word)
            continue
        new_word = word
        for pattern, iv in _PREFIX_INITIAL_VOWEL:
            # If the word matches a prefix + vowel, ensure the leading vowel is correct
            m = pattern.match(word)
            if m:
                prefix = m.group(1)
                rest = word[len(prefix):]
                # Only fix if the word starts with a wrong initial vowel
                # (i.e. the word has an initial vowel before the prefix)
                # Check if there's a leading vowel that doesn't match
                if rest and rest[0].lower() in 'aeiou' and rest[0].lower() != iv:
                    new_word = prefix + iv + rest[1:]
                break
        corrected.append(new_word)
    return ' '.join(corrected)


# ─────────────────────────────────────────────────────────────────────────────
# EXTENDED OCR RULES — Chapters 2, 4, 7, 9, 10, 12, 13
# Previously in language_rules_ocr_extension.py — merged here to eliminate
# the circular import and provide a single-module interface.
# Sources: A Grammar of Runyoro-Rutooro (OCR), Orthography Guide 1995
# ─────────────────────────────────────────────────────────────────────────────

# ── Chapter 2: Sound Change — Y-insertion examples ───────────────────────────

Y_INSERTION_EXAMPLES = {
    "nayara": "just now I made the bed",
    "baayombeka": "just now they built",
    "ndaayara": "I shall make the bed",
    "turaayara": "we shall make the bed",
    "orayegere": "have you ever studied?",
    "barayombekere": "have they ever built?",
}

Y_INSERTION_COUNTEREXAMPLES = {
    "nkaara": "I made the bed (not nkayara)",
    "ndyara": "I shall make the bed (not ndiyara)",
    "tinkaazire": "I have not made the bed (not tinkayazire)",
}

Y_INSERTION_I_STEMS = {
    "nyizire": "I have come",
    "nyikaliire": "I have sat down",
    "twizire": "we have come",
    "oizire": "you have come",
    "mwizire": "you (pl.) have come",
    "aizire": "he/she has come",
    "baizire": "they have come",
}

# ── Chapter 2: Reflexive verb imperatives ────────────────────────────────────

REFLEXIVE_IMPERATIVES = {
    "weesereke":   ("okw-esereka",  "hide yourself"),
    "weebundaaze": ("okw-ebundaaza","humble yourself"),
    "weerekere":   ("okw-erekera",  "set yourself free"),
    "weebale":     ("okw-ebara",    "thank you (lit. count yourself)"),
    "mwesereke":   ("okw-esereka",  "hide yourselves"),
    "mwebundaaze": ("okw-ebundaaza","humble yourselves"),
    "mwerekere":   ("okw-erekera",  "set yourselves free"),
    "mwebale":     ("okw-ebara",    "thank you (plural)"),
}

REFLEXIVE_NON_REFLEXIVE = {
    "weesigege":    ("okw-esiga",    "trust (lit. trust yourself)"),
    "weetegereze":  ("okw-etegereza","understand"),
    "weebuge":      ("okw-ebuga",    "proclaim your bravery"),
    "weesize":      ("okw-esiza",    "stop crying"),
}

# ── Chapter 2: Conversive verb examples ──────────────────────────────────────

CONVERSIVE_EXAMPLES = {
    "okubamba": {
        "meaning": "to peg out",
        "conversive": {
            "okubambura":    "to unpeg",
            "okubambuurra":  "to completely unpeg",
            "okubambuka":    "to break away",
            "okubamburuka":  "to come unpegged",
            "okubamburruuka":"to completely come unpegged",
        },
    },
    "okuleega": {
        "meaning": "to tighten",
        "conversive": {
            "okuleegura":    "to loosen tight string",
            "okuleeguurra":  "to remove band round neck of cow after being bleeded",
            "okuleeguka":    "to get loose",
            "okuleeguruka":  "to become untightened string",
            "okuleegurruuka":"to come unstrung (bow)",
        },
    },
    "okuboha": {
        "meaning": "to fasten",
        "conversive": {
            "okubohoorra":   "to unfasten",
            "okubohoroka":   "to go down (constipated stomach)",
            "okubohorrooka": "to come unfastened",
        },
    },
}

# ── Chapter 12: Derivative Verbs ─────────────────────────────────────────────

APPLIED_VERB_MEANINGS = {
    "place":        "place where action was/will be completed or motion is directed",
    "time":         "time one takes to do something or time by which one does something",
    "cause":        "cause, reason, purpose or motive",
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

DOUBLE_PREPOSITIONAL = {
    "okubohera": {
        "meaning": "to tie for",
        "extended": "okuboheerra (V.Pr.2: to fasten up for, as food for journey)",
        "double":   "okubohereerra (to tie for/fasten up for with reference to place)",
    },
    "okutemera": {
        "meaning": "to cut for",
        "extended": "okutemeerra (to cut grass with a knife)",
        "double":   "okutemereerra (to cut grass for/on behalf of one with reference to place)",
    },
}

CAUSATIVE_FORMATION = {
    "monosyllabic": {
        "rule": "add -isa to simple stem",
        "examples": {"ba": "baisa", "ha": "haisa", "ta": "taisa"},
        "exceptions": {"sa": "siisa", "fa": "fiisa"},
    },
    "verbs_in_ra": {
        "rule": "change -ra into -za",
        "examples": {"okubara": "okubaza", "okuhaarra": "okuharuza"},
    },
    "verbs_in_ta": {
        "rule": "change -ta into -sa",
        "examples": {"okucumita": "okucumisa", "okurubata": "okurubasa"},
    },
    "intransitive_verbs": {
        "rule": "replace final a by -ya",
        "examples": {"okuhaba": "okuhabya", "okwoga": "okwogya", "okwaka": "okwakya", "okubyama": "okubyamya"},
    },
}

PASSIVE_FORMATION = {
    "monosyllabic_simple": {
        "rule": "add -ibwa or -ebwa with sound change",
        "examples": {"ha": "heebwa", "ta": "teebwa", "sa": "siibwa"},
    },
    "monosyllabic_labialised": {
        "rule": "replace final vowel by -ibwa or -ebwa",
        "examples": {"cwa": "cwibwa", "lya": "liibwa"},
    },
    "other_verbs": {
        "rule": "insert w before final a",
        "examples": {"gaba": "gabwa", "diida": "diidwa", "leha": "lehwa"},
    },
}

NEUTER_FORMATION = {
    "rule_1": {
        "description": "replace final vowel by -ika, -eka, -ooka, -uuka",
        "examples": {"okwata": "okwatika", "okuewa": "okucweka", "okugoorra": "okugoorrooka", "okuhuuha": "okuhuuhuuka"},
    },
    "rule_2": {
        "description": "replace last syllable of verbs in -ra by -ka",
        "examples": {"okusobora": "okusoboka", "okutaagura": "okutaaguka", "okujumbura": "okujumbuka"},
    },
}

RECIPROCAL_FORMATION = {
    "suffix_ngana": {
        "description": "add -ngana for reciprocal action",
        "examples": {"okujuma": "okujumangana", "okuseka": "okusekangana", "okugonza": "okugonzangana"},
    },
    "suffix_na": {
        "description": "add -na for associative concept",
        "examples": {"okuganja": "okuganjana", "okuliira": "okuliirana"},
    },
}

# ── Chapter 13: Moods and Tenses ─────────────────────────────────────────────

IMPERATIVE_TENSES = {
    "present": {
        "singular":    "verb stem ending in -a (e.g. Genda 'Go!')",
        "plural":      "subjunctive form with -e (e.g. Mugende 'Go!')",
        "negative_sg": "Otagenda 'Don't go!'",
        "negative_pl": "Mutagenda 'Do not go!'",
    },
    "continuous_present": {
        "singular":    "suffix -ga (e.g. Ikarraga 'Sit for a while')",
        "plural":      "subjunctive with -ge (e.g. Mwikaarreege 'Sit for a while')",
        "negative_sg": "totemaga 'do not habitually cut'",
        "negative_pl": "timutemaga 'do not habitually cut'",
    },
    "near_future": {
        "description": "commands to be obeyed within a few hours",
        "positive":    "subjunctive form (e.g. Nyenkya oije kara 'Come early tomorrow')",
        "negative":    "present tense form (e.g. Nyenkya otaija 'Don't come tomorrow')",
    },
    "far_future": {
        "description": "commands beyond near future limit",
        "positive":    "subjunctive form (e.g. Obu olimubona omunsabire 'When you see him ask him')",
        "negative":    "inverted -ta + -li- (e.g. Obu olimubona otalimusaba 'When you see him don't ask')",
    },
    "continuous_future": {
        "description": "command to be obeyed continuously from moment of speaking",
        "positive":    "subjunctive with -ge (e.g. Otiineege so 'Fear your father')",
        "negative":    "Otalihangiirra 'Never bear false witness'",
    },
}

SUBJUNCTIVE_FUNCTIONS = {
    "purpose":    "express purpose or reason for command",
    "thought":    "express a thought or suggestion",
    "permission": "express a question of permissive nature",
    "wish":       "express wish (often with particle ka)",
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

INDICATIVE_TENSES = {
    "present_indefinite": {
        "description": "expresses customary action",
        "formation":   "no tense prefix, only pronominal prefixes/concords",
        "examples": {
            "positive": "Abahuma banywa amata (Cattle keepers drink milk)",
            "negative": "Abaana barungi tibanya maarwa (Good children do not drink beer)",
        },
    },
    "present_imperfect": {
        "description":   "action still continuing or imperfect in present time",
        "tense_prefix":  "ni- (before consonant/i), na- (before a), ne- (before e), no- (before o)",
        "negative_prefix": "ruku-",
        "examples": {
            "positive": "Engoma niigamba (Drums are sounding)",
            "negative": "Engoma tiirukugamba (Drums are not sounding)",
        },
    },
    "present_perfect": {
        "description": "action or state complete at moment of speaking",
        "formation":   "tense suffixes according to verb ending",
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

VERB_INA_CONJUGATION = {
    "present_positive": {
        "1sg": "nyina", "2sg": "oina",  "3sg": "aina",
        "1pl": "tuina", "2pl": "muina", "3pl": "baina",
    },
    "present_negative": {
        "1sg": "tiinyina", "2sg": "toina",  "3sg": "taina",
        "1pl": "titwina",  "2pl": "timwina", "3pl": "tibaina",
    },
}

VERB_LI_CONJUGATION = {
    "present_positive": {
        "1sg": "ndi",  "2sg": "oli",  "3sg": "ali",
        "1pl": "tuli", "2pl": "muli", "3pl": "bali",
    },
    "present_negative": {
        "1sg": "tindi", "2sg": "toli",  "3sg": "tali",
        "1pl": "tituli", "2pl": "timuli", "3pl": "tibali",
    },
}

# ── Chapter 7: Noun Classes extended ─────────────────────────────────────────

CLASS_12_13_14_DETAILS = {
    "class_12": {
        "prefix": "aka- (akw- before vowel)",
        "description": "diminutives (singular)",
        "examples": [
            ("akajuma", "grain, pill"), ("akanono", "tiny nail, claw"),
            ("akaara", "tiny finger, toe"), ("akanyamunkogoto", "tortoise"),
        ],
    },
    "class_13": {
        "prefix": "utu- (utw- before vowel)",
        "description": "diminutives (plural) / small quantities",
        "formation": "substituted for normal class prefixes to indicate diminution",
        "examples": [
            ("otuta", "a little milk"), ("otwarwa", "a little beer, dregs of beer"),
            ("otwizi", "a little water, a drop of water"),
        ],
        "function": "functions as plural of Class 12, though normal plural is Class 14",
    },
    "class_14": {
        "prefix": "obu- (obw- before vowel)",
        "description": "abstract nouns, mass nouns",
        "examples": [
            ("obujuma", "grains (pl. of akajuma)"), ("obunono", "tiny nails (pl. of akanono)"),
            ("obwara", "tiny fingers (pl. of akaara)"),
        ],
    },
}

AUGMENTATIVE_PEJORATIVE_EXTENDED = {
    "oru_substitution": {
        "description": "oru- substituted for normal class prefix = augmentative or pejorative",
        "examples": [
            ("orusaija", "omusaija", "man",    "clumsy/big man (pejorative)"),
            ("orukazi",  "omukazi",  "woman",  "clumsy woman"),
            ("orwisiki", "omwisiki", "girl",   "clumsy girl"),
            ("orute",    "ente",     "cow",    "clumsy cow"),
            ("oruti",    "omuti",    "tree",   "long stick"),
            ("orunyonyi","enyonyi",  "bird",   "big long bird"),
        ],
    },
    "eki_substitution": {
        "description": "eki-/eky- substituted = magnitude, affection, or contempt",
        "examples": [
            ("ekisaija", "omusaija", "man",     "that clumsy/big man (contempt)"),
            ("ekiiru",   "omwiru",   "servant", "dear poor man (affection) / sturdy peasant"),
            ("ekintu",   "okintu",   "thing",   "monster-like thing"),
        ],
    },
    "eri_substitution": {
        "description": "eri-/ery- substituted = magnitude",
        "examples": [
            ("eriiru",  "omwiru", "servant", "that sturdy peasant"),
            ("erintu",  "okintu", "thing",   "monster-like thing"),
            ("eryana",  "omwana", "child",   "insolent child"),
        ],
    },
}

CLASS6_PLURAL_RULES = {
    "ama_before_consonant_a_i": {
        "rule": "ama- before consonant and vowels a, i",
        "examples": [
            ("amabara", "ibara", "name"), ("amaato", "eryato", "boat, canoe"),
            ("amaiba", "eriiba", "dove, pigeon"),
        ],
    },
    "ame_before_e": {
        "rule": "ame- before e",
        "examples": [
            ("ameegero", "eryegero", "school"), ("ameegesezo", "eryegesezo", "classroom"),
        ],
    },
    "amo_before_o": {
        "rule": "amo- before o",
        "examples": [
            ("amoozi", "eryozi", "edible gourd"), ("amooga", "eryoga", "time of bathing"),
        ],
    },
}

CLASS6_OTHER_PLURALS = {
    "amaju":   ("enju",   "house",       "class 9"),
    "amara":   ("orura",  "intestine",   "class 11"),
    "amahyo":  ("obuhyo", "flock, herd", "class 14"),
    "amaguru": ("okuguru","leg",          "class 15"),
}

# ── Chapters 9 & 10: Noun Formation ──────────────────────────────────────────

DEVERBATIVE_SUFFIXES = {
    "-u": {
        "description": "forms nouns denoting state or noun agents",
        "examples": {
            "fu":   ("okufa",   "dead person",  "to die"),
            "kuru": ("okukura", "old person",   "to grow old"),
            "zigu": ("okuziga", "enemy",        "to track, surround in hunting"),
        },
    },
    "-zi": {
        "description": "forms noun agents (one who does the action)",
        "examples": {
            "omurozi":    ("okurora",    "looker on",          "to see"),
            "omubaizi":   ("okubaija",   "carpenter",          "to do carpentry"),
            "omusengiizi":("okusengiija","one who filters",    "to filter"),
            "omuhiizi":   ("okuhiija",   "one who pants",      "to pant"),
        },
    },
    "-gu": {"description": "forms nouns from verb roots (less common)", "examples": {}},
}

NOUN_FUNCTIONS = {
    "subject": {
        "description": "noun as subject of verb",
        "examples": [
            ("Omunyoro alina omwigo.", "The chief has a walking stick."),
            ("Omusomesa naarora engoma.", "The catechist is looking at the drum."),
        ],
    },
    "object": {
        "description": "noun as object of verb",
        "examples": [
            ("Embwa ekwasire omusu.", "The dog has killed an edible rat."),
            ("Omukazi azaire omwana.", "A woman has given birth to a child."),
        ],
    },
    "apposition": {
        "description": "noun as apposition or attribute to another noun",
        "examples": [
            ("Kiiza, omurongo, ninkuligira.", "I am in love with you Kiiza the child who comes next to twins."),
        ],
    },
}

NOUN_KINDS = {
    "proper": {
        "description": "names for individual persons, things, places, countries",
        "rule": "proper nouns begin with a capital letter",
        "examples": {
            "people":    ["Rwakaikara", "Kaikara", "Peetero", "Yohaana"],
            "places":    ["Butiiti", "Bujumbura", "Mparo", "Kyegeegwa"],
            "countries": ["Bunyoro", "Tooro", "Nkole", "Kigezi", "Rwanda"],
            "towns":     ["Kaseese", "Masindi", "Kabarole", "Hoima", "Mbarara"],
        },
    },
    "common": {
        "description": "names used for any member of a class",
        "examples": ["omuntu (person)", "ekisoro (animal, beast)", "orusozi (mountain)"],
    },
}

VERBAL_NOUNS_CLASS5 = {
    "igesa":  ("okugesa",  "harvest, reaping time",              "to reap, harvest"),
    "izaara": ("okuzaara", "time when a woman gives birth",      "to give birth, produce, bear"),
    "igenda": ("okugenda", "the going (verbal idea)",            "to go"),
    "ihiisa": ("okuhiisa", "the brewing (verbal idea)",          "to brew"),
}

# ── Chapter 4: Words, Affixes, Negation, Numbers ─────────────────────────────

NEGATION_EXTENDED = {
    "declinable": {
        "description": "built on root -aha + genitive particle; answers questions about presence",
        "examples": [
            ("Waaha, taroho.",              "No, he is not there."),
            ("Ente zaaha, tiziizire.",      "No, cows have not come."),
            ("Karamoja ebyokulya byahayo.", "There is no food in Karamoja."),
            ("Kwaha, tagenzire.",           "No, he has not gone. (blunt no, with class 15 kwa)"),
        ],
    },
    "undeclinable": {
        "A'a":        "Refrain from troubling the people, I do not want it.",
        "Nangwa":     "No, I am not going there!",
        "Nga":        "No, come here, I am not going to beat you.",
        "Naakataito": "He does not at all know how to read.",
        "Naakake":    "same use as Naakataito",
        "Busa":       "He does not know anything at all.",
        "Nangwa busa":"He has done nothing wrong.",
        "Busaho":     "No, he will not come this way.",
        "Ntai":       "God forbid, where did I meet him!",
    },
}

AFFIRMATION_WORDS = {
    "Ke":     "Yes (simple affirmation)",
    "Mi":     "Yes, you may",
    "Ego":    "Yes (formal affirmation)",
    "Nukwo":  "Yes, that's it / isn't it?",
    "Ego kwo":"Yes indeed / truly yes",
}

POSSESSIVE_PRONOUNS = {
    1:  ("wa-/waa-/w-", "-nge",  "omwana wange (my child)"),
    2:  ("ba-/baa-/b-", "-itu",  "abaana baitu (our children)"),
    3:  ("gwa-/gw-",    "-gwo",  "omutwe gwange (my head)"),
    4:  ("ya-/yaa-/y-", "-yo",   "emitaano yaitu (our boundaries)"),
    5:  ("lya-/ly-",    "-lyo",  "eryato lyange (my boat)"),
    6:  ("ga-/gaa-/g-", "-go",   "amagezi gaabo (their wisdom)"),
    7:  ("kya-/ky-",    "-kyo",  "ekitiinisa kyawe (your honour)"),
    8:  ("bya-/by-",    "-byo",  "ebitabu byanyu (your books)"),
    9:  ("ya-/yaa-/y-", "-yo",   "ente yaitu (our cow)"),
    10: ("za-/zaa-/z-", "-zo",   "ente zaitu (our cattle)"),
    11: ("rwa-/rw-",    "-rwo",  "orugoye rwe (her cloth)"),
    12: ("ka-/kaa-/k-", "-ko",   "akasozi kange (my hill)"),
    13: ("twa-/tw-",    "-two",  "otwizi twange (my little water)"),
    14: ("bwa-/bw-",    "-bwo",  "obwana bwange (my little children)"),
    15: ("kwa-/kw-",    "-kwo",  "okuguru kwange (my leg)"),
}

GENITIVE_ELISION_RULES = {
    "rule": (
        "The -a of relationship is always elided before a word beginning with a vowel. "
        "Though not written, the particle must be pronounced long."
    ),
    "contexts": [
        ("between two nouns",              "omwana wa Byaruhanga → omwana w'Omuhangi"),
        ("between noun and interrogative", "Omukazi onu w'oha? (Whose woman is this?)"),
        ("between noun and ki?",           "Ebitabu binu byaki? (For what purpose are these books?)"),
        ("between noun and ordinal",       "ekitabu ky'okubanza (the first book)"),
        ("between noun and possessive",    "omwana wange (my child)"),
    ],
    "pronunciation_note": (
        "Though -a is not written before vowels, particles must be pronounced long: "
        "aba → abaa, aga → agaa, eza → ezaa, aka → akaa"
    ),
}

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

PARTS_OF_SPEECH = {
    "nouns":        "names of things concrete or abstract (e.g. ente 'cow', amagezi 'intelligence')",
    "verbs":        "words signifying actions connected with nouns, in concordial agreement",
    "adjectives":   "words qualifying nouns, in concordial agreement (e.g. omukazi omurungi)",
    "pronouns":     "words signifying things without being their names (e.g. nyowe 'I', uwe 'he/she')",
    "numerals":     "qualify nouns in terms of quantity; 1-5 take numeral concords",
    "adverbs":      "describe verbs/adjectives re manner, place, time",
    "ideophones":   "adverbs describing intensity of manner/sound/smell/action",
    "interjections":"express pity, surprise, joy, anger etc.; no grammatical bearing on sentence",
    "joining_words":"particles expressing relation between persons/objects or joining words/phrases",
}

IDEOPHONES = {
    "cuucuucu": "intensity with smell (okununka cuucuucu)",
    "siisiisi":  "intensity with being black (okwiragura siisiisi)",
    "tiitiiti":  "intensity with being white (okwera tiitiiti)",
    "nulinuli":  "tasting very sweet (okunuliirra nulinuli)",
    "peepeepe":  "tasting very bitter (okusaarra peepeepe)",
    "begebege":  "intensity with being hot (okwokya begebege)",
    "tukutuku":  "intensity with being red (okutukura tukutuku)",
}

ORDINAL_FORMATION = {
    "first": {
        "rule": "okubanza 'to begin, come first' preceded by genitive particle",
        "examples": [
            ("omwana (o)w'okubanza",   "the first child"),
            ("abantu (a)b'okubanza",   "the first men"),
            ("ibara lye ery'okubanza", "his first name"),
            ("ekigambo (e)ky'okubanza","the first word"),
        ],
    },
    "second_to_fifth": {
        "rule": "adverbial prefix ka- + numeral stem + genitive particle",
        "examples": [
            ("omwaka (o)gwa kabiri",  "(the) second year"),
            ("ekitebe (e)kya kasatu", "(the) third class"),
            ("orukumo (o)rwa kataano","(the) fifth finger"),
        ],
    },
}

ORDINALS_EXTENDED = {
    "6th_to_10th": {
        "rule": "cardinals (without initial vowel) preceded by genitive particle",
        "examples": [
            ("ekiragiro kya mukaaga", "the sixth commandment"),
            ("omwaka gwa musanju",    "the seventh year"),
        ],
    },
    "above_10th": {
        "rule": "cardinals preceded by genitive particle; units connected by na; 2-5 take plural numeral concord",
        "examples": [
            ("okwezi kwa ikumi na kumu",       "the eleventh month"),
            ("omumwaka gwa ikumi ne'taano",    "in the fifteenth year"),
            ("omurundi ogwa nsanju na musanju","the seventy seventh time"),
        ],
    },
    "fractions": {
        "rule": "numerator first (class 7 prefix for 1, class 8 for 2-5) + genitive + denominator with ka-",
        "examples": [
            ("kimu kya kabiri",    "1/2 (one half)"),
            ("bibiri bya kataano", "2/5 (two fifths)"),
        ],
    },
}

NUMERAL_ADVERBIAL_KA = {
    "rule": "prefix ka- on numeral = how many times / nth occurrence",
    "examples": [
        ("Wakamurora kaingaha?", "How many times have you seen him?"),
        ("Yakazaara kasatu.",    "She has given birth three times."),
        ("Twakagyayo kabiri.",   "We have been there twice."),
    ],
}

NUMBER_CONNECTION = {
    "rule": "hundreds/thousands connected by 'mu' and 'na'",
    "examples": [
        ("ente bibiri mu asatu na itaano", "235 cows"),
        ("emiti rukumi bina n'ataano",     "1450 trees"),
    ],
    "note": "'mu' may be dropped in some cases",
}

# ── Orthography Rules (1995 Guide) ───────────────────────────────────────────

ORTHOGRAPHY_RULES = {
    "alphabet": {
        "vowels":     ["a", "e", "i", "o", "u"],
        "consonants": ["b", "c", "d", "f", "g", "h", "j", "k", "l", "m",
                       "n", "p", "r", "s", "t", "v", "w", "y", "z"],
        "note": "19 consonants total; q, v, x absent from native vocabulary",
    },
    "rule_c":  "c shall always be used without h (e.g. icumu 'spear', omuceeri 'rice')",
    "rule_l": {
        "use_l_before": ["ya", "ye", "yo", "-e", "-i (unless e or i precedes)"],
        "examples_l":   ["okulya (to eat)", "okuleka (to leave)", "okulima (to cultivate)"],
    },
    "rule_r":          "r used in all cases where l is not used",
    "double_consonants": {
        "b_doubled": "indicates non-bilabial fricative b (e.g. ibbango 'hump')",
        "m_doubled": "used in nasal compounds (e.g. emmango 'shafts of spears')",
        "n_doubled": "used in nasal compounds before nasals",
    },
    "long_vowels": "doubled vowel indicates long vowel (e.g. aa, ee, ii, oo, uu)",
    "apostrophe":  "marks elision of initial vowel in fast speech (e.g. n'ente, z'ente)",
    "source":      "Ministry of Gender and Community Development, Uganda, 1st Edition 1995",
}

# ── Utility functions (previously in extension) ───────────────────────────────

def get_derivative_verb_type(verb: str) -> str | None:
    """Identify derivative verb type based on suffix."""
    v = verb.lower().strip()
    if v.endswith(("ira", "era")):
        return "applied/prepositional"
    if v.endswith(("isa", "esa", "ya")):
        return "causative"
    if v.endswith(("ibwa", "ebwa", "wa")):
        return "passive"
    if v.endswith(("ika", "eka", "oka", "uka")):
        return "neuter/stative"
    if v.endswith(("ura", "ora", "uurra", "oorra")):
        return "conversive/reversive"
    if v.endswith(("ngana", "na")):
        return "reciprocal/associative"
    return None


def get_imperative_form(verb_stem: str, number: str = "singular", tense: str = "present") -> str:
    """Generate imperative form for a verb stem."""
    if tense == "present":
        if number == "singular":
            return verb_stem
        return "mu" + verb_stem[:-1] + "e"
    if tense == "continuous_present":
        if number == "singular":
            return verb_stem[:-1] + "ga"
        return "mw" + verb_stem[:-1] + "eege"
    return verb_stem


def is_reflexive_verb(verb: str) -> bool:
    """Return True if verb is reflexive (starts with okw-e)."""
    v = verb.lower().strip()
    return v.startswith("okwe") or v.startswith("okw-e")


def get_full_grammar_context() -> str:
    """
    Complete grammar context including all OCR-derived rules.
    Used by the chat endpoint system prompt.
    """
    base = get_extended_grammar_context()
    additional = (
        "\n--- Additional OCR Grammar Rules ---\n"
        "DERIVATIVE VERBS:\n"
        "  Applied/Prepositional (-ira/-era): action done for/at/with reference to place/time/cause\n"
        "    e.g. okubohera (tie cow's legs when milking), okutemera (plant beans with hoe)\n"
        "  Causative (-isa/-esa/-ya): cause action to happen\n"
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


# ═══════════════════════════════════════════════════════════════════════════════
# GRAMMAR RULES 4 — Pronominal System, Copula, Particles, Relatives, Genitives,
#                   Numbers (extended), Ordinals, Fractions, Suffixes
# ═══════════════════════════════════════════════════════════════════════════════

# ── Self-standing pronouns ────────────────────────────────────────────────────
SELF_STANDING_PRONOUNS = {
    "1sg": "nyowe",   # I / me
    "2sg": "iwe",     # you (sg)
    "3sg": "uwe",     # he / she / him / her
    "1pl": "itwe",    # we / us
    "2pl": "inywe",   # you (pl)
    "3pl": "bo",      # they / them
    # class-based (classes 3-15)
    3:  "gwo",  4:  "yo",  5:  "lyo",  6:  "go",
    7:  "kyo",  8:  "byo", 9:  "yo",   10: "zo",
    11: "rwo",  12: "ko",  13: "two",  14: "bwo", 15: "kwo",
}

# ── Pronominal concords (subject) ─────────────────────────────────────────────
SUBJECT_PRONOMINAL_CONCORDS = {
    1:  "a-",   2:  "ba-",  3:  "gu-",  4:  "e-",
    5:  "li-",  6:  "ga-",  7:  "ki-",  8:  "bi-",
    9:  "e-",   10: "zi-",  11: "ru-",  12: "ka-",
    13: "tu-",  14: "bu-",  15: "ku-",
}

# ── Pronominal concords (object) ──────────────────────────────────────────────
OBJECT_PRONOMINAL_CONCORDS = {
    1:  "-mu-",  2:  "-ba-",  3:  "-gu-",  4:  "-gi-",
    5:  "-li-",  6:  "-ga-",  7:  "-ki-",  8:  "-bi-",
    9:  "-gi-",  10: "-zi-",  11: "-ru-",  12: "-ka-",
    13: "-tu-",  14: "-bu-",  15: "-ku-",
}

# ── Subject relative concords ─────────────────────────────────────────────────
SUBJECT_RELATIVE_CONCORDS = {
    1:  "a-",    2:  "aba-",  3:  "ogu-",  4:  "e-",
    5:  "eri-",  6:  "aga-",  7:  "eki-",  8:  "ebi-",
    9:  "e-",    10: "ezi-",  11: "eru-",  12: "aka-",
    13: "otu-",  14: "obu-",  15: "oku-",
}

# ── Object relative concords ──────────────────────────────────────────────────
OBJECT_RELATIVE_CONCORDS = {
    1:  "ou",   2:  "aba",  3:  "ogu",  4:  "ei",
    5:  "eri",  6:  "aga",  7:  "eki",  8:  "ebi",
    9:  "ei",   10: "ezi",  11: "oru",  12: "aka",
    13: "otu",  14: "obu",  15: "oku",
}

# ── Demonstratives for things in mind (near/mentioned) ───────────────────────
DEMONSTRATIVES_IN_MIND = {
    1:  "ogu",  2:  "abo",  3:  "ogu",  4:  "egi",
    5:  "eri",  6:  "ago",  7:  "eki",  8:  "egi",
    9:  "egi",  10: "ezi",  11: "oru",  12: "ako",
    13: "otu",  14: "obu",  15: "oku",
}

# ── Demonstratives: -nu (near speaker) and -li (far from speaker) ─────────────
DEMONSTRATIVES_NEAR = {   # built on root -nu
    1:  "onu",   2:  "banu",  3:  "gunu",  4:  "enu",
    5:  "linu",  6:  "ganu",  7:  "kinu",  8:  "binu",
    9:  "enu",   10: "zinu",  11: "runu",  12: "kanu",
    13: "tunu",  14: "bunu",  15: "kunu",
}

DEMONSTRATIVES_FAR = {    # built on root -li
    1:  "oli",   2:  "bali",  3:  "guli",  4:  "eri",
    5:  "liri",  6:  "gali",  7:  "kiri",  8:  "biri",
    9:  "eri",   10: "ziri",  11: "ruli",  12: "kali",
    13: "tuli",  14: "buli",  15: "kuli",
}

# ── Genitive particles (object relative concord + -a of relationship) ─────────
GENITIVE_PARTICLES_FULL = {
    1:  "owa",   2:  "aba",   3:  "ogwa",  4:  "eya",
    5:  "erya",  6:  "aga",   7:  "ekya",  8:  "ebya",
    9:  "eya",   10: "eza",   11: "orwa",  12: "aka",
    13: "otwa",  14: "obwa",  15: "okwa",
}

# Short forms (drop initial vowel between two nouns)
GENITIVE_PARTICLES_SHORT = {
    1:  "wa-",   2:  "ba-",   3:  "gwa-",  4:  "ya-",
    5:  "lya-",  6:  "ga-",   7:  "kya-",  8:  "bya-",
    9:  "ya-",   10: "za-",   11: "rwa-",  12: "ka-",
    13: "twa-",  14: "bwa-",  15: "kwa-",
}

# ── Possessive pronoun suffixes (combined with genitive particle) ─────────────
POSSESSIVE_SUFFIXES = {
    "1sg": "-nge",   # my
    "2sg": "-we",    # your (sg)
    "3sg": "-e",     # his/her/its
    "1pl": "-itu",   # our
    "2pl": "-nyu",   # your (pl)
    "3pl": "-bo",    # their
}

# ── Copula particles ──────────────────────────────────────────────────────────
COPULA_NI = {
    # ni- + self-standing pronouns
    "1sg": "niinyowe",  "2sg": "niiwe",   "3sg": "nuwe",
    "1pl": "niitwe",    "2pl": "niinywe", "3pl": "nubo",
    # ni- + demonstratives (near)
    "near_1":  "noonu",  "near_far_1": "nooli",  "near_mind_1": "noogu",
    "near_2":  "nibanu", "far_2":      "nibali",  "mind_2":      "naabo",
}

COPULA_N = {
    # n- + demonstratives near (-nu root)
    1:  "ngunu",  2:  "mbanu",  3:  "ngunu",  4:  "nginu",
    5:  "ndinu",  6:  "nganu",  7:  "nkinu",  8:  "mbinu",
    9:  "nginu",  10: "nzinu",  11: "ndunu",  12: "nkanu",
    13: "ntunu",  14: "mbunu",  15: "nkunu",
}

COPULA_N_FAR = {
    # n- + demonstratives far (-li root)
    1:  "nguli",  2:  "mbali",  3:  "nguli",  4:  "ngiri",
    5:  "ndiri",  6:  "ngali",  7:  "nkiri",  8:  "mbiri",
    9:  "ngiri",  10: "nziri",  11: "nduli",  12: "nkali",
    13: "ntuli",  14: "mbuli",  15: "nkuli",
}

# ── Particle KA (emphatic / permissive) ───────────────────────────────────────
PARTICLE_KA_EXAMPLES = {
    "emphatic_noun":    "ka muntu — the very person",
    "emphatic_adj":     "ka murungi — a really good one",
    "emphatic_pronoun": "ka niiwe — it's really you",
    "emphatic_poss":    "ka wange — it's really my relative",
    "emphatic_dem":     "ka ngunu — here he/she truly is",
    "permissive":       "ka tugende — let's go (shortened from leka tugende)",
}

# ── Joining word NA ───────────────────────────────────────────────────────────
NA_WITH_PRONOUNS = {
    "1sg": "na nyowe",   "2sg": "na iwe",   "3sg": "na uwe",
    "1pl": "na itwe",    "2pl": "na inywe",  "3pl": "na bo",
}

NA_WITH_DEMONSTRATIVES = {
    "near_1":  "n'onu",   "far_1":  "n'oli",   "mind_1": "n'ogu",
    "near_2":  "na banu", "far_2":  "na bali",  "mind_2": "n'abo",
}

# ── DARA (presentative/locative particle) ────────────────────────────────────
DARA_WITH_PRONOUNS = {
    "1sg": "daranyowe",  # here I am
    "3sg": "darawe",     # here he/she is
    "1pl": "daraitwe",   # here we are
    "3pl": "darabo",     # here they are
    3:  "daragwo",  4:  "darayo",  5:  "daralyo",  6:  "darago",
    7:  "darakyo",  8:  "darabyo", 9:  "darayo",   10: "darazo",
    11: "dararwo",  12: "darako",  13: "daratwo",  14: "darabwo", 15: "darakwo",
}

DARA_WITH_NEAR_DEMONSTRATIVES = {
    1:  "daroonu",  2:  "darabanu",  3:  "daragunu",  4:  "daleenu",
    5:  "daralinu", 6:  "daraganu",  7:  "darakinu",  8:  "darabinu",
    9:  "daleenu",  10: "darazinu",  11: "dararunu",  12: "darakanu",
    13: "daratunu", 14: "darabunu",  15: "darakunu",
}

# ── Modal particles -ta and -ti ───────────────────────────────────────────────
MODAL_PARTICLE_TA_EXAMPLES = [
    ("Oraire ota?",          "Good morning / How have you slept?"),
    ("Oroho ota?",           "How are you?"),
    ("Ndooho nti!",          "I am fine! (I am like that)"),
    ("Abakazi balima bata?", "How do women dig?"),
    ("Balima bati:",         "They dig like this (show action)"),
    ("Ente zijuga zita?",    "How do cows moo?"),
    ("Zijuga ziti:",         "They moo like this"),
]

MODAL_PARTICLE_TI_EXAMPLES = [
    ("Tukabagambira tuti, 'Na itwe tuli bantu nka inywe.'",
     "We told them, 'We are also human beings like yourselves.'"),
    ("Mukatugira muti, 'Obu aliija mulituha ente.'",
     "You said to us, 'If he comes you will give us a cow.'"),
]

# ── Names of relationship ─────────────────────────────────────────────────────
NAMES_OF_RELATIONSHIP = {
    "father":           {"3sg": "ise",       "1pl": "ise",       "2pl": "ise",       "3pl": "ise"},
    "mother":           {"3sg": "nyina",     "1pl": "nyinen",    "2pl": "nyina",     "3pl": "nyina"},
    "grandfather":      {"3sg": "isenkuru",  "1pl": "isenkuru",  "2pl": "isenkuru",  "3pl": "isenkuru"},
    "grandmother":      {"3sg": "nyinenkuru","1pl": "nyinenkuru","2pl": "nyinenkuru","3pl": "nyinenkuru"},
    "paternal_aunt":    {"3sg": "isenkati",  "1pl": "isenkati",  "2pl": "isenkati",  "3pl": "isenkati"},
    "maternal_aunt":    {"3sg": "nyinento",  "1pl": "nyinento",  "2pl": "nyinento",  "3pl": "nyinento"},
    "maternal_uncle":   {"3sg": "nyinarumi", "1pl": "nyinarumi", "2pl": "nyinarumi", "3pl": "nyinarumi"},
    "paternal_uncle":   {"3sg": "isento",    "1pl": "isento",    "2pl": "isento",    "3pl": "isento"},
    "father_in_law":    {"3sg": "isezaara"},
    "mother_in_law":    {"3sg": "nyinazaara"},
    "husband":          {"3sg": "iba"},
}

# Combined forms (ise + itwe → isiitwe, isenkuru + itwe → isenkurwitwe)
RELATIONSHIP_COMBINED = {
    "isiitwe":       "our father",
    "isiinywe":      "your father",
    "isenkurwitwe":  "our grandfather",
    "isenkurwinywe": "your grandfather",
}

# ── Extended cardinal numbers (6-1,000,000) ───────────────────────────────────
CARDINALS_EXTENDED = {
    6:       "mukaaga",
    7:       "musanju",
    8:       "munaana",
    9:       "mwenda",
    10:      "ikumi",       # class 5 noun
    20:      "makumi abiri",
    30:      "makumi asatu",
    40:      "makumi ana",
    50:      "makumi ataano",
    60:      "nsanju",      # class 9 prefix
    70:      "nsanju",      # (e)nsanju
    80:      "kinaana",     # class 7
    90:      "kyenda",      # class 7
    100:     "kikumi",      # class 7
    200:     "ebikumi bibiri",
    300:     "ebikumi bisatu",
    400:     "ebikumi bina",
    500:     "ebikumi bitaano",
    600:     "rukaaga",     # class 11
    700:     "rusanju",
    800:     "runaana",
    900:     "rwenda",
    1000:    "rukumi rumu",  # class 11
    2000:    "enkumi ibiri", # class 10
    6000:    "akakaaga",    # class 13
    7000:    "akasanju",
    8000:    "akanaana",
    9000:    "akenda",
    10000:   "omutwaro gumu",  # class 3, or akakumi kamu (class 13)
    100000:  "emitwaro kikumi",
    1000000: "akakaikuru kamu",
}

# Adverbial number prefixes (how many times)
ADVERBIAL_NUMBER_PREFIX = {
    1: "dimu",     # once
    2: "kabiri",   # twice
    3: "kasatu",   # three times
    4: "kana",     # four times
    5: "kataano",  # five times
}

# ── Ordinal formation rules ───────────────────────────────────────────────────
ORDINAL_RULES = {
    "1st":  "genitive_particle + okubanza  (e.g. omwana w'okubanza = first child)",
    "2nd":  "genitive_particle + kabiri    (e.g. omwaka gwa kabiri = second year)",
    "3rd":  "genitive_particle + kasatu    (e.g. ekitebe kya kasatu = third class)",
    "4th":  "genitive_particle + kana",
    "5th":  "genitive_particle + kataano   (e.g. orukumo rwa kataano = fifth finger)",
    "6th":  "genitive_particle + mukaaga   (e.g. ekiragiro kya mukaaga = sixth commandment)",
    "7th":  "genitive_particle + musanju   (e.g. omwaka gwa musanju = seventh year)",
    "8th":  "genitive_particle + munaana",
    "9th":  "genitive_particle + mwenda",
    "10th": "genitive_particle + ikumi",
    "11th+": "genitive_particle + cardinal (units joined by na, e.g. okwezi kwa ikumi na kumu = 11th month)",
}

# ── Fraction formation ────────────────────────────────────────────────────────
FRACTION_RULES = {
    "numerator_first": {
        "description": "numerator (class 7 for 1, class 8 for 2-5) + genitive + ka- + denominator",
        "examples": {
            "1/2": "kimu kya kabiri",
            "2/5": "bibiri bya kataano",
        }
    },
    "denominator_first": {
        "description": "denominator with ka- + class 7/8 genitive + numerator",
        "examples": {
            "1/2": "ekyakabiri kimu",
            "2/5": "ebyakataano bibiri",
            "6/7": "ebyamukaaga musanju",
        }
    },
}

# ── Distributive numbers ──────────────────────────────────────────────────────
DISTRIBUTIVE_EXAMPLES = [
    ("Abantu bazina babiri babiri.",
     "People dance two by two."),
    ("Habisoro byona ebisemiire olitwara musanju musanju.",
     "Of all the clean beasts you will take seven and seven."),
    ("Buli bantu basatu bahimbe orubbaaho rumu.",
     "Let every three persons carry one bench."),
]

# ── Noun suffix alternation ───────────────────────────────────────────────────
NOUN_SUFFIX_ALTERNATION = {
    "-a":  "infinitive / basic verb form (okulima = to dig)",
    "-ira/-era": "applied/prepositional — action for/at/with reference to (limira = dig for)",
    "-isa/-esa": "causative — cause action (limisa = cause to dig / dig with)",
    "-i":  "agent noun (omulimi = cultivator, from -lim-)",
    "-o":  "action noun (omulimo = work/digging, from -lim-)",
    "-a (noun)": "professional/habitual agent (omulima = professional digger)",
    "en- + root + -a": "method noun (endima = method of digging)",
}

VERB_DERIVED_NOUN_EXAMPLES = {
    "okulima":   {"agent": "omulimi (cultivator)", "action": "omulimo (work)", "method": "endima (method of digging)"},
    "okuzaana":  {"agent": "omuzaani (player)",    "action": "omuzaano (play)", "method": "enzaana (method of playing)",
                  "servant": "omuzaana (maid servant)"},
}

# ── Interrogative roots ───────────────────────────────────────────────────────
INTERROGATIVE_ROOTS = {
    "-ha?": {
        "description": "Who? / Which? — takes subject pronominal concords",
        "examples": [
            ("Noogonza oha?",  "Whom do you want?"),
            ("Abaantu baha?",  "Which people?"),
            ("Niiwe oha?",     "Who are you?"),
        ]
    },
    "-ki?": {
        "description": "What? / Which? — takes adjectival concords (irregular)",
        "examples": [
            ("Omutooro muki?", "What kind of Mutooro person?"),
            ("Gunu muki?",     "What is this? (class 4 noun)"),
            ("Muti ki?",       "Which tree?"),
            ("Ogambire ki?",   "What have you said?"),
        ]
    },
}

# ── Enumerative roots ─────────────────────────────────────────────────────────
ENUMERATIVE_ROOTS = {
    "-enka / -onka": "alone, only, self (exclusive): nyenka = I alone, bonka = they only",
    "-ena / -ona":   "all, inclusive: nyeena = all of myself, boona = all of them",
    "-enyini / -onyini": "self, selves (selective): nyeenyini = I myself, boonyini = they themselves",
    "-embi / -ombi": "both (plural only): itwembi = both of us, bombi = both of them",
    "-ndi":          "other: orundi = another, abandi = others",
    "-mu":           "some/one: ente emu = one cow, ezimu = some (cattle)",
}


# ── Helper functions ──────────────────────────────────────────────────────────

def get_subject_relative_concord(noun_class: int) -> str:
    """Return the subject relative concord for a given noun class."""
    return SUBJECT_RELATIVE_CONCORDS.get(noun_class, "")


def get_object_relative_concord(noun_class: int) -> str:
    """Return the object relative concord for a given noun class."""
    return OBJECT_RELATIVE_CONCORDS.get(noun_class, "")


def get_genitive_particle(noun_class: int, emphatic: bool = False) -> str:
    """
    Return the genitive particle for a noun class.
    emphatic=True returns the full form (with initial vowel).
    emphatic=False returns the short form (drops initial vowel between nouns).
    """
    if emphatic:
        return GENITIVE_PARTICLES_FULL.get(noun_class, "")
    return GENITIVE_PARTICLES_SHORT.get(noun_class, "")


def build_possessive(noun_class: int, person: str) -> str:
    """
    Build a possessive phrase: genitive particle + possessive suffix.
    person: '1sg','2sg','3sg','1pl','2pl','3pl'
    e.g. build_possessive(1, '1sg') → 'wange' (my, for class 1 noun)
    """
    gp = GENITIVE_PARTICLES_SHORT.get(noun_class, "")
    ps = POSSESSIVE_SUFFIXES.get(person, "")
    if not gp or not ps:
        return ""
    # Strip trailing dash from genitive particle, append suffix (drop leading dash)
    return gp.rstrip("-") + ps.lstrip("-")


def apply_copula_ni(word: str) -> str:
    """
    Prepend the copula ni- to a word, applying sound change before vowels
    (ni + vowel → n + vowel, e.g. ni + onu → noonu).
    """
    if not word:
        return word
    if word[0] in "aeiouAEIOU":
        return "n" + word
    return "ni" + word


def apply_joining_na(word: str) -> str:
    """
    Prepend the joining word na to a word, applying elision before vowels
    (na + vowel → n' + vowel).
    """
    if not word:
        return word
    if word[0] in "aeiouAEIOU":
        return "n'" + word
    return "na " + word


def build_ordinal_extended(n: int, noun_class: int) -> str:
    """
    Build an ordinal number phrase for n >= 1 with the given noun class.
    Returns a string like 'gwa kabiri' or 'w'okubanza'.
    """
    gp = get_genitive_particle(noun_class, emphatic=False).rstrip("-")
    if n == 1:
        # genitive particle + elision before okubanza (wa → w'okubanza, gwa → gw'okubanza)
        if gp.endswith("a"):
            return f"{gp[:-1]}'okubanza"
        return f"{gp}w'okubanza"
    stems = {
        1: "kumu",
        2: "kabiri", 3: "kasatu", 4: "kana", 5: "kataano",
        6: "mukaaga", 7: "musanju", 8: "munaana", 9: "mwenda", 10: "ikumi",
    }
    if n in stems:
        stem = stems[n]
        # apply elision: if gp ends in vowel and stem starts with vowel
        if gp and gp[-1] in "aeiou" and stem[0] in "aeiou":
            return f"{gp[:-1]}'{stem}"
        return f"{gp} {stem}"
    # n > 10: cardinal with na
    tens = (n // 10) * 10
    units = n % 10
    tens_word = CARDINALS_EXTENDED.get(tens, str(tens))
    if units == 0:
        return f"{gp} {tens_word}"
    units_word = stems.get(units, str(units))
    return f"{gp} {tens_word} na {units_word}"


def build_fraction(numerator: int, denominator: int, numerator_first: bool = True) -> str:
    """
    Build a fraction expression.
    numerator_first=True: kimu kya kabiri (1/2)
    numerator_first=False: ekyakabiri kimu (1/2)
    """
    denom_stems = {2: "kabiri", 3: "kasatu", 4: "kana", 5: "kataano",
                   6: "mukaaga", 7: "musanju", 8: "munaana", 9: "mwenda", 10: "ikumi"}
    num_stems   = {1: "kimu", 2: "bibiri", 3: "bisatu", 4: "bina", 5: "bitaano"}

    d_stem = denom_stems.get(denominator, str(denominator))
    n_stem = num_stems.get(numerator, str(numerator))
    # class 7 genitive for numerator=1, class 8 for 2-5
    gp_num = "kya" if numerator == 1 else "bya"
    gp_den = "ekya" if numerator == 1 else "ebya"

    if numerator_first:
        return f"{n_stem} {gp_num} {d_stem}"
    else:
        return f"{gp_den}{d_stem} {n_stem}"


def get_demonstrative(noun_class: int, proximity: str = "near") -> str:  # type: ignore[override]
    """
    Return demonstrative for a noun class.
    proximity: 'near' (-nu root), 'far' (-li root), 'mind' (things in mind)
    """
    if proximity == "near":
        return DEMONSTRATIVES_NEAR.get(noun_class, "")
    elif proximity == "far":
        return DEMONSTRATIVES_FAR.get(noun_class, "")
    else:
        return DEMONSTRATIVES_IN_MIND.get(noun_class, "")


def get_relationship_name(relation: str, person: str = "3sg") -> str:
    """
    Return the name of relationship for a given relation and person.
    relation: 'father','mother','grandfather','grandmother', etc.
    person: '3sg','1pl','2pl','3pl'
    """
    rel = NAMES_OF_RELATIONSHIP.get(relation, {})
    return rel.get(person, rel.get("3sg", ""))
