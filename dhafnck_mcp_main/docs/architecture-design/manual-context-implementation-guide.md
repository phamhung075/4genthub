# Manual Context System Implementation Guide
**Version**: 1.0  
**Date**: February 3, 2025  
**Purpose**: Step-by-step guide for implementing manual context system

## Overview

This guide provides concrete implementation steps with actual code changes needed to transform the current system into a parameter-driven manual context system.

## 1. New Files to Create

### 1.1 Context Parameter Extractor
**File**: `src/fastmcp/task_management/interface/utils/context_parameter_extractor.py`

```python
"""Context Parameter Extractor

Extracts context-relevant parameters from MCP tool calls for manual context updates.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextParameterExtractor:
    """
    Extracts and validates context parameters from MCP tool calls.
    
    This is the core of the manual context system - only parameters
    explicitly provided by AI agents are captured.
    """
    
    # Define all context-relevant parameters
    WORK_UPDATE_PARAMS = {
        'work_notes',        # Description of work performed
        'progress_made',     # Specific progress achieved
        'files_modified',    # List of modified files
        'files_created',     # List of created files
        'files_deleted',     # List of deleted files
    }
    
    INSIGHT_PARAMS = {
        'decisions_made',    # Technical/architectural decisions
        'blockers',          # Issues blocking progress
        'discoveries',       # Important findings
        'patterns_found',    # Reusable patterns identified
        'risks_identified',  # Potential risks discovered
    }
    
    COMPLETION_PARAMS = {
        'completion_summary',  # Required for task completion
        'testing_notes',       # Testing performed
        'deployment_notes',    # Deployment information
        'documentation_updates', # Docs created/updated
    }
    
    ALL_CONTEXT_PARAMS = WORK_UPDATE_PARAMS | INSIGHT_PARAMS | COMPLETION_PARAMS
    
    def __init__(self):
        self.extracted_count = 0
        self.last_extraction = None
    
    def extract_context_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only context-relevant parameters from the provided params.
        
        Args:
            params: All parameters from MCP tool call
            
        Returns:
            Dictionary containing only context-relevant parameters
        """
        # Extract only parameters that are explicitly provided
        context_params = {}
        
        for param_name in self.ALL_CONTEXT_PARAMS:
            if param_name in params and params[param_name]:
                # Only include non-empty values
                value = params[param_name]
                if isinstance(value, str) and value.strip():
                    context_params[param_name] = value.strip()
                elif isinstance(value, list) and value:
                    context_params[param_name] = value
                elif isinstance(value, dict) and value:
                    context_params[param_name] = value
                elif value:  # Other truthy values
                    context_params[param_name] = value
        
        # Log extraction for debugging
        if context_params:
            self.extracted_count += 1
            self.last_extraction = datetime.utcnow()
            logger.debug(f"Extracted {len(context_params)} context parameters: {list(context_params.keys())}")
        
        return context_params
    
    def has_work_updates(self, params: Dict[str, Any]) -> bool:
        """Check if params contain work update information"""
        return any(
            param in params and params[param] 
            for param in self.WORK_UPDATE_PARAMS
        )
    
    def has_insights(self, params: Dict[str, Any]) -> bool:
        """Check if params contain insights"""
        return any(
            param in params and params[param]
            for param in self.INSIGHT_PARAMS
        )
    
    def has_completion_data(self, params: Dict[str, Any]) -> bool:
        """Check if params contain completion data"""
        return any(
            param in params and params[param]
            for param in self.COMPLETION_PARAMS
        )
    
    def validate_work_notes(self, work_notes: str) -> tuple[bool, Optional[str]]:
        """
        Validate work notes meet minimum quality standards.
        
        Args:
            work_notes: Work notes to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not work_notes or not work_notes.strip():
            return False, "Work notes cannot be empty"
        
        word_count = len(work_notes.split())
        if word_count < 3:
            return False, "Work notes too brief - please describe what you did"
        
        # Check for placeholder text
        placeholders = ["todo", "tbd", "...", "placeholder", "n/a"]
        if any(p in work_notes.lower() for p in placeholders):
            return False, "Work notes contain placeholder text"
        
        return True, None
    
    def validate_completion_summary(self, summary: str) -> tuple[bool, Optional[str]]:
        """
        Validate completion summary meets requirements.
        
        Args:
            summary: Completion summary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not summary or not summary.strip():
            return False, "Completion summary is required"
        
        if len(summary) < 20:
            return False, "Completion summary too short (min 20 characters)"
        
        word_count = len(summary.split())
        if word_count < 5:
            return False, "Completion summary too brief - provide more detail"
        
        # Check for key completion indicators
        completion_words = ["completed", "finished", "implemented", "fixed", "added", "updated", "created"]
        if not any(word in summary.lower() for word in completion_words):
            return False, "Completion summary should describe what was accomplished"
        
        return True, None
    
    def suggest_missing_params(self, action: str, provided_params: Set[str]) -> List[str]:
        """
        Suggest context parameters that might be missing based on action.
        
        Args:
            action: The action being performed
            provided_params: Set of parameter names already provided
            
        Returns:
            List of suggested parameter names
        """
        suggestions = []
        
        if action == "update":
            # Suggest work update params if none provided
            if not any(p in provided_params for p in self.WORK_UPDATE_PARAMS):
                suggestions.extend(["work_notes", "progress_made"])
            
            # Suggest file tracking if code-related terms in params
            if self._seems_code_related(provided_params):
                if "files_modified" not in provided_params:
                    suggestions.append("files_modified")
        
        elif action == "complete":
            if "completion_summary" not in provided_params:
                suggestions.append("completion_summary")
            if "testing_notes" not in provided_params:
                suggestions.append("testing_notes")
        
        return suggestions
    
    def _seems_code_related(self, params: Set[str]) -> bool:
        """Check if parameters suggest code-related work"""
        code_indicators = ["code", "implement", "fix", "bug", "feature", "function", "class"]
        param_str = " ".join(params).lower()
        return any(indicator in param_str for indicator in code_indicators)
```

### 1.2 Parameter Enforcement Service
**File**: `src/fastmcp/task_management/application/services/parameter_enforcement_service.py`

