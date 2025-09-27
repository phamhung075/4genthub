"""Progressive Enforcement Service for Manual Context System

This service implements gradual enforcement based on agent behavior.
New agents get more warnings before strict enforcement kicks in.

Part of Phase 2: Core Enforcement Implementation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import logging

from .parameter_enforcement_service import (
    EnforcementLevel,
    EnforcementResult,
    ParameterEnforcementService,
    AgentCompliance
)

logger = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    """Profile tracking agent's learning progress"""
    agent_id: str
    first_seen: datetime
    enforcement_level: EnforcementLevel
    operations_count: int = 0
    learning_phase_operations: int = 0
    warnings_received: int = 0
    consecutive_compliant: int = 0
    consecutive_failures: int = 0
    last_escalation: Optional[datetime] = None
    compliance_history: List[bool] = field(default_factory=list)
    manually_set_level: bool = False  # Track if level was manually set
    
    def should_escalate(self) -> bool:
        """Determine if agent should move to stricter enforcement"""
        # Don't escalate if already at strict
        if self.enforcement_level == EnforcementLevel.STRICT:
            return False
        
        # Escalate if too many consecutive failures
        if self.consecutive_failures >= 5:
            return True
        
        # Escalate if compliance rate is low after learning phase
        if self.operations_count >= 20:
            recent_compliance = self.compliance_history[-10:] if len(self.compliance_history) >= 10 else self.compliance_history
            compliance_rate = sum(recent_compliance) / len(recent_compliance) if recent_compliance else 0
            if compliance_rate < 0.6:  # Less than 60% compliance
                return True
        
        # Escalate if agent has been warned enough times
        if self.enforcement_level == EnforcementLevel.WARNING and self.warnings_received >= 10:
            return True
        
        return False
    
    def should_deescalate(self) -> bool:
        """Determine if agent can move to less strict enforcement"""
        # Don't deescalate if already at soft
        if self.enforcement_level == EnforcementLevel.SOFT:
            return False
        
        # Deescalate if consistently compliant
        if self.consecutive_compliant >= 20:
            recent_compliance = self.compliance_history[-20:] if len(self.compliance_history) >= 20 else self.compliance_history
            compliance_rate = sum(recent_compliance) / len(recent_compliance) if recent_compliance else 0
            if compliance_rate >= 0.95:  # 95% or higher compliance
                return True
        
        return False
    
    def update_compliance(self, is_compliant: bool, was_warned: bool = False):
        """Update compliance tracking"""
        self.operations_count += 1
        self.compliance_history.append(is_compliant)
        
        # Keep history limited to last 100 operations
        if len(self.compliance_history) > 100:
            self.compliance_history = self.compliance_history[-100:]
        
        if is_compliant:
            self.consecutive_compliant += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_compliant = 0
            if was_warned:
                self.warnings_received += 1
    
    def escalate_level(self):
        """Move to stricter enforcement level"""
        if self.enforcement_level == EnforcementLevel.SOFT:
            self.enforcement_level = EnforcementLevel.WARNING
            logger.info(f"Agent {self.agent_id} escalated to WARNING level")
        elif self.enforcement_level == EnforcementLevel.WARNING:
            self.enforcement_level = EnforcementLevel.STRICT
            logger.info(f"Agent {self.agent_id} escalated to STRICT level")
        
        self.last_escalation = datetime.now(timezone.utc)
        self.consecutive_failures = 0  # Reset counter after escalation
        self.manually_set_level = False  # Clear manual flag after automatic escalation
    
    def deescalate_level(self):
        """Move to less strict enforcement level"""
        if self.enforcement_level == EnforcementLevel.STRICT:
            self.enforcement_level = EnforcementLevel.WARNING
            logger.info(f"Agent {self.agent_id} deescalated to WARNING level")
        elif self.enforcement_level == EnforcementLevel.WARNING:
            self.enforcement_level = EnforcementLevel.SOFT
            logger.info(f"Agent {self.agent_id} deescalated to SOFT level")
        
        self.consecutive_compliant = 0  # Reset counter after deescalation
        self.manually_set_level = False  # Clear manual flag after automatic deescalation


