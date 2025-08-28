"""
Tests for core data types and distributions.
"""

import pytest
import numpy as np
from dataclasses import asdict

from vacsim.core.types import (
    Task, Decision, RobotState, NodeState, Destination,
    set_seed, exp, lognormal, normal_clipped
)


def test_task_creation_and_serialization():
    """Test Task creation and serialization to dict."""
    task = Task(
        id=1,
        arrival_time=10.5,
        size_bits=8192,
        cpu_cycles=500000,
        deadline_s=2.0,
        metadata={"priority": "high"}
    )
    
    # Check fields
    assert task.id == 1
    assert task.arrival_time == 10.5
    assert task.size_bits == 8192
    assert task.cpu_cycles == 500000
    assert task.deadline_s == 2.0
    assert task.metadata == {"priority": "high"}
    
    # Check serialization
    task_dict = asdict(task)
    assert isinstance(task_dict, dict)
    assert task_dict["id"] == 1
    assert task_dict["metadata"]["priority"] == "high"


def test_decision_creation_and_serialization():
    """Test Decision creation and serialization to dict."""
    decision = Decision(
        task_id=1,
        dest=Destination.EDGE,
        reason="Low battery level",
        meta={"battery_level": 0.3}
    )
    
    # Check fields
    assert decision.task_id == 1
    assert decision.dest == Destination.EDGE
    assert decision.reason == "Low battery level"
    assert decision.meta == {"battery_level": 0.3}
    
    # Check serialization
    decision_dict = asdict(decision)
    assert isinstance(decision_dict, dict)
    assert decision_dict["task_id"] == 1
    assert decision_dict["dest"] == Destination.EDGE
    assert decision_dict["meta"]["battery_level"] == 0.3


def test_robot_state_validation():
    """Test validation in RobotState initialization."""
    # Valid state
    state = RobotState(time=10.0, soc=0.75, queue_len=3)
    assert state.time == 10.0
    assert state.soc == 0.75
    assert state.queue_len == 3
    assert state.last_decision is None
    
    # Invalid state (soc out of range)
    with pytest.raises(ValueError):
        RobotState(time=10.0, soc=1.5, queue_len=3)
    
    with pytest.raises(ValueError):
        RobotState(time=10.0, soc=-0.1, queue_len=3)


def test_node_state_validation():
    """Test validation in NodeState initialization."""
    # Valid state
    state = NodeState(name="edge_server", utilization=0.5, queue_len=2)
    assert state.name == "edge_server"
    assert state.utilization == 0.5
    assert state.queue_len == 2
    
    # Invalid state (utilization out of range)
    with pytest.raises(ValueError):
        NodeState(name="edge_server", utilization=1.5, queue_len=2)


def test_distribution_seed_reproducibility():
    """Test that setting seeds makes distributions reproducible."""
    # Set initial seed
    set_seed(42)
    
    # Generate sequence of random values
    exp_values_1 = [exp(1.0) for _ in range(5)]
    lognormal_values_1 = [lognormal(0, 1) for _ in range(5)]
    normal_values_1 = [normal_clipped(0, 1, -2, 2) for _ in range(5)]
    
    # Set same seed again
    set_seed(42)
    
    # Generate second sequence
    exp_values_2 = [exp(1.0) for _ in range(5)]
    lognormal_values_2 = [lognormal(0, 1) for _ in range(5)]
    normal_values_2 = [normal_clipped(0, 1, -2, 2) for _ in range(5)]
    
    # Check that sequences match
    assert exp_values_1 == exp_values_2
    np.testing.assert_allclose(lognormal_values_1, lognormal_values_2)
    np.testing.assert_allclose(normal_values_1, normal_values_2)


def test_normal_clipped_boundaries():
    """Test that normal_clipped respects boundaries."""
    # Test large sample to ensure boundaries are respected
    set_seed(42)
    min_val = -2.0
    max_val = 2.0
    
    for _ in range(100):
        val = normal_clipped(0, 5, min_val, max_val)  # Large std to push boundaries
        assert min_val <= val <= max_val