```python
"""Parameter Enforcement Service

Enforces context parameter requirements for manual context system.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EnforcementLevel(Enum):
    """Enforcement levels for parameter requirements"""
    DISABLED = "disabled"
    SOFT = "soft"          # Log only
    WARNING = "warning"    # Warn but allow
    STRICT = "strict"      # Block operation


@dataclass
class EnforcementResult:
    """Result of parameter enforcement check"""
    allow: bool
    level: EnforcementLevel
    error: Optional[str] = None
    warnings: List[str] = None
    missing_params: List[str] = None
    suggestions: List[str] = None
    hint: Optional[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.missing_params is None:
            self.missing_params = []
        if self.suggestions is None:
            self.suggestions = []


class ParameterEnforcementService:
    """
    Enforces context parameter requirements based on action and configuration.
    
    This service implements the enforcement logic for the manual context system,
    ensuring AI agents provide necessary context through parameters.
    """
    
    # Define required parameters by action
    REQUIRED_PARAMS = {
        "update": {
            "strict": ["work_notes", "progress_made"],
            "recommended": ["files_modified", "blockers"]
        },
        "complete": {
            "strict": ["completion_summary"],
            "recommended": ["testing_notes", "files_created"]
        },
        "create": {
            "strict": [],  # No context params required for creation
            "recommended": ["estimated_effort", "initial_thoughts"]
        }
    }
    
    # Helpful hints for missing parameters
    PARAM_HINTS = {
        "work_notes": "Describe what work you performed (e.g., 'Implemented user authentication using JWT')",
        "progress_made": "Specify concrete progress (e.g., 'Added login and logout endpoints')",
        "files_modified": "List files you changed (e.g., ['src/auth.py', 'routes.py'])",
        "completion_summary": "Provide detailed summary of completed work (min 20 chars)",
        "testing_notes": "Describe testing performed (e.g., 'Added unit tests, all passing')",
        "blockers": "List any blocking issues (e.g., ['Waiting for API documentation'])"
    }
    
    def __init__(self, enforcement_level: EnforcementLevel = EnforcementLevel.WARNING):
        self.default_level = enforcement_level
        self.enforcement_stats = {}
    
    def enforce(
        self, 
        action: str, 
        params: Dict[str, Any],
        agent_id: Optional[str] = None,
        override_level: Optional[EnforcementLevel] = None
    ) -> EnforcementResult:
        """
        Enforce parameter requirements for the given action.
        
        Args:
            action: The action being performed
            params: Parameters provided
            agent_id: Optional agent identifier for tracking
            override_level: Override the default enforcement level
            
        Returns:
            EnforcementResult with enforcement decision
        """
        level = override_level or self.default_level
        
        # No enforcement if disabled
        if level == EnforcementLevel.DISABLED:
            return EnforcementResult(allow=True, level=level)
        
        # Get requirements for action
        requirements = self.REQUIRED_PARAMS.get(action, {})
        if not requirements:
            return EnforcementResult(allow=True, level=level)
        
        # Check strict requirements
        strict_params = requirements.get("strict", [])
        missing_strict = [p for p in strict_params if not params.get(p)]
        
        # Check recommended parameters
        recommended_params = requirements.get("recommended", [])
        missing_recommended = [p for p in recommended_params if not params.get(p)]
        
        # Build result based on level
        if missing_strict:
            if level == EnforcementLevel.STRICT:
                return self._create_strict_result(action, missing_strict, missing_recommended)
            elif level == EnforcementLevel.WARNING:
                return self._create_warning_result(action, missing_strict, missing_recommended)
            else:  # SOFT
                return self._create_soft_result(action, missing_strict, missing_recommended)
        
        # No strict params missing, but maybe recommended ones
        if missing_recommended:
            result = EnforcementResult(
                allow=True,
                level=level,
                warnings=[f"Consider providing: {', '.join(missing_recommended)}"],
                suggestions=missing_recommended
            )
        else:
            result = EnforcementResult(allow=True, level=level)
        
        # Track statistics
        if agent_id:
            self._track_enforcement(agent_id, action, bool(missing_strict))
        
        return result
    
    def _create_strict_result(
        self, 
        action: str, 
        missing_strict: List[str],
        missing_recommended: List[str]
    ) -> EnforcementResult:
        """Create result for strict enforcement"""
        hints = []
        for param in missing_strict:
            if param in self.PARAM_HINTS:
                hints.append(f"• {param}: {self.PARAM_HINTS[param]}")
        
        return EnforcementResult(
            allow=False,
            level=EnforcementLevel.STRICT,
            error=f"Missing required parameters for {action}: {', '.join(missing_strict)}",
            missing_params=missing_strict,
            suggestions=missing_strict + missing_recommended,
            hint="Required parameters:\n" + "\n".join(hints) if hints else None
        )
    
    def _create_warning_result(
        self,
        action: str,
        missing_strict: List[str],
        missing_recommended: List[str]
    ) -> EnforcementResult:
        """Create result for warning enforcement"""
        return EnforcementResult(
            allow=True,
            level=EnforcementLevel.WARNING,
            warnings=[
                f"Missing recommended parameters: {', '.join(missing_strict)}",
                "Future versions will require these parameters"
            ],
            missing_params=missing_strict,
            suggestions=missing_strict + missing_recommended,
            hint=f"Tip: Include {missing_strict[0]} to track your work"
        )
    
    def _create_soft_result(
        self,
        action: str,
        missing_strict: List[str],
        missing_recommended: List[str]
    ) -> EnforcementResult:
        """Create result for soft enforcement"""
        logger.info(f"Soft enforcement: {action} missing {missing_strict}")
        return EnforcementResult(
            allow=True,
            level=EnforcementLevel.SOFT,
            suggestions=missing_strict + missing_recommended
        )
    
    def _track_enforcement(self, agent_id: str, action: str, had_violation: bool):
        """Track enforcement statistics by agent"""
        key = f"{agent_id}:{action}"
        if key not in self.enforcement_stats:
            self.enforcement_stats[key] = {
                "total": 0,
                "violations": 0,
                "compliance_rate": 1.0
            }
        
        stats = self.enforcement_stats[key]
        stats["total"] += 1
        if had_violation:
            stats["violations"] += 1
        stats["compliance_rate"] = 1 - (stats["violations"] / stats["total"])
    
    def get_agent_compliance(self, agent_id: str) -> Dict[str, float]:
        """Get compliance statistics for an agent"""
        agent_stats = {}
        for key, stats in self.enforcement_stats.items():
            if key.startswith(f"{agent_id}:"):
                action = key.split(":")[1]
                agent_stats[action] = stats["compliance_rate"]
        return agent_stats
```

### 1.3 Response Enrichment Service
**File**: `src/fastmcp/task_management/application/services/response_enrichment_service.py`

