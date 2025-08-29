"""
Sanity tests for the battery offloading project.

These smoke tests verify that the basic components of the project
can be imported and instantiated correctly. They serve as a quick
validation that the project structure is working properly.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from battery_offloading import Config, TaskType, Site
from battery_offloading.config import (
    BatteryConfig, ServiceConfig, NetworkConfig, 
    TaskGenerationConfig, SimulationConfig
)
from battery_offloading.enums import TaskType, Site
from battery_offloading.utils import get_timestamp, format_duration


class TestProjectStructure:
    """Test basic project structure and imports."""
    
    def test_can_import_main_package(self):
        """Test that the main package can be imported."""
        import battery_offloading
        assert hasattr(battery_offloading, '__version__')
    
    def test_can_import_enums(self):
        """Test that enum classes can be imported and used."""
        assert TaskType.NAV
        assert TaskType.SLAM  
        assert TaskType.GENERIC
        assert Site.LOCAL
        assert Site.EDGE
        assert Site.CLOUD
    
    def test_can_import_config_classes(self):
        """Test that config classes can be imported."""
        assert BatteryConfig
        assert ServiceConfig
        assert NetworkConfig
        assert TaskGenerationConfig
        assert SimulationConfig
        assert Config


class TestEnums:
    """Test enum functionality."""
    
    def test_task_type_special_detection(self):
        """Test that special task types are correctly identified."""
        assert TaskType.is_special(TaskType.NAV) is True
        assert TaskType.is_special(TaskType.SLAM) is True
        assert TaskType.is_special(TaskType.GENERIC) is False
    
    def test_get_special_tasks(self):
        """Test that special tasks set is correct."""
        special_tasks = TaskType.get_special_tasks()
        assert TaskType.NAV in special_tasks
        assert TaskType.SLAM in special_tasks
        assert TaskType.GENERIC not in special_tasks
        assert len(special_tasks) == 2
    
    def test_site_string_representation(self):
        """Test that Site enum string representation works."""
        assert str(Site.LOCAL) == "local"
        assert str(Site.EDGE) == "edge"
        assert str(Site.CLOUD) == "cloud"


class TestConfiguration:
    """Test configuration loading and validation."""
    
    def test_can_load_baseline_config(self):
        """Test that baseline.yaml can be loaded successfully."""
        config_path = project_root / "configs" / "baseline.yaml"
        assert config_path.exists(), f"baseline.yaml not found at {config_path}"
        
        config = Config.from_yaml(str(config_path))
        assert isinstance(config, Config)
    
    def test_baseline_config_structure(self):
        """Test that baseline config has expected structure."""
        config_path = project_root / "configs" / "baseline.yaml"
        config = Config.from_yaml(str(config_path))
        
        # Test battery configuration
        assert config.battery.capacity_mah > 0
        assert 0 <= config.battery.initial_soc <= 100
        assert config.battery.discharge_rate_ma > 0
        
        # Test service configurations
        assert config.local_service.processing_rate_ops_per_sec > 0
        assert config.edge_service.processing_rate_ops_per_sec > 0
        assert config.cloud_service.processing_rate_ops_per_sec > 0
        
        # Test network configurations
        assert config.edge_network.latency_ms >= 0
        assert config.cloud_network.latency_ms >= 0
        assert config.edge_network.bandwidth_mbps > 0
        assert config.cloud_network.bandwidth_mbps > 0
        
        # Test simulation parameters
        assert config.simulation.duration_sec > 0
        assert 0 <= config.simulation.soc_threshold <= 100
    
    def test_baseline_config_task_ratios(self):
        """Test that task ratios in baseline config are valid."""
        config_path = project_root / "configs" / "baseline.yaml"
        config = Config.from_yaml(str(config_path))
        
        task_gen = config.task_generation
        
        # Test individual ratio bounds
        assert 0 <= task_gen.nav_ratio <= 1
        assert 0 <= task_gen.slam_ratio <= 1
        assert 0 <= task_gen.edge_affinity_ratio <= 1
        
        # Test that NAV + SLAM ratios don't exceed 1.0
        assert task_gen.nav_ratio + task_gen.slam_ratio <= 1.0
    
    def test_config_to_dict(self):
        """Test that config can be converted to dictionary."""
        config_path = project_root / "configs" / "baseline.yaml"
        config = Config.from_yaml(str(config_path))
        
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'battery' in config_dict
        assert 'simulation' in config_dict


class TestUtilities:
    """Test utility functions."""
    
    def test_get_timestamp(self):
        """Test timestamp generation."""
        timestamp = get_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
        # ISO format should contain 'T'
        assert 'T' in timestamp
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(30.5) == "30.5s"
        assert format_duration(125.5) == "2m 5.5s"
        assert format_duration(3661.2) == "1h 1m 1.2s"


class TestProjectFiles:
    """Test that required project files exist."""
    
    def test_required_files_exist(self):
        """Test that all required project files are present."""
        required_files = [
            "README.md",
            "requirements.txt", 
            ".gitignore",
            "configs/baseline.yaml",
            "src/battery_offloading/__init__.py",
            "src/battery_offloading/enums.py",
            "src/battery_offloading/config.py",
            "src/battery_offloading/utils.py",
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])