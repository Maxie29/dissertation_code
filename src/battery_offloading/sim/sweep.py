"""
Parameter sweep functionality for batch experiments.

This module provides utilities for running multiple simulation experiments
with varying parameters, enabling systematic parameter studies and
sensitivity analysis.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Iterator
from datetime import datetime
import copy

from ..config import Config
from ..task import TaskGenerator
from .runner import Runner


class SweepConfig:
    """
    Configuration for parameter sweep experiments.
    
    Handles loading and parsing of sweep configuration files that define
    multiple parameter combinations to test systematically.
    """
    
    def __init__(self, config_path: str):
        """
        Load sweep configuration from YAML file.
        
        Args:
            config_path: Path to sweep configuration file
        """
        self.config_path = Path(config_path)
        self.base_config_dict = {}
        self.sweep_parameters = []
        self.sweep_info = {}
        
        self._load_sweep_config()
    
    def _load_sweep_config(self):
        """Load and parse sweep configuration file."""
        with open(self.config_path, 'r') as f:
            sweep_data = yaml.safe_load(f)
        
        # Extract sweep metadata
        self.sweep_info = sweep_data.get('sweep', {})
        
        # Extract sweep parameters
        self.sweep_parameters = sweep_data.get('sweep_parameters', {})
        
        # Create base configuration (everything except sweep_parameters)
        self.base_config_dict = {k: v for k, v in sweep_data.items() 
                                if k not in ['sweep', 'sweep_parameters']}
    
    def generate_configs(self) -> Iterator[tuple[Config, str]]:
        """
        Generate all parameter combinations from sweep configuration.
        
        Yields:
            Tuple of (Config object, parameter label) for each combination
        """
        if not self.sweep_parameters:
            # No sweep parameters, just return base config
            config = Config.parse_obj(self.base_config_dict)
            yield config, "baseline"
            return
        
        # Handle different sweep parameter structures
        for param_section, param_list in self.sweep_parameters.items():
            if not isinstance(param_list, list):
                continue
                
            for param_set in param_list:
                # Create a copy of base config
                config_dict = copy.deepcopy(self.base_config_dict)
                
                # Get label for this parameter set
                label = param_set.pop('label', f"{param_section}_{len(param_list)}")
                
                # Update the specific section with new parameters
                if param_section in config_dict:
                    config_dict[param_section].update(param_set)
                else:
                    config_dict[param_section] = param_set
                
                # Create Config object
                try:
                    config = Config.parse_obj(config_dict)
                    yield config, label
                except Exception as e:
                    print(f"Warning: Failed to create config for {label}: {e}")
                    continue
    
    def get_sweep_info(self) -> Dict[str, Any]:
        """Get sweep metadata information."""
        return self.sweep_info


class SweepRunner:
    """
    Runs parameter sweep experiments with multiple configurations.
    
    Orchestrates running multiple simulation experiments with different
    parameter combinations and collects comprehensive results.
    """
    
    def __init__(self, sweep_config: SweepConfig):
        """
        Initialize sweep runner.
        
        Args:
            sweep_config: Sweep configuration object
        """
        self.sweep_config = sweep_config
        self.sweep_results = []
    
    def run_sweep(
        self,
        num_tasks: int = 200,
        initial_soc: float = 80.0,
        battery_capacity_wh: float = 100.0,
        results_dir: str = "results",
        seed_base: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Run complete parameter sweep.
        
        Args:
            num_tasks: Number of tasks per simulation
            initial_soc: Initial battery SoC
            battery_capacity_wh: Battery capacity in Wh
            results_dir: Base results directory
            seed_base: Base random seed (incremented for each run)
            
        Returns:
            List of sweep results with parameters and metrics
        """
        print(f"Starting parameter sweep: {self.sweep_config.get_sweep_info().get('name', 'Unnamed')}")
        print(f"Description: {self.sweep_config.get_sweep_info().get('description', 'No description')}")
        
        self.sweep_results.clear()
        run_count = 0
        
        # Generate timestamp for this sweep
        sweep_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sweep_dir = Path(results_dir) / f"sweep_{sweep_timestamp}"
        sweep_dir.mkdir(parents=True, exist_ok=True)
        
        for config, label in self.sweep_config.generate_configs():
            run_count += 1
            run_seed = seed_base + run_count
            
            print(f"\n[{run_count}] Running configuration: {label}")
            print(f"    Seed: {run_seed}")
            
            try:
                # Create task generator for this configuration
                task_gen = TaskGenerator(
                    arrival_rate=config.task_generation.arrival_rate_per_sec,
                    nav_ratio=config.task_generation.nav_ratio,
                    slam_ratio=config.task_generation.slam_ratio,
                    edge_affinity_ratio=config.task_generation.edge_affinity_ratio,
                    avg_size_bytes=int(config.task_generation.avg_data_size_mb * 1024 * 1024),
                    avg_compute_demand=config.task_generation.avg_operations,
                    seed=run_seed
                )
                
                # Create run-specific results directory
                run_dir = sweep_dir / f"run_{run_count:02d}_{label}"
                
                # Create and run simulation
                runner = Runner(
                    config=config,
                    task_generator=task_gen,
                    initial_soc=initial_soc,
                    battery_capacity_wh=battery_capacity_wh,
                    results_dir=str(run_dir)
                )
                
                records, summary = runner.run(num_tasks=num_tasks, save_results=True)
                
                # Store sweep results
                sweep_result = {
                    'run_id': run_count,
                    'parameter_label': label,
                    'seed': run_seed,
                    'config_summary': self._extract_config_summary(config),
                    'metrics': summary,
                    'validation': runner.metrics.validate_hard_rules(),
                    'results_dir': str(run_dir)
                }
                
                self.sweep_results.append(sweep_result)
                
                print(f"    COMPLETED: {summary['total_tasks']} tasks, "
                      f"Final SoC: {summary['final_soc']:.1f}%, "
                      f"Mean latency: {summary['latency_mean_ms']:.1f}ms")
                
            except Exception as e:
                print(f"    FAILED: {e}")
                # Still record the failure
                sweep_result = {
                    'run_id': run_count,
                    'parameter_label': label,
                    'seed': run_seed,
                    'config_summary': self._extract_config_summary(config),
                    'error': str(e),
                    'results_dir': None
                }
                self.sweep_results.append(sweep_result)
        
        # Save sweep summary
        self._save_sweep_summary(sweep_dir)
        
        print(f"\nParameter sweep completed successfully!")
        print(f"  Total runs: {run_count}")
        print(f"  Successful runs: {sum(1 for r in self.sweep_results if 'error' not in r)}")
        print(f"  Results saved to: {sweep_dir}")
        
        return self.sweep_results
    
    def _extract_config_summary(self, config: Config) -> Dict[str, Any]:
        """Extract key configuration parameters for summary."""
        return {
            'arrival_rate': config.task_generation.arrival_rate_per_sec,
            'nav_ratio': config.task_generation.nav_ratio,
            'slam_ratio': config.task_generation.slam_ratio,
            'edge_affinity_ratio': config.task_generation.edge_affinity_ratio,
            'edge_rtt_ms': config.edge_network.latency_ms,
            'cloud_rtt_ms': config.cloud_network.latency_ms,
            'local_ops_per_sec': config.local_service.processing_rate_ops_per_sec,
            'edge_ops_per_sec': config.edge_service.processing_rate_ops_per_sec,
            'cloud_ops_per_sec': config.cloud_service.processing_rate_ops_per_sec
        }
    
    def _save_sweep_summary(self, sweep_dir: Path):
        """Save comprehensive sweep summary."""
        import pandas as pd
        
        # Create summary DataFrame
        summary_rows = []
        for result in self.sweep_results:
            if 'error' in result:
                # Failed run
                row = {
                    'run_id': result['run_id'],
                    'parameter_label': result['parameter_label'],
                    'seed': result['seed'],
                    'status': 'FAILED',
                    'error': result['error']
                }
                row.update(result['config_summary'])
            else:
                # Successful run
                row = {
                    'run_id': result['run_id'],
                    'parameter_label': result['parameter_label'],
                    'seed': result['seed'],
                    'status': 'SUCCESS',
                    'error': ''
                }
                row.update(result['config_summary'])
                row.update({
                    'total_tasks': result['metrics']['total_tasks'],
                    'latency_mean_ms': result['metrics']['latency_mean_ms'],
                    'latency_p95_ms': result['metrics']['latency_p95_ms'],
                    'total_energy_wh': result['metrics']['total_energy_wh'],
                    'final_soc': result['metrics']['final_soc'],
                    'local_ratio': result['metrics']['local_ratio'],
                    'edge_ratio': result['metrics']['edge_ratio'],
                    'cloud_ratio': result['metrics']['cloud_ratio'],
                    'deadline_miss_rate': result['metrics']['deadline_miss_rate'],
                    'rules_valid': result['validation']['all_rules_valid']
                })
            
            summary_rows.append(row)
        
        # Save to CSV
        summary_df = pd.DataFrame(summary_rows)
        summary_path = sweep_dir / "sweep_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        
        # Also save detailed results as JSON for programmatic access
        import json
        detailed_path = sweep_dir / "sweep_detailed.json"
        with open(detailed_path, 'w') as f:
            json.dump(self.sweep_results, f, indent=2, default=str)
        
        print(f"  Summary saved: {summary_path}")
        print(f"  Detailed results: {detailed_path}")


def is_sweep_config(config_path: str) -> bool:
    """
    Check if a configuration file is a sweep configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if file contains sweep parameters
    """
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return 'sweep_parameters' in config_data or 'sweep' in config_data
    except Exception:
        return False


__all__ = ['SweepConfig', 'SweepRunner', 'is_sweep_config']