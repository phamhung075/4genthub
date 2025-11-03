"""
Response Enrichment Service

This service adds visual indicators and contextual guidance to task responses,
making them more understandable and actionable for AI agents.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ContextState:
    """Represents the state of a task's context"""
    exists: bool = False
    last_updated: Optional[datetime] = None
    staleness: Optional[str] = None  # 'fresh', 'stale', 'outdated'
    has_completion_summary: bool = False
    has_testing_notes: bool = False


@dataclass
class ResponseEnrichment:
    """Contains all enrichment data for a response"""
    visual_indicators: Dict[str, str] = field(default_factory=dict)
    context_hints: List[str] = field(default_factory=list)
    actionable_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    template_examples: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    context_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextStalnessLevel:
    """Staleness levels for context"""
    FRESH = "fresh"  # < 1 hour
    RECENT = "recent"  # < 24 hours  
    STALE = "stale"  # > 24 hours
    OUTDATED = "outdated"  # > 7 days
    MISSING = "missing"  # No context


class ResponseEnrichmentService:
    """
    Service for enriching task responses with visual indicators and contextual guidance.
    
    This helps AI agents better understand the state of tasks and what actions to take.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        self._user_id = user_id  # Store user context
        self.visual_indicators = {
            "context_missing": "🚫",
            "context_fresh": "✅",
            "context_stale": "⚠️",
            "context_outdated": "❌",
            "task_new": "🆕",
            "task_in_progress": "🔄",
            "task_blocked": "🚧",
            "task_completed": "✅",
            "priority_critical": "🔴",
            "priority_high": "🟠",
            "priority_medium": "🟡",
            "priority_low": "🟢"
        }

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'ResponseEnrichmentService':
        """Create a new service instance scoped to a specific user."""
        return ResponseEnrichmentService(user_id)
    
    def get_context_state(self, task_id: str, context_data: Optional[Dict[str, Any]] = None) -> ContextState:
        """
        Analyze the state of a task's context.
        
        Args:
            task_id: Task identifier
            context_data: Context data if available
            
        Returns:
            ContextState object describing the context
        """
        state = ContextState()
        
        if not context_data:
            state.exists = False
            state.staleness = ContextStalnessLevel.MISSING
            return state
        
        state.exists = True
        
        # Check for completion data
        metadata = context_data.get("metadata", {})
        state.has_completion_summary = bool(metadata.get("completion_summary"))
        state.has_testing_notes = bool(metadata.get("testing_notes"))
        
        # Check staleness
        updated_at = context_data.get("updated_at")
        if updated_at:
            try:
                if isinstance(updated_at, str):
                    state.last_updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                else:
                    state.last_updated = updated_at
                    
                # Calculate staleness
                now = datetime.now(state.last_updated.tzinfo)
                age = now - state.last_updated
                
                if age.total_seconds() < 3600:  # 1 hour
                    state.staleness = ContextStalnessLevel.FRESH
                elif age.days < 1:
                    state.staleness = ContextStalnessLevel.RECENT
                elif age.days < 7:
                    state.staleness = ContextStalnessLevel.STALE
                else:
                    state.staleness = ContextStalnessLevel.OUTDATED
            except Exception as e:
                logger.debug(f"Could not parse updated_at: {e}")
                state.staleness = ContextStalnessLevel.STALE
        else:
            state.staleness = ContextStalnessLevel.STALE
            
        return state
    
    def enrich_task_response(
        self,
        task_data: Dict[str, Any],
        action: str,
        context_state: Optional[ContextState] = None
    ) -> ResponseEnrichment:
        """
        Enrich a task response with visual indicators and guidance.
        
        Args:
            task_data: Task data from response
            action: Action that was performed
            context_state: Current state of the task's context
            
        Returns:
            ResponseEnrichment object with all enrichment data
        """
        enrichment = ResponseEnrichment()
        
        # Add visual indicators
        task_status = task_data.get("status", "todo")
        task_priority = task_data.get("priority", "medium")
        
        # Status indicator
        status_indicators = {
            "todo": self.visual_indicators["task_new"],
            "in_progress": self.visual_indicators["task_in_progress"],
            "blocked": self.visual_indicators["task_blocked"],
            "done": self.visual_indicators["task_completed"],
            "completed": self.visual_indicators["task_completed"]
        }
        enrichment.visual_indicators["status_indicator"] = status_indicators.get(
            task_status, "❓"
        )
        
        # Priority indicator
        priority_indicators = {
            "critical": self.visual_indicators["priority_critical"],
            "urgent": self.visual_indicators["priority_critical"],
            "high": self.visual_indicators["priority_high"],
            "medium": self.visual_indicators["priority_medium"],
            "low": self.visual_indicators["priority_low"]
        }
        enrichment.visual_indicators["priority_indicator"] = priority_indicators.get(
            task_priority, self.visual_indicators["priority_medium"]
        )
        
        # Context indicator
        if context_state:
            if not context_state.exists:
                enrichment.visual_indicators["context"] = self.visual_indicators["context_missing"]
                enrichment.context_hints.append("⚠️ No context exists - create one before completing")
            elif context_state.staleness == ContextStalnessLevel.FRESH:
                enrichment.visual_indicators["context"] = self.visual_indicators["context_fresh"]
            elif context_state.staleness == ContextStalnessLevel.STALE:
                enrichment.visual_indicators["context"] = self.visual_indicators["context_stale"]
                enrichment.context_hints.append("⚠️ Context is stale - update it with recent progress")
            elif context_state.staleness == ContextStalnessLevel.OUTDATED:
                enrichment.visual_indicators["context"] = self.visual_indicators["context_outdated"]
                enrichment.warnings.append("❌ Context is severely outdated - immediate update required")
        
        # Add actionable suggestions based on action and state
        if action == "create":
            enrichment.actionable_suggestions.append({
                "action": "Update status to in_progress",
                "command": f"manage_task(action='update', task_id='{task_data.get('id')}', status='in_progress')"
            })
            enrichment.actionable_suggestions.append({
                "action": "Create context for the task",
                "command": f"manage_context(action='create', level='task', context_id='{task_data.get('id')}', data={{...}})"
            })
            
        elif action == "update" and task_status == "in_progress":
            if context_state and context_state.staleness != ContextStalnessLevel.FRESH:
                enrichment.actionable_suggestions.append({
                    "action": "Update context with progress",
                    "command": f"manage_context(action='update', level='task', context_id='{task_data.get('id')}', data={{...}})"
                })
                
        elif action == "complete":
            if not context_state or not context_state.has_completion_summary:
                enrichment.warnings.append("⚠️ Task completed without completion summary in context")
                
        # Add template examples
        if action == "create":
            enrichment.template_examples["next_step"] = {
                "description": "Start working on the task",
                "commands": [
                    f"manage_task(action='update', task_id='{task_data.get('id')}', status='in_progress')",
                    f"manage_context(action='create', level='task', context_id='{task_data.get('id')}', data={{'title': '{task_data.get('title')}', 'description': 'Task context'}})"
                ]
            }
            
        # Add context summary
        if context_state:
            if context_state.exists:
                summary_parts = []
                summary_parts.append(f"Context: {enrichment.visual_indicators.get('context', '?')}")
                if context_state.staleness:
                    summary_parts.append(f"({context_state.staleness})")
                if context_state.has_completion_summary:
                    summary_parts.append("✅ Has completion summary")
                if context_state.has_testing_notes:
                    summary_parts.append("✅ Has testing notes")
                enrichment.context_summary = " ".join(summary_parts)
            else:
                enrichment.context_summary = "🚫 No context exists"
                
        # Add metadata
        enrichment.metadata = {
            "enriched_at": datetime.now().isoformat(),
            "action": action,
            "has_context": context_state.exists if context_state else False
        }
        
        return enrichment