"""
Configuration management with YAML loading and Pydantic validation.

This module provides structured configuration loading with automatic validation
for the battery offloading simulation. All configuration parameters are validated
at load time to ensure simulation integrity.

The configuration hierarchy follows the simulation architecture:
- Battery: Physical battery specifications
- Services: Processing capabilities of each tier (local/edge/cloud)
- Network: Communication parameters between tiers
- Tasks: Task generation and characteristics
- Simulation: Runtime parameters and thresholds
"""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, validator


class BatteryConfig(BaseModel):
    """
    Battery specifications and initial state.
    
    Defines the physical characteristics of the mobile device battery
    and its initial state at simulation start.
    """
    capacity_mah: int = Field(gt=0, description="Battery capacity in mAh")
    initial_soc: float = Field(ge=0, le=100, description="Initial state of charge (%)")
    discharge_rate_ma: float = Field(gt=0, description="Base discharge rate in mA")


class ServiceConfig(BaseModel):
    """
    Processing service configuration for each execution tier.
    
    Defines the computational capabilities and power consumption
    characteristics of local, edge, and cloud execution environments.
    """
    processing_rate_ops_per_sec: float = Field(gt=0, description="Operations per second")
    power_consumption_mw: float = Field(ge=0, description="Power consumption in mW")


class NetworkConfig(BaseModel):
    """
    Network communication parameters between execution tiers.
    
    Defines latency, bandwidth, and power costs for data transmission
    between the mobile device and edge/cloud resources.
    """
    latency_ms: float = Field(ge=0, description="Network latency in milliseconds")
    bandwidth_mbps: float = Field(gt=0, description="Available bandwidth in Mbps")
    transmission_power_mw: float = Field(ge=0, description="Power cost for transmission in mW")


class TaskGenerationConfig(BaseModel):
    """
    Parameters for task generation during simulation.
    
    Controls the characteristics and distribution of tasks created
    during the simulation run.
    """
    arrival_rate_per_sec: float = Field(gt=0, description="Task arrival rate (tasks/sec)")
    avg_operations: float = Field(gt=0, description="Average computational operations per task")
    avg_data_size_mb: float = Field(ge=0, description="Average data size per task in MB")
    nav_ratio: float = Field(ge=0, le=1, description="Ratio of NAV tasks")
    slam_ratio: float = Field(ge=0, le=1, description="Ratio of SLAM tasks") 
    edge_affinity_ratio: float = Field(ge=0, le=1, description="Ratio of generic tasks with edge affinity")
    
    @validator('nav_ratio', 'slam_ratio')
    def validate_task_ratios(cls, v, values):
        """Ensure NAV + SLAM ratios don't exceed 1.0"""
        if 'nav_ratio' in values and v + values['nav_ratio'] > 1.0:
            raise ValueError("Combined NAV and SLAM ratios cannot exceed 1.0")
        return v


class SimulationConfig(BaseModel):
    """
    Runtime simulation parameters and control settings.
    
    Defines simulation duration, decision thresholds, and other
    runtime parameters that control simulation behavior.
    """
    duration_sec: float = Field(gt=0, description="Simulation duration in seconds")
    soc_threshold: float = Field(ge=0, le=100, description="SoC threshold for offloading decisions (%)")
    random_seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    output_directory: str = Field(default="results", description="Directory for simulation outputs")


class Config(BaseModel):
    """
    Main configuration container with validation.
    
    Root configuration object that contains all simulation parameters
    organized by functional area. Provides methods for loading from
    YAML files with comprehensive validation.
    
    Examples:
    >>> config = Config.from_yaml('configs/baseline.yaml')
    >>> config.battery.capacity_mah
    5000
    >>> config.simulation.soc_threshold
    30.0
    """
    battery: BatteryConfig
    local_service: ServiceConfig
    edge_service: ServiceConfig
    cloud_service: ServiceConfig
    edge_network: NetworkConfig
    cloud_network: NetworkConfig  
    task_generation: TaskGenerationConfig
    simulation: SimulationConfig
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'Config':
        """
        Load configuration from YAML file with validation.
        
        Args:
            file_path: Path to the YAML configuration file
            
        Returns:
            Validated Config instance
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the YAML file is malformed
            ValidationError: If the configuration doesn't match the schema
            
        Examples:
        >>> config = Config.from_yaml('configs/baseline.yaml')
        >>> isinstance(config, Config)
        True
        """
        config_path = Path(file_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        return cls(**yaml_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dictionary representation of the configuration
            
        Examples:
        >>> config = Config.from_yaml('configs/baseline.yaml')
        >>> config_dict = config.to_dict()
        >>> 'battery' in config_dict
        True
        """
        return self.dict()
    
    def save_yaml(self, file_path: str) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            file_path: Path where to save the configuration
            
        Examples:
        >>> config = Config.from_yaml('configs/baseline.yaml')
        >>> config.save_yaml('configs/modified.yaml')
        """
        config_dict = self.to_dict()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)