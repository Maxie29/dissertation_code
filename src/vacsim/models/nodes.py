import time
from typing import List, Optional


class BaseComputeNode:
    """Base class for compute nodes (robot, edge, cloud)"""
    
    def __init__(self, name: str, cpu_cycles_per_sec: float, base_power_W: float, max_power_W: float):
        """
        Initialize a compute node.
        
        Args:
            name: Node identifier
            cpu_cycles_per_sec: Processing capacity in cycles per second
            base_power_W: Baseline power consumption in Watts when idle
            max_power_W: Maximum power consumption in Watts at full utilization
        """
        self.name = name
        self.cpu_cycles_per_sec = cpu_cycles_per_sec
        self.base_power_W = base_power_W
        self.max_power_W = max_power_W
        # Calculate power slope for linear model
        self.power_slope = max_power_W - base_power_W
    
    def exec_time_for(self, cycles: float) -> float:
        """
        Calculate execution time for given CPU cycles.
        
        Args:
            cycles: Number of CPU cycles required
            
        Returns:
            Execution time in seconds
        """
        if cycles <= 0:
            return 0
        return cycles / self.cpu_cycles_per_sec
    
    def energy_for(self, cycles: float) -> float:
        """
        Calculate energy consumption for executing given CPU cycles.
        Uses linear power model: P = base_power + alpha*utilization
        where alpha = (max_power - base_power)
        
        Args:
            cycles: Number of CPU cycles required
            
        Returns:
            Energy consumption in Joules
        """
        if cycles <= 0:
            return 0
        
        # Calculate execution time
        exec_time = self.exec_time_for(cycles)
        
        # For this simple model, we assume 100% utilization during execution
        # So power = base_power + power_slope
        power = self.base_power_W + self.power_slope
        
        # Energy = Power * Time
        return power * exec_time


class RobotNode(BaseComputeNode):
    """Compute node representing robot onboard computing"""
    
    def __init__(self, name: str, cpu_cycles_per_sec: float, base_power_W: float, max_power_W: float):
        super().__init__(name, cpu_cycles_per_sec, base_power_W, max_power_W)


class EdgeNode(BaseComputeNode):
    """Compute node representing edge server"""
    
    def __init__(self, name: str, cpu_cycles_per_sec: float, base_power_W: float, max_power_W: float):
        super().__init__(name, cpu_cycles_per_sec, base_power_W, max_power_W)


class CloudNode(BaseComputeNode):
    """Compute node representing cloud server"""
    
    def __init__(self, name: str, cpu_cycles_per_sec: float, base_power_W: float, max_power_W: float):
        super().__init__(name, cpu_cycles_per_sec, base_power_W, max_power_W)


class NodeQueue:
    """Simple FIFO queue for compute nodes"""
    
    def __init__(self, node: BaseComputeNode):
        """
        Initialize a queue for a specific compute node.
        
        Args:
            node: The compute node this queue is associated with
        """
        self.node = node
        self.queue = []
        
    def enqueue(self, task_id: str, cycles: float) -> float:
        """
        Add a task to the queue.
        
        Args:
            task_id: Identifier for the task
            cycles: CPU cycles required by the task
            
        Returns:
            Estimated time when task will complete (absolute time)
        """
        current_time = time.time()
        
        # Calculate estimated start time (when the task will start executing)
        if not self.queue:
            start_time = current_time
        else:
            # Start time is the completion time of the last task in the queue
            start_time = self.queue[-1]["completion_time"]
        
        # Calculate execution time
        exec_time = self.node.exec_time_for(cycles)
        
        # Calculate completion time
        completion_time = start_time + exec_time
        
        # Add task to queue
        self.queue.append({
            "task_id": task_id,
            "cycles": cycles,
            "enqueue_time": current_time,
            "start_time": start_time,
            "execution_time": exec_time,
            "completion_time": completion_time
        })
        
        return completion_time
    
    def dequeue(self) -> Optional[dict]:
        """
        Remove and return the next task from the queue.
        
        Returns:
            Task information or None if queue is empty
        """
        if not self.queue:
            return None
        return self.queue.pop(0)
    
    def estimate_queue_delay(self) -> float:
        """
        Estimate the current queuing delay for a new task.
        
        Returns:
            Estimated delay in seconds before a new task would start
        """
        if not self.queue:
            return 0
        
        current_time = time.time()
        last_completion_time = self.queue[-1]["completion_time"]
        
        # Delay is the time from now until the last task completes
        delay = max(0, last_completion_time - current_time)
        return delay
