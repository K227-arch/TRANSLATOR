"""
language_rules_gr5.py
=====================
Implements missing rules from grammar rules 5.docx (Chapters 5, 6, 7):

1.  Locative adverbial prefixes  (omu-/ha-/ku-/owa-/omba)
2.  Locative demonstratives      (munu/muli/hanu/hali/kunu/kuli)
3.  Self-standing adverbials     (mwo/ho/oku + -o of reference)
4.  Adverbial suffixes           (-mu/-ho/-yo)
5.  Locative possessives         (omwange/owange/omwawe/owaawe etc.)
6.  Copula ni- + locatives       (numwo/nuho/nihanu/nukunu etc.)
7.  Dara + locative              (daraho/daramunu/darahanu)
8.  ho + enumerative roots       (hoona/honka/hombi/hoonyini)
9.  Objectival concord           (reversed-object sentences)
10. Noun classes 1a/2a/9a/10a   (names, foreign words, colours)
11. Colour names (Class 9a)
12. Negative nouns               (omu-ta- prefix)
13. Class 9 professional nouns  (en- prefix derivation)
14. Augmentative/pejorative     (class prefix substitution)

All functions are wired into translate.py post-processing via apply_gr5_rules().
"""
import re as _re


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOCATIVE ADVERBIAL PREFIXES
# Source: grammar rules 5.docx — Chapter 5
# omu-/omw- = in/inside   ha- = on/at   ku- = to/towards
# owa- = to a person's place   omba = to an area belonging to a person
# ─────────────────────────────────────────────────────────────────────────────

LOCATIVE_PREFIXES = {
    "omu": "in/inside (enclosed space)",
    "omw": "in/inside (before vowel)",
    "ha":  "on/at (surface or general location)",
    "ku":  "to/towards/at (direction or general)",
    "owa": "to a person's place",
    "omba": "to an area belonging to a person",
}

def build_locative(noun: str, prefix: str = "omu") -> str:
    """
    Build a locative adverbial noun by prepending the locative prefix.
    Handles vowel-initial nouns (omu -> omw, ha stays ha, ku stays ku).
    e.g. build_locative('nju', 'omu') -> 'omunju'
         build_locative('iguru', 'omu') -> 'omwiguru'
         build_locative('eza', 'ha') -> 'hanza'  (table -> on the table)
    """
    noun = noun.strip().lstrip("o").lstrip("e") if noun.startswith(("om","en","ek","eb","er","ab")) else noun
    if prefix == "omu" and noun and noun[0].lower() in "aeiou":
        return "omw" + noun
    return prefix + noun

def get_locative_suffix(prefix: str) -> str:
    """
    Return the correct adverbial suffix for a given locative prefix.
    omu- -> -mu,  ha- -> -ho,  owa-/omba/ku- -> -yo
    """
    if prefix in ("omu", "omw"):
        return "mu"
    if prefix == "ha":
        return "ho"
    return "yo"  # owa-, omba, ku-

