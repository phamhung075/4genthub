"""File Resource Application Facade

This facade provides a unified interface for file resource management operations,
orchestrating domain services and maintaining proper DDD layer separation.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FileResourceInfo:
    """Data transfer object for file resource information"""
    path: Path
    relative_path: Path
    uri: str
    name: str
    description: str
    mime_type: str
    size: int
    is_binary: bool
    tags: set[str]


class FileResourceApplicationFacade:
    """
    Application facade for file resource management.
    
    This facade orchestrates file resource operations and provides a clean
    interface for the controller layer following DDD principles.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize the file resource application facade.
        
        Args:
            project_root: Root path of the project
        """
        self.project_root = Path(project_root).resolve()
        logger.info(f"FileResourceApplicationFacade initialized with project root: {self.project_root}")
    
    def _get_resources_directory(self) -> Optional[Path]:
        """
        Get the resources directory path, handling both local and Docker environments.
        
        Returns:
            Path to the resources directory or None if not found
        """
        # Try absolute Docker path first (/data/resources)
        absolute_docker_resources = Path("/data/resources")
        if absolute_docker_resources.exists() and absolute_docker_resources.is_dir():
            # logger.info(f"Using absolute Docker resources directory: {absolute_docker_resources}")
            return absolute_docker_resources
        
        # Try relative Docker path (data/resources)
        docker_resources = self.project_root / "data" / "resources"
        if docker_resources.exists() and docker_resources.is_dir():
            logger.info(f"Using Docker resources directory: {docker_resources}")
            return docker_resources
        
        # Try local development path (00_RESOURCES)
        local_resources = self.project_root / "00_RESOURCES"
        if local_resources.exists() and local_resources.is_dir():
            logger.info(f"Using local resources directory: {local_resources}")
            return local_resources
        
        # Check if we're in a subdirectory and look for 00_RESOURCES in parent directories
        current_path = self.project_root
        for _ in range(3):  # Check up to 3 levels up
            parent_resources = current_path / "00_RESOURCES"
            if parent_resources.exists() and parent_resources.is_dir():
                logger.info(f"Using parent resources directory: {parent_resources}")
                return parent_resources
            current_path = current_path.parent
            if current_path == current_path.parent:  # Reached filesystem root
                break
        
        logger.warning("No resources directory found (tried data/resources and 00_RESOURCES)")
        return None
    
    def discover_files(self) -> List[FileResourceInfo]:
        """
        Discover all files in the 00_RESOURCES directory that should be exposed as resources.
        Handles both local development (00_RESOURCES) and Docker deployment (data/resources) paths.
        
        Returns:
            List of FileResourceInfo objects for discovered files
        """
        logger.info("Discovering files for resource exposure from 00_RESOURCES...")
        
        discovered_files = []
        
        # Determine the resources directory path
        resources_dir = self._get_resources_directory()
        
        if not resources_dir or not resources_dir.exists():
            logger.warning(f"Resources directory not found: {resources_dir}")
            return discovered_files
        
        logger.info(f"Scanning resources directory: {resources_dir}")
        
        # Define patterns for files to include
        include_patterns = [
            "*.md", "*.py", "*.json", "*.toml", "*.yaml", "*.yml", 
            "*.txt", "*.sh", "*.js", "*.ts", "*.css", "*.html",
            "*.mdx", "*.jsx", "*.tsx", "*.sql", "*.env", "*.conf",
            "*.ini", "*.cfg", "*.xml", "*.csv", "*.log", "*.mdc"
        ]
        
        # Scan all files in the resources directory
        for pattern in include_patterns:
            for file_path in resources_dir.rglob(pattern):
                if self._should_expose_file(file_path):
                    file_info = self._create_file_resource_info(file_path, resources_dir)
                    if file_info:
                        discovered_files.append(file_info)
        
        logger.info(f"Discovered {len(discovered_files)} files for resource exposure from {resources_dir}")
        return discovered_files
    
    def get_file_content(self, relative_path: str) -> Dict[str, Any]:
        """
        Get file content for a given relative path.
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            Dictionary containing file content and metadata
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file access is restricted
        """
        try:
            # Resolve the file path
            requested_path = self.project_root / relative_path
            resolved_path = requested_path.resolve()
            
            # Security validation
            self._validate_file_access(resolved_path, relative_path)
            
            # Get file info
            file_info = self._create_file_resource_info(resolved_path)
            if not file_info:
                raise ValueError(f"File access restricted: {relative_path}")
            
            # Read content
            if file_info.is_binary:
                import base64
                content = resolved_path.read_bytes()
                content_data = base64.b64encode(content).decode('utf-8')
                content_type = "binary"
            else:
                content_data = resolved_path.read_text(encoding='utf-8', errors='replace')
                content_type = "text"
            
            return {
                "content": content_data,
                "content_type": content_type,
                "mime_type": file_info.mime_type,
                "size": file_info.size,
                "name": file_info.name,
                "path": str(file_info.relative_path),
                "tags": list(file_info.tags)
            }
            
        except Exception as e:
            logger.error(f"Error getting file content for {relative_path}: {e}")
            raise
    
    def get_directory_listing(self, relative_path: str = "") -> Dict[str, Any]:
        """
        Get directory listing for a given path.
        
        Args:
            relative_path: Path relative to project root (empty for root)
            
        Returns:
            Dictionary containing directory listing
        """
        try:
            if relative_path:
                target_path = self.project_root / relative_path
            else:
                target_path = self.project_root
            
            target_path = target_path.resolve()
            
            # Security validation
            if not str(target_path).startswith(str(self.project_root)):
                raise ValueError(f"Access denied: Path outside project root")
            
            if not target_path.exists():
                raise FileNotFoundError(f"Directory not found: {relative_path}")
            
            if not target_path.is_dir():
                raise ValueError(f"Not a directory: {relative_path}")
            
            # Get directory contents
            files = []
            directories = []
            
            for item in target_path.iterdir():
                if self._should_expose_file(item):
                    relative_item_path = item.relative_to(self.project_root)
                    
                    if item.is_file():
                        file_info = self._create_file_resource_info(item)
                        if file_info:
                            files.append({
                                "name": item.name,
                                "path": str(relative_item_path),
                                "size": file_info.size,
                                "mime_type": file_info.mime_type,
                                "is_binary": file_info.is_binary
                            })
                    elif item.is_dir():
                        directories.append({
                            "name": item.name,
                            "path": str(relative_item_path)
                        })
            
            return {
                "path": relative_path,
                "directories": sorted(directories, key=lambda x: x["name"]),
                "files": sorted(files, key=lambda x: x["name"]),
                "total_files": len(files),
                "total_directories": len(directories)
            }
            
        except Exception as e:
            logger.error(f"Error getting directory listing for {relative_path}: {e}")
            raise
    
    def _create_file_resource_info(self, file_path: Path, base_path: Optional[Path] = None) -> Optional[FileResourceInfo]:
        """Create FileResourceInfo for a given file path
        
        Args:
            file_path: Path to the file
            base_path: Base path for relative path calculation (defaults to project_root)
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            
            # Use provided base_path or fall back to project_root
            if base_path is None:
                base_path = self.project_root
            
            # Calculate relative path from the base path
            try:
                relative_path = file_path.relative_to(base_path)
            except ValueError:
                # If file is not under base_path, use relative to project_root
                relative_path = file_path.relative_to(self.project_root)
            
            # Create URI with resources prefix for files from resources directory
            resources_dir = self._get_resources_directory()
            if resources_dir and str(file_path).startswith(str(resources_dir)):
                # Make path relative to resources directory for cleaner URIs
                resources_relative = file_path.relative_to(resources_dir)
                uri = f"resources:///{resources_relative.as_posix()}"
            else:
                uri = f"file:///{relative_path.as_posix()}"
            
            mime_type = self._get_mime_type(file_path)
            is_binary = self._is_binary_file(file_path)
            size = file_path.stat().st_size
            
            # Generate tags
            tags = {"file", "resource"}
            if file_path.suffix:
                tags.add(file_path.suffix.lstrip('.'))
            
            # Add category tags based on file type
            if mime_type.startswith('text/'):
                tags.add("text")
            elif mime_type.startswith('application/'):
                tags.add("application")
            
            if is_binary:
                tags.add("binary")
            
            return FileResourceInfo(
                path=file_path,
                relative_path=relative_path,
                uri=uri,
                name=file_path.name,
                description=f"File: {relative_path}",
                mime_type=mime_type,
                size=size,
                is_binary=is_binary,
                tags=tags
            )
            
        except Exception as e:
            logger.warning(f"Error creating file resource info for {file_path}: {e}")
            return None
    
    def _validate_file_access(self, resolved_path: Path, relative_path: str):
        """Validate that file access is allowed"""
        # Security check: ensure the resolved path is within project root
        if not str(resolved_path).startswith(str(self.project_root)):
            raise ValueError(f"Access denied: Path outside project root")
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        
        if not resolved_path.is_file():
            raise ValueError(f"Not a file: {relative_path}")
        
        # Check if file should be exposed
        if not self._should_expose_file(resolved_path):
            raise ValueError(f"File access restricted: {relative_path}")
    
    def _should_expose_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be exposed as a resource.
        Now focuses specifically on files within the 00_RESOURCES directory.
        """
        # Get the resources directory
        resources_dir = self._get_resources_directory()
        
        # If no resources directory found, don't expose any files
        if not resources_dir:
            return False
        
        # Only expose files that are within the resources directory
        try:
            file_path.relative_to(resources_dir)
        except ValueError:
            # File is not within the resources directory
            return False
        
        # Skip hidden files and directories (but allow some important ones)
        if any(part.startswith('.') for part in file_path.parts):
            allowed_hidden = {'.gitignore', '.env.example', '.dockerignore', '.editorconfig'}
            if file_path.name not in allowed_hidden:
                return False
        
        # Skip certain directories even within resources
        skip_dirs = {
            '__pycache__', 'node_modules', '.git', '.venv', 'venv',
            '.pytest_cache', '.coverage', 'htmlcov', '.ruff_cache',
            'dist', 'build', '.cache', 'logs', '.mypy_cache', 'tmp', 'temp'
        }
        
        if any(part in skip_dirs for part in file_path.parts):
            return False
        
        # Skip certain file types
        skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dylib', '.dll', '.lock', '.tmp'}
        if file_path.suffix.lower() in skip_extensions:
            return False
        
        # Skip very large files (> 10MB) - resources should generally be smaller
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:
                logger.debug(f"Skipping large file: {file_path} ({file_path.stat().st_size} bytes)")
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
            '.env': 'text/plain',
            '.ini': 'text/plain',
            '.cfg': 'text/plain',
            '.conf': 'text/plain',
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
        
        # Check file content for binary data (sample first 1024 bytes)
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except (OSError, IOError):
            return False 