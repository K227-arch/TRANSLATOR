"""
seed_github_jsonl.py
====================
One-time script: reads local feedback_pairs.json and pushes all entries
to feedback_all.jsonl on both GitHub repos.
Run once after deploying the new sync code.
"""
import json, base64, urllib.request
from pathlib import Path
from datetime import datetime

BASE         = Path(__file__).parent
LOCAL_JSON   = BASE / "feedback" / "feedback_pairs.json"
GITHUB_JSONL = "lunyoro-translator/backend/feedback/feedback_all.jsonl"
GITHUB_REPOS = ["chriskagenda/TRANSLATOR", "K227-arch/TRANSLATOR"]


def load_env_token(key):
    for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def api(url, method="GET", data=None, token=""):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "runyoro-translator",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def get_sha(repo, path, token):
    result = api(f"https://api.github.com/repos/{repo}/contents/{path}?ref=main", token=token)
    return result.get("sha") if result else None


def push_jsonl(repo, entries, token):
    content_str = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    sha = get_sha(repo, GITHUB_JSONL, token)
    payload = {
        "message": f"feedback: seed {len(entries)} entries to jsonl ({datetime.utcnow().strftime('%Y-%m-%d')})",
        "content": content_b64,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    result = api(f"https://api.github.com/repos/{repo}/contents/{GITHUB_JSONL}",
                 method="PUT", data=payload, token=token)
    if result:
        print(f"  Pushed {len(entries)} entries to {repo}")
    else:
        print(f"  Failed for {repo}")


def main():
    token = load_env_token("GITHUB_TOKEN")
    if not token:
        print("No GITHUB_TOKEN in .env"); return

    entries = json.loads(LOCAL_JSON.read_text(encoding="utf-8"))
    print(f"Seeding {len(entries)} entries to feedback_all.jsonl on GitHub...\n")
    for repo in GITHUB_REPOS:
        push_jsonl(repo, entries, token)
    print("\nDone. feedback_all.jsonl is now seeded on both repos.")


if __name__ == "__main__":
    main()
