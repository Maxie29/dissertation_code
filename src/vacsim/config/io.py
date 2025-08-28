"""
Configuration I/O utilities for loading and validating configuration files.
"""

import os
import yaml
from pydantic import ValidationError
from typing import Dict, Any

try:
    from vacsim.config.schema import ExperimentConfig
    SCHEMA_AVAILABLE = True
except ImportError:
    SCHEMA_AVAILABLE = False
    print("Warning: Could not import schema definitions. Validation will be limited.")
    # Define minimal version for compatibility
    class ExperimentConfig(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            for key, value in kwargs.items():
                setattr(self, key, value)

def load_config(path: str) -> ExperimentConfig:
    """
    Load and validate a configuration from a YAML file.
    
    Args:
        path: Path to the YAML configuration file
        
    Returns:
        A validated ExperimentConfig object
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the configuration is invalid or contains errors
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    try:
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
            
        if not config_dict:
            raise ValueError(f"Empty or invalid YAML in {path}")
            
        # Create the configuration object
        try:
            config = ExperimentConfig(**config_dict)
            print(f"Successfully loaded configuration from {path}")
            return config
        except Exception as e:
            error_str = str(e)
            raise ValueError(f"Configuration validation failed: {error_str}")
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML in {path}: {str(e)}")
