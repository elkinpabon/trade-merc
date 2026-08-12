# TradeMerc PowerShell Launcher for Windows
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         TRADEMERC ALGORITHMIC TRADING PLATFORM          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "backend"
$frontendPath = Join-Path $PSScriptRoot "frontend"

Write-Host "`n[1/2] Starting Flask Backend Server + Trading Engine..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; python run.py"

Start-Sleep -Seconds 3

Write-Host "`n[2/2] Starting Next.js Terminal Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"

Write-Host "`nTradeMerc system launched!" -ForegroundColor Green
Write-Host "Backend Server: http://localhost:5000" -ForegroundColor Gray
Write-Host "Frontend Terminal: http://localhost:3000" -ForegroundColor Gray
