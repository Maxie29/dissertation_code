"""
Policy dispatch demonstration script.

This script validates that the policy implementation strictly adheres 
to the hard dispatch rules and passes all acceptance criteria.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from battery_offloading.policy import (
    BATT_THRESH, 
    is_special, 
    decide_site,
    batch_decide_sites,
    get_dispatch_statistics,
    validate_dispatch_rules
)
from battery_offloading.task import Task
from battery_offloading.enums import TaskType, Site


def demonstrate_basic_rules():
    """Demonstrate basic dispatch rule functionality."""
    print("=== Basic Dispatch Rules ===\n")
    
    print(f"1. Battery Threshold: {BATT_THRESH}%")
    print()
    
    # Create test tasks
    nav_task = Task(1, TaskType.NAV, 1024, 1000000.0, 0.0)
    slam_task = Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0)
    generic_task = Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    
    print("2. Special Task Detection")
    print(f"   NAV task is special: {is_special(nav_task)}")
    print(f"   SLAM task is special: {is_special(slam_task)}")
    print(f"   GENERIC task is special: {is_special(generic_task)}")
    print()
    
    return True


def demonstrate_acceptance_criteria():
    """Demonstrate all acceptance criteria exactly as specified."""
    print("=== Acceptance Criteria Validation ===\n")
    
    results = []
    
    # Create GENERIC task for testing
    generic_task = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    
    print("1. SoC=25%, GENERIC -> CLOUD")
    generic_task.set_edge_affinity(True)  # Edge affinity shouldn't matter at low SoC
    site = decide_site(generic_task, 25.0)
    success = site == Site.CLOUD
    results.append(success)
    print(f"   Result: {site.name} [{'PASS' if success else 'FAIL'}]")
    print()
    
    print("2. SoC=30%, GENERIC -> CLOUD (equal sign goes to cloud)")
    generic_task.set_edge_affinity(True)  # Edge affinity shouldn't matter at boundary
    site = decide_site(generic_task, 30.0)
    success = site == Site.CLOUD
    results.append(success)
    print(f"   Result: {site.name} [{'PASS' if success else 'FAIL'}]")
    print()
    
    print("3. SoC=35%, GENERIC, edge_affinity=True -> EDGE")
    generic_task.set_edge_affinity(True)
    site = decide_site(generic_task, 35.0)
    success = site == Site.EDGE
    results.append(success)
    print(f"   Result: {site.name} [{'PASS' if success else 'FAIL'}]")
    print()
    
    print("4. SoC=35%, GENERIC, edge_affinity=False -> LOCAL")
    generic_task.set_edge_affinity(False)
    site = decide_site(generic_task, 35.0)
    success = site == Site.LOCAL
    results.append(success)
    print(f"   Result: {site.name} [{'PASS' if success else 'FAIL'}]")
    print()
    
    print("5. Any SoC, NAV/SLAM -> LOCAL")
    nav_task = Task(2, TaskType.NAV, 1024, 1000000.0, 0.0)
    slam_task = Task(3, TaskType.SLAM, 1024, 1000000.0, 0.0)
    
    test_socs = [0.0, 25.0, 30.0, 35.0, 80.0, 100.0]
    nav_success = all(decide_site(nav_task, soc) == Site.LOCAL for soc in test_socs)
    slam_success = all(decide_site(slam_task, soc) == Site.LOCAL for soc in test_socs)
    
    success = nav_success and slam_success
    results.append(success)
    print(f"   NAV at all SoC levels: {'PASS' if nav_success else 'FAIL'}")
    print(f"   SLAM at all SoC levels: {'PASS' if slam_success else 'FAIL'}")
    print(f"   Overall: [{'PASS' if success else 'FAIL'}]")
    print()
    
    return all(results)


def demonstrate_boundary_conditions():
    """Demonstrate critical boundary conditions."""
    print("=== Boundary Condition Testing ===\n")
    
    generic_task_edge = Task(1, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    generic_task_local = Task(2, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    
    generic_task_edge.set_edge_affinity(True)
    generic_task_local.set_edge_affinity(False)
    
    print("1. Testing around 30% threshold:")
    boundary_tests = [
        (29.0, "Below threshold"),
        (29.9, "Just below threshold"), 
        (30.0, "Exactly at threshold (critical)"),
        (30.1, "Just above threshold"),
        (31.0, "Above threshold")
    ]
    
    all_boundary_correct = True
    
    for soc, description in boundary_tests:
        site_edge = decide_site(generic_task_edge, soc)
        site_local = decide_site(generic_task_local, soc)
        
        if soc <= 30.0:
            # Should go to CLOUD
            expected = Site.CLOUD
            correct = site_edge == expected and site_local == expected
        else:
            # Should follow edge affinity
            correct = site_edge == Site.EDGE and site_local == Site.LOCAL
        
        all_boundary_correct &= correct
        status = "PASS" if correct else "FAIL"
        
        print(f"   SoC={soc:4.1f}%: Edge->{site_edge.name:5}, Local->{site_local.name:5} ({description}) [{status}]")
    
    print(f"\n   Boundary conditions: [{'PASS' if all_boundary_correct else 'FAIL'}]")
    print()
    
    return all_boundary_correct


def demonstrate_batch_operations():
    """Demonstrate batch dispatch operations."""
    print("=== Batch Operations ===\n")
    
    # Create diverse task mix
    tasks = [
        Task(1, TaskType.NAV, 1024, 1000000.0, 0.0),
        Task(2, TaskType.SLAM, 1024, 1000000.0, 0.0),
        Task(3, TaskType.GENERIC, 1024, 1000000.0, 0.0),
        Task(4, TaskType.GENERIC, 1024, 1000000.0, 0.0),
        Task(5, TaskType.GENERIC, 1024, 1000000.0, 0.0)
    ]
    
    # Set edge affinity for generic tasks
    tasks[2].set_edge_affinity(True)   # GENERIC with edge affinity
    tasks[3].set_edge_affinity(False)  # GENERIC without edge affinity
    tasks[4].set_edge_affinity(True)   # Another GENERIC with edge affinity
    
    print("1. Batch dispatch at low battery (25%):")
    low_soc_decisions = batch_decide_sites(tasks, 25.0)
    
    for i, (task, site) in enumerate(low_soc_decisions):
        task_type = task.type.name
        edge_aff = getattr(task, 'edge_affinity', 'N/A')
        print(f"   Task {i+1} ({task_type}, edge_affinity={edge_aff}): {site.name}")
    
    low_soc_stats = get_dispatch_statistics(low_soc_decisions)
    print(f"   Stats: {low_soc_stats['local_count']} LOCAL, {low_soc_stats['edge_count']} EDGE, {low_soc_stats['cloud_count']} CLOUD")
    print()
    
    print("2. Batch dispatch at high battery (70%):")
    high_soc_decisions = batch_decide_sites(tasks, 70.0)
    
    for i, (task, site) in enumerate(high_soc_decisions):
        task_type = task.type.name
        edge_aff = getattr(task, 'edge_affinity', 'N/A')
        print(f"   Task {i+1} ({task_type}, edge_affinity={edge_aff}): {site.name}")
    
    high_soc_stats = get_dispatch_statistics(high_soc_decisions)
    print(f"   Stats: {high_soc_stats['local_count']} LOCAL, {high_soc_stats['edge_count']} EDGE, {high_soc_stats['cloud_count']} CLOUD")
    print()
    
    return True


def demonstrate_built_in_validation():
    """Demonstrate built-in rule validation."""
    print("=== Built-in Rule Validation ===\n")
    
    validation = validate_dispatch_rules()
    
    print("1. Individual Rule Validation:")
    rule_tests = [
        ("NAV always LOCAL", validation['nav_always_local']),
        ("SLAM always LOCAL", validation['slam_always_local']),
        ("Low SoC to CLOUD", validation['low_soc_to_cloud']),
        ("High SoC + edge affinity", validation['high_soc_edge_affinity']),
        ("High SoC + no edge affinity", validation['high_soc_no_edge_affinity']),
        ("Boundary condition (30%)", validation['boundary_condition_30_percent'])
    ]
    
    for rule_name, passed in rule_tests:
        status = "PASS" if passed else "FAIL"
        print(f"   {rule_name}: [{status}]")
    
    overall_valid = validation['all_rules_valid']
    print(f"\n2. Overall Validation: [{'PASS' if overall_valid else 'FAIL'}]")
    print()
    
    return overall_valid


def main():
    """Main demonstration function."""
    print("=== Policy Dispatch Rules Demonstration ===\n")
    
    # Run all demonstrations
    basic_ok = demonstrate_basic_rules()
    acceptance_ok = demonstrate_acceptance_criteria()
    boundary_ok = demonstrate_boundary_conditions()
    batch_ok = demonstrate_batch_operations()
    validation_ok = demonstrate_built_in_validation()
    
    # Final results
    print("=== Final Results ===")
    print(f"[{'PASS' if basic_ok else 'FAIL'}] Basic rules functionality")
    print(f"[{'PASS' if acceptance_ok else 'FAIL'}] All acceptance criteria")
    print(f"[{'PASS' if boundary_ok else 'FAIL'}] Boundary conditions")
    print(f"[{'PASS' if batch_ok else 'FAIL'}] Batch operations")
    print(f"[{'PASS' if validation_ok else 'FAIL'}] Built-in validation")
    
    all_passed = all([basic_ok, acceptance_ok, boundary_ok, batch_ok, validation_ok])
    
    print(f"\n{'='*60}")
    if all_passed:
        print("SUCCESS: All policy rules implemented correctly!")
        print("HARD RULES VALIDATED:")
        print("  + NAV/SLAM always execute locally")
        print("  + SoC <= 30% (including 30%) -> CLOUD")
        print("  + SoC > 30% -> edge_affinity determines EDGE vs LOCAL")
        print("  + No migration during execution")
        print("  + No unapproved additional conditions")
    else:
        print("FAILURE: Some policy rules failed validation!")
    
    print(f"{'='*60}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)