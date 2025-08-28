import random
import numpy as np
from vacsim.policies.base import OffloadingPolicy, Decision, OffloadTarget
from vacsim.policies.base import RobotState, NodeState, NetworkLink
from vacsim.sim.generator import Task
from vacsim.utils.latency import estimate_total_latency


class AlwaysLocal(OffloadingPolicy):
    """Policy that always executes tasks locally on the robot"""
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        reason = "Policy always chooses local execution"
        return Decision(OffloadTarget.LOCAL, reason)
    
    def explain(self) -> str:
        return "AlwaysLocal: Always executes tasks on the robot regardless of any conditions"


class AlwaysEdge(OffloadingPolicy):
    """Policy that always offloads tasks to the edge server"""
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        reason = "Policy always chooses edge execution"
        return Decision(OffloadTarget.EDGE, reason)
    
    def explain(self) -> str:
        return "AlwaysEdge: Always offloads tasks to the edge server regardless of any conditions"


class AlwaysCloud(OffloadingPolicy):
    """Policy that always offloads tasks to the cloud server"""
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        reason = "Policy always chooses cloud execution"
        return Decision(OffloadTarget.CLOUD, reason)
    
    def explain(self) -> str:
        return "AlwaysCloud: Always offloads tasks to the cloud server regardless of any conditions"


class RandomChoice(OffloadingPolicy):
    """Policy that randomly selects between local, edge, and cloud execution"""
    
    def __init__(self, seed: int = None):
        """
        Initialize random policy with optional seed
        
        Args:
            seed: Random seed for reproducibility (optional)
        """
        self.rng = np.random.default_rng(seed)
        self.seed = seed
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        targets = list(OffloadTarget)
        choice = self.rng.choice(targets)
        reason = f"Random choice (seed={self.seed}): selected {choice.name}"
        return Decision(choice, reason)
    
    def explain(self) -> str:
        return f"RandomChoice: Randomly selects between LOCAL, EDGE, and CLOUD execution (seed={self.seed})"


class GreedyLatency(OffloadingPolicy):
    """Policy that chooses the option with the lowest end-to-end latency"""
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
              cloud: NodeState, network: NetworkLink) -> Decision:
        """
        Make an offloading decision based on the lowest end-to-end latency.
        Uses a consistent latency calculation across all targets and applies
        a stable tie-breaking rule: LOCAL -> EDGE -> CLOUD.
        
        Args:
            task: Task to be offloaded
            robot: Current robot state
            edge: Current edge node state
            cloud: Current cloud node state
            network: Current network state
            
        Returns:
            Decision containing target and reason
        """
        # Define candidates in preference order for tie-breaking
        candidates = [OffloadTarget.LOCAL, OffloadTarget.EDGE, OffloadTarget.CLOUD]
        
        # Calculate latency for each target using shared helper
        lat = {}
        for target in candidates:
            lat[target] = estimate_total_latency(
                target, task, robot, edge, cloud, network
            )
        
        # Find best target with stable tie-breaking
        best = min(candidates, key=lambda t: (lat[t], candidates.index(t)))
        
        # Create reason string with calculated latencies
        reason = (
            f"Greedy latency choice: "
            f"LOCAL={lat[OffloadTarget.LOCAL]:.3f}s, "
            f"EDGE={lat[OffloadTarget.EDGE]:.3f}s, "
            f"CLOUD={lat[OffloadTarget.CLOUD]:.3f}s, "
            f"Selected {best.name}"
        )
        
        return Decision(best, reason)
    
    def explain(self) -> str:
        return "GreedyLatency: Selects the option with the lowest estimated end-to-end latency. When latencies are very close, prefers LOCAL → EDGE → CLOUD."


