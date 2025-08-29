"""
Resource station simulation using SimPy.

This module provides ResourceStation class that models computing resources
(LOCAL/EDGE/CLOUD) with processing capabilities and FIFO queuing using SimPy's
discrete event simulation framework.
"""

import simpy
from typing import Tuple, List, Optional
from dataclasses import dataclass, field
import time

from ..enums import Site
from ..task import Task


@dataclass
class ProcessingRecord:
    """
    Record of a task processing event at a resource station.
    
    Tracks timing information and task details for analysis
    of resource utilization and performance.
    
    Examples:
    >>> record = ProcessingRecord(
    ...     task_id=1,
    ...     start_time=10.5,
    ...     service_time=2.0,
    ...     finish_time=12.5,
    ...     queue_wait_time=0.3
    ... )
    >>> record.total_time
    2.3
    """
    task_id: int | str = field(metadata={"description": "Task identifier"})
    start_time: float = field(metadata={"description": "When processing started (simulation time)"})
    service_time: float = field(metadata={"description": "Actual processing time in seconds"})
    finish_time: float = field(metadata={"description": "When processing finished (simulation time)"})
    queue_wait_time: float = field(default=0.0, metadata={"description": "Time spent waiting in queue"})
    
    @property
    def total_time(self) -> float:
        """
        Get total time from arrival to completion.
        
        Returns:
            Total time including queue wait and service time
            
        Examples:
        >>> record = ProcessingRecord(1, 10.0, 2.0, 12.0, 0.5)
        >>> record.total_time
        2.5
        """
        return self.queue_wait_time + self.service_time


