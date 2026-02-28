"""
Admission strategy factory.
Configures which admission control strategy to use.
"""

from app.services.interfaces.admission import AdmissionStrategy
from app.services.interfaces.optimistic_admission import OptimisticAdmission
from app.services.admission_service import RedisAdmission
from app.core.config import settings


def get_admission_strategy() -> AdmissionStrategy:
    """
    Get configured admission strategy.
    
    Strategy selection based on environment:
    - Development: OptimisticAdmission (simple)
    - Production: RedisAdmission (high-contention)
    
    Can be overridden via ADMISSION_STRATEGY env var.
    """
    strategy = getattr(settings, 'ADMISSION_STRATEGY', 'optimistic')
    
    if strategy == 'redis':
        return RedisAdmission()
    else:
        return OptimisticAdmission()


# Singleton instance
_strategy: AdmissionStrategy = None

def get_admission() -> AdmissionStrategy:
    """Get admission strategy singleton."""
    global _strategy
    if _strategy is None:
        _strategy = get_admission_strategy()
    return _strategy
