"""
Domain Service Protocols

This module contains Protocol definitions for domain services.
Protocols define the interface contracts that infrastructure implementations must fulfill,
following the Dependency Inversion Principle of DDD.
"""

from .cascade_data_provider import (
    CascadeDataProvider,
    TaskCascadeData,
    SubtaskCascadeData,
    BranchCascadeData,
    ProjectCascadeData,
    ContextCascadeData,
)

__all__ = [
    "CascadeDataProvider",
    "TaskCascadeData",
    "SubtaskCascadeData",
    "BranchCascadeData",
    "ProjectCascadeData",
    "ContextCascadeData",
]
