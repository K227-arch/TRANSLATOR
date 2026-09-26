# ── Local dev start script (no Docker required) ───────────────────────────────
# Starts backend on :8000 and frontend on :3002

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND = "$ROOT\backend"
$FRONTEND = "$ROOT\frontend"

Write-Host ""
Write-Host "Starting Runyoro Translator locally..." -ForegroundColor Cyan
Write-Host "  Backend  → http://localhost:8000"
Write-Host "  Frontend → http://localhost:3002"
Write-Host ""

# ── Backend ────────────────────────────────────────────────────────────────────
Write-Host "Starting backend..." -ForegroundColor Yellow
$backendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$BACKEND'; `$env:PORT=8000; `$env:CORS_ORIGINS='http://localhost:3002'; uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
) -PassThru

Start-Sleep -Seconds 4

# ── Frontend ───────────────────────────────────────────────────────────────────
Write-Host "Starting frontend..." -ForegroundColor Yellow
$frontendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$FRONTEND'; `$env:NEXT_PUBLIC_API_URL='http://localhost:8000'; npm run dev -- --port 3002"
) -PassThru

Write-Host ""
Write-Host "Both services started." -ForegroundColor Green
Write-Host "  Backend  → http://localhost:8000/health"
Write-Host "  Frontend → http://localhost:3002"
Write-Host ""
Write-Host "Press Ctrl+C or close the terminal windows to stop."
