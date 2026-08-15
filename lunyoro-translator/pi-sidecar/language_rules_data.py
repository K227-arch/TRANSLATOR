"""
Language rules data for the Pi sidecar.
Extracted from the main backend's language_rules.py — contains all the
grammar constants needed by the /language-rules endpoint.
"""

RL_RULE = (
    "R/L Rule: In Runyoro-Rutooro, 'R' is the dominant consonant. "
    "'L' is only used immediately before or after the vowels 'e' or 'i'. "
    "In all other positions 'R' is used instead of 'L'."
)

GRAMMAR_SUMMARY = (
    "Runyoro-Rutooro is a Bantu language spoken by the Bunyoro-Kitara and Tooro kingdoms "
    "in western Uganda. Key features: 15 noun classes with concordial agreement, "
    "agglutinative verb structure (subject-tense-object-stem-suffix), R/L phonological rule, "
    "vowel harmony, nasal assimilation, and a rich system of derivative verb extensions."
)


def apply_rl_rule(text: str) -> str:
    """Replace L with R except when adjacent to e, i, or y."""
    if not text:
        return text
    chars = list(text)
    result = []
    for i, ch in enumerate(chars):
        if ch not in ('l', 'L'):
            result.append(ch)
            continue
        prev = chars[i - 1].lower() if i > 0 else ''
        nxt = chars[i + 1].lower() if i < len(chars) - 1 else ''
        if prev in ('e', 'i', 'y') or nxt in ('e', 'i', 'y'):
            result.append(ch)
        else:
            result.append('R' if ch.isupper() else 'r')
    return ''.join(result)


EMPAAKO = {
    "Atwooki": "From Atwok — shining star. Given to a child born on a night with stars.",
    "Ateenyi": "From Ateng — beautiful. Given if parents believe the child is beautiful.",
    "Apuuli": "From Apul/Rapuli — a very lovely girl, center of attraction and love in the family.",
    "Amooti": "From Amot — princely, a sign of royalty. Mostly for sons and daughters of kings and chiefs.",
    "Akiiki": "From Ochii/Achii — the one who follows twins. Mostly for firstborns who bear responsibility for siblings.",
    "Adyeeri": "From adyee/odee — parents had failed to get a child and only got one after spiritual intervention.",
    "Acaali": "From Ochal — replica. Given to a child who resembled someone in the family or ancestors.",
    "Abaala": "From Obal/Abal — destroyer/warrior. Usually for sons of chiefs.",
    "Abbooki": "From Obok/Abok — beloved. Child born out of strong love between parents.",
    "Araali": "From Arali/Olal/Alal — lost. Given to the only surviving child after mother lost many children.",
    "Abwooli": "From Abwolo — 'I lied to you'. A woman who conceives but continues having periods.",
    "Okaali": "From 'kal' — royalty. Only for the King in Kitara customs.",
}

INTERJECTIONS = {
    "mawe": "expression of surprise, shock, admiration",
    "hai": "expression of surprise",
    "awe": "expression of surprise, shock",
    "bambi": "expression of sympathy, appreciation",
    "ai bambi": "expression of sympathy",
    "ee": "expression of surprise, admiration",
    "haakiri": "expression of satisfaction",
    "cucu": "expression of surprise",
    "mpora": "expression of sympathy",
    "leero": "expression of surprise, anger, fear, pleasure",
    "nyaburaiwe": "expression of appealing, pity for oneself",
    "nyaaburanyowe": "expression of pity, sadness",
    "mahano": "expression of surprise, shock, disappointment",
    "caali": "expression of kindness, appealing, admiration",
    "ndayaawe": "appealing to someone or swearing by mother's clan",
    "nyaaburoogu": "expression showing pity or admiration",
    "boojo": "expression of admiration, pity, appeal, disappointment or pain",
    "mara boojo": "expression of appealing",
    "ego": "expression of assurance, satisfaction",
    "nukwo": "expression of assurance, satisfaction, dissatisfaction",
    "manyeki": "expression of doubt",
    "nga": "expression of surprise, doubt, negation",
    "busa": "expression of negation",
    "nangwa": "expression of surprise, doubt, negation",
    "taata we": "expression of surprise, shock, pity",
    "Ruhanga wange": "my God — expression of surprise, shock, displeasure",
    "Weza": "indeed",
    "Weebale": "thank you",
    "hee": "expression of surprise, shock",
    "gamba": "expression of surprise",
    "dahira": "expression of surprise, disbelief — literally 'swear!'",
    "ka mahano": "expression of surprise, shock, disappointment",
    "ka kibi": "expression of surprise, pity — literally 'it is bad!'",
    "bbaasi": "enough!",
    "kooboine": "expression of pity",
}