```python
"""Response Enrichment Service

Enriches MCP responses with context reminders, templates, and helpful hints.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContextState:
    """Current state of task context"""
    task_id: str
    last_update: Optional[datetime]
    update_count: int
    has_completion_summary: bool
    progress_percentage: float
    
    def is_stale(self, threshold_minutes: int = 30) -> bool:
        """Check if context is stale"""
        if not self.last_update:
            return True
        age = datetime.utcnow() - self.last_update
        return age > timedelta(minutes=threshold_minutes)
    
    def minutes_since_update(self) -> Optional[int]:
        """Get minutes since last update"""
        if not self.last_update:
            return None
        age = datetime.utcnow() - self.last_update
        return int(age.total_seconds() / 60)


class ResponseEnrichmentService:
    """
    Enriches responses with context-aware hints and templates.
    
    This service enhances the user experience by providing helpful
    reminders, templates, and visual indicators in responses.
    """
    
    def __init__(self):
        self.template_cache = {}
        self.enrichment_count = 0
    
    def enrich_response(
        self,
        base_response: Dict[str, Any],
        context_state: Optional[ContextState] = None,
        action: Optional[str] = None,
        enforcement_result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Enrich response with context information and helpful additions.
        
        Args:
            base_response: The base response to enrich
            context_state: Current context state
            action: The action that was performed
            enforcement_result: Parameter enforcement result
            
        Returns:
            Enriched response dictionary
        """
        enriched = base_response.copy()
        
        # Add context status indicator
        if context_state:
            enriched["context_status"] = self._get_context_status(context_state)
            
            # Add staleness reminder if needed
            if context_state.is_stale():
                enriched["context_reminder"] = self._create_staleness_reminder(context_state)
        
        # Add enforcement warnings
        if enforcement_result and enforcement_result.warnings:
            enriched["parameter_warnings"] = enforcement_result.warnings
        
        # Add update template if appropriate
        if action in ["update", "get"] and context_state:
            if context_state.is_stale() or action == "get":
                enriched["suggested_update"] = self._create_update_template(
                    context_state.task_id,
                    action
                )
        
        # Add completion template for in-progress tasks
        if action == "get" and context_state:
            if 70 <= context_state.progress_percentage < 100:
                enriched["completion_template"] = self._create_completion_template(
                    context_state.task_id
                )
        
        # Add visual progress indicator
        if context_state and "progress" not in enriched:
            enriched["progress_indicator"] = self._create_progress_indicator(
                context_state.progress_percentage
            )
        
        # Add next action hint
        if action:
            enriched["next_action_hint"] = self._suggest_next_action(action, context_state)
        
        self.enrichment_count += 1
        return enriched
    
    def _get_context_status(self, state: ContextState) -> str:
        """Get visual context status indicator"""
        if not state.last_update:
            return "❌ No context"
        
        minutes = state.minutes_since_update()
        if minutes < 5:
            return "✅ Fresh"
        elif minutes < 30:
            return "🟡 Recent"
        elif minutes < 60:
            return "🟠 Getting stale"
        else:
            return "🔴 Stale"
    
    def _create_staleness_reminder(self, state: ContextState) -> str:
        """Create context staleness reminder"""
        minutes = state.minutes_since_update()
        
        if not minutes:
            return "⚠️ No context updates recorded - please update"
        
        if minutes < 60:
            return f"⚠️ Context last updated {minutes} minutes ago - consider updating"
        else:
            hours = minutes // 60
            return f"⚠️ Context last updated {hours} hours ago - please update"
    
    def _create_update_template(self, task_id: str, action: str) -> Dict[str, str]:
        """Create context update template"""
        return {
            "quick_update": f'''manage_task(
    action="update",
    task_id="{task_id}",
    work_notes="[Describe what you did]",
    progress_made="[Specific progress achieved]",
    files_modified=["file1.py", "file2.js"]  # Optional
)''',
            "detailed_update": f'''manage_context(
    action="update",
    level="task",
    context_id="{task_id}",
    data={{
        "progress": {{
            "recent_work": ["Task 1 completed", "Task 2 in progress"],
            "blockers": ["Waiting for API docs"],
            "next_steps": ["Implement error handling", "Add tests"]
        }},
        "technical_notes": {{
            "decisions": ["Chose PostgreSQL for persistence"],
            "patterns": ["Repository pattern for data access"],
            "risks": ["Performance with large datasets"]
        }}
    }}
)''',
            "tip": "Use quick_update for regular progress, detailed_update for major milestones"
        }
    
    def _create_completion_template(self, task_id: str) -> Dict[str, str]:
        """Create task completion template"""
        return {
            "template": f'''manage_task(
    action="complete",
    task_id="{task_id}",
    completion_summary="[Detailed summary of what was accomplished - min 20 chars]",
    testing_notes="[Testing performed and results]",  # Recommended
    files_created=["new_file1.py", "new_file2.js"],  # Optional
    patterns_identified={{  # Optional
        "authentication": "JWT-based auth pattern",
        "error_handling": "Centralized error middleware"
    }}
)''',
            "checklist": [
                "✓ All requirements completed?",
                "✓ Tests written and passing?", 
                "✓ Documentation updated?",
                "✓ Code reviewed?"
            ],
            "tip": "Completion summary should describe what was built and how it works"
        }
    
    def _create_progress_indicator(self, percentage: float) -> str:
        """Create visual progress indicator"""
        filled = int(percentage / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        
        if percentage < 25:
            emoji = "🚀"  # Just started
        elif percentage < 50:
            emoji = "🏗️"  # Building
        elif percentage < 75:
            emoji = "⚙️"  # Working
        elif percentage < 100:
            emoji = "🔧"  # Finishing
        else:
            emoji = "✅"  # Complete
            
        return f"{emoji} [{bar}] {percentage:.0f}%"
    
    def _suggest_next_action(
        self, 
        current_action: str,
        state: Optional[ContextState]
    ) -> str:
        """Suggest next action based on current action and state"""
        if current_action == "create":
            return "Next: Start work and update context with initial progress"
        
        elif current_action == "update":
            if state and state.progress_percentage >= 90:
                return "Next: Consider completing the task if all work is done"
            else:
                return "Next: Continue work and update regularly (every 30-60 min)"
        
        elif current_action == "get":
            if state and state.is_stale():
                return "Next: Update context before continuing work"
            elif state and state.progress_percentage >= 70:
                return "Next: Review remaining work and plan completion"
            else:
                return "Next: Continue with planned work"
        
        elif current_action == "complete":
            return "Next: Move to next priority task or update project status"
        
        return "Next: Check task status and plan next steps"
```

### 1.4 Progressive Enforcement Service
**File**: `src/fastmcp/task_management/application/services/progressive_enforcement_service.py`

