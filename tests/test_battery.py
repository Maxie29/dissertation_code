"""
Tests for the battery model.
"""

import pytest
import warnings

from vacsim.models.battery import BatteryModel, WH_TO_JOULE, NANO_TO_BASE


def test_battery_initialization():
    """Test battery model initialization with valid parameters."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=0.8,
        idle_power_W=5.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9
    )
    
    assert battery.capacity_Wh == 50.0
    assert battery.capacity_J == 50.0 * WH_TO_JOULE
    assert battery.soc == 0.8
    assert battery.idle_power_W == 5.0
    assert battery.move_power_W == 20.0
    assert battery.compute_efficiency_J_per_cycle == 1e-9
    assert battery.net_tx_J_per_bit == 0.0
    assert battery.net_rx_J_per_bit == 0.0
    assert battery.total_energy_used_J == 0.0
    assert battery.total_energy_used_Wh == 0.0
    assert len(battery.events) == 0


def test_battery_initialization_invalid_parameters():
    """Test battery model initialization with invalid parameters."""
    # Negative capacity
    with pytest.raises(ValueError):
        BatteryModel(
            capacity_Wh=-10.0,
            init_soc=0.8,
            idle_power_W=5.0,
            move_power_W=20.0,
            compute_efficiency_J_per_cycle=1e-9
        )
    
    # SOC out of range
    with pytest.raises(ValueError):
        BatteryModel(
            capacity_Wh=50.0,
            init_soc=1.5,
            idle_power_W=5.0,
            move_power_W=20.0,
            compute_efficiency_J_per_cycle=1e-9
        )
    
    # Negative power values
    with pytest.raises(ValueError):
        BatteryModel(
            capacity_Wh=50.0,
            init_soc=0.8,
            idle_power_W=-5.0,
            move_power_W=20.0,
            compute_efficiency_J_per_cycle=1e-9
        )


def test_draw_idle():
    """Test drawing energy for idle operation."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=1.0,
        idle_power_W=10.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9
    )
    
    # Draw for 1 hour (should use 10Wh)
    energy_used = battery.draw_idle(3600)
    
    assert energy_used == 10.0 * 3600  # 10W * 3600s = 36000J
    assert battery.soc == 0.8  # Used 10Wh of 50Wh = 20% of capacity
    assert battery.total_energy_used_J == 10.0 * 3600
    assert battery.total_energy_used_Wh == 10.0
    assert len(battery.events) == 1
    assert battery.events[0]["type"] == "idle"
    
    # Test with negative time
    with pytest.raises(ValueError):
        battery.draw_idle(-10)


def test_draw_move():
    """Test drawing energy for movement."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=1.0,
        idle_power_W=5.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9
    )
    
    # Draw for 30 minutes (should use 10Wh)
    energy_used = battery.draw_move(1800)
    
    assert energy_used == 20.0 * 1800  # 20W * 1800s = 36000J
    assert battery.soc == 0.8  # Used 10Wh of 50Wh = 20% of capacity
    assert battery.total_energy_used_J == 20.0 * 1800
    assert battery.total_energy_used_Wh == 10.0
    assert len(battery.events) == 1
    assert battery.events[0]["type"] == "move"


def test_draw_compute():
    """Test drawing energy for computation."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=1.0,
        idle_power_W=5.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9
    )
    
    # 1 billion cycles at 1nJ/cycle = 1J
    energy_used = battery.draw_compute(1_000_000_000)
    
    assert energy_used == 1.0
    # Very small energy usage, SOC should be very close to 1
    expected_soc = 1.0 - (1.0 / (50.0 * WH_TO_JOULE))
    assert battery.soc == pytest.approx(expected_soc)
    assert battery.total_energy_used_J == 1.0
    assert battery.events[0]["type"] == "compute"
    assert battery.events[0]["cycles"] == 1_000_000_000


