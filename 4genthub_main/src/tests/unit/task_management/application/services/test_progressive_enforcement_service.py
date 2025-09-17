"""Unit Tests for ProgressiveEnforcementService

Tests the progressive enforcement service that gradually increases
enforcement based on agent behavior.

Part of Phase 2: Core Enforcement Implementation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from fastmcp.task_management.application.services.progressive_enforcement_service import (
    ProgressiveEnforcementService,
    AgentProfile,
    EnforcementLevel
)
from fastmcp.task_management.application.services.parameter_enforcement_service import (
    ParameterEnforcementService,
    EnforcementResult
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
        result = self.service.enforce_with_progression(
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