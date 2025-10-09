"""
Orchestrator Router - Strangler Fig Pattern Implementation

This router implements the Strangler Fig pattern for migrating from domain-layer
orchestrator to application-layer orchestrator with zero downtime.

How it works:
1. Checks FEATURE_APPLICATION_ORCHESTRATOR feature flag
2. Routes to appropriate implementation based on flag
3. Maintains identical interface for all callers
4. Enables gradual migration and A/B testing

Migration phases:
- Phase 3 (current): Both implementations available, flag controls routing
- Phase 4-7: Gradual migration of callers, testing with flag enabled
- Phase 8: Remove domain orchestrator, update default flag value to True
"""

from typing import Dict, List, Any, Optional
import logging

from fastmcp.settings import settings
from ...domain.entities.project import Project


logger = logging.getLogger(__name__)


def get_orchestrator(strategy=None):
    """
    Factory function to get the appropriate orchestrator implementation.

    Uses feature flag FEATURE_APPLICATION_ORCHESTRATOR to determine which
    orchestrator to instantiate.

    Args:
        strategy: Optional orchestration strategy (for both implementations)

    Returns:
        Orchestrator instance (domain or application layer)

    Examples:
        # Get orchestrator (automatically selects based on feature flag)
        orchestrator = get_orchestrator()
        result = orchestrator.orchestrate_project(project)

        # With custom strategy
        from .project_orchestrator import CapabilityBasedStrategy
        orchestrator = get_orchestrator(strategy=CapabilityBasedStrategy())
    """
    feature_flag = settings.feature_application_orchestrator

    if feature_flag:
        # NEW: Application layer orchestrator
        from .project_orchestrator import ProjectOrchestrator
        logger.info("[Strangler Fig] Using application layer orchestrator (NEW)")
        return ProjectOrchestrator(strategy=strategy)
    else:
        # OLD: Domain layer orchestrator (backward compatibility)
        from ...domain.services.orchestrator import Orchestrator
        logger.info("[Strangler Fig] Using domain layer orchestrator (LEGACY)")
        return Orchestrator(strategy=strategy)


class OrchestratorRouter:
    """
    Router class that delegates to appropriate orchestrator implementation.

    This provides a class-based API that automatically routes to the correct
    implementation based on feature flag. Use this when you need an instance
    that can be passed around.

    The router maintains identical interface to both orchestrator implementations,
    so callers don't need to change their code during migration.
    """

    def __init__(self, strategy=None):
        """Initialize router with appropriate orchestrator"""
        self._orchestrator = get_orchestrator(strategy)
        self._layer = "application" if settings.feature_application_orchestrator else "domain"
        logger.debug(f"OrchestratorRouter initialized with {self._layer} layer implementation")

    def orchestrate_project(self, project: Project) -> Dict[str, Any]:
        """
        Orchestrate work distribution for a project.

        Routes to appropriate implementation based on feature flag.
        """
        return self._orchestrator.orchestrate_project(project)

    def coordinate_cross_tree_dependencies(self, project: Project) -> List[Dict]:
        """
        Coordinate and validate cross-tree dependencies.

        Routes to appropriate implementation based on feature flag.
        """
        return self._orchestrator.coordinate_cross_tree_dependencies(project)

    def balance_workload(self, project: Project) -> Dict[str, Any]:
        """
        Balance workload across agents.

        Routes to appropriate implementation based on feature flag.
        """
        return self._orchestrator.balance_workload(project)

    @property
    def current_layer(self) -> str:
        """Return which layer is currently handling orchestration"""
        return self._layer

    @property
    def is_using_application_layer(self) -> bool:
        """Check if using new application layer orchestrator"""
        return self._layer == "application"

    @property
    def is_using_domain_layer(self) -> bool:
        """Check if using old domain layer orchestrator"""
        return self._layer == "domain"


# Convenience function for quick orchestration
def orchestrate_project(project: Project, strategy=None) -> Dict[str, Any]:
    """
    Convenience function to orchestrate a project with automatic routing.

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
