"""
Agent API Controller

This controller handles frontend agent metadata operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from typing import Dict, Any, List, Optional

from ...application.facades.agent_application_facade import AgentApplicationFacade
from ...application.services.facade_service import FacadeService

logger = logging.getLogger(__name__)


class AgentAPIController:
    """
    API Controller for agent metadata operations.
    
    This controller provides a clean interface between frontend routes and
    application services, ensuring proper separation of concerns.
    """
    
    def __init__(self):
        """Initialize the controller"""
        self.facade_service = FacadeService.get_instance()
    
    def get_agent_metadata(self, user_id: str, session) -> Dict[str, Any]:
        """
        Get metadata for all available agents.
        
        Args:
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Agent metadata list
        """
        try:
            # Get agent facade from service - agent metadata is project-independent
            facade = self.facade_service.get_agent_facade(
                project_id=None,  # Agent metadata doesn't require project context
                user_id=user_id
            )
            
            # Get all agent metadata
            result = facade.list_all_agents()
            
            if not result.get("success"):
                # Fallback to static metadata if needed
                return {
                    "success": True,
                    "agents": self._get_static_metadata(),
                    "total": len(self._get_static_metadata()),
                    "source": "static"
                }
            
            agents = result.get("agents", [])
            logger.info(f"Retrieved {len(agents)} agent metadata entries")
            
            return {
                "success": True,
                "agents": agents,
                "total": len(agents),
                "source": "facade"
            }
            
        except Exception as e:
            logger.error(f"Error getting agent metadata: {e}")
            # Return static metadata as fallback
            static_agents = self._get_static_metadata()
            return {
                "success": True,
                "agents": static_agents,
                "total": len(static_agents),
                "source": "fallback",
                "error": str(e)
            }
    
    def get_agent_by_id(self, agent_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get metadata for a specific agent.
        
        Args:
            agent_id: Agent identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Single agent metadata
        """
        try:
            # Get agent facade from service - agent metadata is project-independent
            facade = self.facade_service.get_agent_facade(
                project_id=None,  # Agent metadata doesn't require project context
                user_id=user_id
            )
            
            # Get specific agent
            result = facade.get_agent(agent_id)
            
            if not result.get("success"):
                # Try static metadata fallback
                static_agent = self._find_static_agent(agent_id)
                if static_agent:
                    return {
                        "success": True,
                        "agent": static_agent,
                        "source": "static"
                    }
                
                return {
                    "success": False,
                    "error": f"Agent '{agent_id}' not found",
                    "agent": None
                }
            
            agent = result.get("agent")
            logger.info(f"Retrieved agent metadata for {agent_id}")
            
            return {
                "success": True,
                "agent": agent,
                "source": "facade"
            }
            
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            # Try static fallback
            static_agent = self._find_static_agent(agent_id)
            if static_agent:
                return {
                    "success": True,
                    "agent": static_agent,
                    "source": "fallback"
                }
            
            return {
                "success": False,
                "error": str(e),
                "agent": None
            }
    
    def get_agents_by_category(self, category: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get agents filtered by category.
        
        Args:
            category: Agent category to filter by
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Agents in the specified category
        """
        try:
            # Get agent facade from service - agent metadata is project-independent
            facade = self.facade_service.get_agent_facade(
                project_id=None,  # Agent metadata doesn't require project context
                user_id=user_id
            )
            
            # Get agents by category
            result = facade.list_agents_by_category(category)
            
            if not result.get("success"):
                # Fallback to static metadata filtering
                static_agents = [a for a in self._get_static_metadata() if a.get("category") == category]
                return {
                    "success": True,
                    "category": category,
                    "agents": static_agents,
                    "total": len(static_agents),
                    "source": "static"
                }
            
            agents = result.get("agents", [])
            logger.info(f"Retrieved {len(agents)} agents in category {category}")
            
            return {
                "success": True,
                "category": category,
                "agents": agents,
                "total": len(agents),
                "source": "facade"
            }
            
        except Exception as e:
            logger.error(f"Error getting agents by category {category}: {e}")
            # Fallback to static metadata
            static_agents = [a for a in self._get_static_metadata() if a.get("category") == category]
            return {
                "success": True,
                "category": category,
                "agents": static_agents,
                "total": len(static_agents),
                "source": "fallback"
            }
    
    def list_agent_categories(self, user_id: str, session) -> Dict[str, Any]:
        """
        List all available agent categories.
        
        Args:
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            List of agent categories
        """
        try:
            # Get agent facade from service - agent metadata is project-independent
            facade = self.facade_service.get_agent_facade(
                project_id=None,  # Agent metadata doesn't require project context
                user_id=user_id
            )
            
            # Get categories
            result = facade.list_agent_categories()
            
            if not result.get("success"):
                # Fallback to static categories
                categories = self._get_static_categories()
                return {
                    "success": True,
                    "categories": categories,
                    "total": len(categories),
                    "source": "static"
                }
            
            categories = result.get("categories", [])
            logger.info(f"Retrieved {len(categories)} agent categories")
            
            return {
                "success": True,
                "categories": categories,
                "total": len(categories),
                "source": "facade"
            }
            
        except Exception as e:
            logger.error(f"Error listing agent categories: {e}")
            # Fallback to static categories
            categories = self._get_static_categories()
            return {
                "success": True,
                "categories": categories,
                "total": len(categories),
                "source": "fallback"
            }
    
    def _get_static_metadata(self) -> List[Dict[str, Any]]:
        """Get static agent metadata for fallback"""
        return [
            {
                "id": "master-orchestrator-agent",
                "name": "Uber Orchestrator Agent",
                "call_name": "master-orchestrator-agent",
                "role": "Master Coordinator and Decision Maker",
                "description": "The highest-level orchestrator that coordinates all other agents",
                "category": "orchestration",
                "type": "orchestrator",
                "priority": "critical",
                "capabilities": [
                    "Multi-agent coordination",
                    "Strategic planning",
                    "Resource allocation",
                    "Workflow orchestration"
                ],
                "tools": ["All MCP tools"],
                "guidelines": "Use for high-level coordination and when multiple agents need to work together"
            },
            {
                "id": "coding-agent",
                "name": "Coding Agent",
                "call_name": "coding-agent",
                "role": "Software Development Specialist",
                "description": "Specialized in writing, refactoring, and implementing code",
                "category": "development",
                "type": "specialist",
                "priority": "high",
                "capabilities": [
                    "Code implementation",
                    "Refactoring",
                    "API development",
                    "Database design"
                ],
                "tools": ["Code editing tools", "File management"],
                "guidelines": "Use for all coding and implementation tasks"
            },
            {
                "id": "debugger-agent",
                "name": "Debugger Agent",
                "call_name": "debugger-agent",
                "role": "Bug Detection and Resolution Specialist",
                "description": "Expert in identifying, analyzing, and fixing bugs and errors",
                "category": "development",
                "type": "specialist",
                "priority": "high",
                "capabilities": [
                    "Error analysis",
                    "Stack trace interpretation",
                    "Performance debugging"
                ],
                "tools": ["Debugging tools", "Log analysis"],
                "guidelines": "Use when encountering errors, test failures, or unexpected behavior"
            },
            {
                "id": "test-orchestrator-agent",
                "name": "Test Orchestrator Agent",
                "call_name": "test-orchestrator-agent",
                "role": "Testing Strategy and Execution Coordinator",
                "description": "Manages comprehensive testing strategies and coordinates test execution",
                "category": "quality",
                "type": "orchestrator",
                "priority": "high",
                "capabilities": [
                    "Test strategy design",
                    "Test suite orchestration",
                    "Coverage analysis"
                ],
                "tools": ["Test frameworks", "Coverage tools"],
                "guidelines": "Use for designing and executing comprehensive test strategies"
            }
        ]
    
    def _find_static_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific agent in static metadata"""
        return next((a for a in self._get_static_metadata() if a["id"] == agent_id), None)
    
    def _get_static_categories(self) -> List[str]:
        """Get unique categories from static metadata"""
        categories = list(set(agent.get("category", "uncategorized") for agent in self._get_static_metadata()))
        return sorted(categories)