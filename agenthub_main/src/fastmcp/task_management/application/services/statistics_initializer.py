"""Statistics Initializer - Wires up event handlers on application startup"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StatisticsInitializer:
    """
    Application service that initializes branch statistics tracking on startup.
    This ensures event handlers are registered and the system is ready to track
    branch task counts automatically.
    """

    _initialized = False

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize the statistics tracking system.
        This should be called once during application startup.
        """
        if cls._initialized:
            logger.debug("Statistics system already initialized")
            return

        try:
            # Import here to avoid circular dependencies
            from ..services.repository_provider_service import RepositoryProviderService
            from ..services.branch_statistics_integration_service import (
                get_branch_statistics_integration_service
            )

            # Get repositories
            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository()
            branch_repo = provider.get_git_branch_repository()

            # Initialize the integration service (this registers event handlers)
            integration_service = get_branch_statistics_integration_service(
                task_repo,
                branch_repo
            )

            logger.info("Statistics tracking system initialized successfully")
            cls._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize statistics tracking system: {e}")
            raise

    @classmethod
    def recalculate_all_branches(cls, project_id: Optional[str] = None) -> dict:
        """
        Recalculate statistics for all branches.
        Useful for fixing inconsistencies or after bulk operations.

        Args:
            project_id: Optional project ID to limit recalculation

        Returns:
            Dictionary of branch statistics
        """
        try:
            from ..services.repository_provider_service import RepositoryProviderService
            from ..services.branch_statistics_integration_service import (
                get_branch_statistics_integration_service
            )

            # Get repositories
            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository()
            branch_repo = provider.get_git_branch_repository()

            # Get the integration service
            integration_service = get_branch_statistics_integration_service(
                task_repo,
                branch_repo
            )

            # Recalculate all branches
            results = integration_service.recalculate_all_branches(project_id)
            logger.info(f"Recalculated statistics for {len(results)} branches")
            return results

        except Exception as e:
            logger.error(f"Failed to recalculate branch statistics: {e}")
            raise

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if the statistics system is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return cls._initialized