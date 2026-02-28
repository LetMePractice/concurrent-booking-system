"""
Admission control strategy interface.
Allows swapping between different concurrency control approaches.
"""

from abc import ABC, abstractmethod


class AdmissionStrategy(ABC):
    """
    Interface for admission control strategies.
    
    Implementations:
    - OptimisticAdmission: No pre-check, rely on DB optimistic locking
    - RedisAdmission: Fast fail-fast check in Redis before DB
    - QueueAdmission: Serialize all requests through queue
    """
    
    @abstractmethod
    async def admit(self, event_id: int, seats: int = 1) -> bool:
        """
        Check if booking request should be admitted.
        
        Args:
            event_id: Event to book
            seats: Number of seats requested
            
        Returns:
            True if admitted (proceed to DB)
            False if rejected (fail fast)
        """
        pass
    
    @abstractmethod
    async def release(self, event_id: int, seats: int = 1):
        """
        Release reserved seats (on booking failure).
        
        Args:
            event_id: Event ID
            seats: Number of seats to release
        """
        pass
    
    @abstractmethod
    async def sync(self, event_id: int, available_seats: int):
        """
        Sync admission state with database (reconciliation).
        
        Args:
            event_id: Event ID
            available_seats: Current available seats from DB
        """
        pass
