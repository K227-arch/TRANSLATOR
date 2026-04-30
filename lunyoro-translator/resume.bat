@echo off
echo ============================================
echo  Lunyoro Translator - Resume Script
echo ============================================
echo.

cd /d "%~dp0"

echo [1] Starting backend...
start "Backend" cmd /k "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 >nul

echo [2] Starting frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 2 >nul

echo.
echo [3] Checking what still needs to run...
python -c "
import json, os
with open('STATUS.json') as f:
    s = json.load(f)
print('Last updated:', s['last_updated'])
print()
print('PENDING TASKS:')
for p in s['pending']:
    print(' -', p)
print()
print('MODEL STATUS:')
for name, info in s['models'].items():
    trained = 'DONE' if info['trained'] else 'PENDING'
    pushed  = 'PUSHED' if info['pushed_to_hf'] else 'NOT PUSHED'
    print(f'  {name}: trained={trained}, hf={pushed}')
"

echo.
echo [4] To resume NLLB lun2en training (if not done):
echo     python backend/dictionary_pipeline.py --skip-backtrans --only-nllb --only-lun2en-nllb --nllb-epochs 5 --nllb-batch-size 4 --nllb-lr 5e-6
echo.
echo [5] To push nllb_en2lun to HuggingFace (if not done):
echo     python push_models.py --model nllb_en2lun
echo.
echo [6] To push nllb_lun2en to HuggingFace (after training):
echo     python push_models.py --model nllb_lun2en
echo.
echo App running at:
echo   Frontend: http://localhost:3002
echo   Backend:  http://localhost:8000
echo.
pause
