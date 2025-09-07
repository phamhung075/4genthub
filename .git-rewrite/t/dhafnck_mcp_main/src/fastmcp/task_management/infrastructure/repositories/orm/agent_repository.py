"""
Agent Repository Implementation using SQLAlchemy ORM

This module provides agent repository implementation using SQLAlchemy ORM,
supporting both SQLite and PostgreSQL databases.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import and_, desc

from ..base_orm_repository import BaseORMRepository
from ..base_user_scoped_repository import BaseUserScopedRepository
from ...database.models import Agent
from ....domain.repositories.agent_repository import AgentRepository
from ....domain.entities.agent import Agent as AgentEntity, AgentStatus, AgentCapability
from ....domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DatabaseException
)

logger = logging.getLogger(__name__)


class ORMAgentRepository(BaseORMRepository[Agent], BaseUserScopedRepository, AgentRepository):
    """
    Agent repository implementation using SQLAlchemy ORM.
    
    This repository handles all agent-related database operations
    using SQLAlchemy, supporting both SQLite and PostgreSQL.
    """
    
    def __init__(self, session=None, project_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize ORM agent repository with user isolation.
        
        Args:
            session: Database session
            project_id: Project ID for context
            user_id: User ID for data isolation
        """
        # Initialize BaseORMRepository
        BaseORMRepository.__init__(self, Agent)
        
        # Ensure user_id is a valid UUID if provided
        if user_id is not None and not self._is_valid_uuid(user_id):
            # Generate a deterministic UUID for non-UUID user_id values
            user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
            logger.info(f"Converted non-UUID user_id to UUID: {user_id}")
        
        # Initialize BaseUserScopedRepository with user isolation
        from ...database.database_config import get_session
        actual_session = session or get_session()
        BaseUserScopedRepository.__init__(self, actual_session, user_id)
        self.project_id = project_id
    
    def _is_valid_uuid(self, value: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def _normalize_assigned_trees_to_set(self, assigned_trees_raw) -> set:
        """
        Normalize assigned_trees data to a set of strings.
        Handles single UUID strings, UUID objects, lists, and mixed types.
        """
        logger.debug(f"[NORMALIZE] Input type: {type(assigned_trees_raw)}, value: {assigned_trees_raw}")
        
        if isinstance(assigned_trees_raw, str):
            # Single UUID stored as string
            logger.debug(f"[NORMALIZE] Detected string type, returning set with single string")
            return {assigned_trees_raw}
        elif isinstance(assigned_trees_raw, uuid.UUID):
            # Single UUID object (convert to string)
            logger.debug(f"[NORMALIZE] Detected UUID object, converting to string")
            return {str(assigned_trees_raw)}
        elif hasattr(assigned_trees_raw, '__iter__') and not isinstance(assigned_trees_raw, str):
            # List or other iterable (but not string or UUID)
            try:
                # Handle mixed types in the iterable (strings and UUID objects)
                result = set()
                for item in assigned_trees_raw:
                    if isinstance(item, uuid.UUID):
                        result.add(str(item))
                    elif isinstance(item, str):
                        result.add(item)
                    else:
                        # Convert other types to string
                        result.add(str(item))
                return result
            except Exception as e:
                logger.error(f"Error converting {assigned_trees_raw} to set: {e}")
                return set()
        else:
            # Fallback to empty set
            return set()
    
    def _normalize_assigned_trees_to_list(self, assigned_trees_raw) -> list:
        """
        Normalize assigned_trees data to a list of strings.
        Handles single UUID strings, UUID objects, lists, and mixed types.
        """
        if isinstance(assigned_trees_raw, str):
            # Single UUID stored as string
            return [assigned_trees_raw]
        elif isinstance(assigned_trees_raw, uuid.UUID):
            # Single UUID object (convert to string)
            return [str(assigned_trees_raw)]
        elif hasattr(assigned_trees_raw, '__iter__') and not isinstance(assigned_trees_raw, str):
            # List or other iterable (but not string or UUID)
            try:
                # Handle mixed types in the iterable (strings and UUID objects)
                result = []
                for item in assigned_trees_raw:
                    if isinstance(item, uuid.UUID):
                        result.append(str(item))
                    elif isinstance(item, str):
                        result.append(item)
                    else:
                        # Convert other types to string
                        result.append(str(item))
                return result
            except Exception as e:
                logger.error(f"Error converting {assigned_trees_raw} to list: {e}")
                return []
        else:
            # Fallback to empty list
            return []
    
    def _model_to_entity(self, agent: Agent) -> AgentEntity:
        """Convert SQLAlchemy model to domain entity"""
        try:
            # Parse capabilities from JSON list of strings to AgentCapability enum
            capabilities = set()
            if agent.capabilities:
                for cap_str in agent.capabilities:
                    try:
                        capabilities.add(AgentCapability(cap_str))
                    except ValueError:
                        # Skip invalid capabilities
                        logger.warning(f"Invalid capability '{cap_str}' for agent {agent.id}")
            
            # Parse status
            status = AgentStatus.AVAILABLE
            if agent.status:
                try:
                    status = AgentStatus(agent.status)
                except ValueError:
                    logger.warning(f"Invalid status '{agent.status}' for agent {agent.id}")
            
            return AgentEntity(
                id=agent.id,
                name=agent.name,
                description=agent.description or "",
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                capabilities=capabilities,
                specializations=[],  # Agent model doesn't have specializations
                preferred_languages=[],  # Agent model doesn't have preferred languages
                preferred_frameworks=[],  # Agent model doesn't have preferred frameworks
                status=status,
                max_concurrent_tasks=1,  # Agent model doesn't have this field
                current_workload=0,  # Agent model doesn't have this field
                work_hours=None,  # Agent model doesn't have this field
                timezone="UTC",  # Agent model doesn't have this field
                priority_preference="medium",  # Agent model doesn't have this field
                completed_tasks=0,  # Agent model doesn't have this field
                average_task_duration=None,  # Agent model doesn't have this field
                success_rate=100.0,  # Agent model doesn't have this field
                assigned_projects=set(),  # Calculated from relationships
                assigned_trees=set(),  # Calculated from relationships
                active_tasks=set()  # Calculated from relationships
            )
        except Exception as e:
            logger.error(f"Error converting agent model to entity: {e}")
            raise DatabaseException(
                message=f"Failed to convert agent model to entity: {str(e)}",
                operation="model_to_entity",
                table="agents"
            )
    
    def _entity_to_model_dict(self, agent: AgentEntity) -> Dict[str, Any]:
        """Convert domain entity to model dictionary"""
        return {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "capabilities": [cap.value for cap in agent.capabilities],
            "status": agent.status.value,
            "availability_score": 1.0 if agent.is_available() else 0.0,
            "last_active_at": datetime.now() if agent.status == AgentStatus.AVAILABLE else None,
            "model_metadata": {
                "specializations": agent.specializations,
                "preferred_languages": agent.preferred_languages,
                "preferred_frameworks": agent.preferred_frameworks,
                "max_concurrent_tasks": agent.max_concurrent_tasks,
                "current_workload": agent.current_workload,
                "work_hours": agent.work_hours,
                "timezone": agent.timezone,
                "priority_preference": agent.priority_preference,
                "completed_tasks": agent.completed_tasks,
                "average_task_duration": agent.average_task_duration,
                "success_rate": agent.success_rate,
                "assigned_projects": list(agent.assigned_projects),
                "assigned_trees": list(agent.assigned_trees),
                "active_tasks": list(agent.active_tasks)
            }
        }
    
    def register_agent(self, project_id: str, agent_id: str, name: str, call_agent: str = None) -> Dict[str, Any]:
        """Register a new agent to a project"""
        try:
            # Pre-registration validation: Check if agent already exists
            if self.exists(id=agent_id):
                # Try to get the existing agent details for better user feedback
                existing_agent = self.get_by_id(agent_id)
                if existing_agent:
                    raise ValidationException(
                        message=(
                            f"Agent with ID '{agent_id}' already exists. "
                            f"Existing agent name: '{existing_agent.name}'. "
                            f"Use 'manage_agent' with action='get' to view details, "
                            f"or action='update' to modify the existing agent."
                        ),
                        field="id",
                        value=agent_id
                    )
                else:
                    raise ValidationException(
                        message=f"Agent with ID '{agent_id}' already exists. Use the existing agent or choose a different ID.",
                        field="id",
                        value=agent_id
                    )
            
            # Also check if an agent with the same name exists (for better UX)
            existing_by_name = self.find_by_name(name)
            if existing_by_name and existing_by_name.id != agent_id:
                raise ValidationException(
                    message=(
                        f"An agent with name '{name}' already exists (ID: {existing_by_name.id}). "
                        f"Consider using the existing agent or choosing a different name."
                    ),
                    field="name",
                    value=name
                )
            
            # Create agent entity
            agent_entity = AgentEntity(
                id=agent_id,
                name=name,
                description=f"Agent for project {project_id}",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Convert to model dict
            model_dict = self._entity_to_model_dict(agent_entity)
            
            # Add call_agent to model_metadata if provided
            if call_agent:
                model_dict["model_metadata"]["call_agent"] = call_agent
            
            # Add user_id for data isolation
            model_dict = self.set_user_id(model_dict)
            
            # Create agent in database with better error handling
            try:
                agent = self.create(**model_dict)
            except Exception as create_error:
                # Check for database-level duplicate key constraint violation
                error_str = str(create_error).lower()
                if "unique constraint" in error_str or "duplicate key" in error_str or "already exists" in error_str:
                    # This could happen in race conditions even with our checks
                    logger.warning(f"Duplicate key error during agent creation (race condition): {create_error}")
                    raise ValidationException(
                        message=(
                            f"Agent '{name}' (ID: {agent_id}) could not be created due to a duplicate key. "
                            f"Another process may have created it simultaneously. Please try again or use the existing agent."
                        ),
                        field="id",
                        value=agent_id
                    )
                else:
                    # Re-raise other database errors
                    raise create_error
            
            # Convert back to dict for response
            agent_data = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities or [],
                "status": agent.status,
                "availability_score": agent.availability_score,
                "model_metadata": agent.model_metadata or {},
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat()
            }
            
            logger.info(f"Successfully registered agent '{name}' (ID: {agent_id}) for project {project_id}")
            return agent_data
            
        except ValidationException:
            # Re-raise validation exceptions with their helpful messages
            raise
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            # Provide more helpful error message based on error type
            if "foreign key" in str(e).lower():
                raise DatabaseException(
                    message=f"Failed to register agent: Project '{project_id}' does not exist",
                    operation="register_agent",
                    table="agents"
                )
            else:
                raise DatabaseException(
                    message=f"Failed to register agent: {str(e)}",
                    operation="register_agent",
                    table="agents"
                )
    
    def unregister_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Unregister an agent from a project"""
        try:
            # Get agent data before deletion
            agent = self.get_by_id(agent_id)
            if not agent:
                raise ResourceNotFoundException(
                    message=f"Agent {agent_id} not found",
                    resource_type="agent",
                    resource_id=agent_id
                )
            
            # Store agent data for response
            agent_data = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities or [],
                "status": agent.status,
                "model_metadata": agent.model_metadata or {}
            }
            
            # Delete the agent
            deleted = self.delete(agent_id)
            if not deleted:
                raise DatabaseException(
                    message=f"Failed to delete agent {agent_id}",
                    operation="unregister_agent",
                    table="agents"
                )
            
            logger.info(f"Unregistered agent {agent_id} from project {project_id}")
            return {
                "agent_data": agent_data,
                "removed_assignments": []  # Would need to implement assignment tracking
            }
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            raise DatabaseException(
                message=f"Failed to unregister agent: {str(e)}",
                operation="unregister_agent",
                table="agents"
            )
    
    def assign_agent_to_tree(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Assign an agent to a task tree, auto-registering the agent if it doesn't exist"""
        logger.debug(f"[AGENT_REPO] assign_agent_to_tree called with project_id={project_id}, agent_id={agent_id}, git_branch_id={git_branch_id}")
        logger.debug(f"[AGENT_REPO] Type of git_branch_id: {type(git_branch_id)}, value: {git_branch_id}")
        
        try:
            # Parse agent_id - it might be in format "uuid:name" for auto-registration
            actual_agent_id = agent_id
            agent_name = None
            
            if ':' in agent_id:
                # Special format from controller: "uuid:name"
                parts = agent_id.split(':', 1)
                actual_agent_id = parts[0]
                agent_name = parts[1]
                logger.info(f"Parsed agent_id format - UUID: {actual_agent_id}, Name: {agent_name}")
            
            # Get agent using the actual UUID
            agent = self.get_by_id(actual_agent_id)
            auto_registered = False
            
            if not agent:
                # Auto-register the agent with default settings
                logger.info(f"Auto-registering agent {actual_agent_id} in project {project_id}")
                try:
                    # Check if agent already exists by ID before attempting to create
                    # This handles race conditions and duplicate key constraint violations
                    if self.exists(id=actual_agent_id):
                        logger.info(f"Agent {actual_agent_id} already exists, fetching it")
                        agent = self.get_by_id(actual_agent_id)
                        if agent:
                            auto_registered = False
                            logger.info(f"Found existing agent {actual_agent_id} after exists check")
                        else:
                            # This shouldn't happen, but handle it gracefully
                            raise ResourceNotFoundException(
                                message=f"Agent {actual_agent_id} exists but couldn't be retrieved",
                                resource_type="agent",
                                resource_id=actual_agent_id
                            )
                    else:
                        # Determine agent name based on agent_id format
                        if agent_name:
                            # Name was provided in special format
                            pass
                        else:
                            # Fall back to parsing logic
                            import re
                            uuid_pattern = re.compile(
                                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', 
                                re.IGNORECASE
                            )
                            
                            if uuid_pattern.match(actual_agent_id):
                                # It's a UUID, use a default name
                                agent_name = f"agent_{actual_agent_id[:8]}"
                            else:
                                # It's a name (shouldn't happen with new logic, but keep for compatibility)
                                agent_name = actual_agent_id.lstrip('@')
                        
                        # Create agent entity
                        agent_entity = AgentEntity(
                            id=actual_agent_id,
                            name=agent_name,
                            description=f"Auto-registered agent {agent_name} for project {project_id}",
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        # Convert to model dict
                        model_dict = self._entity_to_model_dict(agent_entity)
                        
                        # Add call_agent to model_metadata - use the name with @ prefix
                        model_dict["model_metadata"]["call_agent"] = f"@{agent_name}"
                        
                        # Add user_id for data isolation
                        model_dict = self.set_user_id(model_dict)
                        
                        # Create agent in database with duplicate key handling
                        try:
                            agent = self.create(**model_dict)
                            auto_registered = True
                            logger.info(f"Successfully auto-registered agent {actual_agent_id} (name: {agent_name}) in project {project_id}")
                        except Exception as create_error:
                            # Handle duplicate key constraint violation (race condition)
                            if "UNIQUE constraint" in str(create_error) or "duplicate key" in str(create_error).lower():
                                logger.info(f"Agent {actual_agent_id} was created by another process, fetching it")
                                agent = self.get_by_id(actual_agent_id)
                                if agent:
                                    auto_registered = False
                                    logger.info(f"Found existing agent {actual_agent_id} after race condition")
                                else:
                                    raise ResourceNotFoundException(
                                        message=f"Agent {actual_agent_id} creation failed but agent not found",
                                        resource_type="agent",
                                        resource_id=actual_agent_id
                                    )
                            else:
                                # Re-raise other errors
                                raise create_error
                    
                except Exception as reg_error:
                    logger.error(f"Failed to auto-register agent {actual_agent_id}: {reg_error}")
                    raise ResourceNotFoundException(
                        message=f"Agent {actual_agent_id} not found and auto-registration failed: {str(reg_error)}",
                        resource_type="agent",
                        resource_id=actual_agent_id
                    )
            
            # Update agent model_metadata to include assignment
            logger.debug(f"[AGENT_REPO] Checking if agent already assigned...")
            model_metadata = agent.model_metadata or {}
            logger.debug(f"[AGENT_REPO] model_metadata type: {type(model_metadata)}, value: {model_metadata}")
            
            assigned_trees_raw = model_metadata.get("assigned_trees", [])
            logger.debug(f"[AGENT_REPO] assigned_trees_raw type: {type(assigned_trees_raw)}, value: {assigned_trees_raw}")
            
            # Handle case where assigned_trees might be a single UUID instead of a list
            logger.debug(f"[AGENT_REPO] Calling _normalize_assigned_trees_to_set...")
            assigned_trees = self._normalize_assigned_trees_to_set(assigned_trees_raw)
            logger.debug(f"[AGENT_REPO] assigned_trees after normalization: type={type(assigned_trees)}, value={assigned_trees}")
            
            logger.debug(f"[AGENT_REPO] Checking if git_branch_id {git_branch_id} is in assigned_trees...")
            if git_branch_id in assigned_trees:
                return {
                    "success": True,
                    "message": f"Agent {actual_agent_id} already assigned to tree {git_branch_id}",
                    "auto_registered": auto_registered
                }
            
            assigned_trees.add(git_branch_id)
            model_metadata["assigned_trees"] = list(assigned_trees)
            
            # Update agent
            self.update(actual_agent_id, 
                       model_metadata=model_metadata,
                       updated_at=datetime.now())
            
            logger.info(f"Assigned agent {actual_agent_id} to tree {git_branch_id} in project {project_id}")
            return {
                "success": True,
                "message": f"Agent {actual_agent_id} assigned to tree {git_branch_id}",
                "auto_registered": auto_registered
            }
            
        except ResourceNotFoundException:
            # Re-raise resource not found errors (from auto-registration failure)
            raise
        except Exception as e:
            logger.error(f"Error assigning agent {actual_agent_id if 'actual_agent_id' in locals() else agent_id} to tree {git_branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to assign agent to tree: {str(e)}",
                operation="assign_agent_to_tree",
                table="agents"
            )
    
    def unassign_agent_from_tree(self, project_id: str, agent_id: str, git_branch_id: str = None) -> Dict[str, Any]:
        """Unassign an agent from task tree(s)"""
        try:
            # Get agent
            agent = self.get_by_id(agent_id)
            if not agent:
                raise ResourceNotFoundException(
                    message=f"Agent {agent_id} not found",
                    resource_type="agent",
                    resource_id=agent_id
                )
            
            # Update agent metadata to remove assignment
            model_metadata = agent.model_metadata or {}
            assigned_trees_raw = model_metadata.get("assigned_trees", [])
            
            # Handle case where assigned_trees might be a single UUID instead of a list
            assigned_trees = self._normalize_assigned_trees_to_set(assigned_trees_raw)
            
            if git_branch_id:
                # Remove specific assignment
                if git_branch_id in assigned_trees:
                    assigned_trees.remove(git_branch_id)
                    removed_assignments = [git_branch_id]
                else:
                    removed_assignments = []
            else:
                # Remove all assignments
                removed_assignments = list(assigned_trees)
                assigned_trees.clear()
            
            model_metadata["assigned_trees"] = list(assigned_trees)
            
            # Update agent
            self.update(agent_id, 
                       model_metadata=model_metadata,
                       updated_at=datetime.now())
            
            logger.info(f"Unassigned agent {agent_id} from {len(removed_assignments)} tree(s) in project {project_id}")
            return {
                "removed_assignments": removed_assignments,
                "remaining_assignments": list(assigned_trees)
            }
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error unassigning agent {agent_id}: {e}")
            raise DatabaseException(
                message=f"Failed to unassign agent from tree: {str(e)}",
                operation="unassign_agent_from_tree",
                table="agents"
            )
    
    def get_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Get agent details"""
        try:
            agent = self.get_by_id(agent_id)
            if not agent:
                raise ResourceNotFoundException(
                    message=f"Agent {agent_id} not found",
                    resource_type="agent",
                    resource_id=agent_id
                )
            
            # Get assignments from model_metadata
            model_metadata = agent.model_metadata or {}
            assigned_trees_raw = model_metadata.get("assigned_trees", [])
            
            # Handle case where assigned_trees might be a single UUID instead of a list
            assignments = self._normalize_assigned_trees_to_list(assigned_trees_raw)
            
            agent_data = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities or [],
                "status": agent.status,
                "availability_score": agent.availability_score,
                "model_metadata": model_metadata,
                "assignments": assignments,
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat()
            }
            
            return agent_data
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            raise DatabaseException(
                message=f"Failed to get agent: {str(e)}",
                operation="get_agent",
                table="agents"
            )
    
    def list_agents(self, project_id: str) -> Dict[str, Any]:
        """List all agents in a project"""
        try:
            # Get all agents (project filtering would need to be implemented)
            agents = self.get_all()
            
            agent_list = []
            for agent in agents:
                model_metadata = agent.model_metadata or {}
                assigned_trees_raw = model_metadata.get("assigned_trees", [])
                
                # Handle case where assigned_trees might be a single UUID instead of a list
                assignments = self._normalize_assigned_trees_to_list(assigned_trees_raw)
                
                agent_data = {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "capabilities": agent.capabilities or [],
                    "status": agent.status,
                    "availability_score": agent.availability_score,
                    "model_metadata": model_metadata,
                    "assignments": assignments,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": agent.updated_at.isoformat()
                }
                agent_list.append(agent_data)
            
            return {
                "agents": agent_list,
                "total_agents": len(agent_list)
            }
            
        except Exception as e:
            logger.error(f"Error listing agents for project {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to list agents: {str(e)}",
                operation="list_agents",
                table="agents"
            )
    
    def update_agent(self, project_id: str, agent_id: str, name: str = None, call_agent: str = None) -> Dict[str, Any]:
        """Update agent details"""
        try:
            # Get agent
            agent = self.get_by_id(agent_id)
            if not agent:
                raise ResourceNotFoundException(
                    message=f"Agent {agent_id} not found",
                    resource_type="agent",
                    resource_id=agent_id
                )
            
            # Prepare updates
            updates = {"updated_at": datetime.now()}
            
            if name is not None:
                updates["name"] = name
            
            if call_agent is not None:
                model_metadata = agent.model_metadata or {}
                model_metadata["call_agent"] = call_agent
                updates["model_metadata"] = model_metadata
            
            # Update agent
            if len(updates) > 1:  # More than just updated_at
                updated_agent = self.update(agent_id, **updates)
            else:
                updated_agent = agent
            
            # Get assignments from model_metadata
            model_metadata = updated_agent.model_metadata or {}
            assigned_trees_raw = model_metadata.get("assigned_trees", [])
            
            # Handle case where assigned_trees might be a single UUID instead of a list
            if isinstance(assigned_trees_raw, str):
                # Single UUID stored as string
                assignments = [assigned_trees_raw]
            elif hasattr(assigned_trees_raw, '__iter__') and not isinstance(assigned_trees_raw, str):
                # List or other iterable (but not string)
                assignments = list(assigned_trees_raw)
            else:
                # Fallback to empty list
                assignments = []
            
            agent_data = {
                "id": updated_agent.id,
                "name": updated_agent.name,
                "description": updated_agent.description,
                "capabilities": updated_agent.capabilities or [],
                "status": updated_agent.status,
                "availability_score": updated_agent.availability_score,
                "model_metadata": model_metadata,
                "assignments": assignments,
                "created_at": updated_agent.created_at.isoformat(),
                "updated_at": updated_agent.updated_at.isoformat()
            }
            
            logger.info(f"Updated agent {agent_id} in project {project_id}")
            return agent_data
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            raise DatabaseException(
                message=f"Failed to update agent: {str(e)}",
                operation="update_agent",
                table="agents"
            )
    
    def rebalance_agents(self, project_id: str) -> Dict[str, Any]:
        """Rebalance agent assignments across task trees"""
        try:
            # Get all agents
            agents = self.get_all()
            
            if not agents:
                return {
                    "rebalance_result": {
                        "changes_made": False,
                        "message": "No agents found in project"
                    }
                }
            
            # Simple rebalancing logic (would need more sophisticated implementation)
            changes = []
            
            for agent in agents:
                model_metadata = agent.model_metadata or {}
                assigned_trees_raw = model_metadata.get("assigned_trees", [])
                
                # Handle case where assigned_trees might be a single UUID instead of a list
                assignments = self._normalize_assigned_trees_to_list(assigned_trees_raw)
                
                # For now, just log current assignments
                if assignments:
                    changes.append(f"Agent '{agent.name}' has {len(assignments)} assignments")
            
            logger.info(f"Rebalanced agents in project {project_id}")
            return {
                "rebalance_result": {
                    "changes_made": len(changes) > 0,
                    "changes": changes,
                    "message": f"Analyzed {len(agents)} agents"
                }
            }
            
        except Exception as e:
            logger.error(f"Error rebalancing agents in project {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to rebalance agents: {str(e)}",
                operation="rebalance_agents",
                table="agents"
            )
    
    def get_available_agents(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all available agents"""
        try:
            # Find agents with available status
            agents = self.find_by(status=AgentStatus.AVAILABLE.value)
            
            available_agents = []
            for agent in agents:
                model_metadata = agent.model_metadata or {}
                assigned_trees_raw = model_metadata.get("assigned_trees", [])
                
                # Handle case where assigned_trees might be a single UUID instead of a list
                assignments = self._normalize_assigned_trees_to_list(assigned_trees_raw)
                
                agent_data = {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "capabilities": agent.capabilities or [],
                    "status": agent.status,
                    "availability_score": agent.availability_score,
                    "assignments": assignments,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": agent.updated_at.isoformat()
                }
                available_agents.append(agent_data)
            
            return available_agents
            
        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            raise DatabaseException(
                message=f"Failed to get available agents: {str(e)}",
                operation="get_available_agents",
                table="agents"
            )
    
    def find_by_name(self, name: str) -> Optional[Agent]:
        """
        Find an agent by its name.
        
        Args:
            name: The agent name (with or without @ prefix)
            
        Returns:
            Agent model if found, None otherwise
        """
        try:
            # Strip @ prefix if present
            clean_name = name.lstrip('@')
            
            # Query for agent by name (with user isolation from BaseUserScopedRepository)
            agent = self.find_one_by(name=clean_name)
            if agent:
                logger.info(f"Found agent by name: {clean_name} -> ID: {agent.id}")
                return agent
            
            # Also try with @ prefix in case it was stored that way
            agent = self.find_one_by(name=f"@{clean_name}")
            if agent:
                logger.info(f"Found agent by name with @: @{clean_name} -> ID: {agent.id}")
                return agent
                
            logger.debug(f"No agent found with name: {name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding agent by name '{name}': {e}")
            return None
    
    def search_agents(self, project_id: str, query: str) -> List[Dict[str, Any]]:
        """Search agents by name or capabilities"""
        try:
            # This would need more sophisticated search implementation
            # For now, do a simple name search
            with self.get_db_session() as session:
                search_pattern = f"%{query}%"
                agents = session.query(Agent).filter(
                    Agent.name.ilike(search_pattern)
                ).all()
            
            search_results = []
            for agent in agents:
                model_metadata = agent.model_metadata or {}
                assigned_trees_raw = model_metadata.get("assigned_trees", [])
                
                # Handle case where assigned_trees might be a single UUID instead of a list
                assignments = self._normalize_assigned_trees_to_list(assigned_trees_raw)
                
                agent_data = {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "capabilities": agent.capabilities or [],
                    "status": agent.status,
                    "availability_score": agent.availability_score,
                    "assignments": assignments,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": agent.updated_at.isoformat()
                }
                search_results.append(agent_data)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching agents: {e}")
            raise DatabaseException(
                message=f"Failed to search agents: {str(e)}",
                operation="search_agents",
                table="agents"
            )