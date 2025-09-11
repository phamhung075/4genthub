"""Predictive Loader - Pattern-based Context Preloading

Implements predictive context loading based on tool usage patterns,
session history analysis, and intelligent prefetching strategies.

Key Features:
- Analyze tool usage patterns to predict next context needs
- Learn from session history for context prediction
- Preload likely contexts proactively
- Pattern recognition for workflow optimization
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple, Pattern
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import json
import re
from enum import Enum

logger = logging.getLogger(__name__)


class PredictionTrigger(Enum):
    """Triggers for predictive loading."""
    TOOL_SEQUENCE = "tool_sequence"        # Tool usage pattern detected
    SESSION_PATTERN = "session_pattern"    # Historical session pattern
    TIME_BASED = "time_based"             # Time-based patterns
    CONTEXT_CHAIN = "context_chain"       # Context access chain pattern
    USER_BEHAVIOR = "user_behavior"        # User behavior pattern


@dataclass
class UsagePattern:
    """Pattern extracted from usage history."""
    pattern_id: str
    pattern_type: str
    trigger: PredictionTrigger
    sequence: List[str]  # Sequence of actions/contexts
    confidence: float    # Confidence in pattern (0.0 to 1.0)
    frequency: int       # How often pattern occurs
    last_seen: datetime
    success_rate: float = 0.0  # How often prediction was correct
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    """Result of context prediction."""
    predicted_contexts: List[str]
    confidence_scores: Dict[str, float]
    patterns_used: List[str]
    prediction_reasons: List[str]
    preload_priority: Dict[str, float]


@dataclass
class SessionContext:
    """Context for current session analysis."""
    session_id: str
    start_time: datetime
    tool_sequence: List[str] = field(default_factory=list)
    context_sequence: List[str] = field(default_factory=list)
    current_task_type: Optional[str] = None
    user_id: Optional[str] = None


class PredictiveLoader:
    """
    Predictive context loading engine.
    
    Implements predictive context loading as specified in Phase 3:
    - Analyze tool usage patterns
    - Predict next context needs
    - Preload likely contexts  
    - Learn from session history
    """
    
    def __init__(
        self,
        pattern_min_frequency: int = 3,      # Minimum frequency to consider pattern
        pattern_confidence_threshold: float = 0.6,  # Minimum confidence for predictions
        session_history_days: int = 30,      # Days of session history to analyze
        max_preload_contexts: int = 5        # Maximum contexts to preload
    ):
        """
        Initialize predictive loader.
        
        Args:
            pattern_min_frequency: Minimum frequency to consider a usage pattern
            pattern_confidence_threshold: Minimum confidence for making predictions
            session_history_days: Days of history to consider for pattern analysis
            max_preload_contexts: Maximum number of contexts to preload
        """
        self.pattern_min_frequency = pattern_min_frequency
        self.pattern_confidence_threshold = pattern_confidence_threshold
        self.session_history_days = session_history_days
        self.max_preload_contexts = max_preload_contexts
        
        # Pattern storage
        self.usage_patterns: Dict[str, UsagePattern] = {}
        self.session_history: List[Dict[str, Any]] = []
        self.current_session: Optional[SessionContext] = None
        
        # Pattern recognition
        self.tool_sequences: Dict[Tuple[str, ...], int] = defaultdict(int)
        self.context_transitions: Dict[Tuple[str, str], int] = defaultdict(int)
        self.time_based_patterns: Dict[str, List[datetime]] = defaultdict(list)
        
        # Prediction accuracy tracking
        self.prediction_accuracy: Dict[str, Dict[str, float]] = {}
        
        logger.info("PredictiveLoader initialized")
    
    
    def start_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        """
        Start tracking a new session.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier (optional)
        """
        self.current_session = SessionContext(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            user_id=user_id
        )
        logger.info(f"Started session tracking: {session_id}")
    
    
    def record_tool_usage(self, tool_name: str, context_id: Optional[str] = None) -> None:
        """
        Record tool usage for pattern analysis.
        
        Args:
            tool_name: Name of tool used
            context_id: Context where tool was used (optional)
        """
        if not self.current_session:
            logger.warning("No active session for tool usage recording")
            return
        
        self.current_session.tool_sequence.append(tool_name)
        
        if context_id:
            self.current_session.context_sequence.append(context_id)
        
        # Update tool sequence patterns
        if len(self.current_session.tool_sequence) >= 2:
            # Look at last N tools for sequence patterns
            for window_size in [2, 3, 4]:
                if len(self.current_session.tool_sequence) >= window_size:
                    sequence = tuple(self.current_session.tool_sequence[-window_size:])
                    self.tool_sequences[sequence] += 1
        
        logger.debug(f"Recorded tool usage: {tool_name} (context: {context_id})")
    
    
    def record_context_access(self, context_id: str, context_type: str) -> None:
        """
        Record context access for transition pattern analysis.
        
        Args:
            context_id: ID of accessed context
            context_type: Type of context ('task', 'branch', etc.)
        """
        if not self.current_session:
            logger.warning("No active session for context access recording")
            return
        
        # Record context sequence
        if self.current_session.context_sequence:
            previous_context = self.current_session.context_sequence[-1]
            transition = (previous_context, context_id)
            self.context_transitions[transition] += 1
        
        self.current_session.context_sequence.append(context_id)
        
        # Record time-based patterns
        current_time = datetime.now(timezone.utc)
        time_key = f"{context_type}_{current_time.hour}"  # Hour-based pattern
        self.time_based_patterns[time_key].append(current_time)
        
        logger.debug(f"Recorded context access: {context_id} ({context_type})")
    
    
    def end_session(self) -> Dict[str, Any]:
        """
        End current session and analyze patterns.
        
        Returns:
            Session analysis results
        """
        if not self.current_session:
            logger.warning("No active session to end")
            return {}
        
        # Analyze session and extract patterns
        session_data = {
            'session_id': self.current_session.session_id,
            'user_id': self.current_session.user_id,
            'start_time': self.current_session.start_time,
            'end_time': datetime.now(timezone.utc),
            'tool_sequence': self.current_session.tool_sequence.copy(),
            'context_sequence': self.current_session.context_sequence.copy(),
            'duration_minutes': (datetime.now(timezone.utc) - self.current_session.start_time).total_seconds() / 60
        }
        
        # Add to session history
        self.session_history.append(session_data)
        
        # Cleanup old sessions
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.session_history_days)
        self.session_history = [
            session for session in self.session_history 
            if session['end_time'] > cutoff_date
        ]
        
        # Update usage patterns
        self._update_usage_patterns()
        
        logger.info(f"Ended session: {self.current_session.session_id}")
        self.current_session = None
        
        return session_data
    
    
    def predict_next_contexts(
        self,
        current_context: Dict[str, Any],
        recent_tools: List[str],
        session_context: Optional[Dict[str, Any]] = None
    ) -> PredictionResult:
        """
        Predict next likely contexts based on patterns.
        
        Args:
            current_context: Current context information
            recent_tools: Recently used tools
            session_context: Current session context
            
        Returns:
            Prediction results with confidence scores
        """
        predictions = {}
        confidence_scores = {}
        patterns_used = []
        prediction_reasons = []
        
        # Tool sequence-based predictions
        tool_predictions = self._predict_from_tool_sequence(recent_tools)
        for context_id, confidence in tool_predictions.items():
            predictions[context_id] = max(predictions.get(context_id, 0), confidence)
            confidence_scores[context_id] = confidence
            patterns_used.append(f"tool_sequence:{len(recent_tools)}")
            prediction_reasons.append(f"Tool sequence pattern suggests {context_id}")
        
        # Context transition-based predictions  
        current_context_id = current_context.get('id') or current_context.get('context_id')
        if current_context_id:
            transition_predictions = self._predict_from_context_transitions(current_context_id)
            for context_id, confidence in transition_predictions.items():
                existing_confidence = predictions.get(context_id, 0)
                combined_confidence = max(existing_confidence, confidence)
                predictions[context_id] = combined_confidence
                confidence_scores[context_id] = combined_confidence
                patterns_used.append(f"context_transition:{current_context_id}")
                prediction_reasons.append(f"Context transition pattern suggests {context_id}")
        
        # Time-based predictions
        time_predictions = self._predict_from_time_patterns()
        for context_id, confidence in time_predictions.items():
            existing_confidence = predictions.get(context_id, 0)
            combined_confidence = max(existing_confidence, confidence * 0.7)  # Lower weight for time patterns
            predictions[context_id] = combined_confidence
            confidence_scores[context_id] = combined_confidence
            patterns_used.append("time_based")
            prediction_reasons.append(f"Time-based pattern suggests {context_id}")
        
        # Session history-based predictions
        if session_context:
            history_predictions = self._predict_from_session_history(session_context)
            for context_id, confidence in history_predictions.items():
                existing_confidence = predictions.get(context_id, 0)
                combined_confidence = max(existing_confidence, confidence)
                predictions[context_id] = combined_confidence
                confidence_scores[context_id] = combined_confidence
                patterns_used.append("session_history")
                prediction_reasons.append(f"Session history pattern suggests {context_id}")
        
        # Filter by confidence threshold and limit results
        filtered_predictions = {
            context_id: confidence 
            for context_id, confidence in predictions.items()
            if confidence >= self.pattern_confidence_threshold
        }
        
        # Sort by confidence and limit
        sorted_predictions = sorted(
            filtered_predictions.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:self.max_preload_contexts]
        
        predicted_contexts = [context_id for context_id, _ in sorted_predictions]
        preload_priority = dict(sorted_predictions)
        
        result = PredictionResult(
            predicted_contexts=predicted_contexts,
            confidence_scores=confidence_scores,
            patterns_used=list(set(patterns_used)),
            prediction_reasons=prediction_reasons,
            preload_priority=preload_priority
        )
        
        logger.info(f"Predicted {len(predicted_contexts)} contexts with confidence >= {self.pattern_confidence_threshold}")
        return result
    
    
    def _predict_from_tool_sequence(self, recent_tools: List[str]) -> Dict[str, float]:
        """Predict contexts based on recent tool usage sequence."""
        predictions = {}
        
        if len(recent_tools) < 2:
            return predictions
        
        # Check if recent tools match known sequences
        for window_size in [2, 3, 4]:
            if len(recent_tools) >= window_size:
                sequence = tuple(recent_tools[-window_size:])
                
                # Look for patterns that start with this sequence
                for pattern_seq, frequency in self.tool_sequences.items():
                    if (len(pattern_seq) > len(sequence) and 
                        pattern_seq[:len(sequence)] == sequence and
                        frequency >= self.pattern_min_frequency):
                        
                        # Extract next expected tool and infer context
                        next_tool = pattern_seq[len(sequence)]
                        
                        # Map tools to likely context types (simplified heuristic)
                        context_mapping = self._get_tool_context_mapping()
                        if next_tool in context_mapping:
                            context_type = context_mapping[next_tool]
                            confidence = min(0.9, frequency / 10.0)  # Cap at 90%
                            predictions[f"predicted_{context_type}"] = confidence
        
        return predictions
    
    
    def _predict_from_context_transitions(self, current_context_id: str) -> Dict[str, float]:
        """Predict contexts based on context transition patterns."""
        predictions = {}
        
        # Look for transitions from current context
        for (from_context, to_context), frequency in self.context_transitions.items():
            if (from_context == current_context_id and 
                frequency >= self.pattern_min_frequency):
                
                confidence = min(0.9, frequency / 10.0)
                predictions[to_context] = confidence
        
        return predictions
    
    
    def _predict_from_time_patterns(self) -> Dict[str, float]:
        """Predict contexts based on time-based usage patterns."""
        predictions = {}
        current_hour = datetime.now(timezone.utc).hour
        
        for time_key, access_times in self.time_based_patterns.items():
            if len(access_times) < self.pattern_min_frequency:
                continue
            
            # Extract context type and hour from key
            parts = time_key.split('_')
            if len(parts) >= 2:
                context_type = parts[0]
                pattern_hour = int(parts[1])
                
                # Check if current time matches pattern
                if abs(current_hour - pattern_hour) <= 1:  # Within 1 hour
                    frequency = len(access_times)
                    confidence = min(0.7, frequency / 15.0)  # Lower confidence for time patterns
                    predictions[f"time_based_{context_type}"] = confidence
        
        return predictions
    
    
    def _predict_from_session_history(self, session_context: Dict[str, Any]) -> Dict[str, float]:
        """Predict contexts based on historical session patterns."""
        predictions = {}
        
        if len(self.session_history) < 2:
            return predictions
        
        # Analyze similar sessions
        current_tools = session_context.get('tool_sequence', [])
        current_contexts = session_context.get('context_sequence', [])
        
        for historical_session in self.session_history[-20:]:  # Look at recent sessions
            hist_tools = historical_session.get('tool_sequence', [])
            hist_contexts = historical_session.get('context_sequence', [])
            
            # Calculate similarity to current session
            tool_similarity = self._calculate_sequence_similarity(current_tools, hist_tools)
            context_similarity = self._calculate_sequence_similarity(current_contexts, hist_contexts)
            
            if tool_similarity > 0.5 or context_similarity > 0.5:
                # Predict contexts that appeared later in similar sessions
                similarity_score = max(tool_similarity, context_similarity)
                
                # Get contexts that appeared after similar point
                for context_id in hist_contexts[len(current_contexts):]:
                    confidence = similarity_score * 0.8  # Moderate confidence
                    predictions[context_id] = max(predictions.get(context_id, 0), confidence)
        
        return predictions
    
    
    def _calculate_sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """Calculate similarity between two sequences."""
        if not seq1 or not seq2:
            return 0.0
        
        # Simple Jaccard similarity
        set1 = set(seq1)
        set2 = set(seq2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    
    def _get_tool_context_mapping(self) -> Dict[str, str]:
        """Get mapping from tools to likely context types."""
        # This could be learned from data, but starting with heuristics
        return {
            'manage_task': 'task',
            'manage_subtask': 'task',
            'manage_git_branch': 'branch',
            'manage_project': 'project',
            'manage_context': 'context',
            'Bash': 'execution',
            'Read': 'file',
            'Write': 'file',
            'Edit': 'file'
        }
    
    
    def _update_usage_patterns(self) -> None:
        """Update usage patterns based on recent session data."""
        if not self.session_history:
            return
        
        # Extract patterns from recent sessions
        recent_sessions = self.session_history[-10:]  # Last 10 sessions
        
        for session in recent_sessions:
            tools = session.get('tool_sequence', [])
            contexts = session.get('context_sequence', [])
            
            # Create patterns from tool sequences
            for window_size in [2, 3, 4]:
                for i in range(len(tools) - window_size + 1):
                    sequence = tuple(tools[i:i + window_size])
                    pattern_id = f"tool_seq_{hash(sequence)}"
                    
                    if pattern_id not in self.usage_patterns:
                        self.usage_patterns[pattern_id] = UsagePattern(
                            pattern_id=pattern_id,
                            pattern_type='tool_sequence',
                            trigger=PredictionTrigger.TOOL_SEQUENCE,
                            sequence=list(sequence),
                            confidence=0.5,
                            frequency=1,
                            last_seen=datetime.now(timezone.utc)
                        )
                    else:
                        pattern = self.usage_patterns[pattern_id]
                        pattern.frequency += 1
                        pattern.last_seen = datetime.now(timezone.utc)
                        pattern.confidence = min(0.9, pattern.frequency / 10.0)
        
        logger.debug(f"Updated {len(self.usage_patterns)} usage patterns")
    
    
    def validate_predictions(
        self,
        predictions: List[str],
        actual_contexts: List[str],
        pattern_ids: List[str]
    ) -> Dict[str, float]:
        """
        Validate prediction accuracy and update pattern success rates.
        
        Args:
            predictions: Predicted context IDs
            actual_contexts: Actually accessed context IDs  
            pattern_ids: Pattern IDs used for predictions
            
        Returns:
            Accuracy metrics by pattern
        """
        accuracy_by_pattern = {}
        
        # Calculate hit rate
        correct_predictions = set(predictions) & set(actual_contexts)
        hit_rate = len(correct_predictions) / len(predictions) if predictions else 0.0
        
        # Update pattern success rates
        for pattern_id in pattern_ids:
            if pattern_id in self.usage_patterns:
                pattern = self.usage_patterns[pattern_id]
                
                # Update running average of success rate
                if pattern.success_rate == 0.0:
                    pattern.success_rate = hit_rate
                else:
                    # Exponential moving average
                    alpha = 0.2
                    pattern.success_rate = alpha * hit_rate + (1 - alpha) * pattern.success_rate
                
                accuracy_by_pattern[pattern_id] = pattern.success_rate
        
        logger.info(f"Prediction validation: {len(correct_predictions)}/{len(predictions)} correct (hit rate: {hit_rate:.2f})")
        return accuracy_by_pattern
    
    
    def get_prediction_stats(self) -> Dict[str, Any]:
        """Get statistics about prediction performance."""
        if not self.usage_patterns:
            return {}
        
        pattern_stats = []
        for pattern in self.usage_patterns.values():
            pattern_stats.append({
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type,
                'frequency': pattern.frequency,
                'confidence': pattern.confidence,
                'success_rate': pattern.success_rate
            })
        
        # Calculate overall stats
        total_patterns = len(self.usage_patterns)
        avg_success_rate = sum(p.success_rate for p in self.usage_patterns.values()) / total_patterns
        high_confidence_patterns = sum(1 for p in self.usage_patterns.values() if p.confidence > 0.7)
        
        return {
            'total_patterns': total_patterns,
            'avg_success_rate': avg_success_rate,
            'high_confidence_patterns': high_confidence_patterns,
            'session_history_count': len(self.session_history),
            'pattern_confidence_threshold': self.pattern_confidence_threshold,
            'patterns': pattern_stats[-10:]  # Last 10 patterns
        }