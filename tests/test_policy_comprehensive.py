"""
Comprehensive policy tests covering SoC threshold boundaries, NAV/SLAM mandatory local execution,
and edge_affinity decision branches with extensive edge case coverage.

Acceptance Criteria:
- SoC=30% boundary testing (exactly at threshold)
- NAV/SLAM tasks ALWAYS execute locally regardless of SoC
- edge_affinity branch coverage for GENERIC tasks
- All boundary conditions and edge cases
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


class TestSoCThresholdBoundary:
    """Test SoC=30% threshold boundary conditions comprehensively."""
    
    def test_soc_exactly_30_percent_goes_to_cloud(self):
        """Test that SoC=30.0% exactly goes to CLOUD for GENERIC tasks."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # Test with edge affinity True
        generic_task.set_edge_affinity(True)
        site = decide_site(generic_task, 30.0)
        assert site == Site.CLOUD, "SoC=30.0% with edge_affinity=True should go to CLOUD"
        
        # Test with edge affinity False
        generic_task.set_edge_affinity(False)
        site = decide_site(generic_task, 30.0)
        assert site == Site.CLOUD, "SoC=30.0% with edge_affinity=False should go to CLOUD"
    
    def test_soc_just_below_30_goes_to_cloud(self):
        """Test SoC values just below 30% go to CLOUD."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        test_soc_values = [29.9, 29.99, 29.999]
        
        for soc in test_soc_values:
            # Test with edge affinity True
            generic_task.set_edge_affinity(True)
            site = decide_site(generic_task, soc)
            assert site == Site.CLOUD, f"SoC={soc}% with edge_affinity=True should go to CLOUD"
            
            # Test with edge affinity False
            generic_task.set_edge_affinity(False)
            site = decide_site(generic_task, soc)
            assert site == Site.CLOUD, f"SoC={soc}% with edge_affinity=False should go to CLOUD"
    
    def test_soc_just_above_30_follows_edge_affinity(self):
        """Test SoC values just above 30% follow edge affinity rules."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        test_soc_values = [30.1, 30.01, 30.001]
        
        for soc in test_soc_values:
            # Test with edge affinity True → EDGE
            generic_task.set_edge_affinity(True)
            site = decide_site(generic_task, soc)
            assert site == Site.EDGE, f"SoC={soc}% with edge_affinity=True should go to EDGE"
            
            # Test with edge affinity False → LOCAL
            generic_task.set_edge_affinity(False)
            site = decide_site(generic_task, soc)
            assert site == Site.LOCAL, f"SoC={soc}% with edge_affinity=False should go to LOCAL"
    
    def test_threshold_constant_immutable(self):
        """Test that BATT_THRESH constant is 30 and immutable."""
        assert BATT_THRESH == 30, "BATT_THRESH must be exactly 30"
        assert isinstance(BATT_THRESH, int), "BATT_THRESH must be an integer"


class TestNAVSLAMAlwaysLocal:
    """Test that NAV/SLAM tasks ALWAYS execute locally regardless of SoC level."""
    
    def test_nav_always_local_at_all_soc_levels(self):
        """Test NAV tasks execute locally at every possible SoC level."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        
        # Test across full SoC range including boundaries
        test_soc_values = [
            0.0, 0.1, 1.0, 10.0, 20.0, 25.0,
            29.9, 30.0, 30.1, 31.0, 50.0, 75.0,
            99.0, 99.9, 100.0
        ]
        
        for soc in test_soc_values:
            site = decide_site(nav_task, soc)
            assert site == Site.LOCAL, f"NAV task at SoC={soc}% should execute LOCAL, got {site}"
        
        # Verify is_special detection
        assert is_special(nav_task) is True, "NAV tasks should be detected as special"
    
    def test_slam_always_local_at_all_soc_levels(self):
        """Test SLAM tasks execute locally at every possible SoC level."""
        slam_task = Task(1, TaskType.SLAM, 1024, 1000000.0, 0.0)
        
        # Test across full SoC range including boundaries
        test_soc_values = [
            0.0, 0.1, 1.0, 10.0, 20.0, 25.0,
            29.9, 30.0, 30.1, 31.0, 50.0, 75.0,
            99.0, 99.9, 100.0
        ]
        
        for soc in test_soc_values:
            site = decide_site(slam_task, soc)
            assert site == Site.LOCAL, f"SLAM task at SoC={soc}% should execute LOCAL, got {site}"
        
        # Verify is_special detection
        assert is_special(slam_task) is True, "SLAM tasks should be detected as special"
    
    def test_nav_slam_ignore_edge_affinity(self):
        """Test that NAV/SLAM tasks ignore edge affinity settings completely."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0)
        
        # NAV/SLAM tasks don't have edge_affinity, but test conceptually
        test_soc_values = [0.0, 25.0, 30.0, 35.0, 100.0]
        
        for soc in test_soc_values:
            assert decide_site(nav_task, soc) == Site.LOCAL
            assert decide_site(slam_task, soc) == Site.LOCAL
    
    def test_special_task_detection_comprehensive(self):
        """Test comprehensive special task detection."""
        nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
        slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0)
        generic_task = Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # Positive cases
        assert is_special(nav_task) is True, "NAV should be special"
        assert is_special(slam_task) is True, "SLAM should be special"
        
        # Negative case
        assert is_special(generic_task) is False, "GENERIC should not be special"


