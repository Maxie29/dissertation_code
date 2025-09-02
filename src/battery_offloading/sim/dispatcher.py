"""
Task dispatch and execution module.

This module implements the core dispatch logic that routes tasks to appropriate
execution sites based on policy decisions and handles the execution simulation
including energy consumption tracking.
"""

from typing import Dict, Any, Optional
import simpy
from ..task import Task
from ..battery import Battery
from ..policy import decide_site
from ..enums import Site
from ..energy import PowerParameters, estimate_local_compute_time, estimate_remote_compute_time, estimate_comm_time, estimate_robot_energy
from .resources import ResourceStation
from .network import Network


class Dispatcher:
    """
    Dispatches tasks to execution sites and simulates their execution.
    
    The Dispatcher integrates policy decisions with resource simulation,
    handling both local execution and remote offloading scenarios.
    It tracks energy consumption and updates battery state accordingly.
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        battery: Battery,
        local_station: ResourceStation,
        edge_station: ResourceStation,
        cloud_station: ResourceStation,
        edge_network: Network,
        cloud_network: Network,
        config=None
    ):
        """
        Initialize dispatcher with all required components.
        
        Args:
            env: SimPy simulation environment
            battery: Battery model for SoC tracking
            local_station: Local computation resource
            edge_station: Edge computation resource  
            cloud_station: Cloud computation resource
            edge_network: Network connection to edge
            cloud_network: Network connection to cloud
        """
        self.env = env
        self.battery = battery
        self.stations = {
            Site.LOCAL: local_station,
            Site.EDGE: edge_station,
            Site.CLOUD: cloud_station
        }
        self.networks = {
            Site.EDGE: edge_network,
            Site.CLOUD: cloud_network
        }
        
        # Power parameters for energy calculations
        if config is not None:
            self.power_params = PowerParameters(
                active_local_mw=config.power.active_local_mw,
                tx_mw=config.power.tx_mw,
                rx_mw=config.power.rx_mw,
                idle_mw=config.power.idle_mw
            )
        else:
            # Default power parameters
            self.power_params = PowerParameters(
                active_local_mw=2000.0,  # 2W for local compute
                tx_mw=800.0,  # 0.8W for transmission
                rx_mw=400.0,  # 0.4W for reception
                idle_mw=100.0  # 0.1W idle
            )
        
        # Dispatch statistics
        self.total_dispatched = 0
        self.site_counts = {Site.LOCAL: 0, Site.EDGE: 0, Site.CLOUD: 0}
    
    def dispatch(self, task: Task, now_soc: float):
        """
        Dispatch a single task and simulate its execution.
        
        This method implements the core dispatch logic:
        1. Use policy to decide execution site based on current SoC
        2. Execute task locally or remotely with appropriate timing/energy
        3. Update battery state with consumed energy
        4. Return execution record with all relevant metrics
        
        Args:
            task: Task to be dispatched
            now_soc: Current battery state of charge (0-100%)
            
        Returns:
            Dictionary containing execution record with fields:
            - task_id, task_type, execution_site
            - latency_ms, energy_wh_delta, soc_before, soc_after
            - deadline_ms, missed_deadline (if task has deadline)
            - network_up_ms, network_down_ms (for remote execution)
            - compute_time_ms, queue_wait_ms
            
        Examples:
        >>> env = simpy.Environment()
        >>> battery = Battery(capacity_wh=100.0, initial_soc=80.0)
        >>> # ... create stations and networks ...
        >>> dispatcher = Dispatcher(env, battery, local_station, edge_station, cloud_station, edge_network, cloud_network)
        >>> 
        >>> task = Task(1, TaskType.GENERIC, 1024*1024, 1000000.0, 0.0)
        >>> record = dispatcher.dispatch(task, battery.soc)
        >>> record['execution_site']  
        'edge'  # or 'local'/'cloud' based on policy
        >>> record['latency_ms'] > 0
        True
        """
        # Record initial state
        soc_before = now_soc
        start_time = self.env.now
        
        # Step 1: Policy decision
        execution_site = decide_site(task, now_soc)
        
        # Initialize record
        record = {
            'task_id': task.id,
            'task_type': task.type.name,
            'execution_site': execution_site.name.lower(),
            'soc_before': soc_before,
            'dispatch_time': start_time,
            'task_size_bytes': task.size_bytes,
            'compute_demand': task.compute_demand,
            'deadline_ms': task.deadline_ms if task.deadline_ms is not None else -1,
            'network_up_ms': 0.0,
            'network_down_ms': 0.0,
            'compute_time_ms': 0.0,
            'queue_wait_ms': 0.0
        }
        
        # Step 2: Execute based on site decision
        if execution_site == Site.LOCAL:
            # Local execution: only computation time and energy
            latency_ms, energy_wh = yield from self._execute_local(task)
            record['compute_time_ms'] = latency_ms
            
        else:  # EDGE or CLOUD
            # Remote execution: communication + computation
            latency_ms, energy_wh, net_up_ms, net_down_ms, comp_ms, queue_ms = yield from self._execute_remote(task, execution_site)
            record['network_up_ms'] = net_up_ms
            record['network_down_ms'] = net_down_ms  
            record['compute_time_ms'] = comp_ms
            record['queue_wait_ms'] = queue_ms
        
        # Step 3: Update battery and finalize record
        self.battery.consume_energy_wh(energy_wh, f"task_{task.id}_{execution_site.name.lower()}")
        
        record.update({
            'latency_ms': latency_ms,
            'energy_wh_delta': energy_wh,
            'soc_after': self.battery.get_soc(),
            'finish_time': self.env.now + latency_ms / 1000.0  # Convert ms to seconds
        })
        
        # Check deadline if specified
        if task.deadline_ms is not None:
            record['missed_deadline'] = latency_ms > task.deadline_ms
        else:
            record['missed_deadline'] = False
            
        # Update statistics
        self.total_dispatched += 1
        self.site_counts[execution_site] += 1
        
        return record
    
    def _execute_local(self, task: Task):
        """
        Execute task locally (SimPy generator).
        
        Args:
            task: Task to execute
            
        Yields:
            Tuple of (latency_ms, energy_wh)
        """
        # Get local station and simulate processing
        station = self.stations[Site.LOCAL]
        
        # Use SimPy to simulate processing time including queueing
        start_time = self.env.now
        finish_time, service_time_sec = yield from station.process(task)
        actual_latency_sec = finish_time - start_time
        
        # Convert to milliseconds
        latency_ms = actual_latency_sec * 1000.0
        
        # Calculate energy consumption (robot-side only)
        energy_wh = estimate_robot_energy(
            task=task,
            execution_site=Site.LOCAL,
            power_params=self.power_params,
            local_compute_time_s=service_time_sec
        )
        
        return latency_ms, energy_wh
    
    def _execute_remote(self, task: Task, site: Site):
        """
        Execute task remotely (EDGE or CLOUD) (SimPy generator).
        
        Args:
            task: Task to execute
            site: Remote execution site (EDGE or CLOUD)
            
        Yields:
            Tuple of (total_latency_ms, energy_wh, network_up_ms, network_down_ms, compute_ms, queue_wait_ms)
        """
        network = self.networks[site]
        station = self.stations[site]
        
        # Step 1: Upload task data
        up_result = network.uplink_time(task.size_bytes)
        upload_time_ms = up_result.total_time * 1000.0
        
        # Step 2: Simulate upload delay
        yield self.env.timeout(up_result.total_time)
        
        # Step 3: Remote computation with queueing
        compute_start_time = self.env.now
        finish_time, service_time_sec = yield from station.process(task)
        queue_wait_sec = finish_time - compute_start_time - service_time_sec
        
        compute_time_ms = service_time_sec * 1000.0
        queue_wait_ms = max(0.0, queue_wait_sec * 1000.0)
        
        # Step 4: Download results (assume 1% of input size)
        result_size = max(1024, task.size_bytes // 100)  # At least 1KB
        down_result = network.downlink_time(result_size)
        download_time_ms = down_result.total_time * 1000.0
        
        # Step 5: Simulate download delay
        yield self.env.timeout(down_result.total_time)
        
        # Total latency
        total_latency_ms = upload_time_ms + queue_wait_ms + compute_time_ms + download_time_ms
        
        # Energy consumption (robot-side communication only)
        from ..energy import ComputationTimes
        comm_times = ComputationTimes(
            uplink_s=up_result.total_time,
            downlink_s=down_result.total_time,
            total_comm_s=up_result.total_time + down_result.total_time
        )
        
        energy_wh = estimate_robot_energy(
            task=task,
            execution_site=site,
            power_params=self.power_params,
            local_compute_time_s=0.0,  # No local compute for remote execution
            comm_times=comm_times
        )
        
        return total_latency_ms, energy_wh, upload_time_ms, download_time_ms, compute_time_ms, queue_wait_ms
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get dispatcher statistics.
        
        Returns:
            Dictionary with dispatch statistics
        """
        if self.total_dispatched == 0:
            return {
                'total_dispatched': 0,
                'local_ratio': 0.0,
                'edge_ratio': 0.0,
                'cloud_ratio': 0.0,
                'battery_soc': self.battery.get_soc()
            }
        
        return {
            'total_dispatched': self.total_dispatched,
            'local_count': self.site_counts[Site.LOCAL],
            'edge_count': self.site_counts[Site.EDGE],
            'cloud_count': self.site_counts[Site.CLOUD],
            'local_ratio': self.site_counts[Site.LOCAL] / self.total_dispatched,
            'edge_ratio': self.site_counts[Site.EDGE] / self.total_dispatched,
            'cloud_ratio': self.site_counts[Site.CLOUD] / self.total_dispatched,
            'battery_soc': self.battery.get_soc()
        }
    
    def reset(self):
        """Reset dispatcher statistics."""
        self.total_dispatched = 0
        self.site_counts = {Site.LOCAL: 0, Site.EDGE: 0, Site.CLOUD: 0}
        
        # Reset station statistics
        for station in self.stations.values():
            station.reset_stats()


# Helper function for creating dispatcher from configuration
def create_dispatcher_from_config(env: simpy.Environment, config, battery: Battery, stations: dict, networks: dict) -> Dispatcher:
    """
    Create dispatcher from configuration.
    
    Args:
        env: SimPy environment
        config: Configuration object
        battery: Battery instance
        stations: Dictionary mapping Site to ResourceStation
        networks: Dictionary mapping Site to Network
        
    Returns:
        Configured Dispatcher instance
    """
    return Dispatcher(
        env=env,
        battery=battery,
        local_station=stations[Site.LOCAL],
        edge_station=stations[Site.EDGE], 
        cloud_station=stations[Site.CLOUD],
        edge_network=networks[Site.EDGE],
        cloud_network=networks[Site.CLOUD]
    )


__all__ = ['Dispatcher', 'create_dispatcher_from_config']