"""
Additional Runyoro-Rutooro grammar rules extracted from OCR data.
Sources: Grammar Ch.8, Ch.9, Ch.10, Ch.11, Ch.13, Ch.14, Ch.15, Ch.16,
         Runyoro-Rutooro Orthography Guide (1995)
Imported by language_rules.py
"""

# ─────────────────────────────────────────────────────────────────────────────
# OFFICIAL ORTHOGRAPHY RULES (Rules 1-27)
# Source: Runyoro-Rutooro Orthography Guide, Ministry of Gender, Uganda, 1995
# ─────────────────────────────────────────────────────────────────────────────

ORTHOGRAPHY_RULES = {
    1: "Alphabet: 5 vowels (a,e,i,o,u) + 19 consonants (b,g,d,f,h,j,k,l,m,n,p,r,s,t,v,w,y,z). "
       "Letters q, v, x absent. c used without h.",
    2: "c always used without h. Examples: icumu (spear), omuceeri (rice), okucika (to discuss).",
    3: "l used only before ya/ye/yo and after e/i. Examples: okulya (to eat), omulango (doorway).",
    4: "r used in all other positions where l is not used. Examples: omuceeri, okumira, omusiri.",
    5: "Double consonants: bb=non-bilabial fricative b (ibbango=hump). "
       "mm/nn doubled when object prefix m/n precedes verb starting with m/n "
       "(niimmanya=I know, mmanyire=I know [perfect]).",
    6: "ia/ie/io used with n only (omuniania, omuniongorozi). "
       "ya/ye/yi/yo/yu used with n and other letters (omunya, enyegesa).",
    7: "Long vowels written double (aa,ee,ii,oo,uu). "
       "Grammatical: prefix+vowel-initial stem merges last vowel of prefix with first vowel of stem "
       "(aba+ana=abaana, aka+ato=akaato). "
       "Tense: tense prefix+vowel-initial stem (ni+ija=niija). "
       "Accent: some words have inherently long vowels.",
    8: "Vowels before nasal+consonant combinations are NOT doubled "
       "(okugamba, enyanja, okucumba — NOT okuugamba).",
    9: "w used before a/o/u; y used before e/i. "
       "Examples: w: orwoma (wire), okutwara; y: ekyohyo, okulyeryesa.",
    10: "Prenasals (mb,nd,nt,ng,nk,nj,nc) written as single units. "
        "Vowels before prenasals are long but only doubled before nasal+nasal (mm,nn).",
    11: "ny follows general vowel rule (niinyata, niinyeeta, amanyire).",
    12: "Collective proper names written as one word starting with capital (Baayozefu, Zaakitale).",
    13: "Object relative written separately from subject prefix of verb it precedes.",
    14: "Prepositions/conjunctions written separately from word they precede, "
        "except omu and aha. Elision before a/e/o marked with apostrophe.",
    15: "Possessives written separately from word they precede/follow. "
        "Elision before a/e/o (or li-ma class words starting with i) marked with apostrophe.",
    16: "Adverbs and conjunctions written as one word "
        "(habwokuba=because, kakuba=if, nambere=where, noobu=even if).",
    17: "Affirmative copula ni joined to pronoun it precedes (niinyowe=it is I, niiwe=it is you).",
    18: "Negative copula tali/tibali/tihali separated from word it precedes "
        "unless adverbial suffix (tali musaija, tibali babi).",
    19: "Special copula forms: tihaliyo (nothing there), tiharoho (nothing), murungiho (rather good).",
    20: "ka separated from word it precedes; kwo from word it follows. "
        "ka before a/e/o: apostrophe used (ka niiwe, ka niinyowe).",
    21: "Adverbial suffixes -ho, -yo, -mu, -ko written joined to word they follow.",
    22: "Negative particle ti joined to verb (tinigenda, tinkagenzire).",
    23: "Subject prefix joined to verb stem.",
    24: "Foreign words written as commonly pronounced by Banyoro/Batooro "
        "(bbulangiti=blanket, sukaali=sugar, ekooti=coat, sente=cent, Sande=Sunday).",
    25: "Place names written as one word with capital letter.",
    26: "Particle nya joined to noun it precedes (nyamukazi, nyamusaija, nyakaana).",
    27: "Names of people: spelling left to individual. For writing purposes, "
        "books write names as they are commonly known.",
}


# ─────────────────────────────────────────────────────────────────────────────
# GENITIVE PARTICLES (Chapter 8) — DETAILED
# Source: Grammar Ch.8 — Genitive particles and nya- in combination
# ─────────────────────────────────────────────────────────────────────────────

