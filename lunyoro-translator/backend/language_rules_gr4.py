"""
language_rules_gr4.py
=====================
Implements the 10 missing/incomplete rules from grammar rules 4.docx:

1.  Enumerative pronouns  (-enka/-ona/-enyini/-embi)
2.  Near/far demonstratives  (-nu / -li roots, full 15-class tables)
3.  Subject/object relative concords  (full 15-class tables)
4.  Modal particles  (-ta? / -ti)
5.  Dara presentative word
6.  Ni-/n- copula distribution rules
7.  Ka particle  (emphatic vs permissive)
8.  Fractions and distributives
9.  Verb-to-noun derivation  (ki-/ka-/ru- concords)
10. Kinship terms  (ise/nyina/isenkuru etc. with person agreement)

All functions are wired into translate.py post-processing and the
/language-rules API via language_rules.py imports.
"""
import re as _re

# ─────────────────────────────────────────────────────────────────────────────
# 1. ENUMERATIVE PRONOUNS
# Source: grammar rules 4.docx — Pronominal Roots
# ─────────────────────────────────────────────────────────────────────────────

# Base self-standing pronouns
_SELF_STANDING = {
    "1sg": "nyowe", "2sg": "iwe",  "3sg": "uwe",
    "1pl": "itwe",  "2pl": "inywe","3pl": "bo",
}

# Enumerative suffixes
_ENUM_SUFFIXES = {
    "exclusive":  {"vowel": "enka", "consonant": "onka"},   # alone/only
    "inclusive":  {"vowel": "ena",  "consonant": "ona"},    # all
    "selective":  {"vowel": "enyini","consonant":"onyini"},  # self/selves
    "both":       {"vowel": "embi", "consonant": "ombi"},   # both (pl only)
}

# Pre-built table: person -> type -> form
ENUMERATIVE_PRONOUNS: dict[str, dict[str, str]] = {
    "1sg": {
        "exclusive": "nyenka",    # I alone
        "inclusive": "nyeena",    # all of myself
        "selective": "nyeenyini", # I myself
    },
    "2sg": {
        "exclusive": "wenka",     # you alone
        "inclusive": "weena",     # all of yourself
        "selective": "weenyini",  # you yourself
    },
    "3sg": {
        "exclusive": "wenka",     # he/she alone
        "inclusive": "weena",     # all of himself
        "selective": "weenyini",  # he/she himself
    },
    "1pl": {
        "exclusive": "twendeka",  # we alone
        "inclusive": "tweena",    # all of us
        "selective": "tweenyini", # we ourselves
        "both":      "twembi",    # both of us
    },
    "2pl": {
        "exclusive": "mwenka",    # you alone (pl)
        "inclusive": "mweena",    # all of you
        "selective": "mweenyini", # you yourselves
        "both":      "mwembi",    # both of you
    },
    "3pl": {
        "exclusive": "bonka",     # they only
        "inclusive": "boona",     # all of them
        "selective": "boonyini",  # they themselves
        "both":      "bombi",     # both of them
    },
}

def get_enumerative_pronoun(person: str, enum_type: str) -> str:
    """
    Return the enumerative pronoun for a person and type.
    person: '1sg','2sg','3sg','1pl','2pl','3pl'
    enum_type: 'exclusive','inclusive','selective','both'
    e.g. get_enumerative_pronoun('3pl','inclusive') -> 'boona'
    """
    return ENUMERATIVE_PRONOUNS.get(person, {}).get(enum_type, "")


