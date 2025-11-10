"""
Orchestrator Router - Application Layer Orchestrator

This module provides access to the application layer orchestrator for
coordinating multi-agent work across projects.

The application orchestrator (ProjectOrchestrator) coordinates multiple domain
aggregates and implements workflow logic, which belongs in the application layer
according to DDD principles.
"""

import logging
from typing import Any

from ...domain.entities.project import Project

logger = logging.getLogger(__name__)


def get_orchestrator(strategy=None):
    """
    Factory function to get the application layer orchestrator.

    Args:
        strategy: Optional orchestration strategy

    Returns:
        ProjectOrchestrator instance (application layer)

    Examples:
        # Get orchestrator
        orchestrator = get_orchestrator()
        result = orchestrator.orchestrate_project(project)

        # With custom strategy
        from .project_orchestrator import CapabilityBasedStrategy
        orchestrator = get_orchestrator(strategy=CapabilityBasedStrategy())
    """
    from .project_orchestrator import ProjectOrchestrator
    logger.debug("Using application layer orchestrator")
    return ProjectOrchestrator(strategy=strategy)


class OrchestratorRouter:
    """
    Router class that delegates to the application layer orchestrator.

    This provides a class-based API for the orchestrator. Use this when you
    need an instance that can be passed around.
    """

    def __init__(self, strategy=None):
        """Initialize router with application layer orchestrator"""
        self._orchestrator = get_orchestrator(strategy)
        logger.debug("OrchestratorRouter initialized with application layer implementation")

    def orchestrate_project(self, project: Project):
        """
        Orchestrate work distribution for a project.
        """
        return self._orchestrator.orchestrate_project(project)

    def coordinate_cross_tree_dependencies(self, project: Project):
        """
        Coordinate and validate cross-tree dependencies.
        """
        return self._orchestrator.coordinate_cross_tree_dependencies(project)

    def balance_workload(self, project: Project):
        """
        Balance workload across agents.
        """
        return self._orchestrator.balance_workload(project)


# Convenience function for quick orchestration
def orchestrate_project(project: Project, strategy=None) -> dict[str, Any]:
    """
    Convenience function to orchestrate a project.

    Args:
        project: Project to orchestrate
        strategy: Optional orchestration strategy

    Returns:
        Orchestration results dictionary

    Example:
        from application.orchestration import orchestrate_project
        result = orchestrate_project(my_project)
    """
    orchestrator = get_orchestrator(strategy)
    return orchestrator.orchestrate_project(project)
