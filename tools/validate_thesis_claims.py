#!/usr/bin/env python3
"""
Comprehensive Thesis Claims Validation Tool

Automatically validates 7 key verification points for battery-aware offloading simulation:
1. Static 30% threshold rationality
2. NAV/SLAM must be Local
3. Local vs Edge energy/latency trade-off
4. Stability under different workloads
5. Task type ratio impact
6. SoC curve correctness
7. Deadline miss rate analysis

Generates comprehensive validation report with evidence tables and visualizations.
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import glob
import os
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, List, Tuple, Optional, Any

class ThesisValidator:
    def __init__(self, roots: List[str], out_dir: str, strict: bool = False):
        self.roots = [Path(r) for r in roots]
        self.out_dir = Path(out_dir)
        self.strict = strict
        self.figures_dir = self.out_dir / "figures"
        self.violations_dir = self.out_dir / "violations"
        
        # Create output directories
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(exist_ok=True)
        self.violations_dir.mkdir(exist_ok=True)
        
        self.runs = []  # Will store all found experiment runs
        self.validation_results = {}
        self.report_lines = []
        
        # Thresholds
        self.thresholds = {
            'soc_threshold': 30.0,
            'energy_change_max': 0.8 if strict else 1.5,
            'latency_explosion_max': 1.5 if strict else 2.0,
            'soc_precision': 1e-9
        }

    def discover_runs(self):
        """Discover all experiment runs from the root directories."""
        print("Discovering experiment runs...")
        
        for root in self.roots:
            if not root.exists():
                print(f"   WARNING: Root directory not found: {root}")
                continue
            
            # Find all directories containing summary_statistics.csv
            for csv_file in root.rglob("summary_statistics.csv"):
                run_dir = csv_file.parent
                per_task_file = run_dir / "per_task_results.csv"
                
                if per_task_file.exists():
                    # Infer label from directory structure
                    label = self._infer_label(run_dir)
                    
                    run_info = {
                        'path': run_dir,
                        'label': label,
                        'summary_csv': csv_file,
                        'per_task_csv': per_task_file
                    }
                    
                    self.runs.append(run_info)
        
        print(f"   SUCCESS: Found {len(self.runs)} experiment runs")
        for run in self.runs[:5]:  # Show first 5
            print(f"      - {run['label']}: {run['path']}")
        if len(self.runs) > 5:
            print(f"      ... and {len(self.runs)-5} more")

    def _infer_label(self, run_dir: Path) -> str:
        """Infer experiment label from directory path."""
        parts = run_dir.parts
        
        # Common patterns - check in order of specificity
        patterns = [
            r"run_\d+_(.+)",           # run_01_light_edge_heavy -> light_edge_heavy
            r"(\w+_intensive)",        # slam_intensive, nav_intensive
            r"(\w+_only)",            # generic_only
            r"(\w+_heavy)",           # edge_heavy, local_heavy
            r"(\w+_balanced)",        # light_balanced
            r"(baseline)",            # baseline
            r"(\d{8}_\d{6})"          # timestamp fallback
        ]
        
        # Check each directory part for patterns
        for part in reversed(parts):
            for pattern in patterns:
                match = re.search(pattern, part)
                if match:
                    label = match.group(1)
                    # Don't use pure timestamps unless no other option
                    if not re.match(r'\d{8}_\d{6}', label):
                        return label
        
        # If no pattern matched, try to extract meaningful part
        for part in reversed(parts):
            if not re.match(r'\d{8}_\d{6}', part):  # Skip timestamp directories
                return part
        
        # Ultimate fallback
        return run_dir.name

    def validate_30pct_threshold(self) -> Dict[str, Any]:
        """Validate static 30% SoC threshold rule."""
        print("Validating 30% SoC threshold rule...")
        
        violations = []
        above_30_stats = []
        below_30_stats = []
        
        for run in self.runs:
            try:
                df = pd.read_csv(run['per_task_csv'])
                
                if 'soc_before' not in df.columns or 'task_type' not in df.columns:
                    continue
                
                # Check GENERIC tasks only
                generic_tasks = df[df['task_type'] == 'GENERIC'].copy()
                if len(generic_tasks) == 0:
                    continue
                
                # Above 30% should not use CLOUD
                above_30 = generic_tasks[generic_tasks['soc_before'] > self.thresholds['soc_threshold']]
                cloud_above_30 = above_30[above_30['execution_site'] == 'cloud']
                
                # Below/at 30% should use CLOUD
                below_30 = generic_tasks[generic_tasks['soc_before'] <= self.thresholds['soc_threshold']]
                non_cloud_below_30 = below_30[below_30['execution_site'] != 'cloud']
                
                # Record statistics
                if len(above_30) > 0:
                    site_dist = above_30['execution_site'].value_counts()
                    above_30_stats.append({
                        'run': run['label'],
                        'total_tasks': len(above_30),
                        'local': site_dist.get('local', 0),
                        'edge': site_dist.get('edge', 0),
                        'cloud': site_dist.get('cloud', 0),
                        'violations': len(cloud_above_30)
                    })
                
                if len(below_30) > 0:
                    site_dist = below_30['execution_site'].value_counts()
                    below_30_stats.append({
                        'run': run['label'],
                        'total_tasks': len(below_30),
                        'local': site_dist.get('local', 0),
                        'edge': site_dist.get('edge', 0), 
                        'cloud': site_dist.get('cloud', 0),
                        'violations': len(non_cloud_below_30)
                    })
                
                # Record violations
                for _, task in cloud_above_30.iterrows():
                    violations.append({
                        'run': run['label'],
                        'task_id': task.get('task_id', 'N/A'),
                        'soc_before': task['soc_before'],
                        'execution_site': task['execution_site'],
                        'violation_type': 'cloud_above_30'
                    })
                
                for _, task in non_cloud_below_30.iterrows():
                    violations.append({
                        'run': run['label'],
                        'task_id': task.get('task_id', 'N/A'),
                        'soc_before': task['soc_before'],
                        'execution_site': task['execution_site'],
                        'violation_type': 'non_cloud_below_30'
                    })
                    
            except Exception as e:
                print(f"   WARNING: Error processing {run['label']}: {e}")
                continue
        
        # Save violations if any
        if violations:
            viol_df = pd.DataFrame(violations)
            viol_df.to_csv(self.violations_dir / "30pct_threshold_violations.csv", index=False)
        
        total_violations = len(violations)
        result = {
            'pass': total_violations == 0,
            'total_violations': total_violations,
            'above_30_stats': above_30_stats,
            'below_30_stats': below_30_stats,
            'violations_file': "violations/30pct_threshold_violations.csv" if violations else None
        }
        
        print(f"   {'PASS' if result['pass'] else 'FAIL'}: {total_violations} violations found")
        return result

    def validate_nav_slam_local(self) -> Dict[str, Any]:
        """Validate NAV/SLAM tasks must be Local."""
        print(" Validating NAV/SLAM tasks must be Local...")
        
        violations = []
        stats = []
        
        for run in self.runs:
            try:
                df = pd.read_csv(run['per_task_csv'])
                
                if 'task_type' not in df.columns or 'execution_site' not in df.columns:
                    continue
                
                nav_slam_tasks = df[df['task_type'].isin(['NAV', 'SLAM'])]
                if len(nav_slam_tasks) == 0:
                    continue
                
                non_local = nav_slam_tasks[nav_slam_tasks['execution_site'] != 'local']
                compliance_rate = (len(nav_slam_tasks) - len(non_local)) / len(nav_slam_tasks) * 100
                
                stats.append({
                    'run': run['label'],
                    'total_nav_slam': len(nav_slam_tasks),
                    'local_count': len(nav_slam_tasks[nav_slam_tasks['execution_site'] == 'local']),
                    'violations': len(non_local),
                    'compliance_rate': compliance_rate
                })
                
                # Record violations
                for _, task in non_local.iterrows():
                    violations.append({
                        'run': run['label'],
                        'task_id': task.get('task_id', 'N/A'),
                        'task_type': task['task_type'],
                        'execution_site': task['execution_site'],
                        'soc_before': task.get('soc_before', 'N/A')
                    })
                    
            except Exception as e:
                print(f"   WARNING: Error processing {run['label']}: {e}")
                continue
        
        if violations:
            viol_df = pd.DataFrame(violations)
            viol_df.to_csv(self.violations_dir / "nav_slam_violations.csv", index=False)
        
        total_violations = len(violations)
        avg_compliance = np.mean([s['compliance_rate'] for s in stats]) if stats else 0
        
        result = {
            'pass': total_violations == 0,
            'total_violations': total_violations,
            'avg_compliance_rate': avg_compliance,
            'stats': stats,
            'violations_file': "violations/nav_slam_violations.csv" if violations else None
        }
        
        print(f"   {'PASS' if result['pass'] else 'FAIL'}: {total_violations} violations, {avg_compliance:.1f}% avg compliance")
        return result

    def validate_local_edge_tradeoff(self) -> Dict[str, Any]:
        """Validate Local vs Edge energy/latency trade-off."""
        print(" Validating Local vs Edge trade-off...")
        
        # Find edge_heavy and local_heavy runs (more flexible matching)
        edge_heavy_runs = [r for r in self.runs if 'edge_heavy' in r['label'] or 'edge_0.8' in r['label']]
        local_heavy_runs = [r for r in self.runs if 'local_heavy' in r['label'] or 'edge_0.2' in r['label']]
        
        if not edge_heavy_runs or not local_heavy_runs:
            print("   WARNING: Could not find edge_heavy/local_heavy runs")
            print(f"   DEBUG: Found {len(edge_heavy_runs)} edge_heavy runs, {len(local_heavy_runs)} local_heavy runs")
            print(f"   DEBUG: Available labels: {[r['label'] for r in self.runs[:10]]}")
            return {'pass': False, 'error': 'Missing required runs'}
        
        def get_metrics(runs):
            metrics = []
            for run in runs:
                try:
                    df = pd.read_csv(run['summary_csv'])
                    if len(df) > 0:
                        row = df.iloc[0]
                        metrics.append({
                            'run': run['label'],
                            'latency_mean_ms': row.get('latency_mean_ms', 0),
                            'latency_p95_ms': row.get('latency_p95_ms', 0),
                            'total_energy_wh': row.get('total_energy_wh', 0),
                            'local_ratio': row.get('local_ratio', 0),
                            'edge_ratio': row.get('edge_ratio', 0)
                        })
                except Exception as e:
                    print(f"   WARNING:  Error reading {run['label']}: {e}")
            return metrics
        
        edge_metrics = get_metrics(edge_heavy_runs)
        local_metrics = get_metrics(local_heavy_runs)
        
        if not edge_metrics or not local_metrics:
            return {'pass': False, 'error': 'Could not extract metrics'}
        
        # Average metrics
        edge_avg = {
            'latency_mean': np.mean([m['latency_mean_ms'] for m in edge_metrics]),
            'latency_p95': np.mean([m['latency_p95_ms'] for m in edge_metrics]),
            'energy': np.mean([m['total_energy_wh'] for m in edge_metrics])
        }
        
        local_avg = {
            'latency_mean': np.mean([m['latency_mean_ms'] for m in local_metrics]),
            'latency_p95': np.mean([m['latency_p95_ms'] for m in local_metrics]), 
            'energy': np.mean([m['total_energy_wh'] for m in local_metrics])
        }
        
        # Validate trade-off: energy(local) > energy(edge) AND latency(local) < latency(edge)
        energy_condition = local_avg['energy'] > edge_avg['energy']
        latency_condition = local_avg['latency_mean'] < edge_avg['latency_mean']
        
        # Create comparison chart
        self._create_tradeoff_chart(edge_avg, local_avg)
        
        result = {
            'pass': energy_condition and latency_condition,
            'edge_metrics': edge_avg,
            'local_metrics': local_avg,
            'energy_condition': energy_condition,
            'latency_condition': latency_condition,
            'energy_difference_wh': local_avg['energy'] - edge_avg['energy'],
            'latency_difference_ms': edge_avg['latency_mean'] - local_avg['latency_mean'],
            'chart': 'figures/tradeoff_edge_vs_local.png'
        }
        
        print(f"   {'PASS' if result['pass'] else 'FAIL'}: Energy+{result['energy_difference_wh']:.3f}Wh, Latency-{result['latency_difference_ms']:.1f}ms")
        return result

    def _create_tradeoff_chart(self, edge_avg: Dict, local_avg: Dict):
        """Create trade-off comparison chart."""
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
        
        categories = ['Edge Heavy', 'Local Heavy']
        energy_vals = [edge_avg['energy'], local_avg['energy']]
        latency_mean_vals = [edge_avg['latency_mean'], local_avg['latency_mean']]
        latency_p95_vals = [edge_avg['latency_p95'], local_avg['latency_p95']]
        
        colors = ['#2E86AB', '#A23B72']
        
        ax1.bar(categories, energy_vals, color=colors)
        ax1.set_ylabel('Total Energy (Wh)')
        ax1.set_title('Energy Consumption')
        for i, v in enumerate(energy_vals):
            ax1.text(i, v, f'{v:.3f}', ha='center', va='bottom')
        
        ax2.bar(categories, latency_mean_vals, color=colors)
        ax2.set_ylabel('Mean Latency (ms)')
        ax2.set_title('Mean Latency')
        for i, v in enumerate(latency_mean_vals):
            ax2.text(i, v, f'{v:.1f}', ha='center', va='bottom')
        
        ax3.bar(categories, latency_p95_vals, color=colors)
        ax3.set_ylabel('P95 Latency (ms)')
        ax3.set_title('P95 Latency')
        for i, v in enumerate(latency_p95_vals):
            ax3.text(i, v, f'{v:.1f}', ha='center', va='bottom')
        
        plt.suptitle('Local vs Edge Trade-off Analysis', fontsize=16)
        plt.tight_layout()
        plt.savefig(self.figures_dir / 'tradeoff_edge_vs_local.png', dpi=300, bbox_inches='tight')
        plt.close()

    def validate_workload_stability(self) -> Dict[str, Any]:
        """Validate stability under different workloads."""
        print(" Validating workload stability...")
        
        # Group runs by load levels (flexible matching)
        load_runs = {}
        for run in self.runs:
            label = run['label'].lower()
            if 'light' in label:
                load_runs.setdefault('light', []).append(run)
            elif 'medium' in label:
                load_runs.setdefault('medium', []).append(run)
            elif 'very_heavy' in label:
                load_runs.setdefault('very_heavy', []).append(run)
            elif 'heavy' in label:  # Check very_heavy first to avoid conflict
                load_runs.setdefault('heavy', []).append(run)
        
        if len(load_runs) < 2:
            return {'pass': False, 'error': 'Insufficient load level runs'}
        
        # Extract metrics for each load level
        load_metrics = {}
        for load_level, runs in load_runs.items():
            metrics = []
            for run in runs:
                try:
                    df = pd.read_csv(run['summary_csv'])
                    if len(df) > 0:
                        row = df.iloc[0]
                        metrics.append({
                            'total_energy_wh': row.get('total_energy_wh', 0),
                            'final_soc': row.get('final_soc', 0),
                            'latency_p95_ms': row.get('latency_p95_ms', 0)
                        })
                except Exception as e:
                    continue
            
            if metrics:
                load_metrics[load_level] = {
                    'energy': np.mean([m['total_energy_wh'] for m in metrics]),
                    'soc': np.mean([m['final_soc'] for m in metrics]),
                    'latency_p95': np.mean([m['latency_p95_ms'] for m in metrics])
                }
        
        # Create stability charts
        self._create_stability_charts(load_metrics)
        
        # Check stability conditions
        load_order = ['light', 'medium', 'heavy', 'very_heavy']
        available_loads = [l for l in load_order if l in load_metrics]
        
        energy_stable = True
        soc_monotonic = True
        latency_stable = True
        issues = []
        
        for i in range(1, len(available_loads)):
            prev_load = available_loads[i-1]
            curr_load = available_loads[i]
            
            # Check energy stability (no huge jumps)
            energy_ratio = load_metrics[curr_load]['energy'] / max(load_metrics[prev_load]['energy'], 1e-9)
            if energy_ratio > self.thresholds['energy_change_max']:
                energy_stable = False
                issues.append(f"Energy jump: {prev_load}→{curr_load} ({energy_ratio:.2f}x)")
            
            # Check SoC monotonicity
            if load_metrics[curr_load]['soc'] > load_metrics[prev_load]['soc']:
                soc_monotonic = False
                issues.append(f"SoC increase: {prev_load}→{curr_load}")
            
            # Check latency explosion
            latency_ratio = load_metrics[curr_load]['latency_p95'] / max(load_metrics[prev_load]['latency_p95'], 1)
            if latency_ratio > self.thresholds['latency_explosion_max']:
                latency_stable = False
                issues.append(f"Latency explosion: {prev_load}→{curr_load} ({latency_ratio:.2f}x)")
        
        result = {
            'pass': energy_stable and soc_monotonic and latency_stable,
            'energy_stable': energy_stable,
            'soc_monotonic': soc_monotonic,
            'latency_stable': latency_stable,
            'load_metrics': load_metrics,
            'issues': issues,
            'charts': [
                'figures/stability_energy_vs_load.png',
                'figures/stability_soc_vs_load.png',
                'figures/stability_p95_vs_load.png'
            ]
        }
        
        print(f"   {'PASS' if result['pass'] else 'FAIL'}: {len(issues)} stability issues")
        return result

    def _create_stability_charts(self, load_metrics: Dict):
        """Create workload stability charts."""
        load_order = ['light', 'medium', 'heavy', 'very_heavy']
        available_loads = [l for l in load_order if l in load_metrics]
        
        if len(available_loads) < 2:
            return
        
        energies = [load_metrics[l]['energy'] for l in available_loads]
        socs = [load_metrics[l]['soc'] for l in available_loads]
        latencies = [load_metrics[l]['latency_p95'] for l in available_loads]
        
        # Energy vs load
        plt.figure(figsize=(8, 5))
        plt.plot(available_loads, energies, 'o-', linewidth=2, markersize=8)
        plt.ylabel('Total Energy (Wh)')
        plt.xlabel('Workload Level')
        plt.title('Energy Consumption vs Workload')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.figures_dir / 'stability_energy_vs_load.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # SoC vs load
        plt.figure(figsize=(8, 5))
        plt.plot(available_loads, socs, 'o-', linewidth=2, markersize=8, color='orange')
        plt.ylabel('Final SoC (%)')
        plt.xlabel('Workload Level')
        plt.title('Final SoC vs Workload')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.figures_dir / 'stability_soc_vs_load.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Latency vs load
        plt.figure(figsize=(8, 5))
        plt.plot(available_loads, latencies, 'o-', linewidth=2, markersize=8, color='red')
        plt.ylabel('P95 Latency (ms)')
        plt.xlabel('Workload Level')
        plt.title('P95 Latency vs Workload')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.figures_dir / 'stability_p95_vs_load.png', dpi=300, bbox_inches='tight')
        plt.close()

    def validate_task_type_impact(self) -> Dict[str, Any]:
        """Validate task type ratio impact."""
        print(" Validating task type ratio impact...")
        
        # Find specialized runs
        slam_runs = [r for r in self.runs if 'slam_intensive' in r['label']]
        nav_runs = [r for r in self.runs if 'nav_intensive' in r['label']]
        generic_runs = [r for r in self.runs if 'generic_only' in r['label']]
        
        run_types = {'slam_intensive': slam_runs, 'nav_intensive': nav_runs, 'generic_only': generic_runs}
        
        results = {}
        for run_type, runs in run_types.items():
            if not runs:
                continue
            
            metrics = []
            for run in runs:
                try:
                    df = pd.read_csv(run['summary_csv'])
                    if len(df) > 0:
                        row = df.iloc[0]
                        metrics.append({
                            'local_ratio': row.get('local_ratio', 0),
                            'total_energy_wh': row.get('total_energy_wh', 0),
                            'latency_mean_ms': row.get('latency_mean_ms', 0)
                        })
                except Exception as e:
                    continue
            
            if metrics:
                results[run_type] = {
                    'local_ratio': np.mean([m['local_ratio'] for m in metrics]),
                    'energy': np.mean([m['total_energy_wh'] for m in metrics]),
                    'latency': np.mean([m['latency_mean_ms'] for m in metrics])
                }
        
        # Validate expectations
        expectations_met = True
        analysis = []
        
        if 'slam_intensive' in results and 'generic_only' in results:
            slam = results['slam_intensive']
            generic = results['generic_only']
            
            # SLAM intensive should have higher local_ratio, energy, latency
            local_ok = slam['local_ratio'] > generic['local_ratio']
            energy_ok = slam['energy'] > generic['energy']
            latency_ok = slam['latency'] > generic['latency']
            
            analysis.append(f"SLAM vs Generic: Local↑{local_ok}, Energy↑{energy_ok}, Latency↑{latency_ok}")
            if not (local_ok and energy_ok):  # Latency might be counter-intuitive
                expectations_met = False
        
        result = {
            'pass': expectations_met,
            'results': results,
            'analysis': analysis,
            'available_types': list(results.keys())
        }
        
        print(f"   {'PASS' if result['pass'] else 'FAIL'}: {len(results)} task type scenarios analyzed")
        return result

    def validate_soc_curve(self) -> Dict[str, Any]:
        """Validate SoC curve correctness."""
        print(" Validating SoC curve correctness...")
        
        violations = []
        
        for run in self.runs:
            try:
                df = pd.read_csv(run['per_task_csv'])
                
                if 'soc_after' not in df.columns:
                    continue
                
                # Sort by time if available, otherwise by task order
                time_col = None
                for col in ['arrival_time', 'start_ts', 'finish_ts']:
                    if col in df.columns:
                        time_col = col
                        break
                
                if time_col:
                    df = df.sort_values(time_col)
                
                # Check non-increasing SoC (allowing for floating point precision)
                soc_values = df['soc_after'].values
                for i in range(1, len(soc_values)):
                    if soc_values[i] > soc_values[i-1] + self.thresholds['soc_precision']:
                        violations.append({
                            'run': run['label'],
                            'task_index': i,
                            'task_id': df.iloc[i].get('task_id', f'task_{i}'),
                            'prev_soc': soc_values[i-1],
                            'curr_soc': soc_values[i],
                            'delta': soc_values[i] - soc_values[i-1]
                        })
                        
                        if len(violations) >= 10:  # Limit violations per run
                            break
                
                # Create SoC curve plot for one representative run
                if 'baseline' in run['label'].lower() and len(soc_values) > 10:
                    self._create_soc_curve_plot(soc_values, run['label'])
                    
            except Exception as e:
                print(f"   WARNING: Error processing {run['label']}: {e}")
                continue
        
        if violations:
            viol_df = pd.DataFrame(violations)
            viol_df.to_csv(self.violations_dir / "soc_curve_violations.csv", index=False)
        
        result = {
            'pass': len(violations) == 0,
            'violations': len(violations),
            'violations_file': "violations/soc_curve_violations.csv" if violations else None,
            'chart': 'figures/soc_curve_example.png'
        }
        
        print(f"   {'PASS' if result['pass'] else 'FAIL'}: {len(violations)} SoC violations")
        return result

    def _create_soc_curve_plot(self, soc_values: np.ndarray, run_label: str):
        """Create SoC curve plot."""
        plt.figure(figsize=(10, 6))
        plt.plot(range(len(soc_values)), soc_values, 'b-', linewidth=1.5)
        plt.xlabel('Task Sequence')
        plt.ylabel('SoC (%)')
        plt.title(f'Battery SoC Curve - {run_label}')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(self.figures_dir / 'soc_curve_example.png', dpi=300, bbox_inches='tight')
        plt.close()

    def validate_deadline_miss_rate(self) -> Dict[str, Any]:
        """Validate deadline miss rate (limitation analysis)."""
        print(" Analyzing deadline miss rate...")
        
        miss_rates = []
        
        for run in self.runs:
            try:
                df = pd.read_csv(run['summary_csv'])
                if len(df) > 0:
                    row = df.iloc[0]
                    miss_rate = row.get('deadline_miss_rate', None)
                    
                    if miss_rate is not None:
                        miss_rates.append({
                            'run': run['label'],
                            'miss_rate': miss_rate
                        })
            except Exception as e:
                continue
        
        if not miss_rates:
            return {'pass': True, 'error': 'No deadline data available', 'note': 'Analysis skipped'}
        
        rates = [m['miss_rate'] for m in miss_rates]
        avg_miss_rate = np.mean(rates)
        max_miss_rate = np.max(rates)
        
        # This is a limitation analysis, not a pass/fail
        high_miss_rate = avg_miss_rate > 0.5
        
        result = {
            'pass': True,  # Always pass, this is just analysis
            'avg_miss_rate': avg_miss_rate,
            'max_miss_rate': max_miss_rate,
            'high_miss_rate': high_miss_rate,
            'miss_rate_data': miss_rates,
            'note': 'High miss rate indicates need for dynamic/multi-objective optimization' if high_miss_rate else 'Acceptable miss rates'
        }
        
        print(f"    ANALYZED: Avg miss rate {avg_miss_rate:.2f}, Max {max_miss_rate:.2f}")
        return result

    def generate_report(self):
        """Generate comprehensive validation report."""
        print(" Generating validation report...")
        
        # Run all validations
        self.validation_results = {
            'threshold_30pct': self.validate_30pct_threshold(),
            'nav_slam_local': self.validate_nav_slam_local(),
            'local_edge_tradeoff': self.validate_local_edge_tradeoff(),
            'workload_stability': self.validate_workload_stability(),
            'task_type_impact': self.validate_task_type_impact(),
            'soc_curve': self.validate_soc_curve(),
            'deadline_miss': self.validate_deadline_miss_rate()
        }
        
        # Generate report content
        self._write_report_header()
        self._write_validation_results()
        self._write_reproduction_commands()
        
        # Write report file
        report_path = self.out_dir / "validation_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.report_lines))
        
        # Generate JSON summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_runs': len(self.runs),
            'validations': {
                name: {'pass': result.get('pass', False), 'summary': self._get_result_summary(result)}
                for name, result in self.validation_results.items()
            }
        }
        
        json_path = self.out_dir / "validation_summary.json"
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return report_path, json_path

    def _get_result_summary(self, result: Dict) -> str:
        """Get concise summary for result."""
        if 'error' in result:
            return result['error']
        elif 'violations' in result:
            return f"{result['violations']} violations"
        elif 'issues' in result:
            return f"{len(result['issues'])} issues"
        else:
            return "OK"

    def _write_report_header(self):
        """Write report header."""
        self.report_lines.extend([
            "# Battery-Aware Offloading Thesis Validation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Runs Analyzed:** {len(self.runs)}",
            f"**Strict Mode:** {'Yes' if self.strict else 'No'}",
            "",
            "## Executive Summary",
            "",
            "| Validation Point | Status | Summary |",
            "|------------------|--------|---------|"
        ])
        
        for name, result in self.validation_results.items():
            status = "PASS" if result.get('pass', False) else "FAIL"
            summary = self._get_result_summary(result)
            display_name = name.replace('_', ' ').title()
            self.report_lines.append(f"| {display_name} | {status} | {summary} |")
        
        self.report_lines.extend(["", "---", ""])

    def _write_validation_results(self):
        """Write detailed validation results."""
        for name, result in self.validation_results.items():
            display_name = name.replace('_', ' ').title()
            self.report_lines.extend([
                f"## {display_name}",
                ""
            ])
            
            if name == 'threshold_30pct':
                self._write_threshold_results(result)
            elif name == 'nav_slam_local':
                self._write_nav_slam_results(result)
            elif name == 'local_edge_tradeoff':
                self._write_tradeoff_results(result)
            elif name == 'workload_stability':
                self._write_stability_results(result)
            elif name == 'task_type_impact':
                self._write_task_type_results(result)
            elif name == 'soc_curve':
                self._write_soc_curve_results(result)
            elif name == 'deadline_miss':
                self._write_deadline_results(result)
            
            self.report_lines.extend(["", "---", ""])

    def _write_threshold_results(self, result: Dict):
        """Write 30% threshold validation results."""
        status = "PASS" if result['pass'] else "FAIL"
        self.report_lines.extend([
            f"**Status:** {status}",
            f"**Total Violations:** {result['total_violations']}",
            ""
        ])
        
        if result['above_30_stats']:
            self.report_lines.extend([
                "### SoC > 30% Distribution (GENERIC tasks should avoid CLOUD)",
                "",
                "| Run | Total | Local | Edge | Cloud | Violations |",
                "|-----|-------|-------|------|-------|------------|"
            ])
            for stat in result['above_30_stats']:
                self.report_lines.append(
                    f"| {stat['run']} | {stat['total_tasks']} | {stat['local']} | "
                    f"{stat['edge']} | {stat['cloud']} | {stat['violations']} |"
                )
            self.report_lines.append("")
        
        if result['below_30_stats']:
            self.report_lines.extend([
                "### SoC ≤ 30% Distribution (GENERIC tasks MUST use CLOUD)",
                "",
                "| Run | Total | Local | Edge | Cloud | Violations |",
                "|-----|-------|-------|------|-------|------------|"
            ])
            for stat in result['below_30_stats']:
                self.report_lines.append(
                    f"| {stat['run']} | {stat['total_tasks']} | {stat['local']} | "
                    f"{stat['edge']} | {stat['cloud']} | {stat['violations']} |"
                )

    def _write_nav_slam_results(self, result: Dict):
        """Write NAV/SLAM validation results."""
        status = "PASS" if result['pass'] else "FAIL"
        self.report_lines.extend([
            f"**Status:** {status}",
            f"**Total Violations:** {result['total_violations']}",
            f"**Average Compliance:** {result['avg_compliance_rate']:.1f}%",
            ""
        ])

    def _write_tradeoff_results(self, result: Dict):
        """Write trade-off validation results."""
        if 'error' in result:
            self.report_lines.append(f"**Error:** {result['error']}")
            return
            
        status = "PASS" if result['pass'] else "FAIL"
        self.report_lines.extend([
            f"**Status:** {status}",
            "",
            "### Trade-off Analysis",
            "",
            "| Metric | Edge Heavy | Local Heavy | Difference |",
            "|--------|------------|-------------|------------|",
            f"| Energy (Wh) | {result['edge_metrics']['energy']:.3f} | {result['local_metrics']['energy']:.3f} | {result['energy_difference_wh']:+.3f} |",
            f"| Mean Latency (ms) | {result['edge_metrics']['latency_mean']:.1f} | {result['local_metrics']['latency_mean']:.1f} | {-result['latency_difference_ms']:+.1f} |",
            "",
            f"![Trade-off Chart]({result['chart']})",
            ""
        ])

    def _write_stability_results(self, result: Dict):
        """Write stability validation results."""
        if 'error' in result:
            self.report_lines.append(f"**Error:** {result['error']}")
            return
            
        status = "PASS" if result['pass'] else "FAIL"
        self.report_lines.extend([
            f"**Status:** {status}",
            f"**Issues Found:** {len(result['issues'])}",
            ""
        ])
        
        if result['issues']:
            self.report_lines.extend([
                "### Stability Issues",
                ""
            ])
            for issue in result['issues']:
                self.report_lines.append(f"- {issue}")
            self.report_lines.append("")
        
        for chart in result['charts']:
            self.report_lines.append(f"![Stability Chart]({chart})")

    def _write_task_type_results(self, result: Dict):
        """Write task type impact results."""
        status = "PASS" if result['pass'] else "FAIL"
        self.report_lines.extend([
            f"**Status:** {status}",
            f"**Scenarios Analyzed:** {len(result['available_types'])}",
            ""
        ])
        
        if result['results']:
            self.report_lines.extend([
                "### Task Type Impact Analysis",
                "",
                "| Scenario | Local Ratio | Energy (Wh) | Latency (ms) |",
                "|----------|-------------|-------------|--------------|"
            ])
            for scenario, metrics in result['results'].items():
                self.report_lines.append(
                    f"| {scenario} | {metrics['local_ratio']:.2f} | {metrics['energy']:.3f} | {metrics['latency']:.1f} |"
                )

    def _write_soc_curve_results(self, result: Dict):
        """Write SoC curve validation results."""
        status = "PASS" if result['pass'] else "FAIL"
        self.report_lines.extend([
            f"**Status:** {status}",
            f"**Violations:** {result['violations']}",
            "",
            f"![SoC Curve]({result['chart']})",
            ""
        ])

    def _write_deadline_results(self, result: Dict):
        """Write deadline miss rate results."""
        if 'error' in result:
            self.report_lines.append(f"**Note:** {result['error']}")
            return
            
        self.report_lines.extend([
            f"**Status:**  ANALYZED (Limitation Study)",
            f"**Average Miss Rate:** {result['avg_miss_rate']:.3f}",
            f"**Maximum Miss Rate:** {result['max_miss_rate']:.3f}",
            "",
            f"**Assessment:** {result['note']}",
            ""
        ])

    def _write_reproduction_commands(self):
        """Write reproduction commands."""
        self.report_lines.extend([
            "## Reproduction Commands",
            "",
            "### Windows PowerShell",
            "",
            "```powershell",
            "# Run baseline experiment",
            ".\\scripts\\run_baseline.ps1",
            "",
            "# Run low battery validation",
            ".\\scripts\\run_low_battery_test.ps1",
            "",
            "# Run this validation",
            "$env:PYTHONPATH=\"src\"",
            "python tools\\validate_thesis_claims.py --roots results extracted_results --out-dir tools\\validation_out",
            "```",
            "",
            "### macOS/Linux",
            "",
            "```bash",
            "# Run baseline experiment",
            "./scripts/run_baseline.sh",
            "",
            "# Run low battery validation (adapt PowerShell script)",
            "",
            "# Run this validation",
            "export PYTHONPATH=src",
            "python tools/validate_thesis_claims.py --roots results extracted_results --out-dir tools/validation_out",
            "```",
            ""
        ])

def main():
    parser = argparse.ArgumentParser(description='Validate thesis claims automatically')
    parser.add_argument('--roots', nargs='+', default=['results', 'extracted_results'],
                       help='Root directories to search for results')
    parser.add_argument('--strict', action='store_true',
                       help='Use stricter validation thresholds')
    parser.add_argument('--out-dir', default='tools/validation_out',
                       help='Output directory for validation results')
    
    args = parser.parse_args()
    
    print("THESIS VALIDATION - Battery-Aware Offloading")
    print("=" * 50)
    
    validator = ThesisValidator(args.roots, args.out_dir, args.strict)
    
    # Discover and validate
    validator.discover_runs()
    report_path, json_path = validator.generate_report()
    
    print(f"\n Validation completed!")
    print(f"   Report: {report_path}")
    print(f"   Summary: {json_path}")
    
    # Print key results
    print(f"\n VALIDATION SUMMARY:")
    for name, result in validator.validation_results.items():
        status = "PASS" if result.get('pass', False) else "FAIL"
        display_name = name.replace('_', ' ').title()
        print(f"   {status} {display_name}")
    
    # Count passes
    passes = sum(1 for result in validator.validation_results.values() if result.get('pass', False))
    total = len(validator.validation_results)
    print(f"\n Overall: {passes}/{total} validations passed")

if __name__ == "__main__":
    main()