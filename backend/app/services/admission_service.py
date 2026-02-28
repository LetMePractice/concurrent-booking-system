"""
Admission control service for high-contention scenarios.
Implements AdmissionStrategy interface using Redis.

Circuit Breaker Pattern:
  On Redis failure, the system "fails open" (admits all requests).
  This prevents Redis outages from blocking all bookings.
  Database remains authoritative - Redis is advisory only.
  
  Tradeoff: During Redis outage, system reverts to optimistic locking behavior.
  This is acceptable because:
  - Temporary degradation better than total outage
  - Database constraints still prevent overbooking
  - Redis failures should be rare and monitored
"""

from app.services.interfaces.admission import AdmissionStrategy
from app.infrastructure.redis_client import get_redis
from app.core.metrics import redis_connection_errors, redis_circuit_breaker_open
import os

# Load Lua script
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '../infrastructure/admission_lua.lua')
with open(SCRIPT_PATH, 'r') as f:
    ADMISSION_SCRIPT = f.read()


class RedisAdmission(AdmissionStrategy):
    """
    Redis-based admission control.
    
    Strategy: Fail fast at Redis gate before hitting database.
    Prevents retry storms and load amplification.
    
    Use when:
    - 1000+ concurrent users per event
    - Flash sales / viral events
    - Need to protect database from overload
    """
    
    def __init__(self):
        self.redis = get_redis()
        self.script = self.redis.register_script(ADMISSION_SCRIPT)
    
    async def admit(self, event_id: int, seats: int = 1) -> bool:
        """
        Check if request should be admitted.
        
        Returns:
            True if admitted (proceed to DB)
            False if rejected (fail fast)
        """
        seats_key = f"seats:{event_id}"
        reserved_key = f"reserved:{event_id}"
        
        try:
            result = self.script(keys=[seats_key, reserved_key], args=[seats])
            return bool(result)
        except Exception:
            # Circuit breaker: On Redis failure, fail open (admit all)
            redis_connection_errors.inc()
            redis_circuit_breaker_open.set(1)
            return True
    
    async def release(self, event_id: int, seats: int = 1):
        """Release reserved seats (on booking failure)."""
        reserved_key = f"reserved:{event_id}"
        try:
            self.redis.decrby(reserved_key, seats)
        except Exception:
            pass  # Best effort
    
    async def sync(self, event_id: int, available_seats: int):
        """Sync Redis counter with DB (reconciliation)."""
        seats_key = f"seats:{event_id}"
        try:
            self.redis.set(seats_key, available_seats)
        except Exception:
            pass  # Best effort
