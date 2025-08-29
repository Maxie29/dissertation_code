"""
Energy consumption estimation for battery offloading simulation.

This module provides functions to estimate computation times and energy
consumption for tasks executed locally or offloaded to edge/cloud resources.
It models both computational energy (local processing) and communication
energy (data transmission for offloading).
"""

from typing import NamedTuple, Optional
from dataclasses import dataclass

from .task import Task
from .enums import Site


@dataclass
class PowerParameters:
    """
    Power consumption parameters for different activities.
    
    All power values are in milliwatts (mW) for consistency with
    typical mobile device power measurements.
    
    Examples:
    >>> params = PowerParameters(
    ...     active_local_mw=2000.0,
    ...     tx_mw=800.0,
    ...     rx_mw=400.0
    ... )
    >>> params.active_local_mw
    2000.0
    """
    active_local_mw: float  # Power consumption during local computation (mW)
    tx_mw: float           # Power consumption during transmission (mW)
    rx_mw: float           # Power consumption during reception (mW)
    idle_mw: float = 100.0 # Baseline idle power consumption (mW)


class ComputationTimes(NamedTuple):
    """
    Result of computation time estimation.
    
    Contains timing information for task execution at different
    computing tiers with their respective processing capabilities.
    
    Examples:
    >>> times = ComputationTimes(
    ...     uplink_s=0.1,
    ...     downlink_s=0.05, 
    ...     total_comm_s=0.15
    ... )
    >>> times.total_comm_s
    0.15
    """
    uplink_s: float      # Time to upload task data (seconds)
    downlink_s: float    # Time to download results (seconds) 
    total_comm_s: float  # Total communication time (seconds)


def estimate_local_compute_time(task: Task, local_processing_rate: float) -> float:
    """
    Estimate time required for local task execution.
    
    Args:
        task: Task to be executed
        local_processing_rate: Local processing rate in operations per second
        
    Returns:
        Estimated execution time in seconds
        
    Raises:
        ValueError: If processing rate is not positive
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType
    >>> task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
    >>> estimate_local_compute_time(task, 2000000.0)
    0.5
    """
    if local_processing_rate <= 0:
        raise ValueError(f"Processing rate must be positive, got {local_processing_rate}")
    
    return task.compute_demand / local_processing_rate


def estimate_remote_compute_time(task: Task, remote_processing_rate: float) -> float:
    """
    Estimate time required for remote task execution (edge/cloud).
    
    Args:
        task: Task to be executed
        remote_processing_rate: Remote processing rate in operations per second
        
    Returns:
        Estimated execution time in seconds
        
    Raises:
        ValueError: If processing rate is not positive
        
    Examples:
    >>> from battery_offloading.task import Task  
    >>> from battery_offloading.enums import TaskType
    >>> task = Task(1, TaskType.GENERIC, 1024, 5000000.0, 0.0)
    >>> estimate_remote_compute_time(task, 10000000.0)
    0.5
    """
    if remote_processing_rate <= 0:
        raise ValueError(f"Processing rate must be positive, got {remote_processing_rate}")
    
    return task.compute_demand / remote_processing_rate


