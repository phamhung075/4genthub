"""Enhanced logging configuration for unified log management."""

import logging
import sys
import os
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import datetime

def get_project_root() -> Path:
    """Get the project root directory."""
    current_dir = Path(__file__).resolve()
    # Navigate up from src/fastmcp/task_management/infrastructure/
    project_root = current_dir.parent.parent.parent.parent.parent
    
    # In Docker, try to use /app/logs if available, otherwise fallback to project root
    if Path('/app').exists():
        return Path('/app')
    return project_root

def init_logging(
    backend_log_path: Optional[str] = None,
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """Initialize unified logging configuration for backend."""
    
    # Get project root and ensure logs directory exists
    project_root = get_project_root()
    logs_dir = project_root / "logs"
    
    # Try to create logs directory with better error handling
    try:
        logs_dir.mkdir(exist_ok=True)
    except PermissionError:
        # If we can't create in the preferred location, use /tmp
        logs_dir = Path("/tmp/dhafnck_logs")
        logs_dir.mkdir(exist_ok=True)
        logging.warning(f"Could not create logs in {project_root / 'logs'}, using {logs_dir}")
    
    # Set default backend log path
    if backend_log_path is None:
        backend_log_path = str(logs_dir / "backend.log")
    
    # Create unique logger identifier with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    logger_id = f"backend_{timestamp}"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter with unique identifier
    formatter = logging.Formatter(
        f'[{logger_id}] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        backend_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    
    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log initialization
    logging.info(f"Backend logging initialized - ID: {logger_id}")
    logging.info(f"Log file: {backend_log_path}")
    logging.info(f"Log level: {log_level}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)