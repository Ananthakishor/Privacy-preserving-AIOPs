# SentinelOps AI - Start All Services (Windows PowerShell)
# Run from the ATRIA_PROJECT directory: .\scripts\start_all.ps1
#
# Services started:
#   1. FastAPI backend (port 8000) — includes seed_data + DB init
#   2. React frontend (port 5173)
#   3. Local collector (real psutil + ICMP ping metrics)
#   4. Telemetry simulator (optional, for demos)
#
# Stop all with: Get-Process python,node | Stop-Process -Force

$root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   SentinelOps AI — CICADA 2026 Hackathon ║" -ForegroundColor Cyan
Write-Host "║   TechForcz × Atria Institute of Tech    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. Start Backend (seed DB then start server)
Write-Host "[1/4] Starting FastAPI backend on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\backend'; `
     Write-Host '[BACKEND] Initializing database...' -ForegroundColor Yellow; `
     .\.venv\Scripts\python.exe seed_data.py; `
     Write-Host '[BACKEND] Starting uvicorn...' -ForegroundColor Green; `
     .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000 --log-level info" `
    -WindowStyle Normal

Start-Sleep 4

# 2. Start Frontend
Write-Host "[2/4] Starting React frontend on port 5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\frontend'; npm run dev" `
    -WindowStyle Normal

Start-Sleep 2

# 3. Start Collector (real metrics)
Write-Host "[3/4] Starting local collector (real psutil + ICMP ping)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root'; `
     Write-Host '[COLLECTOR] Starting real metrics collection...' -ForegroundColor Green; `
     collector\.venv\Scripts\python.exe collector\collector.py" `
    -WindowStyle Normal

Start-Sleep 2

# 4. Start Telemetry Simulator (demo scenarios — optional)
Write-Host "[4/4] Starting telemetry simulator (normal mode — demo scenarios)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\telemetry-simulator'; `
     Write-Host '[SIMULATOR] Running normal scenario...' -ForegroundColor Green; `
     .\.venv\Scripts\python.exe simulator.py --scenario normal" `
    -WindowStyle Normal

Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  All services starting. Wait 5-10 seconds..." -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Local UI:     http://localhost:8001 (run collector\local_ui.py separately)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Demo credentials:" -ForegroundColor Yellow
Write-Host "    Admin:    admin@alpha.local / SentinelAdmin2026!" -ForegroundColor White
Write-Host "    Operator: operator@alpha.local / SentinelOp2026!" -ForegroundColor White
Write-Host "    Viewer:   viewer@beta.local / SentinelView2026!" -ForegroundColor White
Write-Host ""
Write-Host "  What's real vs simulated:" -ForegroundColor Yellow
Write-Host "    LIVE  (green badge): psutil CPU/mem/disk, ICMP ping latency" -ForegroundColor Green
Write-Host "    SEED  (blue badge):  seed_data.py baseline samples" -ForegroundColor Blue
Write-Host "    SIM   (yellow badge): telemetry-simulator scenarios" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
