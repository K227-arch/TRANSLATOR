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

def apply_rl_rule_to_text(text: str) -> str:
    """Apply the R/L rule to every word in a sentence."""
    if not text:
        return text
    return ' '.join(apply_rl_rule(w) for w in text.split(' '))


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

_VOWELS = set("aeiouAEIOU")

def apply_apostrophe_elision(text: str) -> str:
    """
    Apply vowel elision with apostrophe for Runyoro-Rutooro particles
    before vowel-initial words.

    e.g.  "na ente"   → "n'ente"
          "za ente"   → "z'ente"
          "na omuntu" → "n'omuntu"

    Only applies when the following word starts with a vowel.
    Source: Runyoro-Rutooro Orthography Guide (1995)
    """
    if not text:
        return text
    import re as _re
    result = text
    for full, elided in _ELISION_PARTICLES:
        # Match particle followed by a vowel-initial word (word boundary aware)
        # e.g. "na ente" but not "na kazi" (k is not a vowel)
        pattern = _re.compile(
            r'\b' + _re.escape(full.strip()) + r'\s+(?=[aeiouAEIOU])',
            _re.IGNORECASE
        )
        result = pattern.sub(elided, result)
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
# IMPORT EXTENDED OCR RULES
# ─────────────────────────────────────────────────────────────────────────────

# Import extended OCR rules from separate module
try:
    from language_rules_ocr_extension import (
        # Ch.2 Sound Change
        Y_INSERTION_EXAMPLES,
        Y_INSERTION_COUNTEREXAMPLES,
        Y_INSERTION_I_STEMS,
        REFLEXIVE_IMPERATIVES,
        REFLEXIVE_NON_REFLEXIVE,
        CONVERSIVE_EXAMPLES,
        # Ch.12 Derivative Verbs
        APPLIED_VERB_MEANINGS,
        APPLIED_VERB_EXAMPLES,
        PREPOSITIONAL_NEW_MEANINGS,
        DOUBLE_PREPOSITIONAL,
        CAUSATIVE_FORMATION,
        PASSIVE_FORMATION,
        NEUTER_FORMATION,
        RECIPROCAL_FORMATION,
        # Ch.13 Moods & Tenses
        IMPERATIVE_TENSES,
        SUBJUNCTIVE_FUNCTIONS,
        SUBJUNCTIVE_EXAMPLES,
        INDICATIVE_TENSES,
        VERB_INA_CONJUGATION,
        VERB_LI_CONJUGATION,
        # Ch.7 Noun Classes
        CLASS_12_13_14_DETAILS,
        AUGMENTATIVE_PEJORATIVE_EXTENDED,
        CLASS6_PLURAL_RULES,
        CLASS6_OTHER_PLURALS,
        # Ch.9/10 Noun Formation
        DEVERBATIVE_SUFFIXES,
        NOUN_FUNCTIONS,
        NOUN_KINDS,
        VERBAL_NOUNS_CLASS5,
        # Ch.4 Words, Affixes, Numbers
        NEGATION_EXTENDED,
        AFFIRMATION_WORDS,
        POSSESSIVE_PRONOUNS,
        GENITIVE_ELISION_RULES,
        INTERROGATIVE_PARTICLES,
        PARTS_OF_SPEECH,
        IDEOPHONES,
        ORDINAL_FORMATION,
        ORDINALS_EXTENDED,
        NUMERAL_ADVERBIAL_KA,
        NUMBER_CONNECTION,
        # Orthography
        ORTHOGRAPHY_RULES,
        # Utility functions
        get_derivative_verb_type,
        get_imperative_form,
        is_reflexive_verb,
        get_full_grammar_context,
    )
except ImportError:
    # Fallback if extension module not available
    pass

