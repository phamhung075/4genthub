"""Claude Agent MCP Controller

This controller provides MCP tool interface for generating Claude Code agent configurations.
Follows DDD principles by delegating all business logic to the application facade.
"""

import logging
from typing import Dict, Any, Optional, List
from ...application.facades.claude_agent_facade import ClaudeAgentFacade

logger = logging.getLogger(__name__)


class ClaudeAgentMCPController:
    """Controller for Claude Code agent generation via MCP tools."""
    
    def __init__(self, facade: Optional[ClaudeAgentFacade] = None):
        """Initialize the controller with a facade instance.
        
        Args:
            facade: Optional facade instance. If not provided, creates a new one.
        """
        self.facade = facade or ClaudeAgentFacade()
    
    def generate_claude_agent(
        self,
        action: str,
        name: Optional[str] = None,
        agent_type: Optional[str] = "custom",
        description: Optional[str] = None,
        expertise: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        initial_prompt: Optional[str] = None,
        language: Optional[str] = "Python",
        additional_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate or manage Claude Code agent configurations.
        
        Args:
            action: Action to perform ('create', 'list', 'get', 'delete')
            name: Name of the agent (required for create, get, delete)
            agent_type: Type of agent template to use (for create)
            description: Custom description for the agent (for create)
            expertise: List of expertise areas (for create)
            tools: List of tools the agent should use (for create)
            initial_prompt: Custom initial prompt (for create)
            language: Programming language for code-related agents (for create)
            additional_config: Additional configuration options (for create)
            
        Returns:
            Dict containing the result of the operation
        """
        try:
            # Validate action
            valid_actions = ['create', 'list', 'get', 'delete']
            if action not in valid_actions:
                return {
                    "success": False,
                    "error": f"Invalid action: {action}. Valid actions: {valid_actions}"
                }
            
            # Process based on action
            if action == 'create':
                if not name:
                    return {"success": False, "error": "'name' is required for create action"}
                
                # Parse expertise if provided as string
                if expertise and isinstance(expertise, str):
                    expertise = [e.strip() for e in expertise.split(',')]
                
                # Parse tools if provided as string
                if tools and isinstance(tools, str):
                    tools = [t.strip() for t in tools.split(',')]
                
                return self.facade.create_agent(
                    name=name,
                    agent_type=agent_type,
                    description=description,
                    expertise=expertise,
                    tools=tools,
                    initial_prompt=initial_prompt,
                    language=language,
                    additional_config=additional_config
                )
            
            elif action == 'list':
                return self.facade.list_agents()
            
            elif action == 'get':
                if not name:
                    return {"success": False, "error": "'name' is required for get action"}
                return self.facade.get_agent(name)
            
            elif action == 'delete':
                if not name:
                    return {"success": False, "error": "'name' is required for delete action"}
                return self.facade.delete_agent(name)
            
        except Exception as e:
            return {"success": False, "error": f"Controller error: {str(e)}"}