"""
Backend API Contract Tests - GitBranch/Branch Management Endpoints

TDD Approach: These tests document the expected API contract between backend and frontend.
Tests are based on GitBranch domain entity and frontend Branch interface expectations.

Reference: agenthub_main/src/fastmcp/task_management/domain/entities/git_branch.py
Frontend: agenthub-frontend/src/types/api.types.ts (Branch interface)

Expected Contract:
- Branch has: id, project_id, name, git_branch_name
- Optional: description, status, is_active
- ISO 8601 timestamps (created_at, updated_at)
- Proper UUID format for IDs
- Task statistics: task_count, completed_tasks, progress_percentage
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from fastmcp.task_management.domain.entities.git_branch import GitBranch


@pytest.fixture
def sample_git_branch(project_id: str):
    """Create a sample git branch for testing API contract."""
    git_branch = GitBranch.create(
        name="Test Branch",
        description="Test git branch for API contract testing",
        project_id=project_id
    )
    git_branch.git_branch_name = "feature/test-api-contract"
    return git_branch


class TestGitBranchAPIContractBasicFields:
    """Test basic fields that SHOULD PASS - core git branch fields."""

    def test_git_branch_has_required_id_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes UUID id field.
        Status: ✅ SHOULD PASS - Core field in GitBranch entity.

        Frontend expects: id: string
        """
        assert hasattr(sample_git_branch, "id"), "GitBranch must have 'id' field"
        assert sample_git_branch.id is not None, "GitBranch id must not be None"

        # Convert to string for UUID validation
        id_str = str(sample_git_branch.id.value if hasattr(sample_git_branch.id, 'value')
                     else sample_git_branch.id)
        assert isinstance(id_str, str), "GitBranch id must be string or convertible to string"

        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(id_str)
        except ValueError:
            pytest.fail(f"GitBranch id '{id_str}' is not a valid UUID")

    def test_git_branch_has_required_project_id_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes project_id field.
        Status: ✅ SHOULD PASS - Required for project association.

        Frontend expects: project_id: string
        """
        assert hasattr(sample_git_branch, "project_id"), (
            "GitBranch must have 'project_id' field"
        )
        assert isinstance(sample_git_branch.project_id, str), (
            "GitBranch project_id must be string"
        )
        assert len(sample_git_branch.project_id) > 0, (
            "GitBranch project_id must not be empty"
        )

    def test_git_branch_has_required_name_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes name field.
        Status: ✅ SHOULD PASS - Required field.

        Frontend expects: name: string
        """
        assert hasattr(sample_git_branch, "name"), "GitBranch must have 'name' field"
        assert isinstance(sample_git_branch.name, str), "GitBranch name must be string"
        assert len(sample_git_branch.name) > 0, "GitBranch name must not be empty"

    def test_git_branch_has_git_branch_name_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes git_branch_name field.
        Status: ✅ SHOULD PASS - Required for actual git branch reference.

        Frontend expects: git_branch_name: string
        Backend has: git_branch_name: str | None
        """
        assert hasattr(sample_git_branch, "git_branch_name"), (
            "GitBranch must have 'git_branch_name' field"
        )
        # git_branch_name can be optional but should be string when present
        if sample_git_branch.git_branch_name is not None:
            assert isinstance(sample_git_branch.git_branch_name, str), (
                "GitBranch git_branch_name must be string when provided"
            )


class TestGitBranchAPIContractTimestamps:
    """Test timestamp fields - ISO 8601 format."""

    def test_git_branch_created_at_is_iso8601_compatible(self, sample_git_branch: GitBranch):
        """
        Verify created_at can be serialized to ISO 8601 format.
        Status: ✅ SHOULD PASS - Standard timestamp field.

        Frontend expects: created_at?: string
        Backend returns: created_at: datetime → serialized as ISO string
        """
        assert hasattr(sample_git_branch, "created_at"), (
            "GitBranch must have 'created_at' field"
        )

        # Handle both datetime objects and string representations
        if isinstance(sample_git_branch.created_at, datetime):
            iso_string = sample_git_branch.created_at.isoformat()
            assert "T" in iso_string, "created_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_git_branch.created_at, str):
            assert "T" in sample_git_branch.created_at, (
                "created_at must be ISO 8601 format (contains 'T')"
            )
            try:
                datetime.fromisoformat(sample_git_branch.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"created_at '{sample_git_branch.created_at}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"created_at must be datetime or string, got {type(sample_git_branch.created_at)}"
            )

    def test_git_branch_updated_at_is_iso8601_compatible(self, sample_git_branch: GitBranch):
        """
        Verify updated_at can be serialized to ISO 8601 format.
        Status: ✅ SHOULD PASS - Standard timestamp field.

        Frontend expects: updated_at?: string
        Backend returns: updated_at: datetime → serialized as ISO string
        """
        assert hasattr(sample_git_branch, "updated_at"), (
            "GitBranch must have 'updated_at' field"
        )

        # Handle both datetime objects and string representations
        if isinstance(sample_git_branch.updated_at, datetime):
            iso_string = sample_git_branch.updated_at.isoformat()
            assert "T" in iso_string, "updated_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_git_branch.updated_at, str):
            assert "T" in sample_git_branch.updated_at, (
                "updated_at must be ISO 8601 format (contains 'T')"
            )
            try:
                datetime.fromisoformat(sample_git_branch.updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"updated_at '{sample_git_branch.updated_at}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"updated_at must be datetime or string, got {type(sample_git_branch.updated_at)}"
            )


class TestGitBranchAPIContractStatusFields:
    """Test status and state fields."""

    def test_git_branch_has_status_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes status field.
        Status: ✅ SHOULD PASS - Standard field.

        Frontend expects: status?: string
        Backend has: status: TaskStatus
        """
        assert hasattr(sample_git_branch, "status"), "GitBranch must have 'status' field"

        # Status may be a value object or string
        status_str = (sample_git_branch.status.value if hasattr(sample_git_branch.status, 'value')
                      else str(sample_git_branch.status))

        valid_statuses = ["todo", "in_progress", "done", "blocked", "cancelled",
                          "review", "testing", "archived"]
        assert status_str in valid_statuses, (
            f"GitBranch status '{status_str}' must be one of {valid_statuses}"
        )

    def test_git_branch_has_archived_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes archived field.
        Status: ✅ SHOULD PASS - Archival support.

        Backend has: archived: bool
        """
        assert hasattr(sample_git_branch, "archived"), "GitBranch must have 'archived' field"
        assert isinstance(sample_git_branch.archived, bool), (
            "GitBranch archived must be boolean"
        )

    def test_git_branch_has_priority_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch includes priority field.
        Status: ✅ SHOULD PASS - Branch-level priority.

        Backend has: priority: Priority
        """
        assert hasattr(sample_git_branch, "priority"), "GitBranch must have 'priority' field"

        # Priority may be a value object or string
        priority_str = (sample_git_branch.priority.value if
                        hasattr(sample_git_branch.priority, 'value')
                        else str(sample_git_branch.priority))

        valid_priorities = ["low", "medium", "high", "urgent", "critical"]
        assert priority_str in valid_priorities, (
            f"GitBranch priority '{priority_str}' must be one of {valid_priorities}"
        )


