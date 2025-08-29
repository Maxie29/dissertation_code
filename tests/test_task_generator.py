"""
Tests for task model and generator.

Validates that the TaskGenerator produces tasks according to specified
distributions and enforces the hard rules for task dispatch.
"""

import pytest
from src.battery_offloading.task import Task, TaskGenerator
from src.battery_offloading.enums import TaskType


class TestTask:
    """Test Task dataclass functionality."""
    
    def test_nav_task_properties(self):
        """Test that NAV tasks have correct properties."""
        task = Task(
            id=1,
            type=TaskType.NAV,
            size_bytes=1024,
            compute_demand=1000.0,
            created_at=0.0
        )
        
        assert task.can_offload is False
        assert task.edge_affinity is False
        assert task.type == TaskType.NAV
    
    def test_slam_task_properties(self):
        """Test that SLAM tasks have correct properties.""" 
        task = Task(
            id=1,
            type=TaskType.SLAM,
            size_bytes=1024,
            compute_demand=1000.0,
            created_at=0.0
        )
        
        assert task.can_offload is False
        assert task.edge_affinity is False
        assert task.type == TaskType.SLAM
    
    def test_generic_task_properties(self):
        """Test that GENERIC tasks have correct properties."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024,
            compute_demand=1000.0,
            created_at=0.0
        )
        
        assert task.can_offload is True
        assert task.type == TaskType.GENERIC
        
        # Test edge affinity setting
        task.set_edge_affinity(True)
        assert task.edge_affinity is True
    
    def test_cannot_set_edge_affinity_on_special_tasks(self):
        """Test that setting edge affinity on special tasks raises error."""
        nav_task = Task(
            id=1,
            type=TaskType.NAV,
            size_bytes=1024,
            compute_demand=1000.0,
            created_at=0.0
        )
        
        with pytest.raises(ValueError):
            nav_task.set_edge_affinity(True)
    
    def test_deadline_calculations(self):
        """Test deadline calculation methods."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024,
            compute_demand=1000.0,
            deadline_ms=500,
            created_at=10.0
        )
        
        assert task.absolute_deadline == 10.5
        assert task.is_expired(10.3) is False
        assert task.is_expired(10.6) is True
    
    def test_no_deadline_task(self):
        """Test tasks without deadlines."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024,
            compute_demand=1000.0,
            deadline_ms=None,
            created_at=10.0
        )
        
        assert task.absolute_deadline is None
        assert task.is_expired(100.0) is False  # Never expires


class TestTaskGenerator:
    """Test TaskGenerator functionality."""
    
    def test_generator_initialization(self):
        """Test generator initialization with valid parameters."""
        generator = TaskGenerator(
            nav_ratio=0.2,
            slam_ratio=0.1,
            edge_affinity_ratio=0.6,
            seed=42
        )
        
        assert generator.nav_ratio == 0.2
        assert generator.slam_ratio == 0.1
        assert abs(generator.generic_ratio - 0.7) < 1e-10  # Handle floating point precision
        assert generator.edge_affinity_ratio == 0.6
    
    def test_invalid_ratios_raise_error(self):
        """Test that invalid ratios raise ValueError."""
        with pytest.raises(ValueError):
            TaskGenerator(nav_ratio=0.7, slam_ratio=0.5)  # Sum > 1.0
        
        with pytest.raises(ValueError):
            TaskGenerator(edge_affinity_ratio=1.5)  # > 1.0
    
    def test_generate_single_task(self):
        """Test generating a single task."""
        generator = TaskGenerator(seed=42)
        task = generator.generate_task(10.0)
        
        assert isinstance(task, Task)
        assert task.created_at == 10.0
        assert task.id == 1
        assert task.size_bytes > 0
        assert task.compute_demand > 0
    
    def test_task_stream_generation(self):
        """Test generating a stream of tasks."""
        generator = TaskGenerator(seed=42)
        tasks = list(generator.make_stream(5))
        
        assert len(tasks) == 5
        assert all(isinstance(t, Task) for t in tasks)
        assert all(t.created_at >= 0 for t in tasks)
        
        # Tasks should have increasing creation times
        for i in range(1, len(tasks)):
            assert tasks[i].created_at > tasks[i-1].created_at
    
    def test_task_distribution_approximates_ratios(self):
        """Test that generated tasks approximate configured ratios."""
        generator = TaskGenerator(
            nav_ratio=0.3,
            slam_ratio=0.2, 
            edge_affinity_ratio=0.6,
            seed=42
        )
        
        # Generate enough tasks for statistical validity
        tasks = list(generator.make_stream(1000))
        stats = generator.get_statistics(tasks)
        
        # Allow 10% tolerance for random variation
        tolerance = 0.1
        
        assert abs(stats['nav_ratio'] - 0.3) < tolerance
        assert abs(stats['slam_ratio'] - 0.2) < tolerance
        assert abs(stats['generic_ratio'] - 0.5) < tolerance
        
        # Edge affinity should apply only to generic tasks
        if stats['generic_count'] > 0:
            assert abs(stats['edge_affinity_ratio'] - 0.6) < tolerance
    
    def test_hard_rules_enforcement(self):
        """Test that hard rules are enforced for all generated tasks."""
        generator = TaskGenerator(
            nav_ratio=0.2,
            slam_ratio=0.1,
            edge_affinity_ratio=0.5,
            seed=42
        )
        
        tasks = list(generator.make_stream(100))
        
        for task in tasks:
            if task.type in [TaskType.NAV, TaskType.SLAM]:
                # Special tasks cannot be offloaded
                assert task.can_offload is False
                assert task.edge_affinity is False
            elif task.type == TaskType.GENERIC:
                # Generic tasks can be offloaded
                assert task.can_offload is True
                # edge_affinity can be True or False for generic tasks
    
    def test_reproducibility_with_seed(self):
        """Test that same seed produces identical task sequences."""
        generator1 = TaskGenerator(seed=42)
        generator2 = TaskGenerator(seed=42)
        
        tasks1 = list(generator1.make_stream(10))
        tasks2 = list(generator2.make_stream(10))
        
        assert len(tasks1) == len(tasks2)
        
        for t1, t2 in zip(tasks1, tasks2):
            assert t1.type == t2.type
            assert t1.size_bytes == t2.size_bytes
            assert t1.compute_demand == t2.compute_demand
            assert t1.edge_affinity == t2.edge_affinity
    
    def test_statistics_calculation(self):
        """Test statistics calculation for generated tasks."""
        generator = TaskGenerator(seed=42)
        tasks = list(generator.make_stream(50))
        stats = generator.get_statistics(tasks)
        
        assert stats['total_tasks'] == 50
        assert stats['nav_count'] + stats['slam_count'] + stats['generic_count'] == 50
        assert 0 <= stats['nav_ratio'] <= 1
        assert 0 <= stats['slam_ratio'] <= 1
        assert 0 <= stats['generic_ratio'] <= 1
        assert abs(stats['nav_ratio'] + stats['slam_ratio'] + stats['generic_ratio'] - 1.0) < 0.01
        assert stats['avg_size_bytes'] > 0
        assert stats['avg_compute_demand'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])