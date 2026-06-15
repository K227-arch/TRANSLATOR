"""Push benchmark_scores.csv and benchmark_scores.json to both GitHub repos."""
import json, base64, urllib.request
from pathlib import Path

BASE = Path("backend")
REPOS = ["chriskagenda/TRANSLATOR", "K227-arch/TRANSLATOR"]
FILES = {
    "lunyoro-translator/backend/feedback/benchmark_scores.csv":
        BASE / "feedback/benchmark_scores.csv",
    "lunyoro-translator/backend/feedback/benchmark_scores.json":
        BASE / "feedback/benchmark_scores.json",
}

token = ""
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("GITHUB_TOKEN="):
        token = line.split("=", 1)[1].strip()

def get_sha(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref=main"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "runyoro-translator",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("sha")
    except:
        return None

def push_file(repo, gh_path, local_path):
    content = base64.b64encode(local_path.read_bytes()).decode("utf-8")
    sha = get_sha(repo, gh_path)
    payload = {
        "message": f"feedback: add {local_path.name} with {local_path.stat().st_size} bytes",
        "content": content,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/{gh_path}",
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
        with urllib.request.urlopen(req, timeout=20) as r:
            json.loads(r.read())
        print(f"  Pushed {local_path.name} to {repo}")
    except Exception as e:
        print(f"  Failed {local_path.name} to {repo}: {e}")

print("Pushing benchmark files to GitHub...")
for gh_path, local_path in FILES.items():
    if local_path.exists():
        for repo in REPOS:
            push_file(repo, gh_path, local_path)
    else:
        print(f"  {local_path.name}: NOT FOUND locally")

print("Done.")
