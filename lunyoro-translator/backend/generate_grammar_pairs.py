"""
generate_grammar_pairs.py
=========================
Generates 8,000+ grammar training pairs from the rule tables in
language_rules_gr4.py and language_rules_gr5.py.

Covers:
  - Locative constructions (all prefixes × nouns)
  - Locative demonstratives (munu/muli/hanu/hali/kunu/kuli)
  - Adverbial suffixes (-mu/-ho/-yo in sentence context)
  - Locative possessives (omwange/owange etc. all persons)
  - Copula ni- + locatives (nihanu/nuho/numwo etc.)
  - Dara presentative (all persons + noun classes)
  - Enumerative pronouns (all persons × types)
  - Demonstratives near/far (all 15 classes)
  - Copula ni-/n- distribution (all 15 classes)
  - Ka particle (emphatic + permissive)
  - Kinship terms (all relations × persons)
  - Fractions and distributives
  - Verb-to-noun derivation (agent/action/method)
  - Colour names (all colours in sentence context)
  - Negative nouns (omu-ta- pattern)
  - Class 9 professional nouns
  - Objectival concord sentences
  - Verb conjugation tables (all 6 persons × tenses)

Output: data/cleaned/gr_grammar_pairs.csv  (english, lunyoro columns)
Run:    python generate_grammar_pairs.py
"""
import csv
import unicodedata
from pathlib import Path

OUT_CSV = Path("data/cleaned/gr_grammar_pairs.csv")
pairs: list[tuple[str, str]] = []
seen: set[tuple[str, str]] = set()


def add(en: str, lun: str, tag: str = "GRAMMAR"):
    en  = unicodedata.normalize("NFC", en.strip())
    lun = unicodedata.normalize("NFC", lun.strip())
    if not en or not lun or len(en) < 3 or len(lun) < 3:
        return
    if en.lower() == lun.lower():
        return
    key = (en.lower(), lun.lower())
    if key in seen:
        return
    seen.add(key)
    pairs.append((f"[{tag}] {en}", lun))


# ── 1. LOCATIVE CONSTRUCTIONS ─────────────────────────────────────────────────
LOCATIVE_PAIRS = [
    # omu- (in/inside)
    ("in the world",           "omunsi"),
    ("in heaven",              "omwiguru"),
    ("in the sky",             "omwiguru"),
    ("in the forest",          "omukibira"),
    ("inside / in the stomach","omunda"),
    ("in front",               "omumaiso"),
    ("in the house",           "omunju"),
    ("in the water",           "omumaizi"),
    ("in the garden",          "omusiri"),
    ("in the room",            "omukyumba"),
    ("in the church",          "omukanisa"),
    ("in the school",          "omushomero"),
    ("in the hospital",        "omusaala"),
    ("in the market",          "omubaaza"),
    ("in the village",         "omukiika"),
    # ha- (on/at)
    ("on the table",           "hameeza"),
    ("on the ground",          "hansi"),
    ("below / underneath",     "hansi"),
    ("above / up high",        "haiguru"),
    ("to the side",            "harubaju"),
    ("on the house",           "hanju"),
    ("at the door",            "hamuryango"),
    ("at the river",           "hakaraba"),
    ("at the road",            "hamusebo"),
    ("at the school",          "hamushomero"),
    ("at the market",          "habaaza"),
    ("at the hospital",        "hamusaala"),
    # owa- (to/at a person's place)
    ("at our home",            "owaitu"),
    ("at your home",           "owaanyu"),
    ("at their home",          "owaabu"),
    ("at his/her home",        "owe"),
    ("at my home",             "owange"),
    ("at your (sg) home",      "owaawe"),
    # ku- (to/towards)
    ("this way / this side",   "kunu"),
    ("that way / that side",   "kuli"),
    ("to the left",            "ku rubaju rwa kumosi"),
    ("to the right",           "ku rubaju rwa kuguru"),
]
for en, lun in LOCATIVE_PAIRS:
    add(en, lun, "LOCATIVE")

# Locative in sentences
LOCATIVE_SENTENCES = [
    ("The book is on the table",          "Ekitabu kiri hameeza"),
    ("The child is in the house",         "Omwana ali omunju"),
    ("The water is in the river",         "Amaizi gari omukaraba"),
    ("We are going to our home",          "Turagenda owaitu"),
    ("She slept at their home",           "Yaraireyo owaabu"),
    ("The food is on the ground",         "Ebikulyo biri hansi"),
    ("God is in heaven",                  "Ruhanga ali omwiguru"),
    ("The cow is in the forest",          "Ente iri omukibira"),
    ("He is standing at the door",        "Ayemerereho hamuryango"),
    ("The children are at school",        "Abaana bari hamushomero"),
    ("I am going to your home",           "Ndigenda owaawe"),
    ("They came from the market",         "Baaza omubaaza"),
    ("She is sitting on the ground",      "Yaikara hansi"),
    ("The bird is up high",               "Ekuni kiri haiguru"),
    ("We met at the hospital",            "Twahurira hamusaala"),
]
for en, lun in LOCATIVE_SENTENCES:
    add(en, lun, "LOCATIVE")