def estimate_comm_time(
    task_size_bytes: int,
    bandwidth_up_mbps: float,
    bandwidth_down_mbps: float,
    rtt_ms: float,
    jitter_ms: float = 0.0,
    result_size_ratio: float = 0.1
) -> ComputationTimes:
    """
    Estimate communication time for task offloading.
    
    Models the time required to upload task data and download results,
    accounting for network bandwidth limitations and round-trip time.
    
    Args:
        task_size_bytes: Size of task data to upload (bytes)
        bandwidth_up_mbps: Uplink bandwidth in Mbps
        bandwidth_down_mbps: Downlink bandwidth in Mbps
        rtt_ms: Round-trip time in milliseconds
        jitter_ms: Additional jitter delay in milliseconds
        result_size_ratio: Ratio of result size to input size (default 0.1)
        
    Returns:
        ComputationTimes with uplink, downlink, and total times
        
    Raises:
        ValueError: If any parameter is negative
        
    Examples:
    >>> times = estimate_comm_time(
    ...     task_size_bytes=10*1024*1024,  # 10MB
    ...     bandwidth_up_mbps=20.0,
    ...     bandwidth_down_mbps=50.0,
    ...     rtt_ms=20.0
    ... )
    >>> times.uplink_s > 0
    True
    >>> times.downlink_s > 0  
    True
    """
    if task_size_bytes < 0:
        raise ValueError(f"Task size cannot be negative, got {task_size_bytes}")
    if bandwidth_up_mbps <= 0:
        raise ValueError(f"Uplink bandwidth must be positive, got {bandwidth_up_mbps}")
    if bandwidth_down_mbps <= 0:
        raise ValueError(f"Downlink bandwidth must be positive, got {bandwidth_down_mbps}")
    if rtt_ms < 0:
        raise ValueError(f"RTT cannot be negative, got {rtt_ms}")
    if jitter_ms < 0:
        raise ValueError(f"Jitter cannot be negative, got {jitter_ms}")
    if not (0 <= result_size_ratio <= 1):
        raise ValueError(f"Result size ratio must be between 0-1, got {result_size_ratio}")
    
    # Convert Mbps to bytes per second
    # 1 Mbps = 1,000,000 bits/sec = 125,000 bytes/sec
    uplink_bps = bandwidth_up_mbps * 125_000
    downlink_bps = bandwidth_down_mbps * 125_000
    
    # Calculate pure transmission times
    uplink_transmission_s = task_size_bytes / uplink_bps
    
    # Result size is typically much smaller than input (e.g., classification result)
    result_size_bytes = max(1, int(task_size_bytes * result_size_ratio))
    downlink_transmission_s = result_size_bytes / downlink_bps
    
    # Add RTT and jitter delays (convert ms to seconds)
    rtt_s = rtt_ms / 1000.0
    jitter_s = jitter_ms / 1000.0
    
    # Model realistic network behavior:
    # - Uplink includes connection setup (1 RTT) + transmission + jitter
    # - Downlink includes processing acknowledgment + transmission + jitter
    uplink_total_s = uplink_transmission_s + (rtt_s / 2) + jitter_s
    downlink_total_s = downlink_transmission_s + (rtt_s / 2) + jitter_s
    
    total_comm_s = uplink_total_s + downlink_total_s
    
    return ComputationTimes(
        uplink_s=uplink_total_s,
        downlink_s=downlink_total_s,
        total_comm_s=total_comm_s
    )


def estimate_robot_energy(
    task: Task,
    execution_site: Site,
    power_params: PowerParameters,
    local_compute_time_s: float,
    comm_times: Optional[ComputationTimes] = None
) -> float:
    """
    Estimate total energy consumption from robot's perspective.
    
    Calculates energy consumed by the robot for task execution, including
    local computation energy and communication energy for offloaded tasks.
    Remote computation energy is not included as specified in requirements.
    
    Args:
        task: Task being executed
        execution_site: Where the task will be executed (LOCAL/EDGE/CLOUD)
        power_params: Power consumption parameters
        local_compute_time_s: Time for local computation (if applicable)
        comm_times: Communication timing (required for EDGE/CLOUD)
        
    Returns:
        Total energy consumption in watt-hours (Wh)
        
    Raises:
        ValueError: If comm_times missing for remote execution
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType, Site
    >>> task = Task(1, TaskType.GENERIC, 1024*1024, 1000000.0, 0.0)
    >>> params = PowerParameters(2000.0, 800.0, 400.0)
    >>> 
    >>> # Local execution
    >>> energy_local = estimate_robot_energy(task, Site.LOCAL, params, 0.5)
    >>> energy_local > 0
    True
    >>>
    >>> # Remote execution  
    >>> comm_times = ComputationTimes(0.1, 0.05, 0.15)
    >>> energy_remote = estimate_robot_energy(task, Site.EDGE, params, 0.0, comm_times)
    >>> energy_remote > 0
    True
    """
    if execution_site in [Site.EDGE, Site.CLOUD] and comm_times is None:
        raise ValueError(f"Communication times required for {execution_site} execution")
    
    total_energy_wh = 0.0
    
    if execution_site == Site.LOCAL:
        # Local execution: only computational energy on robot
        compute_energy_wh = (power_params.active_local_mw / 1000.0) * (local_compute_time_s / 3600.0)
        total_energy_wh = compute_energy_wh
        
    elif execution_site in [Site.EDGE, Site.CLOUD]:
        # Remote execution: only communication energy on robot
        # Robot does not consume energy for remote computation
        
        if comm_times is None:
            raise ValueError("Communication times required for remote execution")
        
        # Energy for uploading task data
        uplink_energy_wh = (power_params.tx_mw / 1000.0) * (comm_times.uplink_s / 3600.0)
        
        # Energy for downloading results
        downlink_energy_wh = (power_params.rx_mw / 1000.0) * (comm_times.downlink_s / 3600.0)
        
        total_energy_wh = uplink_energy_wh + downlink_energy_wh
    
    return total_energy_wh


def get_execution_energy_breakdown(
    task: Task,
    execution_site: Site,
    power_params: PowerParameters,
    local_compute_time_s: float,
    comm_times: Optional[ComputationTimes] = None
) -> dict[str, float]:
    """
    Get detailed breakdown of energy consumption by component.
    
    Args:
        task: Task being executed
        execution_site: Where the task will be executed
        power_params: Power consumption parameters
        local_compute_time_s: Time for local computation
        comm_times: Communication timing for remote execution
        
    Returns:
        Dictionary with energy breakdown in Wh
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType, Site
    >>> task = Task(1, TaskType.GENERIC, 1024*1024, 1000000.0, 0.0)
    >>> params = PowerParameters(2000.0, 800.0, 400.0)
    >>> breakdown = get_execution_energy_breakdown(task, Site.LOCAL, params, 0.5)
    >>> "local_computation" in breakdown
    True
    >>> breakdown["communication"] == 0.0
    True
    """
    breakdown = {
        "local_computation": 0.0,
        "communication": 0.0,
        "uplink": 0.0,
        "downlink": 0.0,
        "total": 0.0
    }
    
    if execution_site == Site.LOCAL:
        # Local execution energy
        compute_energy_wh = (power_params.active_local_mw / 1000.0) * (local_compute_time_s / 3600.0)
        breakdown["local_computation"] = compute_energy_wh
        breakdown["total"] = compute_energy_wh
        
    elif execution_site in [Site.EDGE, Site.CLOUD]:
        if comm_times is not None:
            # Communication energy breakdown
            uplink_energy_wh = (power_params.tx_mw / 1000.0) * (comm_times.uplink_s / 3600.0)
            downlink_energy_wh = (power_params.rx_mw / 1000.0) * (comm_times.downlink_s / 3600.0)
            
            breakdown["uplink"] = uplink_energy_wh
            breakdown["downlink"] = downlink_energy_wh
            breakdown["communication"] = uplink_energy_wh + downlink_energy_wh
            breakdown["total"] = breakdown["communication"]
    
    return breakdown


def calculate_energy_savings(
    task: Task,
    power_params: PowerParameters,
    local_compute_time_s: float,
    comm_times: ComputationTimes
) -> dict[str, float]:
    """
    Calculate energy savings from offloading vs local execution.
    
    Args:
        task: Task being analyzed
        power_params: Power consumption parameters
        local_compute_time_s: Time for local execution
        comm_times: Communication times for offloading
        
    Returns:
        Dictionary with energy comparison and savings
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType
    >>> task = Task(1, TaskType.GENERIC, 1024*1024, 10000000.0, 0.0)
    >>> params = PowerParameters(2000.0, 800.0, 400.0)
    >>> comm_times = ComputationTimes(0.1, 0.05, 0.15)
    >>> savings = calculate_energy_savings(task, params, 5.0, comm_times)
    >>> "local_energy_wh" in savings
    True
    >>> "offload_energy_wh" in savings
    True
    """
    # Calculate local execution energy
    local_energy_wh = estimate_robot_energy(
        task, Site.LOCAL, power_params, local_compute_time_s
    )
    
    # Calculate offloading energy (communication only)
    offload_energy_wh = estimate_robot_energy(
        task, Site.EDGE, power_params, 0.0, comm_times
    )
    
    # Calculate savings
    energy_savings_wh = local_energy_wh - offload_energy_wh
    savings_percentage = (energy_savings_wh / local_energy_wh * 100.0) if local_energy_wh > 0 else 0.0
    
    return {
        "local_energy_wh": local_energy_wh,
        "offload_energy_wh": offload_energy_wh,
        "energy_savings_wh": energy_savings_wh,
        "savings_percentage": savings_percentage,
        "is_beneficial": energy_savings_wh > 0
    }