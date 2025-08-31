# Battery-Aware Offloading Validation Report Generation Guide

## Overview

This guide explains how to generate comprehensive validation reports for the battery-aware offloading simulation framework. The validation report automatically verifies 7 key thesis claims and generates detailed analysis with visualizations.

## Quick Start

### Prerequisites

1. **Environment Setup**:
   ```powershell
   # Windows
   $env:PYTHONPATH="src"
   
   # Linux/macOS  
   export PYTHONPATH=src
   ```

2. **Required Dependencies**:
   - Python 3.11+
   - pandas, numpy, matplotlib
   - All simulation framework dependencies

### Basic Usage

```powershell
# Generate validation report from existing results
python tools/validate_thesis_claims.py --roots results --out-dir tools/validation_out
```

## Complete Workflow

### 1. Backup Previous Reports (Optional)

```powershell
# Create archive for old reports
mkdir tools/validation_archive -ErrorAction SilentlyContinue

# Backup existing validation results
if (Test-Path tools/validation_out) {
    Move-Item tools/validation_out tools/validation_archive/validation_out_$(Get-Date -Format 'yyyyMMdd_HHmmss')
}
```

### 2. Run Required Experiments

The validation report requires specific types of experiments to validate all claims:

#### A. Baseline Experiment
```powershell
python -m battery_offloading run --config configs/baseline.yaml --num-tasks 150
```

#### B. Trade-off Analysis (Critical)
```powershell
python -m battery_offloading run --config configs/sweep_tradeoff_validation.yaml --num-tasks 120
```
*Validates Local vs Edge energy/latency trade-offs*

#### C. Workload Stability Analysis  
```powershell
python -m battery_offloading run --config configs/sweep_workload_stability.yaml --num-tasks 100
```
*Validates system behavior under different load levels*

#### D. Task Type Impact Analysis
```powershell
python -m battery_offloading run --config configs/sweep_task_types.yaml --num-tasks 120
```
*Validates NAV/SLAM vs GENERIC task behavior*

#### E. Low Battery Threshold Tests (Optional)
```powershell
python -m battery_offloading run --config configs/sweep_low_battery.yaml --num-tasks 100
```
*Validates 30% SoC threshold rule*

### 3. Generate Validation Report

```powershell
python tools/validate_thesis_claims.py --roots results extracted_results --out-dir tools/validation_out
```

#### Command Options:
- `--roots`: Directories to search for experiment results (default: `results extracted_results`)
- `--out-dir`: Output directory for validation results (default: `tools/validation_out`)
- `--strict`: Use stricter validation thresholds

### 4. View Results

The validation process generates:

- **`validation_report.md`**: Comprehensive markdown report
- **`validation_summary.json`**: Machine-readable summary  
- **`figures/*.png`**: Visualization charts
- **`violations/*.csv`**: Detailed violation records (if any)

## Validation Claims

The tool validates 7 key thesis claims:

### 1. 30% SoC Threshold Rule ✓
- **Rule**: SoC ≤ 30% → GENERIC tasks MUST use CLOUD
- **Rule**: SoC > 30% → GENERIC tasks may use LOCAL/EDGE
- **Validation**: Checks all GENERIC tasks for compliance

### 2. NAV/SLAM Always Local ✓
- **Rule**: NAV and SLAM tasks ALWAYS execute locally regardless of SoC
- **Validation**: Ensures 100% compliance rate

### 3. Local vs Edge Trade-off ✓
- **Expected**: Local has lower latency but higher energy consumption
- **Expected**: Edge has higher latency but lower energy consumption  
- **Validation**: Compares edge_heavy vs local_heavy configurations

### 4. Workload Stability ✓
- **Expected**: Energy consumption increases gradually with load
- **Expected**: Final SoC decreases monotonically with load
- **Expected**: Latency increases smoothly without explosion
- **Validation**: Tests light → medium → heavy → very_heavy workloads

### 5. Task Type Impact ✓
- **Expected**: NAV/SLAM intensive → higher local_ratio, energy, latency
- **Expected**: Generic only → lower local_ratio, energy, latency
- **Validation**: Compares slam_intensive, nav_intensive, generic_only

### 6. SoC Curve Correctness ✓
- **Expected**: Battery SoC decreases monotonically (non-increasing)
- **Validation**: Checks all task sequences for SoC violations

### 7. Deadline Miss Rate Analysis 📊
- **Purpose**: Documents known system limitations
- **Analysis**: Records miss rates for future improvement (not pass/fail)

## Configuration Requirements

### Experiment Configuration Files

Your configurations must include specific experiment types for full validation:

#### Trade-off Configuration Example:
```yaml
# configs/sweep_tradeoff_validation.yaml
sweep_parameters:
  task_generation:
    - edge_affinity_ratio: 0.2    # local_heavy
      label: "local_heavy"
    - edge_affinity_ratio: 0.8    # edge_heavy  
      label: "edge_heavy"
```

#### Workload Configuration Example:
```yaml
# configs/sweep_workload_stability.yaml
sweep_parameters:
  task_generation:
    - arrival_rate_per_sec: 1.0
      label: "light_balanced"
    - arrival_rate_per_sec: 2.5
      label: "medium_balanced"
    - arrival_rate_per_sec: 4.0
      label: "heavy_balanced"
    - arrival_rate_per_sec: 6.0
      label: "very_heavy_balanced"
```

