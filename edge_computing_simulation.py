"""
Edge Computing Network Simulation — Discrete Time-Step Model
Topology: 5 heterogeneous Edge Nodes + 100 max User Devices
Algorithms: Round Robin, Random, Least Loaded, Weighted Load Balancing
Metrics: Avg Latency, Throughput, CPU Utilization, Packet Loss Rate
"""

import numpy as np
import random
import csv
import os
from dataclasses import dataclass, field
from typing import List

# ─── Tham số mô phỏng  ─────────
SIMULATION_TIME   = 1000      # total simulation seconds
TIME_STEP         = 1.0       # seconds per step
BANDWIDTH_MBPS    = 100
BASE_DELAY_MS     = 5         # edge propagation delay
QUEUE_CAPACITY    = 30        # max tasks queued per node before dropping
RANDOM_SEED       = 42

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

NUM_STEPS = int(SIMULATION_TIME / TIME_STEP)


# ─── Mô hình Edge Node ────────
@dataclass
class EdgeNode:
    node_id:      int
    cpu_capacity: float    # MIPS — how many MIPS this node can process per second
    weight:       float    # for Weighted LB

    queue:         List[float] = field(default_factory=list)   # list of cpu_required per queued task
    cpu_used_hist: List[float] = field(default_factory=list)
    latencies:     List[float] = field(default_factory=list)
    dropped:       int = 0
    completed:     int = 0
    total_data_mb: float = 0.0

    @property
    def queue_size(self) -> int:
        return len(self.queue)

    @property
    def current_load_mips(self) -> float:
        return sum(self.queue)

    @property
    def cpu_utilization(self) -> float:
        if not self.cpu_used_hist:
            return 0.0
        return np.mean(self.cpu_used_hist)

    def step_process(self, time_step: float):
        """Process tasks proportional to CPU capacity during one time step."""
        budget = self.cpu_capacity * time_step   # total MIPS available this step
        used = 0.0
        completed_this_step = 0

        while self.queue and budget > 0:
            cpu_needed = self.queue[0]
            if cpu_needed <= budget:
                budget -= cpu_needed
                used += cpu_needed
                self.queue.pop(0)
                completed_this_step += 1
                self.completed += 1
            else:
                # Partially process the head task
                self.queue[0] -= budget
                used += budget
                budget = 0

        utilization = min(used / (self.cpu_capacity * time_step), 1.0)
        self.cpu_used_hist.append(utilization)


# ───  Mô hình Task ───────────────────────────────────────
@dataclass
class Task:
    task_id:      int
    cpu_required: float   # MIPS needed total
    data_size_kb: float
    arrive_step:  int


# ───  Sinh tác vụ theo kịch bản ─
def generate_tasks_by_step(num_users: int) -> List[List[Task]]:
    """Returns tasks_per_step[step] = list of tasks arriving at that step."""
    tasks_per_step: List[List[Task]] = [[] for _ in range(NUM_STEPS)]
    task_id = 0
    # Poisson arrivals per step
    lam = num_users * 0.5 * TIME_STEP   # expected tasks per step

    for step in range(NUM_STEPS):
        n_arrive = np.random.poisson(lam)
        for _ in range(n_arrive):
            tasks_per_step[step].append(Task(
                task_id=task_id,
                cpu_required=np.random.uniform(100, 1200),
                data_size_kb=np.random.uniform(10, 500),
                arrive_step=step,
            ))
            task_id += 1
    return tasks_per_step


# ───  Cấu hình 5 edge node dị đồng  ────────────
def create_edge_nodes() -> List[EdgeNode]:
    configs = [
        (0, 2000, 1.0),
        (1, 3000, 1.5),
        (2, 2500, 1.2),
        (3, 1500, 0.8),
        (4, 3500, 1.8),
    ]
    return [EdgeNode(node_id=i, cpu_capacity=cap, weight=w) for i, cap, w in configs]


def reset_nodes(nodes: List[EdgeNode]):
    for n in nodes:
        n.queue.clear()
        n.cpu_used_hist.clear()
        n.latencies.clear()
        n.dropped = 0
        n.completed = 0
        n.total_data_mb = 0.0


# ───  Mô hình độ trễ: 
def compute_latency_ms(node: EdgeNode, task: Task) -> float:
    tx_ms      = (task.data_size_kb * 8) / BANDWIDTH_MBPS          # transmission
    prop_ms    = BASE_DELAY_MS                                       # propagation
    queue_ms   = node.queue_size * (task.cpu_required / node.cpu_capacity) * 1000  # queuing
    proc_ms    = (task.cpu_required / node.cpu_capacity) * 1000     # processing
    return tx_ms + prop_ms + queue_ms + proc_ms


# ─── Bốn thuật toán cân bằng tải ────
class RoundRobinAlgorithm:
    def __init__(self):
        self._idx = 0

    def reset(self):
        self._idx = 0

    def select(self, nodes: List[EdgeNode], task: Task) -> EdgeNode:
        node = nodes[self._idx % len(nodes)]
        self._idx += 1
        return node