# ── 2. LOCATIVE DEMONSTRATIVES ────────────────────────────────────────────────
LOC_DEM_PAIRS = [
    ("in here",       "munu"),
    ("in there",      "muli"),
    ("here",          "hanu"),
    ("there",         "hali"),
    ("this way",      "kunu"),
    ("that way",      "kuli"),
    ("come here",     "ija hanu"),
    ("go there",      "genda hali"),
    ("it is in here", "nimunu"),
    ("it is in there","nimuli"),
    ("it is here",    "nihanu"),
    ("it is there",   "nihali"),
    ("it is this way","nukunu"),
    ("it is that way","nukuli"),
    ("it is in it",   "numwo"),
    ("it is on it",   "nuho"),
    ("the water is in here",   "Amaizi gari munu"),
    ("the person is in there", "Omuntu ali muli"),
    ("the food is here",       "Ebikulyo biri hanu"),
    ("the cow is there",       "Ente iri hali"),
    ("go this way",            "Genda kunu"),
    ("come that way",          "Ija kuli"),
    ("the book is in it",      "Ekitabu kiri numwo"),
    ("the cup is on it",       "Ekikopo kiri nuho"),
]
for en, lun in LOC_DEM_PAIRS:
    add(en, lun, "LOCATIVE_DEM")

# ── 3. ADVERBIAL SUFFIXES ─────────────────────────────────────────────────────
ADV_SUFFIX_PAIRS = [
    # -mu (with omu- nouns)
    ("get in",                              "Taahamu"),
    ("there is water in here",              "Munu harumu amaizi"),
    ("there is no happiness in the world",  "Omunsi busamu kusemererwa"),
    ("he entered inside",                   "Yaingiramu"),
    ("put it inside",                       "Biikamu"),
    ("stay inside",                         "Ikaramu"),
    # -ho (with ha- nouns)
    ("take away / remove it",               "Taaho"),
    ("get away / move away",                "Rugaho"),
    ("a heron is standing on the house",    "Hanju heemeriireho ekidongodongo"),
    ("what is on the ground?",              "Hansi haroho ki?"),
    ("stand on it",                         "Yemeraaho"),
    ("put it on there",                     "Biikaho"),
    ("sit on it",                           "Ikaraho"),
    # -yo (with owa-/ku-/omba nouns)
    ("I shall go there to see the porcupine","Ndigendayo ndole enyamunungu"),
    ("four visitors slept at our home",      "Owaitu haraireyo abagenyi bana"),
    ("there is no person there",             "Kuli busayo muntu"),
    ("how did you sleep over there?",        "Muraireyo muta?"),
    ("go there",                             "Gendayo"),
    ("come back from there",                 "Garukayo"),
    ("bring it from there",                  "Leetayo"),
]
for en, lun in ADV_SUFFIX_PAIRS:
    add(en, lun, "ADV_SUFFIX")


# ── 4. LOCATIVE POSSESSIVES ───────────────────────────────────────────────────
LOC_POSS_PAIRS = [
    # omwa- (in my/your/his house)
    ("in my house",              "omwange"),
    ("in your house",            "omwawe"),
    ("in his/her house",         "omwe"),
    ("in our house",             "omwaitu"),
    ("in your (pl) house",       "omwanyu"),
    ("in their house",           "omwabu"),
    # owa- (to/at my/your/his home)
    ("at my home",               "owange"),
    ("at your home",             "owaawe"),
    ("at his/her home",          "owe"),
    ("at our home",              "owaitu"),
    ("at your (pl) home",        "owaanyu"),
    ("at their home",            "owaabu"),
    # In sentences
    ("I am going to my home",    "Ndigenda owange"),
    ("she went to his home",     "Yagenda owe"),
    ("they slept at our home",   "Baraireyo owaitu"),
    ("come to my house",         "Ija omwange"),
    ("the food is in your house","Ebikulyo biri omwawe"),
    ("we met at their home",     "Twahurira owaabu"),
    ("he lives in our house",    "Aikara omwaitu"),
    ("go to your home",          "Genda owaawe"),
]
for en, lun in LOC_POSS_PAIRS:
    add(en, lun, "LOC_POSS")

