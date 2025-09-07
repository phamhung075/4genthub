"""Enhanced Workflow Hint System - AI Agent guidance with multi-project awareness and autonomous operation"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class WorkflowHintEnhancer:
    """Enhanced workflow guidance system for autonomous AI agents with multi-project coordination"""
    
    def __init__(self):
        """Initialize the enhanced workflow hint system"""
        self._logger = logger
        self.workflow_rules = self._load_workflow_rules()
        self.autonomous_rules = self._load_autonomous_operation_rules()
        
    def enhance_task_response(self, 
                             response: Dict[str, Any], 
                             action: str,
                             request_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced response processing with validation, conflict detection, and autonomous guidance"""
        
        if not isinstance(response, dict):
            return response
            
        request_params = request_params or {}
        
        # Handle error responses with enhanced analysis
        if not response.get("success"):
            return self._enhance_error_response(response, action, request_params)
        
        # Extract task context with multi-project awareness
        task_context = self._extract_task_context(response, request_params)
        if not task_context:
            return self._add_basic_workflow_hints(response, action)
        
        # Generate comprehensive workflow guidance
        response["workflow_guidance"] = self._generate_autonomous_guidance(task_context, action, request_params)
        
        # Add autonomous coordination hints
        response["autonomous_coordination"] = self._analyze_autonomous_context(task_context, action)
        
        # Add decision schema for AI agents
        response["autonomous_schema"] = self._generate_decision_schema(task_context, action)
        
        return response
    
    def enhance_response(self, response: Dict[str, Any], operation_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced response with workflow hints and guidance (backward compatibility)"""
        if not isinstance(response, dict):
            return response
            
        enhanced_response = response.copy()
        
        # Add workflow hints section if not present
        if 'workflow_hints' not in enhanced_response:
            enhanced_response['workflow_hints'] = {}
            
        # Add operation context if provided
        if operation_context:
            enhanced_response['workflow_hints']['operation_context'] = operation_context
            
        # Add timestamp for enhancement
        enhanced_response['workflow_hints']['enhanced_at'] = datetime.now(timezone.utc).isoformat()
        
        return enhanced_response
    
    def add_task_hints(self, response: Dict[str, Any], task_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add task-specific workflow hints to response (enhanced version)"""
        enhanced = self.enhance_response(response)
        
        if 'workflow_hints' not in enhanced:
            enhanced['workflow_hints'] = {}
            
        if task_data:
            # Analyze task state for better guidance
            state = self._analyze_task_state(task_data)
            enhanced['workflow_hints']['task_guidance'] = self._generate_task_guidance(state, task_data)
            enhanced['workflow_hints']['next_actions'] = self._suggest_next_actions(state, task_data)
            enhanced['workflow_hints']['autonomous_rules'] = self._get_autonomous_rules_for_task(state)
        else:
            enhanced['workflow_hints']['task_guidance'] = {
                'next_steps': ['Review task requirements', 'Update task progress', 'Add context information'],
                'best_practices': ['Keep task descriptions clear', 'Update status regularly', 'Link related tasks']
            }
                
        return enhanced
    
    def add_context_hints(self, response: Dict[str, Any], context_level: Optional[str] = None) -> Dict[str, Any]:
        """Add context-specific workflow hints to response"""
        enhanced = self.enhance_response(response)
        
        if 'workflow_hints' not in enhanced:
            enhanced['workflow_hints'] = {}
            
        context_guidance = {
            'context_management': [
                'Use appropriate context level for sharing information',
                'Update context after significant discoveries',
                'Consider delegating reusable patterns to higher levels'
            ],
            'autonomous_context_rules': [
                '🤖 AI agents must update context every 30 minutes during active work',
                '🔄 Context preservation is critical for multi-session collaboration',
                '📊 Progress tracking enables better agent coordination'
            ]
        }
        
        if context_level:
            level_specific = {
                'global': ['Share user preferences and global settings', 'Set team-wide standards and conventions'],
                'project': ['Document project-wide decisions and standards', 'Define technical architecture choices'],
                'branch': ['Track branch-specific work and decisions', 'Coordinate feature development'],
                'task': ['Capture task-specific details and progress', 'Document implementation decisions']
            }
            
            if context_level in level_specific:
                context_guidance['level_specific'] = level_specific[context_level]
                
        enhanced['workflow_hints']['context_guidance'] = context_guidance
        return enhanced
    
    def add_collaboration_hints(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add collaboration workflow hints to response"""
        enhanced = self.enhance_response(response)
        
        if 'workflow_hints' not in enhanced:
            enhanced['workflow_hints'] = {}
            
        enhanced['workflow_hints']['collaboration'] = {
            'multi_session': [
                'Update context to share information between sessions',
                'Use appropriate context levels for information sharing',
                'Document decisions and discoveries for future reference'
            ],
            'agent_coordination': [
                'Switch to appropriate specialist agents for specific work',
                'Update task progress to coordinate with other agents',
                'Share reusable patterns through context delegation'
            ],
            'autonomous_collaboration': [
                '🤖 AI agents must validate decisions against multi-project context',
                '🔄 Tasks >70% complete take priority unless critical emergency',
                '🔗 Blocking tasks must be prioritized over non-blocking work'
            ]
        }
        
        return enhanced
    
    def _generate_autonomous_guidance(self, task_context: Dict[str, Any], action: str, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate autonomous workflow guidance with multi-project awareness"""
        
        state = self._analyze_enhanced_state(task_context)
        
        guidance = {
            "current_state": state,
            "autonomous_rules": self._get_autonomous_rules(state, action),
            "decision_matrix": self._generate_decision_matrix(state, task_context),
            "next_actions": self._suggest_autonomous_actions(state, task_context),
            "priority_guidance": self._generate_priority_guidance(state, task_context),
            "hints": self._generate_autonomous_hints(state, task_context, action),
            "warnings": self._check_autonomous_warnings(state, task_context),
            "examples": self._get_autonomous_examples(state, action, task_context),
            "progress_indicator": self._get_progress_indicator(state)
        }
        
        return guidance
    
    def _extract_task_context(self, response: Dict[str, Any], request_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract comprehensive task context with multi-project awareness"""
        
        # Extract task from various response formats
        task = None
        if "task" in response:
            task = response["task"]
        elif "tasks" in response and response["tasks"]:
            task = response["tasks"][0]
        elif "data" in response and response["data"]:
            if isinstance(response["data"], dict) and "task" in response["data"]:
                task = response["data"]["task"]
            elif isinstance(response["data"], list) and response["data"]:
                task = response["data"][0] if isinstance(response["data"][0], dict) else None
        
        if not task or not isinstance(task, dict):
            return None
        
        # Enhance with request context
        context = {
            "task": task,
            "project_id": request_params.get("project_id") or task.get("project_id"),
            "git_branch_id": request_params.get("git_branch_id") or task.get("git_branch_id"),
            "user_context": request_params.get("user_id", "autonomous_ai"),
            "action_context": request_params,
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }
        
        return context
    
    def _analyze_enhanced_state(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced state analysis with autonomous operation focus"""
        
        task = task_context["task"]
        
        # Basic state analysis
        base_state = self._analyze_task_state(task)
        
        # Enhanced autonomous state analysis
        enhanced_state = {
            **base_state,
            "autonomous_ready": self._check_autonomous_readiness(task, task_context),
            "decision_confidence": self._calculate_decision_confidence(task, task_context),
            "priority_score": self._calculate_priority_score(task, task_context),
            "blocking_others": self._check_if_blocking_others(task, task_context),
            "completion_risk": self._assess_completion_risk(task, task_context)
        }
        
        return enhanced_state
    
    def _analyze_task_state(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current task state"""
        
        status = task.get("status", "todo")
        progress = task.get("completion_percentage", 0) or task.get("progress_percentage", 0)
        has_context = task.get("context_id") is not None
        subtasks = task.get("subtasks", [])
        
        # Determine workflow phase
        if status in ["todo", "pending"]:
            phase = "not_started"
        elif status == "in_progress":
            if progress < 25:
                phase = "analysis"
            elif progress < 75:
                phase = "implementation"
            else:
                phase = "finalizing"
        elif status in ["review", "testing"]:
            phase = "review"
        elif status in ["done", "completed"]:
            phase = "completed"
        else:
            phase = "unknown"
        
        # Check subtask completion
        subtasks_complete = 0
        if subtasks:
            for s in subtasks:
                if isinstance(s, dict) and s.get("status") in ["done", "completed"]:
                    subtasks_complete += 1
        
        return {
            "phase": phase,
            "status": status,
            "progress": progress,
            "has_context": has_context,
            "has_subtasks": len(subtasks) > 0,
            "subtasks_total": len(subtasks),
            "subtasks_complete": subtasks_complete,
            "can_complete": has_context and (not subtasks or subtasks_complete == len(subtasks)),
            "time_since_update": self._get_time_since_update(task)
        }
    
    def _get_autonomous_rules(self, state: Dict[str, Any], action: str) -> List[Dict[str, Any]]:
        """Get autonomous operation rules with conflict prevention"""
        
        rules = []
        
        # Core autonomous operation rules
        rules.append({
            "rule_id": "AUTO_001",
            "type": "autonomous_operation",
            "priority": "critical",
            "rule": "🤖 AUTONOMOUS: AI must validate all decisions against project context",
            "enforcement": "mandatory"
        })
        
        rules.append({
            "rule_id": "AUTO_002", 
            "type": "context_preservation",
            "priority": "high",
            "rule": "🔄 CONTEXT: Tasks >70% complete take priority unless critical emergency",
            "enforcement": "mandatory"
        })
        
        rules.append({
            "rule_id": "AUTO_003",
            "type": "dependency_resolution", 
            "priority": "high",
            "rule": "🔗 DEPENDENCIES: Blocking tasks must be prioritized over non-blocking",
            "enforcement": "mandatory"
        })
        
        # Phase-specific autonomous rules
        if state["phase"] == "not_started":
            rules.append({
                "rule_id": "AUTO_004",
                "type": "initiation",
                "priority": "medium",
                "rule": "🚀 START: Autonomous agents must begin work immediately after assignment",
                "enforcement": "recommended"
            })
        
        elif state["phase"] in ["analysis", "implementation"]:
            rules.append({
                "rule_id": "AUTO_005", 
                "type": "progress_tracking",
                "priority": "medium",
                "rule": "📊 PROGRESS: Update progress every 25% completion or 30 minutes",
                "enforcement": "recommended"
            })
        
        elif state["phase"] == "finalizing":
            rules.append({
                "rule_id": "AUTO_006",
                "type": "completion",
                "priority": "high", 
                "rule": "✅ COMPLETION: All subtasks and context must be complete before finishing",
                "enforcement": "mandatory"
            })
        
        return rules
    
    def _generate_decision_matrix(self, state: Dict[str, Any], task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate autonomous decision matrix for AI agents"""
        
        task = task_context["task"]
        
        matrix = {
            "decision_framework": "autonomous_multi_project",
            "priority_factors": {
                "completion_preservation": 100 if state["progress"] > 70 else 0,
                "dependency_impact": self._calculate_dependency_impact(task, task_context),
                "urgency_score": self._calculate_urgency_score(task),
                "progress_momentum": state["progress"] if state["status"] == "in_progress" else 0
            },
            "decision_thresholds": {
                "switch_task_threshold": 150,
                "emergency_override": 200,
                "completion_protection": 70
            },
            "autonomous_actions": self._generate_autonomous_action_recommendations(state, task_context)
        }
        
        return matrix
    
    def _suggest_autonomous_actions(self, state: Dict[str, Any], task_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest specific autonomous actions with executable parameters"""
        
        actions = []
        task = task_context["task"]
        task_id = task.get("id", "UNKNOWN")
        
        # Immediate action based on state
        if state.get("autonomous_ready") and state["phase"] == "not_started":
            actions.append({
                "action_id": "AUTO_START",
                "priority": "immediate",
                "action": "Begin autonomous work",
                "tool": "manage_task",
                "params": {
                    "action": "update",
                    "task_id": task_id,
                    "status": "in_progress", 
                    "details": "Autonomous AI agent beginning work"
                },
                "reason": "Task is ready for autonomous execution",
                "confidence": state.get("decision_confidence", 90)
            })
        
        elif state["phase"] in ["analysis", "implementation"] and state.get("time_since_update", 0) > 1800:
            actions.append({
                "action_id": "AUTO_PROGRESS",
                "priority": "high",
                "action": "Report autonomous progress",
                "tool": "manage_context",
                "params": {
                    "action": "update",
                    "level": "task",
                    "context_id": task_id,
                    "data": {
                        "autonomous_progress": f"Progress update - {state['progress']}% complete",
                        "agent": "autonomous_ai",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                },
                "reason": "Progress update required for autonomous operation",
                "confidence": 95
            })
        
        elif state["can_complete"] and state["phase"] == "finalizing":
            actions.append({
                "action_id": "AUTO_COMPLETE",
                "priority": "high",
                "action": "Complete task autonomously",
                "tool": "manage_task",
                "params": {
                    "action": "complete",
                    "task_id": task_id,
                    "completion_summary": "Task completed by autonomous AI agent",
                    "testing_notes": "Autonomous validation completed"
                },
                "reason": "Task meets all completion criteria",
                "confidence": state.get("decision_confidence", 95)
            })
        
        return actions
    
    def _suggest_next_actions(self, state: Dict[str, Any], task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest next actions based on current state"""
        
        actions = []
        task_id = task.get("id", "TASK_ID")
        
        if state["phase"] == "not_started":
            actions.append({
                "priority": "high",
                "action": "Start the task",
                "tool": "manage_task",
                "params": {
                    "action": "update",
                    "task_id": task_id,
                    "status": "in_progress",
                    "details": "Starting analysis and planning"
                },
                "reason": "Task needs to be marked as in progress"
            })
        
        elif state["phase"] in ["analysis", "implementation"]:
            # Suggest progress update if stale
            if state["time_since_update"] > 1800:  # 30 minutes
                actions.append({
                    "priority": "high",
                    "action": "Update progress",
                    "tool": "report_progress",
                    "params": {
                        "task_id": task_id,
                        "progress_type": "implementation",
                        "description": "Describe what you've accomplished",
                        "percentage_complete": min(state["progress"] + 10, 100)
                    },
                    "reason": "No updates in 30+ minutes"
                })
        
        elif state["phase"] == "finalizing":
            if state["can_complete"]:
                actions.append({
                    "priority": "high",
                    "action": "Complete the task",
                    "tool": "complete_task_with_update",
                    "params": {
                        "task_id": task_id,
                        "completion_summary": "Describe what was accomplished",
                        "testing_notes": "How it was tested (if applicable)"
                    },
                    "reason": "Task is ready for completion"
                })
            else:
                if not state["has_context"]:
                    actions.append({
                        "priority": "critical",
                        "action": "Update context first",
                        "tool": "quick_task_update",
                        "params": {
                            "task_id": task_id,
                            "what_i_did": "Summary of work completed",
                            "progress_percentage": 100
                        },
                        "reason": "Context update required before completion"
                    })
        
        return actions
    
    def _generate_autonomous_hints(self, state: Dict[str, Any], task_context: Dict[str, Any], action: str) -> List[str]:
        """Generate autonomous operation hints"""
        
        hints = []
        task = task_context["task"]
        
        # Phase-based autonomous hints
        phase_hints = {
            "not_started": "🤖 AUTONOMOUS: Begin by understanding requirements and updating status to 'in_progress'",
            "analysis": "🔍 AUTONOMOUS: Focus on problem analysis before implementation, update progress regularly",
            "implementation": "🛠️ AUTONOMOUS: Build incrementally, test as you go, report progress every 25%",
            "finalizing": "✨ AUTONOMOUS: Review work completeness, ensure context is updated before completion",
            "review": "👀 AUTONOMOUS: Address feedback systematically, document changes made"
        }
        
        if state["phase"] in phase_hints:
            hints.append(phase_hints[state["phase"]])
        
        # Autonomous operation specific hints
        if state.get("autonomous_ready"):
            hints.append("🚀 READY: All prerequisites met - autonomous execution can begin immediately")
        
        if state["progress"] > 70:
            hints.append("🔄 MOMENTUM: High progress task - maintain focus unless critical priority emerges")
        
        # Time-based hints
        if state["time_since_update"] > 1800:
            hours = state["time_since_update"] // 3600
            minutes = (state["time_since_update"] % 3600) // 60
            if hours > 0:
                hints.append(f"⏰ STALE: Last update {hours}h {minutes}m ago - autonomous agents should update progress")
            else:
                hints.append(f"⏰ UPDATE: Last update {minutes} minutes ago - consider progress report")
        
        # Completion hints
        if state["can_complete"]:
            hints.append("✅ READY TO COMPLETE: All requirements satisfied - autonomous completion recommended")
        elif state["phase"] == "finalizing":
            if not state["has_context"]:
                hints.append("❌ BLOCKED: Context update required before autonomous completion")
        
        return hints
    
    def _check_autonomous_warnings(self, state: Dict[str, Any], task_context: Dict[str, Any]) -> List[str]:
        """Check for autonomous operation warnings"""
        
        warnings = []
        
        # Completion blockers
        if state["phase"] == "finalizing" or state["progress"] > 90:
            if not state["has_context"]:
                warnings.append("⚠️ AUTONOMOUS BLOCKER: Context not updated - required for completion")
            
            if state["has_subtasks"] and state["subtasks_complete"] < state["subtasks_total"]:
                remaining = state["subtasks_total"] - state["subtasks_complete"]
                warnings.append(f"⚠️ AUTONOMOUS BLOCKER: {remaining} subtasks incomplete - must finish first")
        
        # Stale task warnings
        if state["time_since_update"] > 3600:  # 1 hour
            warnings.append("⏰ AUTONOMOUS WARNING: Task stale for >1 hour - requires immediate attention")
        
        # Progress inconsistency warnings
        if state["status"] == "in_progress" and state["progress"] == 0:
            warnings.append("📊 AUTONOMOUS WARNING: Status 'in_progress' but 0% completion - update progress")
        
        # High-risk completion warnings
        completion_risk = state.get("completion_risk", 0)
        if completion_risk > 70:
            warnings.append(f"🚨 AUTONOMOUS RISK: {completion_risk}% completion risk - review requirements carefully")
        
        return warnings
    
    def _get_autonomous_examples(self, state: Dict[str, Any], action: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get autonomous operation examples"""
        
        task = task_context["task"]
        task_id = task.get("id", "TASK_ID")
        examples = {}
        
        if state["phase"] == "not_started":
            examples["autonomous_start"] = {
                "description": "Autonomous agent begins task",
                "command": f"manage_task(action='update', task_id='{task_id}', status='in_progress', details='🤖 Autonomous AI agent starting task execution')"
            }
        
        if state["phase"] in ["analysis", "implementation"]:
            examples["autonomous_progress"] = {
                "description": "Autonomous progress update",
                "command": f"report_progress(task_id='{task_id}', progress_type='autonomous_implementation', description='🤖 Completed analysis phase', percentage_complete={min(state['progress'] + 25, 100)})"
            }
        
        if state["can_complete"]:
            examples["autonomous_complete"] = {
                "description": "Autonomous task completion",
                "command": f"complete_task_with_update(task_id='{task_id}', completion_summary='🤖 Task completed by autonomous AI agent', testing_notes='Autonomous validation performed')"
            }
        
        return examples
    
    def _get_progress_indicator(self, state: Dict[str, Any]) -> str:
        """Generate visual progress indicator"""
        
        progress = state["progress"]
        filled = int(progress / 10)
        empty = 10 - filled
        
        bar = "█" * filled + "░" * empty
        phase_emoji = {
            "not_started": "⏳",
            "analysis": "🔍", 
            "implementation": "🛠️",
            "finalizing": "✨",
            "review": "👀",
            "completed": "✅"
        }
        
        emoji = phase_emoji.get(state["phase"], "🔄")
        return f"{emoji} [{bar}] {progress}% - {state['phase'].replace('_', ' ').title()}"
    
    # Helper methods for autonomous operation
    
    def _check_autonomous_readiness(self, task: Dict[str, Any], task_context: Dict[str, Any]) -> bool:
        """Check if task is ready for autonomous execution"""
        
        # Basic readiness checks
        has_description = bool(task.get("description") or task.get("title"))
        has_clear_requirements = len(task.get("description", "")) > 10
        not_blocked = task.get("status") != "blocked"
        
        return has_description and has_clear_requirements and not_blocked
    
    def _calculate_decision_confidence(self, task: Dict[str, Any], task_context: Dict[str, Any]) -> int:
        """Calculate autonomous decision confidence score (0-100)"""
        
        confidence = 50  # Base confidence
        
        # Boost confidence for clear tasks
        if task.get("description") and len(task["description"]) > 50:
            confidence += 20
        
        # Boost for tasks with context
        if task.get("context_id"):
            confidence += 15
        
        # Boost for tasks in progress
        if task.get("status") == "in_progress":
            confidence += 10
        
        # Reduce for very new tasks
        created_at = task.get("created_at")
        if created_at and self._is_recently_created(created_at):
            confidence -= 10
        
        return max(0, min(100, confidence))
    
    def _calculate_priority_score(self, task: Dict[str, Any], task_context: Dict[str, Any]) -> int:
        """Calculate task priority score for autonomous decision making"""
        
        score = 50  # Base score
        
        # Priority from task
        priority = task.get("priority", "medium")
        priority_scores = {"low": 10, "medium": 50, "high": 80, "urgent": 100}
        score = priority_scores.get(priority, 50)
        
        # Adjust for progress (higher progress = higher priority to complete)
        progress = task.get("completion_percentage", 0) or task.get("progress_percentage", 0)
        if progress > 70:
            score += 30
        elif progress > 50:
            score += 15
        
        return min(100, score)
    
    def _check_if_blocking_others(self, task: Dict[str, Any], task_context: Dict[str, Any]) -> List[str]:
        """Check if task is blocking other tasks (simplified implementation)"""
        
        # Simplified implementation - would need repository access for full analysis
        blocking_indicators = []
        
        if task.get("is_dependency", False):
            blocking_indicators.append("marked_as_dependency")
        
        if "blocker" in task.get("tags", []):
            blocking_indicators.append("tagged_as_blocker")
        
        return blocking_indicators
    
    def _assess_completion_risk(self, task: Dict[str, Any], task_context: Dict[str, Any]) -> int:
        """Assess risk of not completing task successfully (0-100)"""
        
        risk = 0
        
        # High risk for old tasks without progress
        age_days = self._get_task_age_days(task)
        if age_days > 7 and task.get("completion_percentage", 0) < 25:
            risk += 30
        
        # High risk for tasks without clear description
        if not task.get("description") or len(task["description"]) < 20:
            risk += 25
        
        # High risk for tasks with many incomplete subtasks
        subtasks = task.get("subtasks", [])
        if len(subtasks) > 5:
            risk += 20
        
        return min(100, risk)
    
    def _get_time_since_update(self, task: Dict[str, Any]) -> int:
        """Get seconds since last update"""
        
        last_update = task.get("updated_at")
        if not last_update:
            return 0
        
        try:
            if isinstance(last_update, str):
                # Handle various date formats
                if last_update.endswith('Z'):
                    last_update = last_update[:-1] + '+00:00'
                last_update_dt = datetime.fromisoformat(last_update)
            elif hasattr(last_update, 'timestamp'):
                last_update_dt = last_update
            else:
                return 0
            
            # Ensure timezone awareness
            if last_update_dt.tzinfo is None:
                last_update_dt = last_update_dt.replace(tzinfo=timezone.utc)
            
            time_diff = datetime.now(timezone.utc) - last_update_dt
            return int(time_diff.total_seconds())
        except (ValueError, AttributeError, TypeError):
            return 0
    
    def _is_recently_created(self, created_at: str) -> bool:
        """Check if task was created recently (within 1 hour)"""
        try:
            if isinstance(created_at, str):
                if created_at.endswith('Z'):
                    created_at = created_at[:-1] + '+00:00'
                created_dt = datetime.fromisoformat(created_at)
            else:
                return False
            
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            
            age = datetime.now(timezone.utc) - created_dt
            return age.total_seconds() < 3600  # 1 hour
        except:
            return False
    
    def _get_task_age_days(self, task: Dict[str, Any]) -> int:
        """Get task age in days"""
        created_at = task.get("created_at")
        if not created_at:
            return 0
        
        try:
            if isinstance(created_at, str):
                if created_at.endswith('Z'):
                    created_at = created_at[:-1] + '+00:00'
                created_dt = datetime.fromisoformat(created_at)
            else:
                return 0
            
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            
            age = datetime.now(timezone.utc) - created_dt
            return int(age.days)
        except:
            return 0
    
    # Configuration and rules loading
    
    def _load_workflow_rules(self) -> Dict[str, Any]:
        """Load workflow rules configuration"""
        
        return {
            "update_interval": 1800,  # 30 minutes
            "require_context_for_completion": True,
            "require_subtask_completion": True,
            "autonomous_operation": True,
            "phases": {
                "not_started": {
                    "allowed_actions": ["update", "create_subtask"],
                    "required_fields": ["status"]
                },
                "implementation": {
                    "allowed_actions": ["update", "report_progress", "create_subtask"],
                    "reminder_interval": 1800
                },
                "finalizing": {
                    "allowed_actions": ["update", "complete"],
                    "required_fields": ["completion_summary"]
                }
            }
        }
    
    def _load_autonomous_operation_rules(self) -> Dict[str, Any]:
        """Load autonomous operation rules"""
        
        return {
            "auto_start_threshold": 90,
            "progress_update_interval": 1800,
            "completion_confidence_threshold": 80,
            "context_switching_cost": 50,
            "priority_boost_for_progress": 30
        }
    
    # Support methods (simplified implementations)
    
    def _add_basic_workflow_hints(self, response: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Add basic workflow hints when task context is not available"""
        
        response["workflow_guidance"] = {
            "message": "Basic workflow guidance (task context not available)",
            "general_rules": [
                "🤖 Update task status to 'in_progress' when starting work",
                "📊 Report progress regularly (every 30 minutes during active work)",
                "📝 Update context before completing tasks",
                "✅ Ensure all subtasks are complete before parent task completion"
            ],
            "action_specific": self._get_action_specific_guidance(action)
        }
        
        return response
    
    def _get_action_specific_guidance(self, action: str) -> List[str]:
        """Get guidance specific to the action being performed"""
        
        guidance = {
            "create": ["🆕 Provide clear title and description", "🎯 Set appropriate priority level"],
            "update": ["📝 Include meaningful progress notes", "📊 Update completion percentage"],
            "complete": ["✅ Provide completion summary", "📋 Ensure all subtasks are done"],
            "next": ["🚀 Ready to start? Update status to 'in_progress'"]
        }
        
        return guidance.get(action, ["📌 Follow standard task management workflow"])
    
    def _generate_task_guidance(self, state: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive task guidance"""
        
        guidance = {
            'phase': state['phase'],
            'next_steps': self._get_phase_next_steps(state['phase']),
            'best_practices': self._get_phase_best_practices(state['phase']),
            'progress_indicator': self._get_progress_indicator(state)
        }
        
        if task_data.get('status') == 'pending':
            guidance['suggestions'] = [
                'Consider starting this task to move progress forward',
                'Ensure all dependencies are resolved before starting',
                '🤖 Autonomous agents should begin immediately if ready'
            ]
        elif task_data.get('status') == 'in_progress':
            guidance['suggestions'] = [
                'Update progress regularly to maintain visibility',
                'Consider breaking down large tasks into subtasks',
                '🤖 Report autonomous progress every 30 minutes'
            ]
        
        return guidance
    
    def _get_phase_next_steps(self, phase: str) -> List[str]:
        """Get next steps for the current phase"""
        
        steps = {
            "not_started": ["Update status to 'in_progress'", "Analyze requirements", "Create subtasks if needed"],
            "analysis": ["Complete requirement analysis", "Begin implementation planning", "Update progress to 25%"],
            "implementation": ["Execute planned work", "Test incremental changes", "Update progress regularly"],
            "finalizing": ["Complete final testing", "Update task context", "Prepare completion summary"],
            "review": ["Address review feedback", "Make necessary adjustments", "Update status when ready"],
            "completed": ["Task is complete", "Consider follow-up improvements", "Share learnings"]
        }
        
        return steps.get(phase, ["Continue with current work"])
    
    def _get_phase_best_practices(self, phase: str) -> List[str]:
        """Get best practices for the current phase"""
        
        practices = {
            "not_started": ["Understand requirements fully", "Set clear goals", "Plan approach"],
            "analysis": ["Focus on understanding before building", "Ask questions early", "Document findings"],
            "implementation": ["Build incrementally", "Test frequently", "Keep code clean"],
            "finalizing": ["Review completeness", "Validate requirements", "Document decisions"],
            "review": ["Be responsive to feedback", "Explain changes clearly", "Test thoroughly"],
            "completed": ["Document lessons learned", "Update related documentation", "Plan next steps"]
        }
        
        return practices.get(phase, ["Follow standard practices"])
    
    def _get_autonomous_rules_for_task(self, state: Dict[str, Any]) -> List[str]:
        """Get autonomous operation rules specific to task state"""
        
        rules = [
            "🤖 AUTONOMOUS: Validate decisions against project context",
            "🔄 MOMENTUM: Preserve progress >70% unless critical emergency"
        ]
        
        if state["phase"] == "not_started":
            rules.append("🚀 AUTONOMOUS: Begin work immediately when ready")
        elif state["phase"] in ["analysis", "implementation"]:
            rules.append("📊 AUTONOMOUS: Update progress every 25% or 30 minutes")
        elif state["phase"] == "finalizing":
            rules.append("✅ AUTONOMOUS: Complete when all criteria met")
        
        return rules
    
    def _analyze_autonomous_context(self, task_context: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Analyze context for autonomous operation coordination"""
        
        return {
            "coordination_type": "autonomous_multi_project",
            "project_context": {
                "project_id": task_context.get("project_id"),
                "branch_id": task_context.get("git_branch_id"),
                "multi_project_impact": "low"  # Simplified - would analyze actual dependencies
            },
            "agent_coordination": {
                "current_agent": "autonomous_ai",
                "recommended_agent": self._recommend_agent_for_task(task_context["task"]),
                "coordination_needed": False
            },
            "context_preservation": {
                "should_preserve": task_context["task"].get("completion_percentage", 0) > 70,
                "switching_cost": "medium",
                "completion_benefit": "high" if task_context["task"].get("completion_percentage", 0) > 90 else "medium"
            }
        }
    
    def _recommend_agent_for_task(self, task: Dict[str, Any]) -> str:
        """Recommend appropriate agent type for task"""
        
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        
        if any(word in title + description for word in ["test", "testing", "spec", "validation"]):
            return "test_orchestrator_agent"
        elif any(word in title + description for word in ["ui", "interface", "design", "component"]):
            return "ui_designer_agent"
        elif any(word in title + description for word in ["code", "implement", "develop", "build"]):
            return "coding_agent"
        elif any(word in title + description for word in ["bug", "fix", "debug", "error"]):
            return "debugger_agent"
        elif any(word in title + description for word in ["doc", "document", "guide", "readme"]):
            return "documentation_agent"
        else:
            return "uber_orchestrator_agent"
    
    def _generate_decision_schema(self, task_context: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Generate decision schema for autonomous agents"""
        
        return {
            "schema_version": "1.0",
            "decision_type": "autonomous_task_management",
            "required_validations": [
                "context_completeness",
                "progress_preservation", 
                "dependency_impact",
                "resource_availability"
            ],
            "decision_points": {
                "should_start": {
                    "conditions": ["task_ready", "no_higher_priority", "resources_available"],
                    "confidence_threshold": 80
                },
                "should_continue": {
                    "conditions": ["progress_momentum", "no_critical_interrupts"],
                    "confidence_threshold": 70
                },
                "should_complete": {
                    "conditions": ["all_requirements_met", "quality_validated", "context_updated"],
                    "confidence_threshold": 90
                }
            }
        }
    
    # Additional helper methods (simplified implementations)
    
    def _calculate_dependency_impact(self, task: Dict[str, Any], task_context: Dict[str, Any]) -> int:
        """Calculate impact score for task dependencies"""
        # Simplified implementation
        return 25 if task.get("is_dependency", False) else 0
    
    def _calculate_urgency_score(self, task: Dict[str, Any]) -> int:
        """Calculate urgency score for task"""
        priority_scores = {"low": 10, "medium": 30, "high": 60, "urgent": 90}
        return priority_scores.get(task.get("priority", "medium"), 30)
    
    def _generate_autonomous_action_recommendations(self, state: Dict[str, Any], task_context: Dict[str, Any]) -> List[str]:
        """Generate action recommendations for autonomous agents"""
        
        recommendations = []
        
        if state["phase"] == "not_started" and state.get("autonomous_ready"):
            recommendations.append("RECOMMENDED: Start task immediately")
        
        if state["time_since_update"] > 1800:
            recommendations.append("REQUIRED: Update progress status")
        
        if state["can_complete"]:
            recommendations.append("RECOMMENDED: Complete task now")
        
        return recommendations
    
    def _generate_priority_guidance(self, state: Dict[str, Any], task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate priority guidance for autonomous decision making"""
        
        return {
            "current_priority": state.get("priority_score", 50),
            "priority_factors": {
                "progress_preservation": 30 if state["progress"] > 70 else 0,
                "completion_proximity": 20 if state["progress"] > 90 else 0,
                "time_investment": 15 if state["time_since_update"] < 3600 else 0
            },
            "priority_recommendation": "HIGH" if state.get("priority_score", 50) > 70 else "MEDIUM",
            "switching_advice": "PRESERVE CONTEXT" if state["progress"] > 70 else "FLEXIBLE"
        }
    
    def _enhance_error_response(self, response: Dict[str, Any], action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance error responses with helpful guidance"""
        
        error = response.get("error", "Unknown error")
        
        # Add resolution guidance
        response["resolution_guidance"] = {
            "error_summary": error,
            "likely_cause": self._diagnose_error(error, action, params),
            "resolution_steps": self._get_resolution_steps(error, action),
            "autonomous_recovery": self._get_autonomous_recovery_steps(error, action)
        }
        
        return response
    
    def _diagnose_error(self, error: str, action: str, params: Dict[str, Any]) -> str:
        """Diagnose likely cause of error"""
        
        if "context must be updated" in error.lower():
            return "Task context is outdated or missing"
        elif "missing required field" in error.lower():
            return f"Required parameter not provided for {action}"
        elif "subtasks must be completed" in error.lower():
            return "Parent task has incomplete subtasks"
        elif "not found" in error.lower():
            return "Task or resource does not exist"
        else:
            return "Check error message for specific requirements"
    
    def _get_resolution_steps(self, error: str, action: str) -> List[str]:
        """Get steps to resolve the error"""
        
        steps = []
        
        if "context must be updated" in error.lower():
            steps.extend([
                "1. Update task context using quick_task_update",
                "2. Ensure progress percentage reflects actual completion",
                "3. Retry the completion"
            ])
        elif "subtasks must be completed" in error.lower():
            steps.extend([
                "1. List subtasks to identify incomplete items",
                "2. Complete all remaining subtasks",
                "3. Then complete the parent task"
            ])
        elif "missing required field" in error.lower():
            steps.extend([
                "1. Check the error message for the specific missing field",
                "2. Provide the required parameter",
                "3. Retry the operation"
            ])
        
        return steps
    
    def _get_autonomous_recovery_steps(self, error: str, action: str) -> List[str]:
        """Get autonomous recovery steps for errors"""
        
        recovery_steps = []
        
        if "context must be updated" in error.lower():
            recovery_steps.extend([
                "🤖 AUTO-RECOVERY: Call quick_task_update with current progress",
                "🤖 AUTO-RECOVERY: Then retry completion automatically"
            ])
        elif "not found" in error.lower():
            recovery_steps.extend([
                "🤖 AUTO-RECOVERY: Validate task existence before operations",
                "🤖 AUTO-RECOVERY: Request fresh task data if stale"
            ])
        
        return recovery_steps