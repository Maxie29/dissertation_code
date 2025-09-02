"""
Task dispatch policy with strict hard-coded rules.

This module implements the core task dispatch logic for the battery offloading
simulation. The rules are hard-coded and must NOT be modified or extended
without explicit approval.

HARD RULES (IMMUTABLE):
1. NAV and SLAM tasks ALWAYS execute locally regardless of battery level
2. For GENERIC tasks:
   - If SoC ≤ 30% → CLOUD (note: equal sign goes to cloud)
   - If SoC > 30% → Edge affinity determines LOCAL vs EDGE
3. Decision made at dispatch time only, no migration during execution
4. NO additional conditions (availability, latency, etc.) are permitted

BOUNDARY CONDITION NOTES:
- SoC = 30.0% exactly → CLOUD (equal sign归云)
- This ensures deterministic behavior at the threshold
"""

from typing import Union
from .task import Task
from .enums import TaskType, Site

# Battery threshold for offloading decisions (immutable)
BATT_THRESH = 30


def is_special(task: Task) -> bool:
    """
    Check if a task is special (NAV/SLAM) and must execute locally.
    
    Special tasks bypass all battery-based offloading logic and always
    execute on the local device regardless of SoC level.
    
    Args:
        task: Task to check
        
    Returns:
        True if task is NAV or SLAM, False otherwise
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType
    >>> nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
    >>> slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0) 
    >>> generic_task = Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    >>> is_special(nav_task)
    True
    >>> is_special(slam_task)
    True
    >>> is_special(generic_task)
    False
    """
    return task.type in {TaskType.NAV, TaskType.SLAM}


def decide_site(task: Task, soc: float) -> Site:
    """
    Decide execution site for a task based on hard-coded dispatch rules.
    
    This is the core dispatch function that implements the immutable hard rules.
    The logic is deliberately simple and deterministic with no room for 
    interpretation or modification.
    
    DISPATCH LOGIC:
    1. Special tasks (NAV/SLAM) → LOCAL (always)
    2. GENERIC tasks:
       - SoC ≤ 30% → CLOUD
       - SoC > 30% and edge_affinity=True → EDGE
       - SoC > 30% and edge_affinity=False → LOCAL
    
    Args:
        task: Task to be dispatched
        soc: Current battery state of charge (0-100%)
        
    Returns:
        Site where task should execute (LOCAL/EDGE/CLOUD)
        
    Raises:
        ValueError: If SoC is not in valid range [0, 100]
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType, Site
    >>> 
    >>> # Special tasks always go LOCAL
    >>> nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
    >>> decide_site(nav_task, 10.0)  # Low battery
    <Site.LOCAL: 'local'>
    >>> decide_site(nav_task, 80.0)  # High battery
    <Site.LOCAL: 'local'>
    >>> 
    >>> # Generic tasks follow SoC rules
    >>> generic_task = Task(2, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    >>> generic_task.set_edge_affinity(True)
    >>> 
    >>> # Low SoC → CLOUD
    >>> decide_site(generic_task, 25.0)
    <Site.CLOUD: 'cloud'>
    >>> 
    >>> # Boundary case: exactly 30% → CLOUD
    >>> decide_site(generic_task, 30.0)
    <Site.CLOUD: 'cloud'>
    >>> 
    >>> # High SoC with edge affinity → EDGE
    >>> decide_site(generic_task, 35.0)
    <Site.EDGE: 'edge'>
    >>> 
    >>> # High SoC without edge affinity → LOCAL
    >>> generic_task.set_edge_affinity(False)
    >>> decide_site(generic_task, 35.0)
    <Site.LOCAL: 'local'>
    """
    # Validate SoC range
    if not (0.0 <= soc <= 100.0):
        raise ValueError(f"SoC must be between 0-100%, got {soc}")
    
    # Rule 1: Special tasks (NAV/SLAM) always execute locally
    if is_special(task):
        return Site.LOCAL
    
    # Rule 2: GENERIC tasks follow SoC-based logic
    if task.type == TaskType.GENERIC:
        # Low battery (≤ 30%) → offload to CLOUD
        # Note: Equal sign (30.0%) goes to CLOUD for deterministic behavior
        if soc <= BATT_THRESH:
            return Site.CLOUD
        
        # High battery (> 30%) → edge affinity determines site
        else:  # soc > BATT_THRESH
            if task.edge_affinity:
                return Site.EDGE
            else:
                return Site.LOCAL
    
    # Should never reach here with valid TaskType enum
    raise ValueError(f"Unknown task type: {task.type}")


def batch_decide_sites(tasks: list[Task], soc: float) -> list[tuple[Task, Site]]:
    """
    Decide execution sites for multiple tasks at once.
    
    Applies the same dispatch rules to a batch of tasks using the same
    SoC value (representing the battery state at dispatch time).
    
    Args:
        tasks: List of tasks to dispatch
        soc: Current battery state of charge (0-100%)
        
    Returns:
        List of (task, site) tuples with dispatch decisions
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType
    >>> 
    >>> tasks = [
    ...     Task(1, TaskType.NAV, 1024, 1000000.0, 0.0),
    ...     Task(2, TaskType.GENERIC, 1024, 2000000.0, 0.0)
    ... ]
    >>> tasks[1].set_edge_affinity(True)
    >>> 
    >>> decisions = batch_decide_sites(tasks, 25.0)
    >>> len(decisions)
    2
    >>> decisions[0][1]  # NAV task → LOCAL
    <Site.LOCAL: 'local'>
    >>> decisions[1][1]  # GENERIC task at low SoC → CLOUD
    <Site.CLOUD: 'cloud'>
    """
    return [(task, decide_site(task, soc)) for task in tasks]


