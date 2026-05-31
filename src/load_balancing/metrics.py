"""
Metrics collection and reporting.
"""

from dataclasses import dataclass, field
from typing import List, Dict
import numpy as np

from load_balancing.server import Server, Request


@dataclass
class SimulationMetrics:
    """Holds all the stats from a simulation run."""
    total_requests: int = 0
    completed_requests: int = 0
    rejected_requests: int = 0
    avg_response_time: float = 0.0
    avg_waiting_time: float = 0.0
    avg_queue_length: float = 0.0
    throughput: float = 0.0
    server_utilizations: List[float] = field(default_factory=list)
    
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    
    response_times: List[float] = field(default_factory=list)
    queue_lengths_over_time: List[List[int]] = field(default_factory=list)


class MetricsCollector:
    """Tracks metrics during the simulation."""
    
    def __init__(self, servers: List[Server]):
        self.servers = servers
        self.completed_requests: List[Request] = []
        self.rejected_count = 0
        self.total_generated = 0
        self._queue_snapshots: List[Dict[int, int]] = []
        self._snapshot_times: List[float] = []
    
    def record_completion(self, request: Request):
        self.completed_requests.append(request)
    
    def record_rejection(self):
        self.rejected_count += 1
    
    def record_generation(self):
        self.total_generated += 1
    
    def take_snapshot(self, current_time: float):
        snapshot = {s.id: s.queue_length for s in self.servers}
        self._queue_snapshots.append(snapshot)
        self._snapshot_times.append(current_time)
    
    def compute_metrics(self, duration: float) -> SimulationMetrics:
        m = SimulationMetrics()
        
        m.total_requests = self.total_generated
        m.completed_requests = len(self.completed_requests)
        m.rejected_requests = self.rejected_count
        
        if self.completed_requests:
            resp_times = [r.response_time for r in self.completed_requests 
                         if r.response_time is not None]
            wait_times = [r.waiting_time for r in self.completed_requests 
                         if r.waiting_time is not None]
            
            if resp_times:
                m.response_times = resp_times
                m.avg_response_time = np.mean(resp_times)
                m.p50_response_time = np.percentile(resp_times, 50)
                m.p95_response_time = np.percentile(resp_times, 95)
                m.p99_response_time = np.percentile(resp_times, 99)
            
            if wait_times:
                m.avg_waiting_time = np.mean(wait_times)
        
        if duration > 0:
            m.throughput = m.completed_requests / duration
        
        m.server_utilizations = [s.utilization(duration) for s in self.servers]
        
        if self._queue_snapshots:
            all_lens = []
            for snap in self._queue_snapshots:
                all_lens.extend(snap.values())
            m.avg_queue_length = np.mean(all_lens) if all_lens else 0.0
            
            m.queue_lengths_over_time = [
                [snap.get(s.id, 0) for snap in self._queue_snapshots]
                for s in self.servers
            ]
        
        return m
    
    def reset(self):
        self.completed_requests = []
        self.rejected_count = 0
        self.total_generated = 0
        self._queue_snapshots = []
        self._snapshot_times = []


def print_metrics_summary(metrics: SimulationMetrics, strategy_name: str = ""):
    """Print a nice summary of the results."""
    print("=" * 50)
    if strategy_name:
        print(f"{strategy_name} Results")
        print("=" * 50)
    
    print(f"\nRequests:")
    print(f"  Generated: {metrics.total_requests}")
    print(f"  Completed: {metrics.completed_requests}")
    print(f"  Rejected:  {metrics.rejected_requests}")
    
    rej_rate = (metrics.rejected_requests / metrics.total_requests * 100 
                if metrics.total_requests > 0 else 0)
    print(f"  Rejection rate: {rej_rate:.2f}%")
    
    print(f"\nPerformance:")
    print(f"  Throughput: {metrics.throughput:.2f} req/unit")
    print(f"  Avg response: {metrics.avg_response_time:.4f}")
    print(f"  Avg wait: {metrics.avg_waiting_time:.4f}")
    print(f"  Avg queue len: {metrics.avg_queue_length:.2f}")
    
    print(f"\nResponse time percentiles:")
    print(f"  p50: {metrics.p50_response_time:.4f}")
    print(f"  p95: {metrics.p95_response_time:.4f}")
    print(f"  p99: {metrics.p99_response_time:.4f}")
    
    print(f"\nServer utilization:")
    for i, u in enumerate(metrics.server_utilizations):
        print(f"  Server {i}: {u:.2%}")
    
    avg_u = np.mean(metrics.server_utilizations) if metrics.server_utilizations else 0
    print(f"  Average: {avg_u:.2%}")
    print("=" * 50)
