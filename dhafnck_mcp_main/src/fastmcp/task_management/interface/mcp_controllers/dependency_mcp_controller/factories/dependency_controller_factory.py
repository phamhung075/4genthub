"""Dependency Controller Factory"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP
    from .....application.facades.task_application_facade import TaskApplicationFacade

from ..handlers import DependencyOperationHandler
from ..services import DescriptionService

logger = logging.getLogger(__name__)


class DependencyControllerFactory:
    """Factory for creating dependency controller components"""
    
    @staticmethod
    def create_controller(task_facade: "TaskApplicationFacade") -> "DependencyMCPController":
        """
        Create a fully configured DependencyMCPController.
        
        Args:
            task_facade: The task application facade
            
        Returns:
            Configured DependencyMCPController instance
        """
        from ..dependency_mcp_controller import DependencyMCPController
        return DependencyMCPController(task_facade)
    
    @staticmethod
    def create_handler(task_facade: "TaskApplicationFacade") -> DependencyOperationHandler:
        """
        Create dependency operation handler.
        
        Args:
            task_facade: The task application facade
            
        Returns:
            DependencyOperationHandler instance
        """
        return DependencyOperationHandler(task_facade)
    
    @staticmethod
    def create_description_service() -> DescriptionService:
        """
        Create description service.
        
        Returns:
            DescriptionService instance
        """
        return DescriptionService()