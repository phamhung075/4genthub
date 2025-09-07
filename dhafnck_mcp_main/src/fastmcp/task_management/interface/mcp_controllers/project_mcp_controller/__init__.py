"""
Project MCP Controller - Modular Architecture

This module provides the main project MCP controller with modular architecture.
The controller delegates operations to specialized handlers through factory pattern.
"""

from .project_mcp_controller import ProjectMCPController

__all__ = ['ProjectMCPController']