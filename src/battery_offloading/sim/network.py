"""
Network modeling for task offloading simulation.

This module provides Network class that models communication latency
and bandwidth limitations for data transmission between mobile device
and remote computing resources (EDGE/CLOUD).
"""

from typing import Tuple
from dataclasses import dataclass
import math


@dataclass 
class TransmissionResult:
    """
    Result of network transmission calculation.
    
    Contains timing breakdown for data transmission including
    pure transmission time and latency components.
    
    Examples:
    >>> result = TransmissionResult(
    ...     pure_transmission_time=4.0,
    ...     latency_overhead=0.02,
    ...     total_time=4.02
    ... )
    >>> result.total_time
    4.02
    """
    pure_transmission_time: float  # Time for actual data transmission (seconds)
    latency_overhead: float        # RTT and jitter overhead (seconds)
    total_time: float             # Total transmission time (seconds)


class Network:
    """
    Network model for communication between mobile device and remote resources.
    
    Models bandwidth limitations, round-trip time, and jitter for realistic
    network behavior simulation. Handles bit/byte conversions properly.
    
    Examples:
    >>> network = Network(
    ...     bw_up_mbps=20.0,
    ...     bw_down_mbps=50.0, 
    ...     rtt_ms=20.0,
    ...     jitter_ms=5.0
    ... )
    >>> network.bw_up_mbps
    20.0
    >>> network.rtt_ms
    20.0
    """
    
    def __init__(
        self,
        bw_up_mbps: float,
        bw_down_mbps: float, 
        rtt_ms: float,
        jitter_ms: float = 0.0
    ):
        """
        Initialize network with bandwidth and latency parameters.
        
        Args:
            bw_up_mbps: Uplink bandwidth in megabits per second (Mbps)
            bw_down_mbps: Downlink bandwidth in megabits per second (Mbps) 
            rtt_ms: Round-trip time in milliseconds
            jitter_ms: Network jitter in milliseconds (default 0)
            
        Raises:
            ValueError: If any parameter is negative
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 5.0)
        >>> network.bw_up_mbps
        20.0
        >>> network.bw_down_mbps 
        50.0
        """
        if bw_up_mbps <= 0:
            raise ValueError(f"Uplink bandwidth must be positive, got {bw_up_mbps}")
        
        if bw_down_mbps <= 0:
            raise ValueError(f"Downlink bandwidth must be positive, got {bw_down_mbps}")
        
        if rtt_ms < 0:
            raise ValueError(f"RTT cannot be negative, got {rtt_ms}")
        
        if jitter_ms < 0:
            raise ValueError(f"Jitter cannot be negative, got {jitter_ms}")
        
        self.bw_up_mbps = bw_up_mbps
        self.bw_down_mbps = bw_down_mbps
        self.rtt_ms = rtt_ms
        self.jitter_ms = jitter_ms
        
        # Pre-calculate conversion factors for efficiency
        # 1 Mbps = 1,000,000 bits/sec = 125,000 bytes/sec
        self._uplink_bytes_per_sec = bw_up_mbps * 125_000
        self._downlink_bytes_per_sec = bw_down_mbps * 125_000
    
    def uplink_time(self, bytes_size: int) -> TransmissionResult:
        """
        Calculate uplink transmission time for given data size.
        
        Args:
            bytes_size: Data size in bytes to transmit
            
        Returns:
            TransmissionResult with timing breakdown
            
        Raises:
            ValueError: If bytes_size is negative
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 0.0)
        >>> result = network.uplink_time(10 * 1024 * 1024)  # 10MB
        >>> result.pure_transmission_time
        4.194304
        >>> result.total_time > result.pure_transmission_time  # Should include RTT
        True
        """
        if bytes_size < 0:
            raise ValueError(f"Bytes size cannot be negative, got {bytes_size}")
        
        # Calculate pure transmission time
        pure_time = bytes_size / self._uplink_bytes_per_sec
        
        # Add latency overhead (half RTT + jitter for one-way transmission)
        latency_overhead = (self.rtt_ms / 2 + self.jitter_ms) / 1000.0
        
        total_time = pure_time + latency_overhead
        
        return TransmissionResult(
            pure_transmission_time=pure_time,
            latency_overhead=latency_overhead,
            total_time=total_time
        )
    
    def downlink_time(self, bytes_size: int) -> TransmissionResult:
        """
        Calculate downlink transmission time for given data size.
        
        Args:
            bytes_size: Data size in bytes to receive
            
        Returns:
            TransmissionResult with timing breakdown
            
        Raises:
            ValueError: If bytes_size is negative
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 0.0)  
        >>> result = network.downlink_time(1 * 1024 * 1024)  # 1MB
        >>> result.pure_transmission_time
        0.2097152
        >>> result.total_time > result.pure_transmission_time  # Should include RTT
        True
        """
        if bytes_size < 0:
            raise ValueError(f"Bytes size cannot be negative, got {bytes_size}")
        
        # Calculate pure transmission time
        pure_time = bytes_size / self._downlink_bytes_per_sec
        
        # Add latency overhead (half RTT + jitter for one-way transmission)
        latency_overhead = (self.rtt_ms / 2 + self.jitter_ms) / 1000.0
        
        total_time = pure_time + latency_overhead
        
        return TransmissionResult(
            pure_transmission_time=pure_time,
            latency_overhead=latency_overhead,
            total_time=total_time
        )
    
    def total_time(self, up_bytes: int, down_bytes: int) -> Tuple[float, float, float]:
        """
        Calculate total communication time for bidirectional data transfer.
        
        Args:
            up_bytes: Data size to upload in bytes
            down_bytes: Data size to download in bytes
            
        Returns:
            Tuple of (uplink_time, downlink_time, total_time) in seconds
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 0.0)
        >>> up_time, down_time, total = network.total_time(10*1024*1024, 1*1024*1024)
        >>> total == up_time + down_time
        True
        >>> up_time > 0 and down_time > 0
        True
        """
        uplink_result = self.uplink_time(up_bytes)
        downlink_result = self.downlink_time(down_bytes)
        
        uplink_time = uplink_result.total_time
        downlink_time = downlink_result.total_time
        total = uplink_time + downlink_time
        
        return uplink_time, downlink_time, total
    
    def get_effective_bandwidth(self, bytes_size: int, direction: str) -> float:
        """
        Calculate effective bandwidth including protocol overhead.
        
        Args:
            bytes_size: Data size in bytes
            direction: "up" or "down" for upload/download
            
        Returns:
            Effective bandwidth in Mbps
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 10.0)
        >>> eff_bw = network.get_effective_bandwidth(10*1024*1024, "up")
        >>> eff_bw < 20.0  # Should be less due to latency overhead
        True
        """
        if direction == "up":
            result = self.uplink_time(bytes_size)
        elif direction == "down":
            result = self.downlink_time(bytes_size)
        else:
            raise ValueError(f"Direction must be 'up' or 'down', got {direction}")
        
        # Convert bytes to megabits and calculate effective bandwidth
        megabits = (bytes_size * 8) / 1_000_000
        effective_mbps = megabits / result.total_time
        
        return effective_mbps
    
    def estimate_file_transfer_time(
        self, 
        file_size_mb: float, 
        direction: str,
        include_handshake: bool = True
    ) -> dict[str, float]:
        """
        Estimate file transfer time with detailed breakdown.
        
        Args:
            file_size_mb: File size in megabytes (MB)
            direction: "up" or "down" for upload/download
            include_handshake: Whether to include connection handshake time
            
        Returns:
            Dictionary with timing breakdown
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 5.0)
        >>> breakdown = network.estimate_file_transfer_time(10.0, "up")
        >>> breakdown["file_size_mb"]
        10.0
        >>> breakdown["total_time"] > 0
        True
        """
        file_size_bytes = int(file_size_mb * 1024 * 1024)
        
        if direction == "up":
            result = self.uplink_time(file_size_bytes)
        elif direction == "down":
            result = self.downlink_time(file_size_bytes)
        else:
            raise ValueError(f"Direction must be 'up' or 'down', got {direction}")
        
        # Add connection handshake time if requested (typically 1-2 RTT)
        handshake_time = 0.0
        if include_handshake:
            handshake_time = 2 * (self.rtt_ms / 1000.0)  # 2 RTT for handshake
        
        total_with_handshake = result.total_time + handshake_time
        
        return {
            "file_size_mb": file_size_mb,
            "file_size_bytes": file_size_bytes,
            "direction": direction,
            "pure_transmission_time": result.pure_transmission_time,
            "latency_overhead": result.latency_overhead,
            "handshake_time": handshake_time,
            "total_time": total_with_handshake,
            "effective_bandwidth_mbps": self.get_effective_bandwidth(file_size_bytes, direction)
        }
    
    def bandwidth_delay_product(self) -> float:
        """
        Calculate bandwidth-delay product for the network.
        
        Returns:
            Bandwidth-delay product in bytes
            
        Examples:
        >>> network = Network(20.0, 50.0, 30.0)
        >>> bdp = network.bandwidth_delay_product()
        >>> bdp > 0
        True
        """
        # Use average bandwidth for BDP calculation
        avg_bandwidth_bps = (self._uplink_bytes_per_sec + self._downlink_bytes_per_sec) / 2
        delay_seconds = self.rtt_ms / 1000.0
        
        return avg_bandwidth_bps * delay_seconds
    
    def __str__(self) -> str:
        """
        String representation of network configuration.
        
        Returns:
            Human-readable network description
            
        Examples:
        >>> network = Network(20.0, 50.0, 20.0, 5.0)
        >>> "20.0" in str(network)
        True
        >>> "50.0" in str(network)
        True
        """
        return (f"Network(up={self.bw_up_mbps}Mbps, down={self.bw_down_mbps}Mbps, "
                f"rtt={self.rtt_ms}ms, jitter={self.jitter_ms}ms)")


