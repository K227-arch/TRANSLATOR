$PY312 = "C:\Users\keith\AppData\Local\Programs\Python\Python312\python.exe"
$VENV  = "C:\Users\keith\Desktop\projects\TRANSLATOR\lunyoro-translator\backend\venv312"
$BACKEND = "C:\Users\keith\Desktop\projects\TRANSLATOR\lunyoro-translator\backend"

Write-Host "=== Step 1: Create venv with Python 3.12 ===" -ForegroundColor Cyan
& $PY312 -m venv $VENV
Write-Host "Venv created at $VENV"

$PIP = "$VENV\Scripts\pip.exe"
$PYTHON = "$VENV\Scripts\python.exe"

Write-Host ""
Write-Host "=== Step 2: Install CUDA torch (cu124) ===" -ForegroundColor Cyan
& $PIP install torch --index-url https://download.pytorch.org/whl/cu124

Write-Host ""
Write-Host "=== Step 3: Install ML deps ===" -ForegroundColor Cyan
& $PIP install "transformers>=4.41.0,<4.52.0" sentencepiece sacrebleu pandas huggingface_hub accelerate protobuf rapidfuzz

Write-Host ""
Write-Host "=== Step 4: Verify GPU ===" -ForegroundColor Cyan
& $PYTHON -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPUs:', torch.cuda.device_count()); [print(f'  GPU {i}:', torch.cuda.get_device_name(i)) for i in range(torch.cuda.device_count())]"

Write-Host ""
Write-Host "=== Step 5: Train MarianMT --new-only both directions ===" -ForegroundColor Cyan
Set-Location $BACKEND
& $PYTHON train_marian.py --new-only --direction both --epochs 5 --batch-size 32 --lr 3e-5

Write-Host ""
Write-Host "=== Step 6: Train NLLB --new-only both directions ===" -ForegroundColor Cyan
& $PYTHON train_nllb.py --new-only --direction both --epochs 3 --batch-size 16 --lr 8e-6 --fp16

Write-Host ""
Write-Host "=== Step 7: Push all models to HF Hub ===" -ForegroundColor Cyan
# HF_TOKEN is loaded from .env by push_models.py — do not hardcode here
& $PYTHON push_models.py --model en2lun
& $PYTHON push_models.py --model lun2en
& $PYTHON push_models.py --model nllb_en2lun
& $PYTHON push_models.py --model nllb_lun2en

Write-Host ""
Write-Host "=== ALL DONE ===" -ForegroundColor Green
