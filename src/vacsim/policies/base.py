from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass

from vacsim.sim.generator import Task
from typing import Dict, Any


class OffloadTarget(Enum):
    """Possible targets for offloading decisions"""
    LOCAL = auto()  # Execute on robot
    EDGE = auto()   # Offload to edge
    CLOUD = auto()  # Offload to cloud


@dataclass
class Decision:
    """Decision outcome from offloading policy"""
    target: OffloadTarget
    reason: str  # Explanation for the decision


class NodeState:
    """State of a compute node (robot, edge, or cloud)"""
    def __init__(self, name: str, queue_length: int = 0, estimated_wait_time: float = 0.0):
        self.name = name
        self.queue_length = queue_length
        self.estimated_wait_time = estimated_wait_time  # in seconds


class RobotState(NodeState):
    """State of robot, including battery information"""
    def __init__(self, name: str, battery_soc: float, 
                 queue_length: int = 0, estimated_wait_time: float = 0.0):
        """
        Initialize robot state
        
        Args:
            name: Robot identifier
            battery_soc: Battery state of charge (0.0 to 1.0)
            queue_length: Current task queue length
            estimated_wait_time: Estimated wait time for new tasks
        """
        super().__init__(name, queue_length, estimated_wait_time)
        self.battery_soc = battery_soc  # State of charge (0.0 to 1.0)


class NetworkLink:
    """Network connection between compute nodes"""
    def __init__(self, uplink_rate_bps: float, downlink_rate_bps: float, 
                 latency_s: float):
        """
        Initialize network link
        
        Args:
            uplink_rate_bps: Uplink data rate in bits per second
            downlink_rate_bps: Downlink data rate in bits per second
            latency_s: One-way network latency in seconds
        """
        self.uplink_rate_bps = uplink_rate_bps
        self.downlink_rate_bps = downlink_rate_bps
        self.latency_s = latency_s
    
    def calculate_transfer_time(self, size_bits: int, is_uplink: bool = True) -> float:
        """
        Calculate time to transfer data over this link
        
        Args:
            size_bits: Size of data in bits
            is_uplink: Whether transfer is in uplink direction (True) or downlink (False)
            
        Returns:
            Transfer time in seconds including network latency
        """
        if size_bits <= 0:
            return self.latency_s
            
        rate = self.uplink_rate_bps if is_uplink else self.downlink_rate_bps
        return size_bits / rate + self.latency_s


class OffloadingPolicy(ABC):
    """Abstract base class for offloading decision policies"""
    
    @abstractmethod
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        """
        Make an offloading decision for the given task and system state
        
        Args:
            task: Task to be offloaded or executed locally
            robot: Current robot state
            edge: Current edge node state
            cloud: Current cloud node state
            network: Current network state
            
        Returns:
            Decision containing target and reason
        """
        pass
    
    @abstractmethod
    def explain(self) -> str:
        """
        Return a human-readable explanation of this policy
        
        Returns:
            Description of policy behavior
        """
        pass
