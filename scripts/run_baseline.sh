#!/bin/bash
set -e

echo "Battery Offloading Baseline Experiment Runner (Linux/macOS)"
echo "=========================================================="
echo

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
echo "   Installing dependencies..."
pip install -q -e .
echo

# Get current timestamp for results identification
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
echo "   Experiment timestamp: $TIMESTAMP"
echo

# Run baseline experiment
echo "   Running baseline experiment..."
python -m battery_offloading run --config configs/baseline.yaml
echo

# Run edge latency parameter sweep
echo "   Running edge latency parameter sweep..."
if [ -f "configs/sweep_edge_latency.yaml" ]; then
    python -m battery_offloading run --config configs/sweep_edge_latency.yaml
else
    echo "   Edge latency sweep config not found, running with different parameters..."
    python -m battery_offloading run --config configs/baseline.yaml --num-tasks 100 --seed 1
    python -m battery_offloading run --config configs/baseline.yaml --num-tasks 100 --seed 2
    python -m battery_offloading run --config configs/baseline.yaml --num-tasks 100 --seed 3
fi
echo

# Run workload parameter sweep
echo "   Running workload parameter sweep..."
if [ -f "configs/sweep_workload.yaml" ]; then
    python -m battery_offloading run --config configs/sweep_workload.yaml
else
    echo "Workload sweep config not found, running with different battery levels..."
    python -m battery_offloading run --config configs/baseline.yaml --initial-soc 60.0 --num-tasks 100
    python -m battery_offloading run --config configs/baseline.yaml --initial-soc 80.0 --num-tasks 100
    python -m battery_offloading run --config configs/baseline.yaml --initial-soc 90.0 --num-tasks 100
fi
echo

# Find the most recent results directory
LATEST_DIR=$(find results -name "20*" -type d | sort | tail -1)
LATEST_SWEEP=$(find results -name "sweep_20*" -type d | sort | tail -1)

if [ -z "$LATEST_DIR" ] && [ -z "$LATEST_SWEEP" ]; then
    echo "   Error: No results directories found"
    exit 1
fi

# Create archive name based on timestamp
ARCHIVE_NAME="baseline_results_$TIMESTAMP.zip"

echo "Creating results archive: $ARCHIVE_NAME"

# Create temporary directory to organize files
TEMP_DIR="temp_$TIMESTAMP"
mkdir -p "$TEMP_DIR"

# Copy latest baseline results if available
if [ ! -z "$LATEST_DIR" ]; then
    echo "   Adding baseline results from: $LATEST_DIR"
    mkdir -p "$TEMP_DIR/baseline"
    cp -r "$LATEST_DIR"/* "$TEMP_DIR/baseline/" 2>/dev/null || true
fi

# Copy latest sweep results if available
if [ ! -z "$LATEST_SWEEP" ]; then
    echo "   Adding sweep results from: $LATEST_SWEEP"
    mkdir -p "$TEMP_DIR/sweeps"
    cp -r "$LATEST_SWEEP"/* "$TEMP_DIR/sweeps/" 2>/dev/null || true
fi

# Find and include any other recent result directories (last 2 hours)
echo "   Searching for additional recent results..."
find results -name "20*" -type d -newermt "2 hours ago" | while read -r dir; do
    if [[ "$dir" != "$LATEST_DIR" && "$dir" != "$LATEST_SWEEP" ]]; then
        dirname_only=$(basename "$dir")
        echo "   Adding recent result: $dir"
        mkdir -p "$TEMP_DIR/additional/$dirname_only"
        cp -r "$dir"/* "$TEMP_DIR/additional/$dirname_only/" 2>/dev/null || true
    fi
done

# Create ZIP archive
if command -v zip >/dev/null 2>&1; then
    zip -r "$ARCHIVE_NAME" "$TEMP_DIR"/* >/dev/null
    echo "Created archive: $ARCHIVE_NAME"
else
    echo "Warning: zip command not found, creating tar.gz instead"
    ARCHIVE_NAME="baseline_results_$TIMESTAMP.tar.gz"
    tar -czf "$ARCHIVE_NAME" -C "$TEMP_DIR" .
    echo "Created archive: $ARCHIVE_NAME"
fi

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

# Show archive contents summary
echo
echo "📋 Archive contents summary:"
if [[ "$ARCHIVE_NAME" == *.zip ]]; then
    unzip -l "$ARCHIVE_NAME" | head -20
else
    tar -tzf "$ARCHIVE_NAME" | head -20
fi

echo
echo "Baseline experiment completed successfully!"
echo "Results archived as: $ARCHIVE_NAME"
echo "Archive contains CSV data and PNG visualizations"
echo
echo "To extract:"
if [[ "$ARCHIVE_NAME" == *.zip ]]; then
    echo "   unzip $ARCHIVE_NAME"
else  
    echo "   tar -xzf $ARCHIVE_NAME"
fi
echo

# Deactivate virtual environment
deactivate
echo "Virtual environment deactivated"