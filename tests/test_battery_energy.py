"""
Tests for battery and energy models.

Validates battery energy tracking and energy estimation functions
according to the acceptance criteria.
"""

import pytest
from src.battery_offloading.battery import Battery, EnergyConsumptionRecord
from src.battery_offloading.energy import (
    PowerParameters, ComputationTimes,
    estimate_local_compute_time, estimate_remote_compute_time,
    estimate_comm_time, estimate_robot_energy,
    get_execution_energy_breakdown
)
from src.battery_offloading.task import Task, TaskGenerator
from src.battery_offloading.enums import TaskType, Site


class TestBattery:
    """Test Battery model functionality."""
    
    def test_battery_initialization(self):
        """Test battery initialization with valid parameters."""
        battery = Battery(capacity_wh=100.0, initial_soc=80.0)
        
        assert battery.capacity_wh == 100.0
        assert battery.get_soc() == 80.0
        assert battery.get_remaining_energy_wh() == 80.0
        assert battery.get_total_consumed_wh() == 0.0
    
    def test_battery_invalid_parameters(self):
        """Test battery initialization with invalid parameters."""
        with pytest.raises(ValueError):
            Battery(capacity_wh=-10.0)  # Negative capacity
        
        with pytest.raises(ValueError):
            Battery(capacity_wh=100.0, initial_soc=150.0)  # SoC > 100%
        
        with pytest.raises(ValueError):
            Battery(capacity_wh=100.0, initial_soc=-10.0)  # SoC < 0%
    
    def test_energy_consumption(self):
        """Test energy consumption and SoC update."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # Consume 25 Wh (25% of capacity)
        battery.consume_energy_wh(25.0, "test_computation")
        
        assert battery.get_soc() == 75.0
        assert battery.get_remaining_energy_wh() == 75.0
        assert battery.get_total_consumed_wh() == 25.0
    
    def test_negative_energy_consumption(self):
        """Test that negative energy consumption raises error."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        with pytest.raises(ValueError):
            battery.consume_energy_wh(-5.0)
    
    def test_consumption_history(self):
        """Test energy consumption history tracking."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        battery.consume_energy_wh(10.0, "computation", task_id=1, timestamp=1000.0)
        battery.consume_energy_wh(5.0, "communication", task_id=2, timestamp=1001.0)
        
        history = battery.get_consumption_history()
        assert len(history) == 2
        
        # Check first record
        assert history[0].energy_wh == 10.0
        assert history[0].purpose == "computation"
        assert history[0].task_id == 1
        assert history[0].timestamp == 1000.0
        
        # Check second record
        assert history[1].energy_wh == 5.0
        assert history[1].purpose == "communication"
        assert history[1].task_id == 2
    
    def test_consumption_by_purpose(self):
        """Test energy consumption breakdown by purpose."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        battery.consume_energy_wh(10.0, "computation")
        battery.consume_energy_wh(5.0, "communication")
        battery.consume_energy_wh(3.0, "computation")
        
        breakdown = battery.get_consumption_by_purpose()
        assert breakdown["computation"] == 13.0
        assert breakdown["communication"] == 5.0
    
    def test_battery_depletion(self):
        """Test battery depletion detection."""
        battery = Battery(capacity_wh=100.0, initial_soc=20.0)
        
        assert not battery.is_depleted(10.0)  # Above threshold
        assert battery.is_depleted(25.0)     # Below threshold
    
    def test_soc_set_get(self):
        """Test SoC setter and getter."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        battery.set_soc(60.0)
        assert battery.get_soc() == 60.0
        assert battery.get_remaining_energy_wh() == 60.0
        
        with pytest.raises(ValueError):
            battery.set_soc(150.0)  # Invalid SoC
    
    def test_battery_reset(self):
        """Test battery reset functionality."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        battery.consume_energy_wh(25.0, "test")
        assert len(battery.get_consumption_history()) == 1
        assert battery.get_total_consumed_wh() == 25.0
        
        battery.reset(90.0)
        assert battery.get_soc() == 90.0
        assert len(battery.get_consumption_history()) == 0
        assert battery.get_total_consumed_wh() == 0.0


