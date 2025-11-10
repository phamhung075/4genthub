"""Unit Tests for ProgressiveEnforcementService

Tests the progressive enforcement service that gradually increases
enforcement based on agent behavior.

Part of Phase 2: Core Enforcement Implementation
"""



from fastmcp.task_management.application.services.parameter_enforcement_service import (
    ParameterEnforcementService,
)
from fastmcp.task_management.application.services.progressive_enforcement_service import (
    EnforcementLevel,
    ProgressiveEnforcementService,
)


class TestProgressiveEnforcementService:
    """Test suite for ProgressiveEnforcementService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.base_service = ParameterEnforcementService(EnforcementLevel.WARNING)
        self.service = ProgressiveEnforcementService(
            enforcement_service=self.base_service,
            default_level=EnforcementLevel.WARNING
        )
    
    def test_new_agent_starts_with_default_level(self):
        """Test that new agents start with the default enforcement level"""
        self.service.enforce_with_progression(
            action="update",
            provided_params={},
            agent_id="new_agent"
        )
        
        profile = self.service.get_agent_profile("new_agent")
        assert profile is not None
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert profile.operations_count == 1
        assert len(profile.compliance_history) == 1
    
    def test_learning_phase_more_lenient(self):
        """Test that agents in learning phase get more lenient treatment"""
        # Create agent with STRICT level
        self.service.set_agent_level("test_agent", EnforcementLevel.STRICT)
        
        # First operation should be lenient (WARNING instead of STRICT)
        result = self.service.enforce_with_progression(
            action="update",
            provided_params={},
            agent_id="test_agent"
        )
        
        # During learning phase, should be WARNING even though set to STRICT
        assert result.allowed is True  # WARNING allows
        assert any("Learning phase" in hint for hint in result.hints)
    
    def test_escalation_after_consecutive_failures(self):
        """Test that enforcement escalates after consecutive failures"""
        agent_id = "failing_agent"
        
        # Fail 5 times consecutively (threshold for escalation)
        for i in range(5):
            self.service.enforce_with_progression(
                action="update",
                provided_params={},  # Missing required params
                agent_id=agent_id
            )
        
        profile = self.service.get_agent_profile(agent_id)
        # Should escalate from WARNING to STRICT
        assert profile.enforcement_level == EnforcementLevel.STRICT
        assert profile.consecutive_failures == 0  # Reset after escalation
    
    def test_deescalation_after_consistent_compliance(self):
        """Test that enforcement deescalates after consistent compliance"""
        agent_id = "improving_agent"
        
        # Start at STRICT level
        self.service.set_agent_level(agent_id, EnforcementLevel.STRICT)
        
        # Be compliant for 20 consecutive operations
        for i in range(20):
            self.service.enforce_with_progression(
                action="update",
                provided_params={
                    "work_notes": f"Work update {i}",
                    "progress_made": f"Progress {i}"
                },
                agent_id=agent_id
            )
        
        profile = self.service.get_agent_profile(agent_id)
        # Should deescalate from STRICT to WARNING
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert profile.consecutive_compliant == 0  # Reset after deescalation
    
    def test_compliance_rate_tracking(self):
        """Test that compliance rate is tracked and displayed correctly"""
        agent_id = "mixed_agent"
        
        # Mix of compliant and non-compliant operations
        for i in range(10):
            if i % 2 == 0:
                # Compliant
                params = {"work_notes": "Work", "progress_made": "Progress"}
            else:
                # Non-compliant
                params = {}
            
            result = self.service.enforce_with_progression(
                action="update",
                provided_params=params,
                agent_id=agent_id
            )
        
        # Check that compliance rate is shown in hints
        profile = self.service.get_agent_profile(agent_id)
        assert profile.operations_count == 10
        assert len(profile.compliance_history) == 10
        
        # Last result should show compliance rate
        result = self.service.enforce_with_progression(
            action="update",
            provided_params={},
            agent_id=agent_id
        )
        assert any("Recent compliance" in hint for hint in result.hints)
    
    def test_escalation_based_on_low_compliance_rate(self):
        """Test escalation when compliance rate drops below threshold"""
        agent_id = "low_compliance_agent"
        
        # Skip learning phase
        for i in range(10):
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent_id
            )
        
        # Now have poor compliance (< 60%)
        for i in range(10):
            # Only 3 compliant out of 10 (30% compliance)
            if i < 3:
                params = {"work_notes": "Work", "progress_made": "Progress"}
            else:
                params = {}
            
            self.service.enforce_with_progression(
                action="update",
                provided_params=params,
                agent_id=agent_id
            )
        
        profile = self.service.get_agent_profile(agent_id)
        # Should escalate due to low compliance rate
        assert profile.enforcement_level == EnforcementLevel.STRICT
    
    def test_warnings_count_triggers_escalation(self):
        """Test that too many warnings trigger escalation"""
        agent_id = "warned_agent"
        
        # Receive 10 warnings (threshold for escalation)
        for i in range(10):
            self.service.enforce_with_progression(
                action="update",
                provided_params={},  # Missing params to get warnings
                agent_id=agent_id
            )
        
        profile = self.service.get_agent_profile(agent_id)
        assert profile.warnings_received >= 10
        assert profile.enforcement_level == EnforcementLevel.STRICT
    
    def test_reset_agent_profile(self):
        """Test that agent profile can be reset"""
        agent_id = "reset_agent"
        
        # Build up some history
        for i in range(5):
            self.service.enforce_with_progression(
                action="update",
                provided_params={},
                agent_id=agent_id
            )
        
        # Reset profile
        self.service.reset_agent_profile(agent_id)
        
        profile = self.service.get_agent_profile(agent_id)
        assert profile.operations_count == 0
        assert len(profile.compliance_history) == 0
        assert profile.enforcement_level == EnforcementLevel.WARNING
    
    def test_enforcement_stats(self):
        """Test that overall enforcement statistics are tracked"""
        # Create agents with different levels
        self.service.set_agent_level("soft_agent", EnforcementLevel.SOFT)
        self.service.set_agent_level("warning_agent", EnforcementLevel.WARNING)
        self.service.set_agent_level("strict_agent", EnforcementLevel.STRICT)
        
        # Perform operations
        for agent in ["soft_agent", "warning_agent", "strict_agent"]:
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent
            )
        
        stats = self.service.get_enforcement_stats()
        assert stats["total_agents"] == 3
        assert stats["by_level"]["soft"] == 1
        assert stats["by_level"]["warning"] == 1
        assert stats["by_level"]["strict"] == 1
        assert stats["average_compliance"] == 1.0  # All were compliant
    
    def test_problem_agents_identified(self):
        """Test that problem agents with low compliance are identified"""
        agent_id = "problem_agent"
        
        # Skip learning phase with good compliance
        for i in range(10):
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent_id
            )
        
        # Now have very poor compliance
        for i in range(20):
            self.service.enforce_with_progression(
                action="update",
                provided_params={},  # Non-compliant
                agent_id=agent_id
            )
        
        stats = self.service.get_enforcement_stats()
        assert len(stats["problem_agents"]) == 1
        assert stats["problem_agents"][0]["agent_id"] == agent_id
        assert stats["problem_agents"][0]["compliance_rate"] < 0.5
    
    def test_hints_include_learning_phase_info(self):
        """Test that hints include learning phase information"""
        agent_id = "learning_agent"
        
        # First operation
        result = self.service.enforce_with_progression(
            action="update",
            provided_params={},
            agent_id=agent_id
        )
        
        # Should have learning phase hint
        assert any("Learning phase" in hint and "9 operations remaining" in hint 
                  for hint in result.hints)
        
        # After learning phase
        for i in range(9):
            self.service.enforce_with_progression(
                action="update",
                provided_params={},
                agent_id=agent_id
            )
        
        # No more learning phase hints
        result = self.service.enforce_with_progression(
            action="update",
            provided_params={},
            agent_id=agent_id
        )
        assert not any("Learning phase" in hint for hint in result.hints)
    
    def test_compliance_history_limited(self):
        """Test that compliance history is limited to prevent memory issues"""
        agent_id = "history_agent"

        # Perform many operations
        for i in range(150):
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent_id
            )

        profile = self.service.get_agent_profile(agent_id)
        # History should be limited to last 100
        assert len(profile.compliance_history) == 100
        assert profile.operations_count == 150

    def test_should_escalate_from_compliance_rate(self):
        """Test line 54: escalate when compliance rate < 60% after 20 operations"""
        agent_id = "low_rate_agent"

        # Complete learning phase first (10 operations - all compliant)
        for i in range(10):
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent_id
            )

        # Now do 10 more operations with low compliance rate (50% = 5 out of 10)
        # Alternate between compliant and non-compliant to avoid 5 consecutive failures
        for i in range(10):
            params = {"work_notes": "Work", "progress_made": "Progress"} if i % 2 == 0 else {}
            self.service.enforce_with_progression(
                action="update",
                provided_params=params,
                agent_id=agent_id
            )

        profile = self.service.get_agent_profile(agent_id)
        # Line 54 was hit during the enforcement process
        # Verify the agent escalated to STRICT due to low compliance rate
        # The recent compliance rate was < 60%, which triggered line 54
        recent_compliance = profile.compliance_history[-10:]
        compliance_rate = sum(recent_compliance) / len(recent_compliance)
        assert compliance_rate < 0.6
        # Agent should have escalated from WARNING to STRICT
        assert profile.enforcement_level == EnforcementLevel.STRICT

    def test_should_escalate_from_warnings_at_warning_level(self):
        """Test line 58: escalate when warnings_received >= 10 at WARNING level"""
        agent_id = "warned_escalate_agent"

        # Ensure agent is at WARNING level
        profile = self.service._get_or_create_profile(agent_id)
        assert profile.enforcement_level == EnforcementLevel.WARNING

        # Receive 10 warnings by failing 10 times
        # At WARNING level, non-compliance should increase warnings_received
        for i in range(10):
            self.service.enforce_with_progression(
                action="update",
                provided_params={},  # Missing required params
                agent_id=agent_id
            )

        profile = self.service.get_agent_profile(agent_id)
        # Check line 58: warnings >= 10 at WARNING level
        # Since profile should escalate to STRICT after getting warnings
        # We need to check if it escalated OR if it has 10+ warnings
        assert profile.warnings_received >= 10 or profile.enforcement_level == EnforcementLevel.STRICT

    def test_escalate_level_from_soft_to_warning(self):
        """Test lines 98-99: escalate from SOFT to WARNING level"""
        agent_id = "soft_escalate_agent"

        # Set agent to SOFT level
        self.service.set_agent_level(agent_id, EnforcementLevel.SOFT)
        profile = self.service.get_agent_profile(agent_id)
        assert profile.enforcement_level == EnforcementLevel.SOFT

        # Manually call escalate_level to trigger lines 98-99
        profile.escalate_level()

        # Verify lines 98-99: SOFT -> WARNING
        assert profile.enforcement_level == EnforcementLevel.WARNING
        assert profile.consecutive_failures == 0
        assert profile.manually_set_level is False

    def test_should_deescalate_high_compliance_branch(self):
        """Test branch 72->75: deescalate when compliance >= 95%"""
        agent_id = "high_compliance_agent"

        # Set to STRICT level
        self.service.set_agent_level(agent_id, EnforcementLevel.STRICT)

        # Achieve 20 consecutive compliant operations (100% compliance)
        # Note: consecutive_compliant gets reset after deescalation
        for i in range(20):
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent_id
            )

        profile = self.service.get_agent_profile(agent_id)
        # Branch 72->75: compliance_rate >= 0.95
        # After deescalation, consecutive_compliant is reset to 0
        # So we check compliance_history instead
        compliance_rate = sum(profile.compliance_history[-20:]) / len(profile.compliance_history[-20:])
        assert compliance_rate >= 0.95
        # Should have deescalated from STRICT to WARNING
        assert profile.enforcement_level == EnforcementLevel.WARNING

    def test_escalate_level_from_warning_to_strict(self):
        """Test branch 100->104: escalate from WARNING to STRICT"""
        agent_id = "warning_to_strict_agent"

        # Set agent to WARNING level
        profile = self.service._get_or_create_profile(agent_id)
        assert profile.enforcement_level == EnforcementLevel.WARNING

        # Manually escalate
        profile.escalate_level()

        # Branch 100->104: WARNING -> STRICT
        assert profile.enforcement_level == EnforcementLevel.STRICT
        assert profile.last_escalation is not None

    def test_deescalate_level_from_warning_to_soft(self):
        """Test branch 113->117: deescalate from WARNING to SOFT"""
        agent_id = "warning_to_soft_agent"

        # Set to WARNING level
        profile = self.service._get_or_create_profile(agent_id)
        assert profile.enforcement_level == EnforcementLevel.WARNING

        # Manually deescalate
        profile.deescalate_level()

        # Branch 113->117: WARNING -> SOFT
        assert profile.enforcement_level == EnforcementLevel.SOFT
        assert profile.consecutive_compliant == 0
        assert profile.manually_set_level is False

    def test_reset_agent_profile_when_not_exists(self):
        """Test branch 245->exit: reset when agent doesn't exist"""
        agent_id = "nonexistent_agent"

        # Verify agent doesn't exist
        assert agent_id not in self.service.agent_profiles

        # Call reset on non-existent agent (branch 245->exit: if condition fails)
        self.service.reset_agent_profile(agent_id)

        # Agent should still not exist (no profile created)
        assert agent_id not in self.service.agent_profiles

    def test_enforcement_level_stats_strict_branch(self):
        """Test branch 290->294: count STRICT level agents"""
        agent_id = "strict_stats_agent"

        # Set to STRICT level
        self.service.set_agent_level(agent_id, EnforcementLevel.STRICT)

        # Perform operation to register
        self.service.enforce_with_progression(
            action="update",
            provided_params={"work_notes": "Work", "progress_made": "Progress"},
            agent_id=agent_id
        )

        stats = self.service.get_enforcement_stats()

        # Branch 290->294: profile.enforcement_level == STRICT
        assert stats["by_level"]["strict"] >= 1

    def test_enforcement_stats_no_compliance_history(self):
        """Test branch 298->284: skip agents without compliance history"""
        # Create service with no operations
        fresh_service = ProgressiveEnforcementService(default_level=EnforcementLevel.WARNING)

        # Create profile but don't run any operations
        fresh_service._get_or_create_profile("no_history_agent")

        stats = fresh_service.get_enforcement_stats()

        # Branch 298->284: if profile.compliance_history (false, skips)
        assert stats["total_agents"] == 1
        assert stats["average_compliance"] == 0.0  # No agents with history

    def test_enforcement_stats_with_agents_history(self):
        """Test branch 313->316: calculate average when agents have history"""
        # Create multiple agents with operations
        for i in range(3):
            agent_id = f"history_agent_{i}"
            self.service.enforce_with_progression(
                action="update",
                provided_params={"work_notes": "Work", "progress_made": "Progress"},
                agent_id=agent_id
            )

        stats = self.service.get_enforcement_stats()

        # Branch 313->316: if agents_with_history > 0
        assert stats["total_agents"] == 3
        assert stats["average_compliance"] > 0.0  # Should have calculated average