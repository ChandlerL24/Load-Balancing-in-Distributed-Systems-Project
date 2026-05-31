"""
Tests for the load balancing simulation.
"""

import pytest
import numpy as np

from load_balancing.server import Server, Request
from load_balancing.load_balancer import (
    RoundRobinBalancer,
    RandomBalancer,
    LeastConnectionsBalancer,
)
from load_balancing.simulation import Simulation
from load_balancing.metrics import MetricsCollector


class TestRequest:
    
    def test_create_request(self):
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        assert req.id == 1
        assert req.arrival_time == 0.0
        assert req.service_time == 1.0
        assert req.start_time is None
        assert req.completion_time is None
    
    def test_response_time_calc(self):
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        req.start_time = 0.5
        req.completion_time = 1.5
        
        assert req.response_time == 1.5
        assert req.waiting_time == 0.5
    
    def test_incomplete_request_times(self):
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        assert req.response_time is None
        assert req.waiting_time is None


class TestServer:
    
    def test_create_server(self):
        server = Server(id=0, service_rate=2.0)
        assert server.id == 0
        assert server.service_rate == 2.0
        assert server.queue_length == 0
        assert server.active_connections == 0
    
    def test_enqueue(self):
        server = Server(id=0)
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        
        assert server.enqueue(req)
        assert server.queue_length == 1
        assert req.server_id == 0
    
    def test_queue_full(self):
        server = Server(id=0, queue_capacity=2)
        
        r1 = Request(id=1, arrival_time=0.0, service_time=1.0)
        r2 = Request(id=2, arrival_time=0.1, service_time=1.0)
        r3 = Request(id=3, arrival_time=0.2, service_time=1.0)
        
        assert server.enqueue(r1)
        assert server.enqueue(r2)
        assert not server.enqueue(r3)
        assert server.queue_length == 2
    
    def test_process_request(self):
        server = Server(id=0)
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        
        server.enqueue(req)
        started = server.process_next(current_time=0.0)
        
        assert started is req
        assert req.start_time == 0.0
        assert server.busy_until == 1.0
        assert server.is_busy(0.5)
        assert not server.is_busy(1.5)
    
    def test_complete_request(self):
        server = Server(id=0)
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        
        server.enqueue(req)
        server.process_next(current_time=0.0)
        
        assert server.complete_current(0.5) is None  # not done yet
        
        completed = server.complete_current(1.0)
        assert completed is req
        assert req.completion_time == 1.0
        assert server.requests_processed == 1
    
    def test_utilization_calc(self):
        server = Server(id=0)
        req = Request(id=1, arrival_time=0.0, service_time=5.0)
        
        server.enqueue(req)
        server.process_next(current_time=0.0)
        server.complete_current(5.0)
        
        assert server.utilization(10.0) == 0.5
    
    def test_reset(self):
        server = Server(id=0)
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        
        server.enqueue(req)
        server.process_next(current_time=0.0)
        server.complete_current(1.0)
        
        server.reset()
        
        assert server.queue_length == 0
        assert server.current_request is None
        assert server.requests_processed == 0
        assert server.total_busy_time == 0.0


class TestRoundRobinBalancer:
    
    def test_distributes_evenly(self):
        servers = [Server(id=i) for i in range(3)]
        balancer = RoundRobinBalancer(servers)
        
        reqs = [Request(id=i, arrival_time=i*0.1, service_time=1.0) for i in range(6)]
        
        for req in reqs:
            balancer.route_request(req)
        
        for server in servers:
            assert server.queue_length == 2
    
    def test_skips_full_queues(self):
        servers = [Server(id=i, queue_capacity=1) for i in range(3)]
        balancer = RoundRobinBalancer(servers)
        
        r1 = Request(id=1, arrival_time=0.0, service_time=1.0)
        balancer.route_request(r1)
        
        r2 = Request(id=2, arrival_time=0.1, service_time=1.0)
        balancer.route_request(r2)
        
        r3 = Request(id=3, arrival_time=0.2, service_time=1.0)
        balancer.route_request(r3)
        
        assert servers[0].queue_length == 1
        assert servers[1].queue_length == 1
        assert servers[2].queue_length == 1


class TestRandomBalancer:
    
    def test_distributes_requests(self):
        servers = [Server(id=i) for i in range(3)]
        balancer = RandomBalancer(servers, seed=42)
        
        reqs = [Request(id=i, arrival_time=i*0.1, service_time=1.0) for i in range(100)]
        
        for req in reqs:
            balancer.route_request(req)
        
        total = sum(s.queue_length for s in servers)
        assert total == 100
        
        # should be roughly even
        for server in servers:
            assert server.queue_length > 20


