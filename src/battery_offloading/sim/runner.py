"""
Simulation runner module.

This module provides the main simulation orchestration, integrating task generation,
policy-based dispatch, resource simulation, and metrics collection into a complete
simulation framework.
"""

import simpy
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..task import TaskGenerator
from ..battery import Battery
from ..config import Config
from .dispatcher import Dispatcher
from .metrics import Metrics
from .resources import create_stations_from_config
from .network import create_networks_from_config


class Runner:
    """
    Main simulation runner that orchestrates the complete simulation.
    
    The Runner integrates all simulation components:
    - Task generation with configurable arrival patterns
    - Policy-based dispatch decisions
    - Resource simulation with queueing
    - Energy consumption tracking
    - Comprehensive metrics collection
    """
    
    def __init__(
        self,
        config: Config,
        task_generator: TaskGenerator,
        initial_soc: float = 80.0,
        battery_capacity_wh: float = 100.0,
        results_dir: str = "results"
    ):
        """
        Initialize simulation runner.
        
        Args:
            config: Simulation configuration
            task_generator: Task generator for creating task stream
            initial_soc: Initial battery state of charge (0-100%)
            battery_capacity_wh: Battery capacity in watt-hours
            results_dir: Directory for saving results
        """
        self.config = config
        self.task_generator = task_generator
        self.initial_soc = initial_soc
        self.battery_capacity_wh = battery_capacity_wh
        self.results_dir = Path(results_dir)
        
        # Initialize SimPy environment
        self.env = simpy.Environment()
        
        # Initialize battery
        self.battery = Battery(
            capacity_wh=battery_capacity_wh,
            initial_soc=initial_soc
        )
        
        # Create resources from configuration
        self.stations = create_stations_from_config(self.env, config)
        self.networks = create_networks_from_config(config)
        
        # Create dispatcher
        from ..enums import Site
        self.dispatcher = Dispatcher(
            env=self.env,
            battery=self.battery,
            local_station=self.stations[Site.LOCAL],
            edge_station=self.stations[Site.EDGE],
            cloud_station=self.stations[Site.CLOUD],
            edge_network=self.networks["edge"],
            cloud_network=self.networks["cloud"],
            config=config
        )
        
        # Initialize metrics collector
        self.metrics = Metrics()
        
        # Simulation state
        self.is_running = False
        self.execution_records = []
    
    def run(self, num_tasks: int, save_results: bool = True, run_timestamp: str = None) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Run simulation for specified number of tasks.
        
        This method orchestrates the complete simulation:
        1. Generate task stream using TaskGenerator
        2. For each task, dispatch using policy-based decisions
        3. Simulate execution with resource contention
        4. Track energy consumption and update battery
        5. Collect comprehensive metrics
        6. Save results to CSV files (optional)
        
        Args:
            num_tasks: Number of tasks to process
            save_results: Whether to save results to CSV files
            run_timestamp: Optional timestamp string for results directory
            
        Returns:
            Tuple of (execution_records, summary_statistics)
            
        Examples:
        >>> config = Config.from_yaml('configs/baseline.yaml')
        >>> task_gen = TaskGenerator.from_config(config.task_generation)
        >>> runner = Runner(config, task_gen, initial_soc=80.0)
        >>> 
        >>> records, summary = runner.run(num_tasks=100)
        >>> print(f"Processed {len(records)} tasks")
        >>> print(f"Final SoC: {summary['final_soc']:.1f}%")
        """
        if self.is_running:
            raise RuntimeError("Simulation is already running")
        
        print(f"Starting simulation with {num_tasks} tasks...")
        print(f"Initial battery SoC: {self.battery.get_soc():.1f}%")
        print(f"Battery capacity: {self.battery.capacity_wh:.1f}Wh")
        print()
        
        self.is_running = True
        self.execution_records.clear()
        self.metrics.reset()
        
        try:
            # Start simulation process
            self.env.process(self._simulation_process(num_tasks))
            
            # Run simulation
            self.env.run()
            
            # Collect final metrics
            summary = self.metrics.get_summary_statistics()
            
            print(f"Simulation completed!")
            print(f"Tasks processed: {len(self.execution_records)}")
            print(f"Final battery SoC: {self.battery.get_soc():.1f}%")
            print(f"Total energy consumed: {summary['total_energy_wh']:.2f}Wh")
            print()
            
            # Save results if requested
            if save_results:
                per_task_path, summary_path = self.metrics.save_results(
                    self.results_dir, run_timestamp
                )
                print(f"Results saved:")
                print(f"  Per-task: {per_task_path}")
                print(f"  Summary: {summary_path}")
                print()
            
            return self.execution_records.copy(), summary
            
        finally:
            self.is_running = False
    
    def _simulation_process(self, num_tasks: int):
        """
        Main simulation process (SimPy generator).
        
        Args:
            num_tasks: Number of tasks to process
        """
        # Generate tasks
        print("Generating task stream...")
        tasks = []
        for i in range(num_tasks):
            task = self.task_generator.generate_task(self.env.now)
            tasks.append(task)
        
        print(f"Generated {len(tasks)} tasks")
        
        # Process tasks
        task_count = 0
        for task in tasks:
            # Check if battery is completely depleted
            if self.battery.get_soc() <= 0.1:  # 0.1% threshold to avoid floating point issues
                print(f"Battery depleted at task {task_count + 1}, stopping simulation")
                break
            
            # Dispatch task
            current_soc = self.battery.get_soc()
            
            # Use a coroutine wrapper for dispatch
            record = yield from self._dispatch_task_process(task, current_soc)
            
            # Record results
            self.execution_records.append(record)
            self.metrics.add_record(record)
            
            task_count += 1
            
            # Progress reporting
            if task_count % 50 == 0 or task_count == num_tasks:
                print(f"Processed {task_count}/{num_tasks} tasks, SoC: {self.battery.get_soc():.1f}%")
        
        print(f"Simulation process completed with {task_count} tasks processed")
    
    def _dispatch_task_process(self, task, current_soc):
        """
        SimPy process wrapper for task dispatch.
        
        Args:
            task: Task to dispatch
            current_soc: Current battery SoC
            
        Yields:
            Execution record
        """
        # This is a wrapper to handle the fact that dispatch() might use SimPy processes internally
        record = self.dispatcher.dispatch(task, current_soc)
        
        # If dispatch returned a generator, we need to run it
        if hasattr(record, '__next__'):
            record = yield from record
        
        return record
    
    def run_with_arrival_process(
        self,
        simulation_time_s: float,
        save_results: bool = True,
        run_timestamp: str = None
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Run simulation with Poisson arrival process for specified time.
        
        Args:
            simulation_time_s: Total simulation time in seconds
            save_results: Whether to save results to CSV files
            run_timestamp: Optional timestamp string for results directory
            
        Returns:
            Tuple of (execution_records, summary_statistics)
        """
        if self.is_running:
            raise RuntimeError("Simulation is already running")
        
        print(f"Starting time-based simulation for {simulation_time_s}s...")
        print(f"Task arrival rate: {self.task_generator.arrival_rate} tasks/sec")
        print(f"Initial battery SoC: {self.battery.get_soc():.1f}%")
        print()
        
        self.is_running = True
        self.execution_records.clear()
        self.metrics.reset()
        
        try:
            # Start both arrival and processing processes
            self.env.process(self._arrival_process(simulation_time_s))
            
            # Run simulation
            self.env.run(until=simulation_time_s)
            
            # Collect final metrics
            summary = self.metrics.get_summary_statistics()
            
            print(f"Time-based simulation completed!")
            print(f"Tasks processed: {len(self.execution_records)}")
            print(f"Final battery SoC: {self.battery.get_soc():.1f}%")
            print(f"Total energy consumed: {summary['total_energy_wh']:.2f}Wh")
            print()
            
            # Save results if requested
            if save_results:
                per_task_path, summary_path = self.metrics.save_results(
                    self.results_dir, run_timestamp
                )
                print(f"Results saved:")
                print(f"  Per-task: {per_task_path}")
                print(f"  Summary: {summary_path}")
                print()
            
            return self.execution_records.copy(), summary
            
        finally:
            self.is_running = False
    
    def _arrival_process(self, max_time: float):
        """
        Poisson arrival process (SimPy generator).
        
        Args:
            max_time: Maximum simulation time
        """
        task_count = 0
        
        while self.env.now < max_time:
            # Check battery level
            if self.battery.get_soc() <= 0.1:
                print(f"Battery depleted at time {self.env.now:.1f}s, stopping arrivals")
                break
            
            # Generate next task
            task = self.task_generator.generate_task(self.env.now)
            task_count += 1
            
            # Start processing task
            self.env.process(self._process_single_task(task, task_count))
            
            # Wait for next arrival
            inter_arrival_time = self.task_generator.generate_inter_arrival_time()
            yield self.env.timeout(inter_arrival_time)
        
        print(f"Arrival process completed, generated {task_count} tasks")
    
    def _process_single_task(self, task, task_count):
        """
        Process a single task (SimPy generator).
        
        Args:
            task: Task to process
            task_count: Task counter for reporting
        """
        current_soc = self.battery.get_soc()
        
        # Dispatch task
        record = yield from self._dispatch_task_process(task, current_soc)
        
        # Record results
        self.execution_records.append(record)
        self.metrics.add_record(record)
        
        # Progress reporting
        if task_count % 25 == 0:
            print(f"Processed task {task_count} at time {self.env.now:.1f}s, SoC: {self.battery.get_soc():.1f}%")
    
    def get_current_statistics(self) -> Dict[str, Any]:
        """
        Get current simulation statistics without stopping.
        
        Returns:
            Current statistics dictionary
        """
        return self.metrics.get_summary_statistics()
    
    def print_status(self):
        """Print current simulation status."""
        stats = self.get_current_statistics()
        dispatcher_stats = self.dispatcher.get_statistics()
        
        print("=== Current Simulation Status ===")
        print(f"Simulation time: {self.env.now:.1f}s")
        print(f"Battery SoC: {self.battery.get_soc():.1f}%")
        print(f"Tasks processed: {stats['total_tasks']}")
        print(f"Site distribution: Local={dispatcher_stats['local_count']}, Edge={dispatcher_stats['edge_count']}, Cloud={dispatcher_stats['cloud_count']}")
        print(f"Energy consumed: {stats['total_energy_wh']:.2f}Wh")
        print()
    
    def reset(self):
        """Reset simulation to initial state."""
        if self.is_running:
            raise RuntimeError("Cannot reset while simulation is running")
        
        # Reset environment
        self.env = simpy.Environment()
        
        # Reset battery
        self.battery.reset()
        self.battery.set_soc(self.initial_soc)
        
        # Recreate resources
        self.stations = create_stations_from_config(self.env, self.config)
        self.networks = create_networks_from_config(self.config)
        
        # Recreate dispatcher
        from ..enums import Site
        self.dispatcher = Dispatcher(
            env=self.env,
            battery=self.battery,
            local_station=self.stations[Site.LOCAL],
            edge_station=self.stations[Site.EDGE], 
            cloud_station=self.stations[Site.CLOUD],
            edge_network=self.networks["edge"],
            cloud_network=self.networks["cloud"],
            config=self.config
        )
        
        # Reset metrics
        self.metrics.reset()
        self.execution_records.clear()
        
        print("Simulation reset to initial state")


# Convenience function for quick simulation runs
def run_simulation_from_config(
    config_path: str,
    num_tasks: int,
    initial_soc: float = 80.0,
    battery_capacity_wh: float = 100.0,
    results_dir: str = "results",
    seed: int = 42
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run a complete simulation from configuration file.
    
    Args:
        config_path: Path to YAML configuration file
        num_tasks: Number of tasks to simulate
        initial_soc: Initial battery SoC (0-100%)
        battery_capacity_wh: Battery capacity in Wh
        results_dir: Directory for saving results
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (execution_records, summary_statistics)
    """
    # Load configuration
    config = Config.from_yaml(config_path)
    
    # Create task generator
    task_gen = TaskGenerator.from_config(config.task_generation, seed=seed)
    
    # Create and run simulation
    runner = Runner(
        config=config,
        task_generator=task_gen,
        initial_soc=initial_soc,
        battery_capacity_wh=battery_capacity_wh,
        results_dir=results_dir
    )
    
    return runner.run(num_tasks=num_tasks)


__all__ = ['Runner', 'run_simulation_from_config']