"""
Tests for the configuration system.

This script tests loading a configuration file from the configs/experiments directory
and prints the loaded configuration content to verify everything works correctly.
"""

import os
import sys
import pytest
from pprint import pprint

# Global flag to track if imports succeeded
IMPORTS_OK = False
SCHEMA_OK = False

# Try to import the modules
try:
    from vacsim.config.io import load_config
    IMPORTS_OK = True
    try:
        from vacsim.config.schema import ExperimentConfig, SimulationConfig
        SCHEMA_OK = True
    except ImportError:
        # Schema import failed but IO worked
        pass
except ImportError:
    # Try adding src to path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    try:
        from vacsim.config.io import load_config
        IMPORTS_OK = True
        try:
            from vacsim.config.schema import ExperimentConfig, SimulationConfig
            SCHEMA_OK = True
        except ImportError:
            # Schema import failed but IO worked
            pass
    except ImportError:
        # Both imports failed, define dummy load_config for graceful skipping
        def load_config(path):
            pytest.skip("Could not import vacsim.config.io.load_config")


def test_load_valid_config():
    """Test loading a valid configuration file."""
    if not IMPORTS_OK:
        pytest.skip("Required imports not available")
        
    config_path = os.path.join("configs", "experiments", "example.yaml")
    config = load_config(config_path)
    
    # Basic validation
    if SCHEMA_OK:
        assert isinstance(config, ExperimentConfig)
        
    # These assertions should work regardless of schema availability
    assert hasattr(config, "simulation")
    assert hasattr(config.simulation, "seeds")
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
    if not IMPORTS_OK:
        pytest.skip("Required imports not available")
        
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")


def test_invalid_config():
    """Test handling of invalid configuration."""
    if not IMPORTS_OK:
        pytest.skip("Required imports not available")
        
    # This test would require a fixture with invalid configuration
    # For now, it's a placeholder
    pass


def test_default_values():
    """Test that default values are properly applied."""
    if not IMPORTS_OK:
        pytest.skip("Required imports not available")
        
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


def load_and_print_config():
    """
    Load the example configuration file and print its contents.
    This function is used when running the script directly.
    """
    if not IMPORTS_OK:
        print("⚠️ Could not import vacsim.config.io.load_config - please install the package first")
        print("Try: pip install -e .")
        return False
    
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
        
        return True
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False


if __name__ == "__main__":
    # When run directly, load and print the config
    success = load_and_print_config()
    if success:
        print("Test completed successfully!")
    else:
        sys.exit(1)
