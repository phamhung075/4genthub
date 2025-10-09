"""
Application Layer Orchestration

This module contains application-level orchestration services that coordinate
multiple domain aggregates and manage complex workflows.

According to DDD principles:
- Domain Services: Operate on a SINGLE aggregate
- Application Services: Coordinate MULTIPLE aggregates and implement use cases

The orchestrators in this module are application services because they:
1. Coordinate multiple aggregates (Project, Agent, GitBranch, Task)
2. Implement workflow logic and use cases
3. Use facades to interact with domain layer
"""

from .project_orchestrator import ProjectOrchestrator
from .orchestrator_router import get_orchestrator

__all__ = [
    'ProjectOrchestrator',
    'get_orchestrator',
]