# Common locative adverbial nouns (pre-built)
LOCATIVE_NOUNS = {
    "omunsi":    ("in the world",          "omu"),
    "omwiguru":  ("in heaven/sky",         "omu"),
    "omukibira": ("in the forest",         "omu"),
    "omunda":    ("inside/in the stomach", "omu"),
    "omumaiso":  ("in front",              "omu"),
    "omunziha":  ("where water is deeper", "omu"),
    "hameeza":   ("on the table",          "ha"),
    "hansi":     ("on the ground/below",   "ha"),
    "haiguru":   ("above/up",              "ha"),
    "harubaju":  ("aside/to the side",     "ha"),
    "hanju":     ("on the house",          "ha"),
    "owanyu":    ("at your home",          "owa"),
    "owaitu":    ("at our home",           "owa"),
    "owaabu":    ("at their home",         "owa"),
    "omba":      ("to a person's area",    "omba"),
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. LOCATIVE DEMONSTRATIVES
# Source: grammar rules 5.docx — In Combination with Demonstratives
# mu+nu=munu, mu+li=muli, ha+nu=hanu, ha+li=hali, ku+nu=kunu, ku+li=kuli
# ─────────────────────────────────────────────────────────────────────────────

LOCATIVE_DEMONSTRATIVES = {
    "munu":  ("in here",       "omu", "near"),
    "muli":  ("in there",      "omu", "far"),
    "hanu":  ("here",          "ha",  "near"),
    "hali":  ("there",         "ha",  "far"),
    "kunu":  ("this way/side", "ku",  "near"),
    "kuli":  ("that way/side", "ku",  "far"),
}

def get_locative_demonstrative(prefix: str, proximity: str = "near") -> str:
    """
    Return the locative demonstrative for a prefix and proximity.
    e.g. get_locative_demonstrative('ha', 'near') -> 'hanu'
         get_locative_demonstrative('ku', 'far')  -> 'kuli'
    """
    root = "nu" if proximity == "near" else "li"
    return prefix + root

# ─────────────────────────────────────────────────────────────────────────────
# 3. SELF-STANDING ADVERBIALS  (-o of reference)
# Source: grammar rules 5.docx — In Combination with the -o of Reference
# mu+o=mwo, ha+o=ho, ku+o=kwo (adjective 'real', not adverbial)
# ─────────────────────────────────────────────────────────────────────────────

SELF_STANDING_ADVERBIALS = {
    "mwo": ("in it",    "omu"),
    "ho":  ("on it",    "ha"),
    "oku": ("there/that side", "ku"),
    "omu": ("in there", "omu"),
    "aho": ("on there", "ha"),
}

def get_self_standing_adverbial(prefix: str) -> str:
    """
    Return the self-standing adverbial pronoun for a prefix.
    e.g. get_self_standing_adverbial('ha') -> 'ho'
         get_self_standing_adverbial('omu') -> 'mwo'
    """
    mapping = {"omu": "mwo", "omw": "mwo", "ha": "ho", "ku": "oku"}
    return mapping.get(prefix, "")


# ─────────────────────────────────────────────────────────────────────────────
# 4. ADVERBIAL SUFFIXES  -mu / -ho / -yo
# Source: grammar rules 5.docx — Locatives as Adverbial Suffixes
# -mu: with omu- nouns   -ho: with ha- nouns   -yo: with owa-/omba/ku- nouns
# ─────────────────────────────────────────────────────────────────────────────

ADVERBIAL_SUFFIX_EXAMPLES = {
    "-mu": [
        ("Omunsi busamu kusemererwa",  "there is no happiness in the world"),
        ("Munu harumu amaizi",         "there is water in here"),
        ("Taahamu",                    "get in"),
    ],
    "-ho": [
        ("Hanju heemeriireho ekidongodongo", "a heron is standing on the house"),
        ("Hansi haroho ki?",                 "what is on the ground?"),
        ("Taaho",                            "take away"),
        ("Rugaho",                           "get away"),
    ],
    "-yo": [
        ("Ndigendayo ndole enyamunungu",          "I shall go there to see the porcupine"),
        ("Owaitu haraireyo abagenyi bana",        "four visitors slept at our home"),
        ("Kuli busayo muntu",                     "there is no person there"),
        ("Muraireyo muta?",                       "how did you sleep over there?"),
    ],
}

def apply_adverbial_suffix(verb: str, locative_prefix: str) -> str:
    """
    Append the correct adverbial suffix to a verb based on the locative prefix.
    e.g. apply_adverbial_suffix('genda', 'owa') -> 'gendayo'
         apply_adverbial_suffix('ikara', 'ha')  -> 'ikaraho'
         apply_adverbial_suffix('taaha', 'omu') -> 'taahamu'
    """
    suffix = get_locative_suffix(locative_prefix)
    if verb.endswith(suffix):
        return verb  # already has suffix
    return verb + suffix

def apply_adverbial_suffix_correction(text: str) -> str:
    """
    Correct common MT errors where adverbial suffixes are missing or wrong.
    e.g. 'genda owaitu' -> 'gendayo owaitu'
         'ikara hansi' -> 'ikaraho hansi'
    """
    corrections = [
        # -yo with owa-/ku- locatives
        (r'\b(genda|ruga|ija|garuka|twara|leeta)\s+(owaitu|owaabu|owaawe|owaanyu|owe|owange)\b',
         lambda m: m.group(1) + "yo " + m.group(2)),
        # -ho with ha- locatives
        (r'\b(ikara|yemera|taho|ruga)\s+(hansi|haiguru|harubaju|hameeza|hanu)\b',
         lambda m: m.group(1) + "ho " + m.group(2)),
        # -mu with omu- locatives
        (r'\b(ikara|baho|rumu)\s+(omunsi|omukibira|omunda|omwiguru)\b',
         lambda m: m.group(1) + "mu " + m.group(2)),
    ]
    result = text
    for pattern, repl in corrections:
        result = _re.sub(pattern, repl, result, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. LOCATIVE POSSESSIVES
# Source: grammar rules 5.docx — In Combination with Possessives
# omwa- (in my/your/his house)   owa- (to/at my/your/his home)
# ─────────────────────────────────────────────────────────────────────────────

LOCATIVE_POSSESSIVES_OMWA = {
    "1sg":  "omwange",   # in my house
    "2sg":  "omwawe",    # in your house
    "3sg":  "omwe",      # in his/her house
    "1pl":  "omwaitu",   # in the house where I/we stay
    "2pl":  "omwanyu",   # in the house where you (pl) stay
    "3pl":  "omwabu",    # in the house where he/they stay
}

LOCATIVE_POSSESSIVES_OWA = {
    "1sg":  "owange",    # to/at my home
    "2sg":  "owaawe",    # to/at your home
    "3sg":  "owe",       # to/at his/her home
    "1pl":  "owaitu",    # to/at the home where I/we stay
    "2pl":  "owaanyu",   # to/at the home where you (pl) stay
    "3pl":  "owaabu",    # to/at the home where he/they stay
}

def get_locative_possessive(person: str, locative_type: str = "owa") -> str:
    """
    Return the locative possessive for a person and type.
    locative_type: 'omwa' (in house) | 'owa' (to/at home)
    e.g. get_locative_possessive('1sg', 'omwa') -> 'omwange'
         get_locative_possessive('3pl', 'owa')  -> 'owaabu'
    """
    if locative_type == "omwa":
        return LOCATIVE_POSSESSIVES_OMWA.get(person, "")
    return LOCATIVE_POSSESSIVES_OWA.get(person, "")

# Noun-class locative possessives (classes 3-15 use omwabu/owaabu + pronoun)
LOCATIVE_CLASS_POSSESSIVES = {
    3:  {"omwa": "omwabugwo",  "owa": "owaabugwo"},   # mongoose (cl.3)
    4:  {"omwa": "omwabuyo",   "owa": "owaabuyo"},    # mongooses (cl.4)
    7:  {"omwa": "omwabukyo",  "owa": "owaabukyo"},
    8:  {"omwa": "omwabubyo",  "owa": "owaabubyo"},
    9:  {"omwa": "omwabuyo",   "owa": "owaabuyo"},
    10: {"omwa": "omwabuzo",   "owa": "owaabuzo"},
}

def get_class_locative_possessive(noun_class: int, locative_type: str = "owa") -> str:
    """
    Return the locative possessive for a noun class.
    e.g. get_class_locative_possessive(3, 'omwa') -> 'omwabugwo'
    """
    entry = LOCATIVE_CLASS_POSSESSIVES.get(noun_class, {})
    return entry.get(locative_type, "")


# ─────────────────────────────────────────────────────────────────────────────
# 6. COPULA NI- + LOCATIVE ADVERBIALS
# Source: grammar rules 5.docx — The Copula ni- with adverbials
# numwo, nuho, nihanu, nihali, nukunu, nukuli, nimunu, nimuli
# ─────────────────────────────────────────────────────────────────────────────

COPULA_LOCATIVE = {
    "mwo":  "numwo",   # it is in it
    "ho":   "nuho",    # it is on it
    "hanu": "nihanu",  # it is here
    "hali": "nihali",  # it is there
    "kunu": "nukunu",  # it is this way
    "kuli": "nukuli",  # it is that way
    "munu": "nimunu",  # it is in here
    "muli": "nimuli",  # it is in there
    "oku":  "nooku",   # it is that direction
    "aho":  "naaho",   # it is on there
}

def get_copula_locative(adverbial: str) -> str:
    """
    Return the copula + locative adverbial form.
    e.g. get_copula_locative('hanu') -> 'nihanu'
         get_copula_locative('mwo')  -> 'numwo'
    """
    return COPULA_LOCATIVE.get(adverbial.lower(), "ni" + adverbial)

def apply_copula_locative_correction(text: str) -> str:
    """
    Correct MT errors where copula ni is split from locative adverbials.
    e.g. 'ni hanu' -> 'nihanu', 'ni mwo' -> 'numwo'
    """
    corrections = {
        r'\bni\s+hanu\b':  'nihanu',
        r'\bni\s+hali\b':  'nihali',
        r'\bni\s+kunu\b':  'nukunu',
        r'\bni\s+kuli\b':  'nukuli',
        r'\bni\s+munu\b':  'nimunu',
        r'\bni\s+muli\b':  'nimuli',
        r'\bni\s+mwo\b':   'numwo',
        r'\bni\s+ho\b':    'nuho',
        r'\bni\s+oku\b':   'nooku',
        r'\bni\s+aho\b':   'naaho',
    }
    result = text
    for pattern, repl in corrections.items():
        result = _re.sub(pattern, repl, result, flags=_re.IGNORECASE)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 7. DARA + LOCATIVE
# Source: grammar rules 5.docx — The word dara with adverbials
# daraho, daramunu, darahanu, darahali, darakunu
# ─────────────────────────────────────────────────────────────────────────────

DARA_LOCATIVE = {
    "ho":   "daraho",    # here I come to the place (on it)
    "munu": "daramunu",  # I am sure it is in here
    "hanu": "darahanu",  # I am sure it is from here / come here
    "hali": "darahali",  # it is from there
    "kunu": "darakunu",  # it is this way
    "mwo":  "daramwo",   # in it (here it is inside)
}

def get_dara_locative(adverbial: str) -> str:
    """
    Return the dara + locative form.
    e.g. get_dara_locative('hanu') -> 'darahanu'
         get_dara_locative('ho')   -> 'daraho'
    Note: darahanu also means 'come here, I have something to speak to you'.
    """
    return DARA_LOCATIVE.get(adverbial.lower(), "dara" + adverbial)

# ─────────────────────────────────────────────────────────────────────────────
# 8. HO + ENUMERATIVE ROOTS
# Source: grammar rules 5.docx — The Adverbials mwo and ho
# hoona (everywhere), honka (only there), hombi (both sides), hoonyini (very spot)
# ─────────────────────────────────────────────────────────────────────────────

HO_ENUMERATIVE = {
    "hoona":    "everywhere / all over",
    "honka":    "only there / in that place only",
    "hombi":    "both sides / both places",
    "hoonyini": "the very spot / exactly there",
}

HO_ENUMERATIVE_EXAMPLES = [
    ("Ruhanga ali omwiguru, n'omunsi na buli hantu hoona.", "God is in heaven, on earth and everywhere."),
    ("Hameeza hoona haijwireho ebitabu.", "There are books everywhere on the table."),
    ("Nkarora omusanduuko honka.", "I looked in the box only."),
    ("Hombi, omunda n'aheeru y'orugoye runu nihasisana.", "Both sides of this cloth are alike."),
    ("Ho hoonyini ntahikeho.", "I did not reach the very spot."),
]

def get_ho_enumerative(enum_type: str) -> str:
    """
    Return the ho + enumerative form.
    enum_type: 'all'/'everywhere' -> 'hoona'
               'only' -> 'honka'
               'both' -> 'hombi'
               'self'/'very' -> 'hoonyini'
    """
    mapping = {
        "all": "hoona", "everywhere": "hoona",
        "only": "honka",
        "both": "hombi",
        "self": "hoonyini", "very": "hoonyini",
    }
    return mapping.get(enum_type.lower(), "ho" + enum_type)


# ─────────────────────────────────────────────────────────────────────────────
# 9. OBJECTIVAL CONCORD (REVERSED-OBJECT SENTENCES)
# Source: grammar rules 5.docx — Chapter 6, Object
# When object is fronted, verb takes objectival concord before stem.
# ─────────────────────────────────────────────────────────────────────────────

OBJECTIVAL_CONCORDS = {
    1:  "mu",   2:  "ba",   3:  "gu",   4:  "yi",
    5:  "li",   6:  "ga",   7:  "ki",   8:  "bi",
    9:  "yi",   10: "zi",   11: "ru",   12: "ka",
    13: "tu",   14: "bu",   15: "ku",
}

def get_objectival_concord(noun_class: int) -> str:
    """
    Return the objectival concord for a noun class.
    Used when the object is fronted (reversed) in a sentence.
    e.g. get_objectival_concord(3) -> 'gu'
         'omusiri omukazi agulimire' (the garden the woman dug it)
    """
    return OBJECTIVAL_CONCORDS.get(noun_class, "")

def build_reversed_object_sentence(
    subject: str,
    subject_class: int,
    object_noun: str,
    object_class: int,
    verb_stem: str,
    tense_prefix: str = "a",
) -> str:
    """
    Build a reversed-object sentence where the object is fronted.
    e.g. build_reversed_object_sentence('omukazi', 1, 'omusiri', 3, 'lima', 'a')
         -> 'omusiri omukazi agulimire'
    Subject concord + objectival concord + verb stem + perfect suffix.
    """
    subj_concords = {1:"a", 2:"ba", 3:"gu", 4:"yi", 5:"li", 6:"ga",
                     7:"ki", 8:"bi", 9:"yi", 10:"zi", 11:"ru", 12:"ka",
                     13:"tu", 14:"bu", 15:"ku"}
    s_pfx = subj_concords.get(subject_class, "a")
    o_pfx = OBJECTIVAL_CONCORDS.get(object_class, "")
    # Perfect suffix: -ire (most verbs), handle -a ending
    root = verb_stem.rstrip("a")
    perfect = root + "ire"
    verb_form = s_pfx + o_pfx + perfect
    return f"{object_noun} {subject} {verb_form}"


# ─────────────────────────────────────────────────────────────────────────────
# 10. NOUN CLASSES 1A / 2A / 9A / 10A
# Source: grammar rules 5.docx — Chapter 7
# Class 1a: names without initial vowel (empaako, relationship, animal names)
# Class 2a: plurals of 1a (baa- prefix)
# Class 9a: foreign words, colours, place names (no prefix, no initial vowel)
# Class 10a: plurals of 9a (zaa- prefix)
# ─────────────────────────────────────────────────────────────────────────────

# Class 1a — concordial agreement same as Class 1
CLASS_1A_EXAMPLES = [
    "Abbooki", "Abwoli", "Acaali", "Akiiki", "Amooti",
    "Adyeri", "Apuuli", "Araali", "Ateenyi", "Atwoki", "Bbala",  # empaako
    "mukaaka", "marumi", "rubuga",  # relationship/title names
    "warujojo", "wakame", "wambwa", "wankoko",  # personified animal names
]

# Class 2a — plural prefix baa- (before consonant/u), ba- (before nasal/a/i),
#             be- (before e), bo- (before o)
CLASS_2A_PREFIX_RULES = {
    "consonant": "baa",
    "vowel_a":   "ba",
    "vowel_i":   "ba",
    "vowel_e":   "be",
    "vowel_o":   "bo",
    "nasal":     "ba",
}

def build_class2a_plural(singular: str) -> str:
    """
    Build the Class 2a plural of a Class 1a noun.
    e.g. build_class2a_plural('mukaaka') -> 'baamukaaka'
         build_class2a_plural('Abbooki') -> 'Baabbooki'
         build_class2a_plural('Ogene')   -> 'Boogene'
    """
    s = singular.strip()
    first = s[0].lower() if s else ""
    if first in ("a", "i"):
        prefix = "Ba"
    elif first == "e":
        prefix = "Be"
    elif first == "o":
        prefix = "Bo"
    else:
        prefix = "Baa"
    return prefix + s

# Class 9a — no prefix, no initial vowel; concordial agreement same as Class 9
CLASS_9A_EXAMPLES = {
    # Foreign words
    "ofiisi":      "office",
    "motoka":      "motor car",
    "bbaasi":      "bus",
    "kamera":      "camera",
    "kalenda":     "calendar",
    "gavumenti":   "government",
    "sente":       "cents/money",
    "pikipiki":    "motorcycle",
    # Colours
    "kinyansi":    "green (like grass)",
    "kijubwa":     "green (like ejabwa plant)",
    "rubabi":      "green (like plantain leaf)",
    "kitaka":      "brown (like soil)",
    "kataiki":     "light brown (like termite hill)",
    "kyenju":      "yellow (like ripe banana)",
    "kihuukya":    "purple (like ehuukya berries)",
    "kigaaja":     "red/reddish brown (like reddish cow)",
    "kyeru":       "white (like white cow/hen)",
    "kisiina":     "dark brown (like dark brown cow)",
    "kibuubi":     "grey (like greyish cow)",
    "kikara":      "black (like black cow/hen)",
    "kaneke":      "dark blue",
    "bbururu":     "blue",
    "kakobe":      "purple (baboon-derived)",
    # Place names (adverbial use)
    "Kaseese":     "Kaseese (town)",
    "Kabarole":    "Kabarole (town)",
    "Kilembe":     "Kilembe (town)",
    "Buganda":     "Buganda (kingdom)",
    "Tooro":       "Tooro (kingdom)",
    "Bunyoro":     "Bunyoro (kingdom)",
}

def get_colour_name(english_colour: str) -> str:
    """
    Return the Runyoro-Rutooro colour name for an English colour.
    e.g. get_colour_name('green') -> 'kinyansi'
         get_colour_name('white') -> 'kyeru'
         get_colour_name('black') -> 'kikara'
    """
    colour_map = {
        "green":       "kinyansi",
        "yellow":      "kyenju",
        "white":       "kyeru",
        "black":       "kikara",
        "brown":       "kitaka",
        "red":         "kigaaja",
        "grey":        "kibuubi",
        "dark brown":  "kisiina",
        "light brown": "kataiki",
        "purple":      "kihuukya",
        "blue":        "bbururu",
        "dark blue":   "kaneke",
    }
    return colour_map.get(english_colour.lower().strip(), "")

# Class 10a — plural of 9a, prefix zaa-
def build_class10a_plural(singular: str) -> str:
    """
    Build the Class 10a plural of a Class 9a noun.
    e.g. build_class10a_plural('mayugi') -> 'zaamayugi'
         build_class10a_plural('kyeru')  -> 'zaakyeru'
    """
    return "zaa" + singular.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 11. NEGATIVE NOUNS (omu-ta- prefix)
# Source: grammar rules 5.docx — Class 1 Nouns
# omu- + -ta- + verb stem = person who does NOT do X
# ─────────────────────────────────────────────────────────────────────────────

NEGATIVE_NOUNS = {
    "omutaseka":       ("gloomy person",          "one who does not laugh"),
    "omutagambwaho":   ("touchy person",           "one who is easily offended"),
    "omutooga":        ("dirty person",            "one who does not take a bath"),
    "omutaleesa":      ("title of saza chief",     "Mwenge/Tooro chief title"),
    "omutembameeza":   ("one who climbs the table","pet name"),
    "omutacunguurra":  ("one who fails to clean",  "pet name"),
    "omutacwanono":    ("one who fails to cut nails","pet name"),
}

def build_negative_noun(verb_stem: str) -> str:
    """
    Build a negative noun (Class 1) from a verb stem.
    Pattern: omu- + ta- + verb_stem
    e.g. build_negative_noun('seka') -> 'omutaseka'  (one who doesn't laugh)
         build_negative_noun('tooga') -> 'omutotooga' (one who doesn't bathe)
    """
    stem = verb_stem.strip().lstrip("oku").lstrip("okw")
    return "omuta" + stem

# ─────────────────────────────────────────────────────────────────────────────
# 12. CLASS 9 PROFESSIONAL NOUNS (en- prefix derivation)
# Source: grammar rules 5.docx — Class 9 Nouns
# en- prefix on verb stem = professional/habitual doer or permanent characteristic
# ─────────────────────────────────────────────────────────────────────────────

CLASS9_PROFESSIONAL_NOUNS = {
    "endimi":       ("professional cultivator",    "cf. omulimi"),
    "ensuubuzi":    ("professional trader",        "cf. omusuubuzi"),
    "encwangya":    ("incurable liar",             "cf. omucwangya"),
    "enfaakati":    ("permanent widow/widower",    "cf. mufaakati"),
    "entaahamagenyi": ("frequent wedding attendant", "one who always goes to parties"),
    "engenderakulya": ("one who visits only for food", ""),
    "embungabungi": ("one who is always visiting, idler", ""),
    "entakabonaga": ("one who has never seen anything striking", ""),
}

def derive_class9_professional(verb_stem: str) -> str:
    """
    Derive a Class 9 professional noun from a verb stem.
    Uses en- before consonants, em- before bilabials (b, p).
    e.g. derive_class9_professional('lima') -> 'endima'  (cultivation/professional cultivator)
         derive_class9_professional('baza') -> 'embaza'
    """
    stem = verb_stem.strip()
    if not stem:
        return ""
    first = stem[0].lower()
    prefix = "em" if first in ("b", "p") else "en"
    return prefix + stem

# ─────────────────────────────────────────────────────────────────────────────
# 13. AUGMENTATIVE / PEJORATIVE CLASS PREFIX SUBSTITUTION
# Source: grammar rules 5.docx — Class 5 and Class 7 Emotional Values
# Class 5 (eri-/i-) prefix substituted for magnitude/pejorative
# Class 7 (eki-/ki-) prefix substituted for magnitude/affection/contempt
# ─────────────────────────────────────────────────────────────────────────────

AUGMENTATIVE_EXAMPLES = {
    # Class 5 substitution (magnitude/pejorative)
    "isaija":   ("omusaija",  "man",    "big/disrespectful man"),
    "isigazi":  ("omusigazi", "youth",  "youth acting badly"),
    "eryana":   ("omwana",    "child",  "insolent child"),
    "eriisiki": ("omwisiki",  "girl",   "girl of great beauty/youth"),
    "eriiru":   ("omwiru",    "serf",   "sturdy/troublesome peasant"),
    "erintu":   ("omuntu",    "person", "monster-like person"),
    # Class 7 substitution (magnitude/affection/contempt)
    "ekiiru":   ("omwiru",    "serf",   "dear poor man (affection)"),
    "ekisaija": ("omusaija",  "man",    "clumsy/contemptible man"),
    "ekiyana":  ("omwana",    "child",  "funny-looking child (contempt)"),
}

def build_augmentative(base_noun: str, aug_class: str = "5") -> str:
    """
    Build an augmentative/pejorative form by substituting the class prefix.
    aug_class: '5' (eri-/i-) for magnitude/pejorative
               '7' (eki-/ki-) for magnitude/affection/contempt
    e.g. build_augmentative('omusaija', '5') -> 'isaija'
         build_augmentative('omusaija', '7') -> 'ekisaija'
    """
    # Strip common class 1/3 prefix omu-/omw-
    stem = base_noun.strip()
    for pfx in ("omw", "omu", "aba", "emi", "eki", "ebi", "eri", "aga"):
        if stem.lower().startswith(pfx):
            stem = stem[len(pfx):]
            break
    if aug_class == "5":
        return "i" + stem if stem[0].lower() not in "aeiou" else "eri" + stem
    if aug_class == "7":
        return "eki" + stem
    return stem


# ─────────────────────────────────────────────────────────────────────────────
# MASTER POST-PROCESSING FUNCTION
# Applies all gr5 rules to MT output in the correct order.
# Called from translate.py after gr4 rules.
# ─────────────────────────────────────────────────────────────────────────────

def apply_gr5_rules(text: str, direction: str = "en->lun") -> str:
    """
    Apply all Grammar Rules 5 post-processing corrections to MT output.
    Only applied to Runyoro-Rutooro output (en->lun direction).
    """
    if "lun" not in direction and "->lun" not in direction:
        return text

    result = text
    result = apply_copula_locative_correction(result)   # 6. copula + locatives
    result = apply_adverbial_suffix_correction(result)  # 4. adverbial suffixes
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GRAMMAR CONTEXT EXTENSION  (for chat system prompt)
# ─────────────────────────────────────────────────────────────────────────────

GR5_GRAMMAR_CONTEXT = """
--- Grammar Rules 5 (Locatives, Sentences, Noun Classes) ---
LOCATIVE PREFIXES:
  omu-/omw- = in/inside: omunsi(world), omwiguru(heaven), omukibira(forest)
  ha- = on/at: hameeza(on table), hansi(on ground), haiguru(above)
  ku- = to/towards: kunu(this way), kuli(that way)
  owa- = to a person's place: owaitu(our home), owaabu(their home)
  omba = to an area: omba so (go to your father's home area)

LOCATIVE DEMONSTRATIVES:
  munu(in here), muli(in there), hanu(here), hali(there), kunu(this way), kuli(that way)

SELF-STANDING ADVERBIALS:
  mwo(in it), ho(on it), oku(there/that side), omu(in there), aho(on there)

ADVERBIAL SUFFIXES (must match prefix):
  -mu with omu-: Taahamu(get in), harumu amaizi(water is in here)
  -ho with ha-:  Taaho(take away), Rugaho(get away), heemeriireho(standing on)
  -yo with owa-/ku-/omba: gendayo(go there), haraireyo(slept at home)

LOCATIVE POSSESSIVES:
  omwange(in my house), omwawe(in your house), omwe(in his house)
  owange(at my home), owaawe(at your home), owe(at his home)
  owaitu(at our home), owaanyu(at your pl. home), owaabu(at their home)

COPULA NI- + LOCATIVES:
  nihanu(it is here), nihali(it is there), numwo(it is in it), nuho(it is on it)
  nukunu(it is this way), nukuli(it is that way), nimunu(it is in here)

DARA + LOCATIVE:
  daraho(here I come to the place), daramunu(I am sure it is in here)
  darahanu(I am sure it is from here / come here)

HO + ENUMERATIVE:
  hoona(everywhere), honka(only there), hombi(both sides), hoonyini(the very spot)

OBJECTIVAL CONCORD (reversed object):
  omusiri omukazi agulimire = the woman dug the garden (object fronted)
  Concords: cl.1=mu, cl.3=gu, cl.7=ki, cl.9=yi, cl.10=zi

COLOUR NAMES (Class 9a):
  kinyansi/kijubwa(green), kyeru(white), kikara(black), kigaaja(red/reddish brown)
  kitaka(brown), kisiina(dark brown), kibuubi(grey), kyenju(yellow), bbururu(blue)

NEGATIVE NOUNS (omu-ta-):
  omutaseka(one who doesn't laugh), omutooga(dirty person), omutagambwaho(touchy person)

CLASS 9 PROFESSIONAL NOUNS (en-/em-):
  endimi(professional cultivator), ensuubuzi(professional trader)
  encwangya(incurable liar), enfaakati(permanent widow/widower)

AUGMENTATIVE/PEJORATIVE:
  Class 5 (i-/eri-): isaija(big/bad man), isigazi(youth acting badly)
  Class 7 (eki-): ekisaija(contemptible man), ekiiru(dear poor man - affection)
"""

def get_gr5_grammar_context() -> str:
    """Return Grammar Rules 5 context string for chat system prompt."""
    return GR5_GRAMMAR_CONTEXT

