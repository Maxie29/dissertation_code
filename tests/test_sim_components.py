"""
Tests for SimPy simulation components.

Validates ResourceStation and Network classes according to requirements
and acceptance criteria.
"""

import pytest
import simpy
from src.battery_offloading.sim.resources import ResourceStation, ProcessingRecord, create_stations_from_config
from src.battery_offloading.sim.network import Network, TransmissionResult, create_networks_from_config, validate_network_parameters
from src.battery_offloading.task import Task
from src.battery_offloading.enums import TaskType, Site
from src.battery_offloading.config import Config


class TestResourceStation:
    """Test ResourceStation simulation functionality."""
    
    def test_resource_station_initialization(self):
        """Test resource station creation and basic properties."""
        env = simpy.Environment()
        station = ResourceStation(env, Site.EDGE, 5000000.0, capacity=1)
        
        assert station.name == Site.EDGE
        assert station.service_rate == 5000000.0
        assert station.capacity == 1
        assert isinstance(station.resource, simpy.Resource)
        assert station.get_queue_length() == 0
    
    def test_resource_station_invalid_parameters(self):
        """Test resource station with invalid parameters."""
        env = simpy.Environment()
        
        with pytest.raises(ValueError):
            ResourceStation(env, Site.LOCAL, -1000.0)  # Negative service rate
        
        with pytest.raises(ValueError):
            ResourceStation(env, Site.LOCAL, 1000.0, capacity=0)  # Invalid capacity
    
    def test_service_time_calculation(self):
        """Test service time calculation based on compute demand."""
        env = simpy.Environment()
        station = ResourceStation(env, Site.LOCAL, 2000000.0)  # 2M ops/sec
        
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024,
            compute_demand=4000000.0,  # 4M operations
            created_at=0.0
        )
        
        service_time = station.calculate_service_time(task)
        assert service_time == 2.0  # 4M ops / 2M ops/sec = 2 seconds
    
    def test_single_task_processing(self):
        """Test processing a single task through resource station."""
        env = simpy.Environment()
        station = ResourceStation(env, Site.EDGE, 1000000.0)  # 1M ops/sec
        
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024,
            compute_demand=3000000.0,  # 3M operations -> 3 seconds
            created_at=0.0
        )
        
        def run_task():
            finish_time, service_time = yield from station.process(task)
            assert service_time == 3.0
            assert finish_time == 3.0  # No queue wait for first task
            return finish_time, service_time
        
        env.process(run_task())
        env.run()
        
        # Check statistics
        stats = station.get_utilization_stats()
        assert stats['total_tasks'] == 1
        assert stats['avg_service_time'] == 3.0
        assert stats['avg_queue_time'] == 0.0
    
    def test_multiple_tasks_fifo_queuing(self):
        """Test FIFO queuing behavior with multiple tasks."""
        env = simpy.Environment()
        station = ResourceStation(env, Site.LOCAL, 1000000.0, capacity=1)
        
        tasks = [
            Task(i, TaskType.GENERIC, 1024, 1000000.0, 0.0) for i in range(1, 4)
        ]  # Each task takes 1 second
        
        results = []
        
        def process_task(task):
            finish_time, service_time = yield from station.process(task)
            results.append((task.id, finish_time, service_time))
        
        # Submit all tasks at time 0
        for task in tasks:
            env.process(process_task(task))
        
        env.run()
        
        # Check FIFO ordering: tasks should finish at 1s, 2s, 3s
        assert len(results) == 3
        results.sort(key=lambda x: x[0])  # Sort by task ID
        
        assert results[0] == (1, 1.0, 1.0)  # First task: no wait
        assert results[1] == (2, 2.0, 1.0)  # Second task: 1s wait + 1s service
        assert results[2] == (3, 3.0, 1.0)  # Third task: 2s wait + 1s service
        
        # Check queue statistics
        history = station.get_processing_history()
        assert len(history) == 3
        assert history[0].queue_wait_time == 0.0
        assert history[1].queue_wait_time == 1.0
        assert history[2].queue_wait_time == 2.0
    
    def test_higher_service_rate_faster_processing(self):
        """Test acceptance criteria: higher service rate results in faster processing."""
        env = simpy.Environment()
        
        # Create stations with different service rates
        local_station = ResourceStation(env, Site.LOCAL, 1000000.0)   # 1M ops/sec
        edge_station = ResourceStation(env, Site.EDGE, 5000000.0)     # 5M ops/sec (faster)
        
        task = Task(
            id=1,
            type=TaskType.GENERIC,
            size_bytes=1024,
            compute_demand=5000000.0,  # 5M operations
            created_at=0.0
        )
        
        # Calculate service times
        local_time = local_station.calculate_service_time(task)
        edge_time = edge_station.calculate_service_time(task)
        
        # Edge should be faster (5M ops / 5M ops/sec = 1s vs 5M ops / 1M ops/sec = 5s)
        assert edge_time < local_time
        assert edge_time == 1.0
        assert local_time == 5.0
    
    def test_station_utilization_stats(self):
        """Test station utilization statistics calculation."""
        env = simpy.Environment()
        station = ResourceStation(env, Site.CLOUD, 2000000.0)
        
        tasks = [
            Task(i, TaskType.GENERIC, 1024, 1000000.0, 0.0) for i in range(1, 3)
        ]  # Each task takes 0.5 seconds
        
        def process_tasks():
            for task in tasks:
                yield from station.process(task)
        
        env.process(process_tasks())
        env.run()
        
        stats = station.get_utilization_stats()
        assert stats['total_tasks'] == 2
        assert stats['total_service_time'] == 1.0  # 2 tasks * 0.5s each
        assert stats['utilization'] == 1.0  # 1s service time / 1s total time
    
    def test_station_reset_stats(self):
        """Test resetting station statistics."""
        env = simpy.Environment()
        station = ResourceStation(env, Site.LOCAL, 1000000.0)
        
        task = Task(1, TaskType.GENERIC, 1024, 500000.0, 0.0)
        
        def process_task():
            yield from station.process(task)
        
        env.process(process_task())
        env.run()
        
        # Verify stats exist
        assert station.get_utilization_stats()['total_tasks'] == 1
        
        # Reset and verify cleared
        station.reset_stats()
        assert station.get_utilization_stats()['total_tasks'] == 0
        assert len(station.get_processing_history()) == 0