IDIOMS = {
    "kuburorra mu rwigi": "leaving very early in the morning",
    "baroleriire ha liiso": "watching over a dying person",
    "kucweke nteho ekiti": "running as fast as possible",
    "kurubata atakincwa": "walking hurriedly and excitedly",
    "kugenda obutarora nyuma": "walking very fast and in a concentrated manner",
    "omutima guli enyuma": "dissatisfied, worried",
    "omutima guramaire": "dissatisfied, worried",
    "omutima gwezire": "satisfied, contented",
    "amaiso kugahanga enkiro": "waiting for somebody/something with anxiety",
    "kukwata ogwa timbabaine": "disappear quietly",
    "kwija naamaga": "arrive in panic and anxiety",
    "kutarorwa izooba": "too beautiful to be exposed",
    "kuteera akahuno": "effect of great surprise",
    "garama nkwigate": "talk carelessly",
    "amaiso ga kimpenkirye": "shamelessness",
    "maguru nkakwimaki": "as fast as possible",
    "kuseka ekihiinihiini": "laughing with great happiness",
}

NUMBERS = {
    1: "emu", 2: "ibiri", 3: "isatu", 4: "ina", 5: "itaano",
    6: "mukaaga", 7: "musanju", 8: "munaana", 9: "mwenda", 10: "ikumi",
    11: "ikumi nemu", 20: "abiri", 30: "asatu",
    40: "ana", 50: "atano", 60: "nkaaga", 70: "nsanju",
    80: "kinaana", 90: "kyenda",
    100: "kikumi", 200: "bibiri", 300: "bisatu", 400: "bina",
    1000: "rukumi", 1_000_000: "akakaikuru", 1_000_000_000: "akasirira",
}

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

NOUN_CLASSES = {
    "1": {"prefix": "omu-", "desc": "persons (singular)", "example": "omuntu (person)"},
    "2": {"prefix": "aba-", "desc": "persons (plural)", "example": "abantu (people)"},
    "3": {"prefix": "omu-", "desc": "trees, plants, body parts (sg)", "example": "omuti (tree)"},
    "4": {"prefix": "emi-", "desc": "trees, plants (plural)", "example": "emiti (trees)"},
    "5": {"prefix": "eri-", "desc": "augmentatives, body parts (sg)", "example": "eriiso (eye)"},
    "6": {"prefix": "ama-", "desc": "plural of class 5; liquids", "example": "amaiso (eyes)"},
    "7": {"prefix": "eki-", "desc": "things, diminutives (sg)", "example": "ekitabo (book)"},
    "8": {"prefix": "ebi-", "desc": "things (plural)", "example": "ebitabo (books)"},
    "9": {"prefix": "en-", "desc": "animals, foreign words (sg)", "example": "ente (cow)"},
    "10": {"prefix": "en-", "desc": "animals (plural)", "example": "ente (cows)"},
    "11": {"prefix": "oru-", "desc": "long/thin objects, languages", "example": "orunyoro (Runyoro language)"},
    "12": {"prefix": "aka-", "desc": "diminutives (sg)", "example": "akana (small child)"},
    "13": {"prefix": "utu-", "desc": "diminutives (pl)", "example": "utuana (small children)"},
    "14": {"prefix": "obu-", "desc": "abstract nouns", "example": "obuzima (life)"},
    "15": {"prefix": "oku-", "desc": "verbal infinitives", "example": "okugenda (to go)"},
}

