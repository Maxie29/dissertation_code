"""
Battery model for simulating energy consumption of a vacuum robot.

This module provides a BatteryModel class that tracks battery state and
allows simulating energy consumption for various operations like idling,
movement, computation, and network communication.
"""

import logging
import warnings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants for unit conversion
WH_TO_JOULE = 3600  # 1 Wh = 3600 J
NANO_TO_BASE = 1e-9  # 1 nJ = 1e-9 J


class BatteryModel:
    """
    Battery energy model for vacuum robot simulation.
    
    This class tracks the battery's state of charge (SOC) and energy consumption,
    providing methods to simulate energy usage for different activities.
    """
    
    def __init__(
        self,
        capacity_Wh: float,
        init_soc: float,
        idle_power_W: float,
        move_power_W: float,
        compute_efficiency_J_per_cycle: float,
        net_tx_nJ_per_bit: float = 0.0,
        net_rx_nJ_per_bit: float = 0.0
    ):
        """
        Initialize the battery model.
        
        Args:
            capacity_Wh: Total battery capacity in watt-hours
            init_soc: Initial state of charge (0-1)
            idle_power_W: Power consumption when idle in watts
            move_power_W: Power consumption when moving in watts
            compute_efficiency_J_per_cycle: Energy required per CPU cycle in joules
            net_tx_nJ_per_bit: Energy for transmitting one bit in nanojoules
            net_rx_nJ_per_bit: Energy for receiving one bit in nanojoules
        """
        if capacity_Wh <= 0:
            raise ValueError(f"Battery capacity must be positive, got {capacity_Wh} Wh")
        if not 0 <= init_soc <= 1:
            raise ValueError(f"Initial SOC must be between 0 and 1, got {init_soc}")
        if idle_power_W < 0:
            raise ValueError(f"Idle power cannot be negative, got {idle_power_W} W")
        if move_power_W < 0:
            raise ValueError(f"Move power cannot be negative, got {move_power_W} W")
        if compute_efficiency_J_per_cycle < 0:
            raise ValueError(f"Compute efficiency cannot be negative, got {compute_efficiency_J_per_cycle} J/cycle")
        if net_tx_nJ_per_bit < 0:
            raise ValueError(f"TX energy cannot be negative, got {net_tx_nJ_per_bit} nJ/bit")
        if net_rx_nJ_per_bit < 0:
            raise ValueError(f"RX energy cannot be negative, got {net_rx_nJ_per_bit} nJ/bit")
            
        self.capacity_Wh = capacity_Wh
        self.capacity_J = capacity_Wh * WH_TO_JOULE
        self._soc = init_soc
        self.idle_power_W = idle_power_W
        self.move_power_W = move_power_W
        self.compute_efficiency_J_per_cycle = compute_efficiency_J_per_cycle
        self.net_tx_J_per_bit = net_tx_nJ_per_bit * NANO_TO_BASE
        self.net_rx_J_per_bit = net_rx_nJ_per_bit * NANO_TO_BASE
        
        # Track energy usage
        self.total_energy_used_J = 0.0
        self.total_energy_used_Wh = 0.0
        
        # Event log for tracking energy consumption
        self.events: List[Dict[str, Any]] = []
    
    @property
    def soc(self) -> float:
        """
        Get the current state of charge (0-1).
        """
        return self._soc
    
    def _log_event(self, event_type: str, energy_J: float, energy_requested_J: Optional[float] = None, **kwargs) -> None:
        """
        Log an energy consumption event.
        
        Args:
            event_type: Type of energy consumption event
            energy_J: Actual energy used in joules
            energy_requested_J: Energy that was requested (if different from used)
            **kwargs: Additional event-specific data
        """
        event = {
            "type": event_type,
            "energy_J": energy_J,
            "soc_after": self._soc,
        }
        
        if energy_requested_J is not None and energy_requested_J != energy_J:
            event["energy_requested_J"] = energy_requested_J
        
        event.update(kwargs)
        self.events.append(event)
    
    def _draw_energy(self, energy_J: float) -> float:
        """
        Draw energy from the battery.
        
        Args:
            energy_J: Energy to draw in joules
            
        Returns:
            The actual energy drawn in joules
        """
        if energy_J <= 0:
            return 0.0
            
        # Calculate energy available
        available_energy_J = self._soc * self.capacity_J
        
        # Check if we have enough energy
        if energy_J > available_energy_J:
            # Not enough energy, use what's available and warn
            actual_energy_J = available_energy_J
            warnings.warn(
                f"Insufficient battery energy: requested {energy_J:.2f} J, but only {available_energy_J:.2f} J available. "
                f"SOC will be set to 0."
            )
            self._soc = 0.0
        else:
            # Enough energy, use as requested
            actual_energy_J = energy_J
            self._soc -= energy_J / self.capacity_J
        
        # Update totals
        self.total_energy_used_J += actual_energy_J
        self.total_energy_used_Wh = self.total_energy_used_J / WH_TO_JOULE
        
        return actual_energy_J
    
    def draw_idle(self, dt_s: float) -> float:
        """
        Draw energy for idle operation.
        
        Args:
            dt_s: Time duration in seconds
            
        Returns:
            Energy used in joules
        """
        if dt_s < 0:
            raise ValueError(f"Time cannot be negative, got {dt_s} s")
        
        energy_J = self.idle_power_W * dt_s
        actual_energy_J = self._draw_energy(energy_J)
        
        self._log_event(
            event_type="idle",
            energy_J=actual_energy_J,
            energy_requested_J=energy_J,
            duration_s=dt_s
        )
        
        return actual_energy_J
    
    def draw_move(self, dt_s: float, speed=None) -> float:
        """
        Draw energy for movement.
        
        Args:
            dt_s: Time duration in seconds
            speed: Movement speed (not used currently, placeholder for future)
            
        Returns:
            Energy used in joules
        """
        if dt_s < 0:
            raise ValueError(f"Time cannot be negative, got {dt_s} s")
        
        energy_J = self.move_power_W * dt_s
        actual_energy_J = self._draw_energy(energy_J)
        
        self._log_event(
            event_type="move",
            energy_J=actual_energy_J,
            energy_requested_J=energy_J,
            duration_s=dt_s
        )
        
        return actual_energy_J
    
    def draw_compute(self, cycles: int) -> float:
        """
        Draw energy for computation.
        
        Args:
            cycles: Number of CPU cycles
            
        Returns:
            Energy used in joules
        """
        if cycles < 0:
            raise ValueError(f"CPU cycles cannot be negative, got {cycles}")
        
        energy_J = cycles * self.compute_efficiency_J_per_cycle
        actual_energy_J = self._draw_energy(energy_J)
        
        self._log_event(
            event_type="compute",
            energy_J=actual_energy_J,
            energy_requested_J=energy_J,
            cycles=cycles
        )
        
        return actual_energy_J
    
    def draw_txrx(self, bits_tx: int, bits_rx: int) -> float:
        """
        Draw energy for network transmission and reception.
        
        Args:
            bits_tx: Number of bits transmitted
            bits_rx: Number of bits received
            
        Returns:
            Energy used in joules
        """
        if bits_tx < 0:
            raise ValueError(f"TX bits cannot be negative, got {bits_tx}")
        if bits_rx < 0:
            raise ValueError(f"RX bits cannot be negative, got {bits_rx}")
        
        energy_tx_J = bits_tx * self.net_tx_J_per_bit
        energy_rx_J = bits_rx * self.net_rx_J_per_bit
        energy_J = energy_tx_J + energy_rx_J
        
        actual_energy_J = self._draw_energy(energy_J)
        
        self._log_event(
            event_type="network",
            energy_J=actual_energy_J,
            energy_requested_J=energy_J,
            bits_tx=bits_tx,
            bits_rx=bits_rx,
            energy_tx_J=energy_tx_J,
            energy_rx_J=energy_rx_J
        )
        
        return actual_energy_J
