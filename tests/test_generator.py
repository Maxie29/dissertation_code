import unittest
import numpy as np
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vacsim.sim.generator import TaskGenerator, TaskConfig, Task

class TestTaskGenerator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a fixed seed RNG for reproducible tests
        self.seed = 42
        self.rng = np.random.default_rng(self.seed)
        
        # Create a sample task configuration
        self.config = TaskConfig(
            mean_arrival_rate_hz=10.0,  # 10 tasks per second on average
            
            size_kbits_dist="lognormal",
            size_kbits_params={"mu": 3.0, "sigma": 1.0},
            
            cycles_dist="exp",
            cycles_params={"mean": 1e9},  # 1 billion cycles on average
            
            deadline_s_dist="normal_clipped",
            deadline_s_params={"mean": 2.0, "stddev": 0.5, "min_value": 0.5}
        )
        
        # Create the task generator
        self.generator = TaskGenerator(self.config, self.rng)
    
    def test_task_generation(self):
        """Test that tasks are generated with expected properties"""
        # Generate 1000 tasks for statistical testing
        num_tasks = 1000
        tasks = self.generator.generate_tasks(num_tasks)
        
        # Check that we got the expected number of tasks
        self.assertEqual(len(tasks), num_tasks)
        
        # Check that task IDs are unique and properly formatted
        task_ids = [task.id for task in tasks]
        self.assertEqual(len(set(task_ids)), num_tasks)
        
        # Check that arrival times are monotonically increasing
        arrival_times = [task.arrival_time for task in tasks]
        self.assertTrue(all(arrival_times[i] <= arrival_times[i+1] for i in range(num_tasks-1)))
        
        # Calculate mean inter-arrival time and compare with expected value
        inter_arrival_times = [arrival_times[i+1] - arrival_times[i] for i in range(num_tasks-1)]
        mean_inter_arrival = np.mean(inter_arrival_times)
        expected_mean = 1.0 / self.config.mean_arrival_rate_hz
        
        # Should be within 20% of expected mean for a large sample
        self.assertAlmostEqual(mean_inter_arrival, expected_mean, delta=expected_mean*0.2)
        
        # Check size distribution
        size_bits_mean = np.mean([task.size_bits for task in tasks])
        # We don't do exact comparisons since distributions have randomness
        self.assertTrue(size_bits_mean > 0)
        
        # Check cycles distribution
        cycles_mean = np.mean([task.cpu_cycles for task in tasks])
        # Expected mean should be close to config parameter
        expected_cycles_mean = self.config.cycles_params["mean"]
        self.assertAlmostEqual(cycles_mean, expected_cycles_mean, delta=expected_cycles_mean*0.2)
        
        # Check deadline distribution
        deadline_mean = np.mean([task.deadline_s for task in tasks])
        # Expected deadline should be positive
        self.assertTrue(deadline_mean > 0)


def display_sample_tasks():
    """Display the first 5 generated tasks with a fixed seed"""
    # Use fixed seed for reproducible output
    rng = np.random.default_rng(42)
    
    # Create sample task configuration
    config = TaskConfig(
        mean_arrival_rate_hz=5.0,  # 5 tasks per second on average
        
        size_kbits_dist="lognormal",
        size_kbits_params={"mu": 3.0, "sigma": 1.0},
        
        cycles_dist="exp",
        cycles_params={"mean": 5e8},  # 500 million cycles on average
        
        deadline_s_dist="normal_clipped",
        deadline_s_params={"mean": 1.0, "stddev": 0.3, "min_value": 0.2}
    )
    
    # Create generator and generate 5 tasks
    generator = TaskGenerator(config, rng)
    tasks = generator.generate_tasks(5)
    
    # Print task details
    print("\n=== First 5 Generated Tasks ===")
    for i, task in enumerate(tasks):
        print(f"Task {i+1}:")
        print(f"  ID: {task.id}")
        print(f"  Arrival Time: {task.arrival_time:.6f}s")
        print(f"  Size: {task.size_bits} bits ({task.size_bits/1000:.2f} kbits)")
        print(f"  CPU Cycles: {task.cpu_cycles}")
        print(f"  Deadline: {task.deadline_s:.6f}s")


if __name__ == "__main__":
    # Run tests
    unittest.main(exit=False)
    
    # Display sample tasks
    display_sample_tasks()
