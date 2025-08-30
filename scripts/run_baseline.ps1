# PowerShell script for running baseline experiments on Windows
# Requires PowerShell 5.0 or later

param(
    [switch]$SkipArchive = $false
)

Write-Host "Battery Offloading Baseline Experiment Runner (Windows)" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Error handling
$ErrorActionPreference = "Stop"

try {
    # Check if virtual environment exists
    if (-not (Test-Path "venv")) {
        Write-Host "❌ Error: Virtual environment 'venv' not found." -ForegroundColor Red
        Write-Host "Please create it first with: python -m venv venv" -ForegroundColor Yellow
        exit 1
    }

    # Activate virtual environment
    Write-Host "🔄 Activating virtual environment..." -ForegroundColor Yellow
    
    # Try different activation script locations
    $activateScript = $null
    $possiblePaths = @(
        "venv\Scripts\Activate.ps1",
        "venv\Scripts\activate.bat",
        "venv\bin\activate"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $activateScript = $path
            break
        }
    }
    
    if ($null -eq $activateScript) {
        Write-Host "❌ Error: Could not find virtual environment activation script" -ForegroundColor Red
        exit 1
    }
    
    # Activate the environment
    if ($activateScript.EndsWith(".ps1")) {
        & $activateScript
    } elseif ($activateScript.EndsWith(".bat")) {
        cmd /c $activateScript
    } else {
        # Unix-style activation (for Git Bash, etc.)
        Write-Host "⚠️  Using Unix-style activation" -ForegroundColor Yellow
        & $activateScript
    }
    
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    Write-Host ""

    # Install/update dependencies
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    python -m pip install -q -e .
    Write-Host ""

    # Get current timestamp for results identification
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Write-Host "🏷️  Experiment timestamp: $timestamp" -ForegroundColor Cyan
    Write-Host ""

    # Run baseline experiment
    Write-Host "🎯 Running baseline experiment..." -ForegroundColor Green
    python -m battery_offloading baseline configs/baseline.yaml
    Write-Host ""

    # Run first parameter sweep (edge latency)
    Write-Host "🔄 Running edge latency parameter sweep..." -ForegroundColor Green
    python -m battery_offloading sweep configs/sweep_edge_latency.yaml
    Write-Host ""

    # Run second parameter sweep (workload)
    Write-Host "🔄 Running workload parameter sweep..." -ForegroundColor Green
    python -m battery_offloading sweep configs/sweep_workload.yaml
    Write-Host ""

    if ($SkipArchive) {
        Write-Host "📁 Skipping archive creation (--SkipArchive specified)" -ForegroundColor Yellow
        Write-Host "🎉 Baseline experiments completed!" -ForegroundColor Green
        return
    }

    # Find the most recent results directories
    $latestDir = Get-ChildItem -Path "results" -Directory -Name "20*" | Sort-Object | Select-Object -Last 1
    $latestSweep = Get-ChildItem -Path "results" -Directory -Name "sweep_20*" | Sort-Object | Select-Object -Last 1

    if (-not $latestDir -and -not $latestSweep) {
        Write-Host "❌ Error: No results directories found" -ForegroundColor Red
        exit 1
    }

    # Create archive name based on timestamp
    $archiveName = "baseline_results_$timestamp.zip"

    Write-Host "📦 Creating results archive: $archiveName" -ForegroundColor Yellow

    # Create temporary directory to organize files
    $tempDir = "temp_$timestamp"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    # Copy latest baseline results if available
    if ($latestDir) {
        Write-Host "   Adding baseline results from: results\$latestDir" -ForegroundColor Gray
        $baselineDir = Join-Path $tempDir "baseline"
        New-Item -ItemType Directory -Path $baselineDir -Force | Out-Null
        Copy-Item -Path "results\$latestDir\*" -Destination $baselineDir -Recurse -ErrorAction SilentlyContinue
    }

    # Copy latest sweep results if available
    if ($latestSweep) {
        Write-Host "   Adding sweep results from: results\$latestSweep" -ForegroundColor Gray
        $sweepsDir = Join-Path $tempDir "sweeps"
        New-Item -ItemType Directory -Path $sweepsDir -Force | Out-Null
        Copy-Item -Path "results\$latestSweep\*" -Destination $sweepsDir -Recurse -ErrorAction SilentlyContinue
    }

    # Find and include any other recent result directories (last 2 hours)
    Write-Host "   Searching for additional recent results..." -ForegroundColor Gray
    $cutoffTime = (Get-Date).AddHours(-2)
    $recentDirs = Get-ChildItem -Path "results" -Directory -Name "20*" | Where-Object {
        $dirPath = "results\$_"
        (Get-Item $dirPath).LastWriteTime -gt $cutoffTime -and 
        $_ -ne $latestDir -and $_ -ne $latestSweep
    }

    foreach ($dir in $recentDirs) {
        Write-Host "   Adding recent result: results\$dir" -ForegroundColor Gray
        $additionalDir = Join-Path $tempDir "additional\$dir"
        New-Item -ItemType Directory -Path $additionalDir -Force | Out-Null
        Copy-Item -Path "results\$dir\*" -Destination $additionalDir -Recurse -ErrorAction SilentlyContinue
    }

    # Create ZIP archive using .NET compression
    Write-Host "   Compressing files..." -ForegroundColor Gray
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    
    $fullTempPath = (Resolve-Path $tempDir).Path
    $fullArchivePath = Join-Path (Get-Location) $archiveName
    
    [System.IO.Compression.ZipFile]::CreateFromDirectory($fullTempPath, $fullArchivePath)
    Write-Host "✅ Created archive: $archiveName" -ForegroundColor Green

    # Cleanup temporary directory
    Remove-Item -Path $tempDir -Recurse -Force

    # Show archive info
    Write-Host ""
    Write-Host "📋 Archive information:" -ForegroundColor Cyan
    $archiveInfo = Get-Item $archiveName
    Write-Host "   Size: $([math]::Round($archiveInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray
    Write-Host "   Created: $($archiveInfo.CreationTime)" -ForegroundColor Gray

    # Show some archive contents (first few files)
    Write-Host "   Contents preview:" -ForegroundColor Gray
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($fullArchivePath)
    $archive.Entries | Select-Object -First 10 | ForEach-Object {
        Write-Host "     $($_.FullName)" -ForegroundColor DarkGray
    }
    $archive.Dispose()

    Write-Host ""
    Write-Host "🎉 Baseline experiment completed successfully!" -ForegroundColor Green
    Write-Host "📁 Results archived as: $archiveName" -ForegroundColor Cyan
    Write-Host "📊 Archive contains CSV data and PNG visualizations" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To extract:" -ForegroundColor Yellow
    Write-Host "   Expand-Archive -Path $archiveName -DestinationPath extracted_results" -ForegroundColor White
    Write-Host "   # OR right-click and select 'Extract All...'" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "❌ Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
    exit 1
} finally {
    # Always try to cleanup temp directory if it exists
    if (Test-Path "temp_*") {
        Get-ChildItem -Path "temp_*" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "✅ Cleanup completed" -ForegroundColor Green
}