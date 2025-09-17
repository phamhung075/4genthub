"""Parameter Enforcement Service for Manual Context System

This service enforces context parameter requirements based on action and configuration.
It provides progressive enforcement levels from logging-only to strict blocking.

Part of Phase 2: Core Enforcement Implementation
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


class EnforcementLevel(Enum):
    """Enforcement levels for parameter validation"""
    DISABLED = "disabled"  # No enforcement
    SOFT = "soft"  # Log only, no blocking
    WARNING = "warning"  # Warn but allow operation
    STRICT = "strict"  # Block operation if parameters missing


@dataclass
class EnforcementResult:
    """Result of parameter enforcement check"""
    allowed: bool  # Whether operation should proceed
    level: EnforcementLevel
    missing_required: List[str] = field(default_factory=list)
    missing_recommended: List[str] = field(default_factory=list)
    message: str = ""
    hints: List[str] = field(default_factory=list)
    examples: Dict[str, Any] = field(default_factory=dict)
    compliance_tracked: bool = False
    agent_id: Optional[str] = None


@dataclass
class AgentCompliance:
    """Track agent compliance statistics"""
    agent_id: str
    total_operations: int = 0
    compliant_operations: int = 0
    warnings_issued: int = 0
    operations_blocked: int = 0
    consecutive_failures: int = 0
    last_operation: Optional[datetime] = None
    compliance_rate: float = 0.0
    
    def update_compliance(self, is_compliant: bool, was_blocked: bool = False):
        """Update compliance statistics"""
        self.total_operations += 1
        if is_compliant:
            self.compliant_operations += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            if was_blocked:
                self.operations_blocked += 1
            else:
                self.warnings_issued += 1
        
        self.compliance_rate = (
            self.compliant_operations / self.total_operations 
            if self.total_operations > 0 else 0.0
        )
        self.last_operation = datetime.now(timezone.utc)


class ParameterEnforcementService:
    """Service to enforce context parameter requirements"""
    
    # Required parameters by action
    REQUIRED_PARAMS = {
        "update": {
            "strict": ["work_notes", "progress_made"],
            "recommended": ["files_modified", "blockers_encountered", "decisions_made"]
        },
        "complete": {
            "strict": ["completion_summary"],
            "recommended": ["testing_notes", "deployment_notes", "files_created", "files_modified"]
        },
        "create": {
            "strict": [],
            "recommended": ["estimated_effort", "initial_thoughts", "approach"]
        },
        "subtask_update": {
            "strict": ["progress_notes"],
            "recommended": ["blockers", "insights_found"]
        },
        "subtask_complete": {
            "strict": ["completion_summary"],
            "recommended": ["impact_on_parent", "insights_found", "testing_notes"]
        }
    }
    
    # Helpful parameter templates
    PARAMETER_TEMPLATES = {
        "work_notes": "Brief description of work being done (e.g., 'Refactoring authentication module')",
        "progress_made": "What was accomplished (e.g., 'Completed JWT implementation')",
        "completion_summary": "Detailed summary of what was completed (e.g., 'Implemented JWT auth with refresh tokens, added rate limiting, created comprehensive tests')",
        "testing_notes": "Testing performed (e.g., 'Unit tests added with 95% coverage, integration tests passing')",
        "files_modified": ["auth/jwt.py", "auth/middleware.py", "tests/test_auth.py"],
        "blockers_encountered": ["Redis connection timeout", "Missing API documentation"],
        "decisions_made": ["Use Redis for token storage", "Implement refresh token rotation"],
        "insights_found": ["Found existing utility for token generation", "Database index needed for performance"]
    }
    
    def __init__(self, enforcement_level: EnforcementLevel = EnforcementLevel.WARNING, user_id: Optional[str] = None):
        """Initialize enforcement service
        
        Args:
            enforcement_level: Default enforcement level
            user_id: User context for user-scoped enforcement
        """
        self._user_id = user_id  # Store user context
        self.enforcement_level = enforcement_level
        self.agent_compliance: Dict[str, AgentCompliance] = {}
        logger.info(f"ParameterEnforcementService initialized with level: {enforcement_level.value}")

    def with_user(self, user_id: str) -> 'ParameterEnforcementService':
        """Create a new service instance scoped to a specific user."""
        return ParameterEnforcementService(self.enforcement_level, user_id)
    
    def enforce(
        self,
        action: str,
        provided_params: Dict[str, Any],
        agent_id: Optional[str] = None,
        enforcement_level: Optional[EnforcementLevel] = None
    ) -> EnforcementResult:
        """Enforce parameter requirements for an action
        
        Args:
            action: The action being performed (update, complete, etc.)
            provided_params: Parameters provided by the agent
            agent_id: Optional agent identifier for tracking
            enforcement_level: Override default enforcement level
            
        Returns:
            EnforcementResult with enforcement decision
        """
        level = enforcement_level or self.enforcement_level
        
        # Check if enforcement is disabled
        if level == EnforcementLevel.DISABLED:
            return EnforcementResult(
                allowed=True,
                level=level,
                message="Parameter enforcement disabled"
            )
        
        # Get required parameters for action
        requirements = self.REQUIRED_PARAMS.get(action, {})
        strict_params = requirements.get("strict", [])
        recommended_params = requirements.get("recommended", [])
        
        # Check for missing parameters
        missing_required = [p for p in strict_params if p not in provided_params or not provided_params[p]]
        missing_recommended = [p for p in recommended_params if p not in provided_params or not provided_params[p]]
        
        # Track compliance
        is_compliant = len(missing_required) == 0
        if agent_id:
            self._track_enforcement(agent_id, is_compliant, level == EnforcementLevel.STRICT and not is_compliant)
        
        # Apply enforcement based on level
        if level == EnforcementLevel.SOFT:
            # Log only, always allow
            if missing_required or missing_recommended:
                logger.info(f"[SOFT] Missing parameters for {action}: required={missing_required}, recommended={missing_recommended}")
            return self._create_soft_result(missing_required, missing_recommended, agent_id)
        
        elif level == EnforcementLevel.WARNING:
            # Warn but allow
            if missing_required:
                logger.warning(f"[WARNING] Missing required parameters for {action}: {missing_required}")
            return self._create_warning_result(action, missing_required, missing_recommended, agent_id)
        
        elif level == EnforcementLevel.STRICT:
            # Block if required parameters missing
            if missing_required:
                logger.error(f"[STRICT] Blocking {action} due to missing required parameters: {missing_required}")
                return self._create_strict_result(action, missing_required, missing_recommended, agent_id)
            else:
                # All required parameters provided - return success result with STRICT level
                return EnforcementResult(
                    allowed=True,
                    level=EnforcementLevel.STRICT,
                    missing_required=missing_required,
                    missing_recommended=missing_recommended,
                    hints=[f"✅ All required parameters provided for {action}"] if missing_recommended else [],
                    examples={},
                    compliance_tracked=True,
                    agent_id=agent_id
                )
        
        return EnforcementResult(
            allowed=True,
            level=level,
            message="All required parameters provided"
        )
    
    def _create_soft_result(
        self,
        missing_required: List[str],
        missing_recommended: List[str],
        agent_id: Optional[str]
    ) -> EnforcementResult:
        """Create result for SOFT enforcement (log only)"""
        return EnforcementResult(
            allowed=True,
            level=EnforcementLevel.SOFT,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            message="Operation allowed (soft enforcement - logging only)",
            compliance_tracked=agent_id is not None,
            agent_id=agent_id
        )
    
    def _create_warning_result(
        self,
        action: str,
        missing_required: List[str],
        missing_recommended: List[str],
        agent_id: Optional[str]
    ) -> EnforcementResult:
        """Create result for WARNING enforcement"""
        hints = []
        examples = {}
        
        if missing_required:
            hints.append(f"⚠️ Missing required parameters: {', '.join(missing_required)}")
            hints.append("These parameters will be required in strict mode")
            
            for param in missing_required:
                if param in self.PARAMETER_TEMPLATES:
                    examples[param] = self.PARAMETER_TEMPLATES[param]
        
        if missing_recommended:
            hints.append(f"💡 Consider adding: {', '.join(missing_recommended)}")
        
        message = "Operation allowed with warnings" if missing_required else "Operation allowed"
        
        return EnforcementResult(
            allowed=True,
            level=EnforcementLevel.WARNING,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            message=message,
            hints=hints,
            examples=examples,
            compliance_tracked=agent_id is not None,
            agent_id=agent_id
        )
    
    def _create_strict_result(
        self,
        action: str,
        missing_required: List[str],
        missing_recommended: List[str],
        agent_id: Optional[str]
    ) -> EnforcementResult:
        """Create result for STRICT enforcement (blocking)"""
        hints = [
            f"❌ Operation blocked: Missing required parameters for {action}",
            f"Required: {', '.join(missing_required)}",
            "Please provide these parameters to proceed"
        ]
        
        if missing_recommended:
            hints.append(f"Also recommended: {', '.join(missing_recommended)}")
        
        # Provide helpful examples
        examples = {}
        for param in missing_required:
            if param in self.PARAMETER_TEMPLATES:
                examples[param] = self.PARAMETER_TEMPLATES[param]
        
        # Add example command
        if action == "complete":
            examples["example_command"] = {
                "action": "complete",
                "task_id": "<task_id>",
                "completion_summary": "Implemented feature X with Y approach, achieving Z results",
                "testing_notes": "Added unit tests with 90% coverage, all integration tests passing"
            }
        elif action == "update":
            examples["example_command"] = {
                "action": "update",
                "task_id": "<task_id>",
                "work_notes": "Working on authentication module refactoring",
                "progress_made": "Completed JWT token generation logic",
                "files_modified": ["auth/jwt.py", "auth/utils.py"]
            }
        
        return EnforcementResult(
            allowed=False,
            level=EnforcementLevel.STRICT,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            message=f"Operation blocked: Missing required parameters ({', '.join(missing_required)})",
            hints=hints,
            examples=examples,
            compliance_tracked=agent_id is not None,
            agent_id=agent_id
        )
    
    def _track_enforcement(self, agent_id: str, is_compliant: bool, was_blocked: bool):
        """Track agent compliance statistics"""
        if agent_id not in self.agent_compliance:
            self.agent_compliance[agent_id] = AgentCompliance(agent_id=agent_id)
        
        self.agent_compliance[agent_id].update_compliance(is_compliant, was_blocked)
        
        # Log if compliance is dropping
        compliance = self.agent_compliance[agent_id]
        if compliance.compliance_rate < 0.5 and compliance.total_operations >= 10:
            logger.warning(
                f"Low compliance for agent {agent_id}: "
                f"{compliance.compliance_rate:.1%} "
                f"({compliance.compliant_operations}/{compliance.total_operations})"
            )
    
    def get_agent_compliance(self, agent_id: str) -> Optional[AgentCompliance]:
        """Get compliance statistics for an agent"""
        return self.agent_compliance.get(agent_id)
    
    def get_all_compliance_stats(self) -> Dict[str, AgentCompliance]:
        """Get compliance statistics for all agents"""
        return self.agent_compliance.copy()
    
    def set_enforcement_level(self, level: EnforcementLevel):
        """Update the default enforcement level"""
        logger.info(f"Enforcement level changed from {self.enforcement_level.value} to {level.value}")
        self.enforcement_level = level
    
    def get_parameter_hints(self, action: str) -> Dict[str, Any]:
        """Get helpful hints for parameters required by an action"""
        requirements = self.REQUIRED_PARAMS.get(action, {})
        hints = {
            "action": action,
            "required": requirements.get("strict", []),
            "recommended": requirements.get("recommended", []),
            "templates": {}
        }
        
        # Add templates for all parameters
        all_params = requirements.get("strict", []) + requirements.get("recommended", [])
        for param in all_params:
            if param in self.PARAMETER_TEMPLATES:
                hints["templates"][param] = self.PARAMETER_TEMPLATES[param]
        
        return hints