class TestGitBranchAPIContractOptionalFields:
    """Test optional fields that may be present."""

    def test_git_branch_has_description_field(self, sample_git_branch: GitBranch):
        """
        Verify git branch has description field.
        Status: ✅ SHOULD PASS - Standard optional field.

        Frontend expects: description?: string
        """
        assert hasattr(sample_git_branch, "description"), (
            "GitBranch must have 'description' field"
        )
        # Description can be string or empty
        if sample_git_branch.description is not None:
            assert isinstance(sample_git_branch.description, str), (
                "GitBranch description must be string when provided"
            )

    def test_git_branch_has_assigned_agent_fields(self, sample_git_branch: GitBranch):
        """
        Verify git branch has agent assignment fields.
        Status: ✅ SHOULD PASS - Agent assignment tracking.

        Backend has:
        - assigned_agent_id: str | None (single agent, legacy)
        - assigned_agents: list[str] (multiple agents, current)
        """
        assert hasattr(sample_git_branch, "assigned_agent_id"), (
            "GitBranch should have 'assigned_agent_id' field"
        )
        assert hasattr(sample_git_branch, "assigned_agents"), (
            "GitBranch should have 'assigned_agents' field"
        )

        if sample_git_branch.assigned_agents is not None:
            assert isinstance(sample_git_branch.assigned_agents, list), (
                "assigned_agents must be list"
            )


