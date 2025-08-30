"""
Comprehensive energy tests covering communication costs and timing calculations.

Acceptance Criteria:
- Local execution: NO communication energy cost
- Edge/Cloud execution: HAS communication energy cost  
- 10MB@20Mbps uplink timing: approximately 4s (within ±10% tolerance)
- Accurate power consumption modeling for TX/RX operations
- Communication time estimation accuracy
"""

import pytest
import math
from src.battery_offloading.energy import (
    PowerParameters, ComputationTimes,
    estimate_local_compute_time, estimate_remote_compute_time,
    estimate_comm_time, estimate_robot_energy,
    get_execution_energy_breakdown
)
from src.battery_offloading.task import Task
from src.battery_offloading.enums import TaskType, Site


class TestLocalExecutionNoCommunication:
    """Test that local execution has NO communication energy costs."""
    
    def test_local_execution_zero_communication_energy(self):
        """Test that local execution results in zero communication energy."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=10 * 1024 * 1024,  # 10MB task
            compute_demand=5_000_000.0,   # 5M operations
            created_at=0.0
        )
        
        power_params = PowerParameters(
            active_local_mw=2000.0,  # 2W for local computation
            tx_mw=800.0,             # 800mW for transmission (should not be used)
            rx_mw=400.0,             # 400mW for reception (should not be used)
            idle_mw=150.0
        )
        
        # Local computation time: 5M ops / 1M ops/s = 5 seconds
        local_compute_time_s = estimate_local_compute_time(task, 1_000_000.0)
        assert local_compute_time_s == 5.0
        
        # Calculate local execution energy
        energy_wh = estimate_robot_energy(
            task, Site.LOCAL, power_params, local_compute_time_s
        )
        
        # Should only consume local computation energy
        # 2000mW * 5s = 10000mWs = 10Ws = 10/3600 Wh ≈ 0.00278 Wh
        expected_energy_wh = (2000.0 / 1000.0) * (5.0 / 3600.0)
        assert abs(energy_wh - expected_energy_wh) < 1e-10, \
            f"Local energy should be {expected_energy_wh:.6f} Wh, got {energy_wh:.6f} Wh"
    
    def test_local_execution_energy_breakdown_no_communication(self):
        """Test that local execution energy breakdown shows zero communication."""
        task = Task(1, TaskType.GENERIC, 1024*1024, 2_000_000.0, 0.0)  # 1MB, 2M ops
        power_params = PowerParameters(2500.0, 800.0, 400.0)
        
        local_compute_time_s = estimate_local_compute_time(task, 1_000_000.0)  # 2 seconds
        
        breakdown = get_execution_energy_breakdown(
            task, Site.LOCAL, power_params, local_compute_time_s
        )
        
        # Verify breakdown structure
        assert "local_computation" in breakdown
        assert "communication" in breakdown
        assert "uplink" in breakdown
        assert "downlink" in breakdown
        assert "total" in breakdown
        
        # Local execution should have ZERO communication energy
        assert breakdown["communication"] == 0.0, "Local execution should have zero communication energy"
        assert breakdown["uplink"] == 0.0, "Local execution should have zero uplink energy"
        assert breakdown["downlink"] == 0.0, "Local execution should have zero downlink energy"
        
        # Total should equal only local computation
        assert breakdown["total"] == breakdown["local_computation"], \
            "Total energy should equal local computation energy only"
        
        # Local computation should be positive
        assert breakdown["local_computation"] > 0, "Local computation energy should be positive"
    
    def test_local_various_task_sizes_no_communication(self):
        """Test that various task sizes in local execution never have communication costs."""
        power_params = PowerParameters(2000.0, 800.0, 400.0)
        
        # Test various task sizes
        task_sizes_mb = [0.1, 1.0, 10.0, 50.0, 100.0]
        
        for size_mb in task_sizes_mb:
            task = Task(
                id=1,
                type=TaskType.GENERIC,
                size_bytes=int(size_mb * 1024 * 1024),
                compute_demand=1_000_000.0,  # 1M ops
                created_at=0.0
            )
            
            local_compute_time_s = estimate_local_compute_time(task, 1_000_000.0)  # 1 second
            
            breakdown = get_execution_energy_breakdown(
                task, Site.LOCAL, power_params, local_compute_time_s
            )
            
            assert breakdown["communication"] == 0.0, \
                f"Task size {size_mb}MB should have zero communication energy in local execution"


class TestRemoteExecutionWithCommunication:
    """Test that Edge/Cloud execution HAS communication energy costs."""
    
    def test_edge_execution_has_communication_energy(self):
        """Test that edge execution results in positive communication energy."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=5 * 1024 * 1024,  # 5MB task
            compute_demand=1_000_000.0,   # 1M operations (irrelevant for edge)
            created_at=0.0
        )
        
        power_params = PowerParameters(
            active_local_mw=2000.0,
            tx_mw=800.0,   # 800mW for transmission
            rx_mw=400.0,   # 400mW for reception
            idle_mw=150.0
        )
        
        # Estimate communication times
        comm_times = estimate_comm_time(
            task_size_bytes=5 * 1024 * 1024,
            bandwidth_up_mbps=20.0,
            bandwidth_down_mbps=50.0,
            rtt_ms=20.0
        )
        
        # Calculate edge execution energy (no local computation)
        energy_wh = estimate_robot_energy(
            task, Site.EDGE, power_params, 0.0, comm_times
        )
        
        # Should have positive communication energy
        assert energy_wh > 0, "Edge execution should have positive communication energy"
        
        # Verify it's only communication energy
        breakdown = get_execution_energy_breakdown(
            task, Site.EDGE, power_params, 0.0, comm_times
        )
        
        assert breakdown["local_computation"] == 0.0, "Edge execution should have zero local computation"
        assert breakdown["communication"] > 0.0, "Edge execution should have positive communication energy"
        assert breakdown["uplink"] > 0.0, "Edge execution should have positive uplink energy"
        assert breakdown["downlink"] > 0.0, "Edge execution should have positive downlink energy"
        assert breakdown["total"] == breakdown["communication"], "Total should equal communication energy"
    
    def test_cloud_execution_has_communication_energy(self):
        """Test that cloud execution results in positive communication energy."""
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=8 * 1024 * 1024,  # 8MB task
            compute_demand=5_000_000.0,   # 5M operations (irrelevant for cloud)
            created_at=0.0
        )
        
        power_params = PowerParameters(
            active_local_mw=2500.0,
            tx_mw=900.0,   # 900mW for transmission
            rx_mw=450.0,   # 450mW for reception
            idle_mw=200.0
        )
        
        # Estimate communication times
        comm_times = estimate_comm_time(
            task_size_bytes=8 * 1024 * 1024,
            bandwidth_up_mbps=15.0,
            bandwidth_down_mbps=30.0,
            rtt_ms=100.0
        )
        
        # Calculate cloud execution energy (no local computation)
        energy_wh = estimate_robot_energy(
            task, Site.CLOUD, power_params, 0.0, comm_times
        )
        
        # Should have positive communication energy
        assert energy_wh > 0, "Cloud execution should have positive communication energy"
        
        # Verify energy breakdown
        breakdown = get_execution_energy_breakdown(
            task, Site.CLOUD, power_params, 0.0, comm_times
        )
        
        assert breakdown["local_computation"] == 0.0, "Cloud execution should have zero local computation"
        assert breakdown["communication"] > 0.0, "Cloud execution should have positive communication energy"
        assert breakdown["uplink"] > 0.0, "Cloud execution should have positive uplink energy"  
        assert breakdown["downlink"] > 0.0, "Cloud execution should have positive downlink energy"
        assert breakdown["total"] == breakdown["communication"], "Total should equal communication energy"
    
    def test_remote_execution_communication_components(self):
        """Test that remote execution communication has both uplink and downlink components."""
        task = Task(1, TaskType.GENERIC, 2 * 1024 * 1024, 1_000_000.0, 0.0)  # 2MB task
        power_params = PowerParameters(2000.0, 800.0, 400.0)
        
        comm_times = estimate_comm_time(
            task_size_bytes=2 * 1024 * 1024,
            bandwidth_up_mbps=25.0,
            bandwidth_down_mbps=50.0,
            rtt_ms=30.0
        )
        
        for site in [Site.EDGE, Site.CLOUD]:
            breakdown = get_execution_energy_breakdown(
                task, site, power_params, 0.0, comm_times
            )
            
            # Both uplink and downlink should contribute to communication energy
            assert breakdown["uplink"] > 0, f"{site.value} execution should have uplink energy"
            assert breakdown["downlink"] > 0, f"{site.value} execution should have downlink energy"
            
            # Communication should be sum of uplink and downlink
            expected_comm = breakdown["uplink"] + breakdown["downlink"]
            assert abs(breakdown["communication"] - expected_comm) < 1e-10, \
                f"Communication energy should equal uplink + downlink for {site.value}"


