from vacsim.policies.base import OffloadingPolicy, Decision, OffloadTarget
from vacsim.policies.base import RobotState, NodeState, NetworkLink
from vacsim.sim.generator import Task


class BatteryLevelAwarePolicy(OffloadingPolicy):
    """
    Offloading policy that makes decisions based on battery state of charge (SOC)
    and task deadline requirements.
    """
    
    def __init__(self, low_soc_th: float = 0.2, high_soc_th: float = 0.6, 
                 deadline_slack_s: float = 0.2):
        """
        Initialize battery-aware policy
        
        Args:
            low_soc_th: Threshold for low battery state of charge (0.0 to 1.0)
            high_soc_th: Threshold for high battery state of charge (0.0 to 1.0)
            deadline_slack_s: Slack time in seconds to consider a deadline tight
        """
        if not 0 < low_soc_th < high_soc_th < 1.0:
            raise ValueError("Thresholds must satisfy: 0 < low_soc_th < high_soc_th < 1.0")
        
        self.low_soc_th = low_soc_th
        self.high_soc_th = high_soc_th
        self.deadline_slack_s = deadline_slack_s
    
    def _estimate_local_execution(self, task: Task, robot: RobotState) -> tuple:
        """
        Estimate time and energy for local execution
        
        Returns:
            Tuple of (total_time, energy)
        """
        # Simplified model: assume robot processes at 1 GHz
        cycles_per_sec = 1e9  
        execution_time = task.cpu_cycles / cycles_per_sec
        queue_time = robot.estimated_wait_time
        total_time = queue_time + execution_time
        
        # Simple energy model: 1 nJ per cycle
        energy_per_cycle = 1e-9  
        energy = task.cpu_cycles * energy_per_cycle
        
        return total_time, energy
    
    def _estimate_edge_execution(self, task: Task, edge: NodeState, 
                                network: NetworkLink) -> tuple:
        """
        Estimate time and energy for edge execution
        
        Returns:
            Tuple of (total_time, energy_on_robot)
        """
        # Calculate transfer times
        uplink_time = network.calculate_transfer_time(task.size_bits, is_uplink=True)
        result_size = task.size_bits / 10  # Assume result is 1/10 the input size
        downlink_time = network.calculate_transfer_time(result_size, is_uplink=False)
        
        # Edge processing (assume 3 GHz)
        edge_cycles_per_sec = 3e9
        edge_execution_time = task.cpu_cycles / edge_cycles_per_sec
        edge_queue_time = edge.estimated_wait_time
        
        # Total time
        total_time = uplink_time + edge_queue_time + edge_execution_time + downlink_time
        
        # Energy on robot (only for data transfer)
        tx_energy_per_bit = 1e-7  # 100 nJ per bit
        rx_energy_per_bit = 5e-8  # 50 nJ per bit
        energy = (task.size_bits * tx_energy_per_bit) + (result_size * rx_energy_per_bit)
        
        return total_time, energy
    
    def _estimate_cloud_execution(self, task: Task, cloud: NodeState, 
                                network: NetworkLink) -> tuple:
        """
        Estimate time and energy for cloud execution
        
        Returns:
            Tuple of (total_time, energy_on_robot)
        """
        # Calculate transfer times (assume double latency compared to edge)
        uplink_time = network.calculate_transfer_time(task.size_bits, is_uplink=True) * 1.5
        result_size = task.size_bits / 10  
        downlink_time = network.calculate_transfer_time(result_size, is_uplink=False) * 1.5
        
        # Cloud processing (assume 5 GHz)
        cloud_cycles_per_sec = 5e9
        cloud_execution_time = task.cpu_cycles / cloud_cycles_per_sec
        cloud_queue_time = cloud.estimated_wait_time
        
        total_time = uplink_time + cloud_queue_time + cloud_execution_time + downlink_time
        
        # Energy on robot (only for data transfer, higher for cloud)
        tx_energy_per_bit = 1.2e-7  # 120 nJ per bit
        rx_energy_per_bit = 6e-8  # 60 nJ per bit
        energy = (task.size_bits * tx_energy_per_bit) + (result_size * rx_energy_per_bit)
        
        return total_time, energy
    
    def _is_deadline_tight(self, task: Task, execution_time: float) -> bool:
        """
        Check if the task deadline is tight compared to execution time
        
        Returns:
            True if deadline is tight, False otherwise
        """
        return task.deadline_s < execution_time + self.deadline_slack_s
    
    def decide(self, task: Task, robot: RobotState, edge: NodeState, 
              cloud: NodeState, network: NetworkLink) -> Decision:
        """
        Make offloading decision based on battery SOC and task requirements
        
        Strategy:
        1) If SOC <= low_threshold: Prioritize EDGE (if network is good and deadline permits)
           Otherwise, use LOCAL if network is poor and deadline is tight
        2) If low_threshold < SOC < high_threshold: Compare end-to-end latencies
           and choose the lower energy option when latencies are similar
        3) If SOC >= high_threshold: Prioritize LOCAL (unless deadline is tight)
        
        Returns:
            Decision with target and reason
        """
        # Get current battery state
        soc = robot.battery_soc
        
        # Estimate execution times and energy for each option
        local_time, local_energy = self._estimate_local_execution(task, robot)
        edge_time, edge_energy = self._estimate_edge_execution(task, edge, network)
        cloud_time, cloud_energy = self._estimate_cloud_execution(task, cloud, network)
        
        # Check if deadline is feasible
        local_deadline_ok = local_time <= task.deadline_s
        edge_deadline_ok = edge_time <= task.deadline_s
        
        # Network quality check
        poor_network = network.latency_s > 0.1 or network.uplink_rate_bps < 1e6
        
        # Format a summary for the reason string
        options_summary = (
            f"LOCAL: {local_time:.3f}s, {local_energy:.6f}J | "
            f"EDGE: {edge_time:.3f}s, {edge_energy:.6f}J | "
            f"SOC: {soc:.2f} | Deadline: {task.deadline_s:.3f}s"
        )
        
        # Rule 1: Low battery - prioritize energy saving with EDGE
        if soc <= self.low_soc_th:
            if poor_network and self._is_deadline_tight(task, edge_time):
                # Poor network and tight deadline: use LOCAL
                reason = f"LOW BATTERY ({soc:.2f}) with POOR NETWORK and TIGHT DEADLINE. " + options_summary
                return Decision(OffloadTarget.LOCAL, reason)
            else:
                # Use EDGE to save energy
                reason = f"LOW BATTERY ({soc:.2f}) - prioritizing energy saving with EDGE. " + options_summary
                return Decision(OffloadTarget.EDGE, reason)
        
        # Rule 3: High battery - prioritize LOCAL execution
        elif soc >= self.high_soc_th:
            if self._is_deadline_tight(task, local_time) and edge_deadline_ok:
                # Tight deadline and edge can meet it: use EDGE
                reason = f"HIGH BATTERY ({soc:.2f}) but TIGHT DEADLINE - using EDGE. " + options_summary
                return Decision(OffloadTarget.EDGE, reason)
            else:
                # Use LOCAL since battery is high
                reason = f"HIGH BATTERY ({soc:.2f}) - prioritizing LOCAL execution. " + options_summary
                return Decision(OffloadTarget.LOCAL, reason)
        
        # Rule 2: Medium battery - compare latency and energy
        else:
            # Calculate latency difference ratio
            if local_time > 0:
                latency_diff_ratio = abs(edge_time - local_time) / local_time
            else:
                latency_diff_ratio = 1.0
                
            # If latencies are similar (within 20%)
            if latency_diff_ratio < 0.2:
                # Choose the option with lower energy
                if edge_energy < local_energy:
                    reason = f"MEDIUM BATTERY ({soc:.2f}) - SIMILAR LATENCIES, EDGE uses less energy. " + options_summary
                    return Decision(OffloadTarget.EDGE, reason)
                else:
                    reason = f"MEDIUM BATTERY ({soc:.2f}) - SIMILAR LATENCIES, LOCAL uses less energy. " + options_summary
                    return Decision(OffloadTarget.LOCAL, reason)
            else:
                # Choose the option with lower latency
                if edge_time < local_time:
                    reason = f"MEDIUM BATTERY ({soc:.2f}) - EDGE has lower latency. " + options_summary
                    return Decision(OffloadTarget.EDGE, reason)
                else:
                    reason = f"MEDIUM BATTERY ({soc:.2f}) - LOCAL has lower latency. " + options_summary
                    return Decision(OffloadTarget.LOCAL, reason)
    
    def explain(self) -> str:
        """
        Provide an explanation of the policy
        
        Returns:
            Description of the policy and its thresholds
        """
        return (
            f"Battery-aware offloading policy with thresholds:\n"
            f"- Low battery threshold: {self.low_soc_th:.2f}\n"
            f"- High battery threshold: {self.high_soc_th:.2f}\n"
            f"- Deadline slack: {self.deadline_slack_s:.2f}s\n\n"
            f"Decision logic:\n"
            f"1) When battery <= {self.low_soc_th:.2f}: Prioritize EDGE to save energy\n"
            f"   (unless network is poor and deadline is tight, then use LOCAL)\n"
            f"2) When {self.low_soc_th:.2f} < battery < {self.high_soc_th:.2f}: "
            f"Compare end-to-end latency and energy consumption\n"
            f"3) When battery >= {self.high_soc_th:.2f}: Prioritize LOCAL execution\n"
            f"   (unless deadline is tight and EDGE can meet it)"
        )