class TestNetwork:
    """Test Network communication modeling."""
    
    def test_network_initialization(self):
        """Test network creation with valid parameters."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=20.0, jitter_ms=5.0)
        
        assert network.bw_up_mbps == 20.0
        assert network.bw_down_mbps == 50.0
        assert network.rtt_ms == 20.0
        assert network.jitter_ms == 5.0
    
    def test_network_invalid_parameters(self):
        """Test network initialization with invalid parameters."""
        with pytest.raises(ValueError):
            Network(-20.0, 50.0, 20.0)  # Negative uplink bandwidth
        
        with pytest.raises(ValueError):
            Network(20.0, -50.0, 20.0)  # Negative downlink bandwidth
        
        with pytest.raises(ValueError):
            Network(20.0, 50.0, -20.0)  # Negative RTT
        
        with pytest.raises(ValueError):
            Network(20.0, 50.0, 20.0, -5.0)  # Negative jitter
    
    def test_uplink_time_calculation(self):
        """Test uplink transmission time calculation."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=20.0, jitter_ms=0.0)
        
        # Test 10MB upload
        data_size = 10 * 1024 * 1024  # 10MB in bytes
        result = network.uplink_time(data_size)
        
        # 10MB = 80 Mb, at 20 Mbps = 4 seconds pure transmission
        expected_transmission_time = 4.194304  # Exact: 10*1024*1024 / (20*125000)
        expected_latency = 0.01  # 10ms (half RTT)
        expected_total = expected_transmission_time + expected_latency
        
        assert abs(result.pure_transmission_time - expected_transmission_time) < 0.000001
        assert abs(result.latency_overhead - expected_latency) < 0.000001
        assert abs(result.total_time - expected_total) < 0.000001
    
    def test_downlink_time_calculation(self):
        """Test downlink transmission time calculation."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=20.0, jitter_ms=0.0)
        
        # Test 1MB download
        data_size = 1 * 1024 * 1024  # 1MB in bytes
        result = network.downlink_time(data_size)
        
        # 1MB = 8 Mb, at 50 Mbps = 0.16 seconds pure transmission
        expected_transmission_time = 0.16777216  # Exact: 1*1024*1024 / (50*125000)
        expected_latency = 0.01  # 10ms (half RTT)
        expected_total = expected_transmission_time + expected_latency
        
        assert abs(result.pure_transmission_time - expected_transmission_time) < 0.000001
        assert abs(result.latency_overhead - expected_latency) < 0.000001
        assert abs(result.total_time - expected_total) < 0.000001
    
    def test_acceptance_criteria_10mb_upload(self):
        """Test acceptance criteria: 10MB at 20Mbps should be ~4s including RTT."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=20.0, jitter_ms=0.0)
        
        # 10MB upload as specified in acceptance criteria
        data_size = 10 * 1024 * 1024  # 10MB
        result = network.uplink_time(data_size)
        
        # Pure transmission: 10MB = 83,886,080 bits / 20,000,000 bps = ~4.194s
        # With 10ms latency overhead, total should be ~4.204s
        assert result.pure_transmission_time > 4.19  # Close to 4.194s
        assert result.pure_transmission_time < 4.20
        assert result.total_time > 4.20  # Should include RTT
        assert result.total_time < 4.21
        
        print(f"10MB upload time: {result.total_time:.3f}s (pure: {result.pure_transmission_time:.3f}s)")
    
    def test_total_time_calculation(self):
        """Test bidirectional communication time calculation."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=20.0)
        
        up_time, down_time, total = network.total_time(
            up_bytes=10*1024*1024,  # 10MB upload
            down_bytes=1*1024*1024   # 1MB download  
        )
        
        assert up_time > 0
        assert down_time > 0
        assert total == up_time + down_time
        assert up_time > down_time  # Upload should take longer (lower bandwidth)
    
    def test_effective_bandwidth_calculation(self):
        """Test effective bandwidth with latency overhead."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=100.0)  # High latency
        
        # Large file should approach nominal bandwidth
        large_file = 100 * 1024 * 1024  # 100MB
        eff_bw_up = network.get_effective_bandwidth(large_file, "up")
        eff_bw_down = network.get_effective_bandwidth(large_file, "down")
        
        # Should be close to but less than nominal due to latency overhead
        assert eff_bw_up < 20.0
        assert eff_bw_up > 19.0  # Should be close to 20.0 for large files
        assert eff_bw_down < 50.0
        assert eff_bw_down > 49.0
    
    def test_file_transfer_estimation(self):
        """Test detailed file transfer time estimation."""
        network = Network(bw_up_mbps=25.0, bw_down_mbps=100.0, rtt_ms=30.0, jitter_ms=10.0)
        
        breakdown = network.estimate_file_transfer_time(5.0, "up", include_handshake=True)
        
        assert breakdown["file_size_mb"] == 5.0
        assert breakdown["direction"] == "up"
        assert breakdown["total_time"] > breakdown["pure_transmission_time"]
        assert breakdown["handshake_time"] > 0
        assert "effective_bandwidth_mbps" in breakdown
    
    def test_negative_bytes_error(self):
        """Test error handling for negative byte values."""
        network = Network(20.0, 50.0, 20.0)
        
        with pytest.raises(ValueError):
            network.uplink_time(-1024)
        
        with pytest.raises(ValueError):
            network.downlink_time(-1024)


