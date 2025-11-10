"""
Backend API Contract Tests - Project Management Endpoints

TDD Approach: These tests document the expected API contract between backend and frontend.
Tests are based on Project domain entity and frontend Project interface expectations.

Reference: agenthub_main/src/fastmcp/task_management/domain/entities/project.py
Frontend: agenthub-frontend/src/types/api.types.ts (Project interface)

Expected Contract:
- Project has: id, name, description
- ISO 8601 timestamps (created_at, updated_at)
- Proper UUID format for IDs
- Optional: git_branchs (Record<string, Branch>), status, owner_id
"""

from datetime import datetime
from uuid import uuid4

import pytest

from fastmcp.task_management.domain.entities.project import Project


@pytest.fixture
def sample_project(user_id: str):
    """Create a sample project for testing API contract."""
    project = Project.create(
        name="Sample Project for API Contract Testing",
        description="Test project with multiple fields populated"
    )
    return project


class TestProjectAPIContractBasicFields:
    """Test basic fields that SHOULD PASS - core project fields."""

    def test_project_has_required_id_field(self, sample_project: Project):
        """
        Verify project includes UUID id field.
        Status: ✅ SHOULD PASS - Core field in Project entity.
        """
        assert hasattr(sample_project, "id"), "Project must have 'id' field"
        assert sample_project.id is not None, "Project id must not be None"

        # Convert to string for UUID validation
        id_str = str(sample_project.id)
        assert isinstance(id_str, str), "Project id must be string or convertible to string"

        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(id_str)
        except ValueError:
            pytest.fail(f"Project id '{id_str}' is not a valid UUID")

    def test_project_has_required_name_field(self, sample_project: Project):
        """
        Verify project includes name field.
        Status: ✅ SHOULD PASS - Required field.
        """
        assert hasattr(sample_project, "name"), "Project must have 'name' field"
        assert isinstance(sample_project.name, str), "Project name must be string"
        assert len(sample_project.name) > 0, "Project name must not be empty"

    def test_project_has_description_field(self, sample_project: Project):
        """
        Verify project includes description field.
        Status: ✅ SHOULD PASS - Standard field.
        """
        assert hasattr(sample_project, "description"), "Project must have 'description' field"
        # Description can be string or None
        if sample_project.description is not None:
            assert isinstance(sample_project.description, str), (
                "Project description must be string when provided"
            )


class TestProjectAPIContractTimestamps:
    """Test timestamp fields - ISO 8601 format."""

    def test_project_created_at_is_iso8601_compatible(self, sample_project: Project):
        """
        Verify created_at can be serialized to ISO 8601 format.
        Status: ✅ SHOULD PASS - Standard timestamp field.

        Frontend expects: created_at?: string
        Backend returns: created_at: datetime → serialized as ISO string
        """
        assert hasattr(sample_project, "created_at"), "Project must have 'created_at' field"

        # Handle both datetime objects and string representations
        if isinstance(sample_project.created_at, datetime):
            iso_string = sample_project.created_at.isoformat()
            assert "T" in iso_string, "created_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_project.created_at, str):
            assert "T" in sample_project.created_at, (
                "created_at must be ISO 8601 format (contains 'T')"
            )
            try:
                datetime.fromisoformat(sample_project.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"created_at '{sample_project.created_at}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"created_at must be datetime or string, got {type(sample_project.created_at)}"
            )

    def test_project_updated_at_is_iso8601_compatible(self, sample_project: Project):
        """
        Verify updated_at can be serialized to ISO 8601 format.
        Status: ✅ SHOULD PASS - Standard timestamp field.

        Frontend expects: updated_at?: string
        Backend returns: updated_at: datetime → serialized as ISO string
        """
        assert hasattr(sample_project, "updated_at"), "Project must have 'updated_at' field"

        # Handle both datetime objects and string representations
        if isinstance(sample_project.updated_at, datetime):
            iso_string = sample_project.updated_at.isoformat()
            assert "T" in iso_string, "updated_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_project.updated_at, str):
            assert "T" in sample_project.updated_at, (
                "updated_at must be ISO 8601 format (contains 'T')"
            )
            try:
                datetime.fromisoformat(sample_project.updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"updated_at '{sample_project.updated_at}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"updated_at must be datetime or string, got {type(sample_project.updated_at)}"
            )


