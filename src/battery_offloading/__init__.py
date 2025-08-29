"""
Battery Offloading Research Project

A Python simulation framework for studying task offloading strategies 
in battery-constrained mobile computing environments.

This package provides:
- Task dispatch rules based on battery state of charge (SoC)
- Simulation of local, edge, and cloud computing environments
- Configuration management with YAML support and validation
- Utility functions for data collection and analysis

Key Components:
- enums: TaskType (NAV, SLAM, GENERIC) and Site (LOCAL, EDGE, CLOUD) definitions
- config: Configuration loading and validation using Pydantic
- utils: Common utility functions for timestamps, file I/O, and data processing

Hard Rules:
1. NAV and SLAM tasks always execute locally regardless of battery level
2. For other tasks: SoC ≤ 30% → Cloud; SoC > 30% → Local/Edge based on edge_affinity
3. Task execution site is decided at dispatch time with no migration during execution
"""

__version__ = "0.1.0"
__author__ = "Battery Offloading Research Team"

from .enums import TaskType, Site
from .config import Config
from .task import Task, TaskGenerator
from .battery import Battery
from .energy import (
    PowerParameters, 
    ComputationTimes,
    estimate_local_compute_time,
    estimate_remote_compute_time, 
    estimate_comm_time,
    estimate_robot_energy
)
from .sim import ResourceStation, Network, Dispatcher, Runner, Metrics
from .policy import BATT_THRESH, is_special, decide_site

__all__ = [
    "TaskType",
    "Site", 
    "Config",
    "Task",
    "TaskGenerator",
    "Battery",
    "PowerParameters",
    "ComputationTimes",
    "estimate_local_compute_time",
    "estimate_remote_compute_time",
    "estimate_comm_time",
    "estimate_robot_energy",
    "ResourceStation",
    "Network",
    "Dispatcher",
    "Runner", 
    "Metrics",
    "BATT_THRESH",
    "is_special", 
    "decide_site",
]