# The 7 genitive particles: owa, aba, ekya, ebya, eza, aka, obwa
# Added to nouns/phrases to denote relationship, place, animal names, etc.

GENITIVE_PARTICLE_OWA = {
    "form": "owa-",
    "class": 1,
    "usage": [
        "Kinship/relationship nouns (owanyinentoitwe=our maternal aunt's child)",
        "Adverbial pronouns of place (owaitu=at our home)",
        "Possessive for class 1 nouns",
    ],
    "kinship_examples": {
        "owanyinentoitwe": "our maternal aunt's child",
        "owaisenyowe":     "my step brother / paternal uncle's child",
        "owaisiitwe":      "our step brother / paternal uncle's child",
        "owaisemuntu":     "child born by a paternal uncle",
        "owanyinamuntu":   "one's brother or sister",
    },
}

GENITIVE_PARTICLE_EBY = {
    "form": "ebya-",
    "class": 8,
    "usage": "home/domestic affairs, requirements",
    "examples": {
        "ebyomunju":  "house requirements",
        "ebyamaka":   "home gods",
        "ebyomumaka": "home affairs",
        "ebyenjoka":  "food given to children after death of parent (clan protection ritual)",
    },
}

GENITIVE_PARTICLE_EYA = {
    "form": "eya-",
    "class": 9,
    "usage": "denotes animals in respect of place, time, or characteristic",
    "examples": {
        "eyahaiziba": "animal (snake/leopard/etc.) living at a public well",
    },
}

GENITIVE_PARTICLE_AGA = {
    "form": "aga-",
    "class": 6,
    "proverb_example": "Ag'okwihuka gatengeeta — Rather have shaky teeth than nothing.",
}

GENITIVE_PARTICLE_ORWA = {
    "form": "orwa-",
    "class": 11,
    "example": "rw'okwota — of warming (by fire)",
}

GENITIVE_PARTICLE_KYA = {
    "form": "kya-",
    "class": 7,
    "cow_name_examples": {
        "Kyakitale":      "milk cow born of Kitale (the white cow)",
        "Kyanjumba":      "of Njumba, the reddish cow",
        "Kyabihogo":      "of Bihogo, the red cow",
        "Kyankarabo":     "of Nkarabo, the dark grey cow",
        "Kyakyarutasemba":"cow born of a cow born of Rutasemba",
    },
    "usage_magnitude": "kya- used for magnitude, excessiveness, ugliness, dislike or sympathy",
}