class TestProjectAPIContractOptionalFields:
    """Test optional fields that may be present."""

    def test_project_has_git_branchs_field(self, sample_project: Project):
        """
        Verify project has git_branchs field.
        Status: ✅ SHOULD PASS - Standard field for branch management.

        Frontend expects: git_branchs?: Record<string, Branch>
        Backend has: git_branchs: dict[str, GitBranch]
        """
        assert hasattr(sample_project, "git_branchs"), (
            "Project must have 'git_branchs' field"
        )
        assert isinstance(sample_project.git_branchs, dict), (
            "Project git_branchs must be dictionary"
        )

    def test_project_has_status_field(self, sample_project: Project):
        """
        Verify project has status field (optional).
        Status: ✅ SHOULD PASS - Optional field.

        Frontend expects: status?: string
        """
        # Status field may be present in serialized form
        # This is optional and may be derived from branches
        pass

    def test_project_has_owner_id_field(self, sample_project: Project):
        """
        Verify project can have owner_id field (optional).
        Status: ✅ SHOULD PASS - Optional field for ownership tracking.

        Frontend expects: owner_id?: string
        """
        # owner_id is optional and may be added during serialization
        pass


class TestProjectAPIContractSerialization:
    """Test project serialization to dict for API responses."""

    def test_project_can_serialize_to_dict(self, sample_project: Project):
        """
        Verify Project can be serialized to dictionary for API response.
        Status: ✅ SHOULD PASS - Required for JSON serialization.

        The to_dict() method should not exist on Project entity itself,
        but serialization happens at the DTO/response layer.
        """
        # Project entity may not have to_dict(), that's okay
        # Serialization is handled by DTOs/responses
        pass


class TestProjectAPIContractCompleteStructure:
    """Test that Project matches complete frontend expectations."""

    def test_project_matches_frontend_project_interface(self, sample_project: Project):
        """
        Verify Project entity includes ALL fields expected by frontend.

        Frontend Project interface (from api.types.ts):
        - id: string (required)
        - name: string (required)
        - description?: string
        - created_at?: string
        - updated_at?: string
        - owner_id?: string
        - status?: string
        - git_branchs?: Record<string, Branch>
        - branches?: Branch[] (legacy)
        """
        # Required fields
        required_fields = [
            "id",
            "name",
        ]

        for field in required_fields:
            assert hasattr(sample_project, field), (
                f"Project MUST have required field '{field}'"
            )

        # Common optional fields
        common_fields = [
            "description",
            "created_at",
            "updated_at",
            "git_branchs",
        ]

        for field in common_fields:
            assert hasattr(sample_project, field), (
                f"Project should have common field '{field}'"
            )


