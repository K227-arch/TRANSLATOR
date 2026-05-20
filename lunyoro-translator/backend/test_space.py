import urllib.request, json

BASE = "https://keithtwesigye-runyoro-translator-api.hf.space"
tests = [
    "today is tuesday",
    "today is monday",
    "today is friday",
    "the book is on the table",
    "how are you",
]

for t in tests:
    data = json.dumps({"text": t}).encode()
    req = urllib.request.Request(
        BASE + "/translate", data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        print(f"EN:     {t}")
        print(f"NLLB:   {result.get('translation_nllb')}")
        print(f"Marian: {result.get('translation_marian')}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        break
