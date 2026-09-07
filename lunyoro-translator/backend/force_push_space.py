"""
Force-push specific files to HF Space, bypassing deduplication.
Uses create_commit so HF always processes a new commit and triggers a rebuild.
"""
import os
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd

token = os.environ.get("HF_TOKEN", "")
if not token:
    raise SystemExit("HF_TOKEN not set")

api = HfApi(token=token)
SPACE_ID    = "keithtwesigye/runyoro-translator-api"
BACKEND_DIR = Path(__file__).parent
SPACE_DIR   = BACKEND_DIR.parent / "hf-space"

# Files that changed — force commit them
files_to_force = [
    (BACKEND_DIR / "translate.py",  "translate.py"),
    (BACKEND_DIR / "main.py",       "main.py"),
    (SPACE_DIR   / "Dockerfile",    "Dockerfile"),
]

ops = []
for local, repo_path in files_to_force:
    if not local.exists():
        print(f"  [SKIP] {local} not found")
        continue
    print(f"  Staging {repo_path} ({local.stat().st_size:,} bytes)")
    ops.append(CommitOperationAdd(path_in_repo=repo_path, path_or_fileobj=str(local)))

if not ops:
    raise SystemExit("Nothing to commit")

result = api.create_commit(
    repo_id=SPACE_ID,
    repo_type="space",
    operations=ops,
    commit_message="fix: NLLB via HF Inference API when DISABLE_NLLB=1 (cpu-basic Space)",
)
print(f"Committed: {result.commit_url}")
print("Space will rebuild now — wait ~5 min then test /translate again")