class ResourceStation:
    """
    SimPy-based resource station for processing tasks.
    
    Models a computing resource (LOCAL/EDGE/CLOUD) with specified processing
    rate and FIFO queuing. Uses SimPy's Resource for queue management and
    provides realistic processing time simulation.
    
    Examples:
    >>> import simpy
    >>> env = simpy.Environment()
    >>> station = ResourceStation(env, Site.EDGE, service_rate=5000000.0, capacity=2)
    >>> station.name
    <Site.EDGE: 'edge'>
    >>> station.service_rate
    5000000.0
    """
    
    def __init__(
        self, 
        env: simpy.Environment,
        name: Site,
        service_rate: float,
        capacity: int = 1
    ):
        """
        Initialize resource station with SimPy environment and processing parameters.
        
        Args:
            env: SimPy environment for discrete event simulation
            name: Station identifier (LOCAL/EDGE/CLOUD)
            service_rate: Processing rate in compute_demand units per second
            capacity: Number of parallel processing slots (default 1 for single server)
            
        Raises:
            ValueError: If service_rate is not positive or capacity < 1
            
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.LOCAL, 1000000.0, 1)
        >>> isinstance(station.resource, simpy.Resource)
        True
        """
        if service_rate <= 0:
            raise ValueError(f"Service rate must be positive, got {service_rate}")
        
        if capacity < 1:
            raise ValueError(f"Capacity must be at least 1, got {capacity}")
        
        self.env = env
        self.name = name
        self.service_rate = service_rate
        self.capacity = capacity
        
        # SimPy Resource for FIFO queuing
        self.resource = simpy.Resource(env, capacity=capacity)
        
        # Statistics tracking
        self._processing_history: List[ProcessingRecord] = []
        self._current_queue_length = 0
        self._total_tasks_processed = 0
        self._total_service_time = 0.0
        self._total_queue_time = 0.0
    
    def calculate_service_time(self, task: Task) -> float:
        """
        Calculate service time for a task based on compute demand and service rate.
        
        Args:
            task: Task to be processed
            
        Returns:
            Service time in seconds
            
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.LOCAL, 2000000.0)
        >>> from battery_offloading.task import Task
        >>> from battery_offloading.enums import TaskType
        >>> task = Task(1, TaskType.GENERIC, 1024, 4000000.0, 0.0)
        >>> station.calculate_service_time(task)
        2.0
        """
        return task.compute_demand / self.service_rate
    
    def process(self, task: Task) -> Tuple[float, float]:
        """
        Process a task through the resource station with FIFO queuing.
        
        This is a SimPy process that requests the resource, waits in queue
        if necessary, processes the task, and returns timing information.
        
        Args:
            task: Task to be processed
            
        Returns:
            Tuple of (finish_time, service_time) in simulation time
            
        Examples:
        >>> import simpy
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.EDGE, 1000000.0)
        >>> from battery_offloading.task import Task
        >>> from battery_offloading.enums import TaskType
        >>> task = Task(1, TaskType.GENERIC, 1024, 2000000.0, 0.0)
        >>> 
        >>> def run_simulation():
        ...     result = yield from station.process(task)
        ...     return result
        >>> 
        >>> env.process(run_simulation())  # doctest: +SKIP
        <simpy.events.Process object at 0x...>
        """
        arrival_time = self.env.now
        service_time = self.calculate_service_time(task)
        
        # Request resource (will wait if capacity is full)
        with self.resource.request() as req:
            yield req
            
            # Calculate queue wait time
            start_time = self.env.now
            queue_wait_time = start_time - arrival_time
            
            # Process the task
            yield self.env.timeout(service_time)
            
            finish_time = self.env.now
            
            # Record processing statistics
            record = ProcessingRecord(
                task_id=task.id,
                start_time=start_time,
                service_time=service_time,
                finish_time=finish_time,
                queue_wait_time=queue_wait_time
            )
            
            self._processing_history.append(record)
            self._total_tasks_processed += 1
            self._total_service_time += service_time
            self._total_queue_time += queue_wait_time
            
            return finish_time, service_time
    
    def get_queue_length(self) -> int:
        """
        Get current queue length (number of waiting requests).
        
        Returns:
            Number of tasks waiting for service
            
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.LOCAL, 1000000.0)
        >>> station.get_queue_length()
        0
        """
        return len(self.resource.queue)
    
    def get_processing_history(self) -> List[ProcessingRecord]:
        """
        Get history of all processed tasks.
        
        Returns:
            List of processing records in chronological order
            
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.LOCAL, 1000000.0)
        >>> history = station.get_processing_history()
        >>> len(history)
        0
        """
        return self._processing_history.copy()
    
    def get_utilization_stats(self) -> dict[str, float]:
        """
        Calculate resource utilization statistics.
        
        Returns:
            Dictionary with utilization metrics
            
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.LOCAL, 1000000.0)
        >>> stats = station.get_utilization_stats()
        >>> 'total_tasks' in stats
        True
        >>> stats['total_tasks']
        0
        """
        current_time = self.env.now
        
        # Calculate utilization (service time / total time)
        utilization = 0.0
        if current_time > 0:
            utilization = self._total_service_time / current_time
        
        # Calculate average metrics
        avg_service_time = 0.0
        avg_queue_time = 0.0
        if self._total_tasks_processed > 0:
            avg_service_time = self._total_service_time / self._total_tasks_processed
            avg_queue_time = self._total_queue_time / self._total_tasks_processed
        
        return {
            'total_tasks': self._total_tasks_processed,
            'total_service_time': self._total_service_time,
            'total_queue_time': self._total_queue_time,
            'utilization': utilization,
            'avg_service_time': avg_service_time,
            'avg_queue_time': avg_queue_time,
            'current_queue_length': self.get_queue_length()
        }
    
    def reset_stats(self) -> None:
        """
        Reset all statistics counters.
        
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.LOCAL, 1000000.0)
        >>> station.reset_stats()
        >>> station.get_utilization_stats()['total_tasks']
        0
        """
        self._processing_history.clear()
        self._total_tasks_processed = 0
        self._total_service_time = 0.0
        self._total_queue_time = 0.0
    
    def __str__(self) -> str:
        """
        String representation of resource station.
        
        Returns:
            Human-readable description
            
        Examples:
        >>> env = simpy.Environment()
        >>> station = ResourceStation(env, Site.EDGE, 5000000.0, 2)
        >>> "EDGE" in str(station)
        True
        """
        return (f"ResourceStation(name={self.name.name}, "
                f"service_rate={self.service_rate}, "
                f"capacity={self.capacity}, "
                f"queue_length={self.get_queue_length()})")


def create_stations_from_config(env: simpy.Environment, config) -> dict[Site, ResourceStation]:
    """
    Create resource stations from configuration.
    
    Args:
        env: SimPy environment
        config: Configuration object with service settings
        
    Returns:
        Dictionary mapping Site to ResourceStation
        
    Examples:
    >>> import simpy
    >>> env = simpy.Environment()
    >>> from battery_offloading.config import Config
    >>> config = Config.from_yaml('configs/baseline.yaml')  # doctest: +SKIP
    >>> stations = create_stations_from_config(env, config)  # doctest: +SKIP
    >>> Site.LOCAL in stations  # doctest: +SKIP
    True
    """
    stations = {}
    
    # Create LOCAL station
    stations[Site.LOCAL] = ResourceStation(
        env=env,
        name=Site.LOCAL,
        service_rate=config.local_service.processing_rate_ops_per_sec,
        capacity=1  # Single local processor
    )
    
    # Create EDGE station
    stations[Site.EDGE] = ResourceStation(
        env=env,
        name=Site.EDGE,
        service_rate=config.edge_service.processing_rate_ops_per_sec,
        capacity=1  # Single edge server connection
    )
    
    # Create CLOUD station
    stations[Site.CLOUD] = ResourceStation(
        env=env,
        name=Site.CLOUD,
        service_rate=config.cloud_service.processing_rate_ops_per_sec,
        capacity=1  # Single cloud service connection
    )
    
    return stations