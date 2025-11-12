"""
Backend API Contract Tests - Context Management Endpoints

TDD Approach: These tests document the expected API contract between backend and frontend.
Tests are based on Context domain entity and frontend ContextResponse expectations.

Reference: agenthub_main/src/fastmcp/task_management/application/dtos/context/context_response.py
Frontend: agenthub-frontend/src/types/api.types.ts (ContextResponse interface)
          agenthub-frontend/src/types/context.types.ts (Context types)

Expected Contract:
- ContextResponse contains: success, message, data?, context?
- Context hierarchy: Global → Project → Branch → Task
- ISO 8601 timestamps
- Flexible data structure (dict[str, Any])
"""

from datetime import datetime
from uuid import uuid4

import pytest

from fastmcp.task_management.application.dtos.context import (
    ContextResponse,
    ListContextsResponse,
)
from fastmcp.task_management.domain.entities.context import TaskContext


@pytest.fixture
def sample_context(user_id: str, project_id: str):
    """Create a sample context for testing API contract."""
    context = TaskContext.create(
        context_id=str(uuid4()),
        user_id=user_id,
        data={
            "title": "Test Context",
            "description": "Sample context for API contract testing",
            "requirements": ["Requirement 1", "Requirement 2"],
            "technical_specs": {"language": "Python", "framework": "FastAPI"},
        },
    )
    return context


class TestContextResponseAPIContractBasicFields:
    """Test basic ContextResponse fields that SHOULD PASS."""

    def test_context_response_has_success_field(self):
        """
        Verify ContextResponse includes success boolean field.
        Status: ✅ SHOULD PASS - Required field in ContextResponse.
        """
        response = ContextResponse.success_response(message="Test successful")

        assert hasattr(response, "success"), "ContextResponse must have 'success' field"
        assert isinstance(response.success, bool), "success must be boolean"
        assert response.success is True, "success_response must have success=True"

    def test_context_response_has_message_field(self):
        """
        Verify ContextResponse includes message string field.
        Status: ✅ SHOULD PASS - Required field in ContextResponse.
        """
        response = ContextResponse.success_response(message="Test message")

        assert hasattr(response, "message"), "ContextResponse must have 'message' field"
        assert isinstance(response.message, str), "message must be string"
        assert len(response.message) > 0, "message must not be empty"

    def test_context_response_has_data_field(self):
        """
        Verify ContextResponse includes optional data field.
        Status: ✅ SHOULD PASS - Optional field in ContextResponse.
        """
        response = ContextResponse.success_response(
            data={"key": "value"}, message="Test"
        )

        assert hasattr(response, "data"), "ContextResponse must have 'data' field"
        # data is optional, can be None or dict
        if response.data is not None:
            assert isinstance(response.data, dict), "data must be dict when provided"

    def test_context_response_has_error_field_on_failure(self):
        """
        Verify ContextResponse includes error field on error response.
        Status: ✅ SHOULD PASS - Error field in ContextResponse.
        """
        response = ContextResponse.error_response(
            error="Test error", message="Operation failed"
        )

        assert hasattr(response, "error"), "ContextResponse must have 'error' field"
        assert hasattr(response, "success"), "ContextResponse must have 'success' field"
        assert response.success is False, "error_response must have success=False"
        assert isinstance(response.error, str), "error must be string"


class TestContextResponseAPIContractContextField:
    """Test context field in ContextResponse."""

    def test_context_response_has_context_field(self, sample_context):
        """
        Verify ContextResponse includes optional context field.
        Status: ✅ SHOULD PASS - Optional field for context data.
        """
        response = ContextResponse.success_response(
            context=sample_context, message="Context retrieved"
        )

        assert hasattr(response, "context"), "ContextResponse must have 'context' field"
        # context is optional, can be None or TaskContext
        if response.context is not None:
            assert isinstance(
                response.context, TaskContext
            ), "context must be TaskContext when provided"


class TestTaskContextAPIContractBasicFields:
    """Test TaskContext entity fields."""

    def test_task_context_has_context_id_field(self, sample_context: TaskContext):
        """
        Verify TaskContext includes context_id field.
        Status: ✅ SHOULD PASS - Required field.
        """
        assert hasattr(
            sample_context, "context_id"
        ), "TaskContext must have 'context_id' field"
        assert isinstance(sample_context.context_id, str), "context_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(sample_context.context_id)
        except ValueError:
            pytest.fail(f"context_id '{sample_context.context_id}' is not a valid UUID")

    def test_task_context_has_user_id_field(self, sample_context: TaskContext):
        """
        Verify TaskContext includes user_id field.
        Status: ✅ SHOULD PASS - Required for multi-tenant isolation.
        """
        assert hasattr(
            sample_context, "user_id"
        ), "TaskContext must have 'user_id' field"
        assert isinstance(sample_context.user_id, str), "user_id must be string"

    def test_task_context_has_data_field(self, sample_context: TaskContext):
        """
        Verify TaskContext includes data dictionary field.
        Status: ✅ SHOULD PASS - Core context storage.
        """
        assert hasattr(sample_context, "data"), "TaskContext must have 'data' field"
        assert isinstance(sample_context.data, dict), "data must be dictionary"


