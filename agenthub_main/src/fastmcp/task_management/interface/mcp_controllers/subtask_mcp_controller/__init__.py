"""
Subtask MCP Controller - Modular Architecture

This module provides the main subtask MCP controller with modular architecture.
The controller delegates operations to specialized handlers through factory pattern.
"""

from .subtask_mcp_controller import SubtaskMCPController

__all__ = ['SubtaskMCPController']