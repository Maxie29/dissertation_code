import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vacsim.policies.battery_aware import BatteryLevelAwarePolicy
from vacsim.policies.base import Decision, OffloadTarget, RobotState, NodeState, NetworkLink
from vacsim.sim.generator import Task

class TestBatteryAwarePolicy(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create policy with default thresholds
        self.policy = BatteryLevelAwarePolicy(
            low_soc_th=0.2, 
            high_soc_th=0.6,
            deadline_slack_s=0.2
        )
        
        # Create a sample task
        self.task = Task(
            id="test_task_1",
            arrival_time=0.0,
            size_bits=1_000_000,  # 1 Mb
            cpu_cycles=500_000_000,  # 500M cycles
            deadline_s=1.0  # 1 second deadline
        )
        
        # Create network state (good network)
        self.good_network = NetworkLink(
            uplink_rate_bps=10_000_000,  # 10 Mbps
            downlink_rate_bps=20_000_000,  # 20 Mbps
            latency_s=0.02  # 20ms latency
        )
        
        # Create a poor network
        self.poor_network = NetworkLink(
            uplink_rate_bps=500_000,  # 500 Kbps
            downlink_rate_bps=1_000_000,  # 1 Mbps
            latency_s=0.15  # 150ms latency
        )
        
        # Create edge and cloud states
        self.edge = NodeState("edge", queue_length=0, estimated_wait_time=0.0)
        self.cloud = NodeState("cloud", queue_length=0, estimated_wait_time=0.1)
    
    def test_init_with_invalid_thresholds(self):
        """Test initialization with invalid threshold values"""
        # Low threshold > high threshold
        with self.assertRaises(ValueError):
            BatteryLevelAwarePolicy(low_soc_th=0.7, high_soc_th=0.5)
        
        # Low threshold <= 0
        with self.assertRaises(ValueError):
            BatteryLevelAwarePolicy(low_soc_th=0.0, high_soc_th=0.5)
        
        # High threshold >= 1.0
        with self.assertRaises(ValueError):
            BatteryLevelAwarePolicy(low_soc_th=0.2, high_soc_th=1.0)
    
    def test_low_battery_decision(self):
        """Test decision with low battery level"""
        # Robot with low battery
        robot = RobotState("robot", battery_soc=0.1, queue_length=0, estimated_wait_time=0.0)
        
        # With good network
        decision = self.policy.decide(self.task, robot, self.edge, self.cloud, self.good_network)
        self.assertEqual(decision.target, OffloadTarget.EDGE, 
                         "With low battery and good network, should choose EDGE")
        
        # With poor network and tight deadline
        tight_deadline_task = Task(
            id="test_task_tight",
            arrival_time=0.0,
            size_bits=5_000_000,  # 5 Mb (larger task)
            cpu_cycles=900_000_000,  # 900M cycles (more compute)
            deadline_s=0.3  # Very tight deadline
        )
        decision = self.policy.decide(tight_deadline_task, robot, 
                                    self.edge, self.cloud, self.poor_network)
        self.assertEqual(decision.target, OffloadTarget.LOCAL,
                         "With low battery but poor network and tight deadline, should choose LOCAL")
    
    def test_threshold_edge_cases(self):
        """Test decisions at the threshold boundaries"""
        # At exactly low threshold
        robot_low = RobotState("robot", battery_soc=0.2, queue_length=0, estimated_wait_time=0.0)
        decision_low = self.policy.decide(self.task, robot_low, 
                                       self.edge, self.cloud, self.good_network)
        self.assertEqual(decision_low.target, OffloadTarget.EDGE,
                         "At low threshold, should choose EDGE")
        
        # At exactly high threshold
        robot_high = RobotState("robot", battery_soc=0.6, queue_length=0, estimated_wait_time=0.0)
        decision_high = self.policy.decide(self.task, robot_high, 
                                        self.edge, self.cloud, self.good_network)
        self.assertEqual(decision_high.target, OffloadTarget.LOCAL,
                         "At high threshold, should choose LOCAL")
        
        # Just below high threshold
        robot_below_high = RobotState("robot", battery_soc=0.599, 
                                    queue_length=0, estimated_wait_time=0.0)
        decision = self.policy.decide(self.task, robot_below_high, 
                                   self.edge, self.cloud, self.good_network)
        self.assertIn("MEDIUM BATTERY", decision.reason)


def demonstrate_policy():
    """Demonstrate policy decisions at different SOC levels"""
    # Create policy
    policy = BatteryLevelAwarePolicy(
        low_soc_th=0.2,
        high_soc_th=0.6,
        deadline_slack_s=0.2
    )
    
    # Create sample task
    task = Task(
        id="demo_task",
        arrival_time=0.0,
        size_bits=2_000_000,  # 2 Mb
        cpu_cycles=1_000_000_000,  # 1B cycles
        deadline_s=1.5  # 1.5 second deadline
    )
    
    # Create network state (moderate network)
    network = NetworkLink(
        uplink_rate_bps=5_000_000,  # 5 Mbps
        downlink_rate_bps=10_000_000,  # 10 Mbps
        latency_s=0.05  # 50ms latency
    )
    
    # Create edge and cloud states
    edge = NodeState("edge", queue_length=2, estimated_wait_time=0.1)
    cloud = NodeState("cloud", queue_length=5, estimated_wait_time=0.2)
    
    # Test with 3 battery levels
    soc_levels = [0.1, 0.4, 0.8]
    
    print("\n=== Battery-Aware Policy Demonstration ===")
    print(policy.explain())
    print("\n=== Decision Examples ===")
    
    for soc in soc_levels:
        robot = RobotState("robot", battery_soc=soc, queue_length=0, estimated_wait_time=0.0)
        decision = policy.decide(task, robot, edge, cloud, network)
        
        print(f"\nBattery SOC: {soc:.1f}")
        print(f"Decision: {decision.target.name}")
        print(f"Reason: {decision.reason}")
        print("-" * 50)


if __name__ == "__main__":
    # Run tests
    unittest.main(exit=False)
    
    # Demonstrate policy with examples
    demonstrate_policy()