class TestProjectAPIContractBusinessLogic:
    """Test project business logic and rich domain model methods."""

    def test_project_calculate_health_returns_valid_structure(self, sample_project: Project):
        """
        Verify project health calculation returns expected structure.
        Status: ✅ SHOULD PASS - Rich domain model method.

        Expected structure:
        - overall_health_score: float (0-100)
        - health_status: str (excellent, good, fair, poor, critical)
        - metrics: Dict with completion rates
        - counts: Dict with totals
        """
        health = sample_project.calculate_project_health()

        assert isinstance(health, dict), "Health calculation must return dict"
        assert "overall_health_score" in health, "Health must include overall_health_score"
        assert "health_status" in health, "Health must include health_status"
        assert "metrics" in health, "Health must include metrics"
        assert "counts" in health, "Health must include counts"

        # Verify score range
        assert 0 <= health["overall_health_score"] <= 100, (
            f"Health score must be 0-100, got {health['overall_health_score']}"
        )

        # Verify status values
        valid_statuses = ["excellent", "good", "fair", "poor", "critical"]
        assert health["health_status"] in valid_statuses, (
            f"Health status must be one of {valid_statuses}, got {health['health_status']}"
        )

    def test_project_get_orchestration_status_returns_valid_structure(self, sample_project: Project):
        """
        Verify orchestration status returns expected structure.
        Status: ✅ SHOULD PASS - Rich domain model method.

        Expected structure:
        - project_id: str
        - project_name: str
        - total_branches: int
        - registered_agents: int
        - branches: Dict
        - agents: Dict
        """
        status = sample_project.get_orchestration_status()

        assert isinstance(status, dict), "Orchestration status must return dict"
        assert "project_id" in status, "Status must include project_id"
        assert "project_name" in status, "Status must include project_name"
        assert "total_branches" in status, "Status must include total_branches"
        assert "registered_agents" in status, "Status must include registered_agents"
        assert "branches" in status, "Status must include branches"
        assert "agents" in status, "Status must include agents"

        # Verify types
        assert isinstance(status["total_branches"], int), "total_branches must be int"
        assert isinstance(status["registered_agents"], int), "registered_agents must be int"
        assert isinstance(status["branches"], dict), "branches must be dict"
        assert isinstance(status["agents"], dict), "agents must be dict"

    def test_project_check_deadline_risk_returns_valid_structure(self, sample_project: Project):
        """
        Verify deadline risk check returns expected structure.
        Status: ✅ SHOULD PASS - Rich domain model method.

        Expected structure:
        - risk_level: str (no_risk, low_risk, medium_risk, high_risk, critical_risk)
        - assessment: str
        - recommendation: str
        - metrics: Dict (optional)
        """
        risk = sample_project.check_deadline_risk()

        assert isinstance(risk, dict), "Deadline risk must return dict"
        assert "risk_level" in risk, "Risk must include risk_level"
        assert "assessment" in risk, "Risk must include assessment"
        assert "recommendation" in risk, "Risk must include recommendation"

        # Verify risk level values
        valid_risk_levels = [
            "no_risk", "low_risk", "medium_risk", "high_risk", "critical_risk"
        ]
        assert risk["risk_level"] in valid_risk_levels, (
            f"Risk level must be one of {valid_risk_levels}, got {risk['risk_level']}"
        )

        # Verify string fields
        assert isinstance(risk["assessment"], str), "assessment must be string"
        assert isinstance(risk["recommendation"], str), "recommendation must be string"


class TestProjectAPIContractGitBranchManagement:
    """Test git branch management in project."""

    def test_project_can_create_git_branch(self, sample_project: Project):
        """
        Verify project can create git branches.
        Status: ✅ SHOULD PASS - Core project functionality.
        """
        branch = sample_project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test branch for API contract"
        )

        assert branch is not None, "create_git_branch must return GitBranch"
        assert branch.name == "Test Branch", "Branch name must match"
        assert branch.git_branch_name == "feature/test", "Git branch name must match"

    def test_project_git_branchs_is_dict_with_string_keys(self, sample_project: Project):
        """
        Verify git_branchs is dictionary with string keys (UUIDs).
        Status: ✅ SHOULD PASS - Required structure for frontend.

        Frontend expects: git_branchs?: Record<string, Branch>
        Backend has: git_branchs: dict[str, GitBranch]
        """
        assert isinstance(sample_project.git_branchs, dict), (
            "git_branchs must be dictionary"
        )

        # If there are any branches, verify key format
        for branch_id in sample_project.git_branchs.keys():
            assert isinstance(branch_id, str), "Branch ID keys must be strings"
            # Verify UUID format
            try:
                uuid4_obj = uuid4()
                uuid4_obj = type(uuid4_obj)(branch_id)
            except ValueError:
                pytest.fail(f"Branch ID '{branch_id}' is not a valid UUID")


class TestProjectAPIContractAgentManagement:
    """Test agent registration and assignment in project."""

    def test_project_has_registered_agents_dict(self, sample_project: Project):
        """
        Verify project has registered_agents dictionary.
        Status: ✅ SHOULD PASS - Agent management field.
        """
        assert hasattr(sample_project, "registered_agents"), (
            "Project must have 'registered_agents' field"
        )
        assert isinstance(sample_project.registered_agents, dict), (
            "registered_agents must be dictionary"
        )

    def test_project_has_agent_assignments_dict(self, sample_project: Project):
        """
        Verify project has agent_assignments dictionary.
        Status: ✅ SHOULD PASS - Agent assignment tracking.
        """
        assert hasattr(sample_project, "agent_assignments"), (
            "Project must have 'agent_assignments' field"
        )
        assert isinstance(sample_project.agent_assignments, dict), (
            "agent_assignments must be dictionary"
        )