```python
"""Progressive Enforcement Service

Implements gradual enforcement of parameter requirements.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Agent compliance levels"""
    LEARNING = "learning"      # New agent, gentle guidance
    IMPROVING = "improving"    # Some compliance, increasing enforcement  
    COMPLIANT = "compliant"    # Good compliance, normal enforcement
    EXPERT = "expert"          # Excellent compliance, minimal reminders


@dataclass
class AgentCompliance:
    """Track agent compliance statistics"""
    agent_id: str
    total_operations: int = 0
    compliant_operations: int = 0
    consecutive_failures: int = 0
    last_warning_count: int = 0
    warnings_issued: int = 0
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_operation: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def compliance_rate(self) -> float:
        """Calculate compliance rate"""
        if self.total_operations == 0:
            return 1.0  # New agents start with perfect score
        return self.compliant_operations / self.total_operations
    
    @property
    def level(self) -> ComplianceLevel:
        """Determine agent's compliance level"""
        if self.total_operations < 5:
            return ComplianceLevel.LEARNING
        elif self.compliance_rate < 0.6:
            return ComplianceLevel.LEARNING
        elif self.compliance_rate < 0.8:
            return ComplianceLevel.IMPROVING
        elif self.compliance_rate < 0.95:
            return ComplianceLevel.COMPLIANT
        else:
            return ComplianceLevel.EXPERT


class ProgressiveEnforcementService:
    """
    Implements progressive enforcement based on agent behavior.
    
    New agents get gentle guidance, while repeat offenders
    face stricter enforcement.
    """
    
    # Warning thresholds by compliance level
    WARNING_THRESHOLDS = {
        ComplianceLevel.LEARNING: 5,     # Very patient with new agents
        ComplianceLevel.IMPROVING: 3,    # Some patience
        ComplianceLevel.COMPLIANT: 2,    # Quick escalation
        ComplianceLevel.EXPERT: 1        # Immediate enforcement
    }
    
    def __init__(self):
        self.agent_stats: Dict[str, AgentCompliance] = {}
        self.enforcement_enabled = True
    
    def check_compliance(
        self,
        agent_id: str,
        action: str,
        has_required_params: bool,
        missing_params: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if operation should be allowed based on progressive enforcement.
        
        Args:
            agent_id: Agent identifier
            action: Action being performed
            has_required_params: Whether required parameters were provided
            missing_params: List of missing parameter names
            
        Returns:
            Tuple of (allow_operation, warning_message, enforcement_message)
        """
        if not self.enforcement_enabled:
            return True, None, None
        
        # Get or create agent stats
        if agent_id not in self.agent_stats:
            self.agent_stats[agent_id] = AgentCompliance(agent_id=agent_id)
        
        stats = self.agent_stats[agent_id]
        stats.total_operations += 1
        stats.last_operation = datetime.utcnow()
        
        # If compliant, reset failures and allow
        if has_required_params:
            stats.compliant_operations += 1
            stats.consecutive_failures = 0
            stats.last_warning_count = 0
            return True, None, None
        
        # Not compliant - check progressive enforcement
        stats.consecutive_failures += 1
        threshold = self.WARNING_THRESHOLDS[stats.level]
        
        if stats.consecutive_failures <= threshold:
            # Still in warning phase
            warning = self._create_warning_message(
                stats,
                action,
                missing_params,
                threshold
            )
            stats.warnings_issued += 1
            return True, warning, None
        else:
            # Exceeded threshold - enforce
            enforcement = self._create_enforcement_message(
                stats,
                action,
                missing_params
            )
            return False, None, enforcement
    
    def _create_warning_message(
        self,
        stats: AgentCompliance,
        action: str,
        missing_params: Optional[List[str]],
        threshold: int
    ) -> str:
        """Create progressive warning message"""
        remaining = threshold - stats.consecutive_failures + 1
        
        if stats.level == ComplianceLevel.LEARNING:
            # Gentle guidance for new agents
            message = (
                f"👋 Hi! I notice you're not including context parameters. "
                f"For '{action}' operations, it's helpful to include: {', '.join(missing_params or [])}. "
                f"This helps track your progress! "
                f"({remaining} more reminder{'s' if remaining != 1 else ''} before this becomes required)"
            )
        
        elif stats.level == ComplianceLevel.IMPROVING:
            # Firmer but still friendly
            message = (
                f"⚠️ Context parameters missing for '{action}'. "
                f"Please include: {', '.join(missing_params or [])}. "
                f"({remaining} warning{'s' if remaining != 1 else ''} remaining)"
            )
        
        else:  # COMPLIANT or EXPERT
            # Direct and clear
            message = (
                f"❗ Missing required: {', '.join(missing_params or [])}. "
                f"({remaining} warning{'s' if remaining != 1 else ''} left)"
            )
        
        # Add helpful tip based on frequency
        if stats.consecutive_failures == 1:
            message += "\n💡 Tip: Context helps AI agents collaborate effectively!"
        elif stats.consecutive_failures == threshold:
            message += "\n⚠️ Next operation without context will be blocked."
        
        return message
    
    def _create_enforcement_message(
        self,
        stats: AgentCompliance,
        action: str,
        missing_params: Optional[List[str]]
    ) -> str:
        """Create enforcement message when blocking operation"""
        params_str = ', '.join(missing_params or [])
        
        # Message based on compliance history
        if stats.compliance_rate < 0.3:
            message = (
                f"🛑 Operation blocked: Context parameters are required.\n"
                f"Missing: {params_str}\n\n"
                f"Your compliance rate is {stats.compliance_rate:.0%}. "
                f"Let's work on building better habits! "
                f"Including context helps you and other agents work together effectively."
            )
        else:
            message = (
                f"🚫 Operation blocked: Required parameters missing.\n"
                f"Missing: {params_str}\n\n"
                f"You've had {stats.warnings_issued} warnings. "
                f"Please include the required parameters to continue."
            )
        
        # Add example
        message += f"\n\nExample for '{action}':\n"
        if action == "update":
            message += '''manage_task(
    action="update",
    task_id="...",
    work_notes="Description of work done",
    progress_made="Specific achievements"
)'''
        elif action == "complete":
            message += '''manage_task(
    action="complete", 
    task_id="...",
    completion_summary="Detailed summary of completed work"
)'''
        
        return message
    
    def get_agent_report(self, agent_id: str) -> Dict[str, Any]:
        """Get compliance report for an agent"""
        if agent_id not in self.agent_stats:
            return {"status": "No data available"}
        
        stats = self.agent_stats[agent_id]
        return {
            "agent_id": agent_id,
            "compliance_level": stats.level.value,
            "compliance_rate": f"{stats.compliance_rate:.1%}",
            "total_operations": stats.total_operations,
            "compliant_operations": stats.compliant_operations,
            "warnings_issued": stats.warnings_issued,
            "consecutive_failures": stats.consecutive_failures,
            "first_seen": stats.first_seen.isoformat(),
            "last_operation": stats.last_operation.isoformat(),
            "enforcement_threshold": self.WARNING_THRESHOLDS[stats.level]
        }
    
    def promote_agent(self, agent_id: str):
        """Manually promote agent to next compliance level"""
        if agent_id in self.agent_stats:
            stats = self.agent_stats[agent_id]
            # Boost compliance rate
            bonus_compliant = int(stats.total_operations * 0.1)
            stats.compliant_operations = min(
                stats.compliant_operations + bonus_compliant,
                stats.total_operations
            )
            logger.info(f"Promoted agent {agent_id} - new rate: {stats.compliance_rate:.1%}")
```

