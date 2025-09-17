"""Agent Discovery Service"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class AgentDiscoveryService:
    """Service for discovering available agents"""
    
    def get_available_agents(self) -> List[str]:
        """
        Discover available agents from the agent library directory.
        
        Returns:
            List of available agent names
        """
        # Navigate to the correct agent-library path
        # From this file's location, we need to go up to the project root
        # then into 4genthub_main/agent-library/agents
        current_dir = os.path.dirname(__file__)
        # Go up to src/fastmcp/task_management/interface/mcp_controllers/call_agent_mcp_controller
        # then up 7 levels to project root
        project_root = os.path.abspath(os.path.join(current_dir, '../../../../../../..'))
        AGENT_DIR = os.path.join(project_root, '4genthub_main/agent-library/agents')
        available_agents = []
        
        try:
            abs_agent_dir = os.path.abspath(AGENT_DIR)
            if os.path.exists(abs_agent_dir):
                for entry in os.listdir(abs_agent_dir):
                    if entry.endswith('_agent') and os.path.isdir(os.path.join(abs_agent_dir, entry)):
                        available_agents.append(entry)
                logger.debug(f"Found {len(available_agents)} available agents")
            else:
                logger.debug(f"Agent directory not found: {abs_agent_dir}")
        except Exception as e:
            logger.debug(f"Error discovering agents: {e}")
        
        return available_agents