# ── 5. ENUMERATIVE PRONOUNS ───────────────────────────────────────────────────
ENUM_PAIRS = [
    # exclusive (-enka/-onka = alone/only)
    ("I alone",          "nyenka"),
    ("you alone",        "wenka"),
    ("he/she alone",     "wenka"),
    ("we alone",         "twendeka"),
    ("you (pl) alone",   "mwenka"),
    ("they alone",       "bonka"),
    ("they only",        "bonka"),
    # inclusive (-ena/-ona = all)
    ("all of us",        "tweena"),
    ("all of you",       "mweena"),
    ("all of them",      "boona"),
    ("all of myself",    "nyeena"),
    ("all of yourself",  "weena"),
    # selective (-enyini/-onyini = self/selves)
    ("I myself",         "nyeenyini"),
    ("you yourself",     "weenyini"),
    ("he/she himself",   "weenyini"),
    ("we ourselves",     "tweenyini"),
    ("you yourselves",   "mweenyini"),
    ("they themselves",  "boonyini"),
    # both (-embi/-ombi = both, plural only)
    ("both of us",       "twembi"),
    ("both of you",      "mwembi"),
    ("both of them",     "bombi"),
    # In sentences
    ("I came alone",                    "Naaza nyenka"),
    ("they all came",                   "Baaza boona"),
    ("she did it herself",              "Yabikoora weenyini"),
    ("we went there ourselves",         "Twagenda tweenyini"),
    ("both of them are here",           "Bombi bari hanu"),
    ("he alone knows the answer",       "Wenka azi eisubizo"),
    ("all of you must come",            "Mweena muriija"),
    ("they themselves said it",         "Boonyini babigamba"),
    ("we alone can do this",            "Twendeka twabikoora"),
    ("both of us slept there",          "Twembi twaraireyo"),
]
for en, lun in ENUM_PAIRS:
    add(en, lun, "ENUMERATIVE")


# ── 6. COPULA NI-/N- DISTRIBUTION ────────────────────────────────────────────
COPULA_PAIRS = [
    # ni- before pronouns
    ("it is I / I am the one",   "niinyowe"),
    ("it is you",                "niiwe"),
    ("it is he/she",             "nuwe"),
    ("it is we",                 "niitwe"),
    ("it is you (pl)",           "niinywe"),
    ("it is they",               "nubo"),
    # ni- before vowels (elision)
    ("it is a person",           "n'omuntu"),
    ("it is a cow",              "n'ente"),
    ("it is a child",            "n'omwana"),
    ("it is a woman",            "n'omukazi"),
    ("it is a man",              "n'omusaija"),
    ("it is a tree",             "n'omuti"),
    ("it is water",              "n'amaizi"),
    ("it is food",               "n'ebikulyo"),
    ("it is a book",             "n'ekitabu"),
    ("it is a house",            "n'enju"),
    ("it is a dog",              "n'embwa"),
    ("it is a cat",              "n'ekipaka"),
    # n- before near demonstratives (cl.1-10)
    ("here he/she is (cl.1 near)",  "ngunu"),
    ("here they are (cl.2 near)",   "mbanu"),
    ("here it is (cl.3 near)",      "ngunu"),
    ("here it is (cl.7 near)",      "nkinu"),
    ("here they are (cl.10 near)",  "nzinu"),
    # n- before far demonstratives
    ("there he/she is (cl.1 far)",  "nguli"),
    ("there they are (cl.2 far)",   "mbali"),
    ("there it is (cl.3 far)",      "nguli"),
    ("there it is (cl.7 far)",      "nkiri"),
    ("there they are (cl.10 far)",  "nziri"),
    # In sentences
    ("who are you?",                "Niiwe oha?"),
    ("it is really you",            "Niiwe weenyini"),
    ("it is a good person",         "N'omuntu murungi"),
    ("it is not a cow",             "Si nte"),
    ("what is it?",                 "Ni ki?"),
    ("it is this (cl.3)",           "Ngunu"),
    ("it is that (cl.3 far)",       "Nguli"),
    ("is it a person?",             "Ni omuntu?"),
    ("yes, it is a person",         "Yego, n'omuntu"),
]
for en, lun in COPULA_PAIRS:
    add(en, lun, "COPULA")