def test_draw_txrx():
    """Test drawing energy for network transmission and reception."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=1.0,
        idle_power_W=5.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9,
        net_tx_nJ_per_bit=0.5,
        net_rx_nJ_per_bit=0.3
    )
    
    # 1 million bits TX, 2 million bits RX
    # 1M * 0.5nJ + 2M * 0.3nJ = 0.5J + 0.6J = 1.1J
    energy_used = battery.draw_txrx(1_000_000, 2_000_000)
    
    expected_tx_J = 1_000_000 * 0.5 * NANO_TO_BASE
    expected_rx_J = 2_000_000 * 0.3 * NANO_TO_BASE
    expected_total_J = expected_tx_J + expected_rx_J
    
    assert energy_used == pytest.approx(expected_total_J)
    # Very small energy usage, SOC should be very close to 1
    expected_soc = 1.0 - (expected_total_J / (50.0 * WH_TO_JOULE))
    assert battery.soc == pytest.approx(expected_soc)
    assert battery.total_energy_used_J == pytest.approx(expected_total_J)
    assert battery.events[0]["type"] == "network"
    assert battery.events[0]["bits_tx"] == 1_000_000
    assert battery.events[0]["bits_rx"] == 2_000_000


def test_zero_energy_requests():
    """Test requesting zero energy."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=0.8,
        idle_power_W=5.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9
    )
    
    # All these should return 0 energy used and not change SOC
    assert battery.draw_idle(0) == 0.0
    assert battery.draw_move(0) == 0.0
    assert battery.draw_compute(0) == 0.0
    assert battery.draw_txrx(0, 0) == 0.0
    
    assert battery.soc == 0.8  # Unchanged
    assert battery.total_energy_used_J == 0.0
    assert len(battery.events) == 4  # Still log zero-energy events


def test_insufficient_energy():
    """Test behavior when requesting more energy than available."""
    battery = BatteryModel(
        capacity_Wh=50.0,
        init_soc=0.1,  # Only 5Wh available
        idle_power_W=10.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9
    )
    
    # Try to draw for 1 hour (would need 10Wh, but only 5Wh available)
    with warnings.catch_warnings(record=True) as w:
        energy_used = battery.draw_idle(3600)
        
        # Should have warned about insufficient energy
        assert len(w) == 1
        assert "Insufficient battery" in str(w[0].message)
    
    # Should have used all available energy (5Wh)
    assert energy_used == pytest.approx(5.0 * WH_TO_JOULE)
    assert battery.soc == 0.0  # Battery depleted
    assert battery.total_energy_used_J == pytest.approx(5.0 * WH_TO_JOULE)
    assert battery.total_energy_used_Wh == pytest.approx(5.0)


def test_energy_conservation():
    """Test that energy accounting is consistent."""
    battery = BatteryModel(
        capacity_Wh=100.0,
        init_soc=1.0,
        idle_power_W=5.0,
        move_power_W=20.0,
        compute_efficiency_J_per_cycle=1e-9,
        net_tx_nJ_per_bit=0.5,
        net_rx_nJ_per_bit=0.3
    )
    
    # Perform various operations
    battery.draw_idle(3600)     # 5W * 3600s = 18000J = 5Wh
    battery.draw_move(1800)     # 20W * 1800s = 36000J = 10Wh
    battery.draw_compute(1e9)   # 1e9 cycles * 1e-9 J/cycle = 1J
    battery.draw_txrx(1e6, 2e6) # (1e6 * 0.5 + 2e6 * 0.3) * 1e-9 = 1.1J
    
    # Total should be 5 + 10 + ~0 + ~0 = ~15Wh
    expected_energy_used_Wh = 15.0
    expected_energy_used_J = expected_energy_used_Wh * WH_TO_JOULE
    expected_soc = 1.0 - (expected_energy_used_Wh / 100.0)
    
    assert battery.total_energy_used_Wh == pytest.approx(expected_energy_used_Wh)
    assert battery.total_energy_used_J == pytest.approx(expected_energy_used_J)
    assert battery.soc == pytest.approx(expected_soc)
    
    # Check that events are consistent with total energy
    total_from_events = sum(event["energy_J"] for event in battery.events)
    assert total_from_events == pytest.approx(expected_energy_used_J)
