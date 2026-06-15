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
GITHUB_FILE_PATH      = "lunyoro-translator/backend/feedback/feedback_pairs.json"
GITHUB_JSONL_PATH     = "lunyoro-translator/backend/feedback/feedback_all.jsonl"
GITHUB_BENCH_CSV_PATH = "lunyoro-translator/backend/feedback/benchmark_scores.csv"
GITHUB_BENCH_JSON_PATH= "lunyoro-translator/backend/feedback/benchmark_scores.json"
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


def _get_raw_file(repo: str, path: str) -> tuple[str, str | None]:
    """Fetch a raw text file from GitHub. Returns (content_str, sha)."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={GITHUB_BRANCH}"
    result = _api_request(url)
    if not result:
        return "", None
    try:
        content = base64.b64decode(result["content"]).decode("utf-8")
        return content, result["sha"]
    except Exception as e:
        print(f"[github_sync] Parse error for {repo}/{path}: {e}")
        return "", result.get("sha")


def _put_raw_file(repo: str, path: str, content_str: str, sha: str | None, message: str):
    """Commit a raw text file to GitHub."""
    content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    data = {"message": message, "content": content, "branch": GITHUB_BRANCH}
    if sha:
        data["sha"] = sha
    return _api_request(url, method="PUT", data=data)


def sync_entry_to_repo(repo: str, entry: dict):
    """
    Fetch, append, and push one entry to a single repo (thread-safe per repo).
    Updates both:
      - feedback_pairs.json  (JSON array — used by restore_from_github)
      - feedback_all.jsonl   (JSONL — full raw log, one entry per line)
    """
    with _lock:
        ts = entry.get("timestamp", datetime.utcnow().isoformat())[:10]

        # ── 1. Update feedback_pairs.json (JSON array) ────────────────────────
        entries, sha_json = _get_file(repo)
        # Deduplicate: don't add if same source+translation+timestamp already present
        key = (
            entry.get("source_text", "").strip().lower(),
            entry.get("translation", "").strip().lower(),
            entry.get("timestamp", "")[:16],
        )
        existing_keys = {
            (e.get("source_text", "").strip().lower(),
             e.get("translation", "").strip().lower(),
             (e.get("timestamp") or "")[:16])
            for e in entries
        }
        if key not in existing_keys:
            entries.append(entry)
            result = _put_file(
                repo, entries, sha_json,
                message=f"feedback: add entry {ts} (total: {len(entries)})"
            )
            if result:
                print(f"[github_sync] feedback_pairs.json ✓ {repo} — {len(entries)} entries")
            else:
                print(f"[github_sync] feedback_pairs.json ✗ Failed for {repo}")

        # ── 2. Append to feedback_all.jsonl (raw JSONL log) ───────────────────
        jsonl_content, sha_jsonl = _get_raw_file(repo, GITHUB_JSONL_PATH)
        # Only append if this exact line isn't already there
        new_line = json.dumps(entry, ensure_ascii=False)
        if new_line not in jsonl_content:
            updated_jsonl = (jsonl_content.rstrip("\n") + "\n" + new_line + "\n").lstrip("\n")
            line_count = len([l for l in updated_jsonl.splitlines() if l.strip()])
            result = _put_raw_file(
                repo, GITHUB_JSONL_PATH, updated_jsonl, sha_jsonl,
                message=f"feedback: append to jsonl {ts} ({line_count} lines)"
            )
            if result:
                print(f"[github_sync] feedback_all.jsonl  ✓ {repo} — {line_count} lines")
            else:
                print(f"[github_sync] feedback_all.jsonl  ✗ Failed for {repo}")


def push_benchmark_files_to_github(entries: list):
    """
    Push benchmark_scores.csv and benchmark_scores.json to GitHub.
    Called after a benchmark entry is saved. Non-blocking.
    Only pushes entries that have SQS scores.
    """
    if not GITHUB_TOKEN:
        return

    bench_entries = [e for e in entries if e.get("sqs") is not None]
    if not bench_entries:
        return

    # Build CSV content
    dim_keys = ['score_mng','score_grm','score_tns','score_vcb',
                'score_ort','score_ctx','score_flu','score_cul','sqs']
    headers = ['timestamp','direction','source_text','translation',
               'model_used','domain','rating'] + dim_keys + ['sqs_band']

    def sqs_band(s):
        try:
            s = float(s)
            if s >= 90: return 'Excellent'
            if s >= 75: return 'Good'
            if s >= 60: return 'Usable'
            if s >= 40: return 'Poor'
            return 'Unusable'
        except: return ''

    csv_lines = [','.join(headers)]
    for e in bench_entries:
        row = []
        for h in headers:
            if h == 'sqs_band':
                row.append(sqs_band(e.get('sqs')))
            else:
                val = str(e.get(h, '') or '').replace(',', ';').replace('\n', ' ')
                row.append(val)
        csv_lines.append(','.join(row))
    csv_content = '\n'.join(csv_lines) + '\n'

    # Build JSON content
    json_content = json.dumps(bench_entries, ensure_ascii=False, indent=2)

    ts = datetime.utcnow().strftime('%Y-%m-%d')
    for repo in GITHUB_REPOS:
        def _push(r=repo):
            _, sha_csv  = _get_raw_file(r, GITHUB_BENCH_CSV_PATH)
            _, sha_json = _get_raw_file(r, GITHUB_BENCH_JSON_PATH)
            _put_raw_file(r, GITHUB_BENCH_CSV_PATH,  csv_content,  sha_csv,
                          f"feedback: update benchmark_scores.csv {ts} ({len(bench_entries)} entries)")
            _put_raw_file(r, GITHUB_BENCH_JSON_PATH, json_content, sha_json,
                          f"feedback: update benchmark_scores.json {ts} ({len(bench_entries)} entries)")
            print(f"[github_sync] benchmark files synced to {r}")
        threading.Thread(target=_push, daemon=True).start()


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
    Fetch the full feedback history from GitHub.
    Prefers feedback_all.jsonl (complete raw log) over feedback_pairs.json.
    Used by restore_from_github() on container startup.
    """
    if not GITHUB_TOKEN:
        return []

    repo = GITHUB_REPOS[0]

    # Try JSONL first — it's the most complete
    jsonl_content, _ = _get_raw_file(repo, GITHUB_JSONL_PATH)
    if jsonl_content.strip():
        entries = []
        for line in jsonl_content.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        if entries:
            print(f"[github_sync] Loaded {len(entries)} entries from feedback_all.jsonl")
            return entries

    # Fallback to JSON array
    entries, _ = _get_file(repo)
    print(f"[github_sync] Loaded {len(entries)} entries from feedback_pairs.json (fallback)")
    return entries
