"""
Enumeration definitions for the battery offloading simulation.

This module defines the core enums used throughout the simulation:
- TaskType: Categories of tasks with different execution requirements
- Site: Available execution locations for task offloading

The enums enforce the hard rules of the simulation system.
"""

from enum import Enum
from typing import Set


class TaskType(Enum):
    """
    Task categories with specific execution requirements.
    
    NAV and SLAM are special tasks that must always execute locally
    regardless of battery state, while GENERIC tasks follow standard
    offloading rules based on SoC and edge affinity.
    
    Examples:
    >>> TaskType.NAV.name
    'NAV'
    >>> TaskType.is_special(TaskType.SLAM)
    True
    >>> TaskType.is_special(TaskType.GENERIC)
    False
    """
    NAV = "navigation"
    SLAM = "simultaneous_localization_mapping" 
    GENERIC = "generic_computation"
    
    @classmethod
    def get_special_tasks(cls) -> Set['TaskType']:
        """
        Return set of tasks that must execute locally regardless of battery level.
        
        Returns:
            Set of TaskType values that are considered special tasks
            
        >>> special = TaskType.get_special_tasks()
        >>> TaskType.NAV in special
        True
        >>> TaskType.GENERIC in special
        False
        """
        return {cls.NAV, cls.SLAM}
    
    @classmethod
    def is_special(cls, task_type: 'TaskType') -> bool:
        """
        Check if a task type requires local execution regardless of battery.
        
        Args:
            task_type: The task type to check
            
        Returns:
            True if task must execute locally, False otherwise
            
        >>> TaskType.is_special(TaskType.NAV)
        True
        >>> TaskType.is_special(TaskType.GENERIC)
        False
        """
        return task_type in cls.get_special_tasks()


class Site(Enum):
    """
    Available execution locations for task offloading.
    
    Defines the three-tier computing architecture:
    - LOCAL: On-device execution
    - EDGE: Nearby edge server execution  
    - CLOUD: Remote cloud execution
    
    Examples:
    >>> Site.LOCAL.value
    'local'
    >>> list(Site)
    [<Site.LOCAL: 'local'>, <Site.EDGE: 'edge'>, <Site.CLOUD: 'cloud'>]
    """
    LOCAL = "local"
    EDGE = "edge" 
    CLOUD = "cloud"
    
    def __str__(self) -> str:
        """
        String representation using the enum value.
        
        Returns:
            The string value of the site
            
        >>> str(Site.LOCAL)
        'local'
        """
        return self.value