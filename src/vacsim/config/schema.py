"""
Configuration schema definitions using Pydantic.

This module defines the data models for configuration validation and parsing
in the VacSim system.
"""

from typing import Dict, List, Literal, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class SimulationConfig(BaseModel):
    """
    Simulation parameters configuration.
    """
    seeds: int = Field(
        default=42,
        description="Random seeds for reproducibility"
    )
    duration_s: float = Field(
        default=3600.0,
        description="Total simulation duration in seconds",
        ge=0.0
    )
    time_step_s: float = Field(
        default=0.1,
        description="Simulation time step in seconds",
        gt=0.0
    )


class RobotConfig(BaseModel):
    """
    Robot hardware configuration including battery and power consumption parameters.
    """
    battery_capacity_Wh: float = Field(
        default=50.0,
        description="Battery capacity in watt-hours",
        gt=0.0
    )
    idle_power_W: float = Field(
        default=5.0,
        description="Power consumption when idle in watts",
        ge=0.0
    )
    move_power_W: float = Field(
        default=15.0,
        description="Power consumption when moving in watts",
        gt=0.0
    )
    compute_efficiency_J_per_cycle: float = Field(
        default=1e-9,
        description="Energy required per CPU cycle in joules",
        gt=0.0
    )
    init_soc: float = Field(
        default=1.0,
        description="Initial state of charge as fraction (0-1)",
        ge=0.0,
        le=1.0
    )


class NodeConfig(BaseModel):
    """
    Computational node configuration (robot, edge server, or cloud).
    """
    name: str = Field(
        description="Unique identifier for the node"
    )
    kind: Literal["robot", "edge", "cloud"] = Field(
        description="Type of computational node"
    )
    cpu_cycles_per_sec: float = Field(
        description="Computational capacity in CPU cycles per second",
        gt=0.0
    )
    base_power_W: float = Field(
        default=0.0,
        description="Base power consumption in watts",
        ge=0.0
    )
    max_power_W: float = Field(
        description="Maximum power consumption in watts",
        gt=0.0
    )


class NetworkConfig(BaseModel):
    """
    Network configuration for communication between nodes.
    """
    uplink_Mbps: float = Field(
        description="Uplink bandwidth in megabits per second",
        gt=0.0
    )
    downlink_Mbps: float = Field(
        description="Downlink bandwidth in megabits per second",
        gt=0.0
    )
    rtt_ms: float = Field(
        description="Round-trip time in milliseconds",
        ge=0.0
    )
    tx_energy_nJ_per_bit: float = Field(
        description="Energy consumed for transmitting one bit in nanojoules",
        ge=0.0
    )
    rx_energy_nJ_per_bit: float = Field(
        description="Energy consumed for receiving one bit in nanojoules",
        ge=0.0
    )


class DistributionConfig(BaseModel):
    """
    Statistical distribution configuration.
    """
    type: str = Field(
        description="Type of statistical distribution"
    )
    params: Dict[str, Any] = Field(
        description="Parameters for the distribution"
    )


class TaskConfig(BaseModel):
    """
    Task generation and characteristics configuration.
    """
    mean_arrival_rate_hz: float = Field(
        description="Mean task arrival rate in Hertz (tasks per second)",
        gt=0.0
    )
    size_kbits_dist: DistributionConfig = Field(
        description="Distribution of task input/output data size in kilobits"
    )
    cycles_dist: DistributionConfig = Field(
        description="Distribution of computational requirement in CPU cycles"
    )
    deadline_s_dist: DistributionConfig = Field(
        description="Distribution of task deadlines in seconds"
    )
    type_mix: Dict[str, float] | None = Field(
        default=None,
        description="Distribution of different task types by proportion"
    )
    
    class Config:
        extra = "ignore"
    
    @field_validator('type_mix')
    def validate_type_mix(cls, v):
        if v is not None:
            # Check non-negative values
            if any(prop < 0 for prop in v.values()):
                raise ValueError("All proportions in type_mix must be non-negative")
                
            # Check sum is approximately 1
            total = sum(v.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"Sum of type_mix proportions must be 1.0, got {total}")
        return v

class PolicyConfig(BaseModel):
    """
    Task offloading policy configuration.
    """
    name: str = Field(
        description="Name of the offloading policy to use"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the offloading policy"
    )


class MetricsConfig(BaseModel):
    """
    Metrics collection and output configuration.
    """
    flush_interval_s: float = Field(
        default=1.0,
        description="Interval for flushing metrics to storage in seconds",
        gt=0.0
    )
    out_dir: str = Field(
        default="data/runs",
        description="Directory for output data and metrics"
    )


class ExperimentConfig(BaseModel):
    """
    Top-level experiment configuration combining all other configurations.
    """
    simulation: SimulationConfig = Field(
        default_factory=SimulationConfig,
        description="Simulation parameters"
    )
    robot: RobotConfig = Field(
        default_factory=RobotConfig,
        description="Robot hardware configuration"
    )
    nodes: List[NodeConfig] = Field(
        description="Computational nodes configurations"
    )
    network: NetworkConfig = Field(
        description="Network configuration"
    )
    task: TaskConfig = Field(
        description="Task generation configuration"
    )
    policy: PolicyConfig = Field(
        description="Task offloading policy"
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig,
        description="Metrics collection configuration"
    )