class TestEnergyEstimation:
    """Test energy estimation functions."""
    
    def test_local_compute_time_estimation(self):
        """Test local computation time estimation."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024*1024,  # 1MB
            compute_demand=2000000.0,  # 2M operations
            created_at=0.0
        )
        
        # 1M ops/sec processing rate -> 2 seconds
        time_s = estimate_local_compute_time(task, 1000000.0)
        assert time_s == 2.0
        
        # Invalid processing rate
        with pytest.raises(ValueError):
            estimate_local_compute_time(task, -1000.0)
    
    def test_remote_compute_time_estimation(self):
        """Test remote computation time estimation."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024*1024,
            compute_demand=5000000.0,  # 5M operations
            created_at=0.0
        )
        
        # 10M ops/sec processing rate -> 0.5 seconds
        time_s = estimate_remote_compute_time(task, 10000000.0)
        assert time_s == 0.5
    
    def test_communication_time_estimation(self):
        """Test communication time estimation with acceptance criteria."""
        # Acceptance test: 10MB task, 20Mbps up, 50Mbps down, 20ms RTT
        comm_times = estimate_comm_time(
            task_size_bytes=10*1024*1024,  # 10MB
            bandwidth_up_mbps=20.0,         # 20 Mbps
            bandwidth_down_mbps=50.0,       # 50 Mbps  
            rtt_ms=20.0                     # 20ms RTT
        )
        
        # Check that times are reasonable
        assert comm_times.uplink_s > 0
        assert comm_times.downlink_s > 0
        assert comm_times.total_comm_s > 0
        assert comm_times.total_comm_s == comm_times.uplink_s + comm_times.downlink_s
        
        # Uplink should take longer than downlink (same data, lower bandwidth)
        # But result size is smaller, so actual comparison depends on result_size_ratio
        assert comm_times.uplink_s > comm_times.downlink_s
    
    def test_communication_time_invalid_params(self):
        """Test communication time estimation with invalid parameters."""
        with pytest.raises(ValueError):
            estimate_comm_time(-1024, 20.0, 50.0, 20.0)  # Negative task size
        
        with pytest.raises(ValueError):
            estimate_comm_time(1024, -20.0, 50.0, 20.0)  # Negative bandwidth
        
        with pytest.raises(ValueError):
            estimate_comm_time(1024, 20.0, 50.0, -20.0)  # Negative RTT
    
    def test_robot_energy_local_execution(self):
        """Test robot energy estimation for local execution."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024*1024,
            compute_demand=1000000.0,
            created_at=0.0
        )
        
        power_params = PowerParameters(
            active_local_mw=2000.0,  # 2W
            tx_mw=800.0,
            rx_mw=400.0
        )
        
        # Local execution: 1 second at 2W = 2Wh / 3600 = 0.000556 Wh
        local_time_s = 1.0
        energy_wh = estimate_robot_energy(
            task, Site.LOCAL, power_params, local_time_s
        )
        
        expected_wh = (2000.0 / 1000.0) * (1.0 / 3600.0)  # 2W * (1s / 3600s/h)
        assert abs(energy_wh - expected_wh) < 1e-6
    
    def test_robot_energy_remote_execution(self):
        """Test robot energy estimation for remote execution."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024*1024,
            compute_demand=1000000.0,
            created_at=0.0
        )
        
        power_params = PowerParameters(
            active_local_mw=2000.0,
            tx_mw=800.0,   # 0.8W
            rx_mw=400.0    # 0.4W
        )
        
        comm_times = ComputationTimes(
            uplink_s=0.1,      # 0.1s upload
            downlink_s=0.05,   # 0.05s download  
            total_comm_s=0.15  # Total 0.15s
        )
        
        # Remote execution: no local computation, only communication
        energy_wh = estimate_robot_energy(
            task, Site.EDGE, power_params, 0.0, comm_times
        )
        
        # Expected: 0.8W * 0.1s + 0.4W * 0.05s = 0.08 + 0.02 = 0.1 Wh (converted to hours)
        uplink_wh = (800.0 / 1000.0) * (0.1 / 3600.0)
        downlink_wh = (400.0 / 1000.0) * (0.05 / 3600.0)
        expected_wh = uplink_wh + downlink_wh
        
        assert abs(energy_wh - expected_wh) < 1e-6
    
    def test_robot_energy_missing_comm_times(self):
        """Test that remote execution without comm_times raises error."""
        task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
        power_params = PowerParameters(2000.0, 800.0, 400.0)
        
        with pytest.raises(ValueError):
            estimate_robot_energy(task, Site.EDGE, power_params, 0.0)
    
    def test_energy_breakdown(self):
        """Test detailed energy breakdown functionality."""
        task = Task(1, TaskType.GENERIC, 1024*1024, 1000000.0, 0.0)
        power_params = PowerParameters(2000.0, 800.0, 400.0)
        
        # Local execution breakdown
        breakdown_local = get_execution_energy_breakdown(
            task, Site.LOCAL, power_params, 1.0
        )
        
        assert breakdown_local["local_computation"] > 0
        assert breakdown_local["communication"] == 0.0
        assert breakdown_local["uplink"] == 0.0
        assert breakdown_local["downlink"] == 0.0
        assert breakdown_local["total"] == breakdown_local["local_computation"]
        
        # Remote execution breakdown
        comm_times = ComputationTimes(0.1, 0.05, 0.15)
        breakdown_remote = get_execution_energy_breakdown(
            task, Site.EDGE, power_params, 0.0, comm_times
        )
        
        assert breakdown_remote["local_computation"] == 0.0
        assert breakdown_remote["communication"] > 0.0
        assert breakdown_remote["uplink"] > 0.0
        assert breakdown_remote["downlink"] > 0.0
        assert breakdown_remote["total"] == breakdown_remote["communication"]