class TestLeastConnectionsBalancer:
    
    def test_picks_least_loaded(self):
        servers = [Server(id=i) for i in range(3)]
        balancer = LeastConnectionsBalancer(servers)
        
        # load up servers 0 and 1
        servers[0].enqueue(Request(id=100, arrival_time=0.0, service_time=1.0))
        servers[0].enqueue(Request(id=101, arrival_time=0.0, service_time=1.0))
        servers[1].enqueue(Request(id=102, arrival_time=0.0, service_time=1.0))
        
        # new request should go to server 2
        req = Request(id=1, arrival_time=0.1, service_time=1.0)
        balancer.route_request(req)
        
        assert servers[2].queue_length == 1
    
    def test_balances_load(self):
        servers = [Server(id=i) for i in range(3)]
        balancer = LeastConnectionsBalancer(servers)
        
        reqs = [Request(id=i, arrival_time=i*0.1, service_time=1.0) for i in range(9)]
        
        for req in reqs:
            balancer.route_request(req)
        
        for server in servers:
            assert server.queue_length == 3


class TestSimulation:
    
    def test_create_simulation(self):
        sim = Simulation(num_servers=3, arrival_rate=5.0, service_rate=2.0, duration=100.0)
        
        assert len(sim.servers) == 3
        assert sim.arrival_rate == 5.0
        assert sim.service_rate == 2.0
        assert sim.duration == 100.0
    
    def test_needs_load_balancer(self):
        sim = Simulation(num_servers=3, duration=10.0)
        
        with pytest.raises(RuntimeError):
            sim.run()
    
    def test_runs_and_produces_metrics(self):
        sim = Simulation(
            num_servers=3,
            arrival_rate=5.0,
            service_rate=2.0,
            duration=100.0,
            seed=42,
        )
        sim.set_load_balancer(RoundRobinBalancer(sim.servers))
        
        metrics = sim.run()
        
        assert metrics.total_requests > 0
        assert metrics.completed_requests > 0
        assert metrics.throughput > 0
        assert metrics.avg_response_time > 0
    
    def test_reproducible_with_seed(self):
        def run_sim():
            sim = Simulation(
                num_servers=3,
                arrival_rate=5.0,
                service_rate=2.0,
                duration=100.0,
                seed=42,
            )
            sim.set_load_balancer(RoundRobinBalancer(sim.servers))
            return sim.run()
        
        m1 = run_sim()
        m2 = run_sim()
        
        assert m1.total_requests == m2.total_requests
        assert m1.completed_requests == m2.completed_requests
        assert np.isclose(m1.avg_response_time, m2.avg_response_time)
    
    def test_reset_and_rerun(self):
        sim = Simulation(
            num_servers=3,
            arrival_rate=5.0,
            service_rate=2.0,
            duration=100.0,
            seed=42,
        )
        sim.set_load_balancer(RoundRobinBalancer(sim.servers))
        
        m1 = sim.run()
        sim.reset()
        m2 = sim.run()
        
        assert m1.total_requests == m2.total_requests


class TestMetricsCollector:
    
    def test_basic_collection(self):
        servers = [Server(id=i) for i in range(2)]
        collector = MetricsCollector(servers)
        
        collector.record_generation()
        collector.record_generation()
        collector.record_rejection()
        
        req = Request(id=1, arrival_time=0.0, service_time=1.0)
        req.start_time = 0.0
        req.completion_time = 1.0
        collector.record_completion(req)
        
        metrics = collector.compute_metrics(duration=10.0)
        
        assert metrics.total_requests == 2
        assert metrics.completed_requests == 1
        assert metrics.rejected_requests == 1
    
    def test_snapshots(self):
        servers = [Server(id=i) for i in range(2)]
        collector = MetricsCollector(servers)
        
        servers[0].enqueue(Request(id=1, arrival_time=0.0, service_time=1.0))
        servers[0].enqueue(Request(id=2, arrival_time=0.0, service_time=1.0))
        servers[1].enqueue(Request(id=3, arrival_time=0.0, service_time=1.0))
        
        collector.take_snapshot(1.0)
        
        metrics = collector.compute_metrics(duration=10.0)
        
        assert metrics.avg_queue_length == 1.5  # (2 + 1) / 2
  