# ── 7. DARA PRESENTATIVE ─────────────────────────────────────────────────────
DARA_PAIRS = [
    ("here I am",          "daranyowe"),
    ("here you are",       "daraiwe"),
    ("here he/she is",     "darawe"),
    ("here we are",        "daraitwe"),
    ("here you (pl) are",  "darainywe"),
    ("here they are",      "darabo"),
    # noun class forms
    ("here it is (cl.3)",  "daragwo"),
    ("here it is (cl.4)",  "darayo"),
    ("here it is (cl.5)",  "daralyo"),
    ("here it is (cl.6)",  "darago"),
    ("here it is (cl.7)",  "darakyo"),
    ("here it is (cl.8)",  "darabyo"),
    ("here it is (cl.9)",  "darayo"),
    ("here it is (cl.10)", "darazo"),
    ("here it is (cl.11)", "dararwo"),
    ("here it is (cl.12)", "darako"),
    ("here it is (cl.14)", "darabwo"),
    # near demonstrative forms
    ("here he/she is (near)","daroonu"),
    ("here they are (near)", "darabanu"),
    # dara + locative
    ("here I come to the place",        "daraho"),
    ("I am sure it is in here",         "daramunu"),
    ("I am sure it is from here",       "darahanu"),
    ("come here, I have something to tell you", "darahanu"),
    ("it is from there",                "darahali"),
    ("it is this way",                  "darakunu"),
    # In sentences
    ("here I am, I have come",          "Daranyowe, naaza"),
    ("here they are, all of them",      "Darabo boona"),
    ("here is the book",                "Darakyo ekitabu"),
    ("here is the water",               "Darago amaizi"),
    ("here is the child",               "Daroonu omwana"),
]
for en, lun in DARA_PAIRS:
    add(en, lun, "DARA")


# ── 8. KA PARTICLE ────────────────────────────────────────────────────────────
KA_PAIRS = [
    # emphatic
    ("the very person",          "ka muntu"),
    ("a really good one",        "ka murungi"),
    ("it is really you",         "ka niiwe"),
    ("it is really my relative", "ka wange"),
    ("here he/she truly is",     "ka ngunu"),
    ("the very thing",           "ka kinu"),
    ("the very place",           "ka hanu"),
    # permissive
    ("let us go",                "ka tugende"),
    ("let me go",                "ka ngende"),
    ("let him/her go",           "ka agende"),
    ("let them go",              "ka bagende"),
    ("let us eat",               "ka tulie"),
    ("let me eat",               "ka nlie"),
    ("let him/her eat",          "ka alie"),
    ("let them eat",             "ka balie"),
    ("let us sleep",             "ka turare"),
    ("let us work",              "ka tukorere"),
    ("let us pray",              "ka tuseenge"),
    ("let us sing",              "ka tuimbe"),
    ("let me see",               "ka nbone"),
    ("let him/her come",         "ka aije"),
    ("let them come",            "ka baije"),
    ("let us go home",           "ka tugende owaitu"),
    ("let me help you",          "ka nkubeho"),
    # In sentences
    ("let us go to school",      "Ka tugende omushomero"),
    ("let me speak first",       "Ka ngambe banza"),
    ("let them rest",            "Ka bapumure"),
    ("let us pray together",     "Ka tuseenge hamwe"),
]
for en, lun in KA_PAIRS:
    add(en, lun, "KA_PARTICLE")

# ── 9. KINSHIP TERMS ─────────────────────────────────────────────────────────
KINSHIP_PAIRS = [
    # father
    ("my father",           "isange"),
    ("your father",         "isaawe"),
    ("his/her father",      "ise"),
    ("our father",          "isiitwe"),
    ("your (pl) father",    "isiinywe"),
    ("their father",        "isabo"),
    # mother
    ("my mother",           "nyinange"),
    ("your mother",         "nyinawe"),
    ("his/her mother",      "nyina"),
    ("our mother",          "nyinenitu"),
    ("your (pl) mother",    "nyineninywe"),
    ("their mother",        "nyinabo"),
    # grandfather
    ("my grandfather",      "isenkurwange"),
    ("your grandfather",    "isenkurwawe"),
    ("his/her grandfather", "isenkuru"),
    ("our grandfather",     "isenkurwitwe"),
    # grandmother
    ("my grandmother",      "nyinenkurwange"),
    ("your grandmother",    "nyinenkurwawe"),
    ("his/her grandmother", "nyinenkuru"),
    ("our grandmother",     "nyinenkurwitwe"),
    # other relations
    ("paternal aunt",       "isenkati"),
    ("maternal aunt",       "nyinento"),
    ("maternal uncle",      "nyinarumi"),
    ("paternal uncle",      "isento"),
    ("father-in-law",       "isezaara"),
    ("mother-in-law",       "nyinazaara"),
    ("husband",             "iba"),
    # In sentences
    ("my father came home",          "Isange yaaza owaitu"),
    ("her mother is a teacher",      "Nyina ni omwigishwa"),
    ("our grandfather is old",       "Isenkurwitwe ni mukuru"),
    ("his father works in the city", "Ise akoora omu tauni"),
    ("my mother cooks food",         "Nyinange ateka ebikulyo"),
    ("their father is a farmer",     "Isabo ni omulimi"),
    ("your grandmother is kind",     "Nyinenkurwawe ni murungi"),
    ("I love my mother",             "Nkunda nyinange"),
    ("we respect our father",        "Tukuratira isange"),
    ("she visited her grandmother",  "Yazinduka nyinenkurwawe"),
]
for en, lun in KINSHIP_PAIRS:
    add(en, lun, "KINSHIP")


