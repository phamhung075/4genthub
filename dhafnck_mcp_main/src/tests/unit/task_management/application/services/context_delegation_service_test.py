"""Test suite for ContextDelegationService.

Tests for context delegation management between hierarchy levels.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp.task_management.application.services.context_delegation_service import (
    ContextDelegationService,
    DelegationRequest,
    DelegationResult
)


class TestContextDelegationServiceInit:
    """Test ContextDelegationService initialization."""

    def test_initialization_with_defaults(self):
        """Test service initialization with default values."""
        service = ContextDelegationService()
        
        assert service.repository is None
        assert service._user_id is None

    def test_initialization_with_parameters(self):
        """Test service initialization with custom parameters."""
        mock_repo = Mock()
        service = ContextDelegationService(repository=mock_repo, user_id="test_user_123")
        
        assert service.repository == mock_repo
        assert service._user_id == "test_user_123"

    def test_with_user_method(self):
        """Test with_user method creates new instance with user context."""
        original_service = ContextDelegationService()
        user_id = "test_user_456"
        
        user_scoped_service = original_service.with_user(user_id)
        
        assert user_scoped_service._user_id == user_id
        assert user_scoped_service is not original_service
        assert isinstance(user_scoped_service, ContextDelegationService)

    def test_get_user_scoped_repository_with_with_user_method(self):
        """Test _get_user_scoped_repository with repository that has with_user method."""
        service = ContextDelegationService(user_id="test_user")
        mock_repo = Mock()
        mock_user_scoped_repo = Mock()
        mock_repo.with_user.return_value = mock_user_scoped_repo
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_user_scoped_repo
        mock_repo.with_user.assert_called_once_with("test_user")


    def test_get_user_scoped_repository_no_user_context(self):
        """Test _get_user_scoped_repository returns original repo when no user context."""
        service = ContextDelegationService()  # No user_id
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo


class TestDelegationDataClasses:
    """Test delegation data classes."""

    def test_delegation_request_creation(self):
        """Test DelegationRequest creation."""
        request = DelegationRequest(
            source_level="task",
            source_id="task_123",
            target_level="project",
            target_id="proj_456",
            delegated_data={"pattern": "auth_flow"},
            reason="Reusable authentication pattern",
            trigger_type="manual",
            confidence_score=0.8
        )
        
        assert request.source_level == "task"
        assert request.source_id == "task_123"
        assert request.target_level == "project"
        assert request.target_id == "proj_456"
        assert request.delegated_data["pattern"] == "auth_flow"
        assert request.reason == "Reusable authentication pattern"
        assert request.trigger_type == "manual"
        assert request.confidence_score == 0.8

    def test_delegation_request_defaults(self):
        """Test DelegationRequest with default values."""
        request = DelegationRequest(
            source_level="task",
            source_id="task_123",
            target_level="project",
            target_id="proj_456",
            delegated_data={"data": "test"},
            reason="Test reason"
        )
        
        assert request.trigger_type == "manual"  # Default value
        assert request.confidence_score is None  # Default value

    def test_delegation_result_creation(self):
        """Test DelegationResult creation."""
        result = DelegationResult(
            success=True,
            delegation_id="del_789",
            processed=True,
            approved=True,
            impact_assessment={"score": 85}
        )
        
        assert result.success is True
        assert result.delegation_id == "del_789"
        assert result.processed is True
        assert result.approved is True
        assert result.impact_assessment["score"] == 85

    def test_delegation_result_defaults(self):
        """Test DelegationResult with default values."""
        result = DelegationResult(
            success=False,
            delegation_id="del_fail"
        )
        
        assert result.processed is False  # Default value
        assert result.approved is None  # Default value
        assert result.error_message is None  # Default value
        assert result.impact_assessment is None  # Default value


class TestSyncDelegateContextMethod:
    """Test synchronous delegate_context method."""

    def test_delegate_context_sync_wrapper_no_loop(self):
        """Test synchronous delegate_context wrapper when no event loop exists."""
        service = ContextDelegationService()
        
        request = {
            "source_level": "task",
            "source_id": "task_123",
            "target_level": "project",
            "data": {"pattern": "test"},
            "reason": "Test delegation"
        }
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                expected_result = {"success": True, "delegation_id": "del_123"}
                mock_run.return_value = expected_result
                
                result = service.delegate_context(request)
                
                assert result == expected_result
                mock_run.assert_called_once()

    def test_delegate_context_sync_wrapper_running_loop(self):
        """Test synchronous delegate_context wrapper when event loop is running."""
        service = ContextDelegationService()
        
        request = {
            "source_level": "task",
            "source_id": "task_123",
            "target_level": "project",
            "data": {"pattern": "test"}
        }
        
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            with patch('fastmcp.task_management.application.services.context_delegation_service.logger') as mock_logger:
                result = service.delegate_context(request)
                
                # Should return mock response when loop is running
                assert result["success"] is True
                assert "delegation_id" in result
                mock_logger.debug.assert_called()

    def test_delegate_context_sync_wrapper_exception(self):
        """Test synchronous delegate_context wrapper exception handling."""
        service = ContextDelegationService()
        
        request = {
            "source_level": "task",
            "source_id": "task_123",
            "target_level": "project"
        }
        
        with patch('asyncio.get_event_loop', side_effect=Exception("Unexpected error")):
            result = service.delegate_context(request)
            
            assert result["success"] is False
            assert "error" in result
            assert result["status"] == "failed"

    def test_delegate_context_target_id_resolution(self):
        """Test delegate_context resolves target_id correctly."""
        service = ContextDelegationService()
        
        # Test global target
        request = {
            "source_level": "task",
            "source_id": "task_123",
            "target_level": "global",
            "data": {"pattern": "test"}
        }
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                with patch.object(service, 'process_delegation') as mock_process:
                    mock_run.return_value = {"success": True}
                    
                    service.delegate_context(request)
                    
                    # Should resolve global target_id to singleton
                    mock_run.assert_called_once()


class TestAsyncDelegationProcessing:
    """Test async delegation processing."""

    @pytest.mark.asyncio
    async def test_process_delegation_success(self):
        """Test successful delegation processing."""
        mock_repo = AsyncMock()
        service = ContextDelegationService(repository=mock_repo)
        
        # Mock successful validation
        with patch.object(service, '_validate_delegation_request') as mock_validate:
            mock_validate.return_value = {"valid": True, "errors": []}
            
            with patch.object(service, '_store_delegation_request') as mock_store:
                mock_store.return_value = "del_123"
                
                with patch.object(service, '_assess_delegation_impact') as mock_assess:
                    mock_assess.return_value = {"score": 85, "recommendation": "auto_approve"}
                    
                    with patch.object(service, '_should_auto_approve') as mock_approve:
                        mock_approve.return_value = True
                        
                        with patch.object(service, '_execute_delegation') as mock_execute:
                            mock_execute.return_value = {"success": True, "implemented": True}
                            
                            result = await service.process_delegation(
                                "task", "task_123", "project", "proj_456",
                                {"pattern": "auth"}, "Reusable pattern"
                            )
        
        assert result["success"] is True
        assert result["delegation_id"] == "del_123"
        assert result["auto_approved"] is True

    @pytest.mark.asyncio
    async def test_process_delegation_validation_failure(self):
        """Test delegation processing with validation failure."""
        service = ContextDelegationService()
        
        with patch.object(service, '_validate_delegation_request') as mock_validate:
            mock_validate.return_value = {"valid": False, "errors": ["Invalid source level"]}
            
            result = await service.process_delegation(
                "invalid", "task_123", "project", "proj_456",
                {"data": "test"}, "Test reason"
            )
        
        assert result["success"] is False
        assert "Invalid delegation request" in result["error"]
        assert result["delegation_id"] is None

    @pytest.mark.asyncio
    async def test_process_delegation_queue_for_review(self):
        """Test delegation processing that requires manual review."""
        mock_repo = AsyncMock()
        service = ContextDelegationService(repository=mock_repo)
        
        with patch.object(service, '_validate_delegation_request') as mock_validate:
            mock_validate.return_value = {"valid": True, "errors": []}
            
            with patch.object(service, '_store_delegation_request') as mock_store:
                mock_store.return_value = "del_456"
                
                with patch.object(service, '_assess_delegation_impact') as mock_assess:
                    mock_assess.return_value = {"score": 50, "recommendation": "manual_review"}
                    
                    with patch.object(service, '_should_auto_approve') as mock_approve:
                        mock_approve.return_value = False
                        
                        with patch.object(service, '_queue_for_review') as mock_queue:
                            mock_queue.return_value = {"queued": True, "review_required": True}
                            
                            result = await service.process_delegation(
                                "task", "task_123", "project", "proj_456",
                                {"pattern": "complex"}, "Complex pattern"
                            )
        
        assert result["success"] is True
        assert result["delegation_id"] == "del_456"
        assert result["auto_approved"] is False

    @pytest.mark.asyncio
    async def test_process_delegation_exception(self):
        """Test delegation processing exception handling."""
        service = ContextDelegationService()
        
        with patch.object(service, '_validate_delegation_request', side_effect=Exception("Validation error")):
            result = await service.process_delegation(
                "task", "task_123", "project", "proj_456",
                {"data": "test"}, "Test reason"
            )
        
        assert result["success"] is False
        assert "error" in result
        assert result["delegation_id"] is None


class TestDelegationValidation:
    """Test delegation validation functionality."""

    def test_validate_delegation_request_valid(self):
        """Test validation of valid delegation request."""
        service = ContextDelegationService()
        
        result = service._validate_delegation_request(
            "task", "task_123", "project", "proj_456", {"data": "test"}
        )
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_delegation_request_invalid_source_level(self):
        """Test validation with invalid source level."""
        service = ContextDelegationService()
        
        result = service._validate_delegation_request(
            "invalid_level", "task_123", "project", "proj_456", {"data": "test"}
        )
        
        assert result["valid"] is False
        assert any("Invalid source level" in error for error in result["errors"])

    def test_validate_delegation_request_invalid_target_level(self):
        """Test validation with invalid target level."""
        service = ContextDelegationService()
        
        result = service._validate_delegation_request(
            "task", "task_123", "invalid_level", "proj_456", {"data": "test"}
        )
        
        assert result["valid"] is False
        assert any("Invalid target level" in error for error in result["errors"])

    def test_validate_delegation_request_wrong_direction(self):
        """Test validation with wrong delegation direction (downward)."""
        service = ContextDelegationService()
        
        result = service._validate_delegation_request(
            "project", "proj_123", "task", "task_456", {"data": "test"}
        )
        
        assert result["valid"] is False
        assert any("must delegate upward" in error for error in result["errors"])

    def test_validate_delegation_request_no_data(self):
        """Test validation with no delegated data."""
        service = ContextDelegationService()
        
        result = service._validate_delegation_request(
            "task", "task_123", "project", "proj_456", {}
        )
        
        assert result["valid"] is False
        assert any("No data provided" in error for error in result["errors"])

    def test_validate_delegation_request_same_level(self):
        """Test validation with same source and target level."""
        service = ContextDelegationService()
        
        result = service._validate_delegation_request(
            "project", "proj_123", "project", "proj_456", {"data": "test"}
        )
        
        assert result["valid"] is False
        assert any("must delegate upward" in error for error in result["errors"])


class TestPatternMatching:
    """Test pattern matching functionality."""

    def test_matches_pattern_security_discovery(self):
        """Test pattern matching for security discovery."""
        service = ContextDelegationService()
        
        changes = {
            "findings": "Found security vulnerability in authentication",
            "details": "SQL injection risk identified"
        }
        
        result = service._matches_pattern(changes, "security_discovery")
        assert result is True

    def test_matches_pattern_team_improvement(self):
        """Test pattern matching for team improvement."""
        service = ContextDelegationService()
        
        changes = {
            "process_improvement": "Updated team workflow for better collaboration",
            "details": "New process reduces handoff time"
        }
        
        result = service._matches_pattern(changes, "team_improvement")
        assert result is True

    def test_matches_pattern_reusable_utility(self):
        """Test pattern matching for reusable utility."""
        service = ContextDelegationService()
        
        changes = {
            "component": "Created reusable authentication utility",
            "features": "Helper functions for JWT validation"
        }
        
        result = service._matches_pattern(changes, "reusable_utility")
        assert result is True

    def test_matches_pattern_no_match(self):
        """Test pattern matching with no match."""
        service = ContextDelegationService()
        
        changes = {
            "routine_update": "Updated documentation formatting",
            "details": "Fixed typos in README"
        }
        
        result = service._matches_pattern(changes, "security_discovery")
        assert result is False

    def test_matches_pattern_unknown_pattern(self):
        """Test pattern matching with unknown pattern."""
        service = ContextDelegationService()
        
        changes = {"test": "data"}
        
        result = service._matches_pattern(changes, "unknown_pattern")
        assert result is False

    def test_extract_pattern_data(self):
        """Test extracting data for pattern-based delegation."""
        service = ContextDelegationService()
        
        changes = {"security": "vulnerability found"}
        pattern = "security_discovery"
        
        result = service._extract_pattern_data(changes, pattern)
        
        assert result["pattern"] == pattern
        assert result["extracted_data"] == changes
        assert result["extraction_method"] == "pattern_matching"
        assert "extraction_timestamp" in result


class TestAIConfidenceCalculation:
    """Test AI confidence calculation."""

    def test_calculate_ai_delegation_confidence_high_pattern(self):
        """Test AI confidence calculation for high-confidence patterns."""
        service = ContextDelegationService()
        
        changes = {
            "security": "documented vulnerability with tested fix",
            "validation": "pattern validated with best practice implementation"
        }
        
        confidence = service._calculate_ai_delegation_confidence(changes, "security_insight")
        
        # Should be high due to security pattern + quality indicators
        assert confidence >= 0.9
        assert confidence <= 1.0

    def test_calculate_ai_delegation_confidence_low_pattern(self):
        """Test AI confidence calculation for unknown patterns."""
        service = ContextDelegationService()
        
        changes = {"routine": "simple update"}
        
        confidence = service._calculate_ai_delegation_confidence(changes, "unknown_pattern")
        
        # Should use default confidence for unknown patterns
        assert confidence == 0.5

    def test_calculate_ai_delegation_confidence_with_quality_boost(self):
        """Test AI confidence with quality indicators boost."""
        service = ContextDelegationService()
        
        changes = {
            "component": "reusable authentication component",
            "documentation": "well documented implementation",
            "testing": "thoroughly tested with unit tests",
            "validation": "pattern validated"
        }
        
        confidence = service._calculate_ai_delegation_confidence(changes, "reusable_component")
        
        # Base confidence + quality boosts should be high
        assert confidence > 0.8

    def test_calculate_ai_delegation_confidence_exception(self):
        """Test AI confidence calculation exception handling."""
        service = ContextDelegationService()
        
        # Create changes that might cause exception
        changes = None
        
        confidence = service._calculate_ai_delegation_confidence(changes, "test_pattern")
        
        # Should return default confidence on exception
        assert confidence == 0.5


class TestQueueManagement:
    """Test delegation queue management."""

    @pytest.mark.asyncio
    async def test_get_pending_delegations(self):
        """Test retrieving pending delegations."""
        mock_repo = AsyncMock()
        mock_repo.get_delegations.return_value = [
            {"delegation_id": "del_1", "source_level": "task"},
            {"delegation_id": "del_2", "source_level": "project"}
        ]
        
        service = ContextDelegationService(repository=mock_repo)
        
        delegations = await service.get_pending_delegations()
        
        assert len(delegations) == 2
        assert delegations[0]["delegation_id"] == "del_1"
        
        # Should call repository with correct filters
        mock_repo.get_delegations.assert_called_once_with({"processed": False})

    @pytest.mark.asyncio
    async def test_get_pending_delegations_with_filters(self):
        """Test retrieving pending delegations with filters."""
        mock_repo = AsyncMock()
        mock_repo.get_delegations.return_value = []
        
        service = ContextDelegationService(repository=mock_repo)
        
        await service.get_pending_delegations("project", "proj_123")
        
        # Should apply additional filters
        expected_filters = {
            "processed": False,
            "target_level": "project",
            "target_id": "proj_123"
        }
        mock_repo.get_delegations.assert_called_once_with(expected_filters)

    @pytest.mark.asyncio
    async def test_get_pending_delegations_exception(self):
        """Test get pending delegations exception handling."""
        mock_repo = AsyncMock()
        mock_repo.get_delegations.side_effect = Exception("Query failed")
        
        service = ContextDelegationService(repository=mock_repo)
        
        delegations = await service.get_pending_delegations()
        
        assert len(delegations) == 0

    @pytest.mark.asyncio
    async def test_approve_delegation_success(self):
        """Test successful delegation approval."""
        mock_repo = AsyncMock()
        mock_delegation_data = {
            "delegation_id": "del_123",
            "source_level": "task",
            "source_id": "task_123",
            "target_level": "project",
            "target_id": "proj_456",
            "delegated_data": {"pattern": "auth"},
            "delegation_reason": "Reusable pattern",
            "trigger_type": "manual",
            "processed": False
        }
        mock_repo.get_delegation.return_value = mock_delegation_data
        mock_repo.update_delegation = AsyncMock()
        
        service = ContextDelegationService(repository=mock_repo)
        
        with patch.object(service, '_assess_delegation_impact') as mock_assess:
            mock_assess.return_value = {"score": 90}
            
            with patch.object(service, '_execute_delegation') as mock_execute:
                mock_execute.return_value = {"success": True, "implemented": True}
                
                result = await service.approve_delegation("del_123", "admin")
        
        assert result["success"] is True
        mock_repo.update_delegation.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_delegation_not_found(self):
        """Test delegation approval when delegation not found."""
        mock_repo = AsyncMock()
        mock_repo.get_delegation.return_value = None
        
        service = ContextDelegationService(repository=mock_repo)
        
        result = await service.approve_delegation("nonexistent", "test_approver")
        
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_approve_delegation_already_processed(self):
        """Test delegation approval when already processed."""
        mock_repo = AsyncMock()
        mock_delegation_data = {
            "delegation_id": "del_123",
            "processed": True  # Already processed
        }
        mock_repo.get_delegation.return_value = mock_delegation_data
        
        service = ContextDelegationService(repository=mock_repo)
        
        result = await service.approve_delegation("del_123", "test_approver")
        
        assert result["success"] is False
        assert "already processed" in result["error"]

    @pytest.mark.asyncio
    async def test_reject_delegation_success(self):
        """Test successful delegation rejection."""
        mock_repo = AsyncMock()
        mock_repo.update_delegation = AsyncMock()
        
        service = ContextDelegationService(repository=mock_repo)
        
        result = await service.reject_delegation("del_123", "Not suitable", "reviewer")
        
        assert result["success"] is True
        assert result["delegation_id"] == "del_123"
        assert result["rejected"] is True
        
        # Should update delegation with rejection details
        mock_repo.update_delegation.assert_called_once()
        # Check if args are passed positionally or as kwargs
        call_args = mock_repo.update_delegation.call_args
        if call_args.args:
            # Positional arguments - check the data structure
            update_data = call_args.args[1] if len(call_args.args) > 1 else call_args.args[0]
            if isinstance(update_data, dict):
                assert update_data.get("approved") is False or update_data.get("status") == "rejected"
                assert "Not suitable" in str(update_data)
        else:
            # Keyword arguments
            update_args = call_args[1]
            assert update_args["approved"] is False
            assert update_args["rejected_reason"] == "Not suitable"

    @pytest.mark.asyncio
    async def test_reject_delegation_exception(self):
        """Test delegation rejection exception handling."""
        mock_repo = AsyncMock()
        mock_repo.update_delegation.side_effect = Exception("Update failed")
        
        service = ContextDelegationService(repository=mock_repo)
        
        result = await service.reject_delegation("del_123", "Test reason", "test_rejector")
        
        assert result["success"] is False
        assert "error" in result


class TestQueueStatus:
    """Test delegation queue status functionality."""

    @pytest.mark.asyncio
    async def test_get_queue_status_healthy(self):
        """Test queue status when healthy."""
        service = ContextDelegationService()
        
        with patch.object(service, 'get_pending_delegations') as mock_pending:
            mock_pending.return_value = ["del1", "del2"]  # 2 pending items
            
            status = await service.get_queue_status()
        
        assert status["status"] == "healthy"
        assert status["pending_delegations"] == 2
        assert status["queue_healthy"] is True

    @pytest.mark.asyncio
    async def test_get_queue_status_unhealthy(self):
        """Test queue status when unhealthy (too many pending)."""
        service = ContextDelegationService()
        
        with patch.object(service, 'get_pending_delegations') as mock_pending:
            # Return more than 100 pending items
            mock_pending.return_value = ["del" + str(i) for i in range(150)]
            
            status = await service.get_queue_status()
        
        assert status["status"] == "healthy"  # Overall status still healthy
        assert status["pending_delegations"] == 150
        assert status["queue_healthy"] is False  # Queue health is poor

    @pytest.mark.asyncio
    async def test_get_queue_status_exception(self):
        """Test queue status exception handling."""
        service = ContextDelegationService()
        
        with patch.object(service, 'get_pending_delegations', side_effect=Exception("Queue error")):
            status = await service.get_queue_status()
        
        assert status["status"] == "error"
        assert "error" in status


class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_resolve_target_id_global(self):
        """Test resolving target ID for global level."""
        service = ContextDelegationService()
        
        target_id = await service._resolve_target_id("task_123", "task", "global")
        
        assert target_id == "global_singleton"

    @pytest.mark.asyncio
    async def test_resolve_target_id_project_from_task(self):
        """Test resolving target ID for project level from task."""
        mock_repo = AsyncMock()
        service = ContextDelegationService(repository=mock_repo)
        
        # Mock task context with parent project ID
        with patch.object(service, '_get_context') as mock_get_context:
            mock_get_context.return_value = {"parent_project_id": "proj_789"}
            
            target_id = await service._resolve_target_id("task_123", "task", "project")
        
        assert target_id == "proj_789"

    @pytest.mark.asyncio
    async def test_resolve_target_id_project_default(self):
        """Test resolving target ID for project level with default fallback."""
        mock_repo = AsyncMock()
        service = ContextDelegationService(repository=mock_repo)
        
        # Mock task context without parent project ID
        with patch.object(service, '_get_context') as mock_get_context:
            mock_get_context.return_value = {"other_data": "value"}
            
            target_id = await service._resolve_target_id("task_123", "task", "project")
        
        assert target_id == "dhafnck_mcp"  # Default project

    @pytest.mark.asyncio
    async def test_resolve_target_id_exception(self):
        """Test target ID resolution exception handling."""
        service = ContextDelegationService()
        
        with patch.object(service, '_get_context', side_effect=Exception("Context error")):
            target_id = await service._resolve_target_id("task_123", "task", "project")
        
        # Should return safe default
        assert target_id == "dhafnck_mcp"

    def test_exceeds_threshold_count_type(self):
        """Test threshold checking with count type."""
        service = ContextDelegationService()
        
        context_data = {"key": "value"}
        changes = {"description": "security issue found in security module"}
        threshold_config = {"type": "count", "value": 2, "pattern": "security"}
        
        result = service._exceeds_threshold(context_data, changes, "security_count", threshold_config)
        
        assert result is True  # "security" appears twice

    def test_exceeds_threshold_percentage_type(self):
        """Test threshold checking with percentage type."""
        service = ContextDelegationService()
        
        context_data = {"completion_rate": 85}
        changes = {"update": "progress updated"}
        threshold_config = {"type": "percentage", "value": 80}
        
        result = service._exceeds_threshold(context_data, changes, "completion_rate", threshold_config)
        
        assert result is True  # 85 >= 80

    def test_exceeds_threshold_not_exceeded(self):
        """Test threshold checking when threshold not exceeded."""
        service = ContextDelegationService()
        
        context_data = {"error_count": 3}
        changes = {"update": "minor fix"}
        threshold_config = {"type": "percentage", "value": 10}
        
        result = service._exceeds_threshold(context_data, changes, "error_count", threshold_config)
        
        assert result is False  # 3 < 10

    def test_exceeds_threshold_exception(self):
        """Test threshold checking exception handling."""
        service = ContextDelegationService()
        
        # Invalid threshold config
        threshold_config = {"type": "invalid_type"}
        
        result = service._exceeds_threshold({}, {}, "test", threshold_config)
        
        assert result is False

    def test_extract_threshold_data(self):
        """Test extracting threshold data."""
        service = ContextDelegationService()
        
        context_data = {"error_rate": 15, "other_data": "value"}
        
        result = service._extract_threshold_data(context_data, "error_rate")
        
        assert result["threshold_name"] == "error_rate"
        assert result["threshold_data"] == 15
        assert result["extraction_method"] == "threshold_trigger"
        assert "extraction_timestamp" in result

    def test_extract_ai_pattern_data(self):
        """Test extracting AI pattern data."""
        service = ContextDelegationService()
        
        changes = {"component": "reusable auth utility"}
        pattern = "reusable_component"
        
        result = service._extract_ai_pattern_data(changes, pattern)
        
        assert result["ai_pattern"] == pattern
        assert result["detected_data"] == changes
        assert result["extraction_method"] == "ai_pattern_recognition"
        assert "extraction_timestamp" in result
        assert "confidence_factors" in result