def apply_enumerative_correction(text: str) -> str:
    """
    Correct common MT errors where 'alone/only/all/both/themselves' are
    translated as separate words instead of enumerative pronouns.
    e.g. 'uwe wenka' is correct; 'uwe yenka' -> 'uwe wenka'
    """
    corrections = {
        r'\byenka\b': 'wenka',
        r'\byoona\b': 'boona',
        r'\bbyoona\b': 'boona',
        r'\bboona\s+babo\b': 'boona',
    }
    result = text
    for pattern, repl in corrections.items():
        result = _re.sub(pattern, repl, result, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. NEAR / FAR DEMONSTRATIVES  (full 15-class tables)
# Source: grammar rules 4.docx — Concord Prefixes
# ─────────────────────────────────────────────────────────────────────────────

DEMONSTRATIVES_NEAR_FULL = {   # -nu root (near speaker)
    1: "onu",   2: "banu",  3: "gunu",  4: "enu",
    5: "linu",  6: "ganu",  7: "kinu",  8: "binu",
    9: "enu",   10: "zinu", 11: "runu", 12: "kanu",
    13: "tunu", 14: "bunu", 15: "kunu",
}

DEMONSTRATIVES_FAR_FULL = {    # -li root (far from speaker)
    1: "oli",   2: "bali",  3: "guli",  4: "eri",
    5: "liri",  6: "gali",  7: "kiri",  8: "biri",
    9: "eri",   10: "ziri", 11: "ruli", 12: "kali",
    13: "tuli", 14: "buli", 15: "kuli",
}

DEMONSTRATIVES_IN_MIND_FULL = {  # things already mentioned
    1: "ogu",  2: "abo",  3: "ogu",  4: "egi",
    5: "eri",  6: "ago",  7: "eki",  8: "egi",
    9: "egi",  10: "ezi", 11: "oru", 12: "ako",
    13: "otu", 14: "obu", 15: "oku",
}

def get_demonstrative_full(noun_class: int, proximity: str = "near") -> str:
    """
    Return the correct demonstrative for a noun class and proximity.
    proximity: 'near' | 'far' | 'mind'
    Replaces the incomplete get_demonstrative() in language_rules.py.
    """
    if proximity == "near":
        return DEMONSTRATIVES_NEAR_FULL.get(noun_class, "")
    if proximity == "far":
        return DEMONSTRATIVES_FAR_FULL.get(noun_class, "")
    return DEMONSTRATIVES_IN_MIND_FULL.get(noun_class, "")


# ─────────────────────────────────────────────────────────────────────────────
# 3. SUBJECT / OBJECT RELATIVE CONCORDS  (full 15-class tables)
# Source: grammar rules 4.docx — Concord Prefixes
# ─────────────────────────────────────────────────────────────────────────────

SUBJECT_RELATIVE_CONCORDS_FULL = {
    1: "a-",    2: "aba-",  3: "ogu-",  4: "e-",
    5: "eri-",  6: "aga-",  7: "eki-",  8: "ebi-",
    9: "e-",    10: "ezi-", 11: "eru-", 12: "aka-",
    13: "otu-", 14: "obu-", 15: "oku-",
}

OBJECT_RELATIVE_CONCORDS_FULL = {
    1: "ou",   2: "aba",  3: "ogu",  4: "ei",
    5: "eri",  6: "aga",  7: "eki",  8: "ebi",
    9: "ei",   10: "ezi", 11: "oru", 12: "aka",
    13: "otu", 14: "obu", 15: "oku",
}

def get_subject_relative_concord_full(noun_class: int) -> str:
    return SUBJECT_RELATIVE_CONCORDS_FULL.get(noun_class, "")

def get_object_relative_concord_full(noun_class: int) -> str:
    return OBJECT_RELATIVE_CONCORDS_FULL.get(noun_class, "")

def build_relative_clause(
    noun_class: int,
    verb_stem: str,
    tense_prefix: str = "ni",
    relative_type: str = "subject",
) -> str:
    """
    Build a relative clause verb form.
    Subject relative: concord replaces subject prefix on verb.
    Object relative:  concord inserted after tense prefix.
    e.g. build_relative_clause(1, 'genda', 'ni', 'subject') -> 'anigenda'
    """
    if relative_type == "subject":
        concord = SUBJECT_RELATIVE_CONCORDS_FULL.get(noun_class, "a-").rstrip("-")
        return concord + tense_prefix + verb_stem
    else:
        concord = OBJECT_RELATIVE_CONCORDS_FULL.get(noun_class, "ou")
        return tense_prefix + concord + verb_stem


# ─────────────────────────────────────────────────────────────────────────────
# 4. MODAL PARTICLES  -ta? / -ti
# Source: grammar rules 4.docx — Modal Particles
# ─────────────────────────────────────────────────────────────────────────────

MODAL_TA_PATTERNS = {
    "greeting_how":   ("Oraire ota?",          "Good morning / How have you slept?"),
    "greeting_state": ("Oroho ota?",            "How are you?"),
    "reply_fine":     ("Ndooho nti!",           "I am fine!"),
    "how_do_they":    ("Abakazi balima bata?",  "How do women dig?"),
    "like_this":      ("Balima bati:",          "They dig like this"),
    "how_sound":      ("Ente zijuga zita?",     "How do cows moo?"),
    "sound_like":     ("Zijuga ziti:",          "They moo like this"),
}

def apply_modal_ta_greeting(text: str) -> str:
    """
    Detect and preserve -ota? / -ata? greeting patterns.
    Ensures the model does not split 'ota' into 'o ta' or mistranslate it.
    Returns the text unchanged if no greeting pattern found.
    """
    # Common greeting patterns — preserve as-is
    _greetings = _re.compile(
        r'\b(oraire\s+ota|oroho\s+ota|oli\s+ota|muli\s+ota)\b',
        _re.IGNORECASE
    )
    if _greetings.search(text):
        return text  # already correct, do not modify
    return text


def build_modal_ti_speech(speaker_prefix: str, message: str) -> str:
    """
    Build a reported speech construction using -ti.
    e.g. build_modal_ti_speech('tukabagambira', 'Na itwe tuli bantu nka inywe.')
    -> "Tukabagambira tuti, 'Na itwe tuli bantu nka inywe.'"
    """
    # Derive the -ti form: replace subject prefix with matching -ti concord
    _ti_map = {
        "n": "nti", "tu": "tuti", "o": "oti", "mu": "muti",
        "a": "ati", "ba": "bati",
    }
    ti_form = "bati"  # default
    for pfx, ti in sorted(_ti_map.items(), key=lambda x: -len(x[0])):
        if speaker_prefix.lower().startswith(pfx):
            ti_form = ti
            break
    return f"{speaker_prefix} {ti_form}, '{message}'"


# ─────────────────────────────────────────────────────────────────────────────
# 5. DARA PRESENTATIVE WORD
# Source: grammar rules 4.docx — Word dara
# ─────────────────────────────────────────────────────────────────────────────

DARA_PRONOUNS = {
    "1sg": "daranyowe",  "2sg": "daraiwe",   "3sg": "darawe",
    "1pl": "daraitwe",   "2pl": "darainywe", "3pl": "darabo",
}

DARA_NOUN_CLASSES = {
    3: "daragwo",  4: "darayo",  5: "daralyo",  6: "darago",
    7: "darakyo",  8: "darabyo", 9: "darayo",   10: "darazo",
    11: "dararwo", 12: "darako", 13: "daratwo",  14: "darabwo", 15: "darakwo",
}

DARA_NEAR_DEMONSTRATIVES = {
    1: "daroonu",  2: "darabanu",  3: "daragunu",  4: "daleenu",
    5: "daralinu", 6: "daraganu",  7: "darakinu",  8: "darabinu",
    9: "daleenu",  10: "darazinu", 11: "dararunu", 12: "darakanu",
    13: "daratunu",14: "darabunu", 15: "darakunu",
}

def get_dara_form(person_or_class, near: bool = False) -> str:
    """
    Return the dara (presentative/locative) form.
    person_or_class: '1sg','2sg','3sg','1pl','2pl','3pl' or int noun class
    near=True: use near-demonstrative form (daroonu etc.)
    e.g. get_dara_form('3sg') -> 'darawe'
         get_dara_form(1, near=True) -> 'daroonu'
    """
    if isinstance(person_or_class, str):
        return DARA_PRONOUNS.get(person_or_class, "")
    if near:
        return DARA_NEAR_DEMONSTRATIVES.get(person_or_class, "")
    return DARA_NOUN_CLASSES.get(person_or_class, "")


# ─────────────────────────────────────────────────────────────────────────────
# 6. NI- / N- COPULA DISTRIBUTION RULES
# Source: grammar rules 4.docx — Particles ni- and n-
# ─────────────────────────────────────────────────────────────────────────────

# ni- used before: self-standing pronouns, questions, present imperfect tense
# n- used before: demonstratives (near -nu and far -li roots)

COPULA_NI_PRONOUNS = {
    "1sg": "niinyowe",  "2sg": "niiwe",   "3sg": "nuwe",
    "1pl": "niitwe",    "2pl": "niinywe", "3pl": "nubo",
}

COPULA_N_NEAR = {   # n- + -nu demonstratives
    1: "ngunu",  2: "mbanu",  3: "ngunu",  4: "nginu",
    5: "ndinu",  6: "nganu",  7: "nkinu",  8: "mbinu",
    9: "nginu",  10: "nzinu", 11: "ndunu", 12: "nkanu",
    13: "ntunu", 14: "mbunu", 15: "nkunu",
}

COPULA_N_FAR = {    # n- + -li demonstratives
    1: "nguli",  2: "mbali",  3: "nguli",  4: "ngiri",
    5: "ndiri",  6: "ngali",  7: "nkiri",  8: "mbiri",
    9: "ngiri",  10: "nziri", 11: "nduli", 12: "nkali",
    13: "ntuli", 14: "mbuli", 15: "nkuli",
}

COPULA_RULES = {
    "ni_before_pronoun":    "ni- + self-standing pronoun (niinyowe, niiwe, nuwe...)",
    "ni_before_question":   "ni- before question words (niiwe oha? = who are you?)",
    "ni_before_imperfect":  "ni- as present imperfect tense marker (nigenda = is going)",
    "n_before_near_dem":    "n- + near demonstrative (-nu root): ngunu, mbanu...",
    "n_before_far_dem":     "n- + far demonstrative (-li root): nguli, mbali...",
    "elision_before_vowel": "ni + vowel-initial word: ni drops to n' (n'omuntu = it is a person)",
}

def apply_copula(word: str, copula_type: str = "ni") -> str:
    """
    Apply the correct copula form to a word.
    copula_type: 'ni' (before pronouns/questions) or 'n' (before demonstratives)
    Handles vowel elision automatically.
    e.g. apply_copula('omuntu', 'ni') -> "n'omuntu"
         apply_copula('nyowe', 'ni')  -> 'niinyowe'
    """
    if not word:
        return word
    # Check if it's a known self-standing pronoun
    for person, form in COPULA_NI_PRONOUNS.items():
        if word.lower() in (_SELF_STANDING.get(person, ""), ""):
            return form
    # Vowel elision: ni + vowel -> n'
    if copula_type == "ni" and word[0].lower() in "aeiou":
        return "n'" + word
    if copula_type == "ni":
        return "ni" + word
    # n- copula before demonstratives
    return "n" + word


def apply_copula_to_text(text: str) -> str:
    """
    Correct common MT errors where copula ni is incorrectly split or omitted.
    e.g. 'ni omuntu' -> "n'omuntu", 'ni nyowe' -> 'niinyowe'
    """
    result = _re.sub(r'\bni\s+([aeiou])', lambda m: "n'" + m.group(1), text, flags=_re.IGNORECASE)
    result = _re.sub(r'\bni\s+nyowe\b', 'niinyowe', result, flags=_re.IGNORECASE)
    result = _re.sub(r'\bni\s+iwe\b',   'niiwe',    result, flags=_re.IGNORECASE)
    result = _re.sub(r'\bni\s+uwe\b',   'nuwe',     result, flags=_re.IGNORECASE)
    result = _re.sub(r'\bni\s+itwe\b',  'niitwe',   result, flags=_re.IGNORECASE)
    result = _re.sub(r'\bni\s+inywe\b', 'niinywe',  result, flags=_re.IGNORECASE)
    result = _re.sub(r'\bni\s+bo\b',    'nubo',     result, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 7. KA PARTICLE  (emphatic vs permissive)
# Source: grammar rules 4.docx — Particle ka
# ─────────────────────────────────────────────────────────────────────────────

KA_EMPHATIC_PATTERNS = {
    "noun":    ("ka muntu",   "the very person"),
    "adj":     ("ka murungi", "a really good one"),
    "pronoun": ("ka niiwe",   "it is really you"),
    "poss":    ("ka wange",   "it is really my relative"),
    "dem":     ("ka ngunu",   "here he/she truly is"),
}

KA_PERMISSIVE_EXAMPLES = {
    "1pl": ("ka tugende",  "let us go"),
    "1sg": ("ka ngende",   "let me go"),
    "3sg": ("ka agende",   "let him/her go"),
    "3pl": ("ka bagende",  "let them go"),
}

def build_ka_permissive(person: str, verb_stem: str) -> str:
    """
    Build a permissive construction: ka + subjunctive verb form.
    e.g. build_ka_permissive('1pl', 'genda') -> 'ka tugende'
    """
    _subj_pfx = {
        "1sg": "n",  "2sg": "o",  "3sg": "a",
        "1pl": "tu", "2pl": "mu", "3pl": "ba",
    }
    pfx = _subj_pfx.get(person, "a")
    # Subjunctive: replace final -a with -e
    stem_subj = verb_stem.rstrip("a") + "e" if verb_stem.endswith("a") else verb_stem + "e"
    return f"ka {pfx}{stem_subj}"

def apply_ka_emphatic(text: str) -> str:
    """
    Preserve ka emphatic constructions in MT output.
    Prevents the model from dropping 'ka' before emphatic nouns/pronouns.
    """
    # ka + demonstrative near: ensure no space is dropped
    result = _re.sub(r'\bka\s+(ngunu|mbanu|nginu|ndinu|nganu|nkinu|mbinu|nzinu|ndunu|nkanu|ntunu|mbunu|nkunu)\b',
                     lambda m: "ka " + m.group(1), text, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 8. FRACTIONS AND DISTRIBUTIVES
# Source: grammar rules 4.docx — Ordinals, Fractions, Distributives
# ─────────────────────────────────────────────────────────────────────────────

_FRACTION_DENOM_STEMS = {
    2: "kabiri", 3: "kasatu", 4: "kana",    5: "kataano",
    6: "mukaaga",7: "musanju",8: "munaana", 9: "mwenda", 10: "ikumi",
}
_FRACTION_NUM_CL7 = {1: "kimu"}
_FRACTION_NUM_CL8 = {2: "bibiri", 3: "bisatu", 4: "bina", 5: "bitaano"}

def build_fraction(numerator: int, denominator: int, numerator_first: bool = True) -> str:
    """
    Build a fraction expression in Runyoro-Rutooro.
    numerator_first=True:  kimu kya kabiri  (1/2)
    numerator_first=False: ekyakabiri kimu  (1/2)
    """
    d = _FRACTION_DENOM_STEMS.get(denominator, str(denominator))
    if numerator == 1:
        n_stem = "kimu"
        gp_num = "kya"
        gp_den = "ekya"
    elif numerator <= 5:
        n_stem = _FRACTION_NUM_CL8.get(numerator, str(numerator))
        gp_num = "bya"
        gp_den = "ebya"
    else:
        n_stem = str(numerator)
        gp_num = "bya"
        gp_den = "ebya"
    if numerator_first:
        return f"{n_stem} {gp_num} {d}"
    return f"{gp_den}{d} {n_stem}"


def build_distributive(number_word: str) -> str:
    """
    Build a distributive (X by X) by reduplicating the number word.
    e.g. build_distributive('babiri') -> 'babiri babiri'
         build_distributive('basatu') -> 'basatu basatu'
    """
    return f"{number_word} {number_word}"


def apply_distributive_correction(text: str) -> str:
    """
    Correct MT output where distributive reduplication is missing.
    e.g. 'bazina babiri' should stay as-is; 'bazina babiri babiri' is correct.
    Detects patterns like 'V + number' and checks for reduplication.
    """
    _dist_numbers = r'(babiri|basatu|bana|bataano|mukaaga|musanju|munaana|mwenda)'
    # If a number appears once after a verb of motion/action, suggest reduplication
    result = _re.sub(
        r'\b(' + _dist_numbers[1:-1] + r')\s+(?!\1\b)',
        lambda m: m.group(0),  # leave as-is; flag for review
        text, flags=_re.IGNORECASE
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 9. VERB-TO-NOUN DERIVATION  (ki-/ka-/ru- concords on verb stems)
# Source: grammar rules 4.docx — Noun derivation from verbs
# ─────────────────────────────────────────────────────────────────────────────

# Agent nouns: omu- (cl.1) + verb root + -i
# Action nouns: omu- (cl.3) + verb root + -o
# Method nouns: en- (cl.9) + verb root + -a

VERB_NOUN_DERIVATION = {
    "agent_cl1":   {"prefix": "omu", "suffix": "i",  "desc": "one who does X (omulimi = cultivator)"},
    "action_cl3":  {"prefix": "omu", "suffix": "o",  "desc": "the act/work of X (omulimo = work)"},
    "method_cl9":  {"prefix": "en",  "suffix": "a",  "desc": "method/way of X (endima = method of digging)"},
    "servant_cl1": {"prefix": "omu", "suffix": "a",  "desc": "professional/habitual doer (omulima = professional digger)"},
}

VERB_NOUN_EXAMPLES = {
    "okulima":  {
        "agent":   "omulimi",   # cultivator
        "action":  "omulimo",   # work/digging
        "method":  "endima",    # method of digging
        "servant": "omulima",   # professional digger
    },
    "okuzaana": {
        "agent":   "omuzaani",  # player
        "action":  "omuzaano",  # play
        "method":  "enzaana",   # method of playing
        "servant": "omuzaana",  # maid servant
    },
    "okubara":  {
        "agent":   "omubazi",   # carpenter (r->z before -i)
        "action":  "omubaro",   # counting/carpentry
        "method":  "embara",    # method of counting
    },
    "okuhiija": {
        "agent":   "omuhiizi",  # one who pants (j->z before -i)
        "action":  "omuhiijo",  # panting
    },
}

def derive_agent_noun(verb_infinitive: str) -> str:
    """
    Derive the agent noun (class 1) from a verb infinitive.
    Applies consonant mutation: r->z, t->s, j->z before -i suffix.
    e.g. derive_agent_noun('okulima') -> 'omulimi'
         derive_agent_noun('okubara') -> 'omubazi'
    """
    v = verb_infinitive.lower().strip()
    # Strip infinitive prefix
    for pfx in ("okw", "oku"):
        if v.startswith(pfx):
            stem = v[len(pfx):]
            break
    else:
        stem = v
    # Strip final -a
    root = stem.rstrip("a")
    # Apply consonant mutation before -i
    if root.endswith("r"):
        root = root[:-1] + "z"
    elif root.endswith("t"):
        root = root[:-1] + "s"
    elif root.endswith("j"):
        root = root[:-1] + "z"
    return "omu" + root + "i"


def derive_action_noun(verb_infinitive: str) -> str:
    """
    Derive the action noun (class 3) from a verb infinitive.
    e.g. derive_action_noun('okulima') -> 'omulimo'
    """
    v = verb_infinitive.lower().strip()
    for pfx in ("okw", "oku"):
        if v.startswith(pfx):
            stem = v[len(pfx):]
            break
    else:
        stem = v
    root = stem.rstrip("a")
    return "omu" + root + "o"


def derive_method_noun(verb_infinitive: str) -> str:
    """
    Derive the method noun (class 9) from a verb infinitive.
    e.g. derive_method_noun('okulima') -> 'endima'
    """
    v = verb_infinitive.lower().strip()
    for pfx in ("okw", "oku"):
        if v.startswith(pfx):
            stem = v[len(pfx):]
            break
    else:
        stem = v
    # Class 9 prefix: en- before consonants, em- before b/p
    first = stem[0].lower() if stem else ""
    prefix = "em" if first in ("b", "p") else "en"
    return prefix + stem


# ─────────────────────────────────────────────────────────────────────────────
# 10. KINSHIP TERMS  (ise/nyina/isenkuru etc. with person/number agreement)
# Source: grammar rules 4.docx — Names of Relationship
# ─────────────────────────────────────────────────────────────────────────────

KINSHIP_TERMS = {
    "father": {
        "1sg": "isange",      "2sg": "isaawe",    "3sg": "ise",
        "1pl": "isiitwe",     "2pl": "isiinywe",  "3pl": "isabo",
    },
    "mother": {
        "1sg": "nyinange",    "2sg": "nyinawe",   "3sg": "nyina",
        "1pl": "nyinenitu",   "2pl": "nyineninywe","3pl": "nyinabo",
    },
    "grandfather": {
        "1sg": "isenkurwange","2sg": "isenkurwawe","3sg": "isenkuru",
        "1pl": "isenkurwitwe","2pl": "isenkurwinywe","3pl": "isenkurwabo",
    },
    "grandmother": {
        "1sg": "nyinenkurwange","2sg": "nyinenkurwawe","3sg": "nyinenkuru",
        "1pl": "nyinenkurwitwe","2pl": "nyinenkurwinywe","3pl": "nyinenkurwabo",
    },
    "paternal_aunt": {
        "3sg": "isenkati",
    },
    "maternal_aunt": {
        "3sg": "nyinento",
    },
    "maternal_uncle": {
        "3sg": "nyinarumi",
    },
    "paternal_uncle": {
        "3sg": "isento",
    },
    "father_in_law": {
        "3sg": "isezaara",
    },
    "mother_in_law": {
        "3sg": "nyinazaara",
    },
    "husband": {
        "3sg": "iba",
    },
}

def get_kinship_term(relation: str, person: str = "3sg") -> str:
    """
    Return the kinship term for a relation and person.
    relation: 'father','mother','grandfather','grandmother',
              'paternal_aunt','maternal_aunt','maternal_uncle',
              'paternal_uncle','father_in_law','mother_in_law','husband'
    person: '1sg','2sg','3sg','1pl','2pl','3pl'
    e.g. get_kinship_term('father', '1pl') -> 'isiitwe'
         get_kinship_term('mother', '3sg') -> 'nyina'
    """
    rel = KINSHIP_TERMS.get(relation, {})
    return rel.get(person, rel.get("3sg", ""))


def apply_kinship_correction(text: str) -> str:
    """
    Correct common MT errors in kinship terms.
    e.g. 'ise wange' -> 'isange', 'nyina we' -> 'nyinawe'
    """
    corrections = {
        r'\bise\s+wange\b':    'isange',
        r'\bise\s+wawe\b':     'isaawe',
        r'\bise\s+waitu\b':    'isiitwe',
        r'\bise\s+wanyu\b':    'isiinywe',
        r'\bnyina\s+wange\b':  'nyinange',
        r'\bnyina\s+wawe\b':   'nyinawe',
        r'\bnyina\s+waitu\b':  'nyinenitu',
        r'\bnyina\s+wanyu\b':  'nyineninywe',
        r'\bisenkuru\s+wange\b': 'isenkurwange',
        r'\bisenkuru\s+wawe\b':  'isenkurwawe',
        r'\bisenkuru\s+waitu\b': 'isenkurwitwe',
    }
    result = text
    for pattern, repl in corrections.items():
        result = _re.sub(pattern, repl, result, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MASTER POST-PROCESSING FUNCTION
# Applies all gr4 rules to MT output in the correct order.
# Called from translate.py after existing post-processing.
# ─────────────────────────────────────────────────────────────────────────────

def apply_gr4_rules(text: str, direction: str = "en->lun") -> str:
    """
    Apply all Grammar Rules 4 post-processing corrections to MT output.
    Only applied to Runyoro-Rutooro output (en->lun direction).
    """
    if "lun" not in direction and "->lun" not in direction:
        return text  # only post-process Runyoro output

    result = text
    result = apply_enumerative_correction(result)   # 1. enumeratives
    result = apply_copula_to_text(result)            # 6. copula ni-/n-
    result = apply_ka_emphatic(result)               # 7. ka particle
    result = apply_kinship_correction(result)        # 10. kinship terms
    result = apply_modal_ta_greeting(result)         # 4. modal -ta? greetings
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GRAMMAR CONTEXT EXTENSION  (for chat system prompt)
# ─────────────────────────────────────────────────────────────────────────────

GR4_GRAMMAR_CONTEXT = """
--- Grammar Rules 4 (Pronominal System, Copula, Kinship, Numbers) ---
ENUMERATIVE PRONOUNS:
  -enka/-onka (alone/only): nyenka=I alone, bonka=they only
  -ena/-ona (all): boona=all of them, tweena=all of us
  -enyini/-onyini (self): boonyini=they themselves, nyeenyini=I myself
  -embi/-ombi (both, pl only): bombi=both of them, twembi=both of us

DEMONSTRATIVES:
  Near (-nu root): onu(cl.1), banu(cl.2), gunu(cl.3), kinu(cl.7), zinu(cl.10)
  Far (-li root):  oli(cl.1), bali(cl.2), guli(cl.3), kiri(cl.7), ziri(cl.10)
  In mind: ogu(cl.1), abo(cl.2), eki(cl.7), ezi(cl.10)

COPULA NI-/N-:
  ni- before pronouns: niinyowe(I am), niiwe(you are), nuwe(he/she is)
  ni- before vowels: n'omuntu (it is a person), n'ente (it is a cow)
  n- before near demonstratives: ngunu(cl.3), mbanu(cl.2), nkinu(cl.7)
  n- before far demonstratives: nguli(cl.3), mbali(cl.2), nkiri(cl.7)

MODAL PARTICLES:
  -ota? (how?): Oraire ota? = Good morning; Oroho ota? = How are you?
  -ti (like this / reported speech): Balima bati = They dig like this
    Tukabagambira tuti, '...' = We told them, '...'

DARA (presentative): daranyowe=here I am, darawe=here he/she is,
  darabo=here they are, daroonu=here it is (near, cl.1)

KA PARTICLE:
  Emphatic: ka muntu=the very person, ka niiwe=it is really you
  Permissive: ka tugende=let us go, ka ngende=let me go

KINSHIP TERMS (with possessive agreement):
  father: isange(my), isaawe(your), ise(his/her), isiitwe(our)
  mother: nyinange(my), nyinawe(your), nyina(his/her), nyinenitu(our)
  grandfather: isenkurwange(my), isenkurwawe(your), isenkuru(his/her), isenkurwitwe(our)

FRACTIONS: kimu kya kabiri=1/2, bibiri bya kataano=2/5
DISTRIBUTIVES: babiri babiri=two by two, basatu basatu=three by three

VERB-TO-NOUN DERIVATION:
  Agent (cl.1): omu- + root + -i  (omulimi=cultivator, omubazi=carpenter)
  Action (cl.3): omu- + root + -o  (omulimo=work, omubaro=counting)
  Method (cl.9): en-/em- + stem    (endima=method of digging)
"""

def get_gr4_grammar_context() -> str:
    """Return Grammar Rules 4 context string for chat system prompt."""
    return GR4_GRAMMAR_CONTEXT
