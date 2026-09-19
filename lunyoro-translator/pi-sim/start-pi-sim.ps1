# start-pi-sim.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Starts the Pi virtual environment on Windows (Docker Desktop required).
# Checks model directories, builds images, and launches the full stack.
#
# Usage:
#   cd lunyoro-translator\pi-sim
#   .\start-pi-sim.ps1                  # normal start
#   .\start-pi-sim.ps1 -Build           # force rebuild images
#   .\start-pi-sim.ps1 -Down            # stop and remove containers
#   .\start-pi-sim.ps1 -Logs            # tail logs after starting
#   .\start-pi-sim.ps1 -NllbOnly        # skip Marian, faster boot
# ─────────────────────────────────────────────────────────────────────────────

param(
    [switch]$Build,       # Force --build on docker compose up
    [switch]$Down,        # docker compose down
    [switch]$Logs,        # Tail logs after stack is up
    [switch]$NllbOnly,    # Set DISABLE_MARIAN=1 for faster startup
    [switch]$NoFrontend,  # Skip the frontend service (API-only mode)
    [switch]$Verbose      # Extra log output
)

$ErrorActionPreference = "Stop"
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$modelDir   = Join-Path $projectDir "backend\model"
$composeFile = Join-Path $scriptDir "docker-compose.pi-sim.yml"

