"""
Service interfaces for dependency inversion.
Allows swapping implementations without changing business logic.
"""

from .admission import AdmissionStrategy
from .optimistic_admission import OptimisticAdmission

__all__ = ['AdmissionStrategy', 'OptimisticAdmission']