CONCORDIAL_AGREEMENT = {
    "1": {"subject": "a-", "object": "-mu-", "adjective": "omu-", "demonstrative": "uyu"},
    "2": {"subject": "ba-", "object": "-ba-", "adjective": "aba-", "demonstrative": "aba"},
    "3": {"subject": "gu-", "object": "-gu-", "adjective": "omu-", "demonstrative": "ogwo"},
    "4": {"subject": "gi-", "object": "-gi-", "adjective": "emi-", "demonstrative": "egi"},
    "5": {"subject": "li-", "object": "-li-", "adjective": "eri-", "demonstrative": "eryo"},
    "6": {"subject": "ga-", "object": "-ga-", "adjective": "ama-", "demonstrative": "ago"},
    "7": {"subject": "ki-", "object": "-ki-", "adjective": "eki-", "demonstrative": "ekyo"},
    "8": {"subject": "bi-", "object": "-bi-", "adjective": "ebi-", "demonstrative": "ebyo"},
    "9": {"subject": "i-", "object": "-i-", "adjective": "en-", "demonstrative": "eno"},
    "10": {"subject": "zi-", "object": "-zi-", "adjective": "en-", "demonstrative": "ezo"},
    "11": {"subject": "ru-", "object": "-ru-", "adjective": "oru-", "demonstrative": "orwo"},
    "12": {"subject": "ka-", "object": "-ka-", "adjective": "aka-", "demonstrative": "ako"},
    "13": {"subject": "tu-", "object": "-tu-", "adjective": "utu-", "demonstrative": "utu"},
    "14": {"subject": "bu-", "object": "-bu-", "adjective": "obu-", "demonstrative": "obwo"},
    "15": {"subject": "ku-", "object": "-ku-", "adjective": "oku-", "demonstrative": "okwo"},
}

TENSES = {
    "present_imperfect": {"marker": "ni-", "example": "nigenda", "meaning": "is going"},
    "present_perfect": {"marker": "-ire", "example": "agenzire", "meaning": "has gone"},
    "recent_past": {"marker": "a-", "example": "nayara", "meaning": "just now I made the bed"},
    "remote_past": {"marker": "ka-", "example": "nkaara", "meaning": "I made the bed (remote)"},
    "future_immediate": {"marker": "ra-", "example": "ndaayara", "meaning": "I shall make the bed"},
    "future_remote": {"marker": "raa-", "example": "turaayara", "meaning": "we shall make the bed"},
    "conditional": {"marker": "-ku-", "example": "obaire okukora", "meaning": "if/when (conditional)"},
    "imperative_sg": {"marker": "stem-a", "example": "genda", "meaning": "go! (singular)"},
    "imperative_pl": {"marker": "mu-stem-e", "example": "mugende", "meaning": "go! (plural)"},
    "negative_present": {"marker": "ti-ni-", "example": "tinigenda", "meaning": "is not going"},
    "negative_perfect": {"marker": "tinka-", "example": "tinkagenzire", "meaning": "has not gone"},
}

VERB_SUFFIXES = {
    "-ire / -ere": "perfect tense",
    "-a": "simple present / infinitive base",
    "-aho": "completive (action done at a place)",
    "-anga": "habitual/frequentative",
    "-isa / -esa": "causative",
    "-ibwa / -ebwa": "passive",
    "-ana": "reciprocal (each other)",
    "-ura / -ora": "conversive/reversive (undo the action)",
    "-uka / -oka": "intransitive conversive",
    "-rra": "intensive/completive",
}

DERIVATIVE_SUFFIXES = {
    "causative": ["-isa", "-esa", "-ya"],
    "passive": ["-ibwa", "-ebwa", "-wa"],
    "reciprocal": ["-ana"],
    "reversive": ["-ura", "-ora", "-ula", "-ola"],
    "neuter": ["-uka", "-oka"],
    "intensive": ["-rra", "-rruka", "-rrura"],
    "applied": ["-era", "-ira"],
    "positional": ["-ama"],
}

