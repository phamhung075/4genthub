"""Agent Invocation Handler"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AgentInvocationHandler:
    """Handler for agent invocation operations"""
    
    def __init__(self, call_agent_use_case):
        """
        Initialize handler with call agent use case.
        
        Args:
            call_agent_use_case: Application use case for agent operations
        """
        self._call_agent_use_case = call_agent_use_case
        logger.info("AgentInvocationHandler initialized")
    
    def invoke_agent(self, name_agent: str, available_agents: list) -> Dict[str, Any]:
        """
        Invoke an agent by name.
        
        Args:
            name_agent: Name of the agent to call
            available_agents: List of available agents for error reporting
            
        Returns:
            Dict containing operation result
        """
        try:
            if not name_agent:
                return {
                    "success": False,
                    "error": "Missing required field: name_agent",
                    "error_code": "MISSING_FIELD",
                    "field": "name_agent",
                    "expected": "A valid agent name string",
                    "hint": "Include 'name_agent' in your request body",
                    "available_agents": available_agents
                }
            
            return self._call_agent_use_case.execute(name_agent)
            
        except Exception as e:
            logger.error(f"Call agent error: {e}")
            return {
                "success": False,
                "error": f"Call agent operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e),
                "available_agents": available_agents
            }