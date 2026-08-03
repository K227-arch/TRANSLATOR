"""
quality_test.py — Grammar, tense, and translation quality evaluation
Tests the NLLB INT8 model (current primary) across key Runyoro linguistic features
"""
import requests

API = "http://localhost:8000"

TESTS = {
    "TENSES": [
        # Present
        ("translate",         "I eat food",                     "ningenda/niliira (present)"),
        ("translate",         "He eats food",                   "aliira (present 3sg)"),
        ("translate",         "We eat food",                    "tuliira (present 1pl)"),
        # Past
        ("translate",         "I ate food",                     "nalya/nalyiire (past)"),
        ("translate",         "He went to the market",          "akagenda omu isoko (remote past)"),
        ("translate",         "She came yesterday",             "yakaza ejo (past)"),
        # Future
        ("translate",         "I will go to school",            "nzagenda isomero (future)"),
        ("translate",         "They will eat tomorrow",         "balyira enkyo (future pl)"),
        # Continuous
        ("translate",         "I am going to the market",       "ningenda omu isoko (present cont)"),
        ("translate",         "She is cooking food",            "ali obuteka (present cont)"),
    ],
    "GRAMMAR AGREEMENT": [
        # Subject-verb agreement
        ("translate",         "The children eat food",          "Abaana baliira (cl.2 concord)"),
        ("translate",         "The cow drinks water",           "Ente iinywera amaazi (cl.9)"),
        ("translate",         "The books are on the table",     "Ebitabo biri haihi (cl.8 concord)"),
        # Possession
        ("translate",         "My father",                      "isange (poss cl.1)"),
        ("translate",         "Our house",                      "Eka yaitu (poss 1pl)"),
        # Object markers
        ("translate",         "I love you",                     "ninkugonza (obj marker ku-)"),
        ("translate",         "He told me",                     "yambwira (obj marker m-)"),
    ],
    "COMPLEX SENTENCES": [
        ("translate",         "If you work hard, you will succeed",       "conditional"),
        ("translate",         "The man who went to the market yesterday", "relative clause"),
        ("translate",         "Give me the food that is on the table",    "relative + obj"),
        ("translate",         "I did not go to school today",             "negation"),
        ("translate",         "We have not eaten yet",                    "perfect negation"),
    ],
    "REVERSE (LUN→EN)": [
        ("translate-reverse", "nagenda omu isoko ejo",          "I went to market yesterday"),
        ("translate-reverse", "nzagenda isomero enkyo",         "I will go to school tomorrow"),
        ("translate-reverse", "Abaana baliira ebyokulya",       "Children eat food"),
        ("translate-reverse", "yabwira ati ningenda",           "He said that I am going"),
        ("translate-reverse", "Ruhanga agonza abantu bona",     "God loves all people"),
        ("translate-reverse", "Omwana atagenda ssomero",        "Child does not go to school"),
    ],
}

def run():
    print("=" * 70)
    print("TRANSLATION QUALITY TEST — Grammar, Tenses, Agreement")
    print("Model: NLLB-200 fine-tuned (INT8 ONNX)")
    print("=" * 70)

    for category, cases in TESTS.items():
        print(f"\n{'─'*70}")
        print(f"  {category}")
        print(f"{'─'*70}")
        for endpoint, text, expected_note in cases:
            try:
                r = requests.post(
                    f"{API}/{endpoint}",
                    json={"text": text, "context": "", "refine": False},
                    timeout=30,
                )
                d = r.json()
                translation = d.get("translation", "ERROR")
                method = d.get("method", "?")
                direction = "EN→LUN" if endpoint == "translate" else "LUN→EN"
                print(f"  {direction}: {text}")
                print(f"    → {translation}  [{method}]")
                print(f"    ✎ expected: {expected_note}")
                print()
            except Exception as e:
                print(f"  ERROR: {e}")

if __name__ == "__main__":
    run()