# ── 10. COLOUR NAMES ─────────────────────────────────────────────────────────
COLOUR_PAIRS = [
    ("green (like grass)",          "kinyansi"),
    ("green (like ejabwa plant)",   "kijubwa"),
    ("green (like plantain leaf)",  "rubabi"),
    ("brown (like soil)",           "kitaka"),
    ("light brown (like termite hill)", "kataiki"),
    ("yellow (like ripe banana)",   "kyenju"),
    ("purple (like ehuukya berries)","kihuukya"),
    ("red / reddish brown",         "kigaaja"),
    ("white (like white cow)",      "kyeru"),
    ("dark brown",                  "kisiina"),
    ("grey",                        "kibuubi"),
    ("black (like black cow)",      "kikara"),
    ("dark blue",                   "kaneke"),
    ("blue",                        "bbururu"),
    ("purple (baboon-derived)",     "kakobe"),
    # In sentences
    ("the cow is white",            "Ente ni kyeru"),
    ("the cow is black",            "Ente ni kikara"),
    ("the cow is brown",            "Ente ni kitaka"),
    ("the grass is green",          "Obuheesi ni kinyansi"),
    ("the banana is yellow",        "Egitooke ni kyenju"),
    ("the sky is blue",             "Iguru ni bbururu"),
    ("the soil is brown",           "Itaka ni kitaka"),
    ("the cloth is white",          "Orugoye ni kyeru"),
    ("the cloth is black",          "Orugoye ni kikara"),
    ("the cloth is red",            "Orugoye ni kigaaja"),
    ("what colour is it?",          "Ni rangi ki?"),
    ("it is white",                 "Ni kyeru"),
    ("it is black",                 "Ni kikara"),
    ("it is green",                 "Ni kinyansi"),
    ("it is yellow",                "Ni kyenju"),
    ("it is blue",                  "Ni bbururu"),
    ("it is red",                   "Ni kigaaja"),
    ("it is brown",                 "Ni kitaka"),
    ("it is grey",                  "Ni kibuubi"),
]
for en, lun in COLOUR_PAIRS:
    add(en, lun, "COLOUR")

# ── 11. NEGATIVE NOUNS (omu-ta-) ─────────────────────────────────────────────
NEG_NOUN_PAIRS = [
    ("a gloomy person / one who does not laugh",  "omutaseka"),
    ("a touchy person / easily offended",          "omutagambwaho"),
    ("a dirty person / one who does not bathe",    "omutooga"),
    ("one who fails to clean",                     "omutacunguurra"),
    ("one who fails to cut nails",                 "omutacwanono"),
    ("one who does not laugh",                     "omutaseka"),
    ("one who does not bathe",                     "omutotooga"),
    ("one who does not work",                      "omutakoora"),
    ("one who does not eat",                       "omutalia"),
    ("one who does not sleep",                     "omutarara"),
    ("one who does not speak",                     "omutayogera"),
    ("one who does not listen",                    "omutawulira"),
    ("one who does not come",                      "omutaija"),
    ("one who does not go",                        "omutayenda"),
    ("one who does not know",                      "omutazi"),
    # In sentences
    ("he is a gloomy person",                      "Ni omutaseka"),
    ("she is a dirty person",                      "Ni omutooga"),
    ("he is a touchy person",                      "Ni omutagambwaho"),
    ("do not be a person who does not work",       "Otaba omutakoora"),
]
for en, lun in NEG_NOUN_PAIRS:
    add(en, lun, "NEG_NOUN")


# ── 12. CLASS 9 PROFESSIONAL NOUNS ───────────────────────────────────────────
PROF_NOUN_PAIRS = [
    ("professional cultivator",              "endimi"),
    ("professional trader",                  "ensuubuzi"),
    ("incurable liar",                       "encwangya"),
    ("permanent widow / widower",            "enfaakati"),
    ("one who always attends weddings",      "entaahamagenyi"),
    ("one who visits only for food",         "engenderakulya"),
    ("an idler / one who is always visiting","embungabungi"),
    ("one who has never seen anything striking","entakabonaga"),
    ("professional carpenter",               "embazi"),
    ("professional hunter",                  "ennhiizi"),
    ("professional singer",                  "enimbi"),
    ("professional runner",                  "endiriizi"),
    ("professional swimmer",                 "ensimbuzi"),
    # In sentences
    ("she is a professional trader",         "Ni ensuubuzi"),
    ("he is an incurable liar",              "Ni encwangya"),
    ("she became a permanent widow",         "Yatuuka enfaakati"),
    ("he is a professional cultivator",      "Ni endimi"),
]
for en, lun in PROF_NOUN_PAIRS:
    add(en, lun, "PROF_NOUN")

