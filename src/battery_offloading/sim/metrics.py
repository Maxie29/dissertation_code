"""
Metrics collection and analysis module.

This module provides comprehensive metrics collection and analysis capabilities
for simulation results, including latency statistics, energy consumption,
deadline compliance, and site distribution analysis.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class Metrics:
    """
    Collects and analyzes simulation metrics.
    
    Provides comprehensive analysis of task execution records including
    latency distributions, energy consumption, deadline compliance,
    and execution site statistics.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.records = []
        self.reset()
    
    def reset(self):
        """Reset all collected metrics."""
        self.records.clear()
    
    def add_record(self, record: Dict[str, Any]):
        """
        Add an execution record for analysis.
        
        Args:
            record: Task execution record from Dispatcher
        """
        self.records.append(record.copy())
    
    def add_records(self, records: List[Dict[str, Any]]):
        """
        Add multiple execution records.
        
        Args:
            records: List of task execution records
        """
        for record in records:
            self.add_record(record)
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive summary statistics.
        
        Returns:
            Dictionary with all key metrics including:
            - Latency statistics (mean, median, p95, p99)
            - Energy consumption totals and per-task averages
            - Site distribution (counts and ratios)
            - Deadline compliance rates
            - Battery SoC progression
        """
        if not self.records:
            return self._empty_summary()
        
        df = pd.DataFrame(self.records)
        
        # Basic counts
        total_tasks = len(df)
        
        # Latency statistics
        latencies = df['latency_ms'].values
        latency_stats = {
            'latency_mean_ms': float(np.mean(latencies)),
            'latency_median_ms': float(np.median(latencies)),
            'latency_p50_ms': float(np.percentile(latencies, 50)),
            'latency_p95_ms': float(np.percentile(latencies, 95)),
            'latency_p99_ms': float(np.percentile(latencies, 99)),
            'latency_min_ms': float(np.min(latencies)),
            'latency_max_ms': float(np.max(latencies))
        }
        
        # Energy statistics
        energies = df['energy_wh_delta'].values
        energy_stats = {
            'total_energy_wh': float(np.sum(energies)),
            'energy_per_task_mean_wh': float(np.mean(energies)),
            'energy_per_task_median_wh': float(np.median(energies)),
            'energy_min_wh': float(np.min(energies)),
            'energy_max_wh': float(np.max(energies))
        }
        
        # Site distribution
        site_counts = df['execution_site'].value_counts().to_dict()
        site_stats = {
            'local_count': site_counts.get('local', 0),
            'edge_count': site_counts.get('edge', 0),
            'cloud_count': site_counts.get('cloud', 0),
            'local_ratio': site_counts.get('local', 0) / total_tasks,
            'edge_ratio': site_counts.get('edge', 0) / total_tasks,
            'cloud_ratio': site_counts.get('cloud', 0) / total_tasks
        }
        
        # Task type distribution
        type_counts = df['task_type'].value_counts().to_dict()
        type_stats = {
            'nav_count': type_counts.get('NAV', 0),
            'slam_count': type_counts.get('SLAM', 0),
            'generic_count': type_counts.get('GENERIC', 0),
            'nav_ratio': type_counts.get('NAV', 0) / total_tasks,
            'slam_ratio': type_counts.get('SLAM', 0) / total_tasks,
            'generic_ratio': type_counts.get('GENERIC', 0) / total_tasks
        }
        
        # Deadline analysis
        has_deadlines = df['deadline_ms'] > 0
        deadline_stats = {}
        if has_deadlines.any():
            deadline_df = df[has_deadlines]
            missed = deadline_df['missed_deadline'].sum()
            deadline_stats = {
                'tasks_with_deadlines': int(has_deadlines.sum()),
                'deadlines_missed': int(missed),
                'deadline_miss_rate': float(missed / len(deadline_df)) if len(deadline_df) > 0 else 0.0
            }
        else:
            deadline_stats = {
                'tasks_with_deadlines': 0,
                'deadlines_missed': 0,
                'deadline_miss_rate': 0.0
            }
        
        # Battery SoC progression
        soc_before = df['soc_before'].values
        soc_after = df['soc_after'].values
        battery_stats = {
            'initial_soc': float(soc_before[0]) if len(soc_before) > 0 else 0.0,
            'final_soc': float(soc_after[-1]) if len(soc_after) > 0 else 0.0,
            'soc_drop': float(soc_before[0] - soc_after[-1]) if len(soc_before) > 0 and len(soc_after) > 0 else 0.0,
            'min_soc': float(np.min(soc_after)) if len(soc_after) > 0 else 0.0
        }
        
        # Communication statistics for remote tasks
        remote_df = df[df['execution_site'].isin(['edge', 'cloud'])]
        if not remote_df.empty:
            comm_stats = {
                'remote_tasks': len(remote_df),
                'avg_upload_time_ms': float(np.mean(remote_df['network_up_ms'])),
                'avg_download_time_ms': float(np.mean(remote_df['network_down_ms'])),
                'avg_queue_wait_ms': float(np.mean(remote_df['queue_wait_ms']))
            }
        else:
            comm_stats = {
                'remote_tasks': 0,
                'avg_upload_time_ms': 0.0,
                'avg_download_time_ms': 0.0,
                'avg_queue_wait_ms': 0.0
            }
        
        # Combine all statistics
        summary = {
            'total_tasks': total_tasks,
            'simulation_duration_s': float(df['finish_time'].max() - df['dispatch_time'].min()) if total_tasks > 0 else 0.0,
            **latency_stats,
            **energy_stats,
            **site_stats,
            **type_stats,
            **deadline_stats,
            **battery_stats,
            **comm_stats
        }
        
        return summary
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary statistics."""
        return {
            'total_tasks': 0,
            'simulation_duration_s': 0.0,
            'latency_mean_ms': 0.0,
            'latency_median_ms': 0.0,
            'latency_p50_ms': 0.0,
            'latency_p95_ms': 0.0,
            'latency_p99_ms': 0.0,
            'latency_min_ms': 0.0,
            'latency_max_ms': 0.0,
            'total_energy_wh': 0.0,
            'energy_per_task_mean_wh': 0.0,
            'energy_per_task_median_wh': 0.0,
            'energy_min_wh': 0.0,
            'energy_max_wh': 0.0,
            'local_count': 0,
            'edge_count': 0,
            'cloud_count': 0,
            'local_ratio': 0.0,
            'edge_ratio': 0.0,
            'cloud_ratio': 0.0,
            'nav_count': 0,
            'slam_count': 0,
            'generic_count': 0,
            'nav_ratio': 0.0,
            'slam_ratio': 0.0,
            'generic_ratio': 0.0,
            'tasks_with_deadlines': 0,
            'deadlines_missed': 0,
            'deadline_miss_rate': 0.0,
            'initial_soc': 0.0,
            'final_soc': 0.0,
            'soc_drop': 0.0,
            'min_soc': 0.0,
            'remote_tasks': 0,
            'avg_upload_time_ms': 0.0,
            'avg_download_time_ms': 0.0,
            'avg_queue_wait_ms': 0.0
        }
    
    def get_soc_curve(self) -> List[Dict[str, float]]:
        """
        Get SoC progression curve.
        
        Returns:
            List of dictionaries with task_id, dispatch_time, soc_before, soc_after
        """
        if not self.records:
            return []
        
        curve = []
        for record in self.records:
            curve.append({
                'task_id': record['task_id'],
                'dispatch_time': record['dispatch_time'],
                'soc_before': record['soc_before'],
                'soc_after': record['soc_after']
            })
        return curve
    
    def validate_hard_rules(self) -> Dict[str, bool]:
        """
        Validate that hard dispatch rules are followed.
        
        Returns:
            Dictionary with validation results
        """
        if not self.records:
            return {'all_rules_valid': True}
        
        df = pd.DataFrame(self.records)
        
        # Rule 1: NAV/SLAM tasks always execute locally
        nav_slam_df = df[df['task_type'].isin(['NAV', 'SLAM'])]
        nav_slam_local = nav_slam_df['execution_site'].eq('local').all() if not nav_slam_df.empty else True
        
        # Rule 2: SoC curve is non-increasing (monotonic)
        soc_values = df['soc_after'].values
        soc_monotonic = np.all(np.diff(soc_values) <= 1e-6) if len(soc_values) > 1 else True  # Allow small floating point errors
        
        # Rule 3: Generic tasks follow SoC-based rules (this is enforced by policy, but we can check consistency)
        generic_df = df[df['task_type'] == 'GENERIC']
        
        # For each generic task, check if site matches expected based on SoC
        generic_rule_violations = 0
        for _, row in generic_df.iterrows():
            soc = row['soc_before']
            site = row['execution_site']
            
            if soc <= 30.0:
                expected_site = 'cloud'
            else:
                # We can't check edge_affinity from the record alone, 
                # but we know it should be either 'edge' or 'local'
                expected_site = ['edge', 'local']
            
            if isinstance(expected_site, list):
                if site not in expected_site:
                    generic_rule_violations += 1
            else:
                if site != expected_site:
                    generic_rule_violations += 1
        
        generic_rules_valid = generic_rule_violations == 0
        
        return {
            'nav_slam_always_local': nav_slam_local,
            'soc_curve_monotonic': soc_monotonic,
            'generic_rules_consistent': generic_rules_valid,
            'all_rules_valid': nav_slam_local and soc_monotonic and generic_rules_valid
        }
    
    def save_results(self, results_dir: Path, run_timestamp: str = None) -> tuple[Path, Path]:
        """
        Save detailed results and summary to CSV files.
        
        Args:
            results_dir: Base results directory
            run_timestamp: Optional timestamp string, if None will generate current time
            
        Returns:
            Tuple of (per_task_csv_path, summary_csv_path)
        """
        if run_timestamp is None:
            run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create timestamped directory
        run_dir = results_dir / run_timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save per-task results
        per_task_path = run_dir / "per_task_results.csv"
        if self.records:
            df = pd.DataFrame(self.records)
            df.to_csv(per_task_path, index=False)
        else:
            # Create empty CSV with headers
            pd.DataFrame(columns=['task_id', 'task_type', 'execution_site', 'latency_ms', 
                                'energy_wh_delta', 'soc_before', 'soc_after']).to_csv(per_task_path, index=False)
        
        # Save summary statistics
        summary_path = run_dir / "summary_statistics.csv"
        summary = self.get_summary_statistics()
        summary_df = pd.DataFrame([summary])
        summary_df.to_csv(summary_path, index=False)
        
        return per_task_path, summary_path
    
    def print_summary(self):
        """Print a formatted summary of key metrics."""
        if not self.records:
            print("No records to analyze.")
            return
        
        summary = self.get_summary_statistics()
        validation = self.validate_hard_rules()
        
        print("=== Simulation Summary ===")
        print(f"Total tasks processed: {summary['total_tasks']}")
        print(f"Simulation duration: {summary['simulation_duration_s']:.1f}s")
        print()
        
        print("=== Latency Statistics ===")
        print(f"Mean latency: {summary['latency_mean_ms']:.1f}ms")
        print(f"Median (P50): {summary['latency_p50_ms']:.1f}ms")
        print(f"P95 latency: {summary['latency_p95_ms']:.1f}ms")
        print(f"P99 latency: {summary['latency_p99_ms']:.1f}ms")
        print()
        
        print("=== Energy Consumption ===")
        print(f"Total energy consumed: {summary['total_energy_wh']:.2f}Wh")
        print(f"Average per task: {summary['energy_per_task_mean_wh']:.3f}Wh")
        print()
        
        print("=== Site Distribution ===")
        print(f"Local: {summary['local_count']} ({summary['local_ratio']:.1%})")
        print(f"Edge: {summary['edge_count']} ({summary['edge_ratio']:.1%})")
        print(f"Cloud: {summary['cloud_count']} ({summary['cloud_ratio']:.1%})")
        print()
        
        print("=== Task Types ===")
        print(f"NAV: {summary['nav_count']} ({summary['nav_ratio']:.1%})")
        print(f"SLAM: {summary['slam_count']} ({summary['slam_ratio']:.1%})")
        print(f"GENERIC: {summary['generic_count']} ({summary['generic_ratio']:.1%})")
        print()
        
        print("=== Battery Status ===")
        print(f"Initial SoC: {summary['initial_soc']:.1f}%")
        print(f"Final SoC: {summary['final_soc']:.1f}%")
        print(f"SoC drop: {summary['soc_drop']:.1f}%")
        print(f"Minimum SoC: {summary['min_soc']:.1f}%")
        print()
        
        if summary['tasks_with_deadlines'] > 0:
            print("=== Deadline Compliance ===")
            print(f"Tasks with deadlines: {summary['tasks_with_deadlines']}")
            print(f"Deadlines missed: {summary['deadlines_missed']}")
            print(f"Miss rate: {summary['deadline_miss_rate']:.1%}")
            print()
        
        print("=== Rule Validation ===")
        print(f"NAV/SLAM always local: {'PASS' if validation['nav_slam_always_local'] else 'FAIL'}")
        print(f"SoC curve monotonic: {'PASS' if validation['soc_curve_monotonic'] else 'FAIL'}")
        print(f"Generic rules consistent: {'PASS' if validation['generic_rules_consistent'] else 'FAIL'}")
        print(f"All rules valid: {'PASS' if validation['all_rules_valid'] else 'FAIL'}")


__all__ = ['Metrics']