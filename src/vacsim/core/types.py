"""
Core data types for the VacSim simulator.

This module defines the fundamental data structures and types used throughout the
simulator, including task representations, decision records, state tracking,
and random distribution utilities.
"""

import random
import numpy as np
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, Optional, Any, List, Union, Callable


class Destination(Enum):
    """
    Possible destinations for task offloading.
    """
    LOCAL = auto()  # Execute on the vacuum robot itself
    EDGE = auto()   # Offload to edge server
    CLOUD = auto()  # Offload to cloud server


@dataclass
class Task:
    """
    Representation of a computational task in the system.
    
    Attributes:
        id: Unique task identifier
        arrival_time: Time when the task entered the system (in seconds)
        size_bits: Size of the task data (in bits)
        cpu_cycles: Required CPU cycles to complete the task
        deadline_s: Relative deadline (in seconds)
        metadata: Additional task-specific information
    """
    id: int
    arrival_time: float
    size_bits: int
    cpu_cycles: int
    deadline_s: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """
    Record of a task offloading decision.
    
    Attributes:
        task_id: ID of the task this decision applies to
        dest: Destination where the task should be executed
        reason: Reason/explanation for the decision
        meta: Additional decision metadata
    """
    task_id: int
    dest: Destination
    reason: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RobotState:
    """
    Current state of the vacuum robot.
    
    Attributes:
        time: Current simulation time (in seconds)
        soc: State of charge (between 0 and 1)
        queue_len: Number of tasks in the local execution queue
        last_decision: Last offloading decision made (if any)
    """
    time: float
    soc: float  # Between 0 and 1
    queue_len: int
    last_decision: Optional[Decision] = None
    
    def __post_init__(self):
        if not 0 <= self.soc <= 1:
            raise ValueError(f"State of charge must be between 0 and 1, got {self.soc}")


@dataclass
class NodeState:
    """
    Current state of a computation node.
    
    Attributes:
        name: Node identifier
        utilization: CPU utilization (between 0 and 1)
        queue_len: Number of tasks in the execution queue
    """
    name: str
    utilization: float  # Between 0 and 1
    queue_len: int
    
    def __post_init__(self):
        if not 0 <= self.utilization <= 1:
            raise ValueError(f"Utilization must be between 0 and 1, got {self.utilization}")


# Random distribution utilities
_rng = random.Random()
_np_rng = np.random.RandomState()


def set_seed(seed: int) -> None:
    """
    Set the random seed for all distribution functions.
    
    Args:
        seed: Integer seed value
    """
    _rng.seed(seed)
    _np_rng.seed(seed)
    np.random.seed(seed)
    random.seed(seed)


def exp(rate: float) -> float:
    """
    Generate a random value from an exponential distribution.
    
    Args:
        rate: Rate parameter (lambda)
        
    Returns:
        A random value from the exponential distribution
    """
    if rate <= 0:
        raise ValueError(f"Rate parameter must be positive, got {rate}")
    return _rng.expovariate(rate)


def lognormal(mean: float, sigma: float) -> float:
    """
    Generate a random value from a log-normal distribution.
    
    Args:
        mean: Mean of the log-normal distribution
        sigma: Standard deviation of the log-normal distribution
        
    Returns:
        A random value from the log-normal distribution
    """
    if sigma <= 0:
        raise ValueError(f"Sigma must be positive, got {sigma}")
    return _np_rng.lognormal(mean, sigma)


def normal_clipped(mean: float, std: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """
    Generate a random value from a normal distribution, clipped to specified range.
    
    Args:
        mean: Mean of the normal distribution
        std: Standard deviation of the normal distribution
        min_val: Minimum allowed value (None for no minimum)
        max_val: Maximum allowed value (None for no maximum)
        
    Returns:
        A random value from the clipped normal distribution
    """
    if std <= 0:
        raise ValueError(f"Standard deviation must be positive, got {std}")
    
    val = _np_rng.normal(mean, std)
    
    if min_val is not None:
        val = max(val, min_val)
    if max_val is not None:
        val = min(val, max_val)
        
    return val


def create_distribution(dist_config: Dict[str, Any]) -> Callable[[], float]:
    """
    Create a distribution function from configuration.
    
    Args:
        dist_config: Dictionary with 'type' and 'params' keys
        
    Returns:
        A function that generates random values according to the distribution
    """
    dist_type = dist_config.get('type', '').lower()
    params = dist_config.get('params', {})
    
    if dist_type == 'exponential':
        rate = params.get('rate', 1.0)
        return lambda: exp(rate)
    
    elif dist_type == 'lognormal':
        mean = params.get('mean', 0.0)
        sigma = params.get('sigma', 1.0)
        return lambda: lognormal(mean, sigma)
    
    elif dist_type == 'normal_clipped':
        mean = params.get('mean', 0.0)
        std = params.get('std', 1.0)
        min_val = params.get('min')
        max_val = params.get('max')
        return lambda: normal_clipped(mean, std, min_val, max_val)
    
    elif dist_type == 'constant':
        value = params.get('value', 0.0)
        return lambda: value
    
    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")
