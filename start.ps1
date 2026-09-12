# Onyx Project Launcher
# Usage: .\start.ps1 [demo|train|full]

param(
    [string]$Mode = "demo"  # demo, train, or full
)

# Colors for output
$Success = "Green"
$Warning = "Yellow"
$Error = "Red"
$Info = "Cyan"

Write-Host "========================================" -ForegroundColor $Info
Write-Host "Onyx Startup Script" -ForegroundColor $Info
Write-Host "========================================" -ForegroundColor $Info
Write-Host ""

# Get project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Use the copied project-local runtime. It resolves packages from .venv\Lib\site-packages
# without relying on the non-portable virtual-environment launcher.
$PythonExe = Join-Path $ProjectRoot ".runtime-python310\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Host "[ERROR] Project Python runtime not found at $PythonExe" -ForegroundColor $Error
    exit 1
}
Write-Host "[OK] project runtime ready" -ForegroundColor $Success
# Verify GPU
Write-Host "[...] Checking GPU availability..." -ForegroundColor $Info
& $PythonExe -c "import torch; print('[OK] GPU available:', torch.cuda.is_available()); print('[OK] Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

Write-Host ""
Write-Host "========================================" -ForegroundColor $Info

# Mode selection
switch ($Mode.ToLower()) {
    "demo" {
        Write-Host "MODE: Demo Only (Streamlit App)" -ForegroundColor $Info
        Write-Host "========================================" -ForegroundColor $Info
        Write-Host ""

        Write-Host ""
        Write-Host "[...] Starting Onyx Streamlit Demo..." -ForegroundColor $Info
        Write-Host "Open browser: http://localhost:8511" -ForegroundColor $Success
        Write-Host ""

        $env:STREAMLIT_TELEMETRY_OPTOUT = "true"
        & $PythonExe -m streamlit run demo/app.py --server.port 8511
    }

    "train" {
        Write-Host "MODE: Full Training Pipeline" -ForegroundColor $Info
        Write-Host "========================================" -ForegroundColor $Info
        Write-Host ""
        Write-Host "This will run all 8 training stages:" -ForegroundColor $Info
        Write-Host "  1. Setup (verify environment)" -ForegroundColor $Info
        Write-Host "  2. Data generation (102K transitions)" -ForegroundColor $Info
        Write-Host "  3. GNN training (world model)" -ForegroundColor $Info
        Write-Host "  4. Red agent training (attacker)" -ForegroundColor $Info
        Write-Host "  5. Blue agent training (defender)" -ForegroundColor $Info
        Write-Host "  6. MARL self-play (5 rounds)" -ForegroundColor $Info
        Write-Host "  7. Patch optimization" -ForegroundColor $Info
        Write-Host "  8. Report generation" -ForegroundColor $Info
        Write-Host ""
        Write-Host "Estimated time: 12-14 hours" -ForegroundColor $Warning
        Write-Host ""

        $Confirm = Read-Host "Continue? (yes/no)"
        if ($Confirm -ne "yes") {
            Write-Host "[CANCELLED] Training cancelled by user" -ForegroundColor $Warning
            exit 0
        }

        Write-Host ""
        Write-Host "[...] Starting training pipeline..." -ForegroundColor $Info
        & $PythonExe run.py --stage setup
        & $PythonExe run.py --stage data
        & $PythonExe run.py --stage gnn
        & $PythonExe run.py --stage red
        & $PythonExe run.py --stage blue
        & $PythonExe run.py --stage marl
        & $PythonExe run.py --stage patch
        & $PythonExe run.py --stage report

        Write-Host ""
        Write-Host "[OK] Training complete!" -ForegroundColor $Success
        Write-Host ""
        Write-Host "[...] Starting Streamlit demo..." -ForegroundColor $Info
        $env:STREAMLIT_TELEMETRY_OPTOUT = "true"
        & $PythonExe -m streamlit run demo/app.py --server.port 8511
    }

    "full" {
        Write-Host "MODE: Full Training + Demo" -ForegroundColor $Info
        Write-Host "========================================" -ForegroundColor $Info
        Write-Host ""
        Write-Host "This will:" -ForegroundColor $Info
        Write-Host "  1. Run full 8-stage training pipeline" -ForegroundColor $Info
        Write-Host "  2. Start Streamlit demo on port 8511" -ForegroundColor $Info
        Write-Host ""
        Write-Host "Estimated time: 12-14 hours + demo runtime" -ForegroundColor $Warning
        Write-Host ""

        $Confirm = Read-Host "Continue? (yes/no)"
        if ($Confirm -ne "yes") {
            Write-Host "[CANCELLED] Operation cancelled by user" -ForegroundColor $Warning
            exit 0
        }

        Write-Host ""
        Write-Host "[...] Starting full pipeline..." -ForegroundColor $Info
        & $PythonExe run.py --stage setup
        & $PythonExe run.py --stage data
        & $PythonExe run.py --stage gnn
        & $PythonExe run.py --stage red
        & $PythonExe run.py --stage blue
        & $PythonExe run.py --stage marl
        & $PythonExe run.py --stage patch
        & $PythonExe run.py --stage report

        Write-Host ""
        Write-Host "[OK] Training complete!" -ForegroundColor $Success
        Write-Host ""
        Write-Host "[...] Starting Streamlit demo..." -ForegroundColor $Info
        $env:STREAMLIT_TELEMETRY_OPTOUT = "true"
        & $PythonExe -m streamlit run demo/app.py --server.port 8511
    }

    default {
        Write-Host "[ERROR] Unknown mode: $Mode" -ForegroundColor $Error
        Write-Host ""
        Write-Host "Usage: .\start.ps1 [mode]" -ForegroundColor $Info
        Write-Host ""
        Write-Host "Modes:" -ForegroundColor $Info
        Write-Host "  demo   - Start Streamlit demo only (default)" -ForegroundColor $Info
        Write-Host "  train  - Run full training pipeline (12-14 hours)" -ForegroundColor $Info
        Write-Host "  full   - Run training then start demo" -ForegroundColor $Info
        Write-Host ""
        exit 1
    }
}