#### Task Type Configuration Example:
```yaml  
# configs/sweep_task_types.yaml
sweep_parameters:
  task_generation:
    - slam_ratio: 0.6
      label: "slam_intensive"
    - nav_ratio: 0.6
      label: "nav_intensive"
    - nav_ratio: 0.0
      slam_ratio: 0.0
      label: "generic_only"
```

## Expected Results

A successful validation should show:

```
VALIDATION SUMMARY:
   PASS Threshold 30Pct       ← 30% rule enforced
   PASS Nav Slam Local        ← NAV/SLAM stay local  
   PASS Local Edge Tradeoff   ← Energy/latency trade-off validated
   PASS Workload Stability    ← System stable under load
   PASS Task Type Impact      ← Task types behave correctly
   PASS Soc Curve            ← Battery discharge monotonic
   PASS Deadline Miss        ← Limitations documented

Overall: 7/7 validations passed
```

## Troubleshooting

### Common Issues

#### 1. "Missing required runs" Error
**Problem**: Trade-off validation fails due to missing edge_heavy/local_heavy experiments
**Solution**: Run `sweep_tradeoff_validation.yaml` configuration

#### 2. "Insufficient load level runs" Error  
**Problem**: Stability validation fails due to missing light/medium/heavy experiments
**Solution**: Run `sweep_workload_stability.yaml` configuration

#### 3. Unicode Encoding Errors
**Problem**: Console encoding issues on Windows
**Solution**: 
```powershell
# Set UTF-8 encoding
chcp 65001
# Or run with output redirection
python tools/validate_thesis_claims.py --roots results > validation.log 2>&1
```

#### 4. JSON Serialization Errors
**Problem**: Non-serializable objects in results
**Solution**: This is a known minor issue that doesn't affect the main report generation

### Debugging Tips

1. **Check Experiment Labels**: Ensure your experiment directories have meaningful names
2. **Verify Data Structure**: Confirm `summary_statistics.csv` and `per_task_results.csv` exist
3. **Run Individual Validations**: Use `--debug` flag for detailed output
4. **Check File Permissions**: Ensure write access to output directory

## Advanced Usage

### Custom Validation Thresholds

```powershell
# Use stricter validation criteria
python tools/validate_thesis_claims.py --roots results --strict
```

### Multiple Data Sources

```powershell  
# Validate results from multiple directories
python tools/validate_thesis_claims.py --roots results extracted_results archived_results
```

### Automated Validation Pipeline

```powershell
# Complete validation pipeline script
./scripts/run_validation_experiments.ps1
```

## Integration with Research

### For Paper Writing

1. **Quantitative Evidence**: Use metrics from `validation_summary.json`
2. **Visualizations**: Include charts from `figures/` directory
3. **Violation Analysis**: Reference `violations/*.csv` for detailed analysis
4. **Reproducibility**: Include reproduction commands from report

### For Code Reviews

1. **Regression Testing**: Run validation after code changes
2. **Performance Benchmarks**: Compare validation metrics over time
3. **Rule Compliance**: Verify hard constraints remain enforced

## File Structure

```
tools/validation_out/
├── validation_report.md          # Main report (human-readable)
├── validation_summary.json       # Summary (machine-readable)
├── figures/
│   ├── tradeoff_edge_vs_local.png
│   ├── stability_energy_vs_load.png
│   ├── stability_soc_vs_load.png
│   ├── stability_p95_vs_load.png
│   └── soc_curve_example.png
└── violations/                   # Created only if violations found
    ├── 30pct_threshold_violations.csv
    ├── nav_slam_violations.csv
    └── soc_curve_violations.csv
```

## Maintenance

### Regular Validation

- Run validation after major code changes
- Include validation in CI/CD pipeline  
- Archive reports for version tracking
- Update thresholds as system evolves

### Configuration Updates

- Keep experiment configurations in sync with system capabilities
- Update expected behaviors as requirements change
- Version control all configuration files
- Document configuration rationale

---

## Quick Reference Commands

```powershell
# Complete workflow (Windows)
$env:PYTHONPATH="src"

# Run all required experiments
python -m battery_offloading run --config configs/baseline.yaml --num-tasks 150
python -m battery_offloading run --config configs/sweep_tradeoff_validation.yaml --num-tasks 120  
python -m battery_offloading run --config configs/sweep_workload_stability.yaml --num-tasks 100
python -m battery_offloading run --config configs/sweep_task_types.yaml --num-tasks 120

# Generate validation report
python tools/validate_thesis_claims.py --roots results --out-dir tools/validation_out

# View results
Get-Content tools/validation_out/validation_report.md
```

```bash
# Complete workflow (Linux/macOS)
export PYTHONPATH=src

# Run all required experiments  
python -m battery_offloading run --config configs/baseline.yaml --num-tasks 150
python -m battery_offloading run --config configs/sweep_tradeoff_validation.yaml --num-tasks 120
python -m battery_offloading run --config configs/sweep_workload_stability.yaml --num-tasks 100
python -m battery_offloading run --config configs/sweep_task_types.yaml --num-tasks 120

# Generate validation report
python tools/validate_thesis_claims.py --roots results --out-dir tools/validation_out

# View results
cat tools/validation_out/validation_report.md
```

---

**Last Updated**: August 31, 2025
**Version**: 1.0
**Contact**: Battery Offloading Research Team