"""
Tests for the network model.
"""

import pytest
from vacsim.models.network import NetworkLink, MEGA_TO_BASE, NANO_TO_BASE


def test_network_link_initialization():
    """Test NetworkLink initialization with valid parameters."""
    link = NetworkLink(
        uplink_Mbps=10.0,
        downlink_Mbps=50.0,
        rtt_ms=20.0,
        tx_energy_nJ_per_bit=0.5,
        rx_energy_nJ_per_bit=0.3
    )
    
    # Check stored parameters
    assert link.uplink_Mbps == 10.0
    assert link.downlink_Mbps == 50.0
    assert link.rtt_ms == 20.0
    assert link.tx_energy_nJ_per_bit == 0.5
    assert link.rx_energy_nJ_per_bit == 0.3
    
    # Check converted values
    assert link.uplink_bps == 10.0 * MEGA_TO_BASE
    assert link.downlink_bps == 50.0 * MEGA_TO_BASE
    assert link.rtt_s == 0.02
    assert link.tx_energy_J_per_bit == 0.5 * NANO_TO_BASE
    assert link.rx_energy_J_per_bit == 0.3 * NANO_TO_BASE


def test_network_link_invalid_parameters():
    """Test NetworkLink initialization with invalid parameters."""
    # Zero or negative bandwidth
    with pytest.raises(ValueError):
        NetworkLink(
            uplink_Mbps=0.0,
            downlink_Mbps=50.0,
            rtt_ms=20.0,
            tx_energy_nJ_per_bit=0.5,
            rx_energy_nJ_per_bit=0.3
        )
    
    with pytest.raises(ValueError):
        NetworkLink(
            uplink_Mbps=10.0,
            downlink_Mbps=-5.0,
            rtt_ms=20.0,
            tx_energy_nJ_per_bit=0.5,
            rx_energy_nJ_per_bit=0.3
        )
    
    # Negative RTT
    with pytest.raises(ValueError):
        NetworkLink(
            uplink_Mbps=10.0,
            downlink_Mbps=50.0,
            rtt_ms=-10.0,
            tx_energy_nJ_per_bit=0.5,
            rx_energy_nJ_per_bit=0.3
        )
    
    # Negative energy values
    with pytest.raises(ValueError):
        NetworkLink(
            uplink_Mbps=10.0,
            downlink_Mbps=50.0,
            rtt_ms=20.0,
            tx_energy_nJ_per_bit=-0.1,
            rx_energy_nJ_per_bit=0.3
        )


def test_transmission_time_calculation():
    """Test calculation of transmission time."""
    link = NetworkLink(
        uplink_Mbps=10.0,
        downlink_Mbps=50.0,
        rtt_ms=20.0,
        tx_energy_nJ_per_bit=0.5,
        rx_energy_nJ_per_bit=0.3
    )
    
    # Test normal case: 1 Mbit
    bits = 1_000_000
    expected_tx_time = bits / (10.0 * MEGA_TO_BASE)  # 0.1 seconds
    assert link.time_to_tx(bits) == pytest.approx(expected_tx_time)
    
    # Test normal case: 5 Mbit
    bits = 5_000_000
    expected_rx_time = bits / (50.0 * MEGA_TO_BASE)  # 0.1 seconds
    assert link.time_to_rx(bits) == pytest.approx(expected_rx_time)
    
    # Test edge case: zero bits
    assert link.time_to_tx(0) == 0.0
    assert link.time_to_rx(0) == 0.0
    
    # Test edge case: negative bits (should handle as zero)
    assert link.time_to_tx(-100) == 0.0
    assert link.time_to_rx(-100) == 0.0


def test_energy_calculation():
    """Test calculation of transmission energy."""
    link = NetworkLink(
        uplink_Mbps=10.0,
        downlink_Mbps=50.0,
        rtt_ms=20.0,
        tx_energy_nJ_per_bit=0.5,
        rx_energy_nJ_per_bit=0.3
    )
    
    # Test normal case: 1 Mbit
    bits = 1_000_000
    expected_tx_energy = bits * 0.5 * NANO_TO_BASE  # 0.0000005 J
    expected_rx_energy = bits * 0.3 * NANO_TO_BASE  # 0.0000003 J
    assert link.energy_tx(bits) == pytest.approx(expected_tx_energy)
    assert link.energy_rx(bits) == pytest.approx(expected_rx_energy)
    
    # Test edge case: zero bits
    assert link.energy_tx(0) == 0.0
    assert link.energy_rx(0) == 0.0
    
    # Test edge case: negative bits (should handle as zero)
    assert link.energy_tx(-100) == 0.0
    assert link.energy_rx(-100) == 0.0


def test_round_trip_time():
    """Test round-trip time access."""
    link = NetworkLink(
        uplink_Mbps=10.0,
        downlink_Mbps=50.0,
        rtt_ms=20.0,
        tx_energy_nJ_per_bit=0.5,
        rx_energy_nJ_per_bit=0.3
    )
    
    assert link.rtt() == 0.02  # 20 ms = 0.02 s


def test_large_data_transfer():
    """Test calculations with large data transfers."""
    link = NetworkLink(
        uplink_Mbps=100.0,
        downlink_Mbps=1000.0,
        rtt_ms=5.0,
        tx_energy_nJ_per_bit=0.2,
        rx_energy_nJ_per_bit=0.1
    )
    
    # Test with 1 GB = 8 Gbits
    bits = 8 * 1000 * 1000 * 1000
    
    # Expected time: 8 Gbits / 100 Mbps = 80 seconds
    expected_tx_time = bits / (100.0 * MEGA_TO_BASE)
    assert link.time_to_tx(bits) == pytest.approx(expected_tx_time)
    
    # Expected energy: 8 Gbits * 0.2 nJ/bit * 1e-9 = 0.0016 J
    expected_tx_energy = bits * 0.2 * NANO_TO_BASE
    assert link.energy_tx(bits) == pytest.approx(expected_tx_energy)
