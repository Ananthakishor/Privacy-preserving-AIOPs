# SentinelOps AI - Start All Services (Windows PowerShell 5.1+)
# Run from ATRIA_PROJECT root:  .\scripts\start_all.ps1
#
# Services started:
#   1. FastAPI backend      (port 8000)
#   2. React frontend       (port 5173)
#   3. Local collector      (real psutil + ICMP ping metrics)
#   4. Local UI / egress    (port 8001)
#   5. Telemetry simulator  (optional - normal scenario)
#
# Stop all with:
#   Get-Process python,node | Stop-Process -Force
# ------------------------------------------------------------

$root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  SentinelOps AI - CICADA 2026 Hackathon"     -ForegroundColor Cyan
Write-Host "  TechForcz x Atria Institute of Technology"  -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ── Helper: check if a port is already in use ──────────────────────────────
function Test-Port {
    param([int]$Port)
    $conn = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    return ($conn -ne $null)
}

# ── Kill any stale processes on our ports before starting ─────────────────
foreach ($port in @(8000, 5173, 8001)) {
    $conns = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        $pid = ($conns | Select-Object -First 1).OwningProcess
        Write-Host "  [WARN] Port $port already in use by PID $pid — stopping it..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep 1
    }
}

# ── 1. Backend (seed DB then start uvicorn) ────────────────────────────────
Write-Host "[1/5] Starting FastAPI backend on port 8000..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$root\backend'; " +
    "Write-Host '[BACKEND] Running DB init + seed...' -ForegroundColor Yellow; " +
    ".\.venv\Scripts\python.exe seed_data.py; " +
    "Write-Host '[BACKEND] Starting uvicorn on :8000...' -ForegroundColor Green; " +
    ".\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000 --log-level info"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal
Start-Sleep 5

# ── 2. Frontend ────────────────────────────────────────────────────────────
Write-Host "[2/5] Starting React frontend on port 5173..." -ForegroundColor Yellow
$frontendCmd = "Set-Location '$root\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
Start-Sleep 2

# ── 3. Collector (real psutil + ICMP ping metrics) ─────────────────────────
Write-Host "[3/5] Starting local collector (real metrics)..." -ForegroundColor Yellow
$collectorCmd = "Set-Location '$root'; " +
    "Write-Host '[COLLECTOR] Starting real psutil + ICMP metrics...' -ForegroundColor Green; " +
    "collector\.venv\Scripts\python.exe collector\collector.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $collectorCmd -WindowStyle Normal
Start-Sleep 2

# ── 4. Local UI / Egress proof viewer (port 8001) ──────────────────────────
Write-Host "[4/5] Starting local UI on port 8001 (egress proof viewer)..." -ForegroundColor Yellow
$localUiCmd = "Set-Location '$root'; " +
    "Write-Host '[LOCAL UI] http://localhost:8001 — raw data viewer (local only)' -ForegroundColor Green; " +
    "collector\.venv\Scripts\python.exe collector\local_ui.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $localUiCmd -WindowStyle Normal
Start-Sleep 2

# ── 5. Telemetry simulator (normal scenario) ───────────────────────────────
Write-Host "[5/5] Starting telemetry simulator (normal mode)..." -ForegroundColor Yellow
$simCmd = "Set-Location '$root\telemetry-simulator'; " +
    "Write-Host '[SIMULATOR] Running normal scenario (SIMULATED data)' -ForegroundColor Yellow; " +
    ".\.venv\Scripts\python.exe simulator.py --scenario normal"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $simCmd -WindowStyle Normal

# ── Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  All 5 services started. Wait 10-15s..."     -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:    http://localhost:5173"         -ForegroundColor Cyan
Write-Host "  API Docs:     http://localhost:8000/docs"    -ForegroundColor Cyan
Write-Host "  Local UI:     http://localhost:8001"         -ForegroundColor Cyan
Write-Host ""
Write-Host "  Demo credentials:"                           -ForegroundColor Yellow
Write-Host "    Admin:    admin@alpha.local / SentinelAdmin2026!"   -ForegroundColor White
Write-Host "    Operator: operator@alpha.local / SentinelOp2026!"   -ForegroundColor White
Write-Host "    Viewer:   viewer@beta.local / SentinelView2026!"    -ForegroundColor White
Write-Host ""
Write-Host "  Data badges (shown on dashboard):"          -ForegroundColor Yellow
Write-Host "    LIVE  (green):  psutil CPU/mem/disk, ICMP ping"     -ForegroundColor Green
Write-Host "    SEED  (blue):   seed_data.py baseline samples"      -ForegroundColor Blue
Write-Host "    SIM   (yellow): telemetry-simulator scenarios"      -ForegroundColor Yellow
Write-Host ""
Write-Host "  Demo scenarios (run in a new terminal):"    -ForegroundColor Yellow
Write-Host "    cd telemetry-simulator"                    -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\python.exe simulator.py --scenario cpu_spike"    -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\python.exe simulator.py --scenario correlated"   -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\python.exe simulator.py --scenario auth_failures" -ForegroundColor Gray
Write-Host ""
Write-Host "  Stop all services:"                         -ForegroundColor Yellow
Write-Host "    Get-Process python,node | Stop-Process -Force"      -ForegroundColor Gray
Write-Host "==============================================" -ForegroundColor Green
