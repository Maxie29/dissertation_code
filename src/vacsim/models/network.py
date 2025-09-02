"""
Network link model for simulating network transmission costs.

This module provides a NetworkLink class to model network connections between
nodes, including bandwidth, latency, and energy consumption characteristics.
"""

# Constants for unit conversion
MEGA_TO_BASE = 1_000_000  # 1 Mbps = 1,000,000 bits per second
NANO_TO_BASE = 1e-9       # 1 nJ = 1e-9 J

class NetworkLink:
    """
    Model of a network link with asymmetric bandwidth and energy characteristics.
    
    This class simulates network connections and calculates time and energy costs
    for data transmission and reception.
    """
    
    def __init__(
        self,
        uplink_Mbps: float,
        downlink_Mbps: float,
        rtt_ms: float,
        tx_energy_nJ_per_bit: float,
        rx_energy_nJ_per_bit: float
    ):
        """
        Initialize the network link model.
        
        Args:
            uplink_Mbps: Uplink bandwidth in megabits per second
            downlink_Mbps: Downlink bandwidth in megabits per second
            rtt_ms: Round-trip time in milliseconds
            tx_energy_nJ_per_bit: Energy for transmitting one bit in nanojoules
            rx_energy_nJ_per_bit: Energy for receiving one bit in nanojoules
        """
        if uplink_Mbps <= 0:
            raise ValueError(f"Uplink bandwidth must be positive, got {uplink_Mbps} Mbps")
        if downlink_Mbps <= 0:
            raise ValueError(f"Downlink bandwidth must be positive, got {downlink_Mbps} Mbps")
        if rtt_ms < 0:
            raise ValueError(f"Round-trip time cannot be negative, got {rtt_ms} ms")
        if tx_energy_nJ_per_bit < 0:
            raise ValueError(f"TX energy cannot be negative, got {tx_energy_nJ_per_bit} nJ/bit")
        if rx_energy_nJ_per_bit < 0:
            raise ValueError(f"RX energy cannot be negative, got {rx_energy_nJ_per_bit} nJ/bit")
        
        # Store parameters
        self.uplink_Mbps = uplink_Mbps
        self.downlink_Mbps = downlink_Mbps
        self.rtt_ms = rtt_ms
        self.tx_energy_nJ_per_bit = tx_energy_nJ_per_bit
        self.rx_energy_nJ_per_bit = rx_energy_nJ_per_bit
        
        # Convert to base units
        self.uplink_bps = uplink_Mbps * MEGA_TO_BASE
        self.downlink_bps = downlink_Mbps * MEGA_TO_BASE
        self.rtt_s = rtt_ms / 1000.0
        self.tx_energy_J_per_bit = tx_energy_nJ_per_bit * NANO_TO_BASE
        self.rx_energy_J_per_bit = rx_energy_nJ_per_bit * NANO_TO_BASE
    
    def time_to_tx(self, bits: int) -> float:
        """
        Calculate time required to transmit data.
        
        Args:
            bits: Number of bits to transmit
            
        Returns:
            Time in seconds required for transmission
        """
        if bits <= 0:
            return 0.0
        
        return bits / self.uplink_bps
    
    def time_to_rx(self, bits: int) -> float:
        """
        Calculate time required to receive data.
        
        Args:
            bits: Number of bits to receive
            
        Returns:
            Time in seconds required for reception
        """
        if bits <= 0:
            return 0.0
        
        return bits / self.downlink_bps
    
    def rtt(self) -> float:
        """
        Get the round-trip time.
        
        Returns:
            Round-trip time in seconds
        """
        return self.rtt_s
    
    def energy_tx(self, bits: int) -> float:
        """
        Calculate energy required to transmit data.
        
        Args:
            bits: Number of bits to transmit
            
        Returns:
            Energy in joules required for transmission
        """
        if bits <= 0:
            return 0.0
        
        return bits * self.tx_energy_J_per_bit
    
    def energy_rx(self, bits: int) -> float:
        """
        Calculate energy required to receive data.
        
        Args:
            bits: Number of bits to receive
            
        Returns:
            Energy in joules required for reception
        """
        if bits <= 0:
            return 0.0
        
        return bits * self.rx_energy_J_per_bit
