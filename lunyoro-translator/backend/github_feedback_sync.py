"""
github_feedback_sync.py
=======================
Persists feedback_pairs.json to GitHub so data survives HuggingFace Space restarts.

On every feedback submission:
  1. Fetches current feedback_pairs.json from GitHub (main branch)
  2. Appends the new entry
  3. Commits the updated file back to GitHub

Both repos are updated in parallel:
  - chriskagenda/TRANSLATOR
  - K227-arch/TRANSLATOR
"""
import os
import json
import base64
import threading
import urllib.request
import urllib.error
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_FILE_PATH = "lunyoro-translator/backend/feedback/feedback_pairs.json"
GITHUB_BRANCH = "main"

GITHUB_REPOS = [
    "chriskagenda/TRANSLATOR",
    "K227-arch/TRANSLATOR",
]

_lock = threading.Lock()


def _api_request(url: str, method: str = "GET", data: dict = None) -> dict | None:
    """Make a GitHub API request."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "runyoro-translator",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[github_sync] HTTP {e.code} {url}: {body[:200]}")
        return None
    except Exception as e:
        print(f"[github_sync] Error {url}: {e}")
        return None


def _get_file(repo: str) -> tuple[list, str | None]:
    """
    Fetch current feedback_pairs.json from GitHub.
    Returns (entries_list, sha) — sha is needed to update the file.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    result = _api_request(url)
    if not result:
        return [], None
    try:
        content = base64.b64decode(result["content"]).decode("utf-8")
        entries = json.loads(content)
        if not isinstance(entries, list):
            entries = []
        return entries, result["sha"]
    except Exception as e:
        print(f"[github_sync] Parse error for {repo}: {e}")
        return [], result.get("sha")


def _put_file(repo: str, entries: list, sha: str | None, message: str):
    """Commit updated feedback_pairs.json to GitHub."""
    content = base64.b64encode(
        json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")

    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE_PATH}"
    data = {
        "message": message,
        "content": content,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        data["sha"] = sha

    return _api_request(url, method="PUT", data=data)


def sync_entry_to_repo(repo: str, entry: dict):
    """Fetch, append, and push one entry to a single repo (thread-safe per repo)."""
    with _lock:
        entries, sha = _get_file(repo)
        entries.append(entry)
        ts = entry.get("timestamp", datetime.utcnow().isoformat())[:10]
        result = _put_file(
            repo, entries, sha,
            message=f"feedback: add entry {ts} (total: {len(entries)})"
        )
        if result:
            print(f"[github_sync] ✓ {repo} — {len(entries)} entries")
        else:
            print(f"[github_sync] ✗ Failed to sync to {repo}")


def push_feedback_to_github(entry: dict):
    """
    Push a feedback entry to both GitHub repos in background threads.
    Non-blocking — called after each feedback submission.
    """
    if not GITHUB_TOKEN:
        print("[github_sync] No GITHUB_TOKEN set, skipping sync")
        return

    for repo in GITHUB_REPOS:
        threading.Thread(
            target=sync_entry_to_repo,
            args=(repo, entry),
            daemon=True,
        ).start()


def fetch_all_feedback_from_github() -> list:
    """
    Fetch the full feedback_pairs.json from GitHub (primary repo).
    Used by auto_retrain to get all collected feedback.
    """
    if not GITHUB_TOKEN:
        return []
    entries, _ = _get_file(GITHUB_REPOS[0])
    return entries
