"""
Add a greeting correction map to translate.py.
Fixes common phrases where the model produces the wrong variant
e.g. "How are you?" -> "Oirirwe ota" (morning) instead of "Oli ota" (general).
"""
path = "translate.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add greeting correction map after the imports
greeting_map = '''
# ── Common greeting corrections ──────────────────────────────────────────────
# The model sometimes maps general greetings to time-specific variants.
# These overrides ensure the most natural/common form is used.
_GREETING_CORRECTIONS_EN2LUN = {
    "how are you": "Oli ota?",
    "how are you?": "Oli ota?",
    "how are you doing": "Oli ota?",
    "how are you doing?": "Oli ota?",
    "how do you do": "Oli ota?",
    "good morning": "Oraire ota?",
    "good morning!": "Oraire ota?",
    "good afternoon": "Osibye ota?",
    "good evening": "Osibye ota?",
    "good night": "Oire ota?",
    "hello": "Agandi",
    "hello!": "Agandi!",
    "hi": "Agandi",
    "hi!": "Agandi!",
    "welcome": "Karibu",
    "goodbye": "Weebale",
    "bye": "Weebale",
    "see you later": "Tuzoonaganana",
    "thank you": "Weebale",
    "thank you very much": "Weebale nyo",
    "thanks": "Weebale",
    "please": "Nsaba",
    "sorry": "Onsonyiwa",
    "excuse me": "Onsonyiwa",
    "yes": "Ego",
    "no": "Batako",
}

_GREETING_CORRECTIONS_LUN2EN = {
    "agandi": "Hello / How are you?",
    "agandi?": "Hello / How are you?",
    "oli ota": "How are you?",
    "oli ota?": "How are you?",
    "oraire ota": "Good morning / How did you sleep?",
    "oraire ota?": "Good morning / How did you sleep?",
    "osibye ota": "Good afternoon / How has your day been?",
    "osibye ota?": "Good afternoon / How has your day been?",
    "weebale": "Thank you",
    "weebale nyo": "Thank you very much",
    "weebale muno": "Thank you very much",
    "karibu": "Welcome / You are welcome",
    "ego": "Yes",
    "batako": "No",
    "nsaba": "Please",
    "onsonyiwa": "Sorry / Excuse me",
}


def _apply_greeting_correction(text: str, direction: str) -> str | None:
    """Return a hardcoded correction for common greetings, or None if not applicable."""
    key = text.strip().lower().rstrip(".,!?;").strip()
    if direction == "en2lun":
        return _GREETING_CORRECTIONS_EN2LUN.get(key)
    else:
        return _GREETING_CORRECTIONS_LUN2EN.get(key)

'''

# Insert after the last import line
insert_after = "HF_USERNAME}/lunyoro-sentence-embeddings\",\n}"
if insert_after in content:
    content = content.replace(insert_after, insert_after + "\n" + greeting_map, 1)
    print("Greeting map inserted")
else:
    # fallback: insert after HF_MODELS dict
    insert_after2 = '"sem_model": f"{HF_USERNAME}/lunyoro-sentence-embeddings",\n}'
    if insert_after2 in content:
        content = content.replace(insert_after2, insert_after2 + "\n" + greeting_map, 1)
        print("Greeting map inserted (fallback)")
    else:
        print("ERROR: insertion point not found")
        import sys; sys.exit(1)

# Now hook it into _nllb_translate — apply correction before calling model
# Find the _nllb_translate function entry point
old_nllb_start = '    # \u2500\u2500 Remote API path (explicitly requested or local model unavailable) \u2500\u2500\u2500\u2500\n    if os.getenv("DISABLE_NLLB", "").strip() in ("1", "true", "yes"):'
new_nllb_start = '''    # ── Greeting shortcut — skip neural model for common phrases ──────────────
    greeting = _apply_greeting_correction(text, direction)
    if greeting:
        return greeting

    # ── Remote API path (explicitly requested or local model unavailable) ────
    if os.getenv("DISABLE_NLLB", "").strip() in ("1", "true", "yes"):'''

if old_nllb_start in content:
    content = content.replace(old_nllb_start, new_nllb_start, 1)
    print("Greeting hook added to _nllb_translate")
else:
    print("WARNING: _nllb_translate hook not added — pattern not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")
