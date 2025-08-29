"""
Task model and generator for battery offloading simulation.

This module provides the core Task dataclass and TaskGenerator for creating
tasks with proper distributions according to the simulation requirements.

Hard Rules Enforced:
- NAV and SLAM tasks: can_offload=False (always local execution)
- GENERIC tasks: can_offload=True, with configurable edge_affinity
- Task dispatch decisions based on SoC at creation time only
"""

import random
from dataclasses import dataclass, field
from typing import Iterator, Optional, List
from enum import Enum

from .enums import TaskType


@dataclass
class Task:
    """
    Represents a computational task in the battery offloading simulation.
    
    This class encapsulates all properties needed for task scheduling decisions
    including computational requirements, deadlines, and offloading preferences.
    
    Examples:
    >>> task = Task(
    ...     id=1,
    ...     type=TaskType.NAV,
    ...     size_bytes=1024,
    ...     compute_demand=5000.0,
    ...     created_at=10.5,
    ...     deadline_ms=100
    ... )
    >>> task.can_offload  # NAV tasks cannot be offloaded
    False
    >>> task.edge_affinity  # NAV tasks don't have edge affinity
    False
    """
    
    # Required fields (no defaults)
    id: int | str
    type: TaskType
    size_bytes: int = field(metadata={"description": "Task data size in bytes"})
    compute_demand: float = field(metadata={"description": "Required operations count"})
    created_at: float = field(metadata={"description": "Creation time in simulation clock"})
    
    # Optional fields (with defaults)
    deadline_ms: Optional[int] = field(
        default=None, 
        metadata={"description": "Relative deadline from creation time in ms"}
    )
    priority: int = field(
        default=0, 
        metadata={"description": "Priority level (lower number = higher priority)"}
    )
    
    # Auto-computed fields based on task type
    can_offload: bool = field(init=False)
    edge_affinity: bool = field(init=False)
    
    def __post_init__(self) -> None:
        """
        Set can_offload and edge_affinity based on task type and hard rules.
        
        Hard Rules:
        - NAV and SLAM tasks: can_offload=False, edge_affinity=False
        - GENERIC tasks: can_offload=True, edge_affinity set by generator
        """
        if TaskType.is_special(self.type):
            # NAV and SLAM must execute locally
            self.can_offload = False
            self.edge_affinity = False
        else:
            # GENERIC tasks can be offloaded
            self.can_offload = True
            # edge_affinity will be set by TaskGenerator for GENERIC tasks
            if not hasattr(self, '_edge_affinity_set'):
                self.edge_affinity = False
    
    def set_edge_affinity(self, affinity: bool) -> None:
        """
        Set edge affinity for GENERIC tasks (used by TaskGenerator).
        
        Args:
            affinity: Whether this task prefers edge execution
            
        Raises:
            ValueError: If called on special tasks (NAV/SLAM)
            
        Examples:
        >>> task = Task(id=1, type=TaskType.GENERIC, size_bytes=1024, 
        ...              compute_demand=1000.0, created_at=0.0)
        >>> task.set_edge_affinity(True)
        >>> task.edge_affinity
        True
        """
        if TaskType.is_special(self.type):
            raise ValueError(f"Cannot set edge_affinity for special task type: {self.type}")
        
        self.edge_affinity = affinity
        self._edge_affinity_set = True
    
    @property
    def absolute_deadline(self) -> Optional[float]:
        """
        Calculate absolute deadline in simulation time.
        
        Returns:
            Absolute deadline time, or None if no deadline set
            
        Examples:
        >>> task = Task(id=1, type=TaskType.GENERIC, size_bytes=1024,
        ...              compute_demand=1000.0, deadline_ms=500, created_at=10.0)
        >>> task.absolute_deadline
        10.5
        """
        if self.deadline_ms is None:
            return None
        return self.created_at + (self.deadline_ms / 1000.0)
    
    def is_expired(self, current_time: float) -> bool:
        """
        Check if task has expired based on current simulation time.
        
        Args:
            current_time: Current simulation time in seconds
            
        Returns:
            True if task has expired, False otherwise
            
        Examples:
        >>> task = Task(id=1, type=TaskType.GENERIC, size_bytes=1024,
        ...              compute_demand=1000.0, deadline_ms=500, created_at=10.0)
        >>> task.is_expired(10.3)  # Before deadline
        False
        >>> task.is_expired(10.6)  # After deadline
        True
        """
        if self.deadline_ms is None:
            return False
        return current_time > self.absolute_deadline


