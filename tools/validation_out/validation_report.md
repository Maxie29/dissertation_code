# Battery-Aware Offloading Thesis Validation Report

**Generated:** 2025-08-31 18:21:02
**Runs Analyzed:** 110
**Strict Mode:** No

## Executive Summary

| Validation Point | Status | Summary |
|------------------|--------|---------|
| Threshold 30Pct | PASS | OK |
| Nav Slam Local | PASS | OK |
| Local Edge Tradeoff | PASS | OK |
| Workload Stability | PASS | 0 issues |
| Task Type Impact | PASS | OK |
| Soc Curve | PASS | 0 violations |
| Deadline Miss | PASS | OK |

---

## Threshold 30Pct

**Status:** PASS
**Total Violations:** 0

### SoC > 30% Distribution (GENERIC tasks should avoid CLOUD)

| Run | Total | Local | Edge | Cloud | Violations |
|-----|-------|-------|------|-------|------------|
| results | 144 | 53 | 91 | 0 | 0 |
| results | 144 | 53 | 91 | 0 | 0 |
| results | 37 | 15 | 22 | 0 | 0 |
| results | 37 | 15 | 22 | 0 | 0 |
| results | 37 | 15 | 22 | 0 | 0 |
| results | 141 | 59 | 82 | 0 | 0 |
| results | 37 | 15 | 22 | 0 | 0 |
| results | 141 | 70 | 71 | 0 | 0 |
| results | 141 | 70 | 71 | 0 | 0 |
| results | 143 | 68 | 75 | 0 | 0 |
| results | 143 | 68 | 75 | 0 | 0 |
| results | 73 | 37 | 36 | 0 | 0 |
| results | 105 | 51 | 54 | 0 | 0 |
| balanced | 88 | 49 | 39 | 0 | 0 |
| generic_only | 120 | 62 | 58 | 0 | 0 |
| nav_intensive | 28 | 15 | 13 | 0 | 0 |
| slam_intensive | 39 | 18 | 21 | 0 | 0 |
| very_heavy_balanced | 73 | 42 | 31 | 0 | 0 |
| heavy_balanced | 67 | 40 | 27 | 0 | 0 |
| medium_balanced | 67 | 30 | 37 | 0 | 0 |
| light_balanced | 62 | 25 | 37 | 0 | 0 |
| edge_heavy | 92 | 20 | 72 | 0 | 0 |
| balanced | 79 | 38 | 41 | 0 | 0 |
| local_heavy | 87 | 68 | 19 | 0 | 0 |
| edge_heavy | 60 | 11 | 49 | 0 | 0 |
| balanced | 52 | 27 | 25 | 0 | 0 |
| local_heavy | 54 | 43 | 11 | 0 | 0 |
| balanced | 88 | 49 | 39 | 0 | 0 |
| generic_only | 120 | 62 | 58 | 0 | 0 |
| nav_intensive | 28 | 15 | 13 | 0 | 0 |
| slam_intensive | 39 | 18 | 21 | 0 | 0 |
| very_heavy_balanced | 73 | 42 | 31 | 0 | 0 |
| heavy_balanced | 67 | 40 | 27 | 0 | 0 |
| medium_balanced | 67 | 30 | 37 | 0 | 0 |
| light_balanced | 62 | 25 | 37 | 0 | 0 |
| edge_heavy | 92 | 20 | 72 | 0 | 0 |
| balanced | 79 | 38 | 41 | 0 | 0 |
| local_heavy | 87 | 68 | 19 | 0 | 0 |
| crossing_threshold_33pct | 54 | 31 | 23 | 0 | 0 |
| just_above_32pct | 39 | 24 | 15 | 0 | 0 |
| above_35pct | 73 | 32 | 41 | 0 | 0 |
| high_45pct | 71 | 36 | 35 | 0 | 0 |
| crossing_threshold_33pct | 5 | 4 | 1 | 0 | 0 |
| just_above_32pct | 3 | 3 | 0 | 0 | 0 |
| above_35pct | 4 | 2 | 2 | 0 | 0 |
| high_45pct | 5 | 2 | 3 | 0 | 0 |
| crossing_threshold_33pct | 11 | 8 | 3 | 0 | 0 |
| critical_15pct | 6 | 5 | 1 | 0 | 0 |
| very_low_20pct | 12 | 7 | 5 | 0 | 0 |
| low_25pct | 8 | 6 | 2 | 0 | 0 |
| just_below_28pct | 12 | 4 | 8 | 0 | 0 |
| exactly_30pct | 12 | 4 | 8 | 0 | 0 |
| just_above_32pct | 6 | 3 | 3 | 0 | 0 |
| above_35pct | 9 | 3 | 6 | 0 | 0 |
| high_45pct | 13 | 5 | 8 | 0 | 0 |
| crossing_threshold_33pct | 69 | 42 | 27 | 0 | 0 |
| critical_15pct | 69 | 34 | 35 | 0 | 0 |
| very_low_20pct | 81 | 32 | 49 | 0 | 0 |
| low_25pct | 85 | 42 | 43 | 0 | 0 |
| just_below_28pct | 67 | 34 | 33 | 0 | 0 |
| exactly_30pct | 75 | 36 | 39 | 0 | 0 |
| just_above_32pct | 77 | 47 | 30 | 0 | 0 |
| above_35pct | 73 | 32 | 41 | 0 | 0 |
| high_45pct | 71 | 36 | 35 | 0 | 0 |
| generic_only | 200 | 105 | 95 | 0 | 0 |
| nav_intensive | 102 | 54 | 48 | 0 | 0 |
| slam_intensive | 122 | 66 | 56 | 0 | 0 |
| very_heavy_balanced | 130 | 66 | 64 | 0 | 0 |
| heavy_edge_heavy | 145 | 25 | 120 | 0 | 0 |
| heavy_balanced | 144 | 71 | 73 | 0 | 0 |
| medium_local_heavy | 139 | 110 | 29 | 0 | 0 |
| medium_edge_heavy | 136 | 29 | 107 | 0 | 0 |
| medium_balanced | 141 | 78 | 63 | 0 | 0 |
| light_local_heavy | 135 | 114 | 21 | 0 | 0 |
| light_edge_heavy | 131 | 30 | 101 | 0 | 0 |
| light_balanced | 131 | 64 | 67 | 0 | 0 |
| edge_80ms | 141 | 78 | 63 | 0 | 0 |
| edge_40ms | 135 | 73 | 62 | 0 | 0 |
| edge_20ms | 131 | 68 | 63 | 0 | 0 |
| edge_10ms | 131 | 64 | 67 | 0 | 0 |
| generic_only | 50 | 26 | 24 | 0 | 0 |
| nav_intensive | 20 | 9 | 11 | 0 | 0 |
| slam_intensive | 30 | 18 | 12 | 0 | 0 |
| very_heavy_balanced | 30 | 22 | 8 | 0 | 0 |
| heavy_edge_heavy | 34 | 4 | 30 | 0 | 0 |
| heavy_balanced | 36 | 19 | 17 | 0 | 0 |
| medium_local_heavy | 39 | 32 | 7 | 0 | 0 |
| medium_edge_heavy | 37 | 8 | 29 | 0 | 0 |
| medium_balanced | 35 | 18 | 17 | 0 | 0 |
| light_local_heavy | 31 | 27 | 4 | 0 | 0 |
| light_edge_heavy | 33 | 4 | 29 | 0 | 0 |
| light_balanced | 29 | 10 | 19 | 0 | 0 |
| edge_80ms | 141 | 78 | 63 | 0 | 0 |
| edge_40ms | 135 | 73 | 62 | 0 | 0 |
| edge_20ms | 131 | 68 | 63 | 0 | 0 |
| edge_10ms | 131 | 64 | 67 | 0 | 0 |