CONJUNCTIONS = {
    "na": "and / with",
    "hamwe na": "together with",
    "rundi": "or / either...or",
    "kandi": "and / but / in addition",
    "ekindi": "in addition to",
    "kuba": "because / that / if",
    "kakuba": "if (negative conditional)",
    "ngu": "that (reported speech)",
    "obu": "if / when",
    "noobwa": "even if / though / although",
    "kyonka": "but",
    "baitwa": "but / whereas",
    "nikyo kinu": "all the same",
}

PREPOSITIONS = {
    "mu": "in / into / at",
    "ha": "at / on / near",
    "ku": "to / at / on",
    "aha": "at / there",
    "hanyuma": "after",
    "nka": "like / as",
    "okuhikya": "till / until",
    "nkoomu": "as / like",
    "okuna": "with / by",
}

NEGATION_WORDS = {
    "ti-": "negative prefix (verb)",
    "tindi": "I will not",
    "tinka": "I did not / have not",
    "aha": "not there (declinable negation)",
    "busa": "no / not at all",
    "nga": "no / not",
}

ADJECTIVE_STEMS = {
    "-rungi": "good",
    "-bi": "bad",
    "-raira": "tall/long",
    "-to": "small/young",
    "-nene": "big/fat",
    "-gu": "heavy",
    "-eri": "two",
    "-satu": "three",
    "-na": "four",
    "-taano": "five",
    "-ingi": "many",
    "-eke": "few/little",
    "-iza": "good/beautiful (alternative)",
    "-ire": "old (of things)",
    "-kuru": "old (of persons)",
}

ADVERBS_OF_MANNER = {
    "kijungu": "in a European fashion",
    "kiserukali": "like a soldier",
    "kinyoro": "like a chief / in Runyoro fashion",
    "kizaana": "like a maid-servant",
    "masaija": "in a manly way",
    "mate": "in a cow-like fashion",
    "matale": "in a leonine fashion",
    "bwangu": "quickly, rapidly",
    "mpola": "slowly, gently",
    "nkoomu": "together",
    "hamwe": "together",
}

PERSONAL_PRONOUNS = {
    "nyowe": "I (emphatic)",
    "itwe": "we (emphatic)",
    "iwe": "you (singular)",
    "inywe": "you (plural)",
    "uwe": "he / she",
}

NUMERAL_CONCORDS = {
    1: "omu", 2: "aba", 3: "omu", 4: "emi",
    5: "eri", 6: "ama", 7: "eki", 8: "ebi",
    9: "en", 10: "en", 11: "oru", 12: "aka",
    13: "utu", 14: "obu", 15: "oku",
}

COMPARISON_POSITIVE = "adjective alone — e.g. omukazi omurungi (a good woman)"
COMPARISON_COMPARATIVE = "verb + okusinga — e.g. asinga omurungi (she is better)"
COMPARISON_SUPERLATIVE = "verb + okusinga + bose/byona — e.g. asinga bose omurungi (she is the best)"

GENITIVE_PARTICLES = {
    1: "wa", 2: "ba", 3: "gwa", 4: "gya",
    5: "lya", 6: "ga", 7: "kya", 8: "bya",
    9: "ya", 10: "za", 11: "rwa", 12: "ka",
    13: "twa", 14: "bwa", 15: "kwa",
}

CONDITIONAL_MOOD = {
    "particles": ["obu", "kuba", "kakuba", "kusangwa", "kakusangwa"],
    "structure": "condition particle + subject + -ku- + verb stem",
    "example": "Obu akukora, turamugira (If he does it, we shall tell him)",
}

COORDINATING_PARTICLES = {
    "na": "and / with (connects nouns and clauses)",
    "kandi": "and also / furthermore",
    "rundi": "or / alternatively",
    "kyonka": "but / however",
    "kuba": "because / for / since",
}
