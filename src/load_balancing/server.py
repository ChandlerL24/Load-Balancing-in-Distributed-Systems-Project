"""
Server and Request classes.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Request:
    """A single request with timing info."""
    id: int
    arrival_time: float
    service_time: float
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    server_id: Optional[int] = None
    
    @property
    def response_time(self) -> Optional[float]:
        if self.completion_time is not None:
            return self.completion_time - self.arrival_time
        return None
    
    @property
    def waiting_time(self) -> Optional[float]:
        if self.start_time is not None:
            return self.start_time - self.arrival_time
        return None


@dataclass
class Server:
    """
    A server that processes requests from a queue.
    Handles one request at a time.
    """
    id: int
    service_rate: float = 1.0
    queue_capacity: int = -1  # -1 = no limit
    queue: list = field(default_factory=list)
    current_request: Optional[Request] = None
    busy_until: float = 0.0
    total_busy_time: float = 0.0
    requests_processed: int = 0
    _last_idle_time: float = 0.0
    
    @property
    def queue_length(self) -> int:
        return len(self.queue)
    
    @property
    def active_connections(self) -> int:
        n = len(self.queue)
        if self.current_request is not None:
            n += 1
        return n
    
    def is_busy(self, current_time: float) -> bool:
        return self.busy_until > current_time
    
    def can_accept(self) -> bool:
        if self.queue_capacity == -1:
            return True
        return len(self.queue) < self.queue_capacity
    
    def enqueue(self, request: Request) -> bool:
        if not self.can_accept():
            return False
        request.server_id = self.id
        self.queue.append(request)
        return True
    
    def process_next(self, current_time: float) -> Optional[Request]:
        if self.is_busy(current_time) or not self.queue:
            return None
        
        req = self.queue.pop(0)
        req.start_time = current_time
        self.current_request = req
        self.busy_until = current_time + req.service_time
        return req
    
    def complete_current(self, current_time: float) -> Optional[Request]:
        if self.current_request is None:
            return None
        
        if current_time >= self.busy_until:
            req = self.current_request
            req.completion_time = self.busy_until
            self.total_busy_time += req.service_time
            self.requests_processed += 1
            self.current_request = None
            self._last_idle_time = current_time
            return req
        
        return None
    
    def utilization(self, total_time: float) -> float:
        if total_time <= 0:
            return 0.0
        return min(1.0, self.total_busy_time / total_time)
    
    def reset(self):
        self.queue = []
        self.current_request = None
        self.busy_until = 0.0
        self.total_busy_time = 0.0
        self.requests_processed = 0
        self._last_idle_time = 0.0