def create_networks_from_config(config) -> dict[str, Network]:
    """
    Create network configurations from config object.
    
    Args:
        config: Configuration object with network settings
        
    Returns:
        Dictionary mapping network type to Network instance
        
    Examples:
    >>> from battery_offloading.config import Config
    >>> config = Config.from_yaml('configs/baseline.yaml')  # doctest: +SKIP
    >>> networks = create_networks_from_config(config)  # doctest: +SKIP
    >>> "edge" in networks  # doctest: +SKIP
    True
    """
    networks = {}
    
    # Create EDGE network
    networks["edge"] = Network(
        bw_up_mbps=config.edge_network.bandwidth_mbps,  # Assume symmetric initially
        bw_down_mbps=config.edge_network.bandwidth_mbps,
        rtt_ms=config.edge_network.latency_ms * 2,  # Convert one-way to RTT
        jitter_ms=0.0  # Default no jitter unless specified
    )
    
    # Create CLOUD network
    networks["cloud"] = Network(
        bw_up_mbps=config.cloud_network.bandwidth_mbps,
        bw_down_mbps=config.cloud_network.bandwidth_mbps,
        rtt_ms=config.cloud_network.latency_ms * 2,  # Convert one-way to RTT
        jitter_ms=0.0  # Default no jitter unless specified
    )
    
    return networks


