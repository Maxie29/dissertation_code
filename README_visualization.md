# Visualization Guide for Battery Offloading Simulation

This guide explains how to use the visualization tools provided for analyzing simulation results.

## Available Tools

### 1. Jupyter Notebook Template (`notebooks/analysis_template.ipynb`)

Interactive analysis environment with comprehensive visualizations:

- **Auto-loads latest results** from the results directory
- **5 main visualizations**:
  - Latency distribution histogram (by execution site)
  - Battery SoC curve over time
  - Energy consumption box plots
  - Task distribution pie charts (site & type)
  - Task execution timeline
- **Summary statistics** table
- **Automatic figure saving** to results/figures/

**Usage:**
```bash
# Start Jupyter in the project directory
jupyter notebook
# Open: notebooks/analysis_template.ipynb
# Run all cells to generate analysis
```

### 2. Standalone Plotting Script (`src/battery_offloading/plot_results.py`)

Command-line script for batch plot generation:

**Basic usage:**
```bash
# Plot specific results directory
python -m battery_offloading.plot_results --results-dir results/20250829_180716

# Auto-find latest results in results directory
python -m battery_offloading.plot_results --results-dir results --auto-find
```

**Output:** Creates `figures/` directory with 6 PNG files:
- `latency_distribution.png` - Latency histogram by execution site
- `soc_curve.png` - Battery SoC over time
- `energy_boxplot.png` - Energy consumption by site
- `distribution_pies.png` - Task distribution pie charts
- `task_timeline.png` - Task execution timeline
- `performance_summary.png` - Multi-metric summary dashboard

## Generated Visualizations

### 1. Latency Distribution Histogram
- Shows task latency distribution
- Color-coded by execution site (Local/Edge/Cloud)
- Includes mean and P95 reference lines
- **Units:** Milliseconds (ms)

### 2. Battery SoC Curve
- Battery state of charge over simulation time
- Shows impact of each task execution
- Execution sites marked with different colors
- **Units:** Percentage (%) vs Time (seconds)

### 3. Energy Consumption Box Plot
- Energy consumption distribution by execution site
- Shows median, quartiles, and outliers
- Mean values annotated on each box
- **Units:** Watt-hours (Wh)

### 4. Task Distribution Pie Charts
- Left: Distribution by execution site (Local/Edge/Cloud)
- Right: Distribution by task type (NAV/SLAM/GENERIC)
- Shows percentages and absolute counts
- **Units:** Task counts and percentages

### 5. Task Timeline
- Horizontal bars showing task execution periods
- Color-coded by execution site
- Sorted by arrival time
- **Units:** Time (seconds)

### 6. Performance Summary Dashboard (Script only)
- 4-panel summary with:
  - Latency over time
  - Energy per task
  - Execution site over time
  - Key metrics bar chart

## Chart Requirements Met

✅ **Clear axis labels and units** - All plots include proper axis labels with units (ms, %, Wh, seconds)
✅ **Matplotlib only** - No seaborn dependency, pure matplotlib implementation
✅ **PNG output** - All plots saved as high-resolution PNG files (300 DPI)
✅ **3+ charts minimum** - 6 different visualization types provided

## Example Usage

### For baseline results:
```bash
# Generate baseline simulation
cd src
python -m battery_offloading.cli run --config ../configs/baseline.yaml --num-tasks 50

# Generate plots
python -m battery_offloading.plot_results --results-dir results --auto-find
```

### For sweep results:
```bash
# Generate sweep results
python -m battery_offloading.cli run --config ../configs/sweep_edge_latency.yaml --num-tasks 20

# Generate plots (finds sweep directory automatically)
python -m battery_offloading.plot_results --results-dir results --auto-find
```

## File Organization

After running visualizations:
```
results/20250829_180716/          # Simulation results
├── per_task_results.csv          # Per-task data
├── summary_statistics.csv        # Summary metrics
└── figures/                      # Generated plots
    ├── latency_distribution.png
    ├── soc_curve.png
    ├── energy_boxplot.png
    ├── distribution_pies.png
    ├── task_timeline.png
    └── performance_summary.png
```

## Dependencies

The visualization tools require:
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `matplotlib` - Plotting library
- `pathlib` - Path handling

Install with: `pip install matplotlib pandas numpy`