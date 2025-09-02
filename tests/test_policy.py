"""
Tests for task dispatch policy module.

Validates that the policy implementation strictly adheres to the hard rules
and passes all acceptance criteria without exception.

ACCEPTANCE CRITERIA (MUST PASS):
- SoC=25%, GENERIC → CLOUD
- SoC=30%, GENERIC → CLOUD (equal sign goes to cloud)
- SoC=35%, GENERIC, edge_affinity=True → EDGE  
- SoC=35%, GENERIC, edge_affinity=False → LOCAL
- Any SoC, NAV/SLAM → LOCAL
"""

import pytest
from src.battery_offloading.policy import (
    BATT_THRESH, 
    is_special, 
    decide_site,
    batch_decide_sites,
    get_dispatch_statistics,
    validate_dispatch_rules
)
from src.battery_offloading.task import Task
from src.battery_offloading.enums import TaskType, Site


class TestBasicRules:
    """Test basic dispatch rule functionality."""
    
    def test_battery_threshold_constant(self):
        """Test that battery threshold is set correctly."""
        assert BATT_THRESH == 30
    
    def test_is_special_nav_tasks(self):
        """Test special task detection for NAV tasks."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        assert is_special(nav_task) is True
    
    def test_is_special_slam_tasks(self):
        """Test special task detection for SLAM tasks."""
        slam_task = Task(1, TaskType.SLAM, 1024, 1000000.0, 0.0)
        assert is_special(slam_task) is True
    
    def test_is_special_generic_tasks(self):
        """Test that GENERIC tasks are not considered special."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        assert is_special(generic_task) is False
    
    def test_invalid_soc_raises_error(self):
        """Test that invalid SoC values raise ValueError."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        with pytest.raises(ValueError):
            decide_site(generic_task, -10.0)  # Negative SoC
        
        with pytest.raises(ValueError):
            decide_site(generic_task, 150.0)  # SoC > 100%


class TestAcceptanceCriteria:
    """Test all acceptance criteria exactly as specified."""
    
    def test_soc_25_generic_to_cloud(self):
        """Acceptance Criteria: SoC=25%, GENERIC → CLOUD."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        # Edge affinity doesn't matter when SoC ≤ 30%
        generic_task.set_edge_affinity(True)
        
        site = decide_site(generic_task, 25.0)
        assert site == Site.CLOUD, f"Expected CLOUD for SoC=25%, got {site}"
        
        # Test with edge_affinity=False as well
        generic_task.set_edge_affinity(False)
        site = decide_site(generic_task, 25.0)
        assert site == Site.CLOUD, f"Expected CLOUD for SoC=25% (no edge affinity), got {site}"
    
    def test_soc_30_generic_to_cloud(self):
        """Acceptance Criteria: SoC=30%, GENERIC → CLOUD (equal sign goes to cloud)."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # Test with edge affinity (should still go to CLOUD)
        generic_task.set_edge_affinity(True)
        site = decide_site(generic_task, 30.0)
        assert site == Site.CLOUD, f"Expected CLOUD for SoC=30% (boundary), got {site}"
        
        # Test without edge affinity
        generic_task.set_edge_affinity(False)
        site = decide_site(generic_task, 30.0)
        assert site == Site.CLOUD, f"Expected CLOUD for SoC=30% (boundary, no edge affinity), got {site}"
    
    def test_soc_35_generic_edge_affinity_true_to_edge(self):
        """Acceptance Criteria: SoC=35%, GENERIC, edge_affinity=True → EDGE."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task.set_edge_affinity(True)
        
        site = decide_site(generic_task, 35.0)
        assert site == Site.EDGE, f"Expected EDGE for SoC=35% with edge affinity, got {site}"
    
    def test_soc_35_generic_edge_affinity_false_to_local(self):
        """Acceptance Criteria: SoC=35%, GENERIC, edge_affinity=False → LOCAL."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task.set_edge_affinity(False)
        
        site = decide_site(generic_task, 35.0)
        assert site == Site.LOCAL, f"Expected LOCAL for SoC=35% without edge affinity, got {site}"
    
    def test_any_soc_nav_to_local(self):
        """Acceptance Criteria: Any SoC, NAV → LOCAL."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        
        test_soc_values = [0.0, 10.0, 25.0, 30.0, 35.0, 50.0, 80.0, 100.0]
        
        for soc in test_soc_values:
            site = decide_site(nav_task, soc)
            assert site == Site.LOCAL, f"Expected LOCAL for NAV task at SoC={soc}%, got {site}"
    
    def test_any_soc_slam_to_local(self):
        """Acceptance Criteria: Any SoC, SLAM → LOCAL."""
        slam_task = Task(1, TaskType.SLAM, 1024, 1000000.0, 0.0)
        
        test_soc_values = [0.0, 10.0, 25.0, 30.0, 35.0, 50.0, 80.0, 100.0]
        
        for soc in test_soc_values:
            site = decide_site(slam_task, soc)
            assert site == Site.LOCAL, f"Expected LOCAL for SLAM task at SoC={soc}%, got {site}"


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""
    
    def test_boundary_exactly_30_percent(self):
        """Test the exact boundary condition at 30.0%."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # Test both edge affinity values at exactly 30%
        generic_task.set_edge_affinity(True)
        assert decide_site(generic_task, 30.0) == Site.CLOUD
        
        generic_task.set_edge_affinity(False)
        assert decide_site(generic_task, 30.0) == Site.CLOUD
    
    def test_boundary_just_below_30_percent(self):
        """Test just below the threshold (29.9%)."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task.set_edge_affinity(True)
        
        site = decide_site(generic_task, 29.9)
        assert site == Site.CLOUD, "29.9% should go to CLOUD"
    
    def test_boundary_just_above_30_percent(self):
        """Test just above the threshold (30.1%)."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # With edge affinity → EDGE
        generic_task.set_edge_affinity(True)
        site = decide_site(generic_task, 30.1)
        assert site == Site.EDGE, "30.1% with edge affinity should go to EDGE"
        
        # Without edge affinity → LOCAL
        generic_task.set_edge_affinity(False)
        site = decide_site(generic_task, 30.1)
        assert site == Site.LOCAL, "30.1% without edge affinity should go to LOCAL"
    
    def test_extreme_soc_values(self):
        """Test extreme SoC values (0% and 100%)."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        nav_task = Task(2, TaskType.NAV, 1024, 1000000.0, 0.0)
        
        # 0% SoC
        assert decide_site(generic_task, 0.0) == Site.CLOUD
        assert decide_site(nav_task, 0.0) == Site.LOCAL
        
        # 100% SoC
        generic_task.set_edge_affinity(True)
        assert decide_site(generic_task, 100.0) == Site.EDGE
        generic_task.set_edge_affinity(False)
        assert decide_site(generic_task, 100.0) == Site.LOCAL
        assert decide_site(nav_task, 100.0) == Site.LOCAL


