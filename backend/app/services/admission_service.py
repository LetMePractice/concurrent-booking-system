"""
Admission control service for high-contention scenarios.
Implements AdmissionStrategy interface using Redis.
"""

from app.services.interfaces.admission import AdmissionStrategy
from app.infrastructure.redis_client import get_redis
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
            # On Redis failure, admit (fail open)
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