## 2. Files to Modify

### 2.1 Update Parameter Validation Fix
**File**: `src/fastmcp/task_management/interface/utils/parameter_validation_fix.py`

Add to the existing file (after line 58):

```python
# Add new parameter categories for context updates
CONTEXT_UPDATE_PARAMETERS = {
    'work_notes', 'progress_made', 'files_modified', 'files_created',
    'files_deleted', 'decisions_made', 'blockers', 'discoveries',
    'patterns_found', 'risks_identified'
}

# Add to all parameters
ALL_CONTEXT_PARAMS = CONTEXT_UPDATE_PARAMETERS | {'completion_summary', 'testing_notes'}

# Validation functions for context parameters
@classmethod
def validate_context_params(cls, params: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate context-specific parameters.
    
    Returns:
        Dict mapping parameter names to list of validation errors
    """
    errors = {}
    
    # Validate work_notes if present
    if 'work_notes' in params:
        work_notes = params['work_notes']
        if isinstance(work_notes, str):
            if len(work_notes.strip()) < 10:
                errors.setdefault('work_notes', []).append(
                    "Work notes too brief (min 10 characters)"
                )
            if work_notes.lower() in ['todo', 'tbd', 'n/a', '...']:
                errors.setdefault('work_notes', []).append(
                    "Work notes contain placeholder text"
                )
    
    # Validate completion_summary if present  
    if 'completion_summary' in params:
        summary = params['completion_summary']
        if isinstance(summary, str):
            if len(summary.strip()) < 20:
                errors.setdefault('completion_summary', []).append(
                    "Completion summary too short (min 20 characters)"
                )
            word_count = len(summary.split())
            if word_count < 5:
                errors.setdefault('completion_summary', []).append(
                    "Completion summary needs more detail (min 5 words)"
                )
    
    # Validate file lists
    for param in ['files_modified', 'files_created', 'files_deleted']:
        if param in params:
            files = params[param]
            if isinstance(files, list):
                for file_path in files:
                    if '..' in str(file_path):
                        errors.setdefault(param, []).append(
                            f"Invalid file path: {file_path}"
                        )
    
    return errors
```

### 2.2 Enhance Task MCP Controller
**File**: `src/fastmcp/task_management/interface/controllers/task_mcp_controller.py`

Add imports after line 15:

```python
from ..utils.context_parameter_extractor import ContextParameterExtractor
from ...application.services.parameter_enforcement_service import (
    ParameterEnforcementService, EnforcementLevel
)
from ...application.services.response_enrichment_service import (
    ResponseEnrichmentService, ContextState
)
from ...application.services.progressive_enforcement_service import (
    ProgressiveEnforcementService
)
```

Update __init__ method (after line 94):

```python
# Add new services
self._context_extractor = ContextParameterExtractor()
self._enforcement_service = ParameterEnforcementService(
    EnforcementLevel.WARNING  # Start with warnings
)
self._enrichment_service = ResponseEnrichmentService()
self._progressive_enforcement = ProgressiveEnforcementService()

logger.info("TaskMCPController initialized with manual context system")
```

Update manage_task method (replace the existing method around line 350):

```python
async def manage_task(
    self,
    action: Annotated[str, Field(description="Task management action")],
    task_id: Optional[Annotated[str, Field(description="Task ID")]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Handle task management operations with manual context parameter enforcement.
    
    This method now enforces context parameter requirements to ensure
    AI agents provide necessary context through explicit parameters.
    """
    try:
        logger.info(f"Managing task with action: {action}")
        
        # Extract agent ID if provided
        agent_id = kwargs.get('agent_id', 'unknown')
        
        # Phase 1: Extract context parameters
        context_params = self._context_extractor.extract_context_params(kwargs)
        logger.debug(f"Extracted context params: {list(context_params.keys())}")
        
        # Phase 2: Parameter enforcement
        enforcement_result = self._enforcement_service.enforce(
            action=action,
            params=kwargs,
            agent_id=agent_id
        )
        
        # Phase 3: Progressive enforcement check
        if not enforcement_result.allow:
            # Check progressive enforcement
            allow, warning, enforcement_msg = self._progressive_enforcement.check_compliance(
                agent_id=agent_id,
                action=action,
                has_required_params=False,
                missing_params=enforcement_result.missing_params
            )
            
            if not allow:
                # Operation blocked
                return StandardResponseFormatter.create_error_response(
                    error=enforcement_msg or enforcement_result.error,
                    error_code=ErrorCodes.VALIDATION_ERROR,
                    details={
                        "missing_parameters": enforcement_result.missing_params,
                        "hint": enforcement_result.hint,
                        "suggestions": enforcement_result.suggestions,
                        "compliance_report": self._progressive_enforcement.get_agent_report(agent_id)
                    }
                )
            elif warning:
                # Add warning to response later
                enforcement_result.warnings = [warning]
        
        # Phase 4: Execute the action
        # ... existing action execution logic ...
        
        # Get task facade
        if not hasattr(self, '_facade') or self._facade is None:
            self._facade = self._task_facade_factory.create_task_facade()
        
        # Execute based on action
        if action == "create":
            result = await self._handle_create(kwargs)
        elif action == "update":
            result = await self._handle_update(task_id, kwargs, context_params)
        elif action == "complete":
            result = await self._handle_complete(task_id, kwargs)
        elif action == "get":
            result = await self._handle_get(task_id, kwargs)
        elif action == "list":
            result = await self._handle_list(kwargs)
        elif action == "search":
            result = await self._handle_search(kwargs)
        elif action == "next":
            result = await self._handle_next(kwargs)
        elif action == "add_dependency":
            result = await self._handle_add_dependency(task_id, kwargs)
        elif action == "remove_dependency":
            result = await self._handle_remove_dependency(task_id, kwargs)
        else:
            return StandardResponseFormatter.create_error_response(
                error=f"Unknown action: {action}",
                error_code=ErrorCodes.INVALID_ACTION
            )
        
        # Phase 5: Update context if parameters provided
        if context_params and task_id and result.get("success"):
            try:
                await self._update_task_context(task_id, context_params)
                result["context_updated"] = True
                result["context_params_processed"] = list(context_params.keys())
            except Exception as e:
                logger.warning(f"Failed to update context: {e}")
                result["context_update_warning"] = str(e)
        
        # Phase 6: Get context state for enrichment
        context_state = None
        if task_id:
            try:
                context_state = await self._get_context_state(task_id)
            except Exception as e:
                logger.debug(f"Could not get context state: {e}")
        
        # Phase 7: Enrich response
        enriched_result = self._enrichment_service.enrich_response(
            base_response=result,
            context_state=context_state,
            action=action,
            enforcement_result=enforcement_result
        )
        
        # Phase 8: Add progressive enforcement report if requested
        if kwargs.get('include_compliance_report'):
            enriched_result['compliance_report'] = self._progressive_enforcement.get_agent_report(agent_id)
        
        return enriched_result
        
    except Exception as e:
        logger.error(f"Error in manage_task: {str(e)}", exc_info=True)
        return StandardResponseFormatter.create_error_response(
            error=str(e),
            error_code=ErrorCodes.INTERNAL_ERROR
        )
```