class TestConfigurationIntegration:
    """Test integration with configuration system."""
    
    def test_create_stations_from_config(self):
        """Test creating resource stations from configuration."""
        env = simpy.Environment()
        
        # Load baseline configuration
        config = Config.from_yaml('configs/baseline.yaml')
        stations = create_stations_from_config(env, config)
        
        assert Site.LOCAL in stations
        assert Site.EDGE in stations
        assert Site.CLOUD in stations
        
        # Verify service rates match config
        assert stations[Site.LOCAL].service_rate == config.local_service.processing_rate_ops_per_sec
        assert stations[Site.EDGE].service_rate == config.edge_service.processing_rate_ops_per_sec
        assert stations[Site.CLOUD].service_rate == config.cloud_service.processing_rate_ops_per_sec
    
    def test_create_networks_from_config(self):
        """Test creating network configurations from config."""
        config = Config.from_yaml('configs/baseline.yaml')
        networks = create_networks_from_config(config)
        
        assert "edge" in networks
        assert "cloud" in networks
        
        # Verify network parameters
        edge_net = networks["edge"]
        cloud_net = networks["cloud"]
        
        assert edge_net.bw_up_mbps == config.edge_network.bandwidth_mbps
        assert cloud_net.bw_up_mbps == config.cloud_network.bandwidth_mbps