class TestCommunicationTimingAccuracy:
    """Test communication timing calculations with specific acceptance criteria."""
    
    def test_10mb_20mbps_uplink_timing_acceptance_criteria(self):
        """Test that 10MB@20Mbps uplink takes approximately 4s (±10% tolerance)."""
        # Acceptance criteria: 10MB task, 20Mbps uplink should take ~4 seconds
        task_size_bytes = 10 * 1024 * 1024  # 10MB
        bandwidth_up_mbps = 20.0             # 20Mbps
        bandwidth_down_mbps = 50.0           # 50Mbps (for completeness)
        rtt_ms = 20.0                        # 20ms RTT
        
        comm_times = estimate_comm_time(
            task_size_bytes=task_size_bytes,
            bandwidth_up_mbps=bandwidth_up_mbps,
            bandwidth_down_mbps=bandwidth_down_mbps,
            rtt_ms=rtt_ms
        )
        
        # Calculate expected uplink time
        # 10MB = 10 * 1024 * 1024 bytes = 83,886,080 bits
        # 20Mbps = 20 * 1,000,000 bits/s
        # Time = 83,886,080 / 20,000,000 ≈ 4.19 seconds
        expected_uplink_time_s = (task_size_bytes * 8) / (bandwidth_up_mbps * 1_000_000)
        
        # Acceptance criteria: within ±10% tolerance of ~4 seconds
        tolerance = 0.10  # 10%
        expected_time = 4.0  # ~4 seconds as per acceptance criteria
        
        # The actual implementation adds RTT/2 + jitter to transmission time
        expected_with_overhead = expected_uplink_time_s + (rtt_ms / 1000.0) / 2
        assert abs(comm_times.uplink_s - expected_with_overhead) < 1e-6, \
            f"Calculated uplink time should match formula result with RTT overhead"
        
        # Check against acceptance criteria (4s ± 10%)
        lower_bound = expected_time * (1 - tolerance)  # 3.6s
        upper_bound = expected_time * (1 + tolerance)  # 4.4s
        
        assert lower_bound <= comm_times.uplink_s <= upper_bound, \
            f"10MB@20Mbps uplink should take ~4s (±10%), got {comm_times.uplink_s:.3f}s"
    
    def test_communication_timing_formula_accuracy(self):
        """Test that communication timing formulas are mathematically accurate."""
        test_cases = [
            # (size_mb, up_mbps, down_mbps, expected_up_s, expected_down_s_ratio)
            (1.0, 10.0, 20.0, 0.8, 0.1),     # 1MB: up=0.8s, down=0.1s (assuming 10% result size)
            (5.0, 25.0, 50.0, 1.6, 0.1),     # 5MB: up=1.6s, down=0.1s
            (2.0, 8.0, 40.0, 2.0, 0.05),     # 2MB: up=2.0s, down=0.05s
        ]
        
        for size_mb, up_mbps, down_mbps, expected_up_s, expected_down_s in test_cases:
            size_bytes = int(size_mb * 1024 * 1024)
            
            comm_times = estimate_comm_time(
                task_size_bytes=size_bytes,
                bandwidth_up_mbps=up_mbps,
                bandwidth_down_mbps=down_mbps,
                rtt_ms=10.0
            )
            
            # Calculate expected times manually
            size_bits = size_bytes * 8
            expected_uplink_s = size_bits / (up_mbps * 1_000_000)
            
            # The actual implementation adds RTT/2 to transmission time
            expected_uplink_with_overhead = expected_uplink_s + (10.0 / 1000.0) / 2  # RTT=10ms
            assert abs(comm_times.uplink_s - expected_uplink_with_overhead) < 1e-6, \
                f"Uplink time calculation incorrect for {size_mb}MB@{up_mbps}Mbps (with RTT overhead)"
            
            # Verify times are positive and reasonable
            assert comm_times.uplink_s > 0, "Uplink time should be positive"
            assert comm_times.downlink_s > 0, "Downlink time should be positive"
            assert comm_times.total_comm_s == comm_times.uplink_s + comm_times.downlink_s, \
                "Total communication time should equal uplink + downlink"
    
    def test_communication_timing_edge_cases(self):
        """Test communication timing with edge cases and boundary conditions."""
        # Very small task
        comm_times_small = estimate_comm_time(
            task_size_bytes=1024,  # 1KB
            bandwidth_up_mbps=100.0,
            bandwidth_down_mbps=100.0,
            rtt_ms=1.0
        )
        
        assert comm_times_small.uplink_s > 0, "Small task should have positive uplink time"
        assert comm_times_small.downlink_s > 0, "Small task should have positive downlink time"
        assert comm_times_small.uplink_s < 0.001, "1KB@100Mbps should be very fast"
        
        # Very large task
        comm_times_large = estimate_comm_time(
            task_size_bytes=100 * 1024 * 1024,  # 100MB
            bandwidth_up_mbps=10.0,
            bandwidth_down_mbps=10.0,
            rtt_ms=50.0
        )
        
        assert comm_times_large.uplink_s > 10.0, "100MB@10Mbps should take significant time"
        assert comm_times_large.total_comm_s > comm_times_large.uplink_s, \
            "Total time should include downlink"
        
        # High bandwidth scenario
        comm_times_fast = estimate_comm_time(
            task_size_bytes=10 * 1024 * 1024,  # 10MB
            bandwidth_up_mbps=1000.0,  # 1Gbps
            bandwidth_down_mbps=1000.0,
            rtt_ms=5.0
        )
        
        assert comm_times_fast.uplink_s < 1.0, "High bandwidth should result in fast transfer"
        assert comm_times_fast.total_comm_s < 2.0, "High bandwidth total should be fast"


