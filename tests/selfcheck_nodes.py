# tests/selfcheck_nodes.py
from vacsim.models.nodes import BaseComputeNode, RobotNode, EdgeNode, CloudNode

def demo():
    # Using the parameters from test_nodes.py
    robot = RobotNode(name="robot", cpu_cycles_per_sec=2e9,  base_power_W=2.0,  max_power_W=5.0)
    edge  = EdgeNode(name="edge",  cpu_cycles_per_sec=3.5e9, base_power_W=10.0, max_power_W=35.0)
    cloud = CloudNode(name="cloud", cpu_cycles_per_sec=5e9, base_power_W=20.0, max_power_W=65.0)

    cycles = 5e9

    def show(node):
        t = node.exec_time_for(cycles)         # 秒
        e = node.energy_for(cycles)            # 焦耳
        print(f"{node.name:<5} | time = {t:.6f} s | energy = {e:.3f} J")
        return t, e

    print("=== 5e9 cycles estimation ===")
    tr, er = show(robot)
    te, ee = show(edge)
    tc, ec = show(cloud)

    # 简单 sanity check：更强算力 → 时间更短；能耗应在 [base*time, max*time] 区间
    print("\n=== Sanity checks ===")
    for node, t, e in [("robot", tr, er), ("edge", te, ee), ("cloud", tc, ec)]:
        if node == "robot":
            node_obj = robot
        elif node == "edge":
            node_obj = edge
        else:
            node_obj = cloud
            
        base_energy = node_obj.base_power_W * t
        max_energy = node_obj.max_power_W * t
        
        print(f"{node:<5} | Time: {t:.6f}s | Energy: {e:.3f}J | Range: [{base_energy:.3f}J, {max_energy:.3f}J]")
        if base_energy <= e <= max_energy:
            print(f"✅ Energy within expected range")
        else:
            print(f"❌ Energy outside expected range")
    
    print("\n=== Performance comparison ===")
    if tr > te > tc:
        print("✅ Cloud fastest, Edge second, Robot slowest (as expected)")
    else:
        print("❌ Unexpected performance ordering")

if __name__ == "__main__":
    demo()
