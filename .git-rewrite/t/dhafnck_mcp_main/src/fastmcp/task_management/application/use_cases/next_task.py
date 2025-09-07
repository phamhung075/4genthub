"""Do Next Use Case - Find the next task or subtask to work on"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import asyncio

from ...domain import TaskRepository
from ...infrastructure.services.agent_doc_generator import generate_agent_docs, generate_docs_for_assignees
from ...application.services.unified_context_service import UnifiedContextService
from ...domain.value_objects.task_status import TaskStatus
from ...domain.value_objects.priority import Priority
from ...application.dtos.context import GetContextRequest

logger = logging.getLogger(__name__)

@dataclass
class NextTaskResponse:
    """Response containing the next item to work on"""
    has_next: bool
    next_item: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    context_info: Optional[Dict[str, Any]] = None
    message: str = ""
    
    def __getitem__(self, key):
        """Support dictionary-like access for backward compatibility"""
        if key == "success":
            return True  # Always successful if we got a response
        elif key == "has_next":
            return self.has_next
        elif key == "next_item":
            return self.next_item
        elif key == "context":
            return self.context
        elif key == "context_info":
            return self.context_info
        elif key == "message":
            return self.message
        else:
            raise KeyError(f"Key '{key}' not found in NextTaskResponse")
    
    def get(self, key, default=None):
        """Support dictionary-like get method"""
        try:
            return self[key]
        except KeyError:
            return default


class NextTaskUseCase:
    """Use case for finding the next task or subtask to work on"""
    
    def __init__(self, task_repository: TaskRepository, context_service: Optional[Any] = None, context_factory: Optional[Any] = None):
        self._task_repository = task_repository
        self._context_service = context_service
        self._context_factory = context_factory
    
    def _get_context_factory(self):
        """Get context factory, creating one if needed"""
        if self._context_factory is not None:
            return self._context_factory
        
        # Import here to avoid circular import
        from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
        return UnifiedContextFacadeFactory()
    
    async def execute(self, assignee: Optional[str] = None, project_id: Optional[str] = None, 
                labels: Optional[List[str]] = None, git_branch_id: Optional[str] = None, 
                user_id: Optional[str] = None, include_context: bool = False) -> NextTaskResponse:
        """Find the next task or subtask to work on with optional filtering
        
        Args:
            assignee: Filter by assignee
            project_id: Filter by project ID
            labels: Filter by labels
            git_branch_id: Task tree identifier for context creation (defaults to 'main')
            user_id: User identifier for context creation (defaults to 'default_id')
            include_context: Whether to include full context data in task responses
        """
        # Set defaults for context operations
        if git_branch_id is None:
            git_branch_id = getattr(self._task_repository, 'git_branch_id', 'main')
        if user_id is None:
            user_id = getattr(self._task_repository, 'user_id', 'default_id')
        if project_id is None:
            project_id = getattr(self._task_repository, 'project_id', '')
            
        all_tasks = self._task_repository.find_all()
        
        if not all_tasks:
            return NextTaskResponse(
                has_next=False,
                message="No tasks found. Create a task to get started!"
            )
        
        # Apply filters
        filtered_tasks = self._apply_filters(all_tasks, assignee, project_id, labels)
        
        if not filtered_tasks:
            return NextTaskResponse(
                has_next=False,
                message="No tasks match the specified filters."
            )
        
        # Validate task-context status alignment and detect mismatches
        status_mismatches = self._validate_task_context_alignment(filtered_tasks)
        if status_mismatches:
            return NextTaskResponse(
                has_next=False,
                context={
                    "error_type": "status_mismatch",
                    "mismatches": status_mismatches,
                    "fix_required": True
                },
                message=f"❌ CRITICAL: Found {len(status_mismatches)} task(s) with mismatched task/context status. Fix required before proceeding."
            )
        
        # Filter actionable tasks (todo or in_progress, not done/cancelled/blocked/review/testing)
        actionable_statuses = {"todo", "in_progress"}
        active_tasks = [
            task for task in filtered_tasks 
            if task.status and hasattr(task.status, 'value') and task.status.value in actionable_statuses
        ]
        
        if not active_tasks:
            # Check if all tasks are actually completed
            completed_tasks = [task for task in filtered_tasks if task.status and hasattr(task.status, 'is_done') and task.status.is_done()]
            if len(completed_tasks) == len(filtered_tasks):
                return NextTaskResponse(
                    has_next=False,
                    context=self._get_completion_context(filtered_tasks),
                    message="🎉 All tasks completed! Great job!"
                )
            else:
                # There are tasks but none are actionable (e.g., in review/testing)
                return NextTaskResponse(
                    has_next=False,
                    message="No actionable tasks found."
                )
        
        # Sort tasks by priority and status
        sorted_tasks = self._sort_tasks_by_priority(active_tasks)
        
        # Find the next actionable item
        for task in sorted_tasks:
            # Check if task can be started (dependencies satisfied)
            if not self._can_task_be_started(task, all_tasks):
                continue
            
            # Check if task has incomplete subtasks
            next_subtask = self._find_next_subtask(task)
            if next_subtask:
                # Generate agent documentation for all unique assignees (task and subtask)
                generate_docs_for_assignees(task.assignees, clear_all=False)
                if 'assignees' in next_subtask and next_subtask['assignees']:
                    generate_docs_for_assignees(next_subtask['assignees'], clear_all=False)
                return NextTaskResponse(
                    has_next=True,
                    next_item={
                        "type": "subtask",
                        "task": self._task_to_dict(task, include_context),
                        "subtask": next_subtask,
                        "context": self._get_task_context(task, all_tasks)
                    },
                    message=f"Next action: Work on subtask '{next_subtask['title']}' in task '{task.title}'"
                )
            else:
                # Task itself is the next item to work on
                # Generate agent documentation for all unique assignees
                generate_docs_for_assignees(task.assignees, clear_all=False)
                
                # Generate context_info only if conditions are met (JSON-based context)
                context_info = None
                if self._should_generate_context_info(task):
                    try:
                        # Create hierarchical context service with enhanced error handling
                        factory = self._get_context_factory()
                        context_service = factory.create_unified_service()
                        
                        # Try to get existing context first with timeout protection
                        context_result = None
                        try:
                            # context_service methods are synchronous, no need for await or timeout
                            context_result = context_service.resolve_context(
                                level="task",
                                context_id=task.id.value
                            )
                        except PermissionError as e:
                            logger.warning(f"Permission denied during context resolution for task {task.id.value}: {e}")
                        except FileNotFoundError:
                            logger.debug(f"No existing context file for task {task.id.value}")
                        except Exception as e:
                            logger.warning(f"Context resolution failed for task {task.id.value}: {e}")
                        
                        # If no context exists, try to create one (but don't fail if it doesn't work)
                        if not context_result or not context_result.get("success"):
                            try:
                                # context_service methods are synchronous, no need for await or timeout
                                context_service.create_context(
                                    level="task",
                                    context_id=task.id.value,
                                    data={
                                        "parent_project_id": project_id,
                                        "task_data": {
                                            "title": task.title,
                                            "description": task.description,
                                            "status": task.status.value if task.status and hasattr(task.status, 'value') else str(task.status) if task.status else "todo",
                                            "priority": task.priority.value if task.priority and hasattr(task.priority, 'value') else str(task.priority) if task.priority else "medium",
                                            "assignees": task.assignees or [],
                                            "labels": task.labels or []
                                        }
                                    }
                                )
                                context_result = context_service.resolve_context(
                                    level="task",
                                    context_id=task.id.value
                                )
                            except (PermissionError, OSError) as e:
                                logger.warning(f"Could not create context for task {task.id.value}: {e}")
                                # Continue without context - this is not a fatal error
                        
                        if context_result and context_result.get("success"):
                            context = context_result.get("context")
                            context_info = {
                                "context": context,
                                "created": True,
                                "message": f"Context resolved for task {task.id.value}"
                            }
                        else:
                            # Provide minimal context info even if context creation failed
                            context_info = {
                                "context": None,
                                "created": False,
                                "message": f"Context not available for task {task.id.value} (continuing without context)"
                            }
                    except Exception as e:
                        logger.warning(f"Context management failed for task {task.id}: {e}")
                        # Provide fallback context info
                        context_info = {
                            "context": None,
                            "created": False,
                            "message": f"Context error for task {task.id.value}: {str(e)}"
                        }
                
                return NextTaskResponse(
                    has_next=True,
                    next_item={
                        "type": "task",
                        "task": self._task_to_dict(task, include_context, user_id, project_id, git_branch_id),
                        "context": self._get_task_context(task, all_tasks)
                    },
                    context=task.context_id or str(task.id.value),  # Use task's context_id instead of null
                    context_info=context_info,
                    message=f"Next action: Work on task '{task.title}'"
                )
        
        # All remaining tasks are blocked by dependencies
        blocked_tasks = [task for task in active_tasks if not self._can_task_be_started(task, all_tasks)]
        if blocked_tasks:
            blocking_info = self._get_blocking_info(blocked_tasks, all_tasks)
            return NextTaskResponse(
                has_next=False,
                context=blocking_info,
                message="All remaining tasks are blocked by dependencies. Complete prerequisite tasks first."
            )
        
        return NextTaskResponse(
            has_next=False,
            message="No actionable tasks found."
        )
    
    def _apply_filters(self, tasks: List, assignee: Optional[str], project_id: Optional[str], 
                      labels: Optional[List[str]]) -> List:
        """Apply filters to task list with null safety"""
        # Null safety: ensure we have a valid tasks list
        if not tasks:
            return []
            
        filtered_tasks = list(tasks)  # Convert to list if needed
        
        if assignee and assignee is not None:
            # Null safety: check if assignees exists and is a proper list/iterable
            filtered_tasks = [task for task in filtered_tasks 
                            if hasattr(task, 'assignees') and task.assignees and isinstance(task.assignees, (list, tuple)) and assignee in task.assignees]
        
        if project_id:
            # Filter by project_id - note: task entity doesn't have project_id, so we skip this filter
            # The repository should already be scoped to the correct project via context
            pass
        
        if labels and labels is not None and isinstance(labels, (list, tuple)):
            # Null safety: check if labels exists and is a proper list/iterable
            # Also ensure labels parameter itself is a valid list/tuple to avoid "NoneType is not iterable" error
            filtered_tasks = [task for task in filtered_tasks 
                            if hasattr(task, 'labels') and task.labels is not None and isinstance(task.labels, (list, tuple)) and any(label in task.labels for label in labels)]
        
        return filtered_tasks
    
    def _sort_tasks_by_priority(self, tasks: List) -> List:
        """Sort tasks by priority (critical > urgent > high > medium > low) then by status (todo > in_progress)"""
        # Null safety: ensure we have a valid tasks list
        if not tasks:
            return []
            
        # Use inverted priority levels since sorted() sorts ascending but we want highest priority first
        # PriorityLevel: LOW=1, MEDIUM=2, HIGH=3, URGENT=4, CRITICAL=5
        # Inverted for descending sort: CRITICAL=0, URGENT=1, HIGH=2, MEDIUM=3, LOW=4
        priority_order = {
            Priority.critical().value: 0,
            Priority.urgent().value: 1, 
            Priority.high().value: 2,
            Priority.medium().value: 3,
            Priority.low().value: 4
        }
        status_order = {TaskStatus.todo().value: 0, TaskStatus.in_progress().value: 1}
        
        def safe_sort_key(task):
            """Safe sort key with null checks"""
            try:
                # Safe priority access
                priority_val = task.priority.value if task.priority and hasattr(task.priority, 'value') else str(task.priority) if task.priority else 'medium'
                priority_score = priority_order.get(priority_val, 5)
                
                # Safe status access
                status_val = task.status.value if task.status and hasattr(task.status, 'value') else str(task.status) if task.status else 'todo'
                status_score = status_order.get(status_val, 2)
                
                return (priority_score, status_score)
            except Exception as e:
                logger.warning(f"Error sorting task {getattr(task, 'id', 'unknown')}: {e}")
                return (5, 2)  # Default to lowest priority
        
        return sorted(tasks, key=safe_sort_key)
    
    def _can_task_be_started(self, task, all_tasks: List) -> bool:
        """Check if a task can be started (all dependencies satisfied)"""
        if not task.dependencies:
            return True
        
        # Check if all dependencies are completed
        for dep_id in task.dependencies:
            dep_task = next((t for t in all_tasks if t.id.value == dep_id.value), None)
            if not dep_task or not dep_task.status.is_done():
                return False
        
        return True
    
    def _find_next_subtask(self, task) -> Optional[Dict[str, Any]]:
        """Find the first incomplete subtask in a task"""
        if not task.subtasks:
            return None
        
        for subtask in task.subtasks:
            if not subtask.get('completed', False):
                return subtask
        
        return None
    
    def _should_generate_context_info(self, task) -> bool:
        """
        Check if context_info should be generated for a task.
        Conditions:
        1. Task status is 'todo'
        2. No subtasks are completed (either no subtasks or all subtasks are incomplete)
        """
        try:
            # Null safety: check if task and status exist
            if not task or not hasattr(task, 'status') or not task.status:
                return False
                
            # Check if task status is 'todo'
            status_value = getattr(task.status, 'value', str(task.status)) if task.status else 'unknown'
            if status_value != "todo":
                return False
            
            # Check subtasks: if there are subtasks, none should be completed
            if task.subtasks:
                for subtask in task.subtasks:
                    if subtask and subtask.get('completed', False):
                        return False
            
            return True
        except Exception as e:
            logger.debug(f"Error checking context info generation for task: {e}")
            return False
    
    def _task_to_dict(self, task, include_context: bool = False, user_id: Optional[str] = None, project_id: str = "default_project", git_branch_id: str = "main") -> Dict[str, Any]:
        """Convert task entity to dictionary with optional context data following clean relationship chain"""
        task_dict = task.to_dict()
        
        # Calculate subtask progress
        if task.subtasks:
            progress = task.get_subtask_progress()
            task_dict['subtask_progress'] = progress
        
        # Fetch context data if requested
        if include_context:
            try:
                # Use hierarchical context service to get context data with enhanced error handling
                factory = self._get_context_factory()
                context_service = factory.create_unified_service()
                
                # Get context data with permission error handling
                context_result = None
                try:
                    # context_service methods are synchronous, no need for await or timeout
                    context_result = context_service.resolve_context(
                        level="task",
                        context_id=str(task.id.value)
                    )
                except PermissionError as e:
                    logger.warning(f"Permission denied during context resolution for task {task.id.value}: {e}")
                except (FileNotFoundError, OSError) as e:
                    logger.debug(f"Context file issue for task {task.id.value}: {e}")
                except Exception as e:
                    logger.warning(f"Context resolution failed for task {task.id.value}: {e}")
                
                if context_result and context_result.get("success"):
                    context = context_result.get("context")
                    # Convert context to dict if it has to_dict method
                    if hasattr(context, 'to_dict'):
                        task_dict['context_data'] = context.to_dict()
                    else:
                        task_dict['context_data'] = context
                    task_dict['context_available'] = True
                    logger.debug(f"Context data fetched for task {task.id.value}")
                else:
                    task_dict['context_data'] = None
                    task_dict['context_available'] = False
                    logger.debug(f"No context data found for task {task.id.value}")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch context data for task {task.id.value}: {e}")
                task_dict['context_data'] = None
                task_dict['context_available'] = False
        else:
            task_dict['context_data'] = None
            task_dict['context_available'] = False
        
        return task_dict
    
    def _get_task_context(self, task, all_tasks: List) -> Dict[str, Any]:
        """Get context information for a task"""
        # Count dependencies
        dependency_count = len(task.dependencies) if task.dependencies else 0
        
        # Find tasks blocked by this task
        blocking_tasks = [
            t for t in all_tasks 
            if t.dependencies and any(dep.value == task.id.value for dep in t.dependencies)
        ]
        
        # Calculate overall progress
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.status.is_done()])
        
        context = {
            "task_id": task.id.value,
            "can_start": self._can_task_be_started(task, all_tasks),
            "dependency_count": dependency_count,
            "blocking_count": len(blocking_tasks),
            "overall_progress": {
                "completed": completed_tasks,
                "total": total_tasks,
                "percentage": round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
            }
        }
        
        # Add subtask progress if available
        if task.subtasks:
            progress = task.get_subtask_progress()
            context["subtask_progress"] = progress
        
        return context
    
    def _get_completion_context(self, all_tasks: List) -> Dict[str, Any]:
        """Get context when all tasks are completed"""
        total_tasks = len(all_tasks)
        
        # Count by priority
        priority_counts = {}
        for task in all_tasks:
            priority = str(task.priority)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            "total_completed": total_tasks,
            "priority_breakdown": priority_counts,
            "completion_rate": 100.0
        }
    
    def _get_blocking_info(self, blocked_tasks: List, all_tasks: List) -> Dict[str, Any]:
        """Get information about blocked tasks and their dependencies"""
        blocking_info = {
            "blocked_tasks": [],
            "required_completions": []
        }
        
        for task in blocked_tasks:
            task_info = {
                "id": task.id.value,
                "title": task.title,
                "priority": str(task.priority),
                "blocked_by": []
            }
            
            # Find which dependencies are not completed
            for dep_id in task.dependencies:
                dep_task = next((t for t in all_tasks if t.id.value == dep_id.value), None)
                if dep_task and not dep_task.status.is_done():
                    task_info["blocked_by"].append({
                        "id": dep_task.id.value,
                        "title": dep_task.title,
                        "status": str(dep_task.status)
                    })
                    
                    # Add to required completions if not already there
                    if not any(req["id"] == dep_task.id.value for req in blocking_info["required_completions"]):
                        blocking_info["required_completions"].append({
                            "id": dep_task.id.value,
                            "title": dep_task.title,
                            "status": str(dep_task.status),
                            "priority": str(dep_task.priority)
                        })
            
            blocking_info["blocked_tasks"].append(task_info)
        
        return blocking_info 
    
    def _validate_task_context_alignment(self, tasks: List) -> List[Dict[str, Any]]:
        """
        Validate that task status matches context status for all tasks following clean relationship chain.
        Returns list of mismatches that need to be fixed.
        """
        mismatches = []
        
        try:
            # Create hierarchical context service
            factory = self._get_context_factory()
            context_service = factory.create_unified_service()
            
            for task in tasks:
                try:
                    # Get context for this task using hierarchical system
                    context_result = context_service.resolve_context(
                        level="task",
                        context_id=task.id.value
                    )
                    context = context_result.get("context") if context_result and context_result.get("success") else None
                    
                    if context:
                        # Handle both dict and object with to_dict method
                        if hasattr(context, 'to_dict'):
                            context_data = context.to_dict()
                        else:
                            context_data = context
                        
                        # Ensure context_data is a dictionary
                        if not isinstance(context_data, dict):
                            # If it's a string or other type, skip validation
                            logger.debug(f"Context data for task {task.id.value} is not a dictionary (type: {type(context_data)}), skipping validation")
                            continue
                            
                        context_status = context_data.get('metadata', {}).get('status')
                        task_status = task.status.value if task.status and hasattr(task.status, 'value') else str(task.status) if task.status else 'todo'
                        
                        # Check for status mismatch
                        if context_status and context_status != task_status:
                            mismatch_info = {
                                "task_id": task.id.value,
                                "title": task.title,
                                "task_status": task_status,
                                "context_status": context_status,

                                "fix_action": f"Update context status from '{context_status}' to '{task_status}' or vice versa",
                                "suggested_command": f"manage_context(action='update_property', level='task', context_id='{task.id.value}', property_path='metadata.status', value='{task_status}')"
                            }
                            mismatches.append(mismatch_info)
                            
                        # Also check if task is marked as "done" but context shows incomplete subtasks
                        if task_status == "done" and context_data.get('subtasks', {}).get('items'):
                            incomplete_subtasks = [
                                subtask for subtask in context_data['subtasks']['items']
                                if not subtask.get('completed', False)
                            ]
                            if incomplete_subtasks:
                                mismatch_info = {
                                    "task_id": task.id.value,
                                    "title": task.title,
                                    "task_status": task_status,
                                    "context_status": context_status,
                                    "issue": "task_done_but_subtasks_incomplete",
                                    "incomplete_subtasks": len(incomplete_subtasks),


                                    "fix_action": f"Complete {len(incomplete_subtasks)} remaining subtasks or update task status",
                                    "incomplete_subtask_details": [
                                        {"id": subtask.get('id'), "title": subtask.get('title')} 
                                        for subtask in incomplete_subtasks[:3]  # Show first 3
                                    ]
                                }
                                mismatches.append(mismatch_info)
                                
                except Exception as e:
                    # Log but don't fail for individual task context issues
                    logger.warning(f"Context validation failed for task {task.id.value}: {e}")
                    continue
                    
        except Exception as e:
            # Log but don't fail the entire validation
            logger.warning(f"Context manager initialization failed during validation: {e}")
            
        return mismatches