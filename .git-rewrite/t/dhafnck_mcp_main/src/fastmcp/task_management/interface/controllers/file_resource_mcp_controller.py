"""File Resource MCP Controller

This controller handles MCP tool registration for file resource exposure,
following DDD principles by delegating business logic to application services.
It exposes all files in the project directory as MCP resources.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Annotated, Optional, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from fastmcp.resources import FileResource, DirectoryResource
from fastmcp.utilities.logging import get_logger
from ...application.facades.file_resource_application_facade import FileResourceApplicationFacade

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
        self._file_facade = FileResourceApplicationFacade(self.project_root)
        logger.info(f"FileResourceMCPController initialized with project root: {self.project_root}")
    
    def register_resources(self, mcp: "FastMCP"):
        """Register all file resources with the FastMCP server"""
        logger.info("Registering file resources...")
        
        # Register directory listing resource for the resources directory only
        resources_dir = self._file_facade._get_resources_directory()
        if resources_dir and resources_dir.exists():
            self._register_directory_resource(mcp, resources_dir, "resources")
            logger.info(f"Registered resources directory: {resources_dir}")
        else:
            logger.warning("Resources directory not found, skipping directory resource registration")
        
        # Register individual file resources
        self._register_file_resources(mcp)
        
        # Register file template for dynamic file access
        self._register_file_template(mcp)
        
        logger.info("File resources registered successfully")
    
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
                    tags={"directory", "listing", "resource"}
                )
                mcp.add_resource(directory_resource)
                logger.debug(f"Registered directory resource: {directory}")
        except Exception as e:
            logger.warning(f"Failed to register directory resource for {directory}: {e}")
            return {
                "success": False,
                "error": f"Failed to register directory resource: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def _register_file_resources(self, mcp: "FastMCP"):
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
            return {
                "success": False,
                "error": f"Failed to register file resource: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def _register_single_file(self, mcp: "FastMCP", file_path: Path):
        """Register a single file as a resource (legacy method)"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            uri = f"file://{relative_path.as_posix()}"
            
            # Determine MIME type based on file extension
            mime_type = self._get_mime_type(file_path)
            
            file_resource = FileResource(
                uri=uri,
                path=file_path,
                name=file_path.name,
                description=f"File: {relative_path}",
                mime_type=mime_type,
                tags={"file", file_path.suffix.lstrip('.') if file_path.suffix else "no-extension"}
            )
            
            mcp.add_resource(file_resource)
            logger.debug(f"Registered file resource: {relative_path}")
            
        except Exception as e:
            logger.warning(f"Failed to register file resource for {file_path}: {e}")
    
    def _register_file_template(self, mcp: "FastMCP"):
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
                if not requested_file.exists():
                    return {
                        "success": False,
                        "error": f"Resource not found: {filepath}",
                        "error_code": "NOT_FOUND",
                        "field": "filepath",
                        "expected": "A valid file path within resources directory",
                        "hint": "Check the file path for typos"
                    }
                if not self._file_facade._should_expose_file(requested_file):
                    return {
                        "success": False,
                        "error": f"Resource access restricted: {filepath}",
                        "error_code": "FORBIDDEN",
                        "field": "filepath",
                        "expected": "A file allowed for exposure",
                        "hint": "Check file permissions and exposure rules"
                    }
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
    
    def _should_expose_file(self, file_path: Path) -> bool:
        """Determine if a file should be exposed as a resource"""
        # Skip hidden files and directories
        if any(part.startswith('.') for part in file_path.parts):
            # Allow some important hidden files
            allowed_hidden = {'.gitignore', '.env.example'}
            if file_path.name not in allowed_hidden:
                return False
        
        # Skip certain directories
        skip_dirs = {
            '__pycache__', 'node_modules', '.git', '.venv', 'venv',
            '.pytest_cache', '.coverage', 'htmlcov', '.ruff_cache',
            'dist', 'build', '.cache', 'logs'
        }
        
        if any(part in skip_dirs for part in file_path.parts):
            return False
        
        # Skip certain file types
        skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dylib', '.dll'}
        if file_path.suffix.lower() in skip_extensions:
            return False
        
        # Skip very large files (> 10MB)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:
                return False
        except OSError:
            return False
        
        return True
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension"""
        extension_map = {
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.ts': 'application/typescript',
            '.jsx': 'text/jsx',
            '.tsx': 'text/tsx',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.yaml': 'application/yaml',
            '.yml': 'application/yaml',
            '.toml': 'application/toml',
            '.md': 'text/markdown',
            '.mdx': 'text/mdx',
            '.txt': 'text/plain',
            '.sh': 'application/x-shellscript',
            '.xml': 'application/xml',
            '.csv': 'text/csv',
            '.sql': 'application/sql',
            '.dockerfile': 'text/x-dockerfile',
            '.gitignore': 'text/plain',
        }
        
        return extension_map.get(file_path.suffix.lower(), 'text/plain')
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary"""
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
            '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz',
            '.exe', '.dll', '.so', '.dylib',
            '.mp3', '.mp4', '.avi', '.mov',
            '.woff', '.woff2', '.ttf', '.otf'
        }
        
        if file_path.suffix.lower() in binary_extensions:
            return True
        
        # Check file content for binary data
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except (OSError, IOError):
            return False 