"""
Comprehensive battery tests covering energy consumption, SoC updates,
and boundary protection (0% and 100% boundaries).

Acceptance Criteria:
- Energy consumption properly deducts from battery capacity
- SoC updates correctly reflect energy consumption
- 0% boundary protection (cannot go below 0%)
- 100% boundary protection (cannot go above 100%)
- Energy accounting accuracy and conservation
"""

import pytest
from battery_offloading.battery import Battery, EnergyConsumptionRecord


class TestBatteryInitializationAndValidation:
    """Test battery initialization with comprehensive parameter validation."""
    
    def test_valid_battery_initialization(self):
        """Test battery initialization with valid parameters."""
        battery = Battery(capacity_wh=100.0, initial_soc=80.0)
        
        assert battery.capacity_wh == 100.0
        assert battery.get_soc() == 80.0
        assert battery.get_remaining_energy_wh() == 80.0  # 80% of 100Wh
        assert battery.get_total_consumed_wh() == 0.0
        assert len(battery.get_consumption_history()) == 0
    
    def test_edge_case_initialization_parameters(self):
        """Test battery initialization with edge case parameters."""
        # Minimum valid values
        battery_min = Battery(capacity_wh=0.1, initial_soc=0.0)
        assert battery_min.capacity_wh == 0.1
        assert battery_min.get_soc() == 0.0
        
        # Maximum valid values
        battery_max = Battery(capacity_wh=1000.0, initial_soc=100.0)
        assert battery_max.capacity_wh == 1000.0
        assert battery_max.get_soc() == 100.0
        
        # Realistic phone battery
        battery_phone = Battery(capacity_wh=18.5, initial_soc=85.0)
        assert battery_phone.capacity_wh == 18.5
        assert battery_phone.get_soc() == 85.0
    
    def test_invalid_capacity_parameters(self):
        """Test that invalid capacity parameters raise ValueError."""
        # Negative capacity
        with pytest.raises(ValueError, match="Battery capacity must be positive"):
            Battery(capacity_wh=-10.0, initial_soc=50.0)
        
        # Zero capacity
        with pytest.raises(ValueError, match="Battery capacity must be positive"):
            Battery(capacity_wh=0.0, initial_soc=50.0)
    
    def test_invalid_soc_parameters(self):
        """Test that invalid SoC parameters raise ValueError."""
        # SoC below 0%
        with pytest.raises(ValueError, match="Initial SoC must be between 0-100%"):
            Battery(capacity_wh=100.0, initial_soc=-5.0)
        
        # SoC above 100%
        with pytest.raises(ValueError, match="Initial SoC must be between 0-100%"):
            Battery(capacity_wh=100.0, initial_soc=105.0)


