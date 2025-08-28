import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass
class Task:
    """Representation of a computational task"""
    id: str
    arrival_time: float  # seconds since start
    size_bits: int       # size of task input/output data in bits
    cpu_cycles: int      # computational requirement in CPU cycles
    deadline_s: float    # deadline in seconds


class TaskConfig:
    """Configuration for task generation"""
    def __init__(self,
                mean_arrival_rate_hz: float,
                size_kbits_dist: str,
                size_kbits_params: Dict[str, Any],
                cycles_dist: str,
                cycles_params: Dict[str, Any],
                deadline_s_dist: str,
                deadline_s_params: Dict[str, Any]):
        """
        Initialize task configuration
        
        Args:
            mean_arrival_rate_hz: Average arrival rate in Hz (tasks per second)
            size_kbits_dist: Distribution type for data size ("exp"|"lognormal"|"normal_clipped")
            size_kbits_params: Parameters for the size distribution
            cycles_dist: Distribution type for CPU cycles ("exp"|"lognormal"|"normal_clipped")
            cycles_params: Parameters for the cycles distribution
            deadline_s_dist: Distribution type for deadline ("exp"|"lognormal"|"normal_clipped")
            deadline_s_params: Parameters for the deadline distribution
        """
        self.mean_arrival_rate_hz = mean_arrival_rate_hz
        
        self.size_kbits_dist = size_kbits_dist
        self.size_kbits_params = size_kbits_params
        
        self.cycles_dist = cycles_dist
        self.cycles_params = cycles_params
        
        self.deadline_s_dist = deadline_s_dist
        self.deadline_s_params = deadline_s_params


class TaskGenerator:
    """Generator for computational tasks with configurable properties"""
    
    def __init__(self, cfg: TaskConfig, rng: Optional[np.random.Generator] = None):
        """
        Initialize task generator with given configuration
        
        Args:
            cfg: Task generation configuration
            rng: Random number generator. If None, a new one is created.
        """
        self.cfg = cfg
        self.rng = rng if rng is not None else np.random.default_rng()
        self.next_id = 0
        self.current_time = 0.0
    
    def _sample_from_distribution(self, dist_type: str, params: Dict[str, Any]) -> float:
        """
        Sample a value from the specified distribution
        
        Args:
            dist_type: Distribution type ("exp", "lognormal", or "normal_clipped")
            params: Parameters for the specified distribution
            
        Returns:
            A random value sampled from the specified distribution
        """
        if dist_type == "exp":
            # Exponential distribution with mean parameter
            return self.rng.exponential(scale=params["mean"])
        
        elif dist_type == "lognormal":
            # Log-normal distribution with mu and sigma parameters
            return self.rng.lognormal(mean=params["mu"], sigma=params["sigma"])
        
        elif dist_type == "normal_clipped":
            # Normal distribution clipped to min_value
            value = self.rng.normal(loc=params["mean"], scale=params["stddev"])
            min_value = params.get("min_value", 0)
            return max(value, min_value)
        
        else:
            raise ValueError(f"Unsupported distribution type: {dist_type}")
    
    def next_task(self) -> Task:
        """
        Generate the next task based on configuration
        
        Returns:
            A newly generated Task object
        """
        # Sample inter-arrival time from exponential distribution
        if self.next_id == 0:
            # First task arrives at time 0
            inter_arrival_time = 0
        else:
            # Generate exponential inter-arrival time based on rate
            inter_arrival_time = self.rng.exponential(scale=1.0 / self.cfg.mean_arrival_rate_hz)
        
        # Update current time
        self.current_time += inter_arrival_time
        
        # Generate task ID
        task_id = f"task_{self.next_id}"
        self.next_id += 1
        
        # Sample task properties from respective distributions
        size_kbits = self._sample_from_distribution(
            self.cfg.size_kbits_dist, 
            self.cfg.size_kbits_params
        )
        size_bits = int(size_kbits * 1000)  # Convert from kbits to bits
        
        cpu_cycles = int(self._sample_from_distribution(
            self.cfg.cycles_dist,
            self.cfg.cycles_params
        ))
        
        deadline_s = self._sample_from_distribution(
            self.cfg.deadline_s_dist,
            self.cfg.deadline_s_params
        )
        
        # Create and return task
        return Task(
            id=task_id,
            arrival_time=self.current_time,
            size_bits=size_bits,
            cpu_cycles=cpu_cycles,
            deadline_s=deadline_s
        )
    
    def generate_tasks(self, count: int) -> List[Task]:
        """
        Generate a specified number of tasks
        
        Args:
            count: Number of tasks to generate
            
        Returns:
            List of generated Task objects
        """
        return [self.next_task() for _ in range(count)]
