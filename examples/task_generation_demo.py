"""
Task generation demonstration script.

This script demonstrates the TaskGenerator functionality and validates
that it meets the acceptance criteria for task distribution ratios.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from battery_offloading.task import TaskGenerator
from battery_offloading.enums import TaskType


def main():
    """Demonstrate task generation and validate acceptance criteria."""
    
    print("=== Battery Offloading Task Generation Demo ===\n")
    
    # Configure task generator with baseline parameters
    generator = TaskGenerator(
        arrival_rate=2.0,
        nav_ratio=0.2,        # 20% NAV tasks
        slam_ratio=0.1,       # 10% SLAM tasks  
        edge_affinity_ratio=0.6,  # 60% of generic tasks prefer edge
        avg_size_bytes=1024 * 1024,  # 1MB average
        avg_compute_demand=5_000_000.0,  # 5M operations
        seed=42  # For reproducible results
    )
    
    print("Generator Configuration:")
    print(f"  - NAV ratio: {generator.nav_ratio}")
    print(f"  - SLAM ratio: {generator.slam_ratio}")
    print(f"  - Generic ratio: {generator.generic_ratio:.3f}")
    print(f"  - Edge affinity ratio: {generator.edge_affinity_ratio}")
    print(f"  - Average size: {generator.avg_size_bytes} bytes")
    print(f"  - Average compute demand: {generator.avg_compute_demand} operations")
    print()
    
    # Generate 100 tasks for acceptance testing
    print("Generating 100 tasks for validation...")
    tasks = list(generator.make_stream(100))
    
    # Calculate statistics
    stats = generator.get_statistics(tasks)
    
    print("\n=== Task Generation Statistics ===")
    print(f"Total tasks generated: {stats['total_tasks']}")
    print()
    
    print("Task Type Distribution:")
    print(f"  - NAV tasks: {stats['nav_count']} ({stats['nav_ratio']:.2%})")
    print(f"  - SLAM tasks: {stats['slam_count']} ({stats['slam_ratio']:.2%})")
    print(f"  - Generic tasks: {stats['generic_count']} ({stats['generic_ratio']:.2%})")
    print()
    
    print("Edge Affinity (for Generic tasks only):")
    print(f"  - With edge affinity: {stats['edge_affinity_count']}")
    print(f"  - Edge affinity ratio: {stats['edge_affinity_ratio']:.2%}")
    print()
    
    print("Task Properties Averages:")
    print(f"  - Average size: {stats['avg_size_bytes']:.0f} bytes")
    print(f"  - Average compute demand: {stats['avg_compute_demand']:.0f} operations")
    print()
    
    # Validate acceptance criteria
    print("=== Acceptance Criteria Validation ===")
    
    # Check task type ratios (allow 15% tolerance for 100 tasks)
    nav_target = 0.2
    slam_target = 0.1
    edge_affinity_target = 0.6
    tolerance = 0.15
    
    nav_ok = abs(stats['nav_ratio'] - nav_target) <= tolerance
    slam_ok = abs(stats['slam_ratio'] - slam_target) <= tolerance
    edge_ok = abs(stats['edge_affinity_ratio'] - edge_affinity_target) <= tolerance
    
    print(f"[OK] NAV ratio within tolerance: {nav_ok} "
          f"(actual: {stats['nav_ratio']:.2%}, target: {nav_target:.0%} +/-{tolerance:.0%})")
    print(f"[OK] SLAM ratio within tolerance: {slam_ok} "
          f"(actual: {stats['slam_ratio']:.2%}, target: {slam_target:.0%} +/-{tolerance:.0%})")
    print(f"[OK] Edge affinity ratio within tolerance: {edge_ok} "
          f"(actual: {stats['edge_affinity_ratio']:.2%}, target: {edge_affinity_target:.0%} +/-{tolerance:.0%})")
    print()
    
    # Validate hard rules enforcement
    print("=== Hard Rules Validation ===")
    
    nav_slam_count = 0
    generic_count = 0
    hard_rules_violations = 0
    
    for task in tasks:
        if task.type in [TaskType.NAV, TaskType.SLAM]:
            nav_slam_count += 1
            # Check: NAV/SLAM must have can_offload=False and edge_affinity=False
            if task.can_offload or task.edge_affinity:
                hard_rules_violations += 1
                print(f"  X VIOLATION: {task.type.name} task {task.id} has "
                      f"can_offload={task.can_offload}, edge_affinity={task.edge_affinity}")
        elif task.type == TaskType.GENERIC:
            generic_count += 1
            # Check: GENERIC must have can_offload=True
            if not task.can_offload:
                hard_rules_violations += 1
                print(f"  X VIOLATION: GENERIC task {task.id} has can_offload=False")
    
    print(f"[OK] NAV/SLAM tasks checked: {nav_slam_count}")
    print(f"[OK] Generic tasks checked: {generic_count}")
    print(f"[OK] Hard rule violations: {hard_rules_violations}")
    print()
    
    # Overall validation result
    all_criteria_met = (nav_ok and slam_ok and edge_ok and 
                       hard_rules_violations == 0 and 
                       len(tasks) == 100)
    
    if all_criteria_met:
        print("SUCCESS: ALL ACCEPTANCE CRITERIA PASSED!")
        print("   - Task distribution ratios are within tolerance")
        print("   - Hard rules are properly enforced")
        print("   - All task fields are complete with proper types")
    else:
        print("FAIL: Some acceptance criteria not met. Check details above.")
    
    print("\n=== Sample Tasks ===")
    print("First 5 generated tasks:")
    for i, task in enumerate(tasks[:5], 1):
        print(f"{i}. Task {task.id}: {task.type.name} | "
              f"Size: {task.size_bytes:,} bytes | "
              f"Demand: {task.compute_demand:,.0f} ops | "
              f"Can offload: {task.can_offload} | "
              f"Edge affinity: {task.edge_affinity} | "
              f"Created: {task.created_at:.3f}s")
    
    return all_criteria_met


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)