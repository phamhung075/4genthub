"""Progressive Expander - Smart Context Expansion

Implements progressive task expansion from Epic → Feature → Task level
with intelligent context loading on demand and smart prefetching.

Key Features:
- Start with minimal context at Epic level
- Expand to Features when needed  
- Load Task details on demand
- Smart prefetching based on patterns
- Token-aware expansion (respects max_tokens limits)
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class ContextLevel(Enum):
    """Context expansion levels following the 4-tier hierarchy."""
    GLOBAL = "global"      # Organization-wide context
    PROJECT = "project"    # Project-specific context  
    BRANCH = "branch"      # Git branch context
    TASK = "task"          # Individual task context


class ExpansionTrigger(Enum):
    """Triggers for context expansion."""
    USER_REQUEST = "user_request"        # Explicit user request
    SIMILARITY_MATCH = "similarity_match"  # Semantic similarity detected
    DEPENDENCY_CHAIN = "dependency_chain"  # Task dependency requires context
    PATTERN_BASED = "pattern_based"        # Historical usage pattern
    TOKEN_AVAILABLE = "token_available"    # Available token space
    PREFETCH = "prefetch"                  # Predictive prefetching


@dataclass
class ExpansionCandidate:
    """Candidate for context expansion."""
    context_id: str
    context_level: ContextLevel
    context_type: str  # 'task', 'branch', 'project', 'global'
    priority_score: float  # 0.0 to 1.0
    estimated_tokens: int
    trigger: ExpansionTrigger
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpansionResult:
    """Result of context expansion operation."""
    expanded_contexts: List[Dict[str, Any]]
    total_tokens_used: int
    remaining_token_budget: int
    expansion_path: List[str]  # Path of expansion decisions
    prefetched_contexts: List[str] = field(default_factory=list)


class ProgressiveExpander:
    """
    Progressive context expansion engine.
    
    Implements the progressive task expansion component as specified in Phase 3:
    - Start with minimal context (Epic level)
    - Expand to Features when needed
    - Load Task details on demand  
    - Smart prefetching capabilities
    """
    
    def __init__(
        self,
        default_token_budget: int = 2000,
        min_context_tokens: int = 100,    # Minimum tokens to reserve for essential context
        prefetch_threshold: float = 0.7,  # Similarity threshold for prefetching
        expansion_factor: float = 1.5     # How aggressively to expand
    ):
        """
        Initialize progressive expander.
        
        Args:
            default_token_budget: Default maximum tokens to use
            min_context_tokens: Minimum tokens to keep in reserve
            prefetch_threshold: Threshold for prefetching similar contexts
            expansion_factor: Expansion aggressiveness (1.0 = conservative, 2.0 = aggressive)
        """
        self.default_token_budget = default_token_budget
        self.min_context_tokens = min_context_tokens
        self.prefetch_threshold = prefetch_threshold
        self.expansion_factor = expansion_factor
        
        # Track expansion patterns for learning
        self.expansion_history: List[Dict[str, Any]] = []
        self.context_access_patterns: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"ProgressiveExpander initialized (budget: {default_token_budget} tokens)")
    
    
    def estimate_context_tokens(self, context_data: Dict[str, Any]) -> int:
        """
        Estimate token count for context data.
        
        Args:
            context_data: Context data dictionary
            
        Returns:
            Estimated token count (rough approximation: 1 token ≈ 4 chars)
        """
        if not context_data:
            return 0
            
        # Convert to JSON string and estimate tokens
        json_str = json.dumps(context_data, default=str)
        char_count = len(json_str)
        
        # Rough estimation: 1 token ≈ 4 characters for English text
        token_estimate = max(1, char_count // 4)
        
        return token_estimate
    
    
    def _calculate_expansion_priority(
        self,
        context_id: str,
        context_level: ContextLevel,
        query_context: Dict[str, Any],
        trigger: ExpansionTrigger
    ) -> float:
        """
        Calculate priority score for context expansion.
        
        Args:
            context_id: ID of context to expand
            context_level: Level of context in hierarchy
            query_context: Current query/session context
            trigger: What triggered this expansion
            
        Returns:
            Priority score (0.0 to 1.0)
        """
        base_score = 0.5
        
        # Level-based scoring (deeper = higher priority when relevant)
        level_scores = {
            ContextLevel.TASK: 0.9,      # Most specific
            ContextLevel.BRANCH: 0.7,    # Branch-specific patterns  
            ContextLevel.PROJECT: 0.5,   # Project-wide context
            ContextLevel.GLOBAL: 0.3     # Organizational context
        }
        base_score = level_scores.get(context_level, 0.5)
        
        # Trigger-based adjustment
        trigger_modifiers = {
            ExpansionTrigger.USER_REQUEST: 1.0,      # Explicit user need
            ExpansionTrigger.SIMILARITY_MATCH: 0.8,  # Strong semantic match
            ExpansionTrigger.DEPENDENCY_CHAIN: 0.9,  # Required for understanding
            ExpansionTrigger.PATTERN_BASED: 0.6,     # Historical usage
            ExpansionTrigger.TOKEN_AVAILABLE: 0.4,   # Opportunistic
            ExpansionTrigger.PREFETCH: 0.3           # Speculative
        }
        trigger_modifier = trigger_modifiers.get(trigger, 0.5)
        
        # Historical access patterns
        access_bonus = 0.0
        if context_id in self.context_access_patterns:
            pattern = self.context_access_patterns[context_id]
            access_frequency = pattern.get('access_count', 0) / max(1, pattern.get('total_sessions', 1))
            access_bonus = min(0.3, access_frequency)  # Cap at 30% bonus
        
        # Recency bonus
        recency_bonus = 0.0
        if context_id in self.context_access_patterns:
            last_accessed = self.context_access_patterns[context_id].get('last_accessed')
            if last_accessed:
                # More recent access gets higher priority (up to 20% bonus)
                hours_ago = (datetime.now(timezone.utc) - last_accessed).total_seconds() / 3600
                recency_bonus = max(0.0, 0.2 * (1.0 - min(1.0, hours_ago / 24)))  # Decay over 24 hours
        
        final_score = base_score * trigger_modifier + access_bonus + recency_bonus
        return min(1.0, max(0.0, final_score))  # Clamp to [0, 1]
    
    
    def identify_expansion_candidates(
        self,
        current_context: Dict[str, Any],
        query: str,
        available_contexts: List[Dict[str, Any]],
        similarity_scores: Optional[Dict[str, float]] = None
    ) -> List[ExpansionCandidate]:
        """
        Identify candidates for context expansion.
        
        Args:
            current_context: Currently loaded context
            query: User query or session context
            available_contexts: All available contexts
            similarity_scores: Precomputed similarity scores
            
        Returns:
            List of expansion candidates sorted by priority
        """
        candidates = []
        
        for context in available_contexts:
            context_id = context.get('id', str(context.get('context_id', '')))
            context_type = context.get('context_type', 'unknown')
            
            # Skip if already in current context
            if context_id in current_context.get('loaded_contexts', []):
                continue
            
            # Determine context level
            if context_type == 'task':
                level = ContextLevel.TASK
            elif context_type == 'branch':
                level = ContextLevel.BRANCH
            elif context_type == 'project':
                level = ContextLevel.PROJECT
            else:
                level = ContextLevel.GLOBAL
            
            # Estimate token cost
            estimated_tokens = self.estimate_context_tokens(context)
            
            # Determine expansion triggers
            triggers = []
            
            # Similarity-based trigger
            if similarity_scores and context_id in similarity_scores:
                sim_score = similarity_scores[context_id]
                if sim_score >= self.prefetch_threshold:
                    triggers.append(ExpansionTrigger.SIMILARITY_MATCH)
                elif sim_score >= (self.prefetch_threshold * 0.7):  # Lower threshold for prefetch
                    triggers.append(ExpansionTrigger.PREFETCH)
            
            # Dependency-based trigger  
            if self._has_dependency_relationship(context, current_context):
                triggers.append(ExpansionTrigger.DEPENDENCY_CHAIN)
            
            # Pattern-based trigger
            if self._matches_usage_pattern(context_id, query):
                triggers.append(ExpansionTrigger.PATTERN_BASED)
            
            # Token availability trigger
            if estimated_tokens <= (self.default_token_budget * 0.1):  # Small contexts
                triggers.append(ExpansionTrigger.TOKEN_AVAILABLE)
            
            # Create candidates for each trigger
            for trigger in triggers or [ExpansionTrigger.TOKEN_AVAILABLE]:  # Default trigger
                priority = self._calculate_expansion_priority(
                    context_id, level, current_context, trigger
                )
                
                candidate = ExpansionCandidate(
                    context_id=context_id,
                    context_level=level,
                    context_type=context_type,
                    priority_score=priority,
                    estimated_tokens=estimated_tokens,
                    trigger=trigger,
                    metadata={
                        'similarity_score': similarity_scores.get(context_id, 0.0) if similarity_scores else 0.0,
                        'context_data': context
                    }
                )
                candidates.append(candidate)
        
        # Sort by priority score (descending)
        candidates.sort(key=lambda c: c.priority_score, reverse=True)
        
        logger.info(f"Identified {len(candidates)} expansion candidates")
        return candidates
    
    
    def expand_context_progressive(
        self,
        current_context: Dict[str, Any],
        expansion_candidates: List[ExpansionCandidate],
        token_budget: Optional[int] = None,
        aggressive: bool = False
    ) -> ExpansionResult:
        """
        Progressively expand context within token budget.
        
        Args:
            current_context: Current context state
            expansion_candidates: Sorted list of expansion candidates  
            token_budget: Available token budget (None = use default)
            aggressive: If True, use more aggressive expansion
            
        Returns:
            Expansion result with selected contexts and metadata
        """
        if token_budget is None:
            token_budget = self.default_token_budget
        
        # Reserve minimum tokens
        available_budget = max(0, token_budget - self.min_context_tokens)
        
        # Track expansion decisions
        expanded_contexts = []
        expansion_path = []
        prefetched_contexts = []
        tokens_used = 0
        
        # Apply expansion factor
        if aggressive:
            expansion_multiplier = self.expansion_factor * 1.2
        else:
            expansion_multiplier = self.expansion_factor
        
        # Progressive expansion algorithm
        for candidate in expansion_candidates:
            # Check if we have budget
            needed_tokens = int(candidate.estimated_tokens * expansion_multiplier)
            
            if tokens_used + needed_tokens > available_budget:
                # Try prefetching if it's a high-priority, low-cost item
                if (candidate.priority_score > 0.8 and 
                    candidate.estimated_tokens < (available_budget * 0.1)):
                    prefetched_contexts.append(candidate.context_id)
                    expansion_path.append(f"prefetch:{candidate.context_id}")
                continue
            
            # Add context to expansion
            context_data = candidate.metadata['context_data']
            expanded_contexts.append(context_data)
            tokens_used += needed_tokens
            
            # Record expansion decision
            decision = f"{candidate.trigger.value}:{candidate.context_level.value}:{candidate.context_id}"
            expansion_path.append(decision)
            
            # Update access patterns
            self._record_context_access(candidate.context_id)
            
            # Check for early termination conditions
            if candidate.trigger == ExpansionTrigger.USER_REQUEST:
                # User-requested contexts get priority, continue expanding related items
                continue
            elif tokens_used >= (available_budget * 0.8):
                # Used most of budget, switch to prefetch mode
                aggressive = False
                expansion_multiplier = self.expansion_factor * 0.8
        
        result = ExpansionResult(
            expanded_contexts=expanded_contexts,
            total_tokens_used=tokens_used,
            remaining_token_budget=available_budget - tokens_used,
            expansion_path=expansion_path,
            prefetched_contexts=prefetched_contexts
        )
        
        # Record this expansion for learning
        self.expansion_history.append({
            'timestamp': datetime.now(timezone.utc),
            'token_budget': token_budget,
            'tokens_used': tokens_used,
            'contexts_expanded': len(expanded_contexts),
            'contexts_prefetched': len(prefetched_contexts),
            'expansion_path': expansion_path
        })
        
        logger.info(
            f"Progressive expansion: {len(expanded_contexts)} contexts ({tokens_used}/{token_budget} tokens), "
            f"{len(prefetched_contexts)} prefetched"
        )
        
        return result
    
    
    def _has_dependency_relationship(
        self, 
        candidate_context: Dict[str, Any], 
        current_context: Dict[str, Any]
    ) -> bool:
        """Check if candidate has dependency relationship with current context."""
        # Task-level dependency checking
        candidate_id = candidate_context.get('id') or candidate_context.get('context_id')
        current_tasks = current_context.get('task_ids', [])
        current_dependencies = current_context.get('dependencies', [])
        
        # Direct dependency
        if candidate_id in current_dependencies:
            return True
        
        # Branch/project relationship
        candidate_branch = candidate_context.get('git_branch_id')
        current_branch = current_context.get('git_branch_id')
        
        if candidate_branch and current_branch and candidate_branch == current_branch:
            return True
        
        return False
    
    
    def _matches_usage_pattern(self, context_id: str, query: str) -> bool:
        """Check if context matches historical usage patterns."""
        if context_id not in self.context_access_patterns:
            return False
        
        pattern = self.context_access_patterns[context_id]
        
        # Frequent access pattern  
        access_frequency = pattern.get('access_count', 0) / max(1, pattern.get('total_sessions', 1))
        if access_frequency > 0.3:  # Accessed in >30% of sessions
            return True
        
        # Query keyword matching
        keywords = pattern.get('common_keywords', [])
        query_lower = query.lower()
        for keyword in keywords:
            if keyword.lower() in query_lower:
                return True
        
        return False
    
    
    def _record_context_access(self, context_id: str) -> None:
        """Record context access for pattern learning."""
        if context_id not in self.context_access_patterns:
            self.context_access_patterns[context_id] = {
                'access_count': 0,
                'total_sessions': 0,
                'last_accessed': None,
                'common_keywords': []
            }
        
        pattern = self.context_access_patterns[context_id]
        pattern['access_count'] += 1
        pattern['last_accessed'] = datetime.now(timezone.utc)
        
        # Could add keyword extraction from query here
    
    
    def get_expansion_stats(self) -> Dict[str, Any]:
        """Get statistics about expansion patterns."""
        if not self.expansion_history:
            return {}
        
        recent_expansions = self.expansion_history[-10:]  # Last 10 expansions
        
        avg_tokens = sum(exp['tokens_used'] for exp in recent_expansions) / len(recent_expansions)
        avg_contexts = sum(exp['contexts_expanded'] for exp in recent_expansions) / len(recent_expansions)
        
        return {
            'total_expansions': len(self.expansion_history),
            'avg_tokens_used': avg_tokens,
            'avg_contexts_expanded': avg_contexts,
            'tracked_context_patterns': len(self.context_access_patterns),
            'expansion_factor': self.expansion_factor,
            'token_budget': self.default_token_budget
        }