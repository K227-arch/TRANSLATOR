import urllib.request, json

url = "https://keithtwesigye-runyoro-translator-api.hf.space/translate"
tests = [
    "How many people are visiting today?",
    "The cat is running",
    "Good morning",
    "Where is the hospital?",
    "I love you",
]

for text in tests:
    body = json.dumps({"text": text, "context": "", "refine": False}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        nllb   = data.get("translation_nllb") or "N/A"
        marian = data.get("translation_marian") or "N/A"
        final  = data.get("translation") or "N/A"
        print(f"EN:     {text}")
        print(f"NLLB:   {nllb}")
        print(f"Marian: {marian}")
        print(f"Final:  {final}")
        # Flag if English passthrough detected
        if text.lower()[:15] in nllb.lower():
            print("  *** PASSTHROUGH DETECTED in NLLB ***")
        print()
    except Exception as e:
        print(f"Error [{text}]: {e}")
        print()
