"""
Git Branch MCP Controller - Modular Architecture

This module provides the main git branch MCP controller with modular architecture.
The controller delegates operations to specialized handlers through factory pattern.
"""

from .git_branch_mcp_controller import GitBranchMCPController

__all__ = ['GitBranchMCPController']