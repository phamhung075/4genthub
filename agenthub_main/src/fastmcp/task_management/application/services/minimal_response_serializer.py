"""
Minimal Response Serializer Service

Provides token-optimized serialization for MCP tool responses by excluding redundant
input properties that the caller already knows. Follows the principle of returning
only what changed or was computed.

Token Savings Strategy:
- Full response: ~600-800 tokens (returns all properties including inputs)
- Minimal response: ~150-200 tokens (returns only essential computed values)
- Savings: ~70-75% reduction per create/update operation
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MinimalResponseSerializer:
    """
    Serializes task and subtask entities with minimal redundancy for token optimization.

    Philosophy:
    - INCLUDE: IDs, timestamps, computed values (progress, counts)
    - EXCLUDE: Input properties caller already provided (title, description, assignees, etc.)
    - EXCEPTION: Status/priority included if auto-computed from progress_percentage
    """

    @staticmethod
    def serialize_task_minimal(task, operation: str) -> dict[str, Any]:
        """
        Serialize task entity with minimal properties for create/update operations.

        Args:
            task: Task entity or dictionary
            operation: Operation type ('create' or 'update')

        Returns:
            Minimal task dictionary with only essential computed properties
        """
        # Handle both entity objects and dictionaries
        if hasattr(task, 'to_dict'):
            full_dict = task.to_dict()
        else:
            full_dict = task

        # Essential properties that MUST be returned
        minimal = {
            "id": full_dict.get("id"),
            "created_at": full_dict.get("created_at"),
            "updated_at": full_dict.get("updated_at"),
        }

        # Include computed/derived properties
        if "context_id" in full_dict:
            minimal["context_id"] = full_dict["context_id"]

        if "overall_progress" in full_dict:
            minimal["overall_progress"] = full_dict["overall_progress"]

        if "progress_percentage" in full_dict:
            minimal["progress_percentage"] = full_dict["progress_percentage"]

        if "progress_count" in full_dict:
            minimal["progress_count"] = full_dict["progress_count"]

        if "subtask_count" in full_dict:
            minimal["subtask_count"] = full_dict["subtask_count"]

        if "completed_subtasks" in full_dict:
            minimal["completed_subtasks"] = full_dict["completed_subtasks"]

        if "dependency_count" in full_dict:
            minimal["dependency_count"] = full_dict["dependency_count"]

        # For create operations, include git_branch_id as it's context-critical
        if operation == "create" and "git_branch_id" in full_dict:
            minimal["git_branch_id"] = full_dict["git_branch_id"]

        # Include status/priority if they were auto-computed (not provided by user)
        # This helps the caller know what defaults were applied
        if operation == "create":
            if "status" in full_dict:
                minimal["status"] = full_dict["status"]
            if "priority" in full_dict:
                minimal["priority"] = full_dict["priority"]

        logger.debug(
            f"Task minimal serialization: {len(str(minimal))} chars vs "
            f"{len(str(full_dict))} chars full (saved {100 - (len(str(minimal)) * 100 / len(str(full_dict))):.1f}%)"
        )

        return minimal

    @staticmethod
    def serialize_subtask_minimal(subtask, operation: str) -> dict[str, Any]:
        """
        Serialize subtask entity with minimal properties for create/update operations.

        Args:
            subtask: Subtask entity or dictionary
            operation: Operation type ('create', 'update', or 'complete')

        Returns:
            Minimal subtask dictionary with only essential computed properties
        """
        # Handle both entity objects and dictionaries
        if hasattr(subtask, 'to_dict'):
            full_dict = subtask.to_dict(include_parent_id=True)
        else:
            full_dict = subtask

        # Essential properties that MUST be returned
        # CRITICAL: Include fields required by SubtaskUpdatePayload (title, status, task_id)
        minimal = {
            "id": full_dict.get("id"),
            "title": full_dict.get("title"),  # ✅ FIX: Required by SubtaskUpdatePayload
            "description": full_dict.get("description"),  # ✅ FIX: Required by SubtaskUpdatePayload (optional but should be preserved)
            "status": full_dict.get("status"),  # ✅ FIX: Required by SubtaskUpdatePayload
            "task_id": full_dict.get("parent_task_id"),  # ✅ FIX: Required by SubtaskUpdatePayload (maps to task_id)
            "parent_task_id": full_dict.get("parent_task_id"),  # Keep for backward compatibility
            "created_at": full_dict.get("created_at"),
            "updated_at": full_dict.get("updated_at"),
        }

        # Include computed/derived properties
        if "progress_percentage" in full_dict:
            minimal["progress_percentage"] = full_dict["progress_percentage"]

        if "progress_count" in full_dict:
            minimal["progress_count"] = full_dict["progress_count"]

        # For create operations, include priority as it might be defaulted
        if operation == "create" and "priority" in full_dict:
            minimal["priority"] = full_dict["priority"]

        logger.debug(
            f"Subtask minimal serialization: {len(str(minimal))} chars vs "
            f"{len(str(full_dict))} chars full (saved {100 - (len(str(minimal)) * 100 / len(str(full_dict))):.1f}%)"
        )

        return minimal

    @staticmethod
    def serialize_task_list_minimal(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Serialize task list with moderate optimization for list operations.

        For list operations, include more properties than create/update but still
        optimize by excluding large fields like progress_history.

        Args:
            tasks: List of task dictionaries

        Returns:
            List of optimized task dictionaries
        """
        optimized = []

        for task in tasks:
            # For list operations, include identifying/summary properties
            optimized_task = {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "progress_percentage": task.get("progress_percentage"),
                "subtask_count": task.get("subtask_count"),
                "completed_subtasks": task.get("completed_subtasks"),
                "assignees": task.get("assignees"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
            }

            # Exclude: description, labels, dependencies, progress_history
            # These can be fetched via get operation if needed

            optimized.append(optimized_task)

        return optimized

    @staticmethod
    def serialize_subtask_list_minimal(subtasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Serialize subtask list with moderate optimization for list operations.

        Args:
            subtasks: List of subtask dictionaries

        Returns:
            List of optimized subtask dictionaries
        """
        optimized = []

        for subtask in subtasks:
            # For list operations, include identifying/summary properties
            optimized_subtask = {
                "id": subtask.get("id"),
                "title": subtask.get("title"),
                "status": subtask.get("status"),
                "priority": subtask.get("priority"),
                "progress_percentage": subtask.get("progress_percentage"),
                "assignees": subtask.get("assignees"),
                "created_at": subtask.get("created_at"),
                "updated_at": subtask.get("updated_at"),
            }

            # Exclude: description, progress_history
            # These can be fetched via get operation if needed

            optimized.append(optimized_subtask)

        return optimized

    @staticmethod
    def should_use_minimal_serialization(operation: str) -> bool:
        """
        Determine if minimal serialization should be used for an operation.

        Args:
            operation: Operation type

        Returns:
            True if minimal serialization should be used
        """
        # Use minimal serialization for create/update operations
        minimal_operations = {"create", "update", "complete"}

        # Use full serialization for read operations
        full_operations = {"get", "list", "search", "next"}

        return operation in minimal_operations

    @staticmethod
    def get_token_savings_estimate(operation: str) -> str:
        """
        Estimate token savings for using minimal serialization.

        Args:
            operation: Operation type

        Returns:
            Human-readable savings estimate
        """
        if operation in {"create", "update", "complete"}:
            return "~70-75% reduction (600-800 tokens → 150-200 tokens)"
        elif operation in {"list", "search"}:
            return "~40-50% reduction per item"
        else:
            return "No optimization (full details needed)"
