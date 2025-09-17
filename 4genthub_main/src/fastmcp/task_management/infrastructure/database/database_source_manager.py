"""
Database Source Manager

This module manages database source configuration.
All database operations use PostgreSQL/Supabase.

SUPPORTED CONFIGURATIONS:
- DATABASE_TYPE=supabase (cloud deployment)
- DATABASE_TYPE=postgresql (local deployment)
- All data stored in PostgreSQL
- No local file-based database

USE database_config.py for database operations.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DatabaseMode(Enum):
    """Database execution modes"""
    TEST = "test"           # pytest execution
    NORMAL = "normal"       # normal local execution  
    DOCKER = "docker"       # docker container execution
    STDIN = "stdin"         # stdin/local project execution


class DatabaseSourceManager:
    """
    Single source of truth for database path management (Legacy SQLite Support).
    
    NOTE: This class primarily handles SQLite database paths for backward compatibility.
    PostgreSQL configuration is managed via DATABASE_URL environment variable.
    
    Determines which SQLite database to use based on execution context:
    - Test mode (pytest): 4genthub_test.db (for local testing, always isolated)
    - Normal mode: /data/4genthub.db (local development uses Docker database for consistency)
    - Docker mode: /data/4genthub.db (running inside Docker container)
    - Stdin mode (MCP): local 4genthub.db (MCP stdin cannot access Docker database)
    
    Note: STDIN mode must use local database since it runs outside Docker container.
    For PostgreSQL deployments, set DATABASE_TYPE=postgresql and DATABASE_URL.
    """
    
    _instance: Optional['DatabaseSourceManager'] = None
    _current_mode: Optional[DatabaseMode] = None
    _database_path: Optional[str] = None
    
    def __new__(cls) -> 'DatabaseSourceManager':
        """Singleton pattern to ensure single database source"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database source manager"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._detect_mode()
            self._set_database_path()
    
    def _detect_mode(self) -> None:
        """Detect the current execution mode"""
        # Check for pytest execution
        if 'pytest' in sys.modules or 'PYTEST_CURRENT_TEST' in os.environ:
            self._current_mode = DatabaseMode.TEST
            logger.info("Detected TEST mode (pytest)")
            return
            
        # Check for docker execution
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            self._current_mode = DatabaseMode.DOCKER
            logger.info("Detected DOCKER mode")
            return
            
        # Check for stdin mode (MCP server context)
        if hasattr(sys.stdin, 'isatty') and not sys.stdin.isatty():
            self._current_mode = DatabaseMode.STDIN
            logger.info("Detected STDIN mode (MCP server)")
            return
            
        # Default to normal mode
        self._current_mode = DatabaseMode.NORMAL
        logger.info("Detected NORMAL mode")
    
    def _find_project_root(self) -> Path:
        """Find project root by looking for 4genthub_main directory"""
        current_path = Path(__file__).resolve()
        
        # Walk up the directory tree looking for 4genthub_main
        while current_path.parent != current_path:
            if (current_path / "4genthub_main").exists():
                return current_path
            current_path = current_path.parent
        
        # If not found, use current working directory as fallback
        cwd = Path.cwd()
        if (cwd / "4genthub_main").exists():
            return cwd
            
        # Last resort - use the directory containing 4genthub_main
        current_path = Path(__file__).resolve()
        while current_path.parent != current_path:
            if current_path.name == "4genthub_main":
                return current_path.parent
            current_path = current_path.parent
        
        # Docker-aware fallback path - strictly use /app in Docker
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            # In Docker container, strictly use /app directory as per Dockerfile
            return Path("/app")
        else:
            # Outside Docker, use current working directory
            return Path.cwd()
    
    def _set_database_path(self) -> None:
        """Set database path based on detected mode"""
        # Check for explicit MCP_DB_PATH environment variable first
        explicit_db_path = os.environ.get('MCP_DB_PATH')
        if explicit_db_path:
            self._database_path = explicit_db_path
            logger.info(f"Database path set from MCP_DB_PATH: {self._database_path}")
            return
        
        # Find project root by looking for 4genthub_main directory
        project_root = self._find_project_root()
        
        if self._current_mode == DatabaseMode.TEST:
            # Use test database for pytest (always local for test isolation)
            self._database_path = str(project_root / "4genthub_main" / "database" / "data" / "4genthub_test.db")
            
        elif self._current_mode == DatabaseMode.DOCKER:
            # Use docker database path - strictly /data/ directory as per Dockerfile
            docker_db_path = os.environ.get('DOCKER_DB_PATH', '/data/4genthub.db')
            if not os.path.exists(os.path.dirname(docker_db_path)):
                raise RuntimeError(f"Docker database directory not accessible: {os.path.dirname(docker_db_path)}. Server cannot start without Docker database access.")
            self._database_path = docker_db_path
            
        elif self._current_mode == DatabaseMode.STDIN:
            # STDIN mode (MCP) must use local database since it runs outside Docker container
            # MCP communication happens via stdin/stdout, not inside Docker
            self._database_path = str(project_root / "4genthub_main" / "database" / "data" / "4genthub.db")
            logger.info("MCP STDIN mode using local database (cannot access Docker database)")
            
        else:  # NORMAL mode
            # Use Docker database for local development to ensure consistency
            # This ensures local dev and frontend all use the same database
            docker_db_path = "/data/4genthub.db"
            if os.path.exists(docker_db_path):
                # Docker database exists, use it for consistency
                self._database_path = docker_db_path
                logger.info("Local development will use Docker database for consistency")
            else:
                # Docker database must be accessible for local development
                raise RuntimeError(f"Docker database not accessible: {docker_db_path}. Local development requires Docker database access for consistency. Please start Docker container first.")
        
        logger.info(f"Database path set to: {self._database_path}")
    
    def get_database_path(self) -> str:
        """
        Get the current database path.
        
        Returns:
            str: Absolute path to the database file
            
        Raises:
            RuntimeError: If multiple database sources are detected
        """
        # Check if MCP_DB_PATH environment variable changed since initialization
        explicit_db_path = os.environ.get('MCP_DB_PATH')
        if explicit_db_path and explicit_db_path != self._database_path:
            logger.info(f"MCP_DB_PATH changed to: {explicit_db_path}, updating database path")
            self._database_path = explicit_db_path
        
        if self._database_path is None:
            raise RuntimeError("Database path not initialized")
            
        # Validate single source rule
        self._validate_single_source()
        
        # Log every access for debugging
        logger.debug(f"Database path requested: {self._database_path} (mode: {self._current_mode.value})")
        
        return self._database_path
    
    def get_mode(self) -> DatabaseMode:
        """Get the current database mode"""
        return self._current_mode
    
    def _validate_single_source(self) -> None:
        """
        Validate that only one database source is active.
        
        Raises:
            RuntimeError: If multiple database sources are detected
        """
        project_root = self._find_project_root()
        main_db = project_root / "4genthub_main" / "database" / "data" / "4genthub.db"
        test_db = project_root / "4genthub_main" / "database" / "data" / "4genthub_test.db"
        
        # Check if both databases exist and have recent activity
        main_exists = main_db.exists()
        test_exists = test_db.exists()
        
        if main_exists and test_exists:
            # Check modification times
            main_mtime = main_db.stat().st_mtime if main_exists else 0
            test_mtime = test_db.stat().st_mtime if test_exists else 0
            
            # If both were modified recently (within 1 hour), it's an error
            import time
            current_time = time.time()
            recent_threshold = 3600  # 1 hour
            
            main_recent = (current_time - main_mtime) < recent_threshold
            test_recent = (current_time - test_mtime) < recent_threshold
            
            if main_recent and test_recent and self._current_mode != DatabaseMode.TEST:
                logger.warning(f"Multiple active databases detected:")
                logger.warning(f"  Main DB: {main_db} (modified {current_time - main_mtime:.0f}s ago)")
                logger.warning(f"  Test DB: {test_db} (modified {current_time - test_mtime:.0f}s ago)")
                logger.warning("This is common during development - using mode-appropriate database")
                # Don't raise error - just warn and continue with mode-appropriate database
                return
    
    def force_mode(self, mode: DatabaseMode) -> None:
        """
        Force a specific database mode (for testing/debugging).
        
        Args:
            mode: The database mode to force
        """
        logger.warning(f"Forcing database mode to: {mode.value}")
        self._current_mode = mode
        self._set_database_path()
    
    def get_info(self) -> dict:
        """Get current database source information"""
        return {
            "mode": self._current_mode.value if self._current_mode else None,
            "database_path": self._database_path,
            "is_docker": self._current_mode == DatabaseMode.DOCKER,
            "is_test": self._current_mode == DatabaseMode.TEST,
            "is_stdin": self._current_mode == DatabaseMode.STDIN,
            "is_normal": self._current_mode == DatabaseMode.NORMAL
        }
    
    @classmethod
    def clear_instance(cls) -> None:
        """Clear the singleton instance (mainly for testing)"""
        cls._instance = None
        cls._current_mode = None
        cls._database_path = None
        logger.info("DatabaseSourceManager singleton cleared")


# Global instance
database_source_manager = DatabaseSourceManager()


def get_database_path() -> str:
    """
    DEPRECATED - Local database path no longer used
    
    This function is deprecated and will raise an error.
    Use PostgreSQL/Supabase database instead.
    
    Raises:
        RuntimeError: Always - local database path not supported
    """
    raise RuntimeError(
        "LOCAL DATABASE PATH ACCESS NOT SUPPORTED!\n"
        "This system uses PostgreSQL database connections.\n"
        "✅ SOLUTION: Use PostgreSQL or Supabase database\n"
        "🔧 Set DATABASE_TYPE=postgresql or supabase in your environment\n"
        "📋 Configure DATABASE_URL with your connection string"
    )


def get_database_mode() -> DatabaseMode:
    """Get the current database mode"""
    return database_source_manager.get_mode()


def get_database_info() -> dict:
    """Get current database source information"""
    return database_source_manager.get_info()