class TestGitBranchAPIContractTaskManagement:
    """Test task management fields and methods."""

    def test_git_branch_has_task_collections(self, sample_git_branch: GitBranch):
        """
        Verify git branch has task collection fields.
        Status: ✅ SHOULD PASS - Core task tree functionality.

        Backend has:
        - root_tasks: dict[str, Task]
        - all_tasks: dict[str, Task]
        """
        assert hasattr(sample_git_branch, "root_tasks"), (
            "GitBranch must have 'root_tasks' field"
        )
        assert hasattr(sample_git_branch, "all_tasks"), (
            "GitBranch must have 'all_tasks' field"
        )

        assert isinstance(sample_git_branch.root_tasks, dict), "root_tasks must be dict"
        assert isinstance(sample_git_branch.all_tasks, dict), "all_tasks must be dict"

    def test_git_branch_get_task_count_method(self, sample_git_branch: GitBranch):
        """
        Verify git branch can calculate task count.
        Status: ✅ SHOULD PASS - Required for frontend display.

        Frontend expects task counts in BranchSummary:
        - task_count: number
        - completed_tasks: number
        - progress_percentage: number
        """
        task_count = sample_git_branch.get_task_count()
        assert isinstance(task_count, int), "get_task_count must return int"
        assert task_count >= 0, "task_count must be non-negative"

    def test_git_branch_get_completed_task_count_method(self, sample_git_branch: GitBranch):
        """
        Verify git branch can calculate completed task count.
        Status: ✅ SHOULD PASS - Required for progress tracking.
        """
        completed_count = sample_git_branch.get_completed_task_count()
        assert isinstance(completed_count, int), "get_completed_task_count must return int"
        assert completed_count >= 0, "completed_count must be non-negative"

    def test_git_branch_get_progress_percentage_method(self, sample_git_branch: GitBranch):
        """
        Verify git branch can calculate progress percentage.
        Status: ✅ SHOULD PASS - Required for progress tracking.
        """
        progress = sample_git_branch.get_progress_percentage()
        assert isinstance(progress, float), "get_progress_percentage must return float"
        assert 0.0 <= progress <= 100.0, (
            f"progress_percentage must be 0.0-100.0, got {progress}"
        )

    def test_git_branch_get_tree_status_method(self, sample_git_branch: GitBranch):
        """
        Verify git branch can provide comprehensive tree status.
        Status: ✅ SHOULD PASS - Rich status information.

        Expected structure:
        - tree_name: str
        - total_tasks: int
        - completed_tasks: int
        - progress_percentage: float
        - status_breakdown: Dict
        - priority_breakdown: Dict
        """
        tree_status = sample_git_branch.get_tree_status()

        assert isinstance(tree_status, dict), "get_tree_status must return dict"
        assert "tree_name" in tree_status, "tree_status must include tree_name"
        assert "total_tasks" in tree_status, "tree_status must include total_tasks"
        assert "completed_tasks" in tree_status, "tree_status must include completed_tasks"
        assert "progress_percentage" in tree_status, (
            "tree_status must include progress_percentage"
        )
        assert "status_breakdown" in tree_status, "tree_status must include status_breakdown"
        assert "priority_breakdown" in tree_status, (
            "tree_status must include priority_breakdown"
        )


