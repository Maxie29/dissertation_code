# PowerShell script for running low battery threshold validation experiments
# Tests the critical 30% SoC threshold rule

param(
    [switch]$SkipArchive = $false,
    [int]$TasksPerRun = 150
)

Write-Host "Low Battery Threshold Validation (Windows)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This experiment validates the 30% SoC threshold rule:" -ForegroundColor Yellow
Write-Host "  - SoC > 30%: GENERIC tasks use LOCAL/EDGE based on edge_affinity" -ForegroundColor Gray
Write-Host "  - SoC <= 30%: GENERIC tasks MUST use CLOUD" -ForegroundColor Gray  
Write-Host "  - NAV/SLAM tasks ALWAYS use LOCAL regardless of SoC" -ForegroundColor Gray
Write-Host ""

# Error handling
$ErrorActionPreference = "Stop"

try {
    # Check if virtual environment exists (.venv or venv)
    $venvExists = $false
    if (Test-Path ".venv") {
        $venvExists = $true
        $venvPath = ".venv"
    } elseif (Test-Path "venv") {
        $venvExists = $true
        $venvPath = "venv"
    }
    
    if (-not $venvExists) {
        Write-Host "[ERROR] Virtual environment not found." -ForegroundColor Red
        Write-Host "Please create it first with: python -m venv .venv" -ForegroundColor Yellow
        exit 1
    }

    # Activate virtual environment
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
    
    $activateScript = $null
    $possiblePaths = @("$venvPath\Scripts\Activate.ps1", "$venvPath\Scripts\activate.bat")
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $activateScript = $path
            break
        }
    }
    
    if ($null -eq $activateScript) {
        Write-Host "[ERROR] Could not find virtual environment activation script" -ForegroundColor Red
        exit 1
    }
    
    if ($activateScript.EndsWith(".ps1")) {
        & $activateScript
    } else {
        cmd /c $activateScript
    }
    
    Write-Host "[SUCCESS] Virtual environment activated" -ForegroundColor Green
    Write-Host ""

    # Install/update dependencies
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
    python -m pip install -q -e .
    Write-Host ""

    # Validate the low battery sweep configuration
    Write-Host "[VALIDATING] Low battery sweep configuration..." -ForegroundColor Yellow
    python -m battery_offloading validate-config configs/sweep_low_battery.yaml
    Write-Host ""

    # Get current timestamp
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Write-Host "[INFO] Low battery test timestamp: $timestamp" -ForegroundColor Cyan
    Write-Host ""

    # Run the comprehensive low battery threshold test
    Write-Host "[RUNNING] Low battery threshold validation sweep..." -ForegroundColor Green
    Write-Host "  Testing 9 different battery levels around 30% threshold" -ForegroundColor Gray
    Write-Host "  Tasks per run: $TasksPerRun" -ForegroundColor Gray
    Write-Host ""
    
    python -m battery_offloading run --config configs/sweep_low_battery.yaml --num-tasks $TasksPerRun
    Write-Host ""

    # Run additional targeted tests
    Write-Host "[RUNNING] Additional targeted threshold tests..." -ForegroundColor Green
    
    # Test exactly at threshold with different task mixes
    Write-Host "  [1/3] Testing 30% SoC with NAV-heavy workload..." -ForegroundColor Gray
    python -m battery_offloading run --config configs/baseline.yaml --initial-soc 30.0 --num-tasks 100 --seed 100
    
    Write-Host "  [2/3] Testing 29% SoC with GENERIC-only workload..." -ForegroundColor Gray  
    python -m battery_offloading run --config configs/baseline.yaml --initial-soc 29.0 --num-tasks 100 --seed 101
    
    Write-Host "  [3/3] Testing battery drain across threshold..." -ForegroundColor Gray
    python -m battery_offloading run --config configs/baseline.yaml --initial-soc 32.0 --num-tasks 200 --seed 102
    Write-Host ""

    if ($SkipArchive) {
        Write-Host "[INFO] Skipping archive creation (-SkipArchive specified)" -ForegroundColor Yellow
        Write-Host "[SUCCESS] Low battery threshold validation completed!" -ForegroundColor Green
        return
    }

    # Find the most recent results directories
    $latestSweep = Get-ChildItem -Path "results" -Directory -Name "sweep_*" -ErrorAction SilentlyContinue | Sort-Object | Select-Object -Last 1
    $recentResults = Get-ChildItem -Path "results" -Directory -Name "20*" -ErrorAction SilentlyContinue | 
                     Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-30) } | Sort-Object LastWriteTime

    # Create archive
    $archiveName = "low_battery_validation_$timestamp.zip"
    Write-Host "[INFO] Creating validation results archive: $archiveName" -ForegroundColor Yellow

    $tempDir = "temp_low_battery_$timestamp"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    # Copy sweep results
    if ($latestSweep) {
        Write-Host "   Adding sweep results from: results\$latestSweep" -ForegroundColor Gray
        $sweepDir = Join-Path $tempDir "threshold_sweep"
        New-Item -ItemType Directory -Path $sweepDir -Force | Out-Null
        Copy-Item -Path "results\$latestSweep\*" -Destination $sweepDir -Recurse -ErrorAction SilentlyContinue
    }

    # Copy recent individual test results
    foreach ($result in $recentResults) {
        Write-Host "   Adding test result: results\$($result.Name)" -ForegroundColor Gray
        $testDir = Join-Path $tempDir "individual_tests\$($result.Name)"
        New-Item -ItemType Directory -Path $testDir -Force | Out-Null
        Copy-Item -Path $result.FullName\* -Destination $testDir -Recurse -ErrorAction SilentlyContinue
    }

    # Create ZIP archive
    Write-Host "   Compressing validation results..." -ForegroundColor Gray
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $fullTempPath = (Resolve-Path $tempDir).Path
    $fullArchivePath = Join-Path (Get-Location) $archiveName
    [System.IO.Compression.ZipFile]::CreateFromDirectory($fullTempPath, $fullArchivePath)
    
    # Cleanup
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "[SUCCESS] Created validation archive: $archiveName" -ForegroundColor Green

    # Show archive info
    $archiveInfo = Get-Item $archiveName
    Write-Host ""
    Write-Host "[INFO] Validation Archive Information:" -ForegroundColor Cyan
    Write-Host "   Size: $([math]::Round($archiveInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray
    Write-Host "   Created: $($archiveInfo.CreationTime)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[SUCCESS] Low battery threshold validation completed!" -ForegroundColor Green
    Write-Host "[INFO] Results archived as: $archiveName" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "VALIDATION CHECKLIST:" -ForegroundColor Yellow
    Write-Host "  [ ] Check that SoC > 30% allows LOCAL/EDGE execution for GENERIC tasks" -ForegroundColor Gray
    Write-Host "  [ ] Check that SoC <= 30% forces CLOUD execution for GENERIC tasks" -ForegroundColor Gray  
    Write-Host "  [ ] Verify NAV/SLAM tasks stay LOCAL at all SoC levels" -ForegroundColor Gray
    Write-Host "  [ ] Confirm threshold crossing behavior during simulation" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To extract and analyze:" -ForegroundColor Yellow
    Write-Host "   Expand-Archive -Path $archiveName -DestinationPath validation_results" -ForegroundColor White
    Write-Host "   python analyze_low_battery_results.py" -ForegroundColor White

} catch {
    Write-Host ""
    Write-Host "[ERROR] Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
    exit 1
} finally {
    # Cleanup
    if (Test-Path "temp_low_battery_*") {
        Get-ChildItem -Path "temp_low_battery_*" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[INFO] Cleanup completed" -ForegroundColor Green
}