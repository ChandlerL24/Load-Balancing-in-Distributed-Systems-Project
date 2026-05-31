"""
Load balancing strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from load_balancing.server import Server, Request


class LoadBalancer(ABC):
    """Base class for load balancers."""
    
    def __init__(self, servers: List[Server], name: str = "LoadBalancer"):
        self.servers = servers
        self.name = name
        self._requests_routed = 0
        self._requests_rejected = 0
    
    @abstractmethod
    def select_server(self, request: Request) -> Optional[Server]:
        pass
    
    def route_request(self, request: Request) -> bool:
        server = self.select_server(request)
        if server is None:
            self._requests_rejected += 1
            return False
        
        if server.enqueue(request):
            self._requests_routed += 1
            return True
        else:
            self._requests_rejected += 1
            return False
    
    @property
    def requests_routed(self) -> int:
        return self._requests_routed
    
    @property
    def requests_rejected(self) -> int:
        return self._requests_rejected
    
    def reset(self):
        self._requests_routed = 0
        self._requests_rejected = 0


class RoundRobinBalancer(LoadBalancer):
    """Cycles through servers in order."""
    
    def __init__(self, servers: List[Server]):
        super().__init__(servers, name="Round-Robin")
        self._idx = 0
    
    def select_server(self, request: Request) -> Optional[Server]:
        n = len(self.servers)
        for _ in range(n):
            server = self.servers[self._idx]
            self._idx = (self._idx + 1) % n
            if server.can_accept():
                return server
        return None
    
    def reset(self):
        super().reset()
        self._idx = 0


class RandomBalancer(LoadBalancer):
    """Picks a random available server."""
    
    def __init__(self, servers: List[Server], seed: Optional[int] = None):
        super().__init__(servers, name="Random")
        self._rng = np.random.default_rng(seed)
    
    def select_server(self, request: Request) -> Optional[Server]:
        available = [s for s in self.servers if s.can_accept()]
        if not available:
            return None
        return self._rng.choice(available)


class LeastConnectionsBalancer(LoadBalancer):
    """Picks the server with fewest active connections."""
    
    def __init__(self, servers: List[Server]):
        super().__init__(servers, name="Least-Connections")
    
    def select_server(self, request: Request) -> Optional[Server]:
        available = [s for s in self.servers if s.can_accept()]
        if not available:
            return None
        return min(available, key=lambda s: s.active_connections)


class WeightedRoundRobinBalancer(LoadBalancer):
    """Round-robin but weighted by server capacity."""
    
    def __init__(self, servers: List[Server], weights: Optional[List[float]] = None):
        super().__init__(servers, name="Weighted-Round-Robin")
        
        if weights is None:
            self._weights = [s.service_rate for s in servers]
        else:
            if len(weights) != len(servers):
                raise ValueError("weights length must match servers")
            self._weights = weights
        
        min_w = min(self._weights)
        self._eff_weights = [int(w / min_w) for w in self._weights]
        self._idx = 0
        self._count = 0
    
    def select_server(self, request: Request) -> Optional[Server]:
        n = len(self.servers)
        attempts = sum(self._eff_weights)
        
        for _ in range(attempts):
            server = self.servers[self._idx]
            
            if self._count < self._eff_weights[self._idx]:
                self._count += 1
                if server.can_accept():
                    return server
            else:
                self._count = 0
                self._idx = (self._idx + 1) % n
        
        return None
    
    def reset(self):
        super().reset()
        self._idx = 0
        self._count = 0
