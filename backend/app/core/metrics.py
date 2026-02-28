"""
Metrics instrumentation for observability.
Exposes Prometheus-compatible metrics at /metrics endpoint.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Booking metrics
booking_attempts = Counter(
    'booking_attempts_total',
    'Total booking attempts',
    ['status']  # success, conflict, error
)

booking_latency = Histogram(
    'booking_latency_seconds',
    'Booking request latency',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Admission control metrics
admission_requests = Counter(
    'admission_requests_total',
    'Total admission control requests',
    ['result']  # admitted, rejected
)

admission_latency = Histogram(
    'admission_check_latency_seconds',
    'Admission check latency',
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01]
)

# Database metrics
db_operations = Counter(
    'db_operations_total',
    'Total database operations',
    ['operation']  # read, write, retry
)

db_retries = Counter(
    'db_retry_attempts_total',
    'Database retry attempts due to version conflicts'
)

# Cache metrics
cache_operations = Counter(
    'cache_operations_total',
    'Cache operations',
    ['operation', 'result']  # get/set, hit/miss
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage'
)

# System metrics
active_connections = Gauge(
    'active_db_connections',
    'Number of active database connections'
)

connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

connection_pool_overflow = Gauge(
    'db_connection_pool_overflow',
    'Database connection pool overflow count'
)

redis_connection_errors = Counter(
    'redis_connection_errors_total',
    'Redis connection errors'
)

redis_circuit_breaker_open = Gauge(
    'redis_circuit_breaker_open',
    'Redis circuit breaker state (1=open, 0=closed)'
)

def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.
    
    Usage:
        @app.get("/metrics")
        def metrics():
            return metrics_endpoint()
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Convenience functions for instrumentation
def record_booking_attempt(status: str):
    """Record booking attempt. Status: success, conflict, error"""
    booking_attempts.labels(status=status).inc()

def record_admission(admitted: bool):
    """Record admission control decision."""
    result = "admitted" if admitted else "rejected"
    admission_requests.labels(result=result).inc()

def record_db_operation(operation: str):
    """Record database operation. Operation: read, write, retry"""
    db_operations.labels(operation=operation).inc()

def record_cache_operation(operation: str, hit: bool):
    """Record cache operation."""
    result = "hit" if hit else "miss"
    cache_operations.labels(operation=operation, result=result).inc()