GENITIVE_PARTICLE_OBWA = {
    "form": "obwa-",
    "class": 14,
    "note": "Bwamusana/Bwanswa belong to Class 1a (not class 14), plural in Class 2a",
    "examples": {
        "Bwamusana": "thing of daylight (Class 1a, pl. Baabwamusana)",
        "Bwanswa":   "of the termites (Class 1a, pl. Baabwanswa)",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# NYA- PARTICLE — DETAILED
# Source: Grammar Ch.8 — The particle nya-
# ─────────────────────────────────────────────────────────────────────────────

NYA_PARTICLE_DETAILED = {
    "form": "nya- (pre-prefix or infix)",
    "meanings": ["of", "who", "the one that"],
    "usages": {
        "habits_behaviour": {
            "desc": "People's habits, behaviour, characteristics",
            "examples": {
                "nyamukazi":  "the woman (that specific woman)",
                "nyamusaija": "the man (that specific man)",
                "nyakaana":   "the child (that specific child)",
            },
        },
        "times_effects": {
            "desc": "Times and effects (adverbs and nouns in Class 9, no plural)",
            "examples": {
                "nyalimu":      "once",
                "enyakabiri":   "two times",
                "nyakasatu":    "three times",
                "enyakana":     "four times",
                "nyakataano":   "five times",
                "enyakaara":    "effects of being touched many times",
                "enyakanyansi": "effect of smelly grass in beer-squeezing",
                "enyakaizi":    "effect of too much water in a mixture",
            },
            "note": "nyamukaaga, nyamusanju etc. do NOT exist",
        },
    },
    "orthography_rule": "Rule 26: nya joined to noun it precedes (nyamukazi, nyamusaija)",
}


# ─────────────────────────────────────────────────────────────────────────────
# -NYAKU-, -OWA-, -EYA- PARTICLES IN RELATIVE PHRASES
# Source: Grammar Ch.15 — Compound tenses, relative phrases
# ─────────────────────────────────────────────────────────────────────────────

RELATIVE_PHRASE_PARTICLES = {
    "-nyaku-": {
        "tenses": ["present-indefinite", "present-perfect", "near-past"],
        "usage": "distinguishes relative phrase from direct phrase in these tenses",
        "note": "For classes 1, 4, 9 the initial vowel rule does not apply "
                "because their pronominal concords already consist of a vowel",
        "examples": {
            "nyakumwegesa aliija": "the teacher who will come",
            "nyakuinte erizaara":  "the cow which will produce",
        },
    },
    "-owa-": {
        "tenses": ["near-future"],
        "usage": "marks relative phrase in near-future tense",
        "examples": {
            "owaaraakulyaho ebyawe": "the one who will eat your things (near future)",
        },
    },
    "-eya-": {
        "tenses": ["far-future", "other tenses"],
        "usage": "marks relative phrase in far-future and other tenses",
    },
    "general_rule": (
        "To form a subject relative concord an initial vowel must be added to "
        "the pronominal concord. For classes 1, 4, 9 this rule does not apply "
        "because their concords already consist of a vowel."
    ),
}

# Subject relative concords (full forms with initial vowel)
SUBJECT_RELATIVE_CONCORDS_FULL = {
    1:  "a-",
    2:  "aba- (abe-, abo-, ab-)",
    3:  "ogu- (ogw-)",
    4:  "e- (i-, ey-)",
    5:  "eri- (ery-)",
    6:  "aga- (age-, ago-, ag-)",
    7:  "eki- (eky-)",
    8:  "ebi- (eby-)",
    9:  "e- (i-, y-)",
    10: "ezi- (i-, za-, ze-, zo-, z-)",
    11: "oru- (orw-)",
    12: "aka- (ake-, ako-, ak-)",
    13: "utu- (utw-)",
    14: "obu- (obw-)",
    15: "oku- (okw-)",
}

# Elision of subject relative concord
RELATIVE_CONCORD_ELISION = (
    "The initial vowel of the subject relative concord is often dropped after "
    "the noun it represents, unless emphasis is necessary. "
    "Example: Omukono gwatiire engoma tiguhunga nzige "
    "(The hand which beat the drum [royal drum] does not make the locusts flee)."
)


# ─────────────────────────────────────────────────────────────────────────────
# PRONOMINAL ROOTS & COPULA NI-
# Source: Grammar Ch.4 — Words and affixes
# ─────────────────────────────────────────────────────────────────────────────

PRONOMINAL_ROOTS = {
    "personal": {
        "1sg": "-nge (my, mine)",
        "2sg": "-we (your, yours)",
        "3sg": "-e (his/her/hers)",
        "1pl": "-itu (our, ours)",
        "2pl": "-nyu (your, yours)",
    },
    "self_standing": {
        "1sg": "Nyowe (I)",
        "2sg": "Iwe (You)",
        "3sg": "Uwe (He/She)",
        "1pl": "Itwe (We)",
        "2pl": "Inywe (You pl)",
    },
    "demonstrative": {
        "-nu": "this, these",
        "-li": "that, those",
    },
    "exclusive_enumerative": {
        "-enka / -onka": "alone, self, selves / only, self, selves",
        "-ena / -ona":   "all of me/us/you / all of it or them",
        "-embi / -ombi": "both",
    },
}

# Copula ni- distribution rules
COPULA_NI_RULES = {
    "usage": [
        "In questions before interrogative root -ha? (who?, which?)",
        "In answers to such questions",
        "Before demonstratives and interrogatives with -ha",
        "Before self-standing pronouns (niinyowe=it is I, niiwe=it is you)",
    ],
    "sound_change": "ni + vowel -> long vowel (ni+iwe=niiwe, ni+inyowe=niinyowe)",
    "examples": {
        "niinyowe":  "it is I",
        "niiwe":     "it is you",
        "nuwe":      "it is he/she",
        "niitwe":    "it is we",
        "niinywe":   "it is you (pl)",
        "nubo":      "it is they",
        "nugwo":     "it is it (cl.3)",
        "nuyo":      "it is it (cl.9)",
        "nulyo":     "it is it (cl.5)",
        "nugo":      "it is it (cl.6)",
        "nukyo":     "it is it (cl.7)",
        "nubyo":     "it is it (cl.8)",
        "nuzo":      "it is it (cl.10)",
        "nurwo":     "it is it (cl.11)",
        "nuko":      "it is it (cl.12)",
        "nutwo":     "it is it (cl.13)",
        "nubwo":     "it is it (cl.14)",
        "nukwo":     "it is it / that is it (cl.15)",
    },
    "with_demonstratives": {
        "noonu": "it is this one",
        "nooli": "it is that one",
        "nibanu": "it is these ones",
        "nibali": "it is those ones",
        "nugunu": "it is this one",
        "nguli":  "it is that one",
    },
}

# ka particle (exclusion/restriction)
KA_PARTICLE = {
    "meaning": "it is not any other ... but",
    "rule": "ka separated from word it precedes; apostrophe before a/e/o",
    "examples": {
        "ka niiwe":   "it is you (and no one else)",
        "ka niinyowe":"it is I (and no one else)",
        "ka nugwo":   "it is not any other ... but that one",
        "ka noonu":   "it is not any other person but this one",
        "ka nooli":   "it is not any other person but that one",
    },
}

# Names of relationship
NAMES_OF_RELATIONSHIP = {
    "ise":        "his/her father",
    "nyina":      "his/her mother",
    "isenkuru":   "his/her grandfather",
    "nyinenkuru": "his/her grandmother",
    "isenkati":   "his/her paternal aunt",
    "nyinento":   "his/her maternal aunt",
    "nyinarumi":  "his/her maternal uncle",
    "isento":     "his/her paternal uncle",
    "note": (
        "These express relationship for 3rd person singular. "
        "When added to self-standing pronouns they lose original meaning and "
        "take on the meaning of the pronoun. "
        "Orthography: names of relationship written as one word with the pronoun."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# LOCATIVES (Chapter 5)
# Source: Grammar Ch.5 — Formation of locatives
# ─────────────────────────────────────────────────────────────────────────────

LOCATIVE_PREFIXES = {
    "omu- (omw-)": {
        "meaning": "in, inside, into",
        "examples": {
            "omukibira":    "in the forest",
            "omunziha":     "where the water is deeper",
            "omumaiso":     "in front",
            "omunda":       "inside",
            "omwitumbi":    "at midnight",
        },
    },
    "ha-": {
        "meaning": "at, on, near (specific location)",
        "examples": {
            "hameeza":   "on the table",
            "haiguru":   "on top / above",
            "hansi":     "below / down",
            "harubaju":  "aside",
            "haruguru":  "on top",
            "haifo":     "downwards",
        },
    },
    "ku-": {
        "meaning": "to, at, on (direction/general location)",
        "examples": {
            "kukibira":  "to the forest",
            "kurungiho": "rather well",
        },
    },
    "owa- (owa)": {
        "meaning": "at the home/place of",
        "examples": {
            "owaitu":    "at our home",
            "owaawe":    "at your place",
            "owabugwo":  "at its place",
        },
    },
    "omba-": {
        "meaning": "both sides",
        "examples": {
            "hombi": "both sides (ha + ombi)",
        },
    },
}

# Locative demonstratives
LOCATIVE_DEMONSTRATIVES = {
    "munu":  "in here (mu + nu)",
    "muli":  "in there (mu + li)",
    "hanu":  "here (ha + nu)",
    "hali":  "there (ha + li)",
    "kunu":  "to here (ku + nu)",
    "kuli":  "to there (ku + li)",
}

# Adverbials -mwo and -ho
ADVERBIAL_SUFFIXES = {
    "-ho": "there, at that place (attached to word)",
    "-yo": "there, at that place (class 9/10)",
    "-mu": "in it, therein",
    "-ko": "at it, thereon (class 12)",
    "note": "Rule 21: adverbial suffixes written joined to word they follow",
    "examples": {
        "tihaliyo":  "there is nothing there",
        "tiharoho":  "there is nothing",
        "tiharumu":  "there is nothing in it",
        "murungiho": "rather good",
        "kurungiho": "rather well",
    },
}

# Possessives for locative classes
LOCATIVE_POSSESSIVES = {
    "omwabugwo":  "in its place (mongoose)",
    "omwabuyo":   "in their place (mongooses)",
    "owaabugwo":  "at its place",
    "owaabuyo":   "at their place",
}


# ─────────────────────────────────────────────────────────────────────────────
# COLLECTIVE NOUNS
# Source: Grammar Ch.10 — Some more information about nouns
# ─────────────────────────────────────────────────────────────────────────────

COLLECTIVE_NOUNS = {
    "ekitebe":    "group",
    "igana":      "herd",
    "omuzinga":   "swarm",
    "eka":        "home, family",
    "oruganda":   "clan",
    "ihanga":     "country",
    "orukurato":  "council, parliament, meeting",
    "ihe":        "army",
    "note": (
        "Collective nouns are singular in form but stand for many individuals. "
        "They keep concordial agreement of their own class, not of the individuals."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# FIVE MOODS OF THE VERB
# Source: Grammar Ch.11 — The verb
# ─────────────────────────────────────────────────────────────────────────────

FIVE_MOODS = {
    "infinitive": {
        "desc": "Names an action without mentioning subject",
        "form": "oku- + stem (okugenda=to go, okulya=to eat)",
        "note": "Suffix -ga added to infinitive expresses habitual action",
    },
    "imperative": {
        "desc": "Commands",
        "singular_positive": "verb stem + -a (genda=go!, garuka=come back!)",
        "plural_positive":   "mu- + stem + -e (mugende=go! [pl])",
        "singular_negative": "ota- + stem + -e (otagende=don't go!)",
        "plural_negative":   "muta- + stem + -e (mutagende=don't go! [pl])",
    },
    "indicative": {
        "desc": "States facts, describes actions",
        "note": "Negative prefix ti- changes to t- before pronominal prefixes a- and o-",
    },
    "subjunctive": {
        "desc": "Expresses purpose, suggestion, wish",
        "form": "stem + -e (tuhe=give us, muhe=give him/her, oije=come)",
        "negative": "ota- + stem (otatuha=don't give us, otamuha=don't give him)",
        "note": "Closely related to imperative; often difficult to distinguish",
        "uses": [
            "To enable imperative to express various commands (Genda omwirwarro bakuhe omubazi)",
            "To express thought or suggestion (Mwimuke turuge hanu)",
        ],
    },
    "conditional": {
        "desc": "Expresses conditions and their consequences",
        "marker": "-ku- (conditional tense prefix)",
        "note": "See CONDITIONAL_CONSTRUCTIONS for full details",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PARTICIPLES AND AUXILIARY VERBS (Chapter 14)
# Source: Grammar Ch.14
# ─────────────────────────────────────────────────────────────────────────────

PARTICIPLES = {
    "present_imperfect": {
        "desc": "Verb in present-imperfect used with okuba or another verb",
        "function": "indicates state, manner of action, or time",
        "example": "Ababa nibalya (Those who are eating [at that time])",
    },
    "not_yet": {
        "desc": "Only negative form exists",
        "example": "Abaire atakaliire (He had not eaten yet)",
    },
    "virtual_present": {
        "desc": "Suggests something just happened or is about to happen",
        "example": "Akaija batakaizire (He came before they had arrived)",
    },
    "present_perfect": {
        "desc": "Completed action with present relevance",
        "example": "Nsangire atagenzire nagaruka (Finding he had not gone I came back)",
    },
}

AUXILIARY_VERBS = {
    "okuba": {
        "meaning": "to be",
        "role": "primary auxiliary for compound tenses; expresses required tense",
        "note": "In compound tenses, okuba expresses the tense; main verb stem is modified",
    },
    "okubanza": {
        "meaning": "to begin, to come first",
        "role": "used to form ordinals (preceded by genitive particle)",
    },
    "okugaruka": {
        "meaning": "to come back, return",
        "role": "auxiliary expressing return to action",
    },
    "okumanya": {
        "meaning": "to know, to realise",
        "role": "auxiliary in limited tenses (Akamanya yagenda = he realised and went)",
    },
    "okumalira": {
        "meaning": "to finish",
        "role": "auxiliary expressing completion (Amazirege yaija? = Did he after all come?)",
    },
    "okubaleka": {
        "meaning": "to let, allow",
        "role": "auxiliary (Baleke bagende = Let them go)",
    },
    "okubanza_wait": {
        "meaning": "to wait",
        "role": "Banza muleke enyamaiswa ije = Wait until the animal comes",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# NUMBERS — ORDINALS, FRACTIONS, DISTRIBUTIVES
# Source: Grammar Ch.4 — Words and affixes (numbers section)
# ─────────────────────────────────────────────────────────────────────────────

# Ordinals formed with okubanza preceded by genitive particle
ORDINALS = {
    "formation": "genitive_particle + okubanza (to come first)",
    "examples": {
        "owaakubanza":  "the first (class 1)",
        "ekyakubanza":  "the first (class 7)",
        "ebyakubanza":  "the first (class 8)",
    },
    "note": "Appropriate genitive particle depends on noun class",
}

# Fractions
FRACTIONS = {
    "1/2": "ekyakabiri kimu",
    "2/5": "ebyakataano bibiri",
    "6/7": "ebyamukaaga musanju",
    "note": "Initial vowel used when genitive particle begins the fraction",
}

# Distributives (formed by reduplication)
DISTRIBUTIVES = {
    "formation": "reduplicate the number",
    "examples": {
        "babiri babiri":       "two by two (Abantu bazina babiri babiri = People dance two by two)",
        "musanju musanju":     "seven and seven (take seven and seven of each clean beast)",
    },
    "alternative": "buli + number (buli = each/every)",
}

# Hundreds/thousands connection
NUMBER_CONNECTORS = {
    "mu": "connects hundreds and additional figures (bibiri mu asatu = two hundred and thirty)",
    "na": "connects tens and units (asatu na itaano = thirty-five)",
    "note": "mu may be omitted (emiti rukumi bina n'ataano = 1450 trees)",
}

# Numeral concords for classes (numbers 1-5 must agree)
NUMERAL_CONCORD_DETAILS = {
    "note": "Numeral concords for 1-5 same as pronominal concords except classes 1 and 6",
    "counting": "In mere counting, numeral 1 takes concord for class 9; numerals 2-5 take class 9 concord",
    "class_examples": {
        10: "ente ibiri (two cows)",
        11: "orubabi rumu (one plantain leaf)",
        12: "otubeba tusatu (three little rats)",
        13: "akooya kamu (one piece of hair)",
        14: "obwato bumu (one boat)",
        15: "okwezi kumu (one month/moon)",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# ADJECTIVES — DETAILED (Chapter 16)
# Source: Grammar Ch.16 — Adjectives and adverbs
# ─────────────────────────────────────────────────────────────────────────────

# Types of words that qualify nouns in Runyoro-Rutooro
ADJECTIVE_TYPES = {
    "true_adjectives":          "e.g. omurungi (good), omubi (bad), omunene (big)",
    "nouns_as_qualifiers":      "nouns used to qualify other nouns (omukazi omulimi = a woman capable of digging)",
    "possessive_nouns":         "possessive constructions",
    "relative_present_imperfect": "relative phrases in present-imperfect tense",
    "relative_present_perfect": "relative phrases in present-perfect tense",
    "pronouns":                 "pronouns used as qualifiers",
    "numerals":                 "numerals as qualifiers",
}

# Relative phrases as adjectives
RELATIVE_ADJECTIVE_EXAMPLES = {
    "present_imperfect": {
        "Amaizi agarukufuka":    "cold water",
        "Ente ezirukwiragura":   "black cows",
        "Ekitabu ekirukwera":    "Holy Bible",
    },
    "present_perfect": {
        "Ipaapali eryengere":    "ripe pawpaw",
        "Omucunguuha ogwanire":  "orange tree with fruits on it",
        "Omuhanda ogugalihire":  "wide path",
        "Okuguru okuzimbire":    "swollen leg",
        "Empisi ekereriirwe":    "a hyena leaving the village late",
    },
}

# Adverbs — detailed
ADVERB_TYPES = {
    "manner":  "how action is done",
    "place":   "where action occurs",
    "time":    "when action occurs",
}

# Adverbs formed with bu- prefix
BU_ADVERBS = {
    "formation": "bu- attached to noun stems (size/quality) or adjectival/verb roots",
    "examples": {
        "bwemi":   "upright (from obwemi = height)",
        "bukiika": "crosswise (from obukiika = width)",
        "bugazi":  "flat (from obugazi = width)",
        "bwangu":  "quickly (from obwangu)",
    },
    "sentence_examples": {
        "Emeriire bwemi":   "is standing upright",
        "Teho bukiika":     "put it crosswise",
        "Aswire bugazi":    "has fallen flat",
        "Areete bwangu":    "bringing it quickly",
    },
}

# Adverbs of place
ADVERBS_OF_PLACE = {
    "hoonahoona":       "everywhere",
    "Bugwaizooba":      "west",
    "Burugaizooba":     "east",
    "nambere":          "where",
    "omumaiso ga":      "in front of something",
    "haiguru ya":       "on top of",
    "enyuma ya":        "behind something",
    "hansi ya":         "at the bottom of",
}

# Adverbs of time
ADVERBS_OF_TIME = {
    "itumbi":   "midnight",
    "ihangwa":  "dawn",
    "note": "omu- prefix may mark a particular time (Akaija omwitumbi = He came at midnight)",
}

# Verbal constructions implying action and manner
VERBAL_MANNER_EXPRESSIONS = {
    "Ruhweza airuka":          "Ruhweza runs fast",
    "Akaija atabijwaire":      "He came in a great panic (lit. he came without a dress)",
    "Kabonesa azina":          "Kabonesa sings nicely",
    "Omwana we amuraizeege kitabubukiizi": "His child made him feel better with a book",
}


# ─────────────────────────────────────────────────────────────────────────────
# DERIVATIVE VERBS — ADDITIONAL DETAILS (Chapter 12)
# Source: Grammar Ch.12 — Derivative verbs in particular
# ─────────────────────────────────────────────────────────────────────────────

# Prepositional verb — place/time/beneficiary extensions
PREPOSITIONAL_VERB_EXTENSIONS = {
    "place": {
        "desc": "place where action was/is/will be completed; for motion verbs: direction",
        "examples": {
            "Omukazi tabohera bintu mukisiika": "A woman does not pack things in the inner sitting room",
            "Enyama bagitematemera hakiti":     "People cut meat into pieces on a piece of wood",
            "Bakairukira omukibira":            "They took refuge in the forest",
        },
    },
    "time": {
        "desc": "time taken to have something done or time by which it must be done",
    },
    "beneficiary": {
        "desc": "action done for/on behalf of someone",
        "stem_extension": "okutemera -> okutemeerra (cut for, with reference to place)",
        "example": "Yagutemera omugurusi (He felled it for an old man)",
    },
}

# Prepositional verbs ending in -ra: continuative/durative/repetitive
PREPOSITIONAL_RA_VERBS = {
    "desc": "Prepositional verbs in -ra replace last vowel with -iza/-eza for continuative action",
    "examples": {
        "okusekera":   ("okulegereza", "to keep on reporting"),
        "okufeera":    ("okufeereza",  "to cause someone to lose something"),
        "okulegera":   ("okulegereza", "to keep on reporting"),
        "okusekera":   ("okusekereza", "to laugh at"),
    },
}

# Passive verb — applied/prepositional passives
PASSIVE_APPLIED = {
    "formation": "passives in -ibwa/-ebwa replace -ibwa/-ebwa with -irizibwa/-zebwa",
    "examples": {
        "okubyamibwa":    "okubyamirizibwa (to be laid...)",
        "okugonzebwa":    "okugonderezebwa (to be loved...)",
        "okubazibwa":     "okubalirizibwa (to be talked...)",
    },
}

# Causative — double causative
DOUBLE_CAUSATIVE = {
    "desc": "Some verbs have two causative forms (primary and secondary agent)",
    "examples": {
        "haba (go astray)":  {"causative1": "habya (primary agent)", "causative2": "habisa (secondary agent)"},
        "yoga (bathe)":      {"causative1": "yogya",                 "causative2": "yogesa"},
        "-aka (burn)":       {"causative1": "-akya",                 "causative2": "-akisa"},
        "nyaga (plunder)":   {"causative1": "nyagisa",               "causative2": "nyagisisa"},
        "leka (leave)":      {"causative1": "lekesa",                "causative2": "lekesisa"},
        "baza (speak)":      {"causative1": "bazisa",                "causative2": "bazisisa"},
    },
}

# Reduplicated verb stems
REDUPLICATED_VERBS = {
    "prolongation": {
        "desc": "Expresses prolongation of action",
        "example": "okusekaseka (to laugh at any time without stopping) from okuseka (to laugh)",
    },
    "diminution": {
        "desc": "Expresses diminution of force / slightly done",
        "example": "okulimalima (to dig lightly) from okulima (to dig)",
    },
    "variations": {
        "desc": "Some reduplicated stems are just variations of simple verbs",
        "examples": {
            "okumagamaga":  "to look about, look from side to side, be inattentive",
            "okuhahamuka":  "to run off in a fright, flee",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# VERB INFLECTIONAL CHANGES (Chapter 11)
# Source: Grammar Ch.11 — The verb
# ─────────────────────────────────────────────────────────────────────────────

# Verb okusara example of all inflectional changes
VERB_INFLECTION_EXAMPLE = {
    "infinitive": "okusara (to cut)",
    "forms": {
        "sara":    "direct command",
        "osale":   "command at second hand",
        "sazire":  "perfect participle",
        "saarra":  "applied form",
        "saza":    "causative form",
        "sarwa":   "passive form",
    },
}

# Perfect tense formation — polysyllabic stems ending in -ta
PERFECT_TA_STEMS = {
    "rule": "change -ta into -sire or -sere as sound change allows",
    "examples": {
        "teta (be patted, begin to talk)": "tesire",
        "gota (besiege)":                  "gosere",
    },
}

# Perfect tense — other disyllabic stems
PERFECT_OTHER_STEMS = {
    "rule": "change final -a to -ire or -ere as sound change allows",
    "examples": {
        "soba (be wrong, defective)": "sobire",
        "diida (criticise)":          "diizire",
        "leka (leave)":               "lekire",
        "zaana (play)":               "zaine",
        "raara (lodge)":              "raire",
        "huura (thresh corn)":        "hwire",
        "hoora (revenge)":            "hoire",
    },
}

# Passive form table
PASSIVE_FORM_TABLE = {
    "ha (give)":          {"passive": "heebwa",  "perfect": "-haire"},
    "ewa (break)":        {"passive": "cwibwa",  "perfect": "-cwire"},
    "lya (eat)":          {"passive": "liibwa",  "perfect": "-liire"},
    "tonda (identify)":   {"passive": "tondwa",  "perfect": "-tonzire"},
    "semeza (make clean)":{"passive": "semezebwa","modified_passive": "-semeziibwe"},
    "sekesa (make laugh)":{"passive": "sekesebwa","modified_passive": "-sekesiibwe"},
    "byamya (lay down)":  {"passive": "byamibwa", "modified_passive": "-byamiibwe"},
}

# Intransitive verbs used transitively
INTRANSITIVE_TRANSITIVE = {
    "note": "Many derivative verbs have transitive meanings though not normally transitive",
    "examples": {
        "Newijagiire oturo turungi":           "I slept soundly",
        "Ngenzire oruhanda rutali rurungi":    "I travelled a journey of misfortune",
        "Akantabaara ntaina kintu mukozire":   "He attacked me for nothing",
    },
    "derivative_transitive": [
        "okusekera omuntu (to laugh at a person)",
        "okurwaza omurwaire (to make a sick person sicker)",
        "okugonzera omuntu (to love a person)",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# SENTENCES (Chapter 6)
# Source: Grammar Ch.6 — Sentences
# ─────────────────────────────────────────────────────────────────────────────

SENTENCE_STRUCTURE = {
    "basic": "Subject (noun/pronoun) + Predicate (verb)",
    "example": "embwa ziboigora (Dogs bark) — subject: embwa, predicate: ziboigora",
    "note": "Verbs okuba and -li are often omitted but understood",
}

SENTENCE_TYPES = [
    "subject (noun/pronoun) + verb",
    "subject + verb + object",
    "subject + verb + complement",
    "subject + verb + adverbial",
    "subject + copula + predicate noun",
    "subject + copula + predicate adjective",
    "subject + copula + adverbial",
    "subject + verb + object + complement",
    "extension of predicate alone",
]

# Verb forms after self-standing pronouns without copula ni-
VERB_AFTER_PRONOUN = {
    "positive_relative": {
        "abarukukora":  "those who are working",
        "abaakozire":   "those who worked",
    },
    "negative_relative": {
        "abatarukukora": "those who are not working",
        "abatakole":     "those who did not work",
    },
    "note": "Pronominal prefixes/concords come after self-standing pronouns without copula ni-",
}

# Negative copula ni- in questions
NEGATIVE_COPULA_QUESTIONS = {
    "Tinibo baayangire?":   "Is it not they who refused?",
    "Tinikyo kyandesire?":  "Is it not that that I came for?",
    "note": "Use of negative copula ni- is common in questions",
}

# ─────────────────────────────────────────────────────────────────────────────
# FOREIGN WORDS (Orthography Rule 24)
# Source: Runyoro-Rutooro Orthography Guide, Part IV
# ─────────────────────────────────────────────────────────────────────────────

FOREIGN_WORDS = {
    "bbulangiti":  "blanket",
    "sukaali":     "sugar",
    "ebbeeseni":   "basin",
    "ekooti":      "coat",
    "efulaano":    "flannel",
    "esaati":      "shirt",
    "Omungereza":  "English (person)",
    "kamera":      "camera",
    "Omufaransa":  "French (person)",
    "sente":       "cent",
    "Omucaina":    "Chinese (person)",
    "sooda":       "soda",
    "peeterooli":  "petrol",
    "busiki":      "whisky",
    "bbururu":     "blue",
    "Sande":       "Sunday",
    "etikiti":     "ticket",
    "bbaasi":      "bus",
    "stookingi":   "stockings",
    "rule": "Written as commonly pronounced by Banyoro and Batooro",
}

# ─────────────────────────────────────────────────────────────────────────────
# IMPORT INTO MAIN language_rules.py
# ─────────────────────────────────────────────────────────────────────────────
# To use these rules, add to language_rules.py:
#   from language_rules_extra import *