class ProgressiveEnforcementService:
    """Service managing progressive enforcement based on agent behavior"""
    
    # Configuration for progressive enforcement
    DEFAULT_STARTING_LEVEL = EnforcementLevel.WARNING  # New agents start with warnings
    LEARNING_PHASE_OPERATIONS = 10  # Number of operations in learning phase
    ESCALATION_THRESHOLD_FAILURES = 5  # Consecutive failures before escalation
    DEESCALATION_THRESHOLD_SUCCESS = 20  # Consecutive successes before deescalation
    COMPLIANCE_RATE_THRESHOLD = 0.6  # Minimum acceptable compliance rate
    
    def __init__(
        self,
        enforcement_service: Optional[ParameterEnforcementService] = None,
        default_level: EnforcementLevel = DEFAULT_STARTING_LEVEL
    ):
        """Initialize progressive enforcement service
        
        Args:
            enforcement_service: The parameter enforcement service to use
            default_level: Default enforcement level for new agents
        """
        self.enforcement_service = enforcement_service or ParameterEnforcementService(default_level)
        self.default_level = default_level
        self.agent_profiles: Dict[str, AgentProfile] = {}
        logger.info(f"ProgressiveEnforcementService initialized with default level: {default_level.value}")
    
    def enforce_with_progression(
        self,
        action: str,
        provided_params: Dict[str, any],
        agent_id: str
    ) -> EnforcementResult:
        """Enforce parameters with progressive enforcement based on agent behavior
        
        Args:
            action: The action being performed
            provided_params: Parameters provided by the agent
            agent_id: Agent identifier
            
        Returns:
            EnforcementResult with progressive enforcement applied
        """
        # Get or create agent profile
        profile = self._get_or_create_profile(agent_id)
        
        # Determine enforcement level for this operation
        current_enforcement_level = profile.enforcement_level
        
        # Check if agent is in learning phase
        if profile.operations_count < self.LEARNING_PHASE_OPERATIONS:
            # More lenient during learning phase - override even manually set STRICT levels
            if current_enforcement_level == EnforcementLevel.STRICT:
                current_enforcement_level = EnforcementLevel.WARNING
        
        # Perform enforcement at determined level
        result = self.enforcement_service.enforce(
            action=action,
            provided_params=provided_params,
            agent_id=agent_id,
            enforcement_level=current_enforcement_level
        )
        
        # Update agent profile based on result
        is_compliant = len(result.missing_required) == 0
        was_warned = result.level == EnforcementLevel.WARNING and not is_compliant
        profile.update_compliance(is_compliant, was_warned)
        
        # Check for level changes
        if profile.should_escalate():
            old_level = profile.enforcement_level
            profile.escalate_level()
            result.hints.append(
                f"⚠️ Enforcement level increased from {old_level.value} to {profile.enforcement_level.value} "
                f"due to repeated non-compliance"
            )
        elif profile.should_deescalate():
            old_level = profile.enforcement_level
            profile.deescalate_level()
            result.hints.append(
                f"✅ Enforcement level decreased from {old_level.value} to {profile.enforcement_level.value} "
                f"due to consistent compliance"
            )
        
        # Add learning phase hints
        if profile.operations_count < self.LEARNING_PHASE_OPERATIONS:
            remaining = self.LEARNING_PHASE_OPERATIONS - profile.operations_count
            result.hints.append(
                f"📚 Learning phase: {remaining} operations remaining before standard enforcement"
            )
        
        # Add compliance statistics to result
        if profile.operations_count >= 10:
            recent_compliance = profile.compliance_history[-10:]
            compliance_rate = sum(recent_compliance) / len(recent_compliance) if recent_compliance else 0
            result.hints.append(
                f"📊 Recent compliance: {compliance_rate:.0%} "
                f"({sum(recent_compliance)}/10 operations)"
            )
        
        return result
    
    def _get_or_create_profile(self, agent_id: str) -> AgentProfile:
        """Get existing agent profile or create new one"""
        if agent_id not in self.agent_profiles:
            self.agent_profiles[agent_id] = AgentProfile(
                agent_id=agent_id,
                first_seen=datetime.now(timezone.utc),
                enforcement_level=self.default_level,
                learning_phase_operations=self.LEARNING_PHASE_OPERATIONS
            )
            logger.info(f"New agent profile created for {agent_id} with {self.default_level.value} enforcement")
        
        return self.agent_profiles[agent_id]
    
    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent's enforcement profile"""
        return self.agent_profiles.get(agent_id)
    
    def get_all_profiles(self) -> Dict[str, AgentProfile]:
        """Get all agent profiles"""
        return self.agent_profiles.copy()
    
    def reset_agent_profile(self, agent_id: str):
        """Reset an agent's profile to start fresh"""
        if agent_id in self.agent_profiles:
            old_profile = self.agent_profiles[agent_id]
            self.agent_profiles[agent_id] = AgentProfile(
                agent_id=agent_id,
                first_seen=datetime.now(timezone.utc),
                enforcement_level=self.default_level,
                learning_phase_operations=self.LEARNING_PHASE_OPERATIONS
            )
            logger.info(
                f"Reset profile for agent {agent_id}. "
                f"Previous: {old_profile.operations_count} operations, "
                f"{old_profile.enforcement_level.value} level"
            )
    
    def set_agent_level(self, agent_id: str, level: EnforcementLevel):
        """Manually set enforcement level for an agent"""
        profile = self._get_or_create_profile(agent_id)
        old_level = profile.enforcement_level
        profile.enforcement_level = level
        profile.manually_set_level = True  # Mark as manually set
        logger.info(f"Manually changed agent {agent_id} from {old_level.value} to {level.value}")
    
    def get_enforcement_stats(self) -> Dict[str, any]:
        """Get overall enforcement statistics"""
        stats = {
            "total_agents": len(self.agent_profiles),
            "by_level": {
                "soft": 0,
                "warning": 0,
                "strict": 0
            },
            "learning_phase": 0,
            "average_compliance": 0.0,
            "problem_agents": []
        }
        
        total_compliance = 0
        agents_with_history = 0
        
        for profile in self.agent_profiles.values():
            # Count by level
            if profile.enforcement_level == EnforcementLevel.SOFT:
                stats["by_level"]["soft"] += 1
            elif profile.enforcement_level == EnforcementLevel.WARNING:
                stats["by_level"]["warning"] += 1
            elif profile.enforcement_level == EnforcementLevel.STRICT:
                stats["by_level"]["strict"] += 1
            
            # Count learning phase
            if profile.operations_count < self.LEARNING_PHASE_OPERATIONS:
                stats["learning_phase"] += 1
            
            # Calculate compliance
            if profile.compliance_history:
                compliance_rate = sum(profile.compliance_history) / len(profile.compliance_history)
                total_compliance += compliance_rate
                agents_with_history += 1
                
                # Identify problem agents
                if compliance_rate < 0.5 and profile.operations_count >= 20:
                    stats["problem_agents"].append({
                        "agent_id": profile.agent_id,
                        "compliance_rate": compliance_rate,
                        "operations": profile.operations_count,
                        "level": profile.enforcement_level.value
                    })
        
        # Calculate average compliance
        if agents_with_history > 0:
            stats["average_compliance"] = total_compliance / agents_with_history
        
        return stats