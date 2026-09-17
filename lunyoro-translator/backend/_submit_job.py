"""Submit the SP17 training job via HF Jobs API and print the job ID."""
import os
from huggingface_hub import HfApi
from huggingface_hub._jobs_api import Volume

token = os.environ["HF_TOKEN"]
api = HfApi(token=token)

# Check if a job with same name is already running
print("Checking existing jobs...")
try:
    jobs = list(api.list_jobs(namespace="keithtwesigye"))
    for j in jobs:
        status = getattr(j, "status", {})
        stage  = status.get("stage", "?") if isinstance(status, dict) else getattr(status, "stage", "?")
        name   = getattr(j, "name", "?")
        jid    = getattr(j, "id",   "?")
        print(f"  {jid}  {name}  stage={stage}")
        if name == "sp17-continual-training" and stage in ("running", "pending"):
            print("  Job already running — exiting.")
            exit(0)
except Exception as e:
    print(f"  Could not list jobs: {e}")

print("\nSubmitting sp17-continual-training job on t4-small...")
try:
    # Mount the Space repo read-only at /app so the training script is available
    space_vol = Volume(
        type="space",
        source="keithtwesigye/runyoro-translator-api",
        mount_path="/app",
        read_only=True,
    )

    job = api.run_job(
        image="huggingface/transformers-pytorch-gpu:latest",
        command=["python", "/app/_job_train_sp17.py"],
        env={"HF_HUB_ENABLE_HF_TRANSFER": "1"},
        secrets={"HF_TOKEN": token},
        flavor="t4-small",
        namespace="keithtwesigye",
        volumes=[space_vol],
    )
    job_id = getattr(job, "id", str(job))
    print(f"\nJob submitted successfully!")
    print(f"  Job ID  : {job_id}")
    print(f"  Monitor : https://huggingface.co/jobs/keithtwesigye/{job_id}")
    print(f"\nCheck logs with:")
    print(f"  python _monitor_job.py {job_id}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback; traceback.print_exc()
