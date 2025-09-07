"""File utility functions for File Resource MCP Controller"""

import logging
from pathlib import Path
from typing import Dict, Any

from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


class FileUtils:
    """Utility functions for file operations and metadata"""
    
    @staticmethod
    def should_expose_file(file_path: Path) -> bool:
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
    
    @staticmethod
    def get_mime_type(file_path: Path) -> str:
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
    
    @staticmethod
    def is_binary_file(file_path: Path) -> bool:
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
                return b'\\0' in chunk
        except (OSError, IOError):
            return False
    
    @staticmethod
    def register_single_file_legacy(mcp, file_path: Path, project_root: Path) -> Dict[str, Any]:
        """Register a single file as a resource (legacy method)"""
        try:
            from fastmcp.resources import FileResource
            
            relative_path = file_path.relative_to(project_root)
            uri = f"file://{relative_path.as_posix()}"
            
            # Determine MIME type based on file extension
            mime_type = FileUtils.get_mime_type(file_path)
            
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
            
            return {
                "success": True,
                "message": f"File resource registered: {relative_path}",
                "uri": uri,
                "mime_type": mime_type
            }
            
        except Exception as e:
            logger.warning(f"Failed to register file resource for {file_path}: {e}")
            return {
                "success": False,
                "error": f"Failed to register file resource: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }