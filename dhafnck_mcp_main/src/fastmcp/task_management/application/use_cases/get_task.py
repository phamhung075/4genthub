"""Get Task Use Case"""

import logging
import asyncio
from typing import Optional, Union, Any
from datetime import datetime

from ...application.dtos.task import TaskResponse
from ...application.dtos.context import GetContextRequest

from ...domain import TaskRepository, TaskId
from ...domain.exceptions.task_exceptions import TaskNotFoundError
from ...domain.events import TaskRetrieved
from ...domain.interfaces.utility_service import IAgentDocGenerator
from ...infrastructure.services.agent_doc_generator import generate_docs_for_assignees

logger = logging.getLogger(__name__)


class GetTaskUseCase:
    """Use case for retrieving a task by ID with optional context data"""
    
    def __init__(self, task_repository: TaskRepository, context_service: Optional[Any] = None):
        """
        Initialize the GetTaskUseCase with required dependencies.
        
        Args:
            task_repository: Repository for task data access
            context_service: Optional context service for fetching context data
        """
        self._task_repository = task_repository
        self._context_service = context_service
    
    async def execute(self, task_id: str, generate_rules: bool = True, force_full_generation: bool = False,
                     include_context: bool = False) -> Optional[TaskResponse]:
        """
        Execute the get task use case following clean relationship chain.
        
        Args:
            task_id: The ID of the task to retrieve (contains all necessary context via relationships)
            generate_rules: Whether to generate agent rules
            force_full_generation: Whether to force full rule generation
            include_context: Whether to include full context data
            
        Returns:
            TaskResponse with optional context data or None if task not found
            
        Raises:
            TaskNotFoundError: If the task is not found
        """
        try:
            # Get the task from repository
            domain_task_id = TaskId(task_id)
            task = self._task_repository.find_by_id(domain_task_id)
            
            if not task:
                raise TaskNotFoundError(f"Task with ID {task_id} not found")
            
            # Generate agent documentation if requested
            if generate_rules:
                generate_docs_for_assignees(task.assignees, clear_all=force_full_generation)
            
            # Fetch context data if requested
            context_data = None
            
            if include_context:
                try:
                    # Try to get context using task_id
                    if self._context_service:
                        logger.debug(f"Attempting to fetch context for task {task_id} using context service: {type(self._context_service)}")
                        # Check if it's a UnifiedContextFacade (sync) or old-style async service
                        if hasattr(self._context_service, 'get_context') and not asyncio.iscoroutinefunction(self._context_service.get_context):
                            # UnifiedContextFacade - sync method
                            logger.debug(f"Using UnifiedContextFacade sync method for task {task_id}")
                            context_response = self._context_service.get_context(
                                level="task",
                                context_id=task_id,
                                include_inherited=True
                            )
                            logger.debug(f"Context response received: {context_response}")
                        else:
                            # Old-style async service
                            logger.debug(f"Using old-style async service for task {task_id}")
                            get_context_request = GetContextRequest(task_id=task_id)
                            context_response = await self._context_service.get_context(get_context_request)
                            logger.debug(f"Async context response received: {context_response}")
                        
                        if isinstance(context_response, dict):
                            # UnifiedContextFacade returns dict
                            logger.debug(f"Processing dict response for task {task_id}: keys={list(context_response.keys())}")
                            if context_response.get('success') and context_response.get('context'):
                                # Context data is in 'context' field for UnifiedContextService
                                context_data = context_response['context']
                                logger.debug(f"Context data fetched from context field for task {task_id}")
                            elif context_response.get('success') and context_response.get('data'):
                                # Check if context data is in 'data' field (legacy)
                                data_field = context_response['data']
                                if isinstance(data_field, dict) and 'context_data' in data_field:
                                    context_data = data_field['context_data']
                                    logger.debug(f"Context data fetched from data.context_data for task {task_id}")
                                else:
                                    context_data = data_field
                                    logger.debug(f"Context data fetched from data field for task {task_id}")
                            else:
                                logger.warning(f"No context data found for task {task_id}. Response: {context_response}")
                        else:
                            # Old-style response object
                            if context_response.success and context_response.context:
                                # Convert context to dict if it has to_dict method
                                if hasattr(context_response.context, 'to_dict'):
                                    context_data = context_response.context.to_dict()
                                else:
                                    context_data = context_response.context
                                logger.debug(f"Context data fetched for task {task_id}")
                            elif context_response.success and context_response.data:
                                # Fallback to data field if context field is not present
                                context_data = context_response.data
                                logger.debug(f"Context data fetched for task {task_id} from data field")
                            else:
                                logger.debug(f"No context data found for task {task_id}")
                    else:
                        logger.warning(f"No context service available for task {task_id}")
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch context data for task {task_id}: {e}")
                    import traceback
                    logger.warning(f"Full traceback: {traceback.format_exc()}")
            
            # Publish domain event
            _event = TaskRetrieved(
                task_id=task.id,
                task_data=task.to_dict() if hasattr(task, 'to_dict') else {},
                retrieved_at=datetime.now()
            )
            # Note: Event publishing would be handled by an event dispatcher in a full implementation
            
            # Convert domain task to response DTO with context data
            return TaskResponse.from_domain(task, context_data=context_data)
            
        except TaskNotFoundError:
            logger.warning(f"Task not found: {task_id}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving task {task_id}: {e}")
            raise