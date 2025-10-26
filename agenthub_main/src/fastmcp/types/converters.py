"""
Domain to DTO Converters
Helper functions to convert domain entities to API DTOs
"""

from typing import Any
from datetime import datetime

from .entities import TaskDTO, SubtaskDTO
from .summaries import TaskSummaryDTO, SubtaskSummaryDTO


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Get value from dict or object attribute"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_datetime(value: Any) -> str | None:
    """Format datetime to ISO string"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def task_to_dto(task: Any, include_subtasks: bool = False) -> TaskDTO:
    """Convert domain Task entity or dict to TaskDTO

    Handles both:
    - Entity objects from ORM (task.id, task.title, etc.)
    - Dict objects from performance mode (task['id'], task['title'], etc.)
    """
    # Handle dict input (performance mode)
    if isinstance(task, dict):
        assignees = task.get('assignees') or []
        dependencies = task.get('dependencies') or []
        labels = task.get('labels') or []
        subtasks = task.get('subtasks') or []

        return TaskDTO(
            id=str(task['id']),
            title=task['title'],
            description=task.get('description'),
            status=str(task['status']),
            priority=str(task['priority']),
            assignees=assignees,
            assignees_count=len(assignees),
            subtask_count=task.get('subtask_count', 0),
            has_dependencies=bool(dependencies),
            dependency_count=len(dependencies),
            dependencies=[str(dep) for dep in dependencies],
            has_context=bool(task.get('context_id')),
            context_id=task.get('context_id'),
            context_data=task.get('context_data'),
            git_branch_id=task['git_branch_id'],
            project_id=task.get('project_id', ''),
            created_at=_format_datetime(task.get('created_at')),
            updated_at=_format_datetime(task.get('updated_at')),
            due_date=_format_datetime(task.get('due_date')),
            estimated_effort=task.get('estimated_effort'),
            labels=labels,
            details=task.get('details'),
            progress_percentage=task.get('progress_percentage'),
            progress_history=task.get('progress_history'),
            progress_count=task.get('progress_count'),
            subtasks=[subtask_to_dto(st) for st in subtasks] if include_subtasks and subtasks else None
        )

    # Handle entity object input (standard ORM mode)
    assignees = task.assignees if task.assignees else []
    dependencies = task.dependencies if hasattr(task, 'dependencies') and task.dependencies else []
    labels = task.labels if hasattr(task, 'labels') and task.labels else []
    subtasks = task.subtasks if hasattr(task, 'subtasks') and task.subtasks else []

    return TaskDTO(
        id=str(task.id),
        title=task.title,
        description=task.description,
        status=str(task.status),
        priority=str(task.priority),
        assignees=assignees,
        assignees_count=len(assignees),
        subtask_count=getattr(task, 'subtask_count', 0),
        has_dependencies=bool(dependencies),
        dependency_count=len(dependencies),
        dependencies=[str(dep) for dep in dependencies],
        has_context=bool(getattr(task, 'context_id', None)),
        context_id=str(getattr(task, 'context_id', None)) if getattr(task, 'context_id', None) else None,
        context_data=getattr(task, 'context_data', None),
        git_branch_id=str(task.git_branch_id),
        project_id=str(getattr(task, 'project_id', '')) if getattr(task, 'project_id', '') else '',
        created_at=_format_datetime(getattr(task, 'created_at', None)),
        updated_at=_format_datetime(getattr(task, 'updated_at', None)),
        due_date=_format_datetime(getattr(task, 'due_date', None)),
        estimated_effort=getattr(task, 'estimated_effort', None),
        labels=labels,
        details=getattr(task, 'details', None),
        progress_percentage=getattr(task, 'progress_percentage', None),
        progress_history=getattr(task, 'progress_history', None),
        progress_count=getattr(task, 'progress_count', None),
        subtasks=[subtask_to_dto(st) for st in subtasks] if include_subtasks and subtasks else None
    )


def subtask_to_dto(subtask: Any) -> SubtaskDTO:
    """Convert domain Subtask entity or dict to SubtaskDTO

    Handles both:
    - Entity objects from ORM (subtask.id, subtask.title, etc.)
    - Dict objects from performance mode (subtask['id'], subtask['title'], etc.)
    """
    # Handle dict input (performance mode)
    if isinstance(subtask, dict):
        assignees = subtask.get('assignees') or []
        return SubtaskDTO(
            id=str(subtask['id']),
            task_id=str(subtask.get('parent_task_id', subtask.get('task_id', ''))),  # Frontend expects task_id
            title=subtask['title'],
            description=subtask.get('description'),
            status=str(subtask['status']),
            priority=str(subtask['priority']),
            assignees=assignees,
            assignees_count=len(assignees),
            progress_percentage=subtask.get('progress_percentage'),
            created_at=_format_datetime(subtask.get('created_at')),
            updated_at=_format_datetime(subtask.get('updated_at')),
            progress_notes=subtask.get('progress_notes'),
            completion_summary=subtask.get('completion_summary')
        )

    # Handle entity object input (standard ORM mode)
    assignees = subtask.assignees if subtask.assignees else []
    return SubtaskDTO(
        id=str(subtask.id),
        task_id=str(subtask.parent_task_id),  # Frontend expects task_id
        title=subtask.title,
        description=subtask.description,
        status=str(subtask.status),
        priority=str(subtask.priority),
        assignees=assignees,
        assignees_count=len(assignees),
        progress_percentage=getattr(subtask, 'progress_percentage', None),
        created_at=_format_datetime(getattr(subtask, 'created_at', None)),
        updated_at=_format_datetime(getattr(subtask, 'updated_at', None)),
        progress_notes=getattr(subtask, 'progress_notes', None),
        completion_summary=getattr(subtask, 'completion_summary', None)
    )


def task_summary_to_dto(task: Any) -> TaskSummaryDTO:
    """Convert domain Task or dict to TaskSummaryDTO (lightweight version)

    Handles both:
    - Entity objects from ORM (task.id, task.title, etc.)
    - Dict objects from performance mode (task['id'], task['title'], etc.)
    """
    import logging
    logger = logging.getLogger(__name__)

    # Handle dict input (performance mode)
    if isinstance(task, dict):
        logger.info(f"🔍 CONVERTER (dict mode) - Task {task.get('id', 'unknown')[:8]}")
        logger.info(f"  - subtask_count in dict: {task.get('subtask_count', 'MISSING')}")
        logger.info(f"  - project_id in dict: {task.get('project_id', 'MISSING')}")
        logger.info(f"  - git_branch_id in dict: {task.get('git_branch_id', 'MISSING')}")

        assignees = task.get('assignees') or []
        dependencies = task.get('dependencies') or []
        dto = TaskSummaryDTO(
            id=str(task['id']),
            title=task['title'],
            status=str(task['status']),
            priority=str(task['priority']),
            subtask_count=task.get('subtask_count', 0),
            assignees_count=len(assignees),
            assignees=assignees,
            has_dependencies=bool(dependencies),
            dependency_count=len(dependencies),
            has_context=bool(task.get('context_id')),
            git_branch_id=task.get('git_branch_id'),  # Required by frontend validation
            project_id=task.get('project_id'),  # Required by frontend validation
            created_at=_format_datetime(task.get('created_at')),
            updated_at=_format_datetime(task.get('updated_at'))
        )
        logger.info(f"  ✅ DTO created with subtask_count={dto.subtask_count}")
        return dto

    # Handle entity object input (standard ORM mode)
    logger.info(f"🔍 CONVERTER (entity mode) - Task {str(task.id)[:8]}")
    logger.info(f"  - hasattr subtask_count: {hasattr(task, 'subtask_count')}")
    if hasattr(task, 'subtask_count'):
        logger.info(f"  - subtask_count value: {task.subtask_count}")
    logger.info(f"  - hasattr project_id: {hasattr(task, 'project_id')}")
    logger.info(f"  - hasattr git_branch_id: {hasattr(task, 'git_branch_id')}")

    assignees = task.assignees if task.assignees else []
    dependencies = task.dependencies if hasattr(task, 'dependencies') and task.dependencies else []
    dto = TaskSummaryDTO(
        id=str(task.id),
        title=task.title,
        status=str(task.status),
        priority=str(task.priority),
        subtask_count=getattr(task, 'subtask_count', 0),
        assignees_count=len(assignees),
        assignees=assignees,
        has_dependencies=bool(dependencies),
        dependency_count=len(dependencies),
        has_context=bool(getattr(task, 'context_id', None)),
        git_branch_id=str(getattr(task, 'git_branch_id', None)) if getattr(task, 'git_branch_id', None) else None,  # Required by frontend validation
        project_id=str(getattr(task, 'project_id', None)) if getattr(task, 'project_id', None) else None,  # Required by frontend validation
        created_at=_format_datetime(getattr(task, 'created_at', None)),
        updated_at=_format_datetime(getattr(task, 'updated_at', None))
    )
    logger.info(f"  ✅ DTO created with subtask_count={dto.subtask_count}, project_id={dto.project_id}")
    return dto


def subtask_summary_to_dto(subtask: Any) -> SubtaskSummaryDTO:
    """Convert domain Subtask or dict to SubtaskSummaryDTO (lightweight version)

    Handles both:
    - Entity objects from ORM (subtask.id, subtask.title, etc.)
    - Dict objects from performance mode (subtask['id'], subtask['title'], etc.)
    """
    # Handle dict input (performance mode)
    if isinstance(subtask, dict):
        assignees = subtask.get('assignees') or []
        return SubtaskSummaryDTO(
            id=str(subtask['id']),
            task_id=str(subtask.get('parent_task_id', subtask.get('task_id', ''))),  # Frontend expects task_id
            title=subtask['title'],
            status=str(subtask['status']),
            priority=str(subtask['priority']),
            assignees_count=len(assignees),
            assignees=assignees,
            progress_percentage=subtask.get('progress_percentage'),
            created_at=_format_datetime(subtask.get('created_at')),
            updated_at=_format_datetime(subtask.get('updated_at'))
        )

    # Handle entity object input (standard ORM mode)
    assignees = subtask.assignees if subtask.assignees else []
    return SubtaskSummaryDTO(
        id=str(subtask.id),
        task_id=str(subtask.parent_task_id),  # Frontend expects task_id
        title=subtask.title,
        status=str(subtask.status),
        priority=str(subtask.priority),
        assignees_count=len(assignees),
        assignees=assignees,
        progress_percentage=getattr(subtask, 'progress_percentage', None),
        created_at=_format_datetime(getattr(subtask, 'created_at', None)),
        updated_at=_format_datetime(getattr(subtask, 'updated_at', None))
    )