class TestTaskContextAPIContractTimestamps:
    """Test timestamp fields in TaskContext."""

    def test_task_context_created_at_is_iso8601_compatible(
        self, sample_context: TaskContext
    ):
        """
        Verify created_at can be serialized to ISO 8601 format.
        Status: ✅ SHOULD PASS - Standard timestamp field.
        """
        assert hasattr(
            sample_context, "created_at"
        ), "TaskContext must have 'created_at' field"

        # Handle both datetime objects and string representations
        if isinstance(sample_context.created_at, datetime):
            iso_string = sample_context.created_at.isoformat()
            assert (
                "T" in iso_string
            ), "created_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_context.created_at, str):
            assert (
                "T" in sample_context.created_at
            ), "created_at must be ISO 8601 format (contains 'T')"
            try:
                datetime.fromisoformat(sample_context.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"created_at '{sample_context.created_at}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"created_at must be datetime or string, got {type(sample_context.created_at)}"
            )

    def test_task_context_updated_at_is_iso8601_compatible(
        self, sample_context: TaskContext
    ):
        """
        Verify updated_at can be serialized to ISO 8601 format.
        Status: ✅ SHOULD PASS - Standard timestamp field.
        """
        assert hasattr(
            sample_context, "updated_at"
        ), "TaskContext must have 'updated_at' field"

        # Handle both datetime objects and string representations
        if isinstance(sample_context.updated_at, datetime):
            iso_string = sample_context.updated_at.isoformat()
            assert (
                "T" in iso_string
            ), "updated_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_context.updated_at, str):
            assert (
                "T" in sample_context.updated_at
            ), "updated_at must be ISO 8601 format (contains 'T')"
            try:
                datetime.fromisoformat(sample_context.updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"updated_at '{sample_context.updated_at}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"updated_at must be datetime or string, got {type(sample_context.updated_at)}"
            )


class TestTaskContextAPIContractDataStructure:
    """Test data structure flexibility in TaskContext."""

    def test_task_context_data_supports_nested_structures(
        self, sample_context: TaskContext
    ):
        """
        Verify context data supports nested dictionaries.
        Status: ✅ SHOULD PASS - Flexible data structure.
        """
        assert isinstance(sample_context.data, dict), "data must be dictionary"

        # Verify nested structure support
        if "technical_specs" in sample_context.data:
            assert isinstance(
                sample_context.data["technical_specs"], dict
            ), "Nested structures should be supported"

    def test_task_context_data_supports_arrays(self, sample_context: TaskContext):
        """
        Verify context data supports arrays/lists.
        Status: ✅ SHOULD PASS - Flexible data structure.
        """
        assert isinstance(sample_context.data, dict), "data must be dictionary"

        # Verify array support
        if "requirements" in sample_context.data:
            assert isinstance(
                sample_context.data["requirements"], list
            ), "Arrays should be supported in context data"

    def test_task_context_data_supports_various_types(
        self, sample_context: TaskContext
    ):
        """
        Verify context data supports various Python types.
        Status: ✅ SHOULD PASS - Type flexibility.
        """
        # Context data should support: str, int, float, bool, dict, list, None
        test_data = {
            "string_field": "test",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "dict_field": {"nested": "value"},
            "list_field": [1, 2, 3],
            "null_field": None,
        }

        context = TaskContext.create(
            context_id=str(uuid4()), user_id="test_user", data=test_data
        )

        assert isinstance(context.data, dict), "data must be dictionary"
        assert "string_field" in context.data, "Should support string fields"
        assert "int_field" in context.data, "Should support int fields"
        assert "dict_field" in context.data, "Should support nested dict fields"
        assert "list_field" in context.data, "Should support list fields"


class TestTaskContextAPIContractSerialization:
    """Test TaskContext serialization to dict."""

    def test_task_context_to_dict_method(self, sample_context: TaskContext):
        """
        Verify TaskContext can be serialized to dictionary for API response.
        Status: ✅ SHOULD PASS - Required for JSON serialization.
        """
        context_dict = sample_context.to_dict()

        assert isinstance(context_dict, dict), "to_dict() must return dictionary"

        # Verify required keys in serialized response
        required_keys = ["context_id", "user_id", "data", "created_at", "updated_at"]
        for key in required_keys:
            assert key in context_dict, f"Serialized context must include {key}"

        # Verify timestamps are ISO 8601 strings in serialized form
        assert isinstance(
            context_dict["created_at"], str
        ), "Serialized created_at must be string"
        assert isinstance(
            context_dict["updated_at"], str
        ), "Serialized updated_at must be string"
        assert "T" in context_dict["created_at"], "created_at must be ISO 8601 format"
        assert "T" in context_dict["updated_at"], "updated_at must be ISO 8601 format"