Add new helper methods:

```python
async def _handle_update(
    self, 
    task_id: str, 
    params: Dict[str, Any],
    context_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle task update with context parameter tracking"""
    if not task_id:
        return StandardResponseFormatter.create_error_response(
            error="task_id is required for update action",
            error_code=ErrorCodes.MISSING_FIELD
        )
    
    # Create update request
    update_request = UpdateTaskRequest(task_id=task_id)
    
    # Map parameters to request fields
    if "status" in params:
        update_request.status = params["status"]
    if "priority" in params:
        update_request.priority = params["priority"]
    # ... other fields ...
    
    # Execute update
    facade_response = await self._facade.update_task(update_request)
    
    # Note context params in response
    if context_params:
        facade_response["context_captured"] = {
            "work_notes": context_params.get("work_notes"),
            "progress_made": context_params.get("progress_made"),
            "files_modified": context_params.get("files_modified"),
            "param_count": len(context_params)
        }
    
    return self._standardize_facade_response(facade_response, "update")

async def _update_task_context(
    self,
    task_id: str,
    context_params: Dict[str, Any]
) -> None:
    """Update task context with parameters"""
    # Get context facade
    context_facade = self._context_facade_factory.create()
    
    # Prepare context update
    context_update = {
        "progress": {},
        "technical": {},
        "notes": {}
    }
    
    # Map parameters to context structure
    if "work_notes" in context_params:
        context_update["progress"]["recent_work"] = context_params["work_notes"]
    
    if "progress_made" in context_params:
        context_update["progress"]["achievements"] = context_params["progress_made"]
    
    if "files_modified" in context_params:
        context_update["technical"]["modified_files"] = context_params["files_modified"]
    
    if "decisions_made" in context_params:
        context_update["notes"]["decisions"] = context_params["decisions_made"]
    
    if "blockers" in context_params:
        context_update["progress"]["blockers"] = context_params["blockers"]
    
    # Update context
    await context_facade.update_context(
        level="task",
        context_id=task_id,
        data=context_update
    )

async def _get_context_state(self, task_id: str) -> Optional[ContextState]:
    """Get current context state for a task"""
    try:
        # Get context
        context_facade = self._context_facade_factory.create()
        context = await context_facade.get_context(
            level="task",
            context_id=task_id
        )
        
        if not context or not context.get("data"):
            return None
        
        # Extract state information
        data = context["data"]
        metadata = data.get("metadata", {})
        progress = data.get("progress", {})
        
        # Parse last update time
        last_update = None
        if updated_at := metadata.get("updated_at"):
            try:
                last_update = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except:
                pass
        
        return ContextState(
            task_id=task_id,
            last_update=last_update,
            update_count=metadata.get("update_count", 0),
            has_completion_summary=bool(progress.get("completion_summary")),
            progress_percentage=progress.get("completion_percentage", 0.0)
        )
        
    except Exception as e:
        logger.debug(f"Could not get context state: {e}")
        return None
```

### 2.3 Update Workflow Hint Enhancer
**File**: `src/fastmcp/task_management/interface/controllers/workflow_hint_enhancer.py`

Add new method after line 200:

```python
def enhance_with_context_requirements(
    self,
    response: Dict[str, Any],
    action: str,
    has_context_params: bool
) -> Dict[str, Any]:
    """
    Enhance response with context parameter requirements.
    
    Args:
        response: Response to enhance
        action: Action being performed
        has_context_params: Whether context parameters were provided
        
    Returns:
        Enhanced response
    """
    # Add context parameter hints based on action
    if action == "update" and not has_context_params:
        response["context_hint"] = {
            "message": "💡 Remember to include context parameters",
            "required": ["work_notes", "progress_made"],
            "optional": ["files_modified", "blockers", "decisions_made"],
            "example": '''manage_task(
    action="update",
    task_id="...",
    work_notes="Implemented user authentication",
    progress_made="Added login and logout endpoints",
    files_modified=["auth.py", "routes.py"]
)'''
        }
    
    elif action == "complete":
        response["completion_requirements"] = {
            "required": ["completion_summary"],
            "recommended": ["testing_notes"],
            "tips": [
                "Summary should be at least 20 characters",
                "Include what was built and how it works",
                "Mention any important decisions made"
            ]
        }
    
    # Add parameter validation status
    if action in ["update", "complete"]:
        param_status = self._check_parameter_status(response, action)
        response["parameter_status"] = param_status
    
    return response

def _check_parameter_status(
    self,
    response: Dict[str, Any],
    action: str
) -> Dict[str, Any]:
    """Check status of required parameters"""
    status = {
        "has_required": False,
        "missing": [],
        "provided": []
    }
    
    # Define requirements
    requirements = {
        "update": ["work_notes", "progress_made"],
        "complete": ["completion_summary"]
    }
    
    required = requirements.get(action, [])
    params = response.get("parameters", {})
    
    for param in required:
        if param in params and params[param]:
            status["provided"].append(param)
        else:
            status["missing"].append(param)
    
    status["has_required"] = len(status["missing"]) == 0
    
    return status
```

## 3. Test Implementation

### 3.1 Unit Test for Context Parameter Extractor
**File**: `tests/unit/test_context_parameter_extractor.py`

