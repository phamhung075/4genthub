"""File Resource MCP Controller Factory"""

import logging
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from fastmcp.utilities.logging import get_logger
from ..handlers.resource_registration_handler import ResourceRegistrationHandler
from ..utils.file_utils import FileUtils

logger = get_logger(__name__)


class FileResourceControllerFactory:
    """Factory for creating and managing File Resource MCP Controller components"""
    
    def __init__(self, project_root: Path):
        """Initialize factory with project root path"""
        self.project_root = Path(project_root).resolve()
        self._registration_handler = None
        self._file_utils = FileUtils()
        logger.info(f"FileResourceControllerFactory initialized with project root: {self.project_root}")
    
    def get_registration_handler(self) -> ResourceRegistrationHandler:
        """Get or create resource registration handler"""
        if self._registration_handler is None:
            self._registration_handler = ResourceRegistrationHandler(self.project_root)
        return self._registration_handler
    
    def get_file_utils(self) -> FileUtils:
        """Get file utilities instance"""
        return self._file_utils
    
    def register_all_resources(self, mcp: "FastMCP") -> Dict[str, Any]:
        """Register all file resources with the FastMCP server"""
        try:
            handler = self.get_registration_handler()
            return handler.register_all_resources(mcp)
        except Exception as e:
            logger.error(f"Factory failed to register resources: {e}")
            return {
                "success": False,
                "error": f"Factory failed to register resources: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def should_expose_file(self, file_path: Path) -> bool:
        """Determine if a file should be exposed as a resource"""
        return self._file_utils.should_expose_file(file_path)
    
    def get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension"""
        return self._file_utils.get_mime_type(file_path)
    
    def is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary"""
        return self._file_utils.is_binary_file(file_path)
    
    def register_single_file_legacy(self, mcp: "FastMCP", file_path: Path) -> Dict[str, Any]:
        """Register a single file as a resource (legacy method)"""
        return self._file_utils.register_single_file_legacy(mcp, file_path, self.project_root)