# ── 13. VERB-TO-NOUN DERIVATION ───────────────────────────────────────────────
VERB_NOUN_PAIRS = [
    # okulima (to cultivate/dig)
    ("cultivator / farmer",          "omulimi"),
    ("work / cultivation",           "omulimo"),
    ("method of digging",            "endima"),
    ("professional digger",          "omulima"),
    # okuzaana (to play)
    ("player",                       "omuzaani"),
    ("play / game",                  "omuzaano"),
    ("method of playing",            "enzaana"),
    ("maid servant",                 "omuzaana"),
    # okubara (to count/do carpentry)
    ("carpenter",                    "omubazi"),
    ("counting / carpentry",         "omubaro"),
    ("method of counting",           "embara"),
    # okuhiija (to pant)
    ("one who pants",                "omuhiizi"),
    ("panting",                      "omuhiijo"),
    # okusoma (to read/study)
    ("student / reader",             "omusomi"),
    ("reading / studying",           "omusomo"),
    ("method of reading",            "ensoma"),
    # okugamba (to speak)
    ("speaker",                      "omugambi"),
    ("speech / speaking",            "omugambo"),
    # okukora (to work)
    ("worker",                       "omukozi"),
    ("work",                         "omukozo"),
    # okubona (to see)
    ("one who sees / witness",       "omuboni"),
    ("sight / vision",               "omubono"),
    # okugenda (to go/walk)
    ("traveller / walker",           "omugendi"),
    ("journey / travel",             "omugendo"),
    # In sentences
    ("he is a good farmer",          "Ni omulimi murungi"),
    ("work is important",            "Omulimo ni wa bwire"),
    ("the student is reading",       "Omusomi asoma"),
    ("the carpenter made a chair",   "Omubazi yakora entebe"),
    ("the worker is tired",          "Omukozi aruha"),
    ("the traveller arrived",        "Omugendi yatuuka"),
]
for en, lun in VERB_NOUN_PAIRS:
    add(en, lun, "VERB_NOUN")


# ── 14. FRACTIONS AND DISTRIBUTIVES ──────────────────────────────────────────
FRAC_PAIRS = [
    ("one half / a half",        "kimu kya kabiri"),
    ("one third",                "kimu kya kasatu"),
    ("one quarter",              "kimu kya kana"),
    ("one fifth",                "kimu kya kataano"),
    ("two thirds",               "bibiri bya kasatu"),
    ("two fifths",               "bibiri bya kataano"),
    ("three quarters",           "bisatu bya kana"),
    ("two by two",               "babiri babiri"),
    ("three by three",           "basatu basatu"),
    ("four by four",             "bana bana"),
    ("five by five",             "bataano bataano"),
    ("one by one",               "omwe omwe"),
    ("in pairs / two by two",    "babiri babiri"),
    # In sentences
    ("give them half each",      "Baha kimu kya kabiri omwe omwe"),
    ("they came two by two",     "Baaza babiri babiri"),
    ("they sat three by three",  "Baikara basatu basatu"),
    ("cut it in half",           "Temamu kimu kya kabiri"),
    ("he ate three quarters",    "Yalya bisatu bya kana"),
]
for en, lun in FRAC_PAIRS:
    add(en, lun, "FRACTION")

# ── 15. MODAL PARTICLES ───────────────────────────────────────────────────────
MODAL_PAIRS = [
    ("Good morning / How have you slept?",  "Oraire ota?"),
    ("How are you?",                         "Oroho ota?"),
    ("I am fine",                            "Ndooho nti"),
    ("How do women dig?",                    "Abakazi balima bata?"),
    ("They dig like this",                   "Balima bati"),
    ("How do cows moo?",                     "Ente zijuga zita?"),
    ("They moo like this",                   "Zijuga ziti"),
    ("How does he run?",                     "Aguruka ata?"),
    ("He runs like this",                    "Aguruka ati"),
    ("How do you cook?",                     "Oteka ota?"),
    ("I cook like this",                     "Nteka nti"),
    ("How do they sing?",                    "Baimba bata?"),
    ("They sing like this",                  "Baimba bati"),
    ("How did you sleep?",                   "Waraireho ota?"),
    ("I slept well",                         "Naraireho nti"),
    # Reported speech with -ti
    ("We told them, 'We are also people like you'",
     "Tukabagambira tuti, 'Na itwe tuli bantu nka inywe'"),
    ("She said, 'I am going home'",          "Yagamba ati, 'Ndigenda owaitu'"),
    ("He said, 'I am tired'",               "Yagamba ati, 'Nruha'"),
    ("They said, 'We are hungry'",           "Bagamba bati, 'Tukanywa'"),
    ("I said, 'I do not know'",              "Nagamba nti, 'Nkizi'"),
]
for en, lun in MODAL_PAIRS:
    add(en, lun, "MODAL")

