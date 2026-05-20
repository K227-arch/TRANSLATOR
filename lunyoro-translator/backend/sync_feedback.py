"""
sync_feedback.py
================
Pulls all feedback from the live HuggingFace Space into local files,
merges with existing local feedback_pairs.json, and pushes the merged
result back to both GitHub repos.

Usage:
    python sync_feedback.py
"""

import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE         = Path(__file__).parent
FEEDBACK_DIR = BASE / "feedback"
LOCAL_JSON   = FEEDBACK_DIR / "feedback_pairs.json"
LOCAL_JSONL  = BASE / "feedback.jsonl"

SPACE_URL    = "https://keithtwesigye-runyoro-translator-api.hf.space"
SPACE_DUMP   = f"{SPACE_URL}/feedback/dump"
GITHUB_FILE  = "lunyoro-translator/backend/feedback/feedback_pairs.json"
GITHUB_REPOS = ["chriskagenda/TRANSLATOR", "K227-arch/TRANSLATOR"]


def load_env_token(key: str) -> str:
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return os.getenv(key, "")


def fetch_space_entries() -> tuple[list, int]:
    """
    Pull all raw entries from the Space's /feedback/dump endpoint.
    Falls back to analytics-only count if the endpoint isn't live yet.
    Returns (entries_list, total_count).
    """
    # Try the dump endpoint first (available after latest deploy)
    try:
        with urllib.request.urlopen(SPACE_DUMP, timeout=30) as res:
            data = json.loads(res.read())
        entries = data.get("entries", [])
        print(f"  Space /feedback/dump  : {len(entries)} entries pulled")
        return entries, len(entries)
    except Exception as e:
        print(f"  Space /feedback/dump not available yet: {e}")

    # Fallback: just get the count from analytics
    try:
        url = f"{SPACE_URL}/feedback/analytics"
        with urllib.request.urlopen(url, timeout=20) as res:
            analytics = json.loads(res.read())
        total = analytics.get("total_feedback", 0)
        print(f"  Space /feedback/analytics: {total} entries total (dump endpoint not yet live)")
        return [], total
    except Exception as e:
        print(f"  Could not reach Space: {e}")
        return [], 0


def fetch_github_entries(repo: str, token: str) -> tuple[list, str]:
    """Fetch feedback_pairs.json from a GitHub repo. Returns (entries, sha)."""
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE}?ref=main"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "runyoro-translator",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read())
        content = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
        return content, data.get("sha", "")
    except Exception as e:
        print(f"  GitHub {repo}: ERROR - {e}")
        return [], ""


