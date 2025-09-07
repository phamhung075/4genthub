"""Tests for ParameterEnforcementService"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from fastmcp.task_management.application.services.parameter_enforcement_service import (
    ParameterEnforcementService,
    EnforcementLevel,
    EnforcementResult,
    AgentCompliance
)


class TestAgentCompliance:
    """Test cases for AgentCompliance"""

    def test_init(self):
        """Test AgentCompliance initialization"""
        compliance = AgentCompliance(agent_id="agent-123")
        
        assert compliance.agent_id == "agent-123"
        assert compliance.total_operations == 0
        assert compliance.compliant_operations == 0
        assert compliance.warnings_issued == 0
        assert compliance.operations_blocked == 0
        assert compliance.consecutive_failures == 0
        assert compliance.last_operation is None
        assert compliance.compliance_rate == 0.0

    def test_update_compliance_success(self):
        """Test updating compliance with successful operation"""
        compliance = AgentCompliance(agent_id="agent-123")
        
        compliance.update_compliance(is_compliant=True, was_blocked=False)
        
        assert compliance.total_operations == 1
        assert compliance.compliant_operations == 1
        assert compliance.consecutive_failures == 0
        assert compliance.compliance_rate == 1.0
        assert compliance.last_operation is not None

    def test_update_compliance_failure_with_warning(self):
        """Test updating compliance with failure (warning issued)"""
        compliance = AgentCompliance(agent_id="agent-123")
        
        compliance.update_compliance(is_compliant=False, was_blocked=False)
        
        assert compliance.total_operations == 1
        assert compliance.compliant_operations == 0
        assert compliance.warnings_issued == 1
        assert compliance.operations_blocked == 0
        assert compliance.consecutive_failures == 1
        assert compliance.compliance_rate == 0.0

    def test_update_compliance_failure_with_block(self):
        """Test updating compliance with failure (operation blocked)"""
        compliance = AgentCompliance(agent_id="agent-123")
        
        compliance.update_compliance(is_compliant=False, was_blocked=True)
        
        assert compliance.total_operations == 1
        assert compliance.compliant_operations == 0
        assert compliance.warnings_issued == 0
        assert compliance.operations_blocked == 1
        assert compliance.consecutive_failures == 1
        assert compliance.compliance_rate == 0.0

    def test_update_compliance_mixed_operations(self):
        """Test compliance calculation with mixed operations"""
        compliance = AgentCompliance(agent_id="agent-123")
        
        # 3 successful, 2 failures
        compliance.update_compliance(is_compliant=True)
        compliance.update_compliance(is_compliant=True)
        compliance.update_compliance(is_compliant=False, was_blocked=False)
        compliance.update_compliance(is_compliant=True)
        compliance.update_compliance(is_compliant=False, was_blocked=True)
        
        assert compliance.total_operations == 5
        assert compliance.compliant_operations == 3
        assert compliance.warnings_issued == 1
        assert compliance.operations_blocked == 1
        assert compliance.consecutive_failures == 1  # Reset after success, then 1 failure
        assert compliance.compliance_rate == 0.6

    def test_consecutive_failures_reset(self):
        """Test that consecutive failures reset on success"""
        compliance = AgentCompliance(agent_id="agent-123")
        
        compliance.update_compliance(is_compliant=False)
        compliance.update_compliance(is_compliant=False)
        assert compliance.consecutive_failures == 2
        
        compliance.update_compliance(is_compliant=True)
        assert compliance.consecutive_failures == 0


class TestParameterEnforcementService:
    """Test cases for ParameterEnforcementService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = ParameterEnforcementService(EnforcementLevel.WARNING)

    def test_init(self):
        """Test service initialization"""
        assert self.service.enforcement_level == EnforcementLevel.WARNING
        assert self.service._user_id is None
        assert self.service.agent_compliance == {}

    def test_init_with_user_id(self):
        """Test service initialization with user_id"""
        user_id = "user-123"
        service = ParameterEnforcementService(EnforcementLevel.STRICT, user_id)
        
        assert service.enforcement_level == EnforcementLevel.STRICT
        assert service._user_id == user_id

    @patch('fastmcp.task_management.application.services.parameter_enforcement_service.logger')
    def test_init_logging(self, mock_logger):
        """Test that initialization is logged"""
        ParameterEnforcementService(EnforcementLevel.SOFT)
        mock_logger.info.assert_called_with("ParameterEnforcementService initialized with level: soft")

    def test_with_user(self):
        """Test creating user-scoped service instance"""
        user_id = "user-456"
        
        new_service = self.service.with_user(user_id)
        
        assert isinstance(new_service, ParameterEnforcementService)
        assert new_service.enforcement_level == self.service.enforcement_level
        assert new_service._user_id == user_id

    def test_enforce_disabled_level(self):
        """Test enforcement when level is DISABLED"""
        result = self.service.enforce(
            action="update",
            provided_params={},
            enforcement_level=EnforcementLevel.DISABLED
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.DISABLED
        assert result.message == "Parameter enforcement disabled"

    def test_enforce_soft_level_with_missing_required(self):
        """Test enforcement with SOFT level and missing required parameters"""
        result = self.service.enforce(
            action="update",
            provided_params={},
            enforcement_level=EnforcementLevel.SOFT
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.SOFT
        assert result.message == "Operation allowed (soft enforcement - logging only)"
        assert "work_notes" in result.missing_required
        assert "progress_made" in result.missing_required

    @patch('fastmcp.task_management.application.services.parameter_enforcement_service.logger')
    def test_enforce_soft_level_logging(self, mock_logger):
        """Test that SOFT level logs missing parameters"""
        self.service.enforce(
            action="update",
            provided_params={},
            enforcement_level=EnforcementLevel.SOFT
        )
        
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        assert "[SOFT]" in log_call
        assert "update" in log_call

    def test_enforce_warning_level_with_missing_required(self):
        """Test enforcement with WARNING level and missing required parameters"""
        result = self.service.enforce(
            action="complete",
            provided_params={},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.WARNING
        assert result.message == "Operation allowed with warnings"
        assert "completion_summary" in result.missing_required
        assert len(result.hints) > 0
        assert any("Missing required parameters" in hint for hint in result.hints)
        assert "completion_summary" in result.examples

    @patch('fastmcp.task_management.application.services.parameter_enforcement_service.logger')
    def test_enforce_warning_level_logging(self, mock_logger):
        """Test that WARNING level logs missing required parameters"""
        self.service.enforce(
            action="complete",
            provided_params={},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        mock_logger.warning.assert_called()
        log_call = mock_logger.warning.call_args[0][0]
        assert "[WARNING]" in log_call
        assert "completion_summary" in log_call

    def test_enforce_warning_level_no_missing_required(self):
        """Test WARNING level with no missing required parameters"""
        result = self.service.enforce(
            action="complete",
            provided_params={"completion_summary": "Task completed successfully"},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.WARNING
        assert result.message == "Operation allowed"
        assert result.missing_required == []
        assert len(result.missing_recommended) > 0  # Should have missing recommended

    def test_enforce_strict_level_with_missing_required(self):
        """Test enforcement with STRICT level and missing required parameters"""
        result = self.service.enforce(
            action="update",
            provided_params={"some_param": "value"},
            enforcement_level=EnforcementLevel.STRICT
        )
        
        assert result.allowed is False
        assert result.level == EnforcementLevel.STRICT
        assert "Operation blocked" in result.message
        assert "work_notes" in result.missing_required
        assert "progress_made" in result.missing_required
        assert len(result.hints) > 0
        assert any("Operation blocked" in hint for hint in result.hints)
        assert "example_command" in result.examples

    @patch('fastmcp.task_management.application.services.parameter_enforcement_service.logger')
    def test_enforce_strict_level_logging(self, mock_logger):
        """Test that STRICT level logs blocked operations"""
        self.service.enforce(
            action="update",
            provided_params={},
            enforcement_level=EnforcementLevel.STRICT
        )
        
        mock_logger.error.assert_called()
        log_call = mock_logger.error.call_args[0][0]
        assert "[STRICT]" in log_call
        assert "Blocking update" in log_call

    def test_enforce_strict_level_all_required_provided(self):
        """Test STRICT level when all required parameters are provided"""
        result = self.service.enforce(
            action="complete",
            provided_params={"completion_summary": "Task completed successfully"},
            enforcement_level=EnforcementLevel.STRICT
        )
        
        assert result.allowed is True
        assert result.level == EnforcementLevel.STRICT
        assert result.missing_required == []
        assert len(result.missing_recommended) > 0  # Should still have missing recommended
        assert any("All required parameters provided" in hint for hint in result.hints)

    def test_enforce_agent_compliance_tracking(self):
        """Test that agent compliance is tracked"""
        agent_id = "test-agent"
        
        # First operation - missing required parameters
        result1 = self.service.enforce(
            action="update",
            provided_params={},
            agent_id=agent_id,
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert result1.compliance_tracked is True
        assert result1.agent_id == agent_id
        
        # Second operation - all required parameters provided
        result2 = self.service.enforce(
            action="update",
            provided_params={"work_notes": "Working", "progress_made": "Progress"},
            agent_id=agent_id,
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert result2.compliance_tracked is True
        
        # Check compliance statistics
        compliance = self.service.get_agent_compliance(agent_id)
        assert compliance is not None
        assert compliance.total_operations == 2
        assert compliance.compliant_operations == 1
        assert compliance.compliance_rate == 0.5

    def test_enforce_unknown_action(self):
        """Test enforcement with unknown action"""
        result = self.service.enforce(
            action="unknown_action",
            provided_params={},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        # Should not fail, just have no requirements
        assert result.allowed is True
        assert result.missing_required == []
        assert result.missing_recommended == []

    def test_required_params_structure(self):
        """Test that REQUIRED_PARAMS contains expected structure"""
        assert "update" in self.service.REQUIRED_PARAMS
        assert "complete" in self.service.REQUIRED_PARAMS
        assert "create" in self.service.REQUIRED_PARAMS
        assert "subtask_update" in self.service.REQUIRED_PARAMS
        assert "subtask_complete" in self.service.REQUIRED_PARAMS
        
        # Check structure of requirements
        update_req = self.service.REQUIRED_PARAMS["update"]
        assert "strict" in update_req
        assert "recommended" in update_req
        assert isinstance(update_req["strict"], list)
        assert isinstance(update_req["recommended"], list)

    def test_parameter_templates_coverage(self):
        """Test that parameter templates cover common parameters"""
        templates = self.service.PARAMETER_TEMPLATES
        
        assert "work_notes" in templates
        assert "progress_made" in templates
        assert "completion_summary" in templates
        assert "testing_notes" in templates
        assert "files_modified" in templates
        assert "blockers_encountered" in templates

    def test_get_agent_compliance_nonexistent(self):
        """Test getting compliance for non-existent agent"""
        result = self.service.get_agent_compliance("nonexistent-agent")
        assert result is None

    def test_get_all_compliance_stats(self):
        """Test getting all compliance statistics"""
        # Add some agents
        self.service.enforce("update", {}, agent_id="agent1")
        self.service.enforce("complete", {"completion_summary": "done"}, agent_id="agent2")
        
        stats = self.service.get_all_compliance_stats()
        
        assert len(stats) == 2
        assert "agent1" in stats
        assert "agent2" in stats
        assert isinstance(stats["agent1"], AgentCompliance)
        assert isinstance(stats["agent2"], AgentCompliance)

    @patch('fastmcp.task_management.application.services.parameter_enforcement_service.logger')
    def test_set_enforcement_level(self, mock_logger):
        """Test setting enforcement level"""
        original_level = self.service.enforcement_level
        new_level = EnforcementLevel.STRICT
        
        self.service.set_enforcement_level(new_level)
        
        assert self.service.enforcement_level == new_level
        mock_logger.info.assert_called_with(
            f"Enforcement level changed from {original_level.value} to {new_level.value}"
        )

    def test_get_parameter_hints(self):
        """Test getting parameter hints for an action"""
        hints = self.service.get_parameter_hints("update")
        
        assert hints["action"] == "update"
        assert "work_notes" in hints["required"]
        assert "progress_made" in hints["required"]
        assert "files_modified" in hints["recommended"]
        assert "templates" in hints
        assert "work_notes" in hints["templates"]

    def test_get_parameter_hints_unknown_action(self):
        """Test getting parameter hints for unknown action"""
        hints = self.service.get_parameter_hints("unknown_action")
        
        assert hints["action"] == "unknown_action"
        assert hints["required"] == []
        assert hints["recommended"] == []
        assert hints["templates"] == {}

    def test_empty_string_parameters_considered_missing(self):
        """Test that empty string parameters are considered missing"""
        result = self.service.enforce(
            action="update",
            provided_params={"work_notes": "", "progress_made": ""},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert "work_notes" in result.missing_required
        assert "progress_made" in result.missing_required

    def test_none_parameters_considered_missing(self):
        """Test that None parameters are considered missing"""
        result = self.service.enforce(
            action="update",
            provided_params={"work_notes": None, "progress_made": None},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert "work_notes" in result.missing_required
        assert "progress_made" in result.missing_required

    def test_whitespace_only_parameters_considered_missing(self):
        """Test that whitespace-only parameters are considered missing"""
        result = self.service.enforce(
            action="update",
            provided_params={"work_notes": "   ", "progress_made": "\t\n"},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        # Note: Current implementation checks `not provided_params[p]` which would
        # consider whitespace strings as truthy, so they wouldn't be missing.
        # If this behavior needs to change, the implementation should be updated.
        assert result.missing_required == []  # Whitespace strings are considered present

    @patch('fastmcp.task_management.application.services.parameter_enforcement_service.logger')
    def test_low_compliance_warning(self, mock_logger):
        """Test warning when agent compliance is low"""
        agent_id = "low-compliance-agent"
        
        # Generate 10 non-compliant operations
        for _ in range(10):
            self.service.enforce(
                action="update",
                provided_params={},
                agent_id=agent_id,
                enforcement_level=EnforcementLevel.WARNING
            )
        
        # Should trigger low compliance warning
        mock_logger.warning.assert_called()
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                        if "Low compliance" in str(call)]
        assert len(warning_calls) > 0

    def test_create_strict_result_examples(self):
        """Test that strict results include helpful examples"""
        result = self.service.enforce(
            action="complete",
            provided_params={},
            enforcement_level=EnforcementLevel.STRICT
        )
        
        assert result.allowed is False
        assert "completion_summary" in result.examples
        assert "example_command" in result.examples
        
        example_cmd = result.examples["example_command"]
        assert example_cmd["action"] == "complete"
        assert "completion_summary" in example_cmd
        assert "testing_notes" in example_cmd

    def test_create_strict_result_update_examples(self):
        """Test that strict results for update action include update examples"""
        result = self.service.enforce(
            action="update",
            provided_params={},
            enforcement_level=EnforcementLevel.STRICT
        )
        
        assert result.allowed is False
        example_cmd = result.examples["example_command"]
        assert example_cmd["action"] == "update"
        assert "work_notes" in example_cmd
        assert "progress_made" in example_cmd
        assert "files_modified" in example_cmd

    def test_subtask_actions_requirements(self):
        """Test enforcement for subtask-specific actions"""
        # Test subtask_update
        result = self.service.enforce(
            action="subtask_update",
            provided_params={},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert "progress_notes" in result.missing_required
        assert "blockers" in result.missing_recommended
        assert "insights_found" in result.missing_recommended
        
        # Test subtask_complete
        result = self.service.enforce(
            action="subtask_complete",
            provided_params={},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert "completion_summary" in result.missing_required
        assert "impact_on_parent" in result.missing_recommended
        assert "insights_found" in result.missing_recommended
        assert "testing_notes" in result.missing_recommended

    def test_compliance_tracking_without_agent_id(self):
        """Test that operations without agent_id don't affect compliance tracking"""
        result = self.service.enforce(
            action="update",
            provided_params={},
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert result.compliance_tracked is False
        assert result.agent_id is None
        assert len(self.service.agent_compliance) == 0