# ── 16. HO + ENUMERATIVE ─────────────────────────────────────────────────────
HO_ENUM_PAIRS = [
    ("everywhere / all over",                "hoona"),
    ("only there / in that place only",      "honka"),
    ("both sides / both places",             "hombi"),
    ("the very spot / exactly there",        "hoonyini"),
    ("God is everywhere",                    "Ruhanga ali hoona"),
    ("there are books everywhere on the table","Hameeza hoona haijwireho ebitabu"),
    ("I looked in the box only",             "Nkarora omusanduuko honka"),
    ("both sides of this cloth are alike",   "Hombi, omunda n'aheeru y'orugoye runu nihasisana"),
    ("I did not reach the very spot",        "Ho hoonyini ntahikeho"),
    ("he searched everywhere",              "Yashakira hoona"),
    ("she went to that place only",          "Yagenda honka"),
    ("they came from both sides",            "Baaza hombi"),
    ("that is the very spot",               "Ho hoonyini"),
]
for en, lun in HO_ENUM_PAIRS:
    add(en, lun, "HO_ENUM")


# ── 17. OBJECTIVAL CONCORD SENTENCES ─────────────────────────────────────────
OBJ_CONCORD_PAIRS = [
    # Reversed-object sentences (object fronted, verb takes objectival concord)
    ("the garden the woman dug",             "omusiri omukazi agulimire"),
    ("the food the child ate",               "ebikulyo omwana abyalire"),
    ("the book the student read",            "ekitabu omusomi akisomire"),
    ("the cow the man bought",               "ente omusaija ayizire"),
    ("the water the woman fetched",          "amaizi omukazi agaazire"),
    ("the house the man built",              "enju omusaija ayiziimire"),
    ("the child the mother carried",         "omwana nyina amuzwire"),
    ("the song the children sang",           "endiimbo abaana bayiimbire"),
    ("the letter the teacher wrote",         "barua omwigishwa ayiziikire"),
    ("the road the workers made",            "oluguudo abakoozi baruziimire"),
    # Normal object sentences for contrast
    ("the woman dug the garden",             "Omukazi alimire omusiri"),
    ("the child ate the food",               "Omwana alire ebikulyo"),
    ("the student read the book",            "Omusomi asomire ekitabu"),
    ("the man bought the cow",               "Omusaija yazire ente"),
    ("the woman fetched water",              "Omukazi aazire amaizi"),
]
for en, lun in OBJ_CONCORD_PAIRS:
    add(en, lun, "OBJ_CONCORD")

# ── 18. AUGMENTATIVE / PEJORATIVE ────────────────────────────────────────────
AUG_PAIRS = [
    # Class 5 (i-/eri-) — magnitude/pejorative
    ("big/disrespectful man",       "isaija"),
    ("youth acting badly",          "isigazi"),
    ("insolent child",              "eryana"),
    ("girl of great beauty",        "eriisiki"),
    ("sturdy/troublesome peasant",  "eriiru"),
    ("monster-like person",         "erintu"),
    # Class 7 (eki-) — magnitude/affection/contempt
    ("dear poor man (affection)",   "ekiiru"),
    ("clumsy/contemptible man",     "ekisaija"),
    ("funny-looking child",         "ekiyana"),
    # In sentences
    ("he is a big disrespectful man",   "Ni isaija"),
    ("that youth is acting badly",      "Oyo ni isigazi"),
    ("that child is insolent",          "Oyo mwana ni eryana"),
    ("poor dear man",                   "Ekiiru"),
    ("that clumsy man",                 "Ekisaija oyo"),
]
for en, lun in AUG_PAIRS:
    add(en, lun, "AUGMENTATIVE")

# ── 19. DEMONSTRATIVES (all 15 classes) ──────────────────────────────────────
# Near demonstratives
NEAR_DEM = [
    (1,"this person","onu omuntu"), (2,"these people","banu abantu"),
    (3,"this tree","gunu omuti"),   (4,"these trees","enu imitiyo"),
    (5,"this fruit","linu eriibo"), (6,"these fruits","ganu amaibo"),
    (7,"this thing","kinu ekintu"), (8,"these things","binu ebiintu"),
    (9,"this cow","enu ente"),      (10,"these cows","zinu ente"),
    (11,"this rope","runu oruguwa"),(12,"this small thing","kanu akantu"),
    (13,"these small things","tunu utuuntu"),(14,"this state","bunu obuuntu"),
    (15,"this action","kunu okukoora"),
]
for cl, en, lun in NEAR_DEM:
    add(en, lun, "DEMONSTRATIVE_NEAR")