class TestEnergyConsumptionAndSoCUpdates:
    """Test energy consumption and SoC update mechanisms."""
    
    def test_basic_energy_consumption(self):
        """Test basic energy consumption and SoC update."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # Consume 25 Wh (25% of capacity)
        battery.consume_energy_wh(25.0, "test_computation")
        
        assert battery.get_soc() == 75.0, "SoC should decrease by 25%"
        assert battery.get_remaining_energy_wh() == 75.0, "Remaining energy should be 75 Wh"
        assert battery.get_total_consumed_wh() == 25.0, "Total consumed should be 25 Wh"
    
    def test_multiple_energy_consumptions(self):
        """Test multiple sequential energy consumptions."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # First consumption: 10 Wh
        battery.consume_energy_wh(10.0, "computation")
        assert battery.get_soc() == 90.0
        assert battery.get_total_consumed_wh() == 10.0
        
        # Second consumption: 15 Wh
        battery.consume_energy_wh(15.0, "communication")
        assert battery.get_soc() == 75.0
        assert battery.get_total_consumed_wh() == 25.0
        
        # Third consumption: 5 Wh
        battery.consume_energy_wh(5.0, "idle")
        assert battery.get_soc() == 70.0
        assert battery.get_total_consumed_wh() == 30.0
        
        # Verify consumption history
        history = battery.get_consumption_history()
        assert len(history) == 3
        assert sum(record.energy_wh for record in history) == 30.0
    
    def test_precise_soc_calculation(self):
        """Test precise SoC calculation with small energy consumptions."""
        battery = Battery(capacity_wh=18.5, initial_soc=100.0)  # Realistic phone battery
        
        # Consume 0.185 Wh (1% of capacity)
        battery.consume_energy_wh(0.185, "small_task")
        
        expected_soc = 99.0  # 100% - 1%
        assert abs(battery.get_soc() - expected_soc) < 0.001, f"Expected SoC ~{expected_soc}%, got {battery.get_soc()}%"
        
        # Consume another 1.85 Wh (10% of capacity)
        battery.consume_energy_wh(1.85, "medium_task")
        
        expected_soc = 89.0  # 99% - 10%
        assert abs(battery.get_soc() - expected_soc) < 0.001, f"Expected SoC ~{expected_soc}%, got {battery.get_soc()}%"
    
    def test_energy_consumption_with_metadata(self):
        """Test energy consumption with comprehensive metadata tracking."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # Consume energy with full metadata
        battery.consume_energy_wh(
            energy_wh=10.5,
            purpose="computation",
            task_id=42,
            timestamp=1000.0
        )
        
        history = battery.get_consumption_history()
        assert len(history) == 1
        
        record = history[0]
        assert record.energy_wh == 10.5
        assert record.purpose == "computation"
        assert record.task_id == 42
        assert record.timestamp == 1000.0
        # Note: EnergyConsumptionRecord doesn't track soc_before/soc_after


class TestBoundaryProtection:
    """Test 0% and 100% boundary protection mechanisms."""
    
    def test_zero_percent_boundary_protection(self):
        """Test that SoC cannot go below 0%."""
        battery = Battery(capacity_wh=100.0, initial_soc=10.0)  # Start with 10 Wh remaining
        
        # Try to consume more energy than available
        battery.consume_energy_wh(15.0, "excessive_consumption")
        
        # SoC should be protected at 0%
        assert battery.get_soc() == 0.0, "SoC should be protected at 0%"
        assert battery.get_remaining_energy_wh() == 0.0, "Remaining energy should be 0"
        
        # Total consumed should be the requested amount (implementation allows this)
        assert battery.get_total_consumed_wh() == 15.0, "Implementation tracks full requested consumption"
    
    def test_zero_percent_multiple_excessive_consumptions(self):
        """Test multiple excessive consumptions after reaching 0%."""
        battery = Battery(capacity_wh=100.0, initial_soc=5.0)  # Start with 5 Wh
        
        # First excessive consumption
        battery.consume_energy_wh(10.0, "first_excessive")
        assert battery.get_soc() == 0.0
        assert battery.get_total_consumed_wh() == 10.0  # Implementation tracks full request
        
        # Second excessive consumption (should still track the request)
        battery.consume_energy_wh(5.0, "second_excessive") 
        assert battery.get_soc() == 0.0
        assert battery.get_total_consumed_wh() == 15.0  # Accumulates requests
        
        # Verify history shows both requests
        history = battery.get_consumption_history()
        assert len(history) == 2
        assert history[0].energy_wh == 10.0  # Full request recorded
        assert history[1].energy_wh == 5.0   # Full request recorded
    
    def test_hundred_percent_boundary_protection(self):
        """Test that SoC cannot go above 100% (via reset/set operations)."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # Try to set SoC above 100%
        with pytest.raises(ValueError, match="SoC must be between 0-100%"):
            battery.set_soc(105.0)
        
        # Try to reset to SoC above 100%
        with pytest.raises(ValueError, match="SoC must be between 0-100%"):
            battery.reset(110.0)
        
        # Verify SoC remains at valid value
        assert battery.get_soc() == 100.0
    
    def test_boundary_edge_cases(self):
        """Test exact boundary conditions."""
        # Test exactly 0%
        battery_zero = Battery(capacity_wh=100.0, initial_soc=0.0)
        assert battery_zero.get_soc() == 0.0
        assert battery_zero.get_remaining_energy_wh() == 0.0
        
        # Try to consume from 0% battery
        battery_zero.consume_energy_wh(1.0, "from_empty")
        assert battery_zero.get_soc() == 0.0  # Should remain 0%
        assert battery_zero.get_total_consumed_wh() == 1.0  # Total consumed tracks request even when battery empty
        
        # Test exactly 100%
        battery_full = Battery(capacity_wh=100.0, initial_soc=100.0)
        assert battery_full.get_soc() == 100.0
        assert battery_full.get_remaining_energy_wh() == 100.0


