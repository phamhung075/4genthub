"""Logging utilities for FastMCP."""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Literal, Optional

from rich.console import Console
from rich.logging import RichHandler

from .environment import detect_environment, ensure_log_directory_exists, get_log_file_path


def get_logger(name: str) -> logging.Logger:
    """Get a logger nested under FastMCP namespace.

    Args:
        name: the name of the logger, which will be prefixed with 'FastMCP.'

    Returns:
        a configured logger instance
    """
    return logging.getLogger(f"FastMCP.{name}")


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    logger: logging.Logger | None = None,
    enable_rich_tracebacks: bool = True,
    enable_file_logging: bool = True,
    log_file_name: str = "dhafnck_mcp.log",
) -> None:
    """
    Configure logging for FastMCP with environment-aware file logging.

    Args:
        logger: the logger to configure
        level: the log level to use
        enable_rich_tracebacks: whether to enable rich tracebacks
        enable_file_logging: whether to enable file logging
        log_file_name: name of the log file
    """

    if logger is None:
        logger = logging.getLogger("FastMCP")

    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates on reconfiguration
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)

    # 1. Console handler (always enabled)
    console_handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=enable_rich_tracebacks,
    )
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. File handler (environment-aware)
    if enable_file_logging:
        try:
            environment = detect_environment()
            log_file_path = get_log_file_path(log_file_name)

            # Ensure log directory exists and is writable
            ensure_log_directory_exists(log_file_path.parent)

            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )

            # Use detailed formatter for file logs
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Log successful file handler setup
            logger.info(f"File logging enabled: {log_file_path} (environment: {environment})")

        except Exception as e:
            # If file logging fails, log error but continue with console logging
            logger.error(f"Failed to set up file logging: {e}")
            logger.warning("Continuing with console logging only")


def setup_comprehensive_logging(
    log_level: str = "INFO",
    app_name: str = "DhafnckMCP",
    enable_file_logging: bool = True,
) -> None:
    """
    Set up comprehensive logging for the entire application.

    Args:
        log_level: The log level to use
        app_name: Name of the application for log formatting
        enable_file_logging: Whether to enable file logging
    """

    # Configure FastMCP logger
    configure_logging(
        level=log_level,
        enable_file_logging=enable_file_logging,
        log_file_name=f"{app_name.lower()}.log"
    )

    # Configure root logger for any other loggers
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(getattr(logging, log_level))

        # Add console handler to root logger
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # Add file handler to root logger if enabled
        if enable_file_logging:
            try:
                log_file_path = get_log_file_path(f"{app_name.lower()}_all.log")
                ensure_log_directory_exists(log_file_path.parent)

                file_handler = logging.handlers.RotatingFileHandler(
                    filename=log_file_path,
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=3,
                    encoding='utf-8'
                )
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)

            except Exception as e:
                # Log to console if file logging setup fails
                console_handler.stream.write(f"WARNING: Failed to set up root file logging: {e}\n")


def get_logging_info() -> dict:
    """
    Get information about the current logging configuration.

    Returns:
        Dictionary with logging configuration details
    """
    from .environment import get_environment_info

    env_info = get_environment_info()
    fastmcp_logger = logging.getLogger("FastMCP")
    root_logger = logging.getLogger()

    return {
        "environment": env_info,
        "loggers": {
            "FastMCP": {
                "level": logging.getLevelName(fastmcp_logger.level),
                "handlers": [
                    {
                        "type": type(handler).__name__,
                        "level": logging.getLevelName(handler.level),
                        "formatter": str(handler.formatter._fmt) if hasattr(handler.formatter, '_fmt') else None
                    }
                    for handler in fastmcp_logger.handlers
                ],
                "propagate": fastmcp_logger.propagate
            },
            "root": {
                "level": logging.getLevelName(root_logger.level),
                "handlers": [
                    {
                        "type": type(handler).__name__,
                        "level": logging.getLevelName(handler.level),
                        "formatter": str(handler.formatter._fmt) if hasattr(handler.formatter, '_fmt') else None
                    }
                    for handler in root_logger.handlers
                ]
            }
        }
    }
