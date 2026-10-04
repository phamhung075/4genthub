"""Unified Agent MCP Controller - Complete Operations Package

This package contains the unified implementation of agent management
operations (register, assign, update, etc.).
"""

from .agent_mcp_controller import AgentMCPController

# Maintain backward compatibility aliases
UnifiedAgentMCPController = AgentMCPController

__all__ = ["UnifiedAgentMCPController", "AgentMCPController"]
