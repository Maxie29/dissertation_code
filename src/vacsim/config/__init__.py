"""
Configuration module for VacSim.

This module handles loading, validating, and storing simulation configurations.
"""

from vacsim.config.schema import ExperimentConfig
from vacsim.config.io import load_config

__all__ = ["ExperimentConfig", "load_config"]