class TestEnergyAccountingAccuracy:
    """Test energy accounting accuracy and conservation."""
    
    def test_energy_conservation_principle(self):
        """Test that energy is conserved (consumed + remaining = capacity)."""
        battery = Battery(capacity_wh=50.0, initial_soc=80.0)  # 40 Wh available
        
        initial_remaining = battery.get_remaining_energy_wh()
        
        # Consume various amounts
        consumptions = [5.0, 3.5, 7.2, 2.8]
        for energy in consumptions:
            battery.consume_energy_wh(energy, f"task_{energy}")
        
        total_consumed = sum(consumptions)
        final_remaining = battery.get_remaining_energy_wh()
        
        # Energy conservation check
        assert abs((total_consumed + final_remaining) - initial_remaining) < 1e-10, \
            "Energy conservation: consumed + remaining should equal initial"
        
        # Verify accounting
        assert abs(battery.get_total_consumed_wh() - total_consumed) < 1e-10, \
            "Total consumed should match sum of individual consumptions"
    
    def test_high_precision_energy_tracking(self):
        """Test high precision energy tracking with small values."""
        battery = Battery(capacity_wh=1.0, initial_soc=100.0)  # 1 Wh capacity
        
        # Consume very small amounts
        small_consumptions = [0.001, 0.0005, 0.0002, 0.0003]
        
        for energy in small_consumptions:
            battery.consume_energy_wh(energy, f"micro_task")
        
        expected_total = sum(small_consumptions)  # 0.002 Wh
        expected_soc = 100.0 - (expected_total / 1.0) * 100  # 99.8%
        
        assert abs(battery.get_total_consumed_wh() - expected_total) < 1e-10
        assert abs(battery.get_soc() - expected_soc) < 1e-10
    
    def test_consumption_history_accuracy(self):
        """Test that consumption history accurately tracks all operations."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        consumptions = [
            (10.0, "computation", 1, 1000.0),
            (5.5, "communication", 2, 1001.0),
            (3.2, "idle", 3, 1002.0),
            (0.8, "overhead", 4, 1003.0),
        ]
        
        for energy, purpose, task_id, timestamp in consumptions:
            battery.consume_energy_wh(energy, purpose, task_id, timestamp)
        
        history = battery.get_consumption_history()
        assert len(history) == len(consumptions)
        
        # Verify each record
        for i, (expected_energy, expected_purpose, expected_task_id, expected_timestamp) in enumerate(consumptions):
            record = history[i]
            assert record.energy_wh == expected_energy
            assert record.purpose == expected_purpose
            assert record.task_id == expected_task_id
            assert record.timestamp == expected_timestamp
        
        # Verify total from history matches battery total
        history_total = sum(record.energy_wh for record in history)
        assert abs(history_total - battery.get_total_consumed_wh()) < 1e-10


class TestBatteryStateManagement:
    """Test battery state management operations."""
    
    def test_soc_setter_getter_comprehensive(self):
        """Test SoC setter and getter with comprehensive scenarios."""
        battery = Battery(capacity_wh=100.0, initial_soc=50.0)
        
        # Test valid SoC changes
        test_soc_values = [0.0, 0.1, 25.5, 50.0, 75.3, 99.9, 100.0]
        
        for soc in test_soc_values:
            battery.set_soc(soc)
            assert battery.get_soc() == soc, f"SoC should be {soc}%"
            expected_remaining = (soc / 100.0) * battery.capacity_wh
            assert abs(battery.get_remaining_energy_wh() - expected_remaining) < 1e-10
    
    def test_battery_reset_comprehensive(self):
        """Test comprehensive battery reset functionality."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # Perform some operations
        battery.consume_energy_wh(25.0, "task1")
        battery.consume_energy_wh(15.0, "task2")
        
        # Verify pre-reset state
        assert battery.get_soc() == 60.0
        assert battery.get_total_consumed_wh() == 40.0
        assert len(battery.get_consumption_history()) == 2
        
        # Reset to 80%
        battery.reset(80.0)
        
        # Verify post-reset state
        assert battery.get_soc() == 80.0
        assert battery.get_remaining_energy_wh() == 80.0
        assert battery.get_total_consumed_wh() == 0.0
        assert len(battery.get_consumption_history()) == 0
    
    def test_consumption_breakdown_by_purpose(self):
        """Test energy consumption breakdown by purpose."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        # Mixed consumption purposes
        consumption_data = [
            (10.0, "computation"),
            (5.0, "communication"),
            (3.0, "computation"),
            (2.0, "idle"),
            (1.5, "communication"),
            (0.5, "computation"),
        ]
        
        for energy, purpose in consumption_data:
            battery.consume_energy_wh(energy, purpose)
        
        breakdown = battery.get_consumption_by_purpose()
        
        # Verify breakdown totals
        assert breakdown["computation"] == 13.5  # 10.0 + 3.0 + 0.5
        assert breakdown["communication"] == 6.5  # 5.0 + 1.5
        assert breakdown["idle"] == 2.0
        
        # Verify total matches
        breakdown_total = sum(breakdown.values())
        assert abs(breakdown_total - battery.get_total_consumed_wh()) < 1e-10


class TestErrorHandlingAndValidation:
    """Test comprehensive error handling and input validation."""
    
    def test_negative_energy_consumption(self):
        """Test that negative energy consumption raises appropriate errors."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        with pytest.raises(ValueError, match="Energy consumption cannot be negative"):
            battery.consume_energy_wh(-5.0, "invalid")
        
        with pytest.raises(ValueError, match="Energy consumption cannot be negative"):
            battery.consume_energy_wh(-0.001, "tiny_invalid")
    
    def test_zero_energy_consumption(self):
        """Test zero energy consumption (should be allowed)."""
        battery = Battery(capacity_wh=100.0, initial_soc=100.0)
        
        initial_soc = battery.get_soc()
        battery.consume_energy_wh(0.0, "zero_energy")
        
        # SoC should not change
        assert battery.get_soc() == initial_soc
        assert battery.get_total_consumed_wh() == 0.0
        
        # But should still record the event
        history = battery.get_consumption_history()
        assert len(history) == 1
        assert history[0].energy_wh == 0.0
    
    def test_battery_depletion_detection(self):
        """Test battery depletion detection with various thresholds."""
        battery = Battery(capacity_wh=100.0, initial_soc=25.0)
        
        # Test various depletion thresholds
        assert not battery.is_depleted(20.0), "25% SoC should not be depleted with 20% threshold"
        assert not battery.is_depleted(25.0), "25% SoC should not be depleted with 25% threshold"
        assert battery.is_depleted(30.0), "25% SoC should be depleted with 30% threshold"
        assert battery.is_depleted(50.0), "25% SoC should be depleted with 50% threshold"
        
        # Test with very low SoC
        battery.set_soc(5.0)
        assert battery.is_depleted(10.0), "5% SoC should be depleted with 10% threshold"
        
        # Test with empty battery
        battery.set_soc(0.0)
        assert not battery.is_depleted(0.0), "0% SoC equals 0% threshold, so not depleted (< comparison)"
        assert battery.is_depleted(1.0), "0% SoC should be depleted with any positive threshold"
        assert battery.is_depleted(1.0), "0% SoC should be depleted with any positive threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])