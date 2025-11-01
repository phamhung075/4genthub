"""Agent management module for dynamic per-user agent instances.

This module implements the user-specific agent system where:
- agent-library provides immutable templates
- Each user gets their own customizable agent instances
- Agents are stored per user_id with complete isolation
- Markdown format enables frontend editing
- Full sharing and importing capabilities

Architecture:
- Domain: Business entities and logic (AgentTemplate, UserAgentInstance)
- Application: Use cases and facades
- Infrastructure: Repositories, ORM models, database access
- Interface: MCP tools and REST API controllers
"""

__version__ = "1.0.0"