class TestBatchOperations:
    """Test batch dispatch operations."""
    
    def test_batch_decide_sites(self):
        """Test batch decision making."""
        tasks = [
            Task(1, TaskType.NAV, 1024, 1000000.0, 0.0),
            Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0),
            Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0),
            Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        ]
        
        # Set edge affinity for generic tasks
        tasks[2].set_edge_affinity(True)
        tasks[3].set_edge_affinity(False)
        
        # Test at low SoC (25%) - all GENERIC should go to CLOUD
        decisions = batch_decide_sites(tasks, 25.0)
        
        assert len(decisions) == 4
        assert decisions[0][1] == Site.LOCAL  # NAV
        assert decisions[1][1] == Site.LOCAL  # SLAM
        assert decisions[2][1] == Site.CLOUD  # GENERIC (low SoC overrides edge affinity)
        assert decisions[3][1] == Site.CLOUD  # GENERIC (low SoC)
        
        # Test at high SoC (50%) - edge affinity matters for GENERIC
        decisions = batch_decide_sites(tasks, 50.0)
        
        assert decisions[0][1] == Site.LOCAL  # NAV
        assert decisions[1][1] == Site.LOCAL  # SLAM
        assert decisions[2][1] == Site.EDGE   # GENERIC with edge affinity
        assert decisions[3][1] == Site.LOCAL  # GENERIC without edge affinity
    
    def test_dispatch_statistics(self):
        """Test dispatch statistics calculation."""
        # Create sample decisions
        tasks_sites = [
            (Task(1, TaskType.NAV, 1024, 1000000.0, 0.0), Site.LOCAL),
            (Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0), Site.LOCAL),
            (Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.EDGE),
            (Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.CLOUD)
        ]
        
        stats = get_dispatch_statistics(tasks_sites)
        
        assert stats['total_tasks'] == 4
        assert stats['local_count'] == 2
        assert stats['edge_count'] == 1
        assert stats['cloud_count'] == 1
        assert stats['special_tasks'] == 2  # NAV + SLAM
        assert stats['generic_tasks'] == 2
        assert abs(stats['local_ratio'] - 0.5) < 0.001
    
    def test_empty_batch_statistics(self):
        """Test statistics for empty batch."""
        stats = get_dispatch_statistics([])
        
        assert stats['total_tasks'] == 0
        assert stats['local_count'] == 0
        assert stats['edge_count'] == 0
        assert stats['cloud_count'] == 0
        assert stats['local_ratio'] == 0.0


class TestRuleValidation:
    """Test built-in rule validation."""
    
    def test_validate_dispatch_rules(self):
        """Test that all dispatch rules validate correctly."""
        validation = validate_dispatch_rules()
        
        # All individual rules should pass
        assert validation['nav_always_local'] is True
        assert validation['slam_always_local'] is True
        assert validation['low_soc_to_cloud'] is True
        assert validation['high_soc_edge_affinity'] is True
        assert validation['high_soc_no_edge_affinity'] is True
        assert validation['boundary_condition_30_percent'] is True
        
        # Overall validation should pass
        assert validation['all_rules_valid'] is True


class TestComprehensiveScenarios:
    """Test comprehensive scenarios combining different conditions."""
    
    def test_mixed_task_types_low_battery(self):
        """Test mixed task types at low battery (20%)."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0)
        generic_edge = Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_local = Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        generic_edge.set_edge_affinity(True)
        generic_local.set_edge_affinity(False)
        
        soc = 20.0  # Low battery
        
        # Special tasks should always be LOCAL
        assert decide_site(nav_task, soc) == Site.LOCAL
        assert decide_site(slam_task, soc) == Site.LOCAL
        
        # Generic tasks should go to CLOUD regardless of edge affinity
        assert decide_site(generic_edge, soc) == Site.CLOUD
        assert decide_site(generic_local, soc) == Site.CLOUD
    
    def test_mixed_task_types_high_battery(self):
        """Test mixed task types at high battery (80%)."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0)
        generic_edge = Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_local = Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        generic_edge.set_edge_affinity(True)
        generic_local.set_edge_affinity(False)
        
        soc = 80.0  # High battery
        
        # Special tasks should always be LOCAL
        assert decide_site(nav_task, soc) == Site.LOCAL
        assert decide_site(slam_task, soc) == Site.LOCAL
        
        # Generic tasks should follow edge affinity
        assert decide_site(generic_edge, soc) == Site.EDGE
        assert decide_site(generic_local, soc) == Site.LOCAL
    
    def test_boundary_sweep(self):
        """Test a sweep around the 30% boundary."""
        generic_task_edge = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task_local = Task(2, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        generic_task_edge.set_edge_affinity(True)
        generic_task_local.set_edge_affinity(False)
        
        # Test values around the boundary
        test_values = [29.0, 29.5, 29.9, 30.0, 30.1, 30.5, 31.0]
        
        for soc in test_values:
            if soc <= 30.0:
                # Should go to CLOUD
                assert decide_site(generic_task_edge, soc) == Site.CLOUD
                assert decide_site(generic_task_local, soc) == Site.CLOUD
            else:
                # Should follow edge affinity
                assert decide_site(generic_task_edge, soc) == Site.EDGE
                assert decide_site(generic_task_local, soc) == Site.LOCAL


if __name__ == "__main__":
    # Run specific acceptance criteria tests
    pytest.main([__file__ + "::TestAcceptanceCriteria", "-v"])