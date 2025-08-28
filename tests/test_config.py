"""
Tests for the configuration system.

This script tests loading a configuration file from the configs/experiments directory
and prints the loaded configuration content to verify everything works correctly.
"""

import os
import pytest
from pprint import pprint

from vacsim.config.io import load_config
from vacsim.config.schema import ExperimentConfig, SimulationConfig

def test_load_valid_config():
    """Test loading a valid configuration file."""
    config_path = os.path.join("configs", "experiments", "example.yaml")
    config = load_config(config_path)
    
    # Basic validation
    assert isinstance(config, ExperimentConfig)
    assert config.simulation.seeds == 123
    assert config.simulation.duration_s == 1200
    assert config.robot.battery_capacity_Wh == 50.0
    assert len(config.nodes) == 3
    
    # Check if node types are correctly parsed
    node_kinds = [node.kind for node in config.nodes]
    assert "robot" in node_kinds
    assert "edge" in node_kinds
    assert "cloud" in node_kinds

def test_missing_config_file():
    """Test handling of missing configuration files."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")

def test_invalid_config():
    """Test handling of invalid configuration."""
    # This test would require a fixture with invalid configuration
    # For now, it's a placeholder
    pass

def test_default_values():
    """Test that default values are properly applied."""
    # Minimal config that relies on defaults
    minimal_config = {
        "nodes": [{"name": "robot", "kind": "robot", "cpu_cycles_per_sec": 1e9, "max_power_W": 10.0}],
        "network": {
            "uplink_Mbps": 10.0, 
            "downlink_Mbps": 10.0, 
            "rtt_ms": 10.0,
            "tx_energy_nJ_per_bit": 0.1, 
            "rx_energy_nJ_per_bit": 0.1
        },
        "task": {
            "mean_arrival_rate_hz": 1.0,
            "size_kbits_dist": {"type": "constant", "params": {"value": 10.0}},
            "cycles_dist": {"type": "constant", "params": {"value": 1e9}},
            "deadline_s_dist": {"type": "constant", "params": {"value": 1.0}}
        },
        "policy": {"name": "SimplePolicy"}
    }
    
    # When we have a way to load from dict, add assertion here
    pass

def test_load_example_config():
    """
    Test loading the example configuration file and print its contents.
    """
    config_path = os.path.join("configs", "experiments", "example.yaml")
    
    try:
        # Attempt to load the configuration
        cfg = load_config(config_path)
        
        print(f"\n✅ Successfully loaded configuration from {config_path}")
        
        # Print the configuration content
        print("\n===== Configuration Content =====")
        print(f"Simulation duration: {cfg.simulation.duration_s} seconds")
        print(f"Robot battery capacity: {cfg.robot.battery_capacity_Wh} Wh")
        print(f"Initial state of charge: {cfg.robot.init_soc * 100:.1f}%")
        
        print("\nNodes:")
        for node in cfg.nodes:
            print(f"  - {node.name} ({node.kind}): {node.cpu_cycles_per_sec/1e9:.1f} GHz CPU")
        
        print(f"\nNetwork: {cfg.network.uplink_Mbps} Mbps up / {cfg.network.downlink_Mbps} Mbps down")
        print(f"Task arrival rate: {cfg.task.mean_arrival_rate_hz} tasks/second")
        print(f"Policy: {cfg.policy.name}")
        print(f"Output directory: {cfg.metrics.out_dir}")
        print("================================\n")
        
        return cfg
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        raise


if __name__ == "__main__":
    # When run directly, execute the test function
    test_load_example_config()
    print("Test completed successfully!")
        raise


if __name__ == "__main__":
    # When run directly, execute the test function
    test_load_example_config()
    print("Test completed successfully!")
=======
>>>>>>> Stashed changes