class GreedyEnergy(OffloadingPolicy):
    """Policy that chooses the option with the lowest energy consumption on the robot"""
    
    def _estimate_local_energy(self, task: Task) -> float:
        """Estimate energy consumption for local execution"""
        # Simple energy model: 1 nJ per cycle
        energy_per_cycle = 1e-9
        return task.cpu_cycles * energy_per_cycle
    
    def _estimate_edge_energy(self, task: Task, network: NetworkLink) -> float:
        """Estimate energy consumption for edge execution (on robot)"""
        # Energy for data transfer only (robot side)
        tx_energy_per_bit = 1e-7  # 100 nJ per bit
        rx_energy_per_bit = 5e-8  # 50 nJ per bit
        
        result_size = task.size_bits / 10  # Assume result is 1/10 the input size
        return (task.size_bits * tx_energy_per_bit) + (result_size * rx_energy_per_bit)
    
    def _estimate_cloud_energy(self, task: Task, network: NetworkLink) -> float:
        """Estimate energy consumption for cloud execution (on robot)"""
        # Energy for data transfer only (robot side), higher than edge
        tx_energy_per_bit = 1.2e-7  # 120 nJ per bit
        rx_energy_per_bit = 6e-8  # 60 nJ per bit
        
        result_size = task.size_bits / 10
        return (task.size_bits * tx_energy_per_bit) + (result_size * rx_energy_per_bit)
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        # Estimate energy consumption for each option
        local_energy = self._estimate_local_energy(task)
        edge_energy = self._estimate_edge_energy(task, network)
        cloud_energy = self._estimate_cloud_energy(task, network)
        
        # Find option with minimum energy consumption
        energies = {
            OffloadTarget.LOCAL: local_energy,
            OffloadTarget.EDGE: edge_energy,
            OffloadTarget.CLOUD: cloud_energy
        }
        
        best_target = min(energies, key=energies.get)
        
        reason = (
            f"Greedy energy choice: LOCAL={local_energy:.6f}J, "
            f"EDGE={edge_energy:.6f}J, CLOUD={cloud_energy:.6f}J, "
            f"Selected {best_target.name} (lowest energy)"
        )
        
        return Decision(best_target, reason)
    
    def explain(self) -> str:
        return "GreedyEnergy: Selects the option with the lowest estimated energy consumption on the robot"
        if len(candidates) > 1:
            for target in preference_order:
                if target in candidates:
                    best_target = target
                    break
        else:
            # Otherwise, just use the minimum latency target
            best_target = min(latencies, key=latencies.get)
        
        # Create reason string with all the calculated latencies
        reason = (
            f"Greedy latency choice: LOCAL={latencies[OffloadTarget.LOCAL]:.3f}s, "
            f"EDGE={latencies[OffloadTarget.EDGE]:.3f}s, "
            f"CLOUD={latencies[OffloadTarget.CLOUD]:.3f}s, "
            f"Selected {best_target.name}"
        )
        
        # Add explanation if tie-breaking was used
        if len(candidates) > 1:
            reason += f" (latencies within {epsilon}s, using preference order)"
        else:
            reason += " (lowest latency)"
        
        return Decision(best_target, reason)
    
    def explain(self) -> str:
        return "GreedyLatency: Selects the option with the lowest estimated end-to-end latency. When latencies are very close, prefers LOCAL → EDGE → CLOUD."


class GreedyEnergy(OffloadingPolicy):
    """Policy that chooses the option with the lowest energy consumption on the robot"""
    
    def _estimate_local_energy(self, task: Task) -> float:
        """Estimate energy consumption for local execution"""
        # Simple energy model: 1 nJ per cycle
        energy_per_cycle = 1e-9
        return task.cpu_cycles * energy_per_cycle
    
    def _estimate_edge_energy(self, task: Task, network: NetworkLink) -> float:
        """Estimate energy consumption for edge execution (on robot)"""
        # Energy for data transfer only (robot side)
        tx_energy_per_bit = 1e-7  # 100 nJ per bit
        rx_energy_per_bit = 5e-8  # 50 nJ per bit
        
        result_size = task.size_bits / 10  # Assume result is 1/10 the input size
        return (task.size_bits * tx_energy_per_bit) + (result_size * rx_energy_per_bit)
    
    def _estimate_cloud_energy(self, task: Task, network: NetworkLink) -> float:
        """Estimate energy consumption for cloud execution (on robot)"""
        # Energy for data transfer only (robot side), higher than edge
        tx_energy_per_bit = 1.2e-7  # 120 nJ per bit
        rx_energy_per_bit = 6e-8  # 60 nJ per bit
        
        result_size = task.size_bits / 10
        return (task.size_bits * tx_energy_per_bit) + (result_size * rx_energy_per_bit)
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
               cloud: NodeState, network: NetworkLink) -> Decision:
        # Estimate energy consumption for each option
        local_energy = self._estimate_local_energy(task)
        edge_energy = self._estimate_edge_energy(task, network)
        cloud_energy = self._estimate_cloud_energy(task, network)
        
        # Find option with minimum energy consumption
        energies = {
            OffloadTarget.LOCAL: local_energy,
            OffloadTarget.EDGE: edge_energy,
            OffloadTarget.CLOUD: cloud_energy
        }
        
        best_target = min(energies, key=energies.get)
        
        reason = (
            f"Greedy energy choice: LOCAL={local_energy:.6f}J, "
            f"EDGE={edge_energy:.6f}J, CLOUD={cloud_energy:.6f}J, "
            f"Selected {best_target.name} (lowest energy)"
        )
        
        return Decision(best_target, reason)
    
    def explain(self) -> str:
        return "GreedyEnergy: Selects the option with the lowest estimated energy consumption on the robot"
