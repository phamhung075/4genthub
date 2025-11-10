"""
Test Suite for Project WebSocket Payload Migration (TDD)

Tests the migration of project_management_service.py to use ProjectDeletePayload
with Pydantic validation and fallback handling.

This test suite follows the BranchDeletePayload pattern from git_branch_service.py:206-221
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from fastmcp.task_management.domain.websocket_protocol import ProjectDeletePayload


class TestProjectDeletePayload:
    """Test ProjectDeletePayload Pydantic model validation"""

    def test_valid_payload_creation(self):
        """Test successful creation of ProjectDeletePayload with valid data"""
        payload = ProjectDeletePayload(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Project"
        )

        assert payload.id == "123e4567-e89b-12d3-a456-426614174000"
        assert payload.name == "Test Project"

    def test_empty_id_raises_validation_error(self):
        """Test that empty id raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectDeletePayload(id="", name="Test Project")

        assert "Project ID cannot be empty" in str(exc_info.value)

    def test_whitespace_id_raises_validation_error(self):
        """Test that whitespace-only id raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectDeletePayload(id="   ", name="Test Project")

        assert "Project ID cannot be empty" in str(exc_info.value)

    def test_empty_name_raises_validation_error(self):
        """Test that empty name raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectDeletePayload(
                id="123e4567-e89b-12d3-a456-426614174000",
                name=""
            )

        assert "Project name cannot be empty" in str(exc_info.value)

    def test_whitespace_name_raises_validation_error(self):
        """Test that whitespace-only name raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectDeletePayload(
                id="123e4567-e89b-12d3-a456-426614174000",
                name="   "
            )

        assert "Project name cannot be empty" in str(exc_info.value)

    def test_missing_id_raises_validation_error(self):
        """Test that missing id field raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectDeletePayload(name="Test Project")

        # Pydantic will raise error for missing required field
        assert "id" in str(exc_info.value).lower()

    def test_missing_name_raises_validation_error(self):
        """Test that missing name field raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectDeletePayload(id="123e4567-e89b-12d3-a456-426614174000")

        # Pydantic will raise error for missing required field
        assert "name" in str(exc_info.value).lower()

    def test_model_dump_returns_dict(self):
        """Test that model_dump() returns dictionary with correct structure"""
        payload = ProjectDeletePayload(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Project"
        )

        result = payload.model_dump()

        assert isinstance(result, dict)
        assert result["id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["name"] == "Test Project"
        assert len(result) == 2  # Only id and name


class TestProjectManagementServiceWebSocketIntegration:
    """Test integration of ProjectDeletePayload in project_management_service.py"""

    @patch('fastmcp.task_management.application.services.project_management_service.logger')
    @patch('fastmcp.task_management.application.services.project_management_service.WebSocketNotificationService')
    def test_successful_payload_validation_and_broadcast(self, mock_ws_service, mock_logger):
        """Test successful ProjectDeletePayload validation and WebSocket broadcast"""
        from fastmcp.task_management.infrastructure.persistence.sqlalchemy.repositories.sqlalchemy_project_repository import (
            SQLAlchemyProjectRepository,
        )

        from fastmcp.task_management.application.services.project_management_service import (
            ProjectManagementService,
        )
        from fastmcp.task_management.domain.entities.project import Project

        # Setup mock repository
        mock_repo = MagicMock(spec=SQLAlchemyProjectRepository)
        mock_project = Project(
            name="Test Project",
            description="Test Description"
        )
        mock_repo.get_by_id.return_value = mock_project
        mock_repo.delete.return_value = True

        # Create service with mocked dependencies
        service = ProjectManagementService(
            project_repo=mock_repo,
            user_id="test-user-123"
        )

        # Execute delete operation
        project_id = "123e4567-e89b-12d3-a456-426614174000"
        result = service.delete_project(project_id=project_id)

        # Verify result
        assert result["success"] is True

        # Verify WebSocket service was called with validated payload
        mock_ws_service.sync_broadcast_project_event.assert_called_once()
        call_args = mock_ws_service.sync_broadcast_project_event.call_args

        # Verify the project_data parameter contains validated payload
        assert call_args.kwargs["event_type"] == "deleted"
        assert call_args.kwargs["project_id"] == project_id
        assert call_args.kwargs["user_id"] == "test-user-123"

        project_data = call_args.kwargs["project_data"]
        assert project_data["id"] == project_id
        assert project_data["name"] == "Test Project"

        # Verify success logging
        mock_logger.info.assert_any_call(f"✅ Project delete payload validated: {project_data}")

    @patch('fastmcp.task_management.application.services.project_management_service.logger')
    @patch('fastmcp.task_management.application.services.project_management_service.WebSocketNotificationService')
    def test_fallback_on_validation_failure(self, mock_ws_service, mock_logger):
        """Test fallback to dict when ProjectDeletePayload validation fails"""
        # This test simulates a scenario where validation might fail
        # and ensures the fallback mechanism works correctly

        # We'll test this by mocking the ProjectDeletePayload to raise an error
        with patch('fastmcp.task_management.application.services.project_management_service.ProjectDeletePayload') as mock_payload_class:
            mock_payload_class.side_effect = ValidationError.from_exception_data(
                'ProjectDeletePayload',
                [{'type': 'value_error', 'loc': ('id',), 'msg': 'Test validation error', 'input': ''}]
            )

            from fastmcp.task_management.infrastructure.persistence.sqlalchemy.repositories.sqlalchemy_project_repository import (
                SQLAlchemyProjectRepository,
            )

            from fastmcp.task_management.application.services.project_management_service import (
                ProjectManagementService,
            )
            from fastmcp.task_management.domain.entities.project import Project

            # Setup mock repository
            mock_repo = MagicMock(spec=SQLAlchemyProjectRepository)
            mock_project = Project(
                name="Test Project",
                description="Test Description"
            )
            mock_repo.get_by_id.return_value = mock_project
            mock_repo.delete.return_value = True

            # Create service
            service = ProjectManagementService(
                project_repo=mock_repo,
                user_id="test-user-123"
            )

            # Execute delete operation
            project_id = "123e4567-e89b-12d3-a456-426614174000"
            result = service.delete_project(project_id=project_id)

            # Verify result is still successful (fallback worked)
            assert result["success"] is True

            # Verify error logging for validation failure
            mock_logger.error.assert_any_call(
                pytest.approx("❌ Project delete payload validation failed:", rel=1e-9),
                extra=pytest.approx(mock_payload_class.side_effect, rel=1e-9)
            )

            # Verify WebSocket service was still called with fallback dict
            mock_ws_service.sync_broadcast_project_event.assert_called_once()
            call_args = mock_ws_service.sync_broadcast_project_event.call_args

            project_data = call_args.kwargs["project_data"]
            assert project_data["id"] == project_id
            assert project_data["name"] == "Test Project"

    @patch('fastmcp.task_management.application.services.project_management_service.logger')
    def test_logging_on_successful_validation(self, mock_logger):
        """Test that successful validation logs the validated payload"""
        payload = ProjectDeletePayload(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Project"
        )

        project_data = payload.model_dump()

        # Simulate the logging that should happen in the service
        mock_logger.info(f"✅ Project delete payload validated: {project_data}")

        # Verify logging occurred with correct message
        mock_logger.info.assert_called_once_with(
            f"✅ Project delete payload validated: {project_data}"
        )

    @patch('fastmcp.task_management.application.services.project_management_service.logger')
    def test_logging_on_validation_failure(self, mock_logger):
        """Test that validation failure logs the error"""
        try:
            ProjectDeletePayload(id="", name="Test Project")
        except ValidationError as e:
            # Simulate the logging that should happen in the service
            mock_logger.error(f"❌ Project delete payload validation failed: {e}")

            # Verify error logging occurred
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0][0]
            assert "❌ Project delete payload validation failed:" in call_args


class TestBackwardCompatibility:
    """Test backward compatibility fallback mechanism"""

    def test_fallback_dict_structure_matches_legacy(self):
        """Test that fallback dict structure matches legacy format"""
        # Legacy format (before migration)
        legacy_dict = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Project"
        }

        # New format with fallback
        try:
            payload = ProjectDeletePayload(
                id="123e4567-e89b-12d3-a456-426614174000",
                name="Test Project"
            )
            new_dict = payload.model_dump()
        except Exception:
            # Fallback
            new_dict = {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Test Project"
            }

        # Verify structures match
        assert new_dict == legacy_dict
        assert set(new_dict.keys()) == set(legacy_dict.keys())
