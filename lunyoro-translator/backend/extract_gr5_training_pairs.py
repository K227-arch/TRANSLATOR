"""
extract_gr5_training_pairs.py
==============================
Extracts clean English <-> Runyoro-Rutooro training pairs from
grammar rules 5.docx (Chapters 5, 6, 7) and merges them into
the training CSV files.

Run:
    python extract_gr5_training_pairs.py
"""

import csv
import re
import os
import sys
from pathlib import Path

BACKEND_DIR  = Path(__file__).parent
DATA_DIR     = BACKEND_DIR / "data"
TRAINING_DIR = DATA_DIR / "training"
CLEANED_DIR  = DATA_DIR / "cleaned"
GR5_CSV      = CLEANED_DIR / "gr5_pairs.csv"
TRAIN_CSV    = TRAINING_DIR / "train.csv"
VAL_CSV      = TRAINING_DIR / "val.csv"

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Normalise smart quotes and whitespace."""
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2019', "'").replace('\u2014', '-')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ── All training pairs extracted from grammar rule 5.docx ────────────────────

def get_all_pairs() -> list[tuple[str, str]]:
    pairs = []

    # ── Chapter 5: Locative Agreement Examples ───────────────────────────────
    pairs += [
        ("The world is a bad place.", "Omunsi habi."),
        ("Heaven is a good place.", "Omwiguru harungi."),
        ("The volume of a cup is smaller than that of the sauce pan.", "Omukikopo hafunzire okukira omusafuliya."),
        ("The road is wider than the foot path.", "Omuruguudo hagazi okukira omumuhanda."),
        ("Your home is further than his.", "Owanyu hara okukira owaabu."),
        ("This spot is dirty.", "Hanu hairagwire."),
        ("Visitors slept at our home.", "Owaitu haraireyo abagenyi."),
        ("There is cold in the forest.", "Omukibira harumu obutiti."),
        ("Out of happiness there has come weeping.", "Omukusemererwa haarugamu okurra."),
    ]

    # ── Locative demonstratives ───────────────────────────────────────────────
    pairs += [
        ("in here", "munu"),
        ("in there", "muli"),
        ("here", "hanu"),
        ("there", "hali"),
        ("this way", "kunu"),
        ("this side", "kunu"),
        ("that way", "kuli"),
        ("that side", "kuli"),
        ("in it", "mwo"),
        ("on it", "ho"),
        ("This is a real person.", "Onu muntu kwo."),
        ("in there (enclosed)", "omu"),
        ("on there", "aho"),
        ("there, that side", "oku"),
    ]

    # ── Genitive locatives ────────────────────────────────────────────────────
    pairs += [
        ("In Nyakaana's house.", "Omwa Nyakaana."),
        ("At his maternal aunt's place.", "Owa Nyinento."),
        ("He has gone to his aunt's place.", "Agiire omba nyinento."),
        ("Go to your father.", "Genda owa so."),
        ("Go to your father's home.", "Genda omba so."),
    ]

    # ── Locative possessives ──────────────────────────────────────────────────
    pairs += [
        ("in my house", "omwange"),
        ("in the house where I stay with others", "omwaitu"),
        ("in your house", "omwawe"),
        ("in the house where you stay with others", "omwanyu"),
        ("in his house", "omwe"),
        ("in the house where he stays with others", "omwabu"),
        ("to or at my home", "owange"),
        ("to or at your home", "owaawe"),
        ("to or at his home", "owe"),
        ("to or at our home", "owaitu"),
        ("to or at your home (plural)", "owaanyu"),
        ("to or at their home", "owaabu"),
        ("in its place (mongoose)", "omwabugwo"),
        ("in their place (mongooses)", "omwabuyo"),
        ("at its place", "owaabugwo"),
        ("at their place", "owaabuyo"),
        ("May you get into me, stay within me and I too may stay within you.",
         "Otaahe omwange, oikale omwange naanye nyikale omwaawe."),
        ("A mosquito amongst its relatives is addressed as Rwakinumi.",
         "Omubu guli owabugwo bagweta Rwakinumi."),
        ("Go to your home.", "Mugende owaabu-inywe."),
        ("For what reason have they had to leave their home?", "Owaabubo baihirweyo ki?"),
        ("At Nyakato's house.", "Omwabu Nyakato."),
        ("At those women's house.", "Omwabu abakazi abo."),
        ("At these people's house.", "Omwabu banu."),
        ("At those people's house.", "Omwabu bali."),
    ]

    # ── Adverbial suffixes -mu ────────────────────────────────────────────────
    pairs += [
        ("There is no happiness in the world.", "Omunsi busamu kusemererwa."),
        ("There is water in here.", "Munu harumu amaizi."),
        ("Get in.", "Taahamu."),
    ]

    # ── Adverbial suffixes -ho ────────────────────────────────────────────────
    pairs += [
        ("A heron is standing on the house.", "Hanju heemeriireho ekidongodongo."),
        ("What is on the ground?", "Hansi haroho ki?"),
        ("Take away.", "Taaho."),
        ("Get away.", "Rugaho."),
        ("Where are you coming from?", "Noorugaha?"),
        ("Where are you going?", "Noogyaha?"),
        ("Where has the alarm been raised?", "Egambiiraha?"),
    ]

    # ── Adverbial suffixes -yo ────────────────────────────────────────────────
    pairs += [
        ("I shall go there to see the porcupine.", "Ndigendayo ndole enyamunungu."),
        ("Four visitors slept at our home.", "Owaitu haraireyo abagenyi bana."),
        ("There is a fierce dog at the chief's home.", "Omb'Omunyoro haliyo embwa endurumi."),
        ("There is no person there.", "Kuli busayo muntu."),
        ("How did you sleep over there?", "Muraireyo muta?"),
        ("What had you gone to get from the forest?", "Obaire ogiire kwihayo ki omukibira?"),
        ("There are people of different colors in America.", "Mwameerika haliyo abantu ab'erangi ezitali zimu."),
        ("Kangoobe, do people dig up in the sky?", "Kangoobe, haiguru balimayo?"),
        ("There is something which speaks like a human being in Munyeenya's wilderness.",
         "Hairungu lya Munyeenya haliyo ekintu ekirukugamba nk'omuntu."),
    ]

    # ── Adverbial nouns as complements ────────────────────────────────────────
    pairs += [
        ("The monkeys are in the forest.", "Enkende ziri omukibira."),
        ("We have arrived where the water is deeper.", "Tuhikire omunziha."),
        ("Go in front.", "Genda omumaiso."),
        ("He has some disease in his stomach.", "Aina oburwaire omunda ye."),
        ("The book is on the table.", "Ekitabu kiri hameeza."),
        ("Do not look up.", "Mutarora haiguru."),
        ("Get aside.", "Garuka harubaju."),
        ("Sit down.", "Ikaarra hansi."),
    ]

    # ── Concord prefix ha- ────────────────────────────────────────────────────
    pairs += [
        ("I am sitting in a badly lit spot.", "Nyikaliire ahatarukuhweza kurungi."),
        ("I have left my book on the table where the radio is placed.",
         "Hameeza ahatairwe rrediyo nuho nsigirege ekitabu kyange."),
        ("Which part is written in red ink?", "Ahahandiikirwe na bwino erukutukura ninkaha?"),
        ("He did not get anything from the place he went to.", "Ha yagenzire akarugayo soi."),
        ("She will come at any time she likes.", "Aliija ha alikagondeza."),
        ("This is where they are going to put the churn guard.", "Ha barukugya kuta ekisaabu nihanu."),
    ]

    # ── hamu / handi ──────────────────────────────────────────────────────────
    pairs += [
        ("Stay in one place.", "Ikara hamu."),
        ("Come let us stay together.", "Ija twikale hamu."),
        ("They go together.", "Bagenda hamu."),
        ("Let me go to another place.", "K'angende handi."),
        ("You have put it in another place.", "Okitaire handi."),
        ("Indians dress in a different way, they do not dress like Europeans.",
         "Abahindi bajwara kundi, tibajwara nk'Abajungu."),
    ]

    # ── ho + enumerative roots ────────────────────────────────────────────────
    pairs += [
        ("Whether you go to Buganda or to Tooro, it is all the same.",
         "Ogende Buganda, ogende Tooro hoona nikyo kimu."),
        ("God is in heaven, on earth and everywhere.",
         "Ruhanga ali omwiguru, n'omunsi na buli hantu hoona."),
        ("There are books everywhere on the table.", "Hameeza hoona haijwireho ebitabu."),
        ("I have looked for him everywhere in this house in vain.",
         "Mmuserwire omunju munu hoonayambura."),
        ("Big trees are found everywhere in Kibaale forest.",
         "Hoona hoona omukibira kya Kibaale hasangwamu emitt mikooto."),
        ("I looked in the box only, but I did not check in the cupboard.",
         "Nkarora omusanduuko honka, omukabada ntarolemu."),
        ("People do not fall asleep only when they are in bed.",
         "Abantu tibagwijagiirra omubitabu honka."),
        ("Is this the only place you have seen?", "Hanu honka nuho obaine?"),
        ("Sit only on the form.", "Mwikaarre harubbaaho honka."),
        ("Both sides of this cloth are alike.", "Hombi, omunda n'aheeru y'orugoye runu nihasisana."),
        ("I did not reach the very spot.", "Ho hoonyini ntahikeho."),
    ]

    # ── dara + locative ───────────────────────────────────────────────────────
    pairs += [
        ("Here I come to the place where he hid them.", "Daraho nabonaho ha yabiserekere."),
        ("I am sure it is in here.", "Daramunu da, hati nuho kiri."),
        ("I am sure it is from here that the thief climbed in.",
         "Darahanu da, omusuma onu nuho yatembiire."),
        ("Come here, I have something to speak to you.", "Darahanu."),
    ]

    # ── Copula ni- + locatives ────────────────────────────────────────────────
    pairs += [
        ("I sleep in here.", "Munu numwo ndaara."),
        ("This is our home.", "Hanu nuho owaitu."),
        ("I had put it in here.", "Nuho mbaire nkitaire munu."),
        ("Where had you put it?", "Ha obaire okitaire ninkaha?"),
        ("It is in here.", "Nimunu."),
        ("It is in there.", "Nimuli."),
        ("It's here.", "Nihanu."),
        ("It's there.", "Nihali."),
        ("It is on there.", "Naaho."),
        ("It is this way.", "Nukunu."),
        ("It is that direction.", "Nukuli."),
        ("It is there, that side.", "Nooku."),
    ]

    # ── Chapter 6: Sentence examples ─────────────────────────────────────────
    pairs += [
        ("Dogs bark.", "Embwa ziboigora."),
        ("He did not come.", "Uwe ataije."),
        ("The woman has dug a garden.", "Omukazi alimire omusiri."),
        ("There is wax in his ear.", "Ekikoko kimuli omukutu."),
        ("His arm is paining him.", "Omukono gumuli kubi."),
        ("I am feeling pain in one of the ribs.", "Ekintu kindi omurubaju."),
        ("Cattle are useful animals.", "Ente biba bisoro by'omugaso."),
        ("Quarrelling is no good.", "Enkungani teba nungi."),
        ("Once upon a time, a man got married to a woman.",
         "Hakaimuka omusaija, Yaswera mukazi we."),
        ("She bore him four male children.", "Yamuzaarra abaana bana, boojo."),
        ("Where have the boys gone?", "Aboojo bagiiraha?"),
        ("They have gone to play.", "Bagiire kuzaana."),
        ("What do cocks do?", "Enkokoromi ikora ki?"),
        ("They crow.", "Ikooka."),
        ("Have you brought my books?", "Ebitabu byange obireesire?"),
        ("I have.", "Mbireesire."),
        ("Have they given him his walking stick?", "Omwigo gwe bagumuhaire?"),
        ("They have.", "Bagumuhaire."),
        ("Who has broken this glass?", "Ayasire ekirahule kinu nooha?"),
        ("Kisembo has.", "Ni Kisembo."),
        ("I have. (It is I)", "Niinyowe."),
        ("Go.", "Genda."),
        ("Listen.", "Huliiriza."),
        ("Sit down.", "Ikaarra."),
        ("Leave me alone.", "Ndekesa."),
        ("Has the sun risen?", "Izooba lyaturukire?"),
        ("Yes, it has.", "M."),
        ("Do you still remember what I told you?", "Nookyakiijuka?"),
        ("Yes, I do.", "Eee."),
        ("Extend greetings to the people at your home.", "Aboomuka obaramukye."),
        ("Yes, shall.", "Ego."),
        ("What is this?", "Kinu kiki?"),
        ("It is a book.", "Kitabu."),
        ("What do you want?", "Noogonza ki?"),
        ("I want the teacher.", "Omwegesa."),
        ("They have gone.", "Bagenzire."),
        ("They have given it to me.", "Bakimpaire."),
    ]

    # ── Reversed object sentences ─────────────────────────────────────────────
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
    ]

    # ── Sentence types ────────────────────────────────────────────────────────
    pairs += [
        ("Children ought to love their parents.", "Abaana basemeriire kugonza bazaire baabo."),
        ("It is getting late.", "Obwire pwizire."),
        ("I have not eaten yet.", "Tinkaliire."),
        ("The woman who is not your mother does not care to look at your stomach.",
         "Atali nyoko takurora handa."),
        ("Where is your home?", "Owaanyu ni nkaha?"),
        ("What has the bridegroom put on?", "Omugole ajwaire ki?"),
        ("Travellers, have you had a meal?", "Bagenyi mwaliire?"),
        ("It did not take us time to finish it.", "Twakombere."),
        ("Should I then give you this one too?", "Mbahe na kanu?"),
        ("If you do that you will have saved us from starving.", "Tookutujuna."),
        ("May they make the bed for you so that you may sleep?", "Babaarre mubyame?"),
        ("Let them just put the grass right for us only.", "Batusagasagire."),
        ("Will you continue with your journey tomorrow?", "Nyenkya muraagenda?"),
        ("We shall, but with much difficulty.", "Turaagodya."),
        ("Will you start the journey very early?", "Muraazinduka?"),
        ("We shall, just as unwanted guests always do.", "Turaarucwa."),
        ("Have the girls gone?", "Abaisiki bagenzire?"),
        ("Yes, they have gone.", "M, bagenzire."),
        ("Is it true that the girls did not go?", "Abaisiki tibagenzire kwo?"),
        ("Yes, they have not gone.", "M, tibagenzire."),
        ("Come here.", "Ija hanu."),
        ("May God keep you.", "Ruhanga akulinde."),
        ("May you go in peace.", "Ogende n'obusinge."),
        ("May you come, visitor!", "Kaije mugenyi!"),
        ("May you be found at home.", "Kasangwe!"),
        ("Teacher, I beg you to let me go out.", "Mwegesa ninkusaba kuturuka aheeru."),
    ]

    # ── Chapter 7: Noun class examples ───────────────────────────────────────
    pairs += [
        ("person", "omuntu"),
        ("child", "omwana"),
        ("foreigner", "omunyaihanga"),
        ("gloomy person (one who does not laugh)", "omutaseka"),
        ("touchy person", "omutagambwaho"),
        ("dirty person", "omutooga"),
        ("people", "abantu"),
        ("girls", "abaisiki"),
        ("children", "abaana"),
        ("learners", "abeegi"),
        ("teachers", "abeegesa"),
        ("boys", "aboojo"),
        ("builders", "abombeki"),
        ("my grandmother", "mukaaka"),
        ("Mr. Elephant", "warujojo"),
        ("Mr. Rabbit", "wakame"),
        ("Mr. Dog", "wambwa"),
        ("Mr. Hen", "wankoko"),
        ("mosquito", "omubu"),
        ("spirit of the dead", "omuzimu"),
        ("soul", "omwoyo"),
        ("lip", "omunwa"),
        ("year", "omwaka"),
        ("medicine", "omubazi"),
        ("dove", "eriiba"),
        ("tooth", "eriino"),
        ("eye", "eriiso"),
        ("name", "ibara"),
        ("shoulder", "ibega"),
        ("breast", "ibeere"),
        ("debt", "ibanja"),
        ("cow", "ente"),
        ("fowl", "enkoko"),
        ("cat", "enjangu"),
        ("goat", "embuzi"),
        ("axe", "empango"),
        ("rat", "embeba"),
        ("blood", "esagama"),
        ("nose", "enyindo"),
        ("bird", "enyonyi"),
        ("pipe", "enyungu"),
        ("song", "enanga"),
        ("house", "enju"),
        ("professional cultivator", "endimi"),
        ("professional trader", "ensuubuzi"),
        ("incurable liar", "encwangya"),
        ("permanent widow", "enfaakati"),
        ("cloth", "orugoye"),
        ("tongue", "orulimi"),
        ("language", "orulimi"),
        ("office", "ofiisi"),
        ("motor car", "motoka"),
        ("bus", "bbaasi"),
        ("government", "gavumenti"),
        ("money", "sente"),
        ("motorcycle", "pikipiki"),
        ("green (like grass)", "kinyansi"),
        ("white (like white cow)", "kyeru"),
        ("black (like black cow)", "kikara"),
        ("brown (like soil)", "kitaka"),
        ("red/reddish brown", "kigaaja"),
        ("grey", "kibuubi"),
        ("dark brown", "kisiina"),
        ("yellow (like ripe banana)", "kyenju"),
        ("blue", "bbururu"),
        ("purple", "kihuukya"),
        ("Kaseese is near Kilembe.", "Kaseese eri haihi na Kilembe."),
        ("There are more things at Kaseese than at Kabarole.",
         "Kaseese haliyo ebintu bingi okukira Kabarole."),
        ("All their cattle are reddish brown.", "Ente zaabo zoona bigaaju bisa."),
        ("Count separately each group of cows of the same colour.",
         "Buli nte ez'erangi emu muzibale zonka."),
        ("big/disrespectful man", "isaija"),
        ("youth acting badly", "isigazi"),
        ("insolent child", "eryana"),
        ("clumsy/contemptible man", "ekisaija"),
        ("dear poor man (affection)", "ekiiru"),
        ("one who does not laugh", "omutaseka"),
        ("one who does not take a bath", "omutooga"),
        ("one who is easily offended", "omutagambwaho"),
        ("Creator", "Ruhanga"),
        ("He who gives", "Rugaba"),
        ("angel", "Malaika"),
        ("devil", "Sitaani"),
        ("prime minister", "Bamuroga"),
        ("governor", "Gavana"),
        ("president", "Prezidenti"),
        ("minister", "Minista"),
        ("secretary", "Sekeretare"),
    ]

    # ── Twin names and birth order ────────────────────────────────────────────
    pairs += [
        ("first twin (female)", "Nyangoma"),
        ("first twin (male)", "Isingoma"),
        ("second twin (female)", "Nyakato"),
        ("second twin (male)", "Kato"),
        ("father of twins", "Isaabarongo"),
        ("mother of twins", "Nyinaabarongo"),
    ]

    # ── Names of relationship (extended from gr4) ─────────────────────────────
    pairs += [
        ("my father", "Isenyowe"),
        ("my mother", "Nyinanyowe"),
        ("my grandfather", "Isenkurunyowe"),
        ("my paternal aunt", "Isenkatinyowe"),
        ("my maternal aunt", "Nyinentonyowe"),
        ("my maternal uncle", "Nyinaruminyowe"),
        ("my paternal uncle", "Isentonyowe"),
        ("your father", "so"),
        ("your mother", "nyoko"),
        ("your grandfather", "Swenkuru"),
        ("your grandmother", "Nyakwenkuru"),
        ("his father", "Ise"),
        ("his mother", "Nyina"),
        ("his grandfather", "Isenkuru"),
        ("his grandmother", "Nyinenkuru"),
        ("our father", "Isiitwe"),
        ("our mother", "Nyinaitwe"),
        ("our grandfather", "Isenkurwitwe"),
        ("our grandmother", "Nyinenkurwitwe"),
        ("their father", "Isebo"),
        ("their mother", "Nyinabo"),
        ("their grandfather", "Isenkurubo"),
        ("their grandmother", "Nyinenkurubo"),
        ("my father-in-law", "Isezaaranyowe"),
        ("my mother-in-law", "Nyinazaaranyowe"),
        ("my husband", "Ibanyowe"),
        ("his father-in-law", "Isezaara"),
        ("his mother-in-law", "Nyinazaara"),
        ("her husband", "Iba"),
        ("one's father", "Isemuntu"),
        ("one's mother", "Nyinamuntu"),
        ("one's grandfather", "Isenkurumuntu"),
        ("one's grandmother", "Nyinenkurumuntu"),
        ("sister-in-law", "Karamu"),
    ]

    return pairs


# ── Clean and deduplicate ─────────────────────────────────────────────────────

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

def main():
    print("=== Grammar Rules 5 Training Pair Extraction ===\n")

    raw   = get_all_pairs()
    clean = clean_pairs(raw)
    print(f"Raw pairs:            {len(raw)}")
    print(f"After deduplication:  {len(clean)}")

    write_csv(GR5_CSV, clean)

    split      = int(len(clean) * 0.9)
    train_pairs = clean[:split]
    val_pairs   = clean[split:]

    print(f"\nMerging into training data...")
    n_train = append_to_csv(TRAIN_CSV, train_pairs)
    n_val   = append_to_csv(VAL_CSV,   val_pairs)

    print(f"  Added {n_train} new pairs to train.csv")
    print(f"  Added {n_val}   new pairs to val.csv")
    print(f"\nDone. Total gr5 pairs: {len(clean)}")
    print(f"Run `python train_marian.py --epochs 3 --direction both` to retrain.")


if __name__ == "__main__":
    main()