# ── Colour helpers ────────────────────────────────────────────────────────────
function Write-Ok  ($msg) { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Err ($msg) { Write-Host "  [ERR] $msg" -ForegroundColor Red }
function Write-Hdr ($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# ── --down ────────────────────────────────────────────────────────────────────
if ($Down) {
    Write-Hdr "Stopping Pi-Sim stack"
    docker compose --project-name pi-sim -f $composeFile down --remove-orphans
    Write-Ok "Stack stopped."
    exit 0
}

# ── Pre-flight checks ─────────────────────────────────────────────────────────
Write-Hdr "Pi-Sim Pre-flight Checks"

# Docker
try {
    $null = docker info 2>&1
    Write-Ok "Docker Desktop is running"
} catch {
    Write-Err "Docker Desktop is not running. Start it first."
    exit 1
}

# Model directory
if (-not (Test-Path $modelDir)) {
    Write-Err "Model directory not found: $modelDir"
    Write-Host "  Run: cd lunyoro-translator\backend; python download_models.py" -ForegroundColor Yellow
    exit 1
}

# Check critical ONNX model dirs
$required = @(
    @{ Name = "NLLB en2lun INT8";  Path = "nllb_en2lun_int8";  Files = @("encoder_model.onnx", "decoder_model.onnx") },
    @{ Name = "NLLB lun2en INT8";  Path = "nllb_lun2en_int8";  Files = @("encoder_model.onnx", "decoder_model.onnx") },
    @{ Name = "Marian en2lun ONNX"; Path = "en2lun_onnx";      Files = @("encoder_model.onnx", "decoder_model.onnx") },
    @{ Name = "Marian lun2en ONNX"; Path = "lun2en_onnx";      Files = @("encoder_model.onnx", "decoder_model.onnx") }
)

$fallback = @(
    @{ Name = "NLLB en2lun FP32 ONNX"; Path = "nllb_en2lun_onnx" },
    @{ Name = "NLLB lun2en FP32 ONNX"; Path = "nllb_lun2en_onnx" }
)

$missingCritical = $false
foreach ($m in $required) {
    $dir = Join-Path $modelDir $m.Path
    if (-not (Test-Path $dir)) {
        Write-Warn "$($m.Name) directory missing: $($m.Path)"
        # Check fallback for NLLB
        if ($m.Path -like "nllb_*_int8") {
            $fbPath = $m.Path -replace "_int8$", "_onnx"
            $fbDir  = Join-Path $modelDir $fbPath
            if (Test-Path $fbDir) {
                Write-Ok "  Will fall back to FP32 ONNX: $fbPath"
            } else {
                Write-Err "  No INT8 or FP32 ONNX found for $($m.Name)"
                $missingCritical = $true
            }
        } else {
            Write-Err "  $($m.Name) is required"
            $missingCritical = $true
        }
    } else {
        $allFilesOk = $true
        foreach ($f in $m.Files) {
            if (-not (Test-Path (Join-Path $dir $f))) {
                Write-Warn "  Missing file: $($m.Path)\$f"
                $allFilesOk = $false
            }
        }
        if ($allFilesOk) {
            Write-Ok "$($m.Name): OK"
        } else {
            Write-Warn "$($m.Name): directory exists but some files missing — may fail at runtime"
        }
    }
}

# translation_index.pkl (needed for retrieval/spellcheck)
$indexPath = Join-Path $modelDir "translation_index.pkl"
if (Test-Path $indexPath) {
    Write-Ok "Translation index: OK"
} else {
    Write-Warn "translation_index.pkl missing — spellcheck/lookup will return empty"
    Write-Host "  Run: python backend\build_index.py" -ForegroundColor Yellow
}

if ($missingCritical) {
    Write-Err "Critical models missing. Cannot start."
    Write-Host "`n  To export INT8 models, run:" -ForegroundColor Yellow
    Write-Host "    cd lunyoro-translator\backend" -ForegroundColor Yellow
    Write-Host "    python export_onnx_all.py" -ForegroundColor Yellow
    Write-Host "    python export_onnx_int8.py" -ForegroundColor Yellow
    exit 1
}

# Estimated model memory
Write-Hdr "Estimated Memory Usage"
$nllbEst   = 1.19 * 2   # ~1.19 GB per INT8 direction
$marianEst = 0.55 * 2   # ~0.55 GB per FP32 ONNX direction
$totalEst  = $nllbEst + $marianEst
Write-Host "  NLLB INT8  (x2 directions): ~$([math]::Round($nllbEst, 1)) GB" -ForegroundColor Gray
Write-Host "  Marian FP32 ONNX (x2 dirs): ~$([math]::Round($marianEst, 1)) GB" -ForegroundColor Gray
Write-Host "  Total at steady state:       ~$([math]::Round($totalEst, 1)) GB" -ForegroundColor Gray
Write-Host "  (Pi 5 budget: 8 GB — this matches the real device)" -ForegroundColor Gray

# ── Build or just up ──────────────────────────────────────────────────────────
Write-Hdr "Starting Pi-Sim Stack"

$env:COMPOSE_PROJECT_NAME = "pi-sim"

# Always pass --project-name explicitly so Docker treats this stack as
# completely separate from the original dev stack (project: lunyoro-translator).
# The named network `pisim_net` and named volumes `pisim_history / pisim_mobilenet`
# further ensure zero overlap even if both stacks run simultaneously.
$composeBase = @("--project-name", "pi-sim", "-f", $composeFile)

# Build args
$upArgs = $composeBase + @("up", "-d")
if ($Build) {
    $upArgs += "--build"
}
if ($NoFrontend) {
    $upArgs += "--scale"
    $upArgs += "pi-sim-frontend=0"
    Write-Warn "Frontend disabled (--NoFrontend). API available at http://localhost:8090"
}

# Environment overrides
if ($NllbOnly) {
    $env:DISABLE_MARIAN = "1"
    Write-Warn "NLLB-only mode — MarianMT disabled for faster startup"
} else {
    $env:DISABLE_MARIAN = "0"
}

Write-Host ""
docker compose @upArgs

if ($LASTEXITCODE -ne 0) {
    Write-Err "docker compose up failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

# ── Wait for backend health ────────────────────────────────────────────────────
Write-Hdr "Waiting for Backend to Load Models"
Write-Host "  NLLB INT8 models take 60-120s on first load (2.4 GB total)..." -ForegroundColor Gray

$maxWait = 150   # seconds
$interval = 5
$elapsed  = 0
$ready    = $false

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 3 -ErrorAction Stop
        if ($resp.status -eq "ok") {
            $ready = $true
            break
        }
    } catch { }
    Write-Host "  ... $elapsed`s elapsed" -ForegroundColor Gray
}

if ($ready) {
    Write-Ok "Backend is healthy"
} else {
    Write-Warn "Backend did not respond in ${maxWait}s — it may still be loading models."
    Write-Host "  Check logs: docker compose --project-name pi-sim -f docker-compose.pi-sim.yml logs pi-sim-backend" -ForegroundColor Yellow
}

# ── System info ───────────────────────────────────────────────────────────────
Write-Hdr "Model Status"
try {
    $info = Invoke-RestMethod -Uri "http://localhost:8080/system-info" -TimeoutSec 5
    $nllbEn  = if ($info.nllb_en2lun)  { "LOADED ($($info.nllb_en2lun_format))" } else { "not loaded" }
    $nllbLun = if ($info.nllb_lun2en)  { "LOADED ($($info.nllb_lun2en_format))" } else { "not loaded" }
    $marEn   = if ($info.marian_en2lun) { "LOADED" } else { "not loaded" }
    $marLun  = if ($info.marian_lun2en) { "LOADED" } else { "not loaded" }
    Write-Host "  NLLB  en→lun : $nllbEn"  -ForegroundColor $(if ($info.nllb_en2lun)  {"Green"} else {"Yellow"})
    Write-Host "  NLLB  lun→en : $nllbLun" -ForegroundColor $(if ($info.nllb_lun2en)  {"Green"} else {"Yellow"})
    Write-Host "  Marian en→lun: $marEn"   -ForegroundColor $(if ($info.marian_en2lun) {"Green"} else {"Yellow"})
    Write-Host "  Marian lun→en: $marLun"  -ForegroundColor $(if ($info.marian_lun2en) {"Green"} else {"Yellow"})
    Write-Host "  RAM used: $($info.ram_used_gb) GB / $($info.ram_total_gb) GB ($($info.ram_percent)%)" -ForegroundColor Gray
} catch {
    Write-Warn "Could not fetch /system-info — backend may still be loading"
}

# ── Quick probe translation ───────────────────────────────────────────────────
Write-Hdr "Quick Translation Probe"
try {
    $r1 = Invoke-RestMethod -Uri "http://localhost:8090/translate" -Method POST `
          -ContentType "application/json" `
          -Body '{"text":"Good morning, my friend."}' -TimeoutSec 30
    Write-Ok "en→lun: '$($r1.translation)' [NLLB: $($r1.translation_nllb)] [method: $($r1.method)]"
} catch {
    Write-Warn "Translation probe failed: $_"
}
try {
    $r2 = Invoke-RestMethod -Uri "http://localhost:8090/translate-reverse" -Method POST `
          -ContentType "application/json" `
          -Body '{"text":"Webale muno"}' -TimeoutSec 30
    Write-Ok "lun→en: '$($r2.translation)' [method: $($r2.method)]"
} catch {
    Write-Warn "Reverse probe failed: $_"
}

# ── URLs ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Pi-Sim is running!" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend (full UI) : http://localhost:3090" -ForegroundColor Cyan
Write-Host "  API via nginx      : http://localhost:8090" -ForegroundColor Cyan
Write-Host "  Backend direct     : http://localhost:8080" -ForegroundColor Gray
Write-Host "  Sidecar direct     : http://localhost:8001" -ForegroundColor Gray
Write-Host "  API docs           : http://localhost:8080/docs" -ForegroundColor Gray
Write-Host "  Benchmark endpoint : http://localhost:8080/benchmark" -ForegroundColor Gray
Write-Host ""
Write-Host "  Stop stack : .\start-pi-sim.ps1 -Down" -ForegroundColor Gray
Write-Host "  View logs  : docker compose --project-name pi-sim -f docker-compose.pi-sim.yml logs -f" -ForegroundColor Gray
Write-Host "  Check net  : docker network inspect pisim_net" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

if ($Logs) {
    Write-Host "Tailing logs (Ctrl-C to stop)..." -ForegroundColor Gray
    docker compose @composeBase logs -f
}
