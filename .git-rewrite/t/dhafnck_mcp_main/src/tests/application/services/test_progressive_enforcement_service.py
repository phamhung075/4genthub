"""Tests for ProgressiveEnforcementService"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

from fastmcp.task_management.application.services.progressive_enforcement_service import (
    ProgressiveEnforcementService,
    AgentProfile
)
from fastmcp.task_management.application.services.parameter_enforcement_service import (
    EnforcementLevel,
    EnforcementResult,
    ParameterEnforcementService
)


class TestAgentProfile:
    """Test cases for AgentProfile"""

    def test_init(self):
        """Test AgentProfile initialization"""
        agent_id = "agent-123"
        first_seen = datetime.now(timezone.utc)
        
        profile = AgentProfile(
            agent_id=agent_id,
            first_seen=first_seen,
            enforcement_level=EnforcementLevel.WARNING
        )
        
        assert profile.agent_id == agent_id
        assert profile.first_seen == first_seen
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert profile.operations_count == 0
        assert profile.learning_phase_operations == 0
        assert profile.warnings_received == 0
        assert profile.consecutive_compliant == 0
        assert profile.consecutive_failures == 0
        assert profile.last_escalation is None
        assert profile.compliance_history == []
        assert profile.manually_set_level is False

    def test_should_escalate_consecutive_failures(self):
        """Test escalation trigger based on consecutive failures"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            consecutive_failures=5
        )
        
        assert profile.should_escalate() is True

    def test_should_escalate_low_compliance_rate(self):
        """Test escalation trigger based on low compliance rate"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            operations_count=25
        )
        
        # Set compliance history with low rate (40% compliance)
        profile.compliance_history = [True, False, False, True, False, 
                                    False, True, False, False, False] * 2
        
        assert profile.should_escalate() is True

    def test_should_escalate_too_many_warnings(self):
        """Test escalation trigger based on too many warnings"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            warnings_received=10
        )
        
        assert profile.should_escalate() is True

    def test_should_escalate_already_strict(self):
        """Test that strict level agents don't escalate further"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.STRICT,
            consecutive_failures=10
        )
        
        assert profile.should_escalate() is False

    def test_should_deescalate_consistent_compliance(self):
        """Test deescalation trigger based on consistent compliance"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.STRICT,
            consecutive_compliant=20
        )
        
        # Set high compliance rate (95%)
        profile.compliance_history = [True] * 19 + [False] * 1
        
        assert profile.should_deescalate() is True

    def test_should_deescalate_already_soft(self):
        """Test that soft level agents don't deescalate further"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.SOFT,
            consecutive_compliant=25
        )
        
        assert profile.should_deescalate() is False

    def test_update_compliance_success(self):
        """Test updating compliance with successful operation"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING
        )
        
        profile.update_compliance(is_compliant=True, was_warned=False)
        
        assert profile.operations_count == 1
        assert profile.compliance_history == [True]
        assert profile.consecutive_compliant == 1
        assert profile.consecutive_failures == 0
        assert profile.warnings_received == 0

    def test_update_compliance_failure_with_warning(self):
        """Test updating compliance with failure and warning"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING
        )
        
        profile.update_compliance(is_compliant=False, was_warned=True)
        
        assert profile.operations_count == 1
        assert profile.compliance_history == [False]
        assert profile.consecutive_compliant == 0
        assert profile.consecutive_failures == 1
        assert profile.warnings_received == 1

    def test_update_compliance_history_limit(self):
        """Test that compliance history is limited to 100 operations"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING
        )
        
        # Add 105 operations
        for i in range(105):
            profile.update_compliance(is_compliant=i % 2 == 0)
        
        assert len(profile.compliance_history) == 100
        assert profile.operations_count == 105

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_escalate_level_soft_to_warning(self, mock_logger):
        """Test escalating from SOFT to WARNING"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.SOFT,
            consecutive_failures=3
        )
        
        profile.escalate_level()
        
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert profile.consecutive_failures == 0
        assert profile.manually_set_level is False
        assert profile.last_escalation is not None
        mock_logger.info.assert_called_with("Agent test escalated to WARNING level")

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_escalate_level_warning_to_strict(self, mock_logger):
        """Test escalating from WARNING to STRICT"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            consecutive_failures=5
        )
        
        profile.escalate_level()
        
        assert profile.enforcement_level == EnforcementLevel.STRICT
        assert profile.consecutive_failures == 0
        assert profile.manually_set_level is False
        mock_logger.info.assert_called_with("Agent test escalated to STRICT level")

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_deescalate_level_strict_to_warning(self, mock_logger):
        """Test deescalating from STRICT to WARNING"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.STRICT,
            consecutive_compliant=20
        )
        
        profile.deescalate_level()
        
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert profile.consecutive_compliant == 0
        assert profile.manually_set_level is False
        mock_logger.info.assert_called_with("Agent test deescalated to WARNING level")

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_deescalate_level_warning_to_soft(self, mock_logger):
        """Test deescalating from WARNING to SOFT"""
        profile = AgentProfile(
            agent_id="test",
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            consecutive_compliant=20
        )
        
        profile.deescalate_level()
        
        assert profile.enforcement_level == EnforcementLevel.SOFT
        assert profile.consecutive_compliant == 0
        assert profile.manually_set_level is False
        mock_logger.info.assert_called_with("Agent test deescalated to SOFT level")


class TestProgressiveEnforcementService:
    """Test cases for ProgressiveEnforcementService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_enforcement_service = Mock(spec=ParameterEnforcementService)
        self.service = ProgressiveEnforcementService(
            enforcement_service=self.mock_enforcement_service,
            default_level=EnforcementLevel.WARNING
        )

    def test_init_with_enforcement_service(self):
        """Test initialization with provided enforcement service"""
        assert self.service.enforcement_service == self.mock_enforcement_service
        assert self.service.default_level == EnforcementLevel.WARNING
        assert self.service.agent_profiles == {}

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_init_logging(self, mock_logger):
        """Test that initialization is logged"""
        ProgressiveEnforcementService(default_level=EnforcementLevel.STRICT)
        mock_logger.info.assert_called_with(
            "ProgressiveEnforcementService initialized with default level: strict"
        )

    def test_init_without_enforcement_service(self):
        """Test initialization without enforcement service creates default"""
        service = ProgressiveEnforcementService()
        
        assert isinstance(service.enforcement_service, ParameterEnforcementService)
        assert service.default_level == EnforcementLevel.WARNING

    def test_get_or_create_profile_new_agent(self):
        """Test creating new agent profile"""
        agent_id = "new-agent"
        
        with patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger') as mock_logger:
            profile = self.service._get_or_create_profile(agent_id)
            
            assert profile.agent_id == agent_id
            assert profile.enforcement_level == EnforcementLevel.WARNING
            assert profile.operations_count == 0
            assert agent_id in self.service.agent_profiles
            
            mock_logger.info.assert_called_with(
                f"New agent profile created for {agent_id} with warning enforcement"
            )

    def test_get_or_create_profile_existing_agent(self):
        """Test getting existing agent profile"""
        agent_id = "existing-agent"
        existing_profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.STRICT,
            operations_count=10
        )
        self.service.agent_profiles[agent_id] = existing_profile
        
        profile = self.service._get_or_create_profile(agent_id)
        
        assert profile is existing_profile
        assert profile.operations_count == 10

    def test_enforce_with_progression_learning_phase(self):
        """Test enforcement during learning phase"""
        agent_id = "learning-agent"
        action = "update"
        provided_params = {"work_notes": "working"}
        
        # Mock enforcement result
        mock_result = EnforcementResult(
            allowed=True,
            level=EnforcementLevel.WARNING,
            missing_required=["progress_made"],
            hints=[]
        )
        self.mock_enforcement_service.enforce.return_value = mock_result
        
        result = self.service.enforce_with_progression(action, provided_params, agent_id)
        
        # Should enforce at WARNING level even if agent later escalates to STRICT
        self.mock_enforcement_service.enforce.assert_called_with(
            action=action,
            provided_params=provided_params,
            agent_id=agent_id,
            enforcement_level=EnforcementLevel.WARNING
        )
        
        # Should add learning phase hint
        assert any("Learning phase" in hint for hint in result.hints)

    def test_enforce_with_progression_strict_learning_override(self):
        """Test that STRICT level is overridden during learning phase"""
        agent_id = "strict-learning-agent"
        
        # Create agent with STRICT level but still in learning phase
        profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.STRICT,
            operations_count=3  # Still in learning phase (< 10)
        )
        self.service.agent_profiles[agent_id] = profile
        
        mock_result = EnforcementResult(
            allowed=True,
            level=EnforcementLevel.WARNING,
            missing_required=[],
            hints=[]
        )
        self.mock_enforcement_service.enforce.return_value = mock_result
        
        result = self.service.enforce_with_progression("update", {}, agent_id)
        
        # Should use WARNING level instead of STRICT during learning phase
        self.mock_enforcement_service.enforce.assert_called_with(
            action="update",
            provided_params={},
            agent_id=agent_id,
            enforcement_level=EnforcementLevel.WARNING
        )

    def test_enforce_with_progression_escalation(self):
        """Test automatic escalation during enforcement"""
        agent_id = "escalating-agent"
        
        # Create agent with high failure count
        profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            operations_count=15,  # Past learning phase
            consecutive_failures=4  # Will become 5 after this operation
        )
        self.service.agent_profiles[agent_id] = profile
        
        # Mock enforcement result showing non-compliance
        mock_result = EnforcementResult(
            allowed=True,
            level=EnforcementLevel.WARNING,
            missing_required=["work_notes"],  # Non-compliant
            hints=[]
        )
        self.mock_enforcement_service.enforce.return_value = mock_result
        
        result = self.service.enforce_with_progression("update", {}, agent_id)
        
        # Should escalate to STRICT
        assert profile.enforcement_level == EnforcementLevel.STRICT
        assert any("Enforcement level increased" in hint for hint in result.hints)

    def test_enforce_with_progression_deescalation(self):
        """Test automatic deescalation during enforcement"""
        agent_id = "deescalating-agent"
        
        # Create agent with high compliance
        profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.STRICT,
            operations_count=25,
            consecutive_compliant=19  # Will become 20 after this operation
        )
        # Set high compliance history
        profile.compliance_history = [True] * 19 + [False]  # 95% compliance
        self.service.agent_profiles[agent_id] = profile
        
        # Mock enforcement result showing compliance
        mock_result = EnforcementResult(
            allowed=True,
            level=EnforcementLevel.STRICT,
            missing_required=[],  # Compliant
            hints=[]
        )
        self.mock_enforcement_service.enforce.return_value = mock_result
        
        result = self.service.enforce_with_progression("update", {"work_notes": "work", "progress_made": "progress"}, agent_id)
        
        # Should deescalate to WARNING
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert any("Enforcement level decreased" in hint for hint in result.hints)

    def test_enforce_with_progression_compliance_stats(self):
        """Test that compliance statistics are added to results"""
        agent_id = "stats-agent"
        
        # Create agent with some history
        profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING,
            operations_count=15
        )
        # 70% compliance rate
        profile.compliance_history = [True, True, False, True, True, True, False, True, True, True]
        self.service.agent_profiles[agent_id] = profile
        
        mock_result = EnforcementResult(
            allowed=True,
            level=EnforcementLevel.WARNING,
            missing_required=[],
            hints=[]
        )
        self.mock_enforcement_service.enforce.return_value = mock_result
        
        result = self.service.enforce_with_progression("update", {"work_notes": "work", "progress_made": "progress"}, agent_id)
        
        # Should include compliance statistics
        assert any("Recent compliance: 70%" in hint for hint in result.hints)

    def test_get_agent_profile(self):
        """Test getting agent profile"""
        agent_id = "test-agent"
        profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc),
            enforcement_level=EnforcementLevel.WARNING
        )
        self.service.agent_profiles[agent_id] = profile
        
        result = self.service.get_agent_profile(agent_id)
        assert result == profile

    def test_get_agent_profile_nonexistent(self):
        """Test getting non-existent agent profile"""
        result = self.service.get_agent_profile("nonexistent-agent")
        assert result is None

    def test_get_all_profiles(self):
        """Test getting all agent profiles"""
        # Add some profiles
        profile1 = AgentProfile("agent1", datetime.now(timezone.utc), EnforcementLevel.WARNING)
        profile2 = AgentProfile("agent2", datetime.now(timezone.utc), EnforcementLevel.STRICT)
        self.service.agent_profiles["agent1"] = profile1
        self.service.agent_profiles["agent2"] = profile2
        
        result = self.service.get_all_profiles()
        
        assert len(result) == 2
        assert result["agent1"] == profile1
        assert result["agent2"] == profile2
        assert result is not self.service.agent_profiles  # Should be a copy

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_reset_agent_profile(self, mock_logger):
        """Test resetting agent profile"""
        agent_id = "reset-agent"
        
        # Create agent with some history
        old_profile = AgentProfile(
            agent_id=agent_id,
            first_seen=datetime.now(timezone.utc) - timedelta(days=1),
            enforcement_level=EnforcementLevel.STRICT,
            operations_count=50
        )
        self.service.agent_profiles[agent_id] = old_profile
        
        self.service.reset_agent_profile(agent_id)
        
        new_profile = self.service.agent_profiles[agent_id]
        assert new_profile.operations_count == 0
        assert new_profile.enforcement_level == EnforcementLevel.WARNING
        assert new_profile.first_seen > old_profile.first_seen
        
        mock_logger.info.assert_called()
        assert "Reset profile" in str(mock_logger.info.call_args)

    def test_reset_agent_profile_nonexistent(self):
        """Test resetting non-existent agent profile does nothing"""
        # Should not raise an error
        self.service.reset_agent_profile("nonexistent-agent")
        assert "nonexistent-agent" not in self.service.agent_profiles

    @patch('fastmcp.task_management.application.services.progressive_enforcement_service.logger')
    def test_set_agent_level(self, mock_logger):
        """Test manually setting agent enforcement level"""
        agent_id = "manual-agent"
        
        self.service.set_agent_level(agent_id, EnforcementLevel.STRICT)
        
        profile = self.service.agent_profiles[agent_id]
        assert profile.enforcement_level == EnforcementLevel.STRICT
        assert profile.manually_set_level is True
        
        mock_logger.info.assert_called()
        assert "Manually changed agent" in str(mock_logger.info.call_args)

    def test_get_enforcement_stats_empty(self):
        """Test getting enforcement stats with no agents"""
        stats = self.service.get_enforcement_stats()
        
        expected = {
            "total_agents": 0,
            "by_level": {"soft": 0, "warning": 0, "strict": 0},
            "learning_phase": 0,
            "average_compliance": 0.0,
            "problem_agents": []
        }
        
        assert stats == expected

    def test_get_enforcement_stats_with_agents(self):
        """Test getting enforcement stats with multiple agents"""
        # Create agents with different profiles
        profile1 = AgentProfile("agent1", datetime.now(timezone.utc), EnforcementLevel.WARNING)
        profile1.operations_count = 5  # In learning phase
        profile1.compliance_history = [True, False, True, True, False]  # 60% compliance
        
        profile2 = AgentProfile("agent2", datetime.now(timezone.utc), EnforcementLevel.STRICT) 
        profile2.operations_count = 30
        profile2.compliance_history = [True] * 25 + [False] * 5  # 83% compliance
        
        profile3 = AgentProfile("agent3", datetime.now(timezone.utc), EnforcementLevel.SOFT)
        profile3.operations_count = 25
        profile3.compliance_history = [True] * 10 + [False] * 15  # 40% compliance (problem agent)
        
        self.service.agent_profiles = {
            "agent1": profile1,
            "agent2": profile2,
            "agent3": profile3
        }
        
        stats = self.service.get_enforcement_stats()
        
        assert stats["total_agents"] == 3
        assert stats["by_level"]["soft"] == 1
        assert stats["by_level"]["warning"] == 1
        assert stats["by_level"]["strict"] == 1
        assert stats["learning_phase"] == 1
        assert stats["average_compliance"] > 0.6  # Average of 60%, 83%, 40%
        assert len(stats["problem_agents"]) == 1
        assert stats["problem_agents"][0]["agent_id"] == "agent3"

    def test_class_constants(self):
        """Test that class constants are properly defined"""
        assert ProgressiveEnforcementService.DEFAULT_STARTING_LEVEL == EnforcementLevel.WARNING
        assert ProgressiveEnforcementService.LEARNING_PHASE_OPERATIONS == 10
        assert ProgressiveEnforcementService.ESCALATION_THRESHOLD_FAILURES == 5
        assert ProgressiveEnforcementService.DEESCALATION_THRESHOLD_SUCCESS == 20
        assert ProgressiveEnforcementService.COMPLIANCE_RATE_THRESHOLD == 0.6

    def test_profile_update_compliance_resets_consecutive_counters(self):
        """Test that update_compliance properly resets consecutive counters"""
        profile = AgentProfile("test", datetime.now(timezone.utc), EnforcementLevel.WARNING)
        
        # Build up consecutive failures
        profile.update_compliance(False)
        profile.update_compliance(False) 
        assert profile.consecutive_failures == 2
        assert profile.consecutive_compliant == 0
        
        # Success should reset failures and start compliant count
        profile.update_compliance(True)
        assert profile.consecutive_failures == 0
        assert profile.consecutive_compliant == 1
        
        # Another success should increment compliant
        profile.update_compliance(True)
        assert profile.consecutive_failures == 0
        assert profile.consecutive_compliant == 2
        
        # Failure should reset compliant and start failure count
        profile.update_compliance(False)
        assert profile.consecutive_failures == 1
        assert profile.consecutive_compliant == 0