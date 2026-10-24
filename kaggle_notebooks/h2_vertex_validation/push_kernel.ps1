# PowerShell script to package validation dataset, push to Kaggle, and track kernel status
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 Pushing H2 Vertex DeepSeek Validation Kernel to Kaggle..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Write-Host "Workspace Root:    $repoRoot"
Write-Host "Kernel Directory:  $scriptDir"

# Check if kaggle CLI is installed
if (-not (Get-Command "kaggle" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Kaggle CLI not found in PATH." -ForegroundColor Red
    Write-Host "    Please ensure 'kaggle' is installed (pip install kaggle) and kaggle.json is in ~/.kaggle/" -ForegroundColor Yellow
    exit 1
}

# 1. Dataset Staging & Push
$datasetSlug = "huuhieu3333/grace-h2-vertex-validation"
$stagingDir = Join-Path $scriptDir "dataset_staging"
$packageScript = Join-Path $repoRoot "scripts\package_validation_dataset.py"

# Auto-stage dataset if staging folder does not exist
if (-not (Test-Path $stagingDir)) {
    Write-Host "`n[*] Staging directory not found. Attempting automatic packaging..." -ForegroundColor Yellow
    $valSource = "D:\tai lieu hoc tap\Đề tài nghiên cứu khoa học\papers source code\SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022\validation"
    if (Test-Path $valSource) {
        Write-Host "    Found validation source at: $valSource" -ForegroundColor Green
        python $packageScript --source $valSource --staging $stagingDir
    } else {
        Write-Host "[!] Source validation folder not found at default path." -ForegroundColor Yellow
        Write-Host "    If dataset already exists on Kaggle, will proceed with kernel push." -ForegroundColor Gray
    }
}

if (Test-Path $stagingDir) {
    Write-Host "`n[*] Found dataset staging folder: $stagingDir" -ForegroundColor Yellow
    Write-Host "    Verifying Kaggle dataset '$datasetSlug'..." -ForegroundColor Gray
    
    $datasetCheck = kaggle datasets files $datasetSlug 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Updating existing dataset version..." -ForegroundColor Green
        kaggle datasets version -p $stagingDir -m "Update validation prompts" -r zip
    } else {
        Write-Host "    Creating new Kaggle dataset '$datasetSlug'..." -ForegroundColor Green
        kaggle datasets create -p $stagingDir -r zip
    }
} else {
    Write-Host "[*] Skipping dataset creation (staging dir absent). Assuming dataset '$datasetSlug' exists on Kaggle." -ForegroundColor Gray
}

# 2. Push Kernel
Write-Host "`n[*] Pushing kernel via Kaggle CLI..." -ForegroundColor Yellow
kaggle kernels push -p .

Start-Sleep -Seconds 3

# 3. Check Status
Write-Host "`n[*] Checking Kernel Status..." -ForegroundColor Yellow
kaggle kernels status huuhieu3333/grace-h2-vertex-deepseek-validation

Write-Host "`n[OK] Kernel pushed successfully!" -ForegroundColor Green
Write-Host "To monitor status in real-time, run:" -ForegroundColor Cyan
Write-Host "  kaggle kernels status huuhieu3333/grace-h2-vertex-deepseek-validation" -ForegroundColor White
Write-Host "`nWhen status is 'complete', download results using:" -ForegroundColor Cyan
Write-Host "  kaggle kernels output huuhieu3333/grace-h2-vertex-deepseek-validation -p ../../output/h2_vertex_validation_kaggle/" -ForegroundColor White
