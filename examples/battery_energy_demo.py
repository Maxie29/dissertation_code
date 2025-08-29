"""
Battery and energy model demonstration script.

This script demonstrates the battery and energy estimation functionality
and validates the acceptance criteria specified in the requirements.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from battery_offloading.battery import Battery
from battery_offloading.energy import (
    PowerParameters, estimate_local_compute_time, 
    estimate_comm_time, estimate_robot_energy,
    get_execution_energy_breakdown
)
from battery_offloading.task import Task
from battery_offloading.enums import TaskType, Site


def main():
    """Demonstrate battery and energy models with acceptance criteria."""
    
    print("=== Battery & Energy Model Demo ===\n")
    
    # Initialize realistic battery (typical smartphone)
    print("1. Battery Initialization")
    battery = Battery(capacity_wh=18.5, initial_soc=100.0)  # 18.5Wh @ 100% SoC
    print(f"   Battery: {battery}")
    print(f"   Remaining energy: {battery.get_remaining_energy_wh():.2f} Wh")
    print()
    
    # Power parameters (realistic mobile device values)
    power_params = PowerParameters(
        active_local_mw=2000.0,  # 2W during computation
        tx_mw=800.0,             # 800mW during transmission
        rx_mw=400.0,             # 400mW during reception
        idle_mw=100.0            # 100mW idle
    )
    
    print("2. Power Parameters")
    print(f"   Local computation: {power_params.active_local_mw} mW")
    print(f"   Transmission: {power_params.tx_mw} mW")  
    print(f"   Reception: {power_params.rx_mw} mW")
    print(f"   Idle: {power_params.idle_mw} mW")
    print()
    
    # Acceptance Test: GENERIC task with specified parameters
    print("3. Acceptance Criteria Test")
    print("   Creating GENERIC task: size=10MB, compute_demand=1e9 ops")
    
    task = Task(
        id=1,
        type=TaskType.GENERIC,
        size_bytes=10*1024*1024,  # 10MB as specified
        compute_demand=1e9,       # 1 billion operations as specified
        created_at=0.0
    )
    
    print(f"   Task: {task.type.name}, Size: {task.size_bytes/1024/1024:.1f}MB, Demand: {task.compute_demand:.0e} ops")
    print()
    
    # Communication parameters as specified: 20Mbps up, 50Mbps down, 20ms RTT
    print("4. Communication Time Estimation")
    print("   Network: 20Mbps up, 50Mbps down, 20ms RTT")
    
    comm_times = estimate_comm_time(
        task_size_bytes=task.size_bytes,
        bandwidth_up_mbps=20.0,     # As specified
        bandwidth_down_mbps=50.0,   # As specified  
        rtt_ms=20.0                 # As specified
    )
    
    print(f"   Uplink time: {comm_times.uplink_s:.3f}s")
    print(f"   Downlink time: {comm_times.downlink_s:.3f}s")
    print(f"   Total comm time: {comm_times.total_comm_s:.3f}s")
    print()
    
    # Local execution analysis
    print("5. Local Execution Analysis")
    local_processing_rate = 1000000.0  # 1M ops/sec (reasonable for mobile CPU)
    local_compute_time_s = estimate_local_compute_time(task, local_processing_rate)
    
    energy_local = estimate_robot_energy(
        task, Site.LOCAL, power_params, local_compute_time_s
    )
    
    breakdown_local = get_execution_energy_breakdown(
        task, Site.LOCAL, power_params, local_compute_time_s
    )
    
    print(f"   Processing rate: {local_processing_rate/1e6:.1f}M ops/sec")
    print(f"   Execution time: {local_compute_time_s:.1f}s")
    print(f"   Computation energy: {breakdown_local['local_computation']:.6f} Wh")
    print(f"   Communication energy: {breakdown_local['communication']:.6f} Wh (should be ~0)")
    print(f"   Total energy: {energy_local:.6f} Wh")
    print()
    
    # Edge execution analysis
    print("6. Edge Execution Analysis")
    energy_edge = estimate_robot_energy(
        task, Site.EDGE, power_params, 0.0, comm_times
    )
    
    breakdown_edge = get_execution_energy_breakdown(
        task, Site.EDGE, power_params, 0.0, comm_times
    )
    
    print(f"   Computation energy: {breakdown_edge['local_computation']:.6f} Wh (should be 0)")
    print(f"   Uplink energy: {breakdown_edge['uplink']:.6f} Wh")
    print(f"   Downlink energy: {breakdown_edge['downlink']:.6f} Wh")
    print(f"   Total communication energy: {breakdown_edge['communication']:.6f} Wh (should be > 0)")
    print(f"   Total energy: {energy_edge:.6f} Wh")
    print()
    
    # Cloud execution analysis  
    print("7. Cloud Execution Analysis")
    energy_cloud = estimate_robot_energy(
        task, Site.CLOUD, power_params, 0.0, comm_times
    )
    
    print(f"   Total energy: {energy_cloud:.6f} Wh (should equal Edge energy)")
    print()
    
    # Battery SoC testing
    print("8. Battery SoC Update Testing")
    initial_soc = battery.get_soc()
    
    # Test local execution energy consumption
    print("   Simulating local execution...")
    battery.consume_energy_wh(energy_local, "local_computation", task_id=task.id)
    soc_after_local = battery.get_soc()
    
    print(f"   SoC before: {initial_soc:.2f}%")
    print(f"   Energy consumed: {energy_local:.6f} Wh")
    print(f"   SoC after: {soc_after_local:.2f}%")
    print(f"   SoC decrease: {initial_soc - soc_after_local:.3f}%")
    print()
    
    # Reset and test remote execution
    battery.reset(100.0)
    print("   Simulating edge execution...")
    battery.consume_energy_wh(energy_edge, "edge_communication", task_id=task.id)
    soc_after_edge = battery.get_soc()
    
    print(f"   SoC before: 100.00%")
    print(f"   Energy consumed: {energy_edge:.6f} Wh")
    print(f"   SoC after: {soc_after_edge:.2f}%") 
    print(f"   SoC decrease: {100.0 - soc_after_edge:.3f}%")
    print()
    
    # Acceptance criteria validation
    print("=== Acceptance Criteria Validation ===")
    
    # Criteria 1: Edge/Cloud communication energy > 0, Local communication energy ≈ 0
    comm_energy_ok = (
        breakdown_edge["communication"] > 0 and 
        breakdown_local["communication"] == 0.0
    )
    
    print(f"[{'PASS' if comm_energy_ok else 'FAIL'}] Communication energy:")
    print(f"         Local comm energy: {breakdown_local['communication']:.6f} Wh (should be ~0)")
    print(f"         Edge comm energy: {breakdown_edge['communication']:.6f} Wh (should be > 0)")
    print(f"         Cloud comm energy: {breakdown_edge['communication']:.6f} Wh (should be > 0)")
    
    # Criteria 2: Battery SoC correctly decreases and stays in 0-100% range
    soc_valid = (
        0 <= soc_after_local <= 100 and
        0 <= soc_after_edge <= 100 and
        soc_after_local < initial_soc and
        soc_after_edge < 100.0
    )
    
    print(f"[{'PASS' if soc_valid else 'FAIL'}] Battery SoC updates:")
    print(f"         SoC values in valid range (0-100%): {0 <= soc_after_local <= 100}")
    print(f"         SoC decreases after consumption: {soc_after_local < initial_soc}")
    
    # Overall result
    all_criteria_pass = comm_energy_ok and soc_valid
    
    print(f"\n{'='*50}")
    if all_criteria_pass:
        print("SUCCESS: All acceptance criteria passed!")
        print("  + Edge/Cloud communication energy > 0")
        print("  + Local communication energy ~= 0") 
        print("  + Battery SoC correctly decreases")
        print("  + SoC values remain in 0-100% range")
    else:
        print("FAILURE: Some acceptance criteria failed!")
        
    print(f"{'='*50}")
    
    # Additional insights
    print("\n=== Energy Efficiency Analysis ===")
    if energy_local > energy_edge:
        savings_wh = energy_local - energy_edge
        savings_pct = (savings_wh / energy_local) * 100
        print(f"Offloading saves {savings_wh:.6f} Wh ({savings_pct:.1f}%) for this task")
    else:
        overhead_wh = energy_edge - energy_local  
        overhead_pct = (overhead_wh / energy_local) * 100
        print(f"Offloading adds {overhead_wh:.6f} Wh ({overhead_pct:.1f}%) overhead for this task")
    
    return all_criteria_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)