"""File Resource MCP Controller - Modular Implementation

This controller handles MCP tool registration for file resource exposure,
following DDD principles by delegating business logic to application services.
It exposes all files in the project directory as MCP resources.
"""

import logging
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from fastmcp.utilities.logging import get_logger
from .factories.file_resource_controller_factory import FileResourceControllerFactory

logger = get_logger(__name__)


class FileResourceMCPController:
    """
    MCP Controller for file resource management.
    
    Handles only MCP protocol concerns and exposes all files in the project
    as MCP resources following proper DDD layer separation.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize controller with project root path.
        
        Args:
            project_root: Root path of the project to expose files from
        """
        self.project_root = Path(project_root).resolve()
        self._factory = FileResourceControllerFactory(self.project_root)
        logger.info(f"FileResourceMCPController initialized with project root: {self.project_root}")
    
    def register_resources(self, mcp: "FastMCP"):
        """Register all file resources with the FastMCP server"""
        result = self._factory.register_all_resources(mcp)
        if not result.get("success", False):
            logger.error(f"Failed to register resources: {result.get('error', 'Unknown error')}")
            raise RuntimeError(result.get("error", "Failed to register resources"))
        
        logger.info("File resources registered successfully")
    
    # Legacy method compatibility - delegates to factory
    def _register_directory_resource(self, mcp: "FastMCP", directory: Path, name: str):
        """Register a directory listing resource (legacy method)"""
        handler = self._factory.get_registration_handler()
        return handler._register_directory_resource(mcp, directory, name)
    
    def _register_file_resources(self, mcp: "FastMCP"):
        """Register individual file resources for important files (legacy method)"""
        handler = self._factory.get_registration_handler()
        return handler._register_individual_files(mcp)
    
    def _register_single_file_from_info(self, mcp: "FastMCP", file_info):
        """Register a single file as a resource from FileResourceInfo (legacy method)"""
        handler = self._factory.get_registration_handler()
        return handler._register_single_file_from_info(mcp, file_info)
    
    def _register_single_file(self, mcp: "FastMCP", file_path: Path):
        """Register a single file as a resource (legacy method)"""
        return self._factory.register_single_file_legacy(mcp, file_path)
    
    def _register_file_template(self, mcp: "FastMCP"):
        """Register a template for dynamic file access within resources directory (legacy method)"""
        handler = self._factory.get_registration_handler()
        return handler._register_dynamic_template(mcp)
    
    def _should_expose_file(self, file_path: Path) -> bool:
        """Determine if a file should be exposed as a resource (legacy method)"""
        return self._factory.should_expose_file(file_path)
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension (legacy method)"""
        return self._factory.get_mime_type(file_path)
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary (legacy method)"""
        return self._factory.is_binary_file(file_path)