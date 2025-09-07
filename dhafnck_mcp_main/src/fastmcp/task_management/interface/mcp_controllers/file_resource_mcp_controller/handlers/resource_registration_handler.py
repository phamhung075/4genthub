"""Resource Registration Handler for File Resource MCP Controller"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from fastmcp.resources import FileResource, DirectoryResource
from fastmcp.utilities.logging import get_logger
from .....application.facades.file_resource_application_facade import FileResourceApplicationFacade

logger = get_logger(__name__)


class ResourceRegistrationHandler:
    """Handler for file resource registration operations"""
    
    def __init__(self, project_root: Path):
        """Initialize handler with project root path"""
        self.project_root = Path(project_root).resolve()
        self._file_facade = FileResourceApplicationFacade(self.project_root)
        logger.info(f"ResourceRegistrationHandler initialized with project root: {self.project_root}")
    
    def register_all_resources(self, mcp: "FastMCP") -> Dict[str, Any]:
        """Register all file resources with the FastMCP server"""
        try:
            logger.info("Registering file resources...")
            
            # Register directory listing resource for the resources directory only
            self._register_resources_directory(mcp)
            
            # Register individual file resources
            self._register_individual_files(mcp)
            
            # Register file template for dynamic file access
            self._register_dynamic_template(mcp)
            
            logger.info("File resources registered successfully")
            return {
                "success": True,
                "message": "All file resources registered successfully",
                "project_root": str(self.project_root)
            }
            
        except Exception as e:
            logger.error(f"Failed to register file resources: {e}")
            return {
                "success": False,
                "error": f"Failed to register file resources: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def _register_resources_directory(self, mcp: "FastMCP"):
        """Register directory listing resource for the resources directory"""
        resources_dir = self._file_facade._get_resources_directory()
        if resources_dir and resources_dir.exists():
            self._register_directory_resource(mcp, resources_dir, "resources")
            logger.info(f"Registered resources directory: {resources_dir}")
        else:
            logger.warning("Resources directory not found, skipping directory resource registration")
    
    def _register_directory_resource(self, mcp: "FastMCP", directory: Path, name: str):
        """Register a directory listing resource"""
        try:
            if directory.exists() and directory.is_dir():
                directory_resource = DirectoryResource(
                    uri=f"resources://directory/{name}",
                    path=directory,
                    name=f"{name} Directory Listing",
                    description=f"Lists all files in the {name} directory",
                    recursive=True,
                    mime_type="application/json",
                    tags={
                        "directory", "listing", "resource"
                    }
                )
                mcp.add_resource(directory_resource)
                logger.debug(f"Registered directory resource: {directory}")
        except Exception as e:
            logger.warning(f"Failed to register directory resource for {directory}: {e}")
            raise
    
    def _register_individual_files(self, mcp: "FastMCP"):
        """Register individual file resources for important files"""
        # Use the application facade to discover files
        discovered_files = self._file_facade.discover_files()
        
        for file_info in discovered_files:
            self._register_single_file_from_info(mcp, file_info)
    
    def _register_single_file_from_info(self, mcp: "FastMCP", file_info):
        """Register a single file as a resource from FileResourceInfo"""
        try:
            file_resource = FileResource(
                uri=file_info.uri,
                path=file_info.path,
                name=file_info.name,
                description=file_info.description,
                mime_type=file_info.mime_type,
                tags=file_info.tags
            )
            
            mcp.add_resource(file_resource)
            logger.debug(f"Registered file resource: {file_info.relative_path}")
            
        except Exception as e:
            logger.warning(f"Failed to register file resource for {file_info.path}: {e}")
            raise
    
    def _register_dynamic_template(self, mcp: "FastMCP"):
        """Register a template for dynamic file access within resources directory"""
        @mcp.resource("resources://dynamic/{filepath*}")
        async def get_resource_content(filepath: str) -> str:
            """
            Dynamically access any file in the resources directory by path.
            
            Args:
                filepath: Relative path to the file from resources directory
            
            Returns:
                File content as string
            """
            try:
                resources_dir = self._file_facade._get_resources_directory()
                if not resources_dir:
                    return {
                        "success": False,
                        "error": "Resources directory not found",
                        "error_code": "NOT_FOUND",
                        "field": "resources_dir",
                        "expected": "A valid resources directory",
                        "hint": "Ensure the resources directory exists"
                    }
                
                requested_file = resources_dir / filepath
                
                # Security check - ensure file is within resources directory
                try:
                    requested_file.relative_to(resources_dir)
                except ValueError:
                    return {
                        "success": False,
                        "error": "Access denied: Path outside resources directory",
                        "error_code": "FORBIDDEN",
                        "field": "filepath",
                        "expected": "A path within the resources directory",
                        "hint": "Do not use .. or absolute paths"
                    }
                
                # Check if file exists
                if not requested_file.exists():
                    return {
                        "success": False,
                        "error": f"Resource not found: {filepath}",
                        "error_code": "NOT_FOUND",
                        "field": "filepath",
                        "expected": "A valid file path within resources directory",
                        "hint": "Check the file path for typos"
                    }
                
                # Check if file should be exposed
                if not self._file_facade._should_expose_file(requested_file):
                    return {
                        "success": False,
                        "error": f"Resource access restricted: {filepath}",
                        "error_code": "FORBIDDEN",
                        "field": "filepath",
                        "expected": "A file allowed for exposure",
                        "hint": "Check file permissions and exposure rules"
                    }
                
                # Create file info and check accessibility
                file_info = self._file_facade._create_file_resource_info(requested_file, resources_dir)
                if not file_info:
                    return {
                        "success": False,
                        "error": f"Cannot access resource: {filepath}",
                        "error_code": "FORBIDDEN",
                        "field": "filepath",
                        "expected": "A file allowed for exposure",
                        "hint": "Check file permissions and exposure rules"
                    }
                
                # Handle binary vs text files
                if file_info.is_binary:
                    import base64
                    content = requested_file.read_bytes()
                    return f"Binary file (base64): {base64.b64encode(content).decode('utf-8')}"
                else:
                    return requested_file.read_text(encoding='utf-8', errors='replace')
                    
            except Exception as e:
                logger.error(f"Error reading resource {filepath}: {e}")
                return {
                    "success": False,
                    "error": f"Error reading resource: {str(e)}",
                    "error_code": "INTERNAL_ERROR",
                    "details": str(e)
                }