class TestAcceptanceCriteria:
    """Test specific acceptance criteria scenarios."""
    
    def test_acceptance_criteria_generic_task(self):
        """Test acceptance criteria: GENERIC task with specified parameters."""
        # Create task: size=10MB, compute_demand=1e9, 20Mbps up, 50Mbps down, 20ms RTT
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=10*1024*1024,  # 10MB
            compute_demand=1e9,       # 1 billion operations
            created_at=0.0
        )
        
        power_params = PowerParameters(
            active_local_mw=2000.0,
            tx_mw=800.0,
            rx_mw=400.0
        )
        
        # Communication times for Edge/Cloud
        comm_times = estimate_comm_time(
            task_size_bytes=10*1024*1024,
            bandwidth_up_mbps=20.0,
            bandwidth_down_mbps=50.0,
            rtt_ms=20.0
        )
        
        # Local execution energy (computation only)
        local_compute_time_s = estimate_local_compute_time(task, 1000000.0)  # 1000s
        energy_local = estimate_robot_energy(
            task, Site.LOCAL, power_params, local_compute_time_s
        )
        
        # Edge execution energy (communication only)
        energy_edge = estimate_robot_energy(
            task, Site.EDGE, power_params, 0.0, comm_times
        )
        
        # Cloud execution energy (communication only)  
        energy_cloud = estimate_robot_energy(
            task, Site.CLOUD, power_params, 0.0, comm_times
        )
        
        # Acceptance criteria validation
        # 1. Edge/Cloud communication energy > 0
        assert energy_edge > 0, "Edge execution should have communication energy > 0"
        assert energy_cloud > 0, "Cloud execution should have communication energy > 0"
        
        # 2. Local execution communication energy ≈ 0 (only computation energy)
        breakdown_local = get_execution_energy_breakdown(
            task, Site.LOCAL, power_params, local_compute_time_s
        )
        assert breakdown_local["communication"] == 0.0, "Local execution should have no communication energy"
        
        # 3. Verify energy values are reasonable
        assert energy_local > 0, "Local execution energy should be > 0"
        assert energy_edge == energy_cloud, "Edge and Cloud communication energy should be equal"
        
        print(f"Local energy: {energy_local:.6f} Wh")
        print(f"Edge energy: {energy_edge:.6f} Wh") 
        print(f"Cloud energy: {energy_cloud:.6f} Wh")
        print(f"Communication time: {comm_times.total_comm_s:.3f}s")
    
    def test_battery_soc_decrease(self):
        """Test that battery SoC correctly decreases after energy consumption."""
        battery = Battery(capacity_wh=18.5, initial_soc=100.0)  # Realistic phone battery
        initial_soc = battery.get_soc()
        
        # Consume some energy
        energy_consumed_wh = 1.85  # 10% of capacity
        battery.consume_energy_wh(energy_consumed_wh, "test_task")
        
        final_soc = battery.get_soc()
        
        # Acceptance criteria validation
        # 1. SoC should decrease
        assert final_soc < initial_soc, "SoC should decrease after energy consumption"
        
        # 2. SoC should be in valid range 0-100%
        assert 0 <= final_soc <= 100, f"SoC should be 0-100%, got {final_soc}%"
        
        # 3. SoC decrease should match energy consumed
        expected_decrease = (energy_consumed_wh / battery.capacity_wh) * 100
        actual_decrease = initial_soc - final_soc
        assert abs(actual_decrease - expected_decrease) < 0.01, \
            f"SoC decrease {actual_decrease}% should match expected {expected_decrease}%"
        
        print(f"Initial SoC: {initial_soc}%")
        print(f"Final SoC: {final_soc}%")
        print(f"Energy consumed: {energy_consumed_wh} Wh")
        print(f"SoC decrease: {actual_decrease}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])