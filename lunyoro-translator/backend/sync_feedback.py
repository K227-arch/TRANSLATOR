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
GITHUB_FILE  = "lunyoro-translator/backend/feedback/feedback_pairs.json"
GITHUB_REPOS = ["chriskagenda/TRANSLATOR", "K227-arch/TRANSLATOR"]


def load_env_token(key: str) -> str:
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return os.getenv(key, "")


def fetch_space_feedback() -> list[dict]:
    """
    Reconstruct all feedback entries from the Space's analytics endpoint.
    The /feedback/analytics endpoint exposes recent_feedback (last 10),
    so we also pull the full stats to know the total.
    Since there's no raw-dump endpoint, we fetch what's available and
    supplement with the GitHub copy for older entries.
    """
    entries = []

    # 1. Pull the full analytics (has recent_feedback + counts)
    try:
        url = f"{SPACE_URL}/feedback/analytics"
        with urllib.request.urlopen(url, timeout=20) as res:
            analytics = json.loads(res.read())
        print(f"  Space total: {analytics['total_feedback']} entries")
        print(f"  Space recent (last 10): {len(analytics.get('recent_feedback', []))} entries")
    except Exception as e:
        print(f"  Could not reach Space analytics: {e}")
        analytics = {}

    return analytics


def fetch_github_entries(repo: str, token: str) -> tuple[list, str | None]:
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
        return content, data.get("sha")
    except Exception as e:
        print(f"  GitHub {repo}: ERROR - {e}")
        return [], None


def push_github(repo: str, token: str, entries: list, sha: str | None, count: int):
    """Push updated feedback_pairs.json to GitHub."""
    content = base64.b64encode(
        json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_FILE}"
    data = {
        "message": f"feedback: sync {count} entries from Space ({datetime.utcnow().strftime('%Y-%m-%d')})",
        "content": content,
        "branch": "main",
    }
    if sha:
        data["sha"] = sha
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
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
        print(f"  ✓ Pushed {count} entries to {repo}")
    except Exception as e:
        print(f"  ✗ Failed to push to {repo}: {e}")


def rebuild_jsonl(entries: list):
    """Rewrite feedback.jsonl from the merged entries list."""
    with open(LOCAL_JSONL, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"  Rewrote feedback.jsonl ({len(entries)} lines)")


def export_csv(entries: list):
    """Export all_feedback.csv and approved_pairs.csv from merged entries."""
    try:
        import pandas as pd

        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(entries)

        # all_feedback.csv
        df.to_csv(FEEDBACK_DIR / "all_feedback.csv", index=False, encoding="utf-8")

        # approved_pairs.csv — positive ratings only, as en/lunyoro columns
        rows = []
        for e in entries:
            if e.get("rating", 0) >= 1:
                src = (e.get("source_text") or "").strip()
                tgt = (e.get("correction") or e.get("translation") or "").strip()
                direction = e.get("direction", "en→lun")
                if src and tgt and src.lower() != tgt.lower():
                    if "lun" in direction and direction.index("lun") > direction.index("en"):
                        rows.append({"english": src, "lunyoro": tgt})
                    else:
                        rows.append({"english": tgt, "lunyoro": src})

        if rows:
            pd.DataFrame(rows).drop_duplicates().to_csv(
                FEEDBACK_DIR / "approved_pairs.csv", index=False, encoding="utf-8"
            )
            print(f"  Exported {len(rows)} approved pairs → feedback/approved_pairs.csv")

        print(f"  Exported {len(df)} total entries → feedback/all_feedback.csv")
    except ImportError:
        print("  pandas not available — skipping CSV export")


def main():
    print("\n=== Feedback Sync: Space → Local + GitHub ===\n")

    github_token = load_env_token("GITHUB_TOKEN")
    if not github_token:
        print("WARNING: No GITHUB_TOKEN found in .env — GitHub push will be skipped")

    # ── 1. Load local feedback_pairs.json ─────────────────────────────────────
    local_entries = []
    if LOCAL_JSON.exists():
        local_entries = json.loads(LOCAL_JSON.read_text(encoding="utf-8"))
    print(f"Local feedback_pairs.json : {len(local_entries)} entries")

    # ── 2. Fetch from both GitHub repos ───────────────────────────────────────
    all_github: list[list] = []
    shas: dict = {}
    if github_token:
        for repo in GITHUB_REPOS:
            entries, sha = fetch_github_entries(repo, github_token)
            print(f"GitHub {repo:<35}: {len(entries)} entries")
            all_github.append(entries)
            shas[repo] = sha
    else:
        all_github = [[], []]

    # ── 3. Check Space total ───────────────────────────────────────────────────
    analytics = fetch_space_feedback()
    space_total = analytics.get("total_feedback", 0)

    # ── 4. Merge all sources (deduplicate by source_text + translation + timestamp) ──
    seen = set()
    merged = []

    def add_entries(source_list: list):
        for e in source_list:
            key = (
                (e.get("source_text") or "").strip().lower(),
                (e.get("translation") or "").strip().lower(),
                e.get("timestamp", "")[:16],   # minute-level dedup
            )
            if key not in seen and key[0]:
                seen.add(key)
                merged.append(e)

    # Priority: local → github[0] → github[1]
    add_entries(local_entries)
    for gh_entries in all_github:
        add_entries(gh_entries)

    print(f"\nMerged total             : {len(merged)} unique entries")

    if space_total > len(merged):
        print(f"\n⚠  Space has {space_total} entries but only {len(merged)} could be recovered.")
        print("   The remaining entries are in the Space container's ephemeral feedback.jsonl.")
        print("   They will sync to GitHub on the next feedback submission, or you can")
        print("   add a /feedback/dump endpoint to the Space to export them all at once.")

    # ── 5. Save locally ────────────────────────────────────────────────────────
    print("\nSaving locally...")
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_JSON.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Saved feedback_pairs.json ({len(merged)} entries)")
    rebuild_jsonl(merged)
    export_csv(merged)

    # ── 6. Push merged result back to GitHub ───────────────────────────────────
    if github_token and merged:
        print("\nPushing merged entries to GitHub...")
        for repo in GITHUB_REPOS:
            push_github(repo, github_token, merged, shas.get(repo), len(merged))

    # ── 7. Summary ─────────────────────────────────────────────────────────────
    positive = sum(1 for e in merged if e.get("rating", 0) > 0)
    negative = sum(1 for e in merged if e.get("rating", 0) < 0)
    corrections = sum(1 for e in merged if (e.get("correction") or "").strip())
    print(f"\n{'='*45}")
    print(f"  Total entries  : {len(merged)}")
    print(f"  Positive (👍)  : {positive}")
    print(f"  Negative (👎)  : {negative}")
    print(f"  With correction: {corrections}")
    print(f"  Space total    : {space_total}  ({'in sync' if space_total <= len(merged) else f'{space_total - len(merged)} still in container'})")
    print(f"{'='*45}\n")


if __name__ == "__main__":
    main()
