import urllib.request, json, base64
from pathlib import Path

BASE = Path("backend")

# ── 1. Space live count ───────────────────────────────────────────────────────
try:
    with urllib.request.urlopen(
        "https://keithtwesigye-runyoro-translator-api.hf.space/feedback/stats",
        timeout=15
    ) as r:
        space = json.loads(r.read())
    print(f"Space (live container)           : {space['total']} entries")
    print(f"  thumbs up  : {space['thumbs_up']}")
    print(f"  thumbs down: {space['thumbs_down']}")
except Exception as e:
    print(f"Space: ERROR - {e}")

# ── 2. GitHub ─────────────────────────────────────────────────────────────────
token = ""
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("GITHUB_TOKEN="):
        token = line.split("=", 1)[1].strip()

REPOS = ["chriskagenda/TRANSLATOR", "K227-arch/TRANSLATOR"]
for repo in REPOS:
    for fname, path in [
        ("feedback_all.jsonl",   "lunyoro-translator/backend/feedback/feedback_all.jsonl"),
        ("feedback_pairs.json",  "lunyoro-translator/backend/feedback/feedback_pairs.json"),
    ]:
        url = f"https://api.github.com/repos/{repo}/contents/{path}?ref=main"
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "runyoro-translator",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            raw = base64.b64decode(data["content"]).decode("utf-8")
            if fname.endswith(".jsonl"):
                count = len([l for l in raw.splitlines() if l.strip()])
            else:
                count = len(json.loads(raw))
            print(f"GitHub {repo:<35} {fname:<25}: {count} entries")
        except Exception as e:
            print(f"GitHub {repo} {fname}: ERROR - {e}")

# ── 3. Local files ────────────────────────────────────────────────────────────
print()
for label, path in [
    ("Local feedback_pairs.json", BASE / "feedback/feedback_pairs.json"),
    ("Local feedback.jsonl",      BASE / "feedback.jsonl"),
]:
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        if str(path).endswith(".json"):
            count = len(json.loads(raw))
        else:
            count = len([l for l in raw.splitlines() if l.strip()])
        print(f"{label:<40}: {count} entries")
    else:
        print(f"{label:<40}: NOT FOUND")
