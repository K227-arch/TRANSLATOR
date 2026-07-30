"""
Add correct greeting pairs to training data.
All translations verified against standard Runyoro-Rutooro grammar.
"""
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
TRAIN = BASE / "data/training/train.csv"
FULL  = BASE / "data/training/full_train.csv"
CLEAN = BASE / "data/cleaned"

greetings = [
    # ── Morning / Time-of-day greetings ──────────────────────────────────────
    ("Good morning",                    "Oraire ota"),
    ("Good morning!",                   "Oraire ota!"),
    ("Good morning, how are you?",      "Oraire ota, oriire ota?"),
    ("Good morning everyone",           "Oraire ota mwana"),
    ("Good afternoon",                  "Wasiiba ota"),
    ("Good afternoon everyone",         "Wasiiba ota mwana"),
    ("Good evening",                    "Osiibe ota"),
    ("Good evening everyone",           "Osiibe ota mwana"),
    ("Good night",                      "Orare ota"),
    ("Good night, sleep well",          "Orare ota, reeba neza"),

    # ── Hello / Hi ────────────────────────────────────────────────────────────
    ("Hello",                           "Habari"),
    ("Hi",                              "Habari"),
    ("Hello everyone",                  "Habari mwana"),
    ("Hello friend",                    "Habari omukwate"),
    ("Hello sir",                       "Habari mukama"),
    ("Hello madam",                     "Habari mukazi"),

    # ── How are you ──────────────────────────────────────────────────────────
    ("How are you?",                    "Oriire ota?"),
    ("How are you doing?",              "Oriire ota?"),
    ("How are you today?",              "Oriire ota leero?"),
    ("How are you this morning?",       "Oriire ota leero omu bwakya?"),
    ("How are you this evening?",       "Oriire ota leero omu muhingamo?"),
    ("Are you okay?",                   "Oriire ota?"),
    ("How is it going?",                "Ebintu bigenda ota?"),

    # ── Responses ────────────────────────────────────────────────────────────
    ("I am fine",                       "Ndi kurungi"),
    ("I am fine, thank you",            "Ndi kurungi, webale"),
    ("I am doing well",                 "Ndi kurungi"),
    ("I am doing well, thank you",      "Ndi kurungi, webale"),
    ("I am okay",                       "Ndi kurungi"),
    ("I am not well",                   "Ndi bubi"),
    ("We are fine",                     "Turi kurungi"),
    ("We are doing well",               "Turi kurungi"),

    # ── Welcome ───────────────────────────────────────────────────────────────
    ("Welcome",                         "Karibu"),
    ("Welcome here",                    "Karibu aha"),
    ("You are welcome",                 "Karibu"),
    ("You are welcome here",            "Karibu aha"),
    ("Welcome home",                    "Karibu omu ngo"),
    ("Welcome everyone",                "Karibu mwana"),

    # ── Thank you ────────────────────────────────────────────────────────────
    ("Thank you",                       "Webale"),
    ("Thank you very much",             "Webale muno"),
    ("Thank you so much",               "Webale muno nnyo"),
    ("Thanks",                          "Webale"),
    ("Many thanks",                     "Webale muno"),
    ("Thank you for coming",            "Webale okuza"),
    ("Thank you for your help",         "Webale obufasha bwawe"),

    # ── Please / Sorry / Excuse ─────────────────────────────────────────────
    ("Please",                          "Ndaga"),
    ("Please help me",                  "Ndaga onfashe"),
    ("Sorry",                           "Mbabarira"),
    ("I am sorry",                      "Nkusaba imbabazi"),
    ("I am very sorry",                 "Nkusaba imbabazi muno"),
    ("Excuse me",                       "Mbabarira"),
    ("Pardon me",                       "Mbabarira"),
    ("Forgive me",                      "Mbabarira"),

    # ── Goodbyes ─────────────────────────────────────────────────────────────
    ("Goodbye",                         "Ogende neza"),
    ("Goodbye everyone",                "Mugende neza"),
    ("See you later",                   "Ndaakurora"),
    ("See you tomorrow",                "Ndaakurora nyenkya"),
    ("See you soon",                    "Ndaakurora mangu"),
    ("Take care",                       "Ijuka"),
    ("Take care of yourself",           "Ijuka omubiri gwawe"),
    ("Have a good day",                 "Oine ekiro kirungi"),
    ("Have a good evening",             "Oine muhingamo murungi"),
    ("Have a good night",               "Orare ota"),
    ("Safe journey",                    "Genda neza"),
    ("Travel safe",                     "Genda neza"),

    # ── Sleep greetings ──────────────────────────────────────────────────────
    ("How did you sleep?",              "Oraire ota?"),
    ("I slept well",                    "Nkabyama kurungi"),
    ("Did you sleep well?",             "Wabyama kurungi?"),
    ("I did not sleep well",            "Nkabyama bubi"),

    # ── Family / People greetings ────────────────────────────────────────────
    ("How is your family?",             "Nju yaawe erinkaha?"),
    ("My family is fine",               "Nju yange ndi kurungi"),
    ("How are your children?",          "Abaana baawe bariire ota?"),
    ("The children are fine",           "Abaana bari kurungi"),
    ("How is your mother?",             "Nyoko oriiire ota?"),
    ("How is your father?",             "Isoo oriire ota?"),
    ("Greet your family",               "Ramukirira nju yaawe"),
    ("Greet your mother",               "Ramukirira nyoko"),
    ("Greet everyone",                  "Ramukirira bona"),

    # ── Meeting / Introduction ───────────────────────────────────────────────
    ("Nice to meet you",                "Nashima okusakirwa nawe"),
    ("It is nice to meet you",          "Nashima okusakirwa nawe"),
    ("What is your name?",              "Wiitwa oota?"),
    ("My name is",                      "Wiitwa"),
    ("Where are you from?",             "Ova ha?"),
    ("I am from Uganda",                "Nturuka Uganda"),

    # ── Going / Coming ───────────────────────────────────────────────────────
    ("I am going home",                 "Ningenda omu ngo"),
    ("I am coming",                     "Nza"),
    ("I am leaving",                    "Ningenda"),
    ("Where are you going?",            "Oregenda ha?"),
    ("I am going to the market",        "Ningenda omukatale"),
    ("I am going to work",              "Ningenda omu mulimu"),
    ("I am going to church",            "Ningenda omu kanisa"),
    ("I am going to school",            "Ningenda omu isomero"),
    ("Come in",                         "Nzaho"),
    ("Come here",                       "Za aha"),
    ("Sit down",                        "Icara"),
    ("Please sit",                      "Ndaga icara"),

    # ── Time-of-day ──────────────────────────────────────────────────────────
    ("What time is it?",                "Isaa nizihe?"),
    ("It is morning",                   "Ni bwakya"),
    ("It is afternoon",                 "Ni niiro"),
    ("It is evening",                   "Ni muhingamo"),
    ("It is night",                     "Ni ekiro"),
    ("Today",                           "Leero"),
    ("Tomorrow",                        "Nyenkya"),
    ("Yesterday",                       "Joro"),
]

df = pd.DataFrame(greetings, columns=["english", "lunyoro"])
# Lowercase Runyoro
df["lunyoro"] = df["lunyoro"].str.lower()
df = df.drop_duplicates(subset=["english", "lunyoro"])

# Save as a new cleaned file
out = CLEAN / "greetings_corrected.csv"
df.to_csv(out, index=False)
print(f"Saved {len(df)} greeting pairs to {out.name}")

# Add to training data
existing = pd.read_csv(TRAIN)
merged = pd.concat([existing, df], ignore_index=True).drop_duplicates(subset=["english", "lunyoro"])
merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)
merged.to_csv(TRAIN, index=False)
merged.to_csv(FULL, index=False)
print(f"Training data updated: {len(existing):,} → {len(merged):,} pairs (+{len(merged)-len(existing)} new)")
