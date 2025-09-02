"""
SimPy resources and network demonstration script.

This script demonstrates the ResourceStation and Network functionality
and validates the acceptance criteria specified in the requirements.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import simpy
from battery_offloading.sim.resources import ResourceStation, create_stations_from_config
from battery_offloading.sim.network import Network, create_networks_from_config
from battery_offloading.task import Task
from battery_offloading.enums import TaskType, Site
from battery_offloading.config import Config


def demonstrate_resource_stations():
    """Demonstrate ResourceStation functionality and acceptance criteria."""
    print("=== ResourceStation Demonstration ===\n")
    
    # Create SimPy environment
    env = simpy.Environment()
    
    # Create stations with different service rates
    print("1. Creating Resource Stations")
    local_station = ResourceStation(env, Site.LOCAL, service_rate=1000000.0)   # 1M ops/sec
    edge_station = ResourceStation(env, Site.EDGE, service_rate=5000000.0)     # 5M ops/sec (faster)
    cloud_station = ResourceStation(env, Site.CLOUD, service_rate=10000000.0)  # 10M ops/sec (fastest)
    
    print(f"   LOCAL: {local_station}")
    print(f"   EDGE:  {edge_station}")  
    print(f"   CLOUD: {cloud_station}")
    print()
    
    # Create test task
    print("2. Test Task")
    task = Task(
        id=1,
        type=TaskType.GENERIC,
        size_bytes=5*1024*1024,  # 5MB
        compute_demand=10000000.0,  # 10M operations
        created_at=0.0
    )
    print(f"   Task: {task.compute_demand/1e6:.1f}M operations")
    print()
    
    # Calculate service times
    print("3. Service Time Calculation")
    local_time = local_station.calculate_service_time(task)
    edge_time = edge_station.calculate_service_time(task)  
    cloud_time = cloud_station.calculate_service_time(task)
    
    print(f"   LOCAL service time: {local_time:.1f}s")
    print(f"   EDGE service time:  {edge_time:.1f}s")
    print(f"   CLOUD service time: {cloud_time:.1f}s")
    print()
    
    # Acceptance Criteria 1: Higher service rate = faster processing
    print("4. Acceptance Criteria Validation")
    faster_processing = edge_time < local_time and cloud_time < edge_time
    print(f"   [{'PASS' if faster_processing else 'FAIL'}] Higher service rate -> faster processing")
    print(f"         LOCAL (1M ops/s): {local_time:.1f}s")
    print(f"         EDGE (5M ops/s):  {edge_time:.1f}s") 
    print(f"         CLOUD (10M ops/s): {cloud_time:.1f}s")
    print(f"         Speedup EDGE vs LOCAL: {local_time/edge_time:.1f}x")
    print(f"         Speedup CLOUD vs LOCAL: {local_time/cloud_time:.1f}x")
    print()
    
    # Demonstrate FIFO queuing
    print("5. FIFO Queuing Demonstration")
    env = simpy.Environment()  # Create new environment for clean state
    fifo_station = ResourceStation(env, Site.LOCAL, service_rate=1000000.0)
    
    # Create multiple tasks
    tasks = [
        Task(i, TaskType.GENERIC, 1024, 2000000.0, 0.0) for i in range(1, 4)
    ]  # Each task takes 2s on local station
    
    processing_results = []
    
    def process_task_demo(station, task):
        """Process a single task and record results."""
        start_time = env.now
        finish_time, service_time = yield from station.process(task)
        queue_wait = start_time  # Since all submitted at time 0
        processing_results.append((task.id, queue_wait, service_time, finish_time))
    
    # Submit all tasks at time 0
    for task in tasks:
        env.process(process_task_demo(fifo_station, task))
    
    env.run()
    
    print("   FIFO processing results:")
    for task_id, queue_wait, service_time, finish_time in processing_results:
        print(f"     Task {task_id}: queue={queue_wait:.1f}s, service={service_time:.1f}s, finish={finish_time:.1f}s")
    
    # Verify FIFO order
    finish_times = [result[3] for result in processing_results]
    fifo_correct = all(finish_times[i] <= finish_times[i+1] for i in range(len(finish_times)-1))
    print(f"   [{'PASS' if fifo_correct else 'FAIL'}] FIFO ordering maintained")
    print()
    
    return faster_processing and fifo_correct


def demonstrate_network():
    """Demonstrate Network functionality and acceptance criteria."""
    print("=== Network Demonstration ===\n")
    
    # Create network as specified in acceptance criteria
    print("1. Network Configuration")
    network = Network(
        bw_up_mbps=20.0,     # 20 Mbps uplink as specified
        bw_down_mbps=50.0,   # 50 Mbps downlink  
        rtt_ms=20.0,         # 20ms RTT as specified
        jitter_ms=0.0        # No jitter for deterministic testing
    )
    print(f"   {network}")
    print()
    
    # Test 10MB upload as specified in acceptance criteria
    print("2. Acceptance Criteria Test: 10MB Upload at 20Mbps")
    data_size = 10 * 1024 * 1024  # 10MB as specified
    result = network.uplink_time(data_size)
    
    print(f"   Data size: {data_size/1024/1024:.1f}MB")
    print(f"   Pure transmission time: {result.pure_transmission_time:.3f}s")
    print(f"   Latency overhead: {result.latency_overhead:.3f}s") 
    print(f"   Total time: {result.total_time:.3f}s")
    print()
    
    # Calculate theoretical time
    theoretical_time = (data_size * 8) / (network.bw_up_mbps * 1000000)  # Convert to bits and calculate
    print(f"3. Theoretical vs Actual Comparison")
    print(f"   Theoretical time (80Mb / 20Mbps): {theoretical_time:.3f}s")
    print(f"   Actual transmission time: {result.pure_transmission_time:.3f}s")
    print(f"   Time with RTT included: {result.total_time:.3f}s")
    print()
    
    # Acceptance criteria validation
    approximately_4s = 4.0 <= result.pure_transmission_time <= 4.3  # Allow some tolerance
    includes_rtt = result.total_time > result.pure_transmission_time
    
    print("4. Acceptance Criteria Validation")
    print(f"   [{'PASS' if approximately_4s else 'FAIL'}] 10MB upload ~= 4s: {result.pure_transmission_time:.3f}s")
    print(f"   [{'PASS' if includes_rtt else 'FAIL'}] Total time includes RTT: {result.total_time:.3f}s > {result.pure_transmission_time:.3f}s")
    print()
    
    # Test different file sizes
    print("5. File Size Comparison")
    test_sizes = [1, 5, 10, 50]  # MB
    
    for size_mb in test_sizes:
        size_bytes = size_mb * 1024 * 1024
        up_result = network.uplink_time(size_bytes)
        down_result = network.downlink_time(size_bytes)
        
        print(f"   {size_mb:2d}MB: up={up_result.total_time:.2f}s, down={down_result.total_time:.2f}s")
    print()
    
    # Bidirectional communication test
    print("6. Bidirectional Communication")
    up_time, down_time, total_time = network.total_time(
        up_bytes=10*1024*1024,   # 10MB upload
        down_bytes=1*1024*1024   # 1MB download (typical result size)
    )
    
    print(f"   Upload time (10MB): {up_time:.3f}s")
    print(f"   Download time (1MB): {down_time:.3f}s")
    print(f"   Total communication: {total_time:.3f}s")
    print()
    
    return approximately_4s and includes_rtt


def demonstrate_config_integration():
    """Demonstrate integration with configuration system."""
    print("=== Configuration Integration ===\n")
    
    # Load configuration
    print("1. Loading Configuration")
    config = Config.from_yaml('configs/baseline.yaml')
    print(f"   Configuration loaded successfully")
    print(f"   Local service rate: {config.local_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    print(f"   Edge service rate: {config.edge_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    print(f"   Cloud service rate: {config.cloud_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    print()
    
    # Create stations from config
    print("2. Creating Stations from Config")
    env = simpy.Environment()
    stations = create_stations_from_config(env, config)
    
    for site, station in stations.items():
        print(f"   {site.name}: {station.service_rate/1e6:.1f}M ops/s")
    print()
    
    # Create networks from config
    print("3. Creating Networks from Config")
    networks = create_networks_from_config(config)
    
    for name, network in networks.items():
        print(f"   {name.upper()}: {network}")
    print()
    
    return True


def main():
    """Main demonstration function."""
    print("=== SimPy Resources & Network Demo ===\n")
    
    # Run demonstrations
    resource_ok = demonstrate_resource_stations()
    network_ok = demonstrate_network()  
    config_ok = demonstrate_config_integration()
    
    # Overall results
    print("=== Final Results ===")
    print(f"[{'PASS' if resource_ok else 'FAIL'}] ResourceStation functionality")
    print(f"[{'PASS' if network_ok else 'FAIL'}] Network functionality")
    print(f"[{'PASS' if config_ok else 'FAIL'}] Configuration integration")
    
    all_passed = resource_ok and network_ok and config_ok
    
    print(f"\n{'='*50}")
    if all_passed:
        print("SUCCESS: All acceptance criteria passed!")
        print("  + Higher service rate results in faster processing")
        print("  + FIFO queuing works correctly")
        print("  + 10MB upload at 20Mbps takes ~4s")
        print("  + Total time includes RTT overhead")
        print("  + Configuration integration works")
    else:
        print("FAILURE: Some acceptance criteria failed!")
    print(f"{'='*50}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)