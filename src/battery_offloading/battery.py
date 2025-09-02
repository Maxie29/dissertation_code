"""
Battery model for tracking energy consumption and state of charge.

This module provides a Battery class that models the robot's power source,
tracking energy consumption from computation and communication activities.
The battery maintains state of charge (SoC) as a percentage and provides
methods for consuming energy and querying current state.
"""

from typing import List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class EnergyConsumptionRecord:
    """
    Record of a single energy consumption event.
    
    Tracks when energy was consumed, how much, and for what purpose
    to enable detailed analysis of battery usage patterns.
    
    Examples:
    >>> record = EnergyConsumptionRecord(
    ...     timestamp=1000.5,
    ...     energy_wh=0.01,
    ...     purpose="local_computation",
    ...     task_id=42
    ... )
    >>> record.energy_wh
    0.01
    """
    timestamp: float = field(metadata={"description": "Simulation time when energy was consumed"})
    energy_wh: float = field(metadata={"description": "Energy consumed in Wh"})
    purpose: str = field(metadata={"description": "Purpose of energy consumption (compute/communication)"})
    task_id: Optional[int] = field(default=None, metadata={"description": "Associated task ID if applicable"})


class Battery:
    """
    Battery model for tracking robot energy consumption.
    
    Models a lithium-ion battery with capacity specified in Wh and tracks
    state of charge as a percentage. Provides methods for consuming energy
    and maintaining consumption history for analysis.
    
    Examples:
    >>> battery = Battery(capacity_wh=100.0, initial_soc=80.0)
    >>> battery.get_soc()
    80.0
    >>> battery.consume_energy_wh(10.0, "computation", task_id=1)
    >>> battery.get_soc()
    70.0
    """
    
    def __init__(self, capacity_wh: float, initial_soc: float = 100.0):
        """
        Initialize battery with specified capacity and initial state of charge.
        
        Args:
            capacity_wh: Battery capacity in watt-hours (Wh)
            initial_soc: Initial state of charge as percentage (0-100)
            
        Raises:
            ValueError: If capacity <= 0 or initial_soc not in [0, 100]
            
        Examples:
        >>> battery = Battery(100.0, 90.0)
        >>> battery.capacity_wh
        100.0
        >>> battery.get_soc()
        90.0
        """
        if capacity_wh <= 0:
            raise ValueError(f"Battery capacity must be positive, got {capacity_wh}")
        
        if not (0 <= initial_soc <= 100):
            raise ValueError(f"Initial SoC must be between 0-100%, got {initial_soc}")
        
        self.capacity_wh = capacity_wh
        self._current_energy_wh = capacity_wh * (initial_soc / 100.0)
        self._consumption_history: List[EnergyConsumptionRecord] = []
        self._total_consumed_wh = 0.0
    
    def get_soc(self) -> float:
        """
        Get current state of charge as percentage.
        
        Returns:
            Current state of charge (0-100%)
            
        Examples:
        >>> battery = Battery(100.0, 50.0)
        >>> battery.get_soc()
        50.0
        """
        return (self._current_energy_wh / self.capacity_wh) * 100.0
    
    def set_soc(self, soc_percent: float) -> None:
        """
        Set state of charge directly (for initialization/reset purposes).
        
        Args:
            soc_percent: Target state of charge as percentage (0-100)
            
        Raises:
            ValueError: If soc_percent not in [0, 100]
            
        Examples:
        >>> battery = Battery(100.0, 80.0)
        >>> battery.set_soc(60.0)
        >>> battery.get_soc()
        60.0
        """
        if not (0 <= soc_percent <= 100):
            raise ValueError(f"SoC must be between 0-100%, got {soc_percent}")
        
        self._current_energy_wh = self.capacity_wh * (soc_percent / 100.0)
    
    def get_remaining_energy_wh(self) -> float:
        """
        Get remaining energy in watt-hours.
        
        Returns:
            Remaining energy capacity in Wh
            
        Examples:
        >>> battery = Battery(100.0, 75.0)
        >>> battery.get_remaining_energy_wh()
        75.0
        """
        return self._current_energy_wh
    
    def consume_energy_wh(
        self, 
        energy_wh: float, 
        purpose: str = "unknown", 
        task_id: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> None:
        """
        Consume energy from the battery and update state of charge.
        
        Args:
            energy_wh: Energy to consume in watt-hours
            purpose: Description of energy consumption purpose
            task_id: Associated task ID if applicable
            timestamp: Simulation timestamp, uses current time if None
            
        Raises:
            ValueError: If energy_wh is negative
            
        Examples:
        >>> battery = Battery(100.0, 100.0)
        >>> battery.consume_energy_wh(25.0, "computation")
        >>> battery.get_soc()
        75.0
        >>> battery.get_total_consumed_wh()
        25.0
        """
        if energy_wh < 0:
            raise ValueError(f"Energy consumption cannot be negative, got {energy_wh}")
        
        if timestamp is None:
            timestamp = time.time()
        
        # Consume energy (allow going below 0 for realistic modeling)
        self._current_energy_wh = max(0.0, self._current_energy_wh - energy_wh)
        self._total_consumed_wh += energy_wh
        
        # Record consumption event
        record = EnergyConsumptionRecord(
            timestamp=timestamp,
            energy_wh=energy_wh,
            purpose=purpose,
            task_id=task_id
        )
        self._consumption_history.append(record)
    
    def get_total_consumed_wh(self) -> float:
        """
        Get total energy consumed since battery creation.
        
        Returns:
            Total energy consumed in Wh
            
        Examples:
        >>> battery = Battery(100.0, 100.0)
        >>> battery.consume_energy_wh(10.0, "task1")
        >>> battery.consume_energy_wh(5.0, "task2") 
        >>> battery.get_total_consumed_wh()
        15.0
        """
        return self._total_consumed_wh
    
    def get_consumption_history(self) -> List[EnergyConsumptionRecord]:
        """
        Get history of all energy consumption events.
        
        Returns:
            List of consumption records in chronological order
            
        Examples:
        >>> battery = Battery(100.0, 100.0)
        >>> battery.consume_energy_wh(5.0, "test")
        >>> history = battery.get_consumption_history()
        >>> len(history)
        1
        >>> history[0].energy_wh
        5.0
        """
        return self._consumption_history.copy()
    
    def is_depleted(self, threshold_soc: float = 0.0) -> bool:
        """
        Check if battery is depleted below threshold.
        
        Args:
            threshold_soc: SoC threshold below which battery is considered depleted
            
        Returns:
            True if current SoC is below threshold
            
        Examples:
        >>> battery = Battery(100.0, 5.0)
        >>> battery.is_depleted(10.0)
        True
        >>> battery.is_depleted(3.0)
        False
        """
        return self.get_soc() < threshold_soc
    
    def get_consumption_by_purpose(self) -> dict[str, float]:
        """
        Get energy consumption breakdown by purpose.
        
        Returns:
            Dictionary mapping purpose to total energy consumed (Wh)
            
        Examples:
        >>> battery = Battery(100.0, 100.0)
        >>> battery.consume_energy_wh(10.0, "computation")
        >>> battery.consume_energy_wh(5.0, "communication")
        >>> battery.consume_energy_wh(3.0, "computation")
        >>> breakdown = battery.get_consumption_by_purpose()
        >>> breakdown["computation"]
        13.0
        >>> breakdown["communication"]
        5.0
        """
        breakdown = {}
        for record in self._consumption_history:
            if record.purpose not in breakdown:
                breakdown[record.purpose] = 0.0
            breakdown[record.purpose] += record.energy_wh
        return breakdown
    
    def reset(self, soc_percent: float = 100.0) -> None:
        """
        Reset battery to specified state of charge and clear history.
        
        Args:
            soc_percent: Target state of charge as percentage (0-100)
            
        Examples:
        >>> battery = Battery(100.0, 50.0)
        >>> battery.consume_energy_wh(10.0, "test")
        >>> battery.reset(80.0)
        >>> battery.get_soc()
        80.0
        >>> len(battery.get_consumption_history())
        0
        """
        self.set_soc(soc_percent)
        self._consumption_history.clear()
        self._total_consumed_wh = 0.0
    
    def __str__(self) -> str:
        """
        String representation of battery state.
        
        Returns:
            Human-readable battery state
            
        Examples:
        >>> battery = Battery(100.0, 75.5)
        >>> "75.5%" in str(battery)
        True
        """
        return f"Battery(capacity={self.capacity_wh}Wh, SoC={self.get_soc():.1f}%)"