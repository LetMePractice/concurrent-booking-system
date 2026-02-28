"""
Optimistic admission strategy - no pre-check.
Relies entirely on database optimistic locking.
"""

from app.services.interfaces.admission import AdmissionStrategy


class OptimisticAdmission(AdmissionStrategy):
    """
    No admission control - always admit.
    Relies on DB optimistic locking to handle conflicts.
    
    Use when:
    - <100 concurrent users per event
    - Normal load scenarios
    - Simplicity preferred over fail-fast
    """
    
    async def admit(self, event_id: int, seats: int = 1) -> bool:
        """Always admit - let DB handle conflicts."""
        return True
    
    async def release(self, event_id: int, seats: int = 1):
        """No-op - nothing to release."""
        pass
    
    async def sync(self, event_id: int, available_seats: int):
        """No-op - no state to sync."""
        pass
