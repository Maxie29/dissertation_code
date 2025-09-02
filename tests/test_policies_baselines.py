import unittest
import sys
import os
import numpy as np
from collections import Counter

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vacsim.policies.baselines import (
    AlwaysLocal, AlwaysEdge, AlwaysCloud, RandomChoice,
    GreedyLatency, GreedyEnergy
)
from vacsim.policies.base import OffloadTarget, Decision, RobotState, NodeState, NetworkLink
from vacsim.sim.generator import Task
from vacsim.utils.latency import estimate_total_latency

class TestBaselinePolicies(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a sample task
        self.task = Task(
            id="test_task",
            arrival_time=0.0,
            size_bits=2_000_000,  # 2 Mb
            cpu_cycles=1_000_000_000,  # 1B cycles
            deadline_s=2.0  # 2 second deadline
        )
        
        # Create states
        self.robot = RobotState("robot", battery_soc=0.5, queue_length=0, estimated_wait_time=0.0)
        self.edge = NodeState("edge", queue_length=2, estimated_wait_time=0.1)
        self.cloud = NodeState("cloud", queue_length=5, estimated_wait_time=0.2)
        
        # Create network
        self.network = NetworkLink(
            uplink_rate_bps=5_000_000,  # 5 Mbps
            downlink_rate_bps=10_000_000,  # 10 Mbps
            latency_s=0.05  # 50ms latency
        )
        
        # Create policies
        self.always_local = AlwaysLocal()
        self.always_edge = AlwaysEdge()
        self.always_cloud = AlwaysCloud()
        self.random_choice = RandomChoice(seed=42)
        self.greedy_latency = GreedyLatency()
        self.greedy_energy = GreedyEnergy()
    
    def test_always_policies(self):
        """Test the 'Always' policies return their expected targets"""
        # AlwaysLocal should always return LOCAL
        decision = self.always_local.decide(
            self.task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.LOCAL)
        
        # AlwaysEdge should always return EDGE
        decision = self.always_edge.decide(
            self.task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.EDGE)
        
        # AlwaysCloud should always return CLOUD
        decision = self.always_cloud.decide(
            self.task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.CLOUD)
    
    def test_random_choice_distribution(self):
        """Test RandomChoice produces approximately uniform distribution"""
        # Create seeded policy for reproducibility
        random_policy = RandomChoice(seed=42)
        
        # Make many decisions and count occurrences
        decisions = []
        num_trials = 1000
        for _ in range(num_trials):
            decision = random_policy.decide(
                self.task, self.robot, self.edge, self.cloud, self.network
            )
            decisions.append(decision.target)
        
        # Count occurrences of each target
        counter = Counter(decisions)
        
        # Each target should occur approximately 1/3 of the time
        expected_count = num_trials / 3
        tolerance = num_trials * 0.1  # Allow 10% deviation
        
        self.assertAlmostEqual(counter[OffloadTarget.LOCAL], expected_count, delta=tolerance)
        self.assertAlmostEqual(counter[OffloadTarget.EDGE], expected_count, delta=tolerance)
        self.assertAlmostEqual(counter[OffloadTarget.CLOUD], expected_count, delta=tolerance)
    
    def test_random_choice_reproducibility(self):
        """Test RandomChoice produces the same sequence with the same seed"""
        # Create two policies with the same seed
        random_policy1 = RandomChoice(seed=123)
        random_policy2 = RandomChoice(seed=123)
        
        # Generate sequences of decisions
        decisions1 = []
        decisions2 = []
        for _ in range(10):
            d1 = random_policy1.decide(self.task, self.robot, self.edge, self.cloud, self.network)
            d2 = random_policy2.decide(self.task, self.robot, self.edge, self.cloud, self.network)
            decisions1.append(d1.target)
            decisions2.append(d2.target)
        
        # Both sequences should match
        self.assertEqual(decisions1, decisions2)
    
    def test_greedy_latency(self):
        """Test GreedyLatency chooses the option with lowest latency"""
        # Create a task where local would be fastest (small computation)
        small_task = Task(
            id="small_task",
            arrival_time=0.0,
            size_bits=10_000_000,  # 10 Mb (large data size)
            cpu_cycles=100_000,  # 100K cycles (minimal computation)
            deadline_s=1.0
        )
        
        decision = self.greedy_latency.decide(
            small_task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.LOCAL)
        
        # Create a task where edge would be fastest (medium computation, good network)
        medium_task = Task(
            id="medium_task",
            arrival_time=0.0,
            size_bits=1_000_000,  # 1 Mb (medium data size)
            cpu_cycles=5_000_000_000,  # 5B cycles (significant computation)
            deadline_s=2.0
        )
        
        decision = self.greedy_latency.decide(
            medium_task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.EDGE)
    
    def test_greedy_energy(self):
        """Test GreedyEnergy chooses the option with lowest energy consumption"""
        # Create a task where offloading would save energy (high computation)
        compute_heavy_task = Task(
            id="compute_heavy_task",
            arrival_time=0.0,
            size_bits=100_000,  # 100 Kb (small data size)
            cpu_cycles=10_000_000_000,  # 10B cycles (heavy computation)
            deadline_s=5.0
        )
        
        decision = self.greedy_energy.decide(
            compute_heavy_task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.EDGE)
        
        # Create a task where local would save energy (high data size, low computation)
        data_heavy_task = Task(
            id="data_heavy_task",
            arrival_time=0.0,
            size_bits=50_000_000,  # 50 Mb (large data size)
            cpu_cycles=100_000,  # 100K cycles (minimal computation)
            deadline_s=5.0
        )
        
        decision = self.greedy_energy.decide(
            data_heavy_task, self.robot, self.edge, self.cloud, self.network
        )
        self.assertEqual(decision.target, OffloadTarget.LOCAL)


def compare_policies():
    """Compare decisions from all policies for a single task"""
    # Create a task
    task = Task(
        id="comparison_task",
        arrival_time=0.0,
        size_bits=3_000_000,  # 3 Mb
        cpu_cycles=2_500_000_000,  # 2.5B cycles
        deadline_s=3.0  # 3 second deadline
    )
    
    # Create states
    robot = RobotState("robot", battery_soc=0.5, queue_length=0, estimated_wait_time=0.0)
    edge = NodeState("edge", queue_length=1, estimated_wait_time=0.05)
    cloud = NodeState("cloud", queue_length=3, estimated_wait_time=0.15)
    
    # Create network
    network = NetworkLink(
        uplink_rate_bps=6_000_000,  # 6 Mbps
        downlink_rate_bps=12_000_000,  # 12 Mbps
        latency_s=0.04  # 40ms latency
    )
    
    # Use the shared latency helper to calculate latencies
    local_latency = estimate_total_latency(OffloadTarget.LOCAL, task, robot, edge, cloud, network)
    edge_latency = estimate_total_latency(OffloadTarget.EDGE, task, robot, edge, cloud, network)
    cloud_latency = estimate_total_latency(OffloadTarget.CLOUD, task, robot, edge, cloud, network)
    
    # Create policies
    policies = {
        "AlwaysLocal": AlwaysLocal(),
        "AlwaysEdge": AlwaysEdge(),
        "AlwaysCloud": AlwaysCloud(),
        "RandomChoice(42)": RandomChoice(seed=42),
        "GreedyLatency": GreedyLatency(),
        "GreedyEnergy": GreedyEnergy()
    }
    
    # Get decisions
    print("\n=== Policy Comparison Table ===")
    print(f"Task: {task.size_bits/1000:.0f} Kbits, {task.cpu_cycles/1e6:.1f}M cycles, {task.deadline_s}s deadline")
    print(f"Latencies: LOCAL={local_latency:.3f}s, EDGE={edge_latency:.3f}s, CLOUD={cloud_latency:.3f}s")
    print("-" * 80)
    print(f"{'Policy':<16} | {'Decision':<8} | {'Reason'}")
    print("-" * 80)
    
    for name, policy in policies.items():
        decision = policy.decide(task, robot, edge, cloud, network)
        print(f"{name:<16} | {decision.target.name:<8} | {decision.reason[:50]}...")


if __name__ == "__main__":
    # Run tests
    unittest.main(exit=False)
    
    # Show policy comparison
    compare_policies()
