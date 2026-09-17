import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
api.upload_file(
    path_or_fileobj="_job_train_sp17.py",
    path_in_repo="_job_train_sp17.py",
    repo_id="keithtwesigye/runyoro-translator-api",
    repo_type="space",
    commit_message="Add SP17 continual training job script",
)
print("OK: _job_train_sp17.py uploaded to Space")