def validate_network_parameters(
    bw_up_mbps: float,
    bw_down_mbps: float,
    rtt_ms: float
) -> dict[str, bool]:
    """
    Validate network parameters for realistic values.
    
    Args:
        bw_up_mbps: Uplink bandwidth in Mbps
        bw_down_mbps: Downlink bandwidth in Mbps
        rtt_ms: Round-trip time in milliseconds
        
    Returns:
        Dictionary with validation results
        
    Examples:
    >>> result = validate_network_parameters(20.0, 50.0, 20.0)
    >>> result["valid_bandwidth"]
    True
    >>> result["valid_latency"]
    True
    """
    validation = {
        "valid_bandwidth": True,
        "valid_latency": True,
        "realistic_asymmetry": True,
        "warnings": []
    }
    
    # Check bandwidth validity
    if bw_up_mbps <= 0 or bw_down_mbps <= 0:
        validation["valid_bandwidth"] = False
        validation["warnings"].append("Bandwidth must be positive")
    
    # Check latency validity  
    if rtt_ms < 0:
        validation["valid_latency"] = False
        validation["warnings"].append("RTT cannot be negative")
    
    # Check realistic asymmetry (downlink usually >= uplink for most connections)
    if bw_down_mbps < bw_up_mbps:
        validation["realistic_asymmetry"] = False
        validation["warnings"].append("Downlink bandwidth typically >= uplink bandwidth")
    
    # Check for unrealistic values
    if rtt_ms > 1000:  # > 1 second RTT
        validation["warnings"].append("RTT > 1s may indicate satellite or poor connectivity")
    
    if bw_up_mbps > 1000 or bw_down_mbps > 1000:  # > 1 Gbps
        validation["warnings"].append("Bandwidth > 1Gbps may be unrealistic for mobile devices")
    
    return validation