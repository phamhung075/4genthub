"""Unified Agent MCP Controller - Complete Operations Package

This package contains the unified implementation that combines both agent management
(register, assign, update, etc.) and agent invocation (call_agent) operations.
"""

from .agent_mcp_controller import AgentMCPController

# Maintain backward compatibility aliases
UnifiedAgentMCPController = AgentMCPController

__all__ = ['UnifiedAgentMCPController', 'AgentMCPController']