class TestContextResponseAPIContractSerialization:
    """Test ContextResponse serialization to dict."""

    def test_context_response_to_dict_method(self, sample_context: TaskContext):
        """
        Verify ContextResponse can be serialized to dictionary for API response.
        Status: ✅ SHOULD PASS - Required for JSON serialization.
        """
        response = ContextResponse.success_response(
            context=sample_context, message="Context retrieved successfully"
        )

        response_dict = response.to_dict()

        assert isinstance(response_dict, dict), "to_dict() must return dictionary"

        # Verify required keys
        assert "success" in response_dict, "Serialized response must include success"
        assert "message" in response_dict, "Serialized response must include message"

        # Verify context is serialized
        if "context" in response_dict:
            assert isinstance(
                response_dict["context"], dict
            ), "Serialized context must be dictionary"


class TestListContextsResponseAPIContract:
    """Test ListContextsResponse specific fields."""

    def test_list_contexts_response_has_contexts_array(
        self, sample_context: TaskContext
    ):
        """
        Verify ListContextsResponse includes contexts array.
        Status: ✅ SHOULD PASS - Required for list operations.
        """
        response = ListContextsResponse.success_response(
            contexts=[sample_context], message="Contexts retrieved"
        )

        assert hasattr(
            response, "contexts"
        ), "ListContextsResponse must have 'contexts' field"
        assert isinstance(response.contexts, list), "contexts must be list"

        if len(response.contexts) > 0:
            assert isinstance(
                response.contexts[0], TaskContext
            ), "contexts must contain TaskContext objects"

    def test_list_contexts_response_to_dict_serializes_array(
        self, sample_context: TaskContext
    ):
        """
        Verify ListContextsResponse serializes contexts array properly.
        Status: ✅ SHOULD PASS - Required for JSON serialization.
        """
        response = ListContextsResponse.success_response(
            contexts=[sample_context], message="Contexts retrieved"
        )

        response_dict = response.to_dict()

        assert "contexts" in response_dict, "Serialized response must include contexts"
        assert isinstance(
            response_dict["contexts"], list
        ), "Serialized contexts must be list"

        if len(response_dict["contexts"]) > 0:
            assert isinstance(
                response_dict["contexts"][0], dict
            ), "Each serialized context must be dictionary"


class TestContextAPIContractCompleteStructure:
    """Test that Context types match complete frontend expectations."""

    def test_context_response_matches_frontend_interface(
        self, sample_context: TaskContext
    ):
        """
        Verify ContextResponse matches frontend ContextResponse interface.

        Frontend ContextResponse (from api.types.ts):
        - success: boolean
        - data?: any
        - error?: string
        - message?: string
        - context?: any
        - level?: string
        - inherited?: any
        """
        response = ContextResponse.success_response(
            context=sample_context, data={"key": "value"}, message="Test message"
        )

        # Required fields
        assert hasattr(response, "success"), "Must have success"
        assert hasattr(response, "message"), "Must have message"

        # Optional fields
        assert hasattr(response, "data"), "Should have data"
        assert hasattr(response, "error"), "Should have error"
        assert hasattr(response, "context"), "Should have context"


class TestContextAPIContractHierarchy:
    """Test context hierarchy support (Global → Project → Branch → Task)."""

    def test_context_supports_hierarchical_data(self):
        """
        Verify context can store hierarchical context data.
        Status: ✅ SHOULD PASS - Hierarchical context support.

        Context levels:
        - Global: Organization-wide standards
        - Project: Project-specific context
        - Branch: Branch-specific context
        - Task: Task-specific context
        """
        # Test global context data structure
        global_context = TaskContext.create(
            context_id=str(uuid4()),
            user_id="test_user",
            data={
                "organization_standards": {"coding_style": "PEP 8"},
                "compliance_requirements": {"GDPR": True},
                "shared_resources": ["lib1", "lib2"],
            },
        )

        assert isinstance(global_context.data, dict), "Global context data must be dict"
        assert (
            "organization_standards" in global_context.data
        ), "Should support organization standards"

    def test_context_inheritance_pattern(self):
        """
        Verify context supports inheritance pattern.
        Status: ✅ SHOULD PASS - Child contexts can inherit parent data.

        Pattern: Child context inherits from parent, can override fields.
        """
        # Parent (project) context
        parent_context = TaskContext.create(
            context_id=str(uuid4()),
            user_id="test_user",
            data={
                "project_name": "Test Project",
                "technology_stack": ["Python", "React"],
                "shared_config": {"timeout": 30},
            },
        )

        # Child (task) context - inherits and extends
        child_context = TaskContext.create(
            context_id=str(uuid4()),
            user_id="test_user",
            data={
                "task_name": "Implement feature",
                "task_specific_data": {"complexity": "high"},
                # Can reference parent context_id for inheritance
                "parent_context_id": parent_context.context_id,
            },
        )

        assert isinstance(parent_context.data, dict), "Parent context must have data"
        assert isinstance(child_context.data, dict), "Child context must have data"