class TestGitBranchAPIContractSerialization:
    """Test git branch serialization to dict for API responses."""

    def test_git_branch_to_dict_method(self, sample_git_branch: GitBranch):
        """
        Verify GitBranch can be serialized to dictionary for API response.
        Status: ✅ SHOULD PASS - Required for JSON serialization.
        """
        branch_dict = sample_git_branch.to_dict()

        assert isinstance(branch_dict, dict), "to_dict() must return dictionary"

        # Verify required keys in serialized response
        required_keys = ["id", "name", "project_id", "created_at", "updated_at"]
        for key in required_keys:
            assert key in branch_dict, f"Serialized branch must include {key}"

        # Verify ID is string in serialized form
        assert isinstance(branch_dict["id"], str), "Serialized id must be string"

        # Verify timestamps are ISO 8601 strings in serialized form
        assert isinstance(branch_dict["created_at"], str), "Serialized created_at must be string"
        assert isinstance(branch_dict["updated_at"], str), "Serialized updated_at must be string"
        assert "T" in branch_dict["created_at"], "created_at must be ISO 8601 format"
        assert "T" in branch_dict["updated_at"], "updated_at must be ISO 8601 format"

    def test_git_branch_serialized_status_is_string(self, sample_git_branch: GitBranch):
        """
        Verify status is serialized as string, not value object.
        Status: ✅ SHOULD PASS - Frontend expects string.
        """
        branch_dict = sample_git_branch.to_dict()

        assert "status" in branch_dict, "Serialized branch must include status"
        assert isinstance(branch_dict["status"], str), "Serialized status must be string"

    def test_git_branch_serialized_priority_is_string(self, sample_git_branch: GitBranch):
        """
        Verify priority is serialized as string, not value object.
        Status: ✅ SHOULD PASS - Frontend expects string.
        """
        branch_dict = sample_git_branch.to_dict()

        assert "priority" in branch_dict, "Serialized branch must include priority"
        assert isinstance(branch_dict["priority"], str), "Serialized priority must be string"


class TestGitBranchAPIContractCompleteStructure:
    """Test that GitBranch matches complete frontend expectations."""

    def test_git_branch_matches_frontend_branch_interface(self, sample_git_branch: GitBranch):
        """
        Verify GitBranch entity includes ALL fields expected by frontend.

        Frontend Branch interface (from api.types.ts):
        - id: string (required)
        - project_id: string (required)
        - name: string (required)
        - git_branch_name: string (required)
        - description?: string
        - status?: string
        - is_active?: boolean
        - created_at?: string
        - updated_at?: string
        """
        # Required fields
        required_fields = [
            "id",
            "project_id",
            "name",
        ]

        for field in required_fields:
            assert hasattr(sample_git_branch, field), (
                f"GitBranch MUST have required field '{field}'"
            )

        # Common optional fields
        common_fields = [
            "git_branch_name",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]

        for field in common_fields:
            assert hasattr(sample_git_branch, field), (
                f"GitBranch should have common field '{field}'"
            )


class TestGitBranchAPIContractFrontendSummaryFields:
    """Test fields needed for BranchSummary frontend type."""

    def test_git_branch_provides_branch_summary_data(self, sample_git_branch: GitBranch):
        """
        Verify GitBranch can provide data for BranchSummary frontend type.

        Frontend BranchSummary (from api.types.ts):
        - id, project_id, name, git_branch_name
        - status?, priority?
        - task_count, completed_tasks, progress_percentage
        - in_progress_tasks, blocked_tasks, todo_tasks
        - last_activity?, has_urgent_tasks?, is_completed?
        """
        # Verify summary methods exist
        assert callable(getattr(sample_git_branch, "get_task_count", None)), (
            "GitBranch must have get_task_count method"
        )
        assert callable(getattr(sample_git_branch, "get_completed_task_count", None)), (
            "GitBranch must have get_completed_task_count method"
        )
        assert callable(getattr(sample_git_branch, "get_progress_percentage", None)), (
            "GitBranch must have get_progress_percentage method"
        )
        assert callable(getattr(sample_git_branch, "get_active_task_count", None)), (
            "GitBranch must have get_active_task_count method"
        )
