"""Context Prioritizer - Multi-factor Relevance Scoring

Implements intelligent context prioritization using multiple scoring factors
including relevance, recency, frequency, user preferences, and completeness.

Key Features:
- Score contexts by relevance to current query
- Consider recency and frequency of access
- Apply user preferences and project settings  
- Balance completeness vs context size
- Dynamic weight adjustment based on context
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import math

logger = logging.getLogger(__name__)


class ScoreFactor(Enum):
    """Different factors used in context scoring."""
    SEMANTIC_RELEVANCE = "semantic_relevance"    # How relevant to current query
    RECENCY = "recency"                         # How recently accessed
    FREQUENCY = "frequency"                     # How often accessed
    COMPLETENESS = "completeness"               # How complete the context is
    SIZE_PENALTY = "size_penalty"               # Penalty for large contexts
    USER_PREFERENCE = "user_preference"         # User-specific preferences
    PROJECT_PRIORITY = "project_priority"       # Project-level priorities
    DEPENDENCY_BOOST = "dependency_boost"       # Boost for dependency relationships
    TASK_STATUS = "task_status"                 # Task completion status relevance
    AGENT_AFFINITY = "agent_affinity"          # Affinity to assigned agents


@dataclass
class ScoringWeights:
    """Configurable weights for different scoring factors."""
    semantic_relevance: float = 0.3      # 30% weight
    recency: float = 0.15                # 15% weight  
    frequency: float = 0.15              # 15% weight
    completeness: float = 0.10           # 10% weight
    size_penalty: float = 0.05           # 5% penalty weight
    user_preference: float = 0.10        # 10% weight
    project_priority: float = 0.10       # 10% weight
    dependency_boost: float = 0.05       # 5% boost weight
    
    def normalize(self) -> 'ScoringWeights':
        """Normalize weights to sum to 1.0."""
        total = (self.semantic_relevance + self.recency + self.frequency + 
                self.completeness + self.user_preference + self.project_priority + 
                self.dependency_boost)
        
        if total > 0:
            factor = 1.0 / total
            return ScoringWeights(
                semantic_relevance=self.semantic_relevance * factor,
                recency=self.recency * factor,
                frequency=self.frequency * factor,
                completeness=self.completeness * factor,
                size_penalty=self.size_penalty,  # Keep as penalty
                user_preference=self.user_preference * factor,
                project_priority=self.project_priority * factor,
                dependency_boost=self.dependency_boost * factor
            )
        return self


@dataclass
class ContextScore:
    """Detailed score breakdown for a context."""
    context_id: str
    total_score: float
    factor_scores: Dict[ScoreFactor, float] = field(default_factory=dict)
    explanations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class UserPreferences:
    """User-specific context preferences."""
    preferred_context_types: List[str] = field(default_factory=list)
    max_context_size: int = 2000  # Max tokens
    priority_boost_keywords: List[str] = field(default_factory=list)
    penalty_keywords: List[str] = field(default_factory=list)
    agent_preferences: Dict[str, float] = field(default_factory=dict)  # agent_id -> preference score


class ContextPrioritizer:
    """
    Multi-factor context prioritization engine.
    
    Implements context prioritization as specified in Phase 3:
    - Score contexts by relevance
    - Consider recency and frequency  
    - Apply user preferences
    - Balance completeness vs size
    """
    
    def __init__(
        self,
        default_weights: Optional[ScoringWeights] = None,
        recency_decay_hours: float = 24.0,      # Hours for recency decay
        frequency_window_days: int = 30,         # Days for frequency calculation
        size_penalty_threshold: int = 1500      # Token count for size penalty
    ):
        """
        Initialize context prioritizer.
        
        Args:
            default_weights: Default scoring weights
            recency_decay_hours: Hours over which recency score decays
            frequency_window_days: Days to consider for frequency scoring
            size_penalty_threshold: Token threshold for applying size penalty
        """
        self.default_weights = default_weights or ScoringWeights()
        self.recency_decay_hours = recency_decay_hours
        self.frequency_window_days = frequency_window_days
        self.size_penalty_threshold = size_penalty_threshold
        
        # Track context access patterns
        self.context_access_history: Dict[str, List[datetime]] = {}
        self.context_metadata_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ContextPrioritizer initialized")
    
    
    def score_context(
        self,
        context_id: str,
        context_data: Dict[str, Any],
        query: str,
        semantic_similarity: float,
        user_preferences: Optional[UserPreferences] = None,
        project_context: Optional[Dict[str, Any]] = None,
        current_task: Optional[Dict[str, Any]] = None,
        weights: Optional[ScoringWeights] = None
    ) -> ContextScore:
        """
        Score a context using multiple factors.
        
        Args:
            context_id: ID of context to score
            context_data: Context data dictionary
            query: Current query or session context
            semantic_similarity: Precomputed semantic similarity score
            user_preferences: User-specific preferences
            project_context: Project-level context
            current_task: Current task context
            weights: Custom scoring weights
            
        Returns:
            Detailed context score
        """
        if weights is None:
            weights = self.default_weights.normalize()
        
        if user_preferences is None:
            user_preferences = UserPreferences()
        
        # Initialize score breakdown
        factor_scores = {}
        explanations = []
        
        # 1. Semantic Relevance Score
        semantic_score = self._calculate_semantic_score(
            context_data, query, semantic_similarity
        )
        factor_scores[ScoreFactor.SEMANTIC_RELEVANCE] = semantic_score
        explanations.append(f"Semantic relevance: {semantic_score:.3f}")
        
        # 2. Recency Score
        recency_score = self._calculate_recency_score(context_id)
        factor_scores[ScoreFactor.RECENCY] = recency_score
        explanations.append(f"Recency: {recency_score:.3f}")
        
        # 3. Frequency Score
        frequency_score = self._calculate_frequency_score(context_id)
        factor_scores[ScoreFactor.FREQUENCY] = frequency_score
        explanations.append(f"Frequency: {frequency_score:.3f}")
        
        # 4. Completeness Score
        completeness_score = self._calculate_completeness_score(context_data)
        factor_scores[ScoreFactor.COMPLETENESS] = completeness_score
        explanations.append(f"Completeness: {completeness_score:.3f}")
        
        # 5. Size Penalty
        size_penalty = self._calculate_size_penalty(context_data)
        factor_scores[ScoreFactor.SIZE_PENALTY] = size_penalty
        if size_penalty > 0:
            explanations.append(f"Size penalty: {size_penalty:.3f}")
        
        # 6. User Preference Score
        user_pref_score = self._calculate_user_preference_score(
            context_data, user_preferences, query
        )
        factor_scores[ScoreFactor.USER_PREFERENCE] = user_pref_score
        explanations.append(f"User preference: {user_pref_score:.3f}")
        
        # 7. Project Priority Score
        project_score = self._calculate_project_priority_score(
            context_data, project_context
        )
        factor_scores[ScoreFactor.PROJECT_PRIORITY] = project_score
        explanations.append(f"Project priority: {project_score:.3f}")
        
        # 8. Dependency Boost
        dependency_boost = self._calculate_dependency_boost(
            context_data, current_task
        )
        factor_scores[ScoreFactor.DEPENDENCY_BOOST] = dependency_boost
        if dependency_boost > 0:
            explanations.append(f"Dependency boost: {dependency_boost:.3f}")
        
        # Calculate total weighted score
        total_score = (
            semantic_score * weights.semantic_relevance +
            recency_score * weights.recency +
            frequency_score * weights.frequency +
            completeness_score * weights.completeness +
            user_pref_score * weights.user_preference +
            project_score * weights.project_priority +
            dependency_boost * weights.dependency_boost -
            size_penalty * weights.size_penalty  # Subtract penalty
        )
        
        # Ensure score is between 0 and 1
        total_score = max(0.0, min(1.0, total_score))
        
        return ContextScore(
            context_id=context_id,
            total_score=total_score,
            factor_scores=factor_scores,
            explanations=explanations,
            metadata={
                'estimated_tokens': self._estimate_tokens(context_data),
                'context_type': context_data.get('context_type', 'unknown'),
                'last_accessed': self._get_last_access_time(context_id)
            }
        )
    
    
    def score_contexts_batch(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        semantic_similarities: Dict[str, float],
        user_preferences: Optional[UserPreferences] = None,
        project_context: Optional[Dict[str, Any]] = None,
        current_task: Optional[Dict[str, Any]] = None,
        weights: Optional[ScoringWeights] = None
    ) -> List[ContextScore]:
        """
        Score multiple contexts efficiently.
        
        Args:
            contexts: List of context data dictionaries
            query: Current query or session context
            semantic_similarities: Precomputed similarity scores by context_id
            user_preferences: User-specific preferences
            project_context: Project-level context
            current_task: Current task context
            weights: Custom scoring weights
            
        Returns:
            List of context scores sorted by total score (descending)
        """
        scores = []
        
        for context in contexts:
            context_id = context.get('id') or str(context.get('context_id', ''))
            similarity = semantic_similarities.get(context_id, 0.0)
            
            score = self.score_context(
                context_id=context_id,
                context_data=context,
                query=query,
                semantic_similarity=similarity,
                user_preferences=user_preferences,
                project_context=project_context,
                current_task=current_task,
                weights=weights
            )
            scores.append(score)
        
        # Sort by total score (descending)
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        logger.info(f"Scored {len(scores)} contexts, top score: {scores[0].total_score:.3f}" if scores else "No contexts scored")
        return scores
    
    
    def _calculate_semantic_score(
        self, 
        context_data: Dict[str, Any], 
        query: str, 
        similarity: float
    ) -> float:
        """Calculate semantic relevance score."""
        # Base similarity score
        base_score = similarity
        
        # Boost for exact keyword matches
        query_words = set(query.lower().split())
        context_text = self._extract_searchable_text(context_data).lower()
        context_words = set(context_text.split())
        
        keyword_matches = len(query_words & context_words)
        keyword_boost = min(0.2, keyword_matches * 0.05)  # Up to 20% boost
        
        return min(1.0, base_score + keyword_boost)
    
    
    def _calculate_recency_score(self, context_id: str) -> float:
        """Calculate recency score based on last access time."""
        last_access = self._get_last_access_time(context_id)
        if not last_access:
            return 0.1  # Low score for never accessed
        
        hours_ago = (datetime.now(timezone.utc) - last_access).total_seconds() / 3600
        
        # Exponential decay: score = exp(-hours / decay_constant)
        decay_score = math.exp(-hours_ago / self.recency_decay_hours)
        
        return decay_score
    
    
    def _calculate_frequency_score(self, context_id: str) -> float:
        """Calculate frequency score based on access history."""
        if context_id not in self.context_access_history:
            return 0.1  # Low score for never accessed
        
        # Count accesses within frequency window
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.frequency_window_days)
        recent_accesses = [
            access for access in self.context_access_history[context_id]
            if access > cutoff
        ]
        
        # Normalize frequency (log scale to avoid dominance of very frequent items)
        frequency_score = math.log(len(recent_accesses) + 1) / math.log(self.frequency_window_days + 1)
        
        return min(1.0, frequency_score)
    
    
    def _calculate_completeness_score(self, context_data: Dict[str, Any]) -> float:
        """Calculate completeness score based on available data."""
        # Count non-empty fields
        total_fields = 0
        filled_fields = 0
        
        # Define expected fields by context type
        expected_fields = {
            'task': ['title', 'description', 'status', 'assignees', 'details'],
            'branch': ['git_branch_name', 'branch_info', 'branch_workflow'],
            'project': ['name', 'description', 'project_settings'],
            'global': ['organization_name', 'global_settings']
        }
        
        context_type = context_data.get('context_type', 'task')
        fields_to_check = expected_fields.get(context_type, expected_fields['task'])
        
        for field in fields_to_check:
            total_fields += 1
            if field in context_data and context_data[field]:
                if isinstance(context_data[field], (str, list, dict)):
                    if context_data[field]:  # Non-empty
                        filled_fields += 1
                else:
                    filled_fields += 1  # Non-empty primitive types
        
        completeness = filled_fields / total_fields if total_fields > 0 else 0.0
        
        return completeness
    
    
    def _calculate_size_penalty(self, context_data: Dict[str, Any]) -> float:
        """Calculate penalty for oversized contexts."""
        estimated_tokens = self._estimate_tokens(context_data)
        
        if estimated_tokens <= self.size_penalty_threshold:
            return 0.0
        
        # Linear penalty after threshold
        excess_tokens = estimated_tokens - self.size_penalty_threshold
        penalty = min(0.5, excess_tokens / self.size_penalty_threshold)  # Cap at 50% penalty
        
        return penalty
    
    
    def _calculate_user_preference_score(
        self, 
        context_data: Dict[str, Any], 
        user_preferences: UserPreferences,
        query: str
    ) -> float:
        """Calculate user preference score."""
        base_score = 0.5
        
        # Context type preference
        context_type = context_data.get('context_type', 'unknown')
        if context_type in user_preferences.preferred_context_types:
            base_score += 0.3
        
        # Keyword preferences
        query_lower = query.lower()
        context_text = self._extract_searchable_text(context_data).lower()
        
        # Boost for preferred keywords
        for keyword in user_preferences.priority_boost_keywords:
            if keyword.lower() in query_lower or keyword.lower() in context_text:
                base_score += 0.1
        
        # Penalty for avoided keywords
        for keyword in user_preferences.penalty_keywords:
            if keyword.lower() in query_lower or keyword.lower() in context_text:
                base_score -= 0.1
        
        # Agent preference
        assignees = context_data.get('assignees', [])
        if assignees and isinstance(assignees, list):
            for assignee in assignees:
                if assignee in user_preferences.agent_preferences:
                    pref_score = user_preferences.agent_preferences[assignee]
                    base_score += pref_score * 0.1  # Small boost/penalty
        
        return max(0.0, min(1.0, base_score))
    
    
    def _calculate_project_priority_score(
        self, 
        context_data: Dict[str, Any], 
        project_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate project-level priority score."""
        base_score = 0.5
        
        if not project_context:
            return base_score
        
        # Priority based on project settings
        project_priorities = project_context.get('priorities', {})
        context_type = context_data.get('context_type', 'unknown')
        
        if context_type in project_priorities:
            priority_multiplier = project_priorities[context_type]
            base_score = priority_multiplier
        
        # Task status priority
        if context_type == 'task':
            status = context_data.get('status', 'todo')
            status_priorities = {
                'in_progress': 0.9,
                'review': 0.8,
                'blocked': 0.7,
                'todo': 0.5,
                'done': 0.2
            }
            base_score *= status_priorities.get(status, 0.5)
        
        return max(0.0, min(1.0, base_score))
    
    
    def _calculate_dependency_boost(
        self, 
        context_data: Dict[str, Any], 
        current_task: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate boost for dependency relationships."""
        if not current_task:
            return 0.0
        
        context_id = context_data.get('id') or str(context_data.get('context_id', ''))
        current_task_id = current_task.get('id') or str(current_task.get('task_id', ''))
        
        # Check for direct dependency
        current_dependencies = current_task.get('dependencies', [])
        if context_id in current_dependencies:
            return 0.8  # Strong boost for direct dependencies
        
        # Check for same branch/project relationship
        context_branch = context_data.get('git_branch_id')
        current_branch = current_task.get('git_branch_id')
        
        if context_branch and current_branch and context_branch == current_branch:
            return 0.3  # Moderate boost for same branch
        
        context_project = context_data.get('project_id')
        current_project = current_task.get('project_id')
        
        if context_project and current_project and context_project == current_project:
            return 0.1  # Small boost for same project
        
        return 0.0
    
    
    def _estimate_tokens(self, context_data: Dict[str, Any]) -> int:
        """Estimate token count for context data."""
        import json
        json_str = json.dumps(context_data, default=str)
        return max(1, len(json_str) // 4)  # Rough approximation
    
    
    def _extract_searchable_text(self, context_data: Dict[str, Any]) -> str:
        """Extract searchable text from context data."""
        searchable_fields = ['title', 'description', 'details', 'name', 'git_branch_name']
        text_parts = []
        
        for field in searchable_fields:
            if field in context_data and isinstance(context_data[field], str):
                text_parts.append(context_data[field])
        
        return ' '.join(text_parts)
    
    
    def _get_last_access_time(self, context_id: str) -> Optional[datetime]:
        """Get last access time for context."""
        if context_id in self.context_access_history:
            access_times = self.context_access_history[context_id]
            return max(access_times) if access_times else None
        return None
    
    
    def record_context_access(self, context_id: str, access_time: Optional[datetime] = None) -> None:
        """Record context access for scoring."""
        if access_time is None:
            access_time = datetime.now(timezone.utc)
        
        if context_id not in self.context_access_history:
            self.context_access_history[context_id] = []
        
        self.context_access_history[context_id].append(access_time)
        
        # Keep only recent history to prevent unbounded growth
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.frequency_window_days * 2)
        self.context_access_history[context_id] = [
            access for access in self.context_access_history[context_id]
            if access > cutoff
        ]
    
    
    def adjust_weights_dynamically(
        self, 
        query: str, 
        context_type: str,
        user_feedback: Optional[Dict[str, float]] = None
    ) -> ScoringWeights:
        """
        Dynamically adjust scoring weights based on context.
        
        Args:
            query: Current query
            context_type: Type of contexts being scored
            user_feedback: User feedback on previous scoring results
            
        Returns:
            Adjusted scoring weights
        """
        weights = ScoringWeights()
        
        # Adjust based on query characteristics
        if len(query.split()) > 10:  # Long query
            weights.semantic_relevance = 0.4  # Increase semantic importance
            weights.completeness = 0.15       # Value complete contexts more
        elif len(query.split()) <= 3:        # Short query  
            weights.frequency = 0.2           # Rely more on usage patterns
            weights.recency = 0.2
        
        # Adjust based on context type
        if context_type == 'task':
            weights.dependency_boost = 0.1    # Task relationships matter
            weights.project_priority = 0.15   # Project context important
        elif context_type == 'global':
            weights.frequency = 0.1           # Global context less about frequency
            weights.completeness = 0.2        # Completeness very important
        
        # Apply user feedback if available
        if user_feedback:
            for factor_name, adjustment in user_feedback.items():
                if hasattr(weights, factor_name):
                    current_value = getattr(weights, factor_name)
                    new_value = max(0.0, min(1.0, current_value + adjustment))
                    setattr(weights, factor_name, new_value)
        
        return weights.normalize()
    
    
    def get_scoring_stats(self) -> Dict[str, Any]:
        """Get statistics about scoring performance."""
        total_contexts_tracked = len(self.context_access_history)
        
        if total_contexts_tracked == 0:
            return {}
        
        # Calculate access statistics
        total_accesses = sum(len(history) for history in self.context_access_history.values())
        avg_accesses_per_context = total_accesses / total_contexts_tracked
        
        # Most frequently accessed contexts
        frequent_contexts = sorted(
            self.context_access_history.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        return {
            'total_contexts_tracked': total_contexts_tracked,
            'total_accesses_recorded': total_accesses,
            'avg_accesses_per_context': avg_accesses_per_context,
            'recency_decay_hours': self.recency_decay_hours,
            'frequency_window_days': self.frequency_window_days,
            'size_penalty_threshold': self.size_penalty_threshold,
            'most_frequent_contexts': [
                {'context_id': ctx_id, 'access_count': len(history)}
                for ctx_id, history in frequent_contexts
            ]
        }