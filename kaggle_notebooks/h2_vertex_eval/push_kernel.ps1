# PowerShell script to push H2 Vertex Evaluation kernel to Kaggle and check status
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 Pushing H2 Vertex Evaluation Kernel to Kaggle..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Current Directory: $(Get-Location)"

# Check if kaggle CLI is installed
if (-not (Get-Command "kaggle" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Kaggle CLI not found in PATH." -ForegroundColor Red
    Write-Host "    Please ensure 'kaggle' is installed (pip install kaggle) and kaggle.json is in ~/.kaggle/" -ForegroundColor Yellow
    exit 1
}

Write-Host "Pushing kernel via Kaggle CLI..." -ForegroundColor Yellow
kaggle kernels push -p .

Start-Sleep -Seconds 3

Write-Host "`nChecking Kernel Status..." -ForegroundColor Yellow
kaggle kernels status huuhieu3333/grace-h2-vertex-deepseek-evaluation

Write-Host "`n[OK] Kernel pushed successfully!" -ForegroundColor Green
Write-Host "To monitor status in real-time, run:" -ForegroundColor Cyan
Write-Host "  kaggle kernels status huuhieu3333/grace-h2-vertex-deepseek-evaluation" -ForegroundColor White
Write-Host "`nWhen status is 'complete', download results using:" -ForegroundColor Cyan
Write-Host "  kaggle kernels output huuhieu3333/grace-h2-vertex-deepseek-evaluation -p ../../output/h2_vertex_deepseek_v41_kaggle/" -ForegroundColor White
