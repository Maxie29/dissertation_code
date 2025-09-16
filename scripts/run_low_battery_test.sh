#!/bin/bash
set -e

echo "Low Battery Threshold Validation (Linux/macOS)"
echo "=============================================="
echo
echo "This experiment validates the 30% SoC threshold rule:"
echo "  - SoC > 30%: GENERIC tasks use LOCAL/EDGE based on edge_affinity"
echo "  - SoC <= 30%: GENERIC tasks MUST use CLOUD"
echo "  - NAV/SLAM tasks ALWAYS use LOCAL regardless of SoC"
echo

# Default parameters
SKIP_ARCHIVE=false
TASKS_PER_RUN=150

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-archive)
            SKIP_ARCHIVE=true
            shift
            ;;
        --tasks-per-run)
            TASKS_PER_RUN="$2"
            shift 2
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--skip-archive] [--tasks-per-run N]"
            exit 1
            ;;
    esac
done

# Check if virtual environment exists (prioritize Unix-style over Windows-style)
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    VENV_PATH="venv"
elif [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ] && [ -f "venv/Scripts/activate" ]; then
    VENV_PATH="venv"
    ACTIVATE_SCRIPT="Scripts/activate"
elif [ -d ".venv" ] && [ -f ".venv/Scripts/activate" ]; then
    VENV_PATH=".venv"
    ACTIVATE_SCRIPT="Scripts/activate"
else
    echo "Error: Virtual environment not found."
    echo "Please create it first with: python -m venv .venv"
    exit 1
fi

# Set default activate script if not set
if [ -z "$ACTIVATE_SCRIPT" ]; then
    ACTIVATE_SCRIPT="bin/activate"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source $VENV_PATH/$ACTIVATE_SCRIPT

# Verify we're in the right environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

echo "Virtual environment activated: $VIRTUAL_ENV"
echo

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -e .
echo

# Validate the low battery sweep configuration
echo "✅ Validating low battery sweep configuration..."
python -m battery_offloading validate-config configs/sweep_low_battery.yaml
echo

# Get current timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
echo "⏰ Low battery test timestamp: $TIMESTAMP"
echo

# Run the comprehensive low battery threshold test
echo "🔋 Running low battery threshold validation sweep..."
echo "  Testing 9 different battery levels around 30% threshold"
echo "  Tasks per run: $TASKS_PER_RUN"
echo

python -m battery_offloading run --config configs/sweep_low_battery.yaml --num-tasks $TASKS_PER_RUN
echo

# Run additional targeted tests
echo "🎯 Running additional targeted threshold tests..."

# Test exactly at threshold with different task mixes
echo "  [1/3] Testing 30% SoC with NAV-heavy workload..."
python -m battery_offloading run --config configs/baseline.yaml --initial-soc 30.0 --num-tasks 100 --seed 100

echo "  [2/3] Testing 29% SoC with GENERIC-only workload..."
python -m battery_offloading run --config configs/baseline.yaml --initial-soc 29.0 --num-tasks 100 --seed 101

echo "  [3/3] Testing battery drain across threshold..."
python -m battery_offloading run --config configs/baseline.yaml --initial-soc 32.0 --num-tasks 200 --seed 102
echo

if [ "$SKIP_ARCHIVE" = true ]; then
    echo "⏭️  Skipping archive creation (--skip-archive specified)"
    echo "✅ Low battery threshold validation completed!"
    deactivate
    exit 0
fi

# Find the most recent results directories
LATEST_SWEEP=$(find results -name "sweep_*" -type d | sort | tail -1)
RECENT_RESULTS=$(find results -name "20*" -type d -newermt "30 minutes ago" | sort)

# Create archive
ARCHIVE_NAME="low_battery_validation_$TIMESTAMP.zip"
echo "📦 Creating validation results archive: $ARCHIVE_NAME"

TEMP_DIR="temp_low_battery_$TIMESTAMP"
mkdir -p "$TEMP_DIR"

# Copy sweep results
if [ ! -z "$LATEST_SWEEP" ]; then
    echo "   Adding sweep results from: $LATEST_SWEEP"
    mkdir -p "$TEMP_DIR/threshold_sweep"
    cp -r "$LATEST_SWEEP"/* "$TEMP_DIR/threshold_sweep/" 2>/dev/null || true
fi

# Copy recent individual test results
if [ ! -z "$RECENT_RESULTS" ]; then
    mkdir -p "$TEMP_DIR/individual_tests"
    echo "$RECENT_RESULTS" | while read -r result; do
        if [ ! -z "$result" ]; then
            dirname_only=$(basename "$result")
            echo "   Adding test result: $result"
            mkdir -p "$TEMP_DIR/individual_tests/$dirname_only"
            cp -r "$result"/* "$TEMP_DIR/individual_tests/$dirname_only/" 2>/dev/null || true
        fi
    done
fi

# Create ZIP archive
if command -v zip >/dev/null 2>&1; then
    echo "   Compressing validation results..."
    zip -r "$ARCHIVE_NAME" "$TEMP_DIR"/* >/dev/null
    echo "✅ Created validation archive: $ARCHIVE_NAME"
else
    echo "Warning: zip command not found, creating tar.gz instead"
    ARCHIVE_NAME="low_battery_validation_$TIMESTAMP.tar.gz"
    tar -czf "$ARCHIVE_NAME" -C "$TEMP_DIR" .
    echo "✅ Created validation archive: $ARCHIVE_NAME"
fi

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

# Show archive info
if [ -f "$ARCHIVE_NAME" ]; then
    ARCHIVE_SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')
    echo
    echo "📋 Validation Archive Information:"
    echo "   Size: $ARCHIVE_SIZE"
    echo "   Created: $(date)"
fi

echo
echo "✅ Low battery threshold validation completed!"
echo "📦 Results archived as: $ARCHIVE_NAME"
echo
echo "🔍 VALIDATION CHECKLIST:"
echo "  [ ] Check that SoC > 30% allows LOCAL/EDGE execution for GENERIC tasks"
echo "  [ ] Check that SoC <= 30% forces CLOUD execution for GENERIC tasks"
echo "  [ ] Verify NAV/SLAM tasks stay LOCAL at all SoC levels"
echo "  [ ] Confirm threshold crossing behavior during simulation"
echo
echo "📊 To extract and analyze:"
if [[ "$ARCHIVE_NAME" == *.zip ]]; then
    echo "   unzip $ARCHIVE_NAME -d validation_results"
else
    echo "   tar -xzf $ARCHIVE_NAME -C validation_results"
fi
echo "   python analyze_low_battery_results.py"
echo

# Deactivate virtual environment
deactivate
echo "Virtual environment deactivated"