class TestAcceptanceCriteria:
    """Test specific acceptance criteria."""
    
    def test_higher_service_rate_faster_processing(self):
        """Test that higher service rate results in faster processing."""
        env = simpy.Environment()
        
        # Create stations representing Local vs Edge (Edge should be faster)
        local_station = ResourceStation(env, Site.LOCAL, 1000000.0)   # 1M ops/sec
        edge_station = ResourceStation(env, Site.EDGE, 5000000.0)     # 5M ops/sec
        
        # Same task on both stations
        task = Task(1, TaskType.GENERIC, 1024, 3000000.0, 0.0)  # 3M operations
        
        local_time = local_station.calculate_service_time(task)
        edge_time = edge_station.calculate_service_time(task)
        
        # Edge should be faster: 3M/5M = 0.6s vs 3M/1M = 3.0s
        assert edge_time < local_time
        assert edge_time == 0.6
        assert local_time == 3.0
        
        print(f"Local processing time: {local_time}s")
        print(f"Edge processing time: {edge_time}s")
        print(f"Edge speedup: {local_time/edge_time:.1f}x")
    
    def test_10mb_20mbps_transmission_time(self):
        """Test acceptance criteria: 10MB at 20Mbps takes ~4s including RTT."""
        network = Network(bw_up_mbps=20.0, bw_down_mbps=50.0, rtt_ms=20.0)
        
        # Test exactly as specified in acceptance criteria
        result = network.uplink_time(10 * 1024 * 1024)  # 10MB
        
        # Should be approximately 4s for pure transmission + RTT overhead
        theoretical_time = (10 * 1024 * 1024 * 8) / (20 * 1000000)  # bits / bps
        
        assert abs(result.pure_transmission_time - theoretical_time) < 0.01
        assert result.total_time > theoretical_time  # Should include RTT
        assert result.total_time < theoretical_time + 0.1  # RTT should be small
        
        print(f"10MB upload theoretical: {theoretical_time:.3f}s")
        print(f"10MB upload with RTT: {result.total_time:.3f}s")
        print(f"RTT overhead: {result.latency_overhead:.3f}s")


class TestNetworkValidation:
    """Test network parameter validation."""
    
    def test_parameter_validation_valid(self):
        """Test validation with valid parameters."""
        result = validate_network_parameters(20.0, 50.0, 30.0)
        
        assert result["valid_bandwidth"] is True
        assert result["valid_latency"] is True
        assert result["realistic_asymmetry"] is True
        assert len(result["warnings"]) == 0
    
    def test_parameter_validation_invalid(self):
        """Test validation with invalid parameters."""
        result = validate_network_parameters(-20.0, 50.0, -10.0)
        
        assert result["valid_bandwidth"] is False
        assert result["valid_latency"] is False
        assert len(result["warnings"]) >= 2
    
    def test_parameter_validation_warnings(self):
        """Test validation warnings for unrealistic values."""
        result = validate_network_parameters(100.0, 50.0, 2000.0)  # Uplink > downlink, high RTT
        
        assert result["realistic_asymmetry"] is False
        assert any("RTT" in warning for warning in result["warnings"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])