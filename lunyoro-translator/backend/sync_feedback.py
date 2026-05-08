"""
sync_feedback.py
================
Polls GitHub every 2 minutes and updates local feedback_pairs.json automatically.
Run once: python sync_feedback.py
Run as watcher: python sync_feedback.py --watch
"""
import os
import json
import base64
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR    = Path(__file__).parent
LOCAL_FILE  = BASE_DIR / "feedback" / "feedback_pairs.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO        = "chriskagenda/TRANSLATOR"
REMOTE_PATH = "lunyoro-translator/backend/feedback/feedback_pairs.json"
POLL_INTERVAL = 120  # seconds


def fetch_from_github() -> list | None:
    url = f"https://api.github.com/repos/{REPO}/contents/{REMOTE_PATH}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "translator-sync",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read())
            return json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    except Exception as e:
        print(f"[sync] Fetch error: {e}")
        return None


def sync_once():
    remote = fetch_from_github()
    if remote is None:
        return False

    # Read local
    local = []
    if LOCAL_FILE.exists():
        try:
            local = json.loads(LOCAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            local = []

    if len(remote) == len(local):
        print(f"[sync] Up to date ({len(local)} entries)")
        return False

    # Write updated file
    LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_FILE.write_text(
        json.dumps(remote, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[sync] Updated: {len(local)} → {len(remote)} entries")
    return True


def watch():
    print(f"[sync] Watching GitHub every {POLL_INTERVAL}s — Ctrl+C to stop")
    while True:
        sync_once()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    import sys
    if "--watch" in sys.argv:
        watch()
    else:
        sync_once()