def push_github(repo: str, token: str, entries: list, sha: str, count: int):
    """Push updated feedback_pairs.json to GitHub."""
    content = base64.b64encode(
        json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE}"
    payload = {
        "message": f"feedback: sync {count} entries ({datetime.utcnow().strftime('%Y-%m-%d')})",
        "content": content,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "runyoro-translator",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            json.loads(res.read())
        print(f"  Pushed {count} entries to {repo}")
    except Exception as e:
        print(f"  Failed to push to {repo}: {e}")


def rebuild_jsonl(entries: list):
    """Rewrite feedback.jsonl from the merged entries list."""
    with open(LOCAL_JSONL, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"  Rewrote feedback.jsonl ({len(entries)} lines)")


def export_csv(entries: list):
    """Export all_feedback.csv and approved_pairs.csv."""
    try:
        import pandas as pd
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(entries)

        # all_feedback.csv — write to a temp name first to avoid locked-file errors
        csv_path = FEEDBACK_DIR / "all_feedback.csv"
        tmp_path = FEEDBACK_DIR / "all_feedback_tmp.csv"
        df.to_csv(tmp_path, index=False, encoding="utf-8")
        try:
            tmp_path.replace(csv_path)
        except PermissionError:
            print(f"  all_feedback.csv is open in another program — saved as all_feedback_tmp.csv instead")
        print(f"  Exported {len(df)} total entries -> feedback/all_feedback.csv")

        # approved_pairs.csv — positive ratings only
        rows = []
        for e in entries:
            if e.get("rating", 0) >= 1:
                src = (e.get("source_text") or "").strip()
                tgt = (e.get("correction") or e.get("translation") or "").strip()
                direction = e.get("direction", "en->lun")
                if src and tgt and src.lower() != tgt.lower():
                    if direction in ("en->lun", "en\u2192lun"):
                        rows.append({"english": src, "lunyoro": tgt})
                    else:
                        rows.append({"english": tgt, "lunyoro": src})
        if rows:
            pd.DataFrame(rows).drop_duplicates().to_csv(
                FEEDBACK_DIR / "approved_pairs.csv", index=False, encoding="utf-8"
            )
            print(f"  Exported {len(rows)} approved pairs -> feedback/approved_pairs.csv")
    except ImportError:
        print("  pandas not available — skipping CSV export")


def main():
    print("\n=== Feedback Sync: Space -> Local + GitHub ===\n")

    github_token = load_env_token("GITHUB_TOKEN")
    if not github_token:
        print("WARNING: No GITHUB_TOKEN in .env — GitHub push will be skipped")

    # 1. Load local
    local_entries = []
    if LOCAL_JSON.exists():
        local_entries = json.loads(LOCAL_JSON.read_text(encoding="utf-8"))
    print(f"Local feedback_pairs.json : {len(local_entries)} entries")

    # 2. Fetch from GitHub repos — prefer feedback_all.jsonl over feedback_pairs.json
    all_github: list[list] = []
    shas: dict = {}
    if github_token:
        for repo in GITHUB_REPOS:
            # Try JSONL first (more complete)
            jsonl_url = f"https://api.github.com/repos/{repo}/contents/lunyoro-translator/backend/feedback/feedback_all.jsonl?ref=main"
            req = urllib.request.Request(jsonl_url, headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "runyoro-translator",
            })
            jsonl_entries = []
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    data = json.loads(res.read())
                raw = base64.b64decode(data["content"]).decode("utf-8")
                for line in raw.splitlines():
                    line = line.strip()
                    if line:
                        try:
                            jsonl_entries.append(json.loads(line))
                        except Exception:
                            pass
                print(f"GitHub {repo:<35}: {len(jsonl_entries)} entries (jsonl)")
            except Exception:
                # Fall back to JSON array
                gh_entries, sha = fetch_github_entries(repo, github_token)
                jsonl_entries = gh_entries
                shas[repo] = sha
                print(f"GitHub {repo:<35}: {len(jsonl_entries)} entries (json array fallback)")
            all_github.append(jsonl_entries)

    # 3. Fetch from live Space (dump endpoint)
    space_entries, space_total = fetch_space_entries()

    # 4. Merge all sources — deduplicate by (source_text, translation, timestamp[:16])
    seen: set = set()
    merged: list = []

    def add_entries(source_list: list):
        for e in source_list:
            key = (
                (e.get("source_text") or "").strip().lower(),
                (e.get("translation") or "").strip().lower(),
                (e.get("timestamp") or "")[:16],
            )
            if key[0] and key not in seen:
                seen.add(key)
                merged.append(e)

    # Priority: Space (freshest) > local > github[0] > github[1]
    add_entries(space_entries)
    add_entries(local_entries)
    for gh_entries in all_github:
        add_entries(gh_entries)

    print(f"\nMerged total             : {len(merged)} unique entries")

    if space_total > len(merged):
        gap = space_total - len(merged)
        print(f"\n  {gap} entries are still only in the Space container.")
        print("  They will appear here after the Space restarts (ephemeral storage).")
        print("  Re-run this script after the Space finishes restarting to get them all.")

    # 5. Save locally
    print("\nSaving locally...")
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_JSON.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Saved feedback_pairs.json ({len(merged)} entries)")
    rebuild_jsonl(merged)
    export_csv(merged)

    # 6. Push merged result back to GitHub
    if github_token and merged:
        print("\nPushing merged entries to GitHub...")
        for repo in GITHUB_REPOS:
            push_github(repo, github_token, merged, shas.get(repo, ""), len(merged))

    # 7. Summary
    positive    = sum(1 for e in merged if e.get("rating", 0) > 0)
    negative    = sum(1 for e in merged if e.get("rating", 0) < 0)
    corrections = sum(1 for e in merged if (e.get("correction") or "").strip())
    print(f"\n{'='*45}")
    print(f"  Total local entries : {len(merged)}")
    print(f"  Positive (thumbs up): {positive}")
    print(f"  Negative (thumbs dn): {negative}")
    print(f"  With correction     : {corrections}")
    print(f"  Space total         : {space_total}  "
          f"({'in sync' if space_total <= len(merged) else str(space_total - len(merged)) + ' still in container'})")
    print(f"{'='*45}\n")


if __name__ == "__main__":
    main()