class TestPowerConsumptionModeling:
    """Test accurate power consumption modeling for TX/RX operations."""
    
    def test_uplink_downlink_power_consumption_accuracy(self):
        """Test that uplink/downlink power consumption is calculated accurately."""
        task = Task(1, TaskType.GENERIC, 4 * 1024 * 1024, 1_000_000.0, 0.0)  # 4MB
        
        power_params = PowerParameters(
            active_local_mw=2000.0,
            tx_mw=800.0,   # 0.8W transmission
            rx_mw=400.0,   # 0.4W reception
            idle_mw=150.0
        )
        
        comm_times = estimate_comm_time(
            task_size_bytes=4 * 1024 * 1024,
            bandwidth_up_mbps=16.0,  # 16Mbps up
            bandwidth_down_mbps=32.0, # 32Mbps down
            rtt_ms=25.0
        )
        
        breakdown = get_execution_energy_breakdown(
            task, Site.EDGE, power_params, 0.0, comm_times
        )
        
        # Calculate expected energies manually
        # Uplink: tx_mw * uplink_time_s / (1000 * 3600) [convert mW*s to Wh]
        expected_uplink_wh = (power_params.tx_mw / 1000.0) * (comm_times.uplink_s / 3600.0)
        expected_downlink_wh = (power_params.rx_mw / 1000.0) * (comm_times.downlink_s / 3600.0)
        
        assert abs(breakdown["uplink"] - expected_uplink_wh) < 1e-10, \
            f"Uplink energy should be {expected_uplink_wh:.6f} Wh, got {breakdown['uplink']:.6f} Wh"
        
        assert abs(breakdown["downlink"] - expected_downlink_wh) < 1e-10, \
            f"Downlink energy should be {expected_downlink_wh:.6f} Wh, got {breakdown['downlink']:.6f} Wh"
    
    def test_power_parameter_scaling(self):
        """Test that energy consumption scales correctly with power parameters."""
        task = Task(1, TaskType.GENERIC, 1024 * 1024, 1_000_000.0, 0.0)  # 1MB
        
        comm_times = ComputationTimes(
            uplink_s=0.5,    # Fixed 0.5s uplink
            downlink_s=0.1,  # Fixed 0.1s downlink
            total_comm_s=0.6
        )
        
        # Test different power parameters
        power_configs = [
            (400.0, 200.0),   # Low power
            (800.0, 400.0),   # Medium power (double)
            (1200.0, 600.0),  # High power (triple)
        ]
        
        base_energy = None
        
        for tx_mw, rx_mw in power_configs:
            power_params = PowerParameters(2000.0, tx_mw, rx_mw)
            
            breakdown = get_execution_energy_breakdown(
                task, Site.EDGE, power_params, 0.0, comm_times
            )
            
            if base_energy is None:
                base_energy = breakdown["communication"]
            else:
                # Energy should scale proportionally with power
                ratio = (tx_mw + rx_mw) / (400.0 + 200.0)  # Relative to first config
                expected_energy = base_energy * ratio
                
                assert abs(breakdown["communication"] - expected_energy) < 1e-8, \
                    f"Energy should scale with power parameters"
    
    def test_time_energy_relationship(self):
        """Test that energy consumption scales correctly with communication time."""
        task = Task(1, TaskType.GENERIC, 1024 * 1024, 1_000_000.0, 0.0)
        power_params = PowerParameters(2000.0, 800.0, 400.0)
        
        # Test with different time scenarios
        time_configs = [
            (0.1, 0.05),  # Fast connection
            (0.5, 0.1),   # Medium connection
            (1.0, 0.2),   # Slow connection
        ]
        
        for uplink_s, downlink_s in time_configs:
            comm_times = ComputationTimes(
                uplink_s=uplink_s,
                downlink_s=downlink_s,
                total_comm_s=uplink_s + downlink_s
            )
            
            breakdown = get_execution_energy_breakdown(
                task, Site.EDGE, power_params, 0.0, comm_times
            )
            
            # Verify energy scales with time
            expected_uplink_wh = (800.0 / 1000.0) * (uplink_s / 3600.0)
            expected_downlink_wh = (400.0 / 1000.0) * (downlink_s / 3600.0)
            
            assert abs(breakdown["uplink"] - expected_uplink_wh) < 1e-10
            assert abs(breakdown["downlink"] - expected_downlink_wh) < 1e-10


