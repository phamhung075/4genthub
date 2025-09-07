"""
Task MCP Controller - Modular Architecture

This module provides the main task MCP controller with modular architecture.
The controller delegates operations to specialized handlers through factory pattern.
"""

from .task_mcp_controller import TaskMCPController

__all__ = ['TaskMCPController']