```python
"""Tests for ContextParameterExtractor"""

import pytest
from fastmcp.task_management.interface.utils.context_parameter_extractor import (
    ContextParameterExtractor
)


class TestContextParameterExtractor:
    """Test context parameter extraction"""
    
    def setup_method(self):
        """Set up test instance"""
        self.extractor = ContextParameterExtractor()
    
    def test_extracts_work_update_params(self):
        """Test extraction of work update parameters"""
        params = {
            "action": "update",
            "task_id": "test-123",
            "work_notes": "Implemented authentication",
            "progress_made": "Added JWT support",
            "files_modified": ["auth.py", "routes.py"],
            "other_param": "should be ignored"
        }
        
        result = self.extractor.extract_context_params(params)
        
        assert result == {
            "work_notes": "Implemented authentication",
            "progress_made": "Added JWT support", 
            "files_modified": ["auth.py", "routes.py"]
        }
        assert "other_param" not in result
        assert "action" not in result
    
    def test_ignores_empty_values(self):
        """Test that empty values are not extracted"""
        params = {
            "work_notes": "",  # Empty string
            "progress_made": "   ",  # Whitespace only
            "files_modified": [],  # Empty list
            "decisions_made": None,  # None value
            "blockers": "Has real value"
        }
        
        result = self.extractor.extract_context_params(params)
        
        assert result == {"blockers": "Has real value"}
    
    def test_validates_work_notes(self):
        """Test work notes validation"""
        # Too short
        valid, error = self.extractor.validate_work_notes("OK")
        assert not valid
        assert "too brief" in error
        
        # Placeholder text
        valid, error = self.extractor.validate_work_notes("TODO: write notes")
        assert not valid
        assert "placeholder" in error
        
        # Valid
        valid, error = self.extractor.validate_work_notes(
            "Implemented user authentication with JWT tokens"
        )
        assert valid
        assert error is None
    
    def test_validates_completion_summary(self):
        """Test completion summary validation"""
        # Too short
        valid, error = self.extractor.validate_completion_summary("Done")
        assert not valid
        assert "too short" in error
        
        # No completion words
        valid, error = self.extractor.validate_completion_summary(
            "Made some changes to the code"
        )
        assert not valid
        assert "what was accomplished" in error
        
        # Valid
        valid, error = self.extractor.validate_completion_summary(
            "Successfully implemented JWT authentication with refresh tokens"
        )
        assert valid
        assert error is None
    
    def test_suggests_missing_params(self):
        """Test parameter suggestions"""
        # Update without any context params
        suggestions = self.extractor.suggest_missing_params(
            "update",
            {"task_id", "status"}
        )
        assert "work_notes" in suggestions
        assert "progress_made" in suggestions
        
        # Complete without summary
        suggestions = self.extractor.suggest_missing_params(
            "complete",
            {"task_id"}
        )
        assert "completion_summary" in suggestions
        assert "testing_notes" in suggestions
```

### 3.2 Integration Test for Enforcement
**File**: `tests/integration/test_manual_context_enforcement.py`

```python
"""Integration tests for manual context enforcement"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastmcp.task_management.interface.controllers.task_mcp_controller import (
    TaskMCPController
)


class TestManualContextEnforcement:
    """Test manual context parameter enforcement"""
    
    @pytest.fixture
    async def controller(self):
        """Create test controller"""
        task_facade_factory = Mock()
        context_facade_factory = Mock()
        
        controller = TaskMCPController(
            task_facade_factory=task_facade_factory,
            context_facade_factory=context_facade_factory
        )
        
        # Mock the facade
        controller._facade = AsyncMock()
        
        return controller
    
    async def test_update_without_context_params_gets_warning(self, controller):
        """Test that updates without context get warnings"""
        # Mock facade response
        controller._facade.update_task = AsyncMock(return_value={
            "success": True,
            "task": {"id": "test-123"}
        })
        
        result = await controller.manage_task(
            action="update",
            task_id="test-123",
            status="in_progress"
        )
        
        # Should succeed but with warning
        assert result["success"] is True
        assert "parameter_warnings" in result
        assert any("context parameters" in w.lower() for w in result["parameter_warnings"])
    
    async def test_update_with_context_params_succeeds(self, controller):
        """Test that updates with context parameters succeed"""
        # Mock facade response
        controller._facade.update_task = AsyncMock(return_value={
            "success": True,
            "task": {"id": "test-123"}
        })
        
        result = await controller.manage_task(
            action="update",
            task_id="test-123",
            status="in_progress",
            work_notes="Implemented authentication flow",
            progress_made="Added login and logout endpoints",
            files_modified=["auth.py", "routes.py", "tests/test_auth.py"]
        )
        
        # Should succeed without warnings
        assert result["success"] is True
        assert "parameter_warnings" not in result
        assert result.get("context_updated") is True
        assert "work_notes" in result["context_params_processed"]
    
    async def test_complete_without_summary_fails(self, controller):
        """Test that completion without summary fails"""
        result = await controller.manage_task(
            action="complete",
            task_id="test-123"
        )
        
        # Should fail
        assert result["success"] is False
        assert "completion_summary" in result["error"].lower()
    
    async def test_complete_with_summary_succeeds(self, controller):
        """Test that completion with summary succeeds"""
        # Mock facade response
        controller._facade.complete_task = AsyncMock(return_value={
            "success": True,
            "task": {"id": "test-123", "status": "done"}
        })
        
        result = await controller.manage_task(
            action="complete",
            task_id="test-123",
            completion_summary="Successfully implemented JWT authentication with login, logout, and token refresh. All tests passing.",
            testing_notes="Added 15 unit tests and 5 integration tests"
        )
        
        # Should succeed
        assert result["success"] is True
        assert "context_updated" in result
    
    async def test_progressive_enforcement_escalation(self, controller):
        """Test that repeated violations lead to enforcement"""
        # Mock facade
        controller._facade.update_task = AsyncMock(return_value={
            "success": True,
            "task": {"id": "test-123"}
        })
        
        agent_id = "test-agent"
        
        # First few attempts should get warnings
        for i in range(3):
            result = await controller.manage_task(
                action="update",
                task_id="test-123",
                agent_id=agent_id,
                status="in_progress"
            )
            assert result["success"] is True
            assert "parameter_warnings" in result
        
        # Next attempt should be blocked
        result = await controller.manage_task(
            action="update",
            task_id="test-123",
            agent_id=agent_id,
            status="in_progress"
        )
        assert result["success"] is False
        assert "blocked" in result["error"].lower()
    
    async def test_response_enrichment_with_stale_context(self, controller):
        """Test response enrichment when context is stale"""
        # Mock facade response
        controller._facade.get_task = AsyncMock(return_value={
            "success": True,
            "task": {"id": "test-123"}
        })
        
        # Mock stale context state
        from datetime import datetime, timedelta
        stale_time = datetime.utcnow() - timedelta(hours=2)
        
        controller._get_context_state = AsyncMock(return_value=Mock(
            task_id="test-123",
            last_update=stale_time,
            is_stale=Mock(return_value=True),
            minutes_since_update=Mock(return_value=120)
        ))
        
        result = await controller.manage_task(
            action="get",
            task_id="test-123"
        )
        
        # Should include staleness reminder
        assert "context_reminder" in result
        assert "2 hours ago" in result["context_reminder"]
        assert "suggested_update" in result
```

## 4. Database Migration

### 4.1 Create Migration Script
**File**: `database/migrations/add_context_tracking_tables.sql`