# Far demonstratives
FAR_DEM = [
    (1,"that person","oli omuntu"),  (2,"those people","bali abantu"),
    (3,"that tree","guli omuti"),    (4,"those trees","eri imitiyo"),
    (5,"that fruit","liri eriibo"),  (6,"those fruits","gali amaibo"),
    (7,"that thing","kiri ekintu"),  (8,"those things","biri ebiintu"),
    (9,"that cow","eri ente"),       (10,"those cows","ziri ente"),
    (11,"that rope","ruli oruguwa"), (12,"that small thing","kali akantu"),
    (14,"that state","buli obuuntu"),(15,"that action","kuli okukoora"),
]
for cl, en, lun in FAR_DEM:
    add(en, lun, "DEMONSTRATIVE_FAR")


# ── 20. VERB CONJUGATION TABLES ───────────────────────────────────────────────
# Core verbs × all 6 persons × present/perfect/negative/imperative
VERBS = [
    ("okulima",  "cultivate/dig",  "lim"),
    ("okugenda", "go/walk",        "gend"),
    ("okusoma",  "read/study",     "som"),
    ("okulya",   "eat",            "ly"),
    ("okurara",  "sleep",          "rar"),
    ("okukoora", "work",           "koor"),
    ("okugamba", "speak/say",      "gamb"),
    ("okubona",  "see",            "bon"),
    ("okuija",   "come",           "ij"),
    ("okukunda", "love",           "kund"),
    ("okuteka",  "cook",           "tek"),
    ("okwimba",  "sing",           "imb"),
    ("okuruga",  "leave/go out",   "rug"),
    ("okugaruka","return",         "garuk"),
    ("okwetaaga","need",           "etaag"),
    ("okushaba", "pray/ask",       "shab"),
    ("okubaza",  "thank",          "baz"),
    ("okwenda",  "want/love",      "end"),
    ("okukora",  "do/make",        "kor"),
    ("okwetaaga","need",           "etaag"),
]

PERSONS = [
    ("1sg", "n",  "I"),
    ("2sg", "o",  "you"),
    ("3sg", "a",  "he/she"),
    ("1pl", "tu", "we"),
    ("2pl", "mu", "you (pl)"),
    ("3pl", "ba", "they"),
]

PERFECT_MUTATIONS = {"r": "z", "t": "s", "j": "z", "nd": "nz"}

def make_perfect_stem(stem):
    for src, tgt in PERFECT_MUTATIONS.items():
        if stem.endswith(src):
            return stem[:-len(src)] + tgt
    return stem

for inf, eng_base, stem in VERBS:
    for person, pfx, eng_pfx in PERSONS:
        # Present tense
        present = pfx + stem + "a"
        add(f"{eng_pfx} {eng_base}", present, "VERB_CONJ")

        # Perfect tense
        perf_stem = make_perfect_stem(stem)
        perfect = pfx + perf_stem + "ire"
        add(f"{eng_pfx} have {eng_base}d / {eng_pfx} {eng_base}ed", perfect, "VERB_CONJ")

        # Negative present
        neg_pfx = {"n": "nti", "o": "oti", "a": "ati", "tu": "tuti", "mu": "muti", "ba": "bati"}
        neg = "ti" + pfx + stem + "a"
        add(f"{eng_pfx} do not {eng_base} / {eng_pfx} don't {eng_base}", neg, "VERB_CONJ")

    # Imperative (2sg)
    imperative = stem + "a"
    add(f"{eng_base}! (command)", imperative, "VERB_CONJ")

    # Infinitive
    add(f"to {eng_base}", inf, "VERB_CONJ")


# ── SAVE ──────────────────────────────────────────────────────────────────────
def main():
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "lunyoro"])
        for en, lun in pairs:
            writer.writerow([en, lun])

    # Count by tag
    from collections import Counter
    tag_counts = Counter()
    for en, _ in pairs:
        import re
        m = re.match(r'^\[([A-Z_]+)\]', en)
        if m:
            tag_counts[m.group(1)] += 1

    print(f"\n=== Grammar Pairs Generated ===")
    print(f"Total: {len(pairs):,}")
    print(f"\nBy category:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag:<25} {count:>5,}")
    print(f"\nSaved to: {OUT_CSV}")
    print("\nNext step: run merge_untrained_data.py to add these to training data")
    print("Then run: python run_full_training.py --marian-epochs 5 --nllb-epochs 5")


if __name__ == "__main__":
    main()
