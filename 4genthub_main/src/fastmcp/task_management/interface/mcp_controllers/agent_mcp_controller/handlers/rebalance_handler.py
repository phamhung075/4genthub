"""
Agent Rebalance Handler

Handles agent rebalancing operations for optimizing agent assignments across project branches.
"""

import logging
from typing import Dict, Any
from .....application.facades.agent_application_facade import AgentApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class AgentRebalanceHandler:
    """Handler for agent rebalancing operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def rebalance_agents(self, facade: AgentApplicationFacade, project_id: str) -> Dict[str, Any]:
        """Rebalance agent assignments across project branches."""
        
        try:
            result = facade.rebalance_agents(project_id)
            
            # Extract rebalancing statistics if available
            rebalanced_count = result.get('rebalanced_agents', 0) if isinstance(result, dict) else 0
            
            return self._response_formatter.create_success_response(
                operation="rebalance",
                data=result,
                metadata={
                    "project_id": project_id,
                    "rebalanced_agents": rebalanced_count,
                    "success_message": f"Agent rebalancing completed successfully ({rebalanced_count} agents affected)"
                }
            )
            
        except Exception as e:
            logger.error(f"Error rebalancing agents: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="rebalance",
                error=f"Failed to rebalance agents: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id}
            )