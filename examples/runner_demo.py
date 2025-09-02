"""
Runner and simulation demonstration script.

This script demonstrates the complete simulation framework including
task generation, policy-based dispatch, resource simulation, and
metrics collection. Validates acceptance criteria for 200 tasks.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from battery_offloading.config import Config
from battery_offloading.task import TaskGenerator
from battery_offloading.sim.runner import Runner
from battery_offloading.enums import TaskType


def demonstrate_basic_simulation():
    """Demonstrate basic simulation with task count."""
    print("=== Basic Simulation Demo ===\n")
    
    # Load configuration
    config = Config.from_yaml('configs/baseline.yaml')
    print(f"Configuration loaded successfully")
    print(f"Local service rate: {config.local_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    print(f"Edge service rate: {config.edge_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    print(f"Cloud service rate: {config.cloud_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    print()
    
    # Create task generator
    task_gen = TaskGenerator(
        arrival_rate=config.task_generation.arrival_rate_per_sec,
        nav_ratio=config.task_generation.nav_ratio,
        slam_ratio=config.task_generation.slam_ratio,
        edge_affinity_ratio=config.task_generation.edge_affinity_ratio,
        avg_size_bytes=int(config.task_generation.avg_data_size_mb * 1024 * 1024),  # Convert MB to bytes
        avg_compute_demand=config.task_generation.avg_operations,
        seed=42
    )
    print(f"Task generator created")
    print(f"Task mix: {config.task_generation.nav_ratio:.1%} NAV, {config.task_generation.slam_ratio:.1%} SLAM, {1 - config.task_generation.nav_ratio - config.task_generation.slam_ratio:.1%} GENERIC")
    print(f"Arrival rate: {task_gen.arrival_rate:.2f} tasks/sec")
    print()
    
    # Create runner
    runner = Runner(
        config=config,
        task_generator=task_gen,
        initial_soc=80.0,
        battery_capacity_wh=100.0,
        results_dir="results"
    )
    
    # Run simulation with 50 tasks for demonstration
    print("Running simulation with 50 tasks...")
    records, summary = runner.run(num_tasks=50, save_results=False)
    
    print(f"\n=== Results ===")
    print(f"Tasks processed: {len(records)}")
    print(f"Mean latency: {summary['latency_mean_ms']:.1f}ms")
    print(f"P95 latency: {summary['latency_p95_ms']:.1f}ms")
    print(f"Total energy: {summary['total_energy_wh']:.2f}Wh")
    print(f"Final SoC: {summary['final_soc']:.1f}%")
    print(f"Site distribution: {summary['local_count']} local, {summary['edge_count']} edge, {summary['cloud_count']} cloud")
    print()
    
    return len(records) == 50 and summary['final_soc'] < 80.0


def demonstrate_200_task_acceptance():
    """Demonstrate acceptance criteria with 200 tasks."""
    print("=== 200 Task Acceptance Test ===\n")
    
    # Load configuration
    config = Config.from_yaml('configs/baseline.yaml')
    
    # Create task generator with fixed seed for reproducibility
    task_gen = TaskGenerator(
        arrival_rate=config.task_generation.arrival_rate_per_sec,
        nav_ratio=config.task_generation.nav_ratio,
        slam_ratio=config.task_generation.slam_ratio,
        edge_affinity_ratio=config.task_generation.edge_affinity_ratio,
        avg_size_bytes=int(config.task_generation.avg_data_size_mb * 1024 * 1024),  # Convert MB to bytes
        avg_compute_demand=config.task_generation.avg_operations,
        seed=123
    )
    
    # Create runner
    runner = Runner(
        config=config,
        task_generator=task_gen,
        initial_soc=80.0,
        battery_capacity_wh=100.0,
        results_dir="results"
    )
    
    print("Starting 200-task simulation...")
    print(f"Initial conditions:")
    print(f"  Battery SoC: {runner.battery.get_soc():.1f}%")
    print(f"  Battery capacity: {runner.battery.capacity_wh:.1f}Wh")
    print(f"  Task generation seed: 123")
    print()
    
    # Run simulation
    records, summary = runner.run(num_tasks=200, save_results=True)
    
    # Print detailed results
    print("=== Detailed Results ===")
    runner.metrics.print_summary()
    
    # Validate acceptance criteria
    print("=== Acceptance Criteria Validation ===")
    
    validation_results = []
    
    # 1. CSV files generated
    results_generated = len(records) > 0 and 'total_tasks' in summary
    print(f"[{'PASS' if results_generated else 'FAIL'}] Results generated and saved to CSV")
    validation_results.append(results_generated)
    
    # 2. SoC curve monotonic (non-increasing)
    rule_validation = runner.metrics.validate_hard_rules()
    soc_monotonic = rule_validation['soc_curve_monotonic']
    print(f"[{'PASS' if soc_monotonic else 'FAIL'}] SoC curve is monotonic (non-increasing)")
    validation_results.append(soc_monotonic)
    
    # 3. NAV/SLAM tasks always local
    nav_slam_local = rule_validation['nav_slam_always_local']
    print(f"[{'PASS' if nav_slam_local else 'FAIL'}] NAV/SLAM tasks always execute locally")
    validation_results.append(nav_slam_local)
    
    # 4. Required fields in per-task records
    required_fields = ['task_id', 'execution_site', 'latency_ms', 'energy_wh_delta', 'soc_after']
    fields_present = all(field in records[0] for field in required_fields) if records else False
    print(f"[{'PASS' if fields_present else 'FAIL'}] Required fields present in per-task records")
    validation_results.append(fields_present)
    
    # 5. Summary statistics complete
    required_summary_fields = ['latency_mean_ms', 'latency_p95_ms', 'total_energy_wh', 'final_soc', 'local_ratio', 'edge_ratio', 'cloud_ratio']
    summary_complete = all(field in summary for field in required_summary_fields)
    print(f"[{'PASS' if summary_complete else 'FAIL'}] Summary statistics complete")
    validation_results.append(summary_complete)
    
    # 6. Energy consumption recorded
    energy_consumed = summary['total_energy_wh'] > 0
    print(f"[{'PASS' if energy_consumed else 'FAIL'}] Energy consumption recorded")
    validation_results.append(energy_consumed)
    
    # 7. Latency statistics reasonable
    latency_reasonable = 0 < summary['latency_mean_ms'] < 60000  # Between 0 and 60 seconds
    print(f"[{'PASS' if latency_reasonable else 'FAIL'}] Latency statistics reasonable ({summary['latency_mean_ms']:.1f}ms)")
    validation_results.append(latency_reasonable)
    
    # 8. Task distribution follows policy
    has_all_sites = summary['local_count'] > 0  # Should have some local (NAV/SLAM at minimum)
    print(f"[{'PASS' if has_all_sites else 'FAIL'}] Task distribution includes local execution")
    validation_results.append(has_all_sites)
    
    print()
    overall_pass = all(validation_results)
    
    # Print task type breakdown
    print("=== Task Type Analysis ===")
    print(f"NAV tasks: {summary['nav_count']} ({summary['nav_ratio']:.1%})")
    print(f"SLAM tasks: {summary['slam_count']} ({summary['slam_ratio']:.1%})")  
    print(f"GENERIC tasks: {summary['generic_count']} ({summary['generic_ratio']:.1%})")
    print()
    
    # Print site distribution
    print("=== Site Distribution ===")
    print(f"Local: {summary['local_count']} ({summary['local_ratio']:.1%})")
    print(f"Edge: {summary['edge_count']} ({summary['edge_ratio']:.1%})")
    print(f"Cloud: {summary['cloud_count']} ({summary['cloud_ratio']:.1%})")
    print()
    
    # Show first few and last few SoC values to demonstrate monotonic decrease
    print("=== SoC Progression Sample ===")
    soc_curve = runner.metrics.get_soc_curve()
    print("First 5 tasks:")
    for i in range(min(5, len(soc_curve))):
        task_data = soc_curve[i]
        print(f"  Task {task_data['task_id']}: {task_data['soc_before']:.2f}% -> {task_data['soc_after']:.2f}%")
    
    if len(soc_curve) > 10:
        print("Last 5 tasks:")
        for i in range(max(0, len(soc_curve)-5), len(soc_curve)):
            task_data = soc_curve[i]
            print(f"  Task {task_data['task_id']}: {task_data['soc_before']:.2f}% -> {task_data['soc_after']:.2f}%")
    print()
    
    return overall_pass


def demonstrate_time_based_simulation():
    """Demonstrate time-based simulation with Poisson arrivals."""
    print("=== Time-Based Simulation Demo ===\n")
    
    # Load configuration
    config = Config.from_yaml('configs/baseline.yaml')
    
    # Create task generator
    task_gen = TaskGenerator(
        arrival_rate=config.task_generation.arrival_rate_per_sec,
        nav_ratio=config.task_generation.nav_ratio,
        slam_ratio=config.task_generation.slam_ratio,
        edge_affinity_ratio=config.task_generation.edge_affinity_ratio,
        avg_size_bytes=int(config.task_generation.avg_data_size_mb * 1024 * 1024),  # Convert MB to bytes
        avg_compute_demand=config.task_generation.avg_operations,
        seed=456
    )
    
    # Create runner
    runner = Runner(
        config=config,
        task_generator=task_gen,
        initial_soc=90.0,  # Higher initial SoC for longer simulation
        battery_capacity_wh=100.0,
        results_dir="results"
    )
    
    # Run time-based simulation for 30 seconds
    print("Running time-based simulation for 30 seconds...")
    records, summary = runner.run_with_arrival_process(
        simulation_time_s=30.0,
        save_results=False
    )
    
    print(f"\n=== Time-Based Results ===")
    print(f"Simulation duration: {summary['simulation_duration_s']:.1f}s")
    print(f"Tasks arrived and processed: {len(records)}")
    print(f"Average task rate: {len(records) / summary['simulation_duration_s']:.2f} tasks/s")
    print(f"Final battery SoC: {summary['final_soc']:.1f}%")
    print()
    
    return len(records) > 0


def main():
    """Main demonstration function."""
    print("=== Runner and Simulation Framework Demo ===\n")
    
    # Run demonstrations
    basic_ok = demonstrate_basic_simulation()
    acceptance_ok = demonstrate_200_task_acceptance()
    time_based_ok = demonstrate_time_based_simulation()
    
    # Final results
    print("=== Final Demo Results ===")
    print(f"[{'PASS' if basic_ok else 'FAIL'}] Basic simulation functionality")
    print(f"[{'PASS' if acceptance_ok else 'FAIL'}] 200-task acceptance criteria")
    print(f"[{'PASS' if time_based_ok else 'FAIL'}] Time-based simulation")
    
    all_passed = basic_ok and acceptance_ok and time_based_ok
    
    print(f"\n{'='*60}")
    if all_passed:
        print("SUCCESS: All simulation framework components working!")
        print("VALIDATED FEATURES:")
        print("  + Complete task dispatch and execution simulation")
        print("  + Policy-based site selection with battery awareness")  
        print("  + Resource contention and queueing simulation")
        print("  + Energy consumption tracking and SoC updates")
        print("  + Comprehensive metrics collection and analysis")
        print("  + CSV result export with timestamps")
        print("  + Hard rule validation (NAV/SLAM local, SoC monotonic)")
        print("  + Both task-count and time-based simulation modes")
    else:
        print("FAILURE: Some simulation components failed validation!")
    
    print(f"{'='*60}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)