class TestEnergyEstimationEdgeCases:
    """Test energy estimation edge cases and error handling."""
    
    def test_remote_execution_without_comm_times_error(self):
        """Test that remote execution without communication times raises appropriate error."""
        task = Task(1, TaskType.GENERIC, 1024, 1_000_000.0, 0.0)
        power_params = PowerParameters(2000.0, 800.0, 400.0)
        
        # Should raise error for Edge execution without comm_times
        with pytest.raises(ValueError, match="Communication times required"):
            estimate_robot_energy(task, Site.EDGE, power_params, 0.0)
        
        # Should raise error for Cloud execution without comm_times
        with pytest.raises(ValueError, match="Communication times required"):
            estimate_robot_energy(task, Site.CLOUD, power_params, 0.0)
    
    def test_invalid_communication_parameters(self):
        """Test that invalid communication parameters raise appropriate errors."""
        # Negative task size
        with pytest.raises(ValueError, match="Task size cannot be negative"):
            estimate_comm_time(-1024, 20.0, 50.0, 20.0)
        
        # Zero bandwidth
        with pytest.raises(ValueError, match="Uplink bandwidth must be positive"):
            estimate_comm_time(1024, 0.0, 50.0, 20.0)
        
        with pytest.raises(ValueError, match="Downlink bandwidth must be positive"):
            estimate_comm_time(1024, 20.0, 0.0, 20.0)
        
        # Negative RTT
        with pytest.raises(ValueError, match="RTT cannot be negative"):
            estimate_comm_time(1024, 20.0, 50.0, -10.0)
    
    def test_zero_size_task_communication(self):
        """Test communication estimation with zero-size task."""
        comm_times = estimate_comm_time(
            task_size_bytes=0,
            bandwidth_up_mbps=20.0,
            bandwidth_down_mbps=50.0,
            rtt_ms=20.0
        )
        
        # Should still have some time due to protocol overhead/RTT
        assert comm_times.uplink_s >= 0, "Zero-size task should have non-negative uplink time"
        assert comm_times.downlink_s >= 0, "Zero-size task should have non-negative downlink time"
        assert comm_times.total_comm_s >= 0, "Zero-size task should have non-negative total time"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])