class TestEdgeAffinityBranches:
    """Test edge_affinity decision branches for GENERIC tasks comprehensively."""
    
    def test_edge_affinity_true_above_threshold(self):
        """Test edge_affinity=True behavior above SoC threshold."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task.set_edge_affinity(True)
        
        # Test various SoC values above threshold
        test_soc_values = [30.1, 31.0, 40.0, 50.0, 75.0, 90.0, 100.0]
        
        for soc in test_soc_values:
            site = decide_site(generic_task, soc)
            assert site == Site.EDGE, f"GENERIC task with edge_affinity=True at SoC={soc}% should go to EDGE"
    
    def test_edge_affinity_false_above_threshold(self):
        """Test edge_affinity=False behavior above SoC threshold."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task.set_edge_affinity(False)
        
        # Test various SoC values above threshold
        test_soc_values = [30.1, 31.0, 40.0, 50.0, 75.0, 90.0, 100.0]
        
        for soc in test_soc_values:
            site = decide_site(generic_task, soc)
            assert site == Site.LOCAL, f"GENERIC task with edge_affinity=False at SoC={soc}% should go to LOCAL"
    
    def test_edge_affinity_ignored_below_threshold(self):
        """Test that edge_affinity is ignored when SoC ≤ 30%."""
        generic_task_edge = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        generic_task_local = Task(2, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        generic_task_edge.set_edge_affinity(True)
        generic_task_local.set_edge_affinity(False)
        
        # Test various SoC values at or below threshold
        test_soc_values = [0.0, 10.0, 20.0, 29.0, 30.0]
        
        for soc in test_soc_values:
            # Both should go to CLOUD regardless of edge affinity
            site_edge = decide_site(generic_task_edge, soc)
            site_local = decide_site(generic_task_local, soc)
            
            assert site_edge == Site.CLOUD, f"GENERIC with edge_affinity=True at SoC={soc}% should go to CLOUD"
            assert site_local == Site.CLOUD, f"GENERIC with edge_affinity=False at SoC={soc}% should go to CLOUD"
    
    def test_edge_affinity_state_persistence(self):
        """Test that edge_affinity state persists correctly."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # Initially should be False (default)
        assert generic_task.edge_affinity is False, "Default edge_affinity should be False"
        
        # Set to True and verify
        generic_task.set_edge_affinity(True)
        assert generic_task.edge_affinity is True, "edge_affinity should be True after setting"
        
        # Test dispatch with True
        site = decide_site(generic_task, 50.0)
        assert site == Site.EDGE, "Should go to EDGE with edge_affinity=True"
        
        # Set back to False and verify
        generic_task.set_edge_affinity(False)
        assert generic_task.edge_affinity is False, "edge_affinity should be False after setting"
        
        # Test dispatch with False
        site = decide_site(generic_task, 50.0)
        assert site == Site.LOCAL, "Should go to LOCAL with edge_affinity=False"


class TestBatchPolicyOperations:
    """Test batch policy operations with comprehensive scenarios."""
    
    def test_mixed_batch_low_soc(self):
        """Test mixed batch of tasks at low SoC (≤30%)."""
        tasks = [
            Task(1, TaskType.NAV, 1024, 1000000.0, 0.0),
            Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0),
            Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0),
            Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0),
        ]
        
        # Set edge affinity for generic tasks
        tasks[2].set_edge_affinity(True)
        tasks[3].set_edge_affinity(False)
        
        # Test at exactly 30% SoC
        decisions = batch_decide_sites(tasks, 30.0)
        
        expected_sites = [Site.LOCAL, Site.LOCAL, Site.CLOUD, Site.CLOUD]
        actual_sites = [site for _, site in decisions]
        
        assert actual_sites == expected_sites, f"Expected {expected_sites}, got {actual_sites}"
    
    def test_mixed_batch_high_soc(self):
        """Test mixed batch of tasks at high SoC (>30%)."""
        tasks = [
            Task(1, TaskType.NAV, 1024, 1000000.0, 0.0),
            Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0),
            Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0),
            Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0),
        ]
        
        # Set edge affinity for generic tasks
        tasks[2].set_edge_affinity(True)
        tasks[3].set_edge_affinity(False)
        
        # Test at 50% SoC
        decisions = batch_decide_sites(tasks, 50.0)
        
        expected_sites = [Site.LOCAL, Site.LOCAL, Site.EDGE, Site.LOCAL]
        actual_sites = [site for _, site in decisions]
        
        assert actual_sites == expected_sites, f"Expected {expected_sites}, got {actual_sites}"
    
    def test_batch_statistics_comprehensive(self):
        """Test comprehensive batch statistics calculation."""
        # Create a diverse batch
        tasks_and_sites = [
            (Task(1, TaskType.NAV, 1024, 1000000.0, 0.0), Site.LOCAL),
            (Task(2, TaskType.NAV, 1024, 1000000.0, 0.0), Site.LOCAL),
            (Task(3, TaskType.SLAM, 1024, 1000000.0, 0.0), Site.LOCAL),
            (Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.EDGE),
            (Task(5, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.EDGE),
            (Task(6, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.LOCAL),
            (Task(7, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.CLOUD),
        ]
        
        stats = get_dispatch_statistics(tasks_and_sites)
        
        # Verify counts
        assert stats['total_tasks'] == 7
        assert stats['local_count'] == 4  # 2 NAV + 1 SLAM + 1 GENERIC
        assert stats['edge_count'] == 2   # 2 GENERIC
        assert stats['cloud_count'] == 1  # 1 GENERIC
        assert stats['special_tasks'] == 3  # 2 NAV + 1 SLAM
        assert stats['generic_tasks'] == 4  # 4 GENERIC
        
        # Verify ratios
        assert abs(stats['local_ratio'] - 4/7) < 0.001
        assert abs(stats['edge_ratio'] - 2/7) < 0.001
        assert abs(stats['cloud_ratio'] - 1/7) < 0.001


class TestPolicyErrorHandling:
    """Test policy error handling and edge cases."""
    
    def test_invalid_soc_values(self):
        """Test that invalid SoC values raise appropriate errors."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        
        # Test negative SoC
        with pytest.raises(ValueError, match="SoC must be between 0-100%"):
            decide_site(generic_task, -0.1)
        
        with pytest.raises(ValueError, match="SoC must be between 0-100%"):
            decide_site(generic_task, -10.0)
        
        # Test SoC > 100%
        with pytest.raises(ValueError, match="SoC must be between 0-100%"):
            decide_site(generic_task, 100.1)
        
        with pytest.raises(ValueError, match="SoC must be between 0-100%"):
            decide_site(generic_task, 150.0)
    
    def test_boundary_soc_values_valid(self):
        """Test that boundary SoC values (0.0, 100.0) are valid."""
        generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        nav_task = Task(2, TaskType.NAV, 1024, 1000000.0, 0.0)
        
        # Test 0.0% - should not raise error
        generic_task.set_edge_affinity(False)
        site = decide_site(generic_task, 0.0)
        assert site == Site.CLOUD, "SoC=0.0% should go to CLOUD"
        
        site = decide_site(nav_task, 0.0)
        assert site == Site.LOCAL, "NAV at SoC=0.0% should go to LOCAL"
        
        # Test 100.0% - should not raise error
        generic_task.set_edge_affinity(True)
        site = decide_site(generic_task, 100.0)
        assert site == Site.EDGE, "SoC=100.0% with edge_affinity should go to EDGE"
        
        site = decide_site(nav_task, 100.0)
        assert site == Site.LOCAL, "NAV at SoC=100.0% should go to LOCAL"


class TestBuiltInValidation:
    """Test built-in validation system comprehensively."""
    
    def test_validation_all_rules_pass(self):
        """Test that built-in validation passes all rules."""
        validation = validate_dispatch_rules()
        
        # Check each individual rule
        individual_rules = [
            'nav_always_local',
            'slam_always_local', 
            'low_soc_to_cloud',
            'high_soc_edge_affinity',
            'high_soc_no_edge_affinity',
            'boundary_condition_30_percent'
        ]
        
        for rule in individual_rules:
            assert validation[rule] is True, f"Rule '{rule}' should pass validation"
        
        # Check overall validation
        assert validation['all_rules_valid'] is True, "Overall validation should pass"
    
    def test_validation_contains_all_rules(self):
        """Test that validation covers all expected rules."""
        validation = validate_dispatch_rules()
        
        expected_rules = {
            'nav_always_local',
            'slam_always_local',
            'low_soc_to_cloud',
            'high_soc_edge_affinity', 
            'high_soc_no_edge_affinity',
            'boundary_condition_30_percent',
            'all_rules_valid'
        }
        
        actual_rules = set(validation.keys())
        assert actual_rules == expected_rules, f"Validation should contain exactly {expected_rules}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])