```sql
-- Add context tracking tables for manual context system
-- Migration: add_context_tracking_tables
-- Date: 2025-02-03

-- Add columns to tasks table for context tracking
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_context_update TIMESTAMP;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS context_update_count INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS context_staleness_minutes INTEGER DEFAULT 0;

-- Create context sync journal for fail-safe persistence
CREATE TABLE IF NOT EXISTS context_sync_journal (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    context_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    sync_attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    synced_at TIMESTAMP,
    error_message TEXT,
    retry_after TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_sync_journal_status ON context_sync_journal(sync_status);
CREATE INDEX idx_sync_journal_task ON context_sync_journal(task_id);
CREATE INDEX idx_sync_journal_retry ON context_sync_journal(retry_after);

-- Create agent compliance tracking table
CREATE TABLE IF NOT EXISTS agent_compliance_stats (
    agent_id VARCHAR(100) PRIMARY KEY,
    total_operations INTEGER DEFAULT 0,
    operations_with_context INTEGER DEFAULT 0,
    compliance_rate DECIMAL(5,4) DEFAULT 0.0,
    warning_count INTEGER DEFAULT 0,
    enforcement_level VARCHAR(20) DEFAULT 'soft',
    consecutive_failures INTEGER DEFAULT 0,
    last_warning_at TIMESTAMP,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_operation_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    promoted_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_compliance_agent ON agent_compliance_stats(agent_id);
CREATE INDEX idx_compliance_level ON agent_compliance_stats(enforcement_level);

-- Create context parameter tracking table
CREATE TABLE IF NOT EXISTS context_parameter_usage (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36),
    agent_id VARCHAR(100),
    action VARCHAR(50),
    parameters_provided JSONB,
    parameter_count INTEGER,
    has_required_params BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_param_usage_task ON context_parameter_usage(task_id);
CREATE INDEX idx_param_usage_agent ON context_parameter_usage(agent_id);
CREATE INDEX idx_param_usage_time ON context_parameter_usage(created_at);

-- Add update trigger for task context tracking
CREATE OR REPLACE FUNCTION update_task_context_tracking()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.updated_at > OLD.updated_at THEN
        NEW.context_staleness_minutes = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - COALESCE(NEW.last_context_update, NEW.created_at))) / 60;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_context_tracking_trigger
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION update_task_context_tracking();
```

## 5. Configuration

### 5.1 Enforcement Configuration
**File**: `config/context_enforcement.yaml`

```yaml
# Manual Context System Enforcement Configuration
version: "1.0"

enforcement:
  # Global enforcement settings
  enabled: true
  default_level: warning  # disabled, soft, warning, strict
  
  # Progressive enforcement settings
  progressive:
    enabled: true
    thresholds:
      learning: 5      # New agents get 5 warnings
      improving: 3     # Improving agents get 3 warnings
      compliant: 2     # Compliant agents get 2 warnings
      expert: 1        # Expert agents get 1 warning
    
    # Compliance level thresholds
    levels:
      learning:
        operations_required: 5
        compliance_rate: 0.6
      improving:
        operations_required: 10
        compliance_rate: 0.8
      compliant:
        operations_required: 20
        compliance_rate: 0.95
  
  # Parameter requirements by action
  parameters:
    update:
      required:
        - work_notes
        - progress_made
      optional:
        - files_modified
        - files_created
        - files_deleted
        - decisions_made
        - blockers
      validation:
        work_notes:
          min_length: 10
          min_words: 3
        progress_made:
          min_length: 10
          min_words: 3
    
    complete:
      required:
        - completion_summary
      optional:
        - testing_notes
        - files_created
        - patterns_identified
        - deployment_notes
      validation:
        completion_summary:
          min_length: 20
          min_words: 5
          must_contain: ["completed", "implemented", "fixed", "added", "updated"]
    
    create:
      required: []  # No context params required
      optional:
        - initial_thoughts
        - estimated_effort
        - technical_approach
  
  # Response enrichment settings
  enrichment:
    enabled: true
    staleness_threshold_minutes: 30
    include_templates: true
    include_progress_bar: true
    include_compliance_report: false  # Set true for debugging
  
  # Sync and journal settings
  sync:
    retry_attempts: 3
    retry_delay_seconds: 5
    retry_backoff_multiplier: 2
    max_retry_delay_seconds: 300
    journal_path: "./data/context_journal"
    journal_retention_days: 30
  
  # Feature flags for gradual rollout
  rollout:
    percentage: 100  # Percentage of agents to enforce
    excluded_agents:  # Agents to exclude from enforcement
      - "test_agent"
      - "migration_agent"
    pilot_agents:  # Agents to enforce strictly (for testing)
      - "pilot_agent_1"
      - "pilot_agent_2"
```

## 6. Deployment Instructions

### 6.1 Deployment Steps

1. **Database Migration**
   ```bash
   # Run migration script
   psql -U $DB_USER -d $DB_NAME -f database/migrations/add_context_tracking_tables.sql
   ```

2. **Deploy New Files**
   - Copy all new service files to appropriate directories
   - Ensure proper Python package structure

3. **Update Configuration**
   ```bash
   # Copy configuration
   cp config/context_enforcement.yaml /app/config/
   
   # Set environment variable
   export CONTEXT_ENFORCEMENT_CONFIG=/app/config/context_enforcement.yaml
   ```

4. **Gradual Rollout**
   - Start with `enforcement.default_level: soft` (logging only)
   - Monitor logs for parameter usage
   - Switch to `warning` after 1 week
   - Switch to `strict` after positive feedback

5. **Monitoring**
   ```sql
   -- Monitor compliance rates
   SELECT 
       agent_id,
       compliance_rate,
       total_operations,
       enforcement_level
   FROM agent_compliance_stats
   ORDER BY compliance_rate ASC;
   
   -- Check sync journal health
   SELECT 
       sync_status,
       COUNT(*) as count,
       AVG(sync_attempts) as avg_attempts
   FROM context_sync_journal
   GROUP BY sync_status;
   ```

## 7. Rollback Plan

If issues arise:

1. **Disable Enforcement**
   ```yaml
   # In config/context_enforcement.yaml
   enforcement:
     enabled: false
   ```

2. **Clear Progressive Tracking**
   ```sql
   -- Reset agent compliance
   UPDATE agent_compliance_stats 
   SET consecutive_failures = 0,
       warning_count = 0;
   ```

3. **Revert Code**
   - Remove enforcement calls from controllers
   - Keep parameter extraction for logging

## Conclusion

This implementation guide provides a complete path from the current system to a fully functional manual context system. The implementation is designed to be:

1. **Non-breaking**: All changes are backward compatible
2. **Gradual**: Progressive enforcement allows smooth adoption
3. **Helpful**: Rich error messages and templates guide usage
4. **Resilient**: Local journal ensures no data loss
5. **Monitorable**: Comprehensive metrics for tracking adoption

The system transforms context management from an aspiration to an enforceable reality through parameter-driven updates.

---
*Implementation Guide v1.0 - February 2025*