def get_dispatch_statistics(decisions: list[tuple[Task, Site]]) -> dict[str, Union[int, float]]:
    """
    Calculate statistics for a batch of dispatch decisions.
    
    Provides insights into how tasks were distributed across execution sites
    based on the dispatch policy.
    
    Args:
        decisions: List of (task, site) tuples from batch_decide_sites()
        
    Returns:
        Dictionary with dispatch statistics
        
    Examples:
    >>> from battery_offloading.task import Task
    >>> from battery_offloading.enums import TaskType, Site
    >>> 
    >>> # Create sample decisions
    >>> tasks = [
    ...     (Task(1, TaskType.NAV, 1024, 1000000.0, 0.0), Site.LOCAL),
    ...     (Task(2, TaskType.GENERIC, 1024, 1000000.0, 0.0), Site.CLOUD)
    ... ]
    >>> 
    >>> stats = get_dispatch_statistics(tasks)
    >>> stats['total_tasks']
    2
    >>> stats['local_count']
    1
    >>> stats['cloud_count'] 
    1
    """
    if not decisions:
        return {
            'total_tasks': 0,
            'local_count': 0,
            'edge_count': 0,
            'cloud_count': 0,
            'local_ratio': 0.0,
            'edge_ratio': 0.0,
            'cloud_ratio': 0.0,
            'special_tasks': 0,
            'generic_tasks': 0
        }
    
    total_tasks = len(decisions)
    local_count = sum(1 for _, site in decisions if site == Site.LOCAL)
    edge_count = sum(1 for _, site in decisions if site == Site.EDGE)
    cloud_count = sum(1 for _, site in decisions if site == Site.CLOUD)
    
    special_count = sum(1 for task, _ in decisions if is_special(task))
    generic_count = total_tasks - special_count
    
    return {
        'total_tasks': total_tasks,
        'local_count': local_count,
        'edge_count': edge_count,
        'cloud_count': cloud_count,
        'local_ratio': local_count / total_tasks,
        'edge_ratio': edge_count / total_tasks,
        'cloud_ratio': cloud_count / total_tasks,
        'special_tasks': special_count,
        'generic_tasks': generic_count
    }


def validate_dispatch_rules() -> dict[str, bool]:
    """
    Validate that dispatch rules work correctly for all scenarios.
    
    This function serves as a built-in test to ensure the dispatch logic
    maintains consistency with the hard rules.
    
    Returns:
        Dictionary with validation results for each rule
        
    Examples:
    >>> validation = validate_dispatch_rules()
    >>> validation['nav_always_local']
    True
    >>> validation['slam_always_local']
    True
    >>> validation['low_soc_to_cloud']
    True
    """
    from .task import Task
    
    validation_results = {}
    
    # Test Rule 1: Special tasks always LOCAL
    nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
    slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0)
    
    validation_results['nav_always_local'] = all([
        decide_site(nav_task, 0.0) == Site.LOCAL,
        decide_site(nav_task, 30.0) == Site.LOCAL,
        decide_site(nav_task, 100.0) == Site.LOCAL
    ])
    
    validation_results['slam_always_local'] = all([
        decide_site(slam_task, 0.0) == Site.LOCAL,
        decide_site(slam_task, 30.0) == Site.LOCAL,
        decide_site(slam_task, 100.0) == Site.LOCAL
    ])
    
    # Test Rule 2: GENERIC tasks with SoC logic
    generic_task = Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    
    # Low SoC → CLOUD
    validation_results['low_soc_to_cloud'] = all([
        decide_site(generic_task, 0.0) == Site.CLOUD,
        decide_site(generic_task, 15.0) == Site.CLOUD,
        decide_site(generic_task, 29.0) == Site.CLOUD,
        decide_site(generic_task, 30.0) == Site.CLOUD  # Boundary case
    ])
    
    # High SoC with edge affinity → EDGE
    generic_task.set_edge_affinity(True)
    validation_results['high_soc_edge_affinity'] = all([
        decide_site(generic_task, 31.0) == Site.EDGE,
        decide_site(generic_task, 50.0) == Site.EDGE,
        decide_site(generic_task, 100.0) == Site.EDGE
    ])
    
    # High SoC without edge affinity → LOCAL
    generic_task.set_edge_affinity(False)
    validation_results['high_soc_no_edge_affinity'] = all([
        decide_site(generic_task, 31.0) == Site.LOCAL,
        decide_site(generic_task, 50.0) == Site.LOCAL,
        decide_site(generic_task, 100.0) == Site.LOCAL
    ])
    
    # Test boundary condition (SoC = 30.0% exactly)
    validation_results['boundary_condition_30_percent'] = (
        decide_site(generic_task, 30.0) == Site.CLOUD
    )
    
    validation_results['all_rules_valid'] = all(validation_results.values())
    
    return validation_results


# Export the immutable threshold for reference
__all__ = [
    'BATT_THRESH',
    'is_special',
    'decide_site',
    'batch_decide_sites',
    'get_dispatch_statistics',
    'validate_dispatch_rules'
]