"""
Agent Operation Factory

Factory class that coordinates agent operations by routing them to appropriate handlers.
"""

import logging
from typing import Dict, Any, Optional
from .....application.facades.agent_application_facade import AgentApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes
from ..handlers.crud_handler import AgentCRUDHandler
from ..handlers.assignment_handler import AgentAssignmentHandler
from ..handlers.rebalance_handler import AgentRebalanceHandler

logger = logging.getLogger(__name__)


class AgentOperationFactory:
    """Factory for coordinating agent operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        
        # Initialize handlers
        self._crud_handler = AgentCRUDHandler(response_formatter)
        self._assignment_handler = AgentAssignmentHandler(response_formatter)
        self._rebalance_handler = AgentRebalanceHandler(response_formatter)
        
        logger.info("AgentOperationFactory initialized with modular handlers")
    
    def handle_operation(self, operation: str, facade: AgentApplicationFacade, 
                        **kwargs) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        
        try:
            # CRUD Operations
            if operation in ["register", "get", "list", "update", "unregister"]:
                return self._handle_crud_operation(operation, facade, **kwargs)
            
            # Assignment Operations
            elif operation in ["assign", "unassign"]:
                return self._handle_assignment_operation(operation, facade, **kwargs)
            
            # Rebalancing Operations
            elif operation == "rebalance":
                return self._handle_rebalance_operation(operation, facade, **kwargs)
            
            else:
                return self._response_formatter.create_error_response(
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    error_code=ErrorCodes.INVALID_OPERATION,
                    metadata={"valid_operations": [
                        "register", "assign", "get", "list", "update",
                        "unassign", "unregister", "rebalance"
                    ]}
                )
                
        except Exception as e:
            logger.error(f"Error in AgentOperationFactory.handle_operation: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"operation": operation}
            )
    
    def _handle_crud_operation(self, operation: str, facade: AgentApplicationFacade, 
                              **kwargs) -> Dict[str, Any]:
        """Handle CRUD operations."""
        
        project_id = kwargs.get('project_id')
        agent_id = kwargs.get('agent_id')
        name = kwargs.get('name')
        call_agent = kwargs.get('call_agent')
        
        if operation == "register":
            return self._crud_handler.register_agent(
                facade=facade,
                project_id=project_id,
                agent_id=agent_id,
                name=name,
                call_agent=call_agent
            )
        
        elif operation == "get":
            return self._crud_handler.get_agent(
                facade=facade,
                project_id=project_id,
                agent_id=agent_id
            )
        
        elif operation == "list":
            return self._crud_handler.list_agents(
                facade=facade,
                project_id=project_id
            )
        
        elif operation == "update":
            return self._crud_handler.update_agent(
                facade=facade,
                project_id=project_id,
                agent_id=agent_id,
                name=name,
                call_agent=call_agent
            )
        
        elif operation == "unregister":
            return self._crud_handler.unregister_agent(
                facade=facade,
                project_id=project_id,
                agent_id=agent_id
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported CRUD operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )
    
    def _handle_assignment_operation(self, operation: str, facade: AgentApplicationFacade, 
                                   **kwargs) -> Dict[str, Any]:
        """Handle assignment operations."""
        
        project_id = kwargs.get('project_id')
        agent_id = kwargs.get('agent_id')
        git_branch_id = kwargs.get('git_branch_id')
        
        if operation == "assign":
            return self._assignment_handler.assign_agent(
                facade=facade,
                project_id=project_id,
                agent_id=agent_id,
                git_branch_id=git_branch_id
            )
        
        elif operation == "unassign":
            return self._assignment_handler.unassign_agent(
                facade=facade,
                project_id=project_id,
                agent_id=agent_id,
                git_branch_id=git_branch_id
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported assignment operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )
    
    def _handle_rebalance_operation(self, operation: str, facade: AgentApplicationFacade, 
                                  **kwargs) -> Dict[str, Any]:
        """Handle rebalance operations."""
        
        project_id = kwargs.get('project_id')
        
        if operation == "rebalance":
            return self._rebalance_handler.rebalance_agents(
                facade=facade,
                project_id=project_id
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported rebalance operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )