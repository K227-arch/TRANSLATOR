import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
api.upload_file(
    path_or_fileobj="_hf_job_train.py",
    path_in_repo="_hf_job_train.py",
    repo_id="keithtwesigye/runyoro-translator-api",
    repo_type="space",
    commit_message="Add HF job training script",
)
print("OK: _hf_job_train.py uploaded to Space")