class RandomAlgorithm:
    def select(self, nodes: List[EdgeNode], task: Task) -> EdgeNode:
        return random.choice(nodes)


class LeastLoadedAlgorithm:
    def select(self, nodes: List[EdgeNode], task: Task) -> EdgeNode:
        return min(nodes, key=lambda n: n.current_load_mips / n.cpu_capacity)


class WeightedLBAlgorithm:
    def select(self, nodes: List[EdgeNode], task: Task) -> EdgeNode:
        scores = [n.weight / (n.current_load_mips / n.cpu_capacity + 0.05)
                  for n in nodes]
        total = sum(scores)
        probs = [s / total for s in scores]
        return random.choices(nodes, weights=probs, k=1)[0]


# ───  Engine mô phỏng & thu thập chỉ số QoS ───
@dataclass
class SimResult:
    algorithm:           str
    scenario:            int
    num_users:           int
    avg_latency_ms:      float
    throughput_mbps:     float
    avg_cpu_utilization: float
    packet_loss_rate:    float
    tasks_total:         int
    tasks_completed:     int


def run_simulation(algo_name: str, algo, nodes: List[EdgeNode],
                   tasks_per_step: List[List[Task]],
                   scenario: int, num_users: int) -> SimResult:
    reset_nodes(nodes)
    total_tasks = sum(len(s) for s in tasks_per_step)
    total_latency = 0.0
    total_data_mb = 0.0
    dropped = 0

    for step in range(NUM_STEPS):
        # Deliver arriving tasks
        for task in tasks_per_step[step]:
            node = algo.select(nodes, task)
            if node.queue_size >= QUEUE_CAPACITY:
                dropped += 1
                node.dropped += 1
                continue
            latency = compute_latency_ms(node, task)
            node.queue.append(task.cpu_required)
            node.latencies.append(latency)
            node.total_data_mb += task.data_size_kb / 1024
            total_latency += latency
            total_data_mb += task.data_size_kb / 1024

        # Each node processes tasks for this time step
        for node in nodes:
            node.step_process(TIME_STEP)

    completed = total_tasks - dropped
    avg_latency = total_latency / completed if completed > 0 else 0
    throughput  = total_data_mb / SIMULATION_TIME * 8   # Mbps
    avg_cpu     = np.mean([n.cpu_utilization for n in nodes])
    loss_rate   = dropped / total_tasks if total_tasks > 0 else 0

    return SimResult(
        algorithm=algo_name,
        scenario=scenario,
        num_users=num_users,
        avg_latency_ms=round(avg_latency, 2),
        throughput_mbps=round(throughput, 4),
        avg_cpu_utilization=round(avg_cpu, 4),
        packet_loss_rate=round(loss_rate, 4),
        tasks_total=total_tasks,
        tasks_completed=completed,
    )


# ─── Chạy toàn bộ thực nghiệm, lưu results.csv ────
def main():
    out_dir      = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(out_dir, "results.csv")

    scenarios = {1: 10, 2: 30, 3: 60, 4: 100}

    rr = RoundRobinAlgorithm()
    algorithms = {
        "Round Robin":  rr,
        "Random":       RandomAlgorithm(),
        "Least Loaded": LeastLoadedAlgorithm(),
        "Weighted LB":  WeightedLBAlgorithm(),
    }

    nodes      = create_edge_nodes()
    all_results: List[SimResult] = []

    print(f"{'-'*75}")
    print(f"  Edge Computing Simulation  |  5 Heterogeneous Nodes  |  {SIMULATION_TIME}s")
    print(f"  Node capacities: {[n.cpu_capacity for n in nodes]} MIPS")
    print(f"{'-'*75}")

    for sc_id, num_users in scenarios.items():
        np.random.seed(RANDOM_SEED + sc_id)
        random.seed(RANDOM_SEED + sc_id)
        tasks_by_step = generate_tasks_by_step(num_users)
        total = sum(len(s) for s in tasks_by_step)
        print(f"\nScenario {sc_id}: {num_users} users  |  {total} tasks  |  Queue cap: {QUEUE_CAPACITY}/node")

        for algo_name, algo in algorithms.items():
            if isinstance(algo, RoundRobinAlgorithm):
                algo.reset()
            np.random.seed(RANDOM_SEED)
            random.seed(RANDOM_SEED)

            r = run_simulation(algo_name, algo, nodes, tasks_by_step, sc_id, num_users)
            all_results.append(r)

            print(
                f"  [{algo_name:<18}]  "
                f"Latency: {r.avg_latency_ms:7.1f} ms  "
                f"Thput: {r.throughput_mbps:6.3f} Mbps  "
                f"CPU: {r.avg_cpu_utilization*100:5.1f}%  "
                f"Loss: {r.packet_loss_rate*100:5.1f}%  "
                f"({r.tasks_completed}/{r.tasks_total})"
            )

    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(SimResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for r in all_results:
            writer.writerow(r.__dict__)

    print(f"\n{'-'*75}")
    print(f"  Results saved -> {results_path}")
    print(f"{'-'*75}\n")
    return all_results


if __name__ == "__main__":
    main()
