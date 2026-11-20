# SentinelOps AI - Start All Services (Windows PowerShell)
# Run from the ATRIA_PROJECT directory: .\scripts\start_all.ps1

$root = Split-Path -Parent $PSScriptRoot

Write-Host "[SentinelOps] Starting all services..." -ForegroundColor Cyan

# 1. Start Backend
Write-Host "[1/3] Starting FastAPI backend on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\activate; python seed_data.py; uvicorn app.main:app --reload --port 8000" -WindowStyle Normal

Start-Sleep 3

# 2. Start Frontend
Write-Host "[2/3] Starting React frontend on port 5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev" -WindowStyle Normal

Start-Sleep 2

# 3. Start Telemetry Simulator (normal mode)
Write-Host "[3/3] Starting telemetry simulator (normal mode)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\telemetry-simulator'; .\.venv\Scripts\activate; python simulator.py --scenario normal" -WindowStyle Normal

Write-Host ""
Write-Host "[SentinelOps] All services starting..." -ForegroundColor Green
Write-Host "  Dashboard:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "  API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Local UI:   http://localhost:8001  (run collector/local_ui.py separately)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Demo credentials:" -ForegroundColor Yellow
Write-Host "  Admin:    admin@alpha.local / SentinelAdmin2026!" -ForegroundColor White
Write-Host "  Operator: operator@alpha.local / SentinelOp2026!" -ForegroundColor White
Write-Host "  Viewer:   viewer@beta.local / SentinelView2026!" -ForegroundColor White
