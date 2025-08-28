from typing import Any
from vacsim.policies.base import OffloadTarget, RobotState, NodeState, NetworkLink
from vacsim.sim.generator import Task

def _exec_time(cycles: float, cpu_cycles_per_sec: float) -> float:
    """Calculate execution time given cycles and CPU speed"""
    if cpu_cycles_per_sec <= 0:
        return float("inf")
    return cycles / cpu_cycles_per_sec

def _tx_time(bits: float, bps: float) -> float:
    """Calculate transmission time given bits and bandwidth"""
    if bps <= 0:
        return float("inf")
    return bits / bps

def estimate_total_latency(target: OffloadTarget, task: Task, 
                          robot: RobotState, edge: NodeState, 
                          cloud: NodeState, network: NetworkLink) -> float:
    """
    Calculate total end-to-end latency for a given target.
    
    Formula:
    latency = uplink_time + rtt/2 + execution_time + queue_time + rtt/2 + downlink_time
    
    Args:
        target: Offload target (LOCAL, EDGE, or CLOUD)
        task: Task to be executed
        robot: Robot state for local execution
        edge: Edge node state
        cloud: Cloud node state
        network: Network link parameters
        
    Returns:
        Estimated total latency in seconds
    """
    # Task parameters
    size_bits = task.size_bits  # Already in bits
    result_size_bits = size_bits / 10  # Assuming result is 1/10 of input size
    cpu_cycles = task.cpu_cycles
    
    if target == OffloadTarget.LOCAL:
        # Local execution: only queue time + execution time
        local_cpu_cycles_per_sec = 1e9  # 1 GHz processor
        exec_time = cpu_cycles / local_cpu_cycles_per_sec
        queue_time = robot.estimated_wait_time
        return queue_time + exec_time
    
    elif target == OffloadTarget.EDGE:
        # Edge execution with network latency
        edge_cpu_cycles_per_sec = 3e9  # 3 GHz edge processor
        
        # Network times
        uplink_time = size_bits / network.uplink_rate_bps
        downlink_time = result_size_bits / network.downlink_rate_bps
        
        # RTT is twice the one-way latency
        rtt_s = network.latency_s * 2
        
        # Processing times
        exec_time = cpu_cycles / edge_cpu_cycles_per_sec
        queue_time = edge.estimated_wait_time
        
        # Total latency
        return uplink_time + (rtt_s/2) + queue_time + exec_time + (rtt_s/2) + downlink_time
    
    elif target == OffloadTarget.CLOUD:
        # Cloud execution with worse network conditions
        cloud_cpu_cycles_per_sec = 5e9  # 5 GHz cloud processor
        cloud_factor = 1.5  # Cloud network is slower than edge
        
        # Network times
        uplink_time = size_bits / (network.uplink_rate_bps / cloud_factor)
        downlink_time = result_size_bits / (network.downlink_rate_bps / cloud_factor)
        
        # Longer RTT for cloud
        rtt_s = network.latency_s * 2 * cloud_factor
        
        # Processing times
        exec_time = cpu_cycles / cloud_cpu_cycles_per_sec
        queue_time = cloud.estimated_wait_time
        
        # Total latency
        return uplink_time + (rtt_s/2) + queue_time + exec_time + (rtt_s/2) + downlink_time
    
    else:
        raise ValueError(f"Unknown target: {target}")
