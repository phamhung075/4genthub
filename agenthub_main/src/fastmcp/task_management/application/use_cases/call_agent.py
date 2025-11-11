"""Call Agent Use Case

DDD-compliant use case for calling/loading agents.
This wraps the agent_management module's call_agent functionality.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CallAgentUseCase:
    """Use case for calling/loading specialized agents.

    This is a lightweight wrapper around the agent_management module's
    call_agent functionality, providing a DDD-compliant interface.
    """

    def __init__(self):
        """Initialize the CallAgentUseCase."""
        pass

    def execute(self, name_agent: str, user_id: str | None = None) -> dict[str, Any]:
        """
        Execute the call agent use case.

        Args:
            name_agent: Agent slug (e.g., "coding-agent", "master-orchestrator-agent")
            user_id: Optional user ID (extracted from JWT token if not provided)

        Returns:
            Dictionary containing agent configuration and metadata

        Raises:
            ValueError: If agent template not found
        """
        # Import here to avoid circular dependency
        from ....agent_management.interface.mcp_controllers.call_agent import (
            call_agent_mcp_tool,
        )

        return call_agent_mcp_tool(name_agent=name_agent, user_id=user_id)