class TaskGenerator:
    """
    Generates tasks according to specified distributions and ratios.
    
    This generator creates tasks following the hard rules while maintaining
    statistical distributions for arrival patterns and task characteristics.
    
    Examples:
    >>> generator = TaskGenerator(
    ...     arrival_rate=2.0,
    ...     nav_ratio=0.2,
    ...     slam_ratio=0.1, 
    ...     edge_affinity_ratio=0.6,
    ...     seed=42
    ... )
    >>> tasks = list(generator.make_stream(5))
    >>> len(tasks)
    5
    >>> all(isinstance(t, Task) for t in tasks)
    True
    """
    
    def __init__(
        self,
        arrival_rate: float = 2.0,
        nav_ratio: float = 0.2,
        slam_ratio: float = 0.1,
        edge_affinity_ratio: float = 0.5,
        avg_size_bytes: int = 1024 * 1024,  # 1MB
        avg_compute_demand: float = 5_000_000.0,  # 5M operations
        avg_deadline_ms: Optional[int] = 1000,  # 1 second
        seed: Optional[int] = None
    ):
        """
        Initialize task generator with specified parameters.
        
        Args:
            arrival_rate: Tasks per second (for Poisson arrival process)
            nav_ratio: Proportion of NAV tasks (0.0 to 1.0)
            slam_ratio: Proportion of SLAM tasks (0.0 to 1.0)
            edge_affinity_ratio: Proportion of GENERIC tasks with edge affinity
            avg_size_bytes: Average task size in bytes
            avg_compute_demand: Average computational operations required
            avg_deadline_ms: Average relative deadline in milliseconds
            seed: Random seed for reproducibility
            
        Raises:
            ValueError: If task ratios are invalid
        """
        if nav_ratio + slam_ratio > 1.0:
            raise ValueError(f"nav_ratio ({nav_ratio}) + slam_ratio ({slam_ratio}) cannot exceed 1.0")
        
        if not (0.0 <= edge_affinity_ratio <= 1.0):
            raise ValueError(f"edge_affinity_ratio must be between 0.0 and 1.0, got {edge_affinity_ratio}")
        
        self.arrival_rate = arrival_rate
        self.nav_ratio = nav_ratio
        self.slam_ratio = slam_ratio
        self.generic_ratio = 1.0 - nav_ratio - slam_ratio
        self.edge_affinity_ratio = edge_affinity_ratio
        self.avg_size_bytes = avg_size_bytes
        self.avg_compute_demand = avg_compute_demand
        self.avg_deadline_ms = avg_deadline_ms
        
        self._rng = random.Random(seed)
        self._task_counter = 0
    
    def _next_task_type(self) -> TaskType:
        """
        Select next task type based on configured ratios.
        
        Returns:
            TaskType selected according to probability distribution
        """
        r = self._rng.random()
        
        if r < self.nav_ratio:
            return TaskType.NAV
        elif r < self.nav_ratio + self.slam_ratio:
            return TaskType.SLAM
        else:
            return TaskType.GENERIC
    
    def _generate_task_properties(self) -> tuple[int, float, Optional[int]]:
        """
        Generate random task properties using exponential distributions.
        
        Returns:
            Tuple of (size_bytes, compute_demand, deadline_ms)
        """
        # Use exponential distribution around averages for realistic variation
        size_bytes = max(1, int(self._rng.expovariate(1.0 / self.avg_size_bytes)))
        compute_demand = max(1.0, self._rng.expovariate(1.0 / self.avg_compute_demand))
        
        deadline_ms = None
        if self.avg_deadline_ms is not None:
            deadline_ms = max(10, int(self._rng.expovariate(1.0 / self.avg_deadline_ms)))
        
        return size_bytes, compute_demand, deadline_ms
    
    def _next_inter_arrival_time(self) -> float:
        """
        Generate next inter-arrival time for Poisson process.
        
        Returns:
            Time until next task arrival in seconds
        """
        return self._rng.expovariate(self.arrival_rate)
    
    def generate_task(self, current_time: float) -> Task:
        """
        Generate a single task at the specified time.
        
        Args:
            current_time: Current simulation time when task is created
            
        Returns:
            New Task instance with appropriate properties
            
        Examples:
        >>> generator = TaskGenerator(seed=42)
        >>> task = generator.generate_task(10.5)
        >>> task.created_at
        10.5
        >>> isinstance(task.id, int)
        True
        """
        self._task_counter += 1
        task_type = self._next_task_type()
        size_bytes, compute_demand, deadline_ms = self._generate_task_properties()
        
        task = Task(
            id=self._task_counter,
            type=task_type,
            size_bytes=size_bytes,
            compute_demand=compute_demand,
            deadline_ms=deadline_ms,
            priority=0,  # Default priority, can be customized later
            created_at=current_time
        )
        
        # Set edge affinity for GENERIC tasks
        if task.type == TaskType.GENERIC:
            has_edge_affinity = self._rng.random() < self.edge_affinity_ratio
            task.set_edge_affinity(has_edge_affinity)
        
        return task
    
    def make_stream(self, num_tasks: int, start_time: float = 0.0) -> Iterator[Task]:
        """
        Generate a stream of tasks with Poisson arrival times.
        
        Args:
            num_tasks: Number of tasks to generate
            start_time: Starting simulation time
            
        Yields:
            Task instances with appropriate arrival timing
            
        Examples:
        >>> generator = TaskGenerator(seed=42)
        >>> tasks = list(generator.make_stream(3))
        >>> len(tasks)
        3
        >>> all(t.created_at >= 0 for t in tasks)
        True
        """
        current_time = start_time
        
        for _ in range(num_tasks):
            # Generate inter-arrival time and advance clock
            inter_arrival = self._next_inter_arrival_time()
            current_time += inter_arrival
            
            # Generate and yield task
            task = self.generate_task(current_time)
            yield task
    
    def get_statistics(self, tasks: List[Task]) -> dict:
        """
        Calculate statistics for a list of generated tasks.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Dictionary with task distribution statistics
            
        Examples:
        >>> generator = TaskGenerator(nav_ratio=0.2, slam_ratio=0.1, seed=42)
        >>> tasks = list(generator.make_stream(100))
        >>> stats = generator.get_statistics(tasks)
        >>> 'nav_ratio' in stats
        True
        >>> 0.0 <= stats['nav_ratio'] <= 1.0
        True
        """
        if not tasks:
            return {}
        
        nav_count = sum(1 for t in tasks if t.type == TaskType.NAV)
        slam_count = sum(1 for t in tasks if t.type == TaskType.SLAM)
        generic_count = sum(1 for t in tasks if t.type == TaskType.GENERIC)
        
        edge_affinity_count = sum(1 for t in tasks 
                                if t.type == TaskType.GENERIC and t.edge_affinity)
        
        total_tasks = len(tasks)
        
        return {
            'total_tasks': total_tasks,
            'nav_count': nav_count,
            'slam_count': slam_count, 
            'generic_count': generic_count,
            'nav_ratio': nav_count / total_tasks,
            'slam_ratio': slam_count / total_tasks,
            'generic_ratio': generic_count / total_tasks,
            'edge_affinity_count': edge_affinity_count,
            'edge_affinity_ratio': edge_affinity_count / max(1, generic_count),  # Avoid division by zero
            'avg_size_bytes': sum(t.size_bytes for t in tasks) / total_tasks,
            'avg_compute_demand': sum(t.compute_demand for t in tasks) / total_tasks,
        }