import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vacsim.models.nodes import BaseComputeNode, RobotNode, EdgeNode, CloudNode, NodeQueue

class TestNodes(unittest.TestCase):
    
    def test_zero_cycles(self):
        """Test computation with zero cycles"""
        node = BaseComputeNode("test", 1e9, 5, 10)
        self.assertEqual(node.exec_time_for(0), 0)
        self.assertEqual(node.energy_for(0), 0)
    
    def test_large_cycles(self):
        """Test computation with very large number of cycles"""
        node = BaseComputeNode("test", 1e9, 5, 10)
        # 10^15 cycles at 10^9 cycles/sec = 10^6 seconds = ~11.6 days
        cycles = 1e15
        self.assertAlmostEqual(node.exec_time_for(cycles), 1e6)
        # Power = 5 + (10-5) = 10W
        # Energy = Power * Time = 10W * 10^6s = 10^7 J
        self.assertAlmostEqual(node.energy_for(cycles), 1e7)
    
    def test_power_model(self):
        """Test linear power consumption model"""
        base_power = 5
        max_power = 15
        node = BaseComputeNode("test", 1e9, base_power, max_power)
        
        # Calculate power for different cycle counts
        cycles_1s = 1e9  # 1 second of computation
        energy_1s = node.energy_for(cycles_1s)
        power_1s = energy_1s / 1
        
        cycles_2s = 2e9  # 2 seconds of computation
        energy_2s = node.energy_for(cycles_2s)
        power_2s = energy_2s / 2
        
        # Power should be the same regardless of computation time
        # (assuming 100% utilization)
        self.assertAlmostEqual(power_1s, power_2s)
        
        # Power should be base_power + (max_power - base_power) = max_power
        # since we assume 100% utilization during execution
        self.assertAlmostEqual(power_1s, max_power)


def example_comparison():
    """Show example of time and energy estimates for 5e9 cycles on different nodes"""
    # Create sample nodes with realistic parameters
    robot = RobotNode("robot", 2e9, 2, 5)  # 2 GHz, 2-5W power
    edge = EdgeNode("edge", 3.5e9, 10, 35)  # 3.5 GHz, 10-35W power
    cloud = CloudNode("cloud", 5e9, 20, 65)  # 5 GHz, 20-65W power
    
    # Test workload
    cycles = 5e9
    
    # Calculate execution times
    robot_time = robot.exec_time_for(cycles)
    edge_time = edge.exec_time_for(cycles)
    cloud_time = cloud.exec_time_for(cycles)
    
    # Calculate energy consumption
    robot_energy = robot.energy_for(cycles)
    edge_energy = edge.energy_for(cycles)
    cloud_energy = cloud.energy_for(cycles)
    
    # Print results
    print("\nExecution time and energy comparison for 5e9 cycles:")
    print(f"Robot: {robot_time:.4f}s, {robot_energy:.2f}J")
    print(f"Edge:  {edge_time:.4f}s, {edge_energy:.2f}J")
    print(f"Cloud: {cloud_time:.4f}s, {cloud_energy:.2f}J")


if __name__ == "__main__":
    # Run tests
    unittest.main(exit=False)
    
    # Show example comparison
    example_comparison()