### SoC ≤ 30% Distribution (GENERIC tasks MUST use CLOUD)

| Run | Total | Local | Edge | Cloud | Violations |
|-----|-------|-------|------|-------|------------|
| results | 67 | 0 | 0 | 67 | 0 |
| results | 76 | 0 | 0 | 76 | 0 |
| results | 67 | 0 | 0 | 67 | 0 |
| results | 76 | 0 | 0 | 76 | 0 |
| crossing_threshold_33pct | 15 | 0 | 0 | 15 | 0 |
| critical_15pct | 69 | 0 | 0 | 69 | 0 |
| very_low_20pct | 81 | 0 | 0 | 81 | 0 |
| low_25pct | 85 | 0 | 0 | 85 | 0 |
| just_below_28pct | 67 | 0 | 0 | 67 | 0 |
| exactly_30pct | 75 | 0 | 0 | 75 | 0 |
| just_above_32pct | 38 | 0 | 0 | 38 | 0 |
| critical_15pct | 3 | 0 | 0 | 3 | 0 |
| very_low_20pct | 5 | 0 | 0 | 5 | 0 |
| low_25pct | 3 | 0 | 0 | 3 | 0 |
| just_below_28pct | 7 | 0 | 0 | 7 | 0 |
| exactly_30pct | 8 | 0 | 0 | 8 | 0 |

---

## Nav Slam Local

**Status:** PASS
**Total Violations:** 0
**Average Compliance:** 100.0%


---

## Local Edge Tradeoff

**Status:** PASS

### Trade-off Analysis

| Metric | Edge Heavy | Local Heavy | Difference |
|--------|------------|-------------|------------|
| Energy (Wh) | 0.066 | 0.099 | +0.034 |
| Mean Latency (ms) | 2066.6 | 1349.2 | -717.3 |

![Trade-off Chart](figures/tradeoff_edge_vs_local.png)


---

## Workload Stability

**Status:** PASS
**Issues Found:** 0

![Stability Chart](figures/stability_energy_vs_load.png)
![Stability Chart](figures/stability_soc_vs_load.png)
![Stability Chart](figures/stability_p95_vs_load.png)

---

## Task Type Impact

**Status:** PASS
**Scenarios Analyzed:** 3

### Task Type Impact Analysis

| Scenario | Local Ratio | Energy (Wh) | Latency (ms) |
|----------|-------------|-------------|--------------|
| slam_intensive | 0.78 | 0.236 | 2995.1 |
| nav_intensive | 0.83 | 0.235 | 2752.4 |
| generic_only | 0.52 | 0.161 | 2396.1 |

---

## Soc Curve

**Status:** PASS
**Violations:** 0

![SoC Curve](figures/soc_curve_example.png)


---

## Deadline Miss

**Status:**  ANALYZED (Limitation Study)
**Average Miss Rate:** 0.741
**Maximum Miss Rate:** 1.000

**Assessment:** High miss rate indicates need for dynamic/multi-objective optimization


---

## Reproduction Commands

### Windows PowerShell

```powershell
# Run baseline experiment
.\scripts\run_baseline.ps1

# Run low battery validation
.\scripts\run_low_battery_test.ps1

# Run this validation
$env:PYTHONPATH="src"
python tools\validate_thesis_claims.py --roots results extracted_results --out-dir tools\validation_out
```

### macOS/Linux

```bash
# Run baseline experiment
./scripts/run_baseline.sh

# Run low battery validation (adapt PowerShell script)

# Run this validation
export PYTHONPATH=src
python tools/validate_thesis_claims.py --roots results extracted_results --out-dir tools/validation_out
```
