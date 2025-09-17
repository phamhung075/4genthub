"""Unit Tests for ParameterEnforcementService

Tests the parameter enforcement service with different enforcement levels
and various parameter combinations.

Part of Phase 2: Core Enforcement Implementation
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from fastmcp.task_management.application.services.parameter_enforcement_service import (
    ParameterEnforcementService,
    EnforcementLevel,
    EnforcementResult,
    AgentCompliance
)


class TestParameterEnforcementService:
    """Test suite for ParameterEnforcementService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = ParameterEnforcementService(EnforcementLevel.WARNING)
    
    def test_enforcement_disabled(self):
        """Test that DISABLED level always allows operations"""
        service = ParameterEnforcementService(EnforcementLevel.DISABLED)
        
        result = service.enforce(
            action="update",
            provided_params={},  # No params provided
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.DISABLED
        assert result.message == "Parameter enforcement disabled"
    
    def test_soft_enforcement_logs_only(self):
        """Test that SOFT level logs but doesn't block"""
        service = ParameterEnforcementService(EnforcementLevel.SOFT)
        
        result = service.enforce(
            action="update",
            provided_params={},  # Missing required params
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.SOFT
        assert "work_notes" in result.missing_required
        assert "progress_made" in result.missing_required
        assert result.compliance_tracked is True
    
    def test_warning_enforcement_warns_but_allows(self):
        """Test that WARNING level warns but allows operation"""
        service = ParameterEnforcementService(EnforcementLevel.WARNING)
        
        result = service.enforce(
            action="update",
            provided_params={"details": "Some work done"},
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.WARNING
        assert len(result.missing_required) == 2  # work_notes, progress_made
        assert len(result.hints) > 0
        assert "work_notes" in result.examples
        assert "progress_made" in result.examples
    
    def test_strict_enforcement_blocks_missing_required(self):
        """Test that STRICT level blocks when required params missing"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        result = service.enforce(
            action="update",
            provided_params={"status": "in_progress"},
            agent_id="test_agent"
        )
        
        assert result.allowed is False
        assert result.level == EnforcementLevel.STRICT
        assert "Operation blocked" in result.message
        assert len(result.missing_required) == 2
        assert "example_command" in result.examples
    
    def test_strict_enforcement_allows_with_required_params(self):
        """Test that STRICT level allows when required params provided"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        result = service.enforce(
            action="update",
            provided_params={
                "work_notes": "Refactoring auth module",
                "progress_made": "Completed JWT implementation"
            },
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.STRICT
        assert len(result.missing_required) == 0
        # Should still show recommended params
        assert "files_modified" in result.missing_recommended
    
    def test_complete_action_requires_completion_summary(self):
        """Test that complete action requires completion_summary"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        # Without completion_summary
        result = service.enforce(
            action="complete",
            provided_params={},
            agent_id="test_agent"
        )
        
        assert result.allowed is False
        assert "completion_summary" in result.missing_required
        assert "example_command" in result.examples
        
        # With completion_summary
        result = service.enforce(
            action="complete",
            provided_params={
                "completion_summary": "Implemented feature X with full test coverage"
            },
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert len(result.missing_required) == 0
    
    def test_agent_compliance_tracking(self):
        """Test that agent compliance is tracked correctly"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        # First operation - non-compliant
        service.enforce(
            action="update",
            provided_params={},
            agent_id="test_agent"
        )
        
        # Second operation - compliant
        service.enforce(
            action="update",
            provided_params={
                "work_notes": "Working on feature",
                "progress_made": "50% complete"
            },
            agent_id="test_agent"
        )
        
        # Check compliance stats
        compliance = service.get_agent_compliance("test_agent")
        assert compliance is not None
        assert compliance.total_operations == 2
        assert compliance.compliant_operations == 1
        assert compliance.operations_blocked == 1
        assert compliance.compliance_rate == 0.5
    
    def test_parameter_hints_for_actions(self):
        """Test that parameter hints are provided for different actions"""
        service = ParameterEnforcementService()
        
        # Update action hints
        hints = service.get_parameter_hints("update")
        assert "work_notes" in hints["required"]
        assert "progress_made" in hints["required"]
        assert "files_modified" in hints["recommended"]
        assert "work_notes" in hints["templates"]
        
        # Complete action hints
        hints = service.get_parameter_hints("complete")
        assert "completion_summary" in hints["required"]
        assert "testing_notes" in hints["recommended"]
        assert "completion_summary" in hints["templates"]
    
    def test_subtask_operations(self):
        """Test enforcement for subtask operations"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        # Subtask update
        result = service.enforce(
            action="subtask_update",
            provided_params={},
            agent_id="test_agent"
        )
        
        assert result.allowed is False
        assert "progress_notes" in result.missing_required
        
        # Subtask complete
        result = service.enforce(
            action="subtask_complete",
            provided_params={
                "completion_summary": "Subtask completed"
            },
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert "impact_on_parent" in result.missing_recommended
    
    def test_empty_and_none_params_filtered(self):
        """Test that empty strings and None values are treated as missing"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        result = service.enforce(
            action="update",
            provided_params={
                "work_notes": "",  # Empty string
                "progress_made": None,  # None value
                "details": "   "  # Whitespace only
            },
            agent_id="test_agent"
        )
        
        assert result.allowed is False
        assert "work_notes" in result.missing_required
        assert "progress_made" in result.missing_required
    
    def test_enforcement_level_can_be_changed(self):
        """Test that enforcement level can be changed at runtime"""
        service = ParameterEnforcementService(EnforcementLevel.SOFT)
        
        # Initially SOFT - should allow
        result = service.enforce("update", {}, "test_agent")
        assert result.allowed is True
        
        # Change to STRICT
        service.set_enforcement_level(EnforcementLevel.STRICT)
        
        # Now should block
        result = service.enforce("update", {}, "test_agent")
        assert result.allowed is False
    
    def test_unknown_action_has_no_requirements(self):
        """Test that unknown actions have no parameter requirements"""
        service = ParameterEnforcementService(EnforcementLevel.STRICT)
        
        result = service.enforce(
            action="unknown_action",
            provided_params={},
            agent_id="test_agent"
        )
        
        assert result.allowed is True
        assert len(result.missing_required) == 0
        assert len(result.missing_recommended) == 0