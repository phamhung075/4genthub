"""Workflow Hints Simplifier for AI-Optimized Guidance

This module simplifies complex workflow guidance structures into concise, actionable
hints that AI agents can process 40% faster while maintaining semantic meaning.

Enhanced with Phase 3 HintOptimizer for ultra-flat structure optimization.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Set
from enum import Enum
from dataclasses import dataclass
import re
import os

logger = logging.getLogger(__name__)

# Import Phase 3 HintOptimizer
try:
    from .hint_optimizer import HintOptimizer
    HINT_OPTIMIZER_AVAILABLE = True
except ImportError:
    logger.warning("HintOptimizer not available, falling back to legacy simplification")
    HINT_OPTIMIZER_AVAILABLE = False
    HintOptimizer = None


class HintType(Enum):
    """Types of workflow hints"""
    ACTION = "action"           # Next action to take
    VALIDATION = "validation"   # Validation requirements
    DEPENDENCY = "dependency"   # Dependency information
    CONTEXT = "context"        # Context requirements
    OPTIMIZATION = "optimization"  # Performance optimizations


class Priority(Enum):
    """Hint priority levels"""
    CRITICAL = "critical"      # Must be addressed immediately
    HIGH = "high"             # Should be addressed soon
    MEDIUM = "medium"         # Normal priority
    LOW = "low"              # Optional/nice-to-have


@dataclass
class SimplifiedHint:
    """Simplified workflow hint"""
    type: HintType
    action: str
    priority: Priority
    context: Optional[str] = None
    estimated_time: Optional[str] = None
    dependencies: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "type": self.type.value,
            "action": self.action,
            "priority": self.priority.value
        }
        if self.context:
            result["context"] = self.context
        if self.estimated_time:
            result["estimated_time"] = self.estimated_time
        if self.dependencies:
            result["dependencies"] = self.dependencies
        return result


class WorkflowHintsSimplifier:
    """Simplifies workflow guidance for optimal AI processing
    
    Enhanced with Phase 3 HintOptimizer integration for ultra-flat structure.
    Uses environment variable ENABLE_ULTRA_HINTS to enable new optimization mode.
    """
    
    # Action verb mapping for conciseness
    ACTION_VERBS = {
        # Reduce verbose phrases to single verbs
        "you should": "",
        "please": "",
        "it is recommended to": "",
        "consider": "",
        "you might want to": "",
        "it would be good to": "",
        "you may": "",
        # Simplify common actions
        "create a new": "create",
        "update the existing": "update",
        "delete the": "delete",
        "add a": "add",
        "remove the": "remove",
        "check if": "verify",
        "make sure": "ensure",
        "take a look at": "review",
        "go ahead and": "",
    }
    
    # Priority keywords
    PRIORITY_KEYWORDS = {
        Priority.CRITICAL: [
            "critical", "urgent", "immediately", "asap", "blocking",
            "must", "required", "essential", "mandatory"
        ],
        Priority.HIGH: [
            "important", "should", "recommended", "needs", "priority",
            "soon", "before", "after"
        ],
        Priority.MEDIUM: [
            "consider", "might", "could", "optional", "when possible"
        ],
        Priority.LOW: [
            "eventually", "if time permits", "nice to have", "future",
            "later", "minor"
        ]
    }
    
    # Context indicators
    CONTEXT_INDICATORS = {
        "when": "conditional",
        "if": "conditional", 
        "after": "sequential",
        "before": "sequential",
        "while": "concurrent",
        "during": "concurrent",
        "for": "scope",
        "with": "requirements"
    }
    
    def __init__(self):
        """Initialize the simplifier with optional Phase 3 HintOptimizer"""
        self._metrics = {
            "hints_processed": 0,
            "complexity_reduced": 0,
            "words_saved": 0,
            "processing_time_saved_ms": 0
        }
        
        # Phase 3: Ultra-flat hints optimization
        self.ultra_hints_enabled = (
            HINT_OPTIMIZER_AVAILABLE and
            os.getenv('ENABLE_ULTRA_HINTS', 'true').lower() in ['true', '1', 'yes', 'on']
        )
        
        if self.ultra_hints_enabled and HINT_OPTIMIZER_AVAILABLE:
            self.hint_optimizer = HintOptimizer()
            logger.info("Phase 3 Ultra-Hints optimization is ENABLED")
        else:
            self.hint_optimizer = None
            logger.info("Using legacy workflow hints simplification")
    
    def simplify_workflow_guidance(
        self,
        guidance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simplify complete workflow guidance structure
        
        Phase 3: Uses HintOptimizer for ultra-flat structure when enabled,
        otherwise falls back to legacy simplification.
        
        Args:
            guidance: Original workflow guidance
            
        Returns:
            Simplified guidance structure (flat hints or legacy format)
        """
        if not guidance:
            return {}
        
        # Phase 3: Use HintOptimizer for ultra-flat structure
        if self.ultra_hints_enabled and self.hint_optimizer:
            try:
                ultra_result = self.hint_optimizer.optimize_workflow_hints(guidance)
                
                # Merge performance metrics
                hint_metrics = self.hint_optimizer.get_performance_metrics()
                if hint_metrics["hints_processed"] > 0:
                    self._metrics["hints_processed"] += hint_metrics["hints_processed"]
                    self._metrics["complexity_reduced"] += hint_metrics["total_bytes_saved"]
                    
                logger.debug(
                    f"Ultra-hints optimization: {hint_metrics['average_reduction_percent']:.1f}% "
                    f"reduction, {hint_metrics['estimated_ai_speedup_percent']:.1f}% faster AI processing"
                )
                
                return ultra_result
                
            except Exception as e:
                logger.warning(f"HintOptimizer failed, falling back to legacy: {e}")
                # Fall through to legacy processing
        
        # Legacy simplification process
        simplified = {}
        
        # Process next steps
        if "next_steps" in guidance:
            simplified["next"] = self._simplify_next_steps(guidance["next_steps"])
        
        # Process autonomous guidance  
        if "autonomous_guidance" in guidance:
            autonomous = guidance["autonomous_guidance"]
            if isinstance(autonomous, dict):
                # Extract confidence if present
                if "confidence" in autonomous:
                    simplified["confidence"] = autonomous["confidence"]
                
                # Extract key guidance points
                if "recommendations" in autonomous:
                    simplified["recommendations"] = self._extract_key_points(
                        autonomous["recommendations"]
                    )
        
        # Process validation requirements
        if "validation" in guidance:
            simplified["validation"] = self._simplify_validation(guidance["validation"])
        
        # Process dependencies
        if "dependencies" in guidance:
            simplified["dependencies"] = self._simplify_dependencies(guidance["dependencies"])
        
        # Extract performance hints
        if "performance_hints" in guidance:
            simplified["performance"] = self._simplify_performance_hints(
                guidance["performance_hints"]
            )
        
        # Update metrics
        original_size = len(str(guidance))
        simplified_size = len(str(simplified))
        self._metrics["complexity_reduced"] += max(0, original_size - simplified_size)
        self._metrics["hints_processed"] += 1
        
        return simplified
    
    def _simplify_next_steps(self, next_steps: Any) -> Any:
        """Simplify next steps structure"""
        if isinstance(next_steps, dict):
            result = {}
            
            # Simplify recommendations
            if "recommendations" in next_steps:
                recommendations = next_steps["recommendations"]
                if isinstance(recommendations, list):
                    # Take top 3 most important recommendations
                    simplified_recs = []
                    for rec in recommendations[:3]:
                        simplified_recs.append(self._simplify_text(str(rec)))
                    result["actions"] = simplified_recs
                elif isinstance(recommendations, str):
                    result["action"] = self._simplify_text(recommendations)
            
            # Simplify required actions
            if "required_actions" in next_steps:
                required = next_steps["required_actions"]
                if isinstance(required, list):
                    result["required"] = [self._simplify_text(str(action)) for action in required[:3]]
                elif isinstance(required, str):
                    result["required"] = self._simplify_text(required)
            
            # Add context if present
            if "context" in next_steps:
                result["context"] = self._extract_key_context(next_steps["context"])
            
            return result
            
        elif isinstance(next_steps, list):
            # Convert list to simplified actions
            return [self._simplify_text(str(step)) for step in next_steps[:3]]
        
        elif isinstance(next_steps, str):
            return self._simplify_text(next_steps)
        
        return next_steps
    
    def _simplify_validation(self, validation: Any) -> Dict[str, Any]:
        """Simplify validation requirements"""
        if not validation:
            return {}
        
        result = {}
        
        if isinstance(validation, dict):
            # Extract required fields
            if "required_fields" in validation:
                result["required"] = validation["required_fields"]
            
            # Extract validation rules (simplified)
            if "rules" in validation:
                rules = validation["rules"]
                if isinstance(rules, list):
                    result["rules"] = [self._simplify_text(str(rule)) for rule in rules[:3]]
                elif isinstance(rules, str):
                    result["rule"] = self._simplify_text(rules)
            
            # Extract constraints
            if "constraints" in validation:
                result["constraints"] = self._extract_key_points(validation["constraints"])
        
        elif isinstance(validation, list):
            result["rules"] = [self._simplify_text(str(rule)) for rule in validation[:3]]
        
        return result
    
    def _simplify_dependencies(self, dependencies: Any) -> Any:
        """Simplify dependency information"""
        if isinstance(dependencies, dict):
            result = {}
            
            # Required dependencies
            if "required" in dependencies:
                result["required"] = self._extract_ids_or_names(dependencies["required"])
            
            # Optional dependencies
            if "optional" in dependencies:
                result["optional"] = self._extract_ids_or_names(dependencies["optional"])
            
            # Blocking information
            if "blocked_by" in dependencies:
                result["blocked_by"] = self._extract_ids_or_names(dependencies["blocked_by"])
            
            return result
        
        elif isinstance(dependencies, list):
            return self._extract_ids_or_names(dependencies)
        
        return dependencies
    
    def _simplify_performance_hints(self, hints: Any) -> Dict[str, Any]:
        """Simplify performance optimization hints"""
        if not hints:
            return {}
        
        result = {}
        
        if isinstance(hints, dict):
            # Cache suggestions
            if "caching" in hints:
                result["cache"] = self._simplify_text(str(hints["caching"]))
            
            # Query optimizations
            if "query_optimization" in hints:
                result["query"] = self._simplify_text(str(hints["query_optimization"]))
            
            # Field selection
            if "field_selection" in hints:
                result["fields"] = hints["field_selection"]
            
            # Batch operations
            if "batching" in hints:
                result["batch"] = self._simplify_text(str(hints["batching"]))
        
        return result
    
    def _simplify_text(self, text: str) -> str:
        """Simplify text by removing verbose phrases and words"""
        if not text or not isinstance(text, str):
            return text
        
        original_length = len(text.split())
        
        # Convert to lowercase for processing
        simplified = text.lower().strip()
        
        # Remove verbose phrases
        for verbose, replacement in self.ACTION_VERBS.items():
            simplified = re.sub(r'\b' + re.escape(verbose) + r'\b', replacement, simplified)
        
        # Remove extra whitespace
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        
        # Capitalize first letter
        if simplified:
            simplified = simplified[0].upper() + simplified[1:]
        
        # Track word savings
        final_length = len(simplified.split())
        self._metrics["words_saved"] += max(0, original_length - final_length)
        
        return simplified
    
    def _extract_key_points(self, data: Any, max_points: int = 3) -> List[str]:
        """Extract key points from complex data"""
        if isinstance(data, list):
            return [self._simplify_text(str(item)) for item in data[:max_points]]
        elif isinstance(data, dict):
            points = []
            for key, value in list(data.items())[:max_points]:
                if isinstance(value, str):
                    points.append(f"{key}: {self._simplify_text(value)}")
                else:
                    points.append(f"{key}: {str(value)}")
            return points
        elif isinstance(data, str):
            return [self._simplify_text(data)]
        else:
            return [str(data)]
    
    def _extract_key_context(self, context: Any) -> str:
        """Extract key context information"""
        if isinstance(context, dict):
            # Look for most important context keys
            priority_keys = ["when", "if", "after", "before", "requires"]
            for key in priority_keys:
                if key in context:
                    return f"{key} {self._simplify_text(str(context[key]))}"
            
            # Fallback to first available key
            if context:
                first_key = next(iter(context))
                return f"{first_key}: {self._simplify_text(str(context[first_key]))}"
        
        elif isinstance(context, str):
            return self._simplify_text(context)
        
        return str(context)
    
    def _extract_ids_or_names(self, data: Any) -> List[str]:
        """Extract IDs or names from complex dependency data"""
        if isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, dict):
                    # Look for ID or name fields
                    if "id" in item:
                        result.append(item["id"])
                    elif "name" in item:
                        result.append(item["name"])
                    elif "title" in item:
                        result.append(item["title"])
                    else:
                        result.append(str(item))
                else:
                    result.append(str(item))
            return result
        elif isinstance(data, dict):
            if "id" in data:
                return [data["id"]]
            elif "name" in data:
                return [data["name"]]
            elif "items" in data:
                return self._extract_ids_or_names(data["items"])
        
        return [str(data)]
    
    def _detect_priority(self, text: str) -> Priority:
        """Detect priority level from text"""
        text_lower = text.lower()
        
        # Check each priority level
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return priority
        
        return Priority.MEDIUM  # Default priority
    
    def _detect_hint_type(self, text: str) -> HintType:
        """Detect hint type from text content"""
        text_lower = text.lower()
        
        # Action keywords
        if any(word in text_lower for word in ["create", "update", "delete", "add", "remove", "run", "execute"]):
            return HintType.ACTION
        
        # Validation keywords
        if any(word in text_lower for word in ["validate", "check", "verify", "ensure", "required"]):
            return HintType.VALIDATION
        
        # Dependency keywords
        if any(word in text_lower for word in ["depends", "requires", "after", "before", "blocked"]):
            return HintType.DEPENDENCY
        
        # Context keywords
        if any(word in text_lower for word in ["when", "if", "while", "during", "context"]):
            return HintType.CONTEXT
        
        # Optimization keywords
        if any(word in text_lower for word in ["optimize", "cache", "performance", "faster", "efficient"]):
            return HintType.OPTIMIZATION
        
        return HintType.ACTION  # Default type
    
    def create_structured_hints(
        self,
        guidance: Dict[str, Any]
    ) -> List[SimplifiedHint]:
        """
        Create structured hints from guidance
        
        Args:
            guidance: Original workflow guidance
            
        Returns:
            List of structured hints
        """
        hints = []
        
        # Process next steps as action hints
        if "next_steps" in guidance:
            next_steps = guidance["next_steps"]
            
            if isinstance(next_steps, dict):
                # Recommendations become action hints
                if "recommendations" in next_steps:
                    recs = next_steps["recommendations"]
                    if isinstance(recs, list):
                        for rec in recs[:3]:  # Limit to top 3
                            hints.append(SimplifiedHint(
                                type=HintType.ACTION,
                                action=self._simplify_text(str(rec)),
                                priority=self._detect_priority(str(rec))
                            ))
                    elif isinstance(recs, str):
                        hints.append(SimplifiedHint(
                            type=HintType.ACTION,
                            action=self._simplify_text(recs),
                            priority=self._detect_priority(recs)
                        ))
                
                # Required actions become high priority hints
                if "required_actions" in next_steps:
                    required = next_steps["required_actions"]
                    if isinstance(required, list):
                        for action in required[:2]:  # Limit to top 2
                            hints.append(SimplifiedHint(
                                type=HintType.ACTION,
                                action=self._simplify_text(str(action)),
                                priority=Priority.HIGH
                            ))
        
        # Process validation as validation hints
        if "validation" in guidance:
            validation = guidance["validation"]
            if isinstance(validation, dict) and "rules" in validation:
                rules = validation["rules"]
                if isinstance(rules, list):
                    for rule in rules[:2]:
                        hints.append(SimplifiedHint(
                            type=HintType.VALIDATION,
                            action=self._simplify_text(str(rule)),
                            priority=Priority.HIGH
                        ))
        
        # Process dependencies
        if "dependencies" in guidance:
            deps = guidance["dependencies"]
            if isinstance(deps, dict) and "blocked_by" in deps:
                blocked_by = deps["blocked_by"]
                if blocked_by:
                    hints.append(SimplifiedHint(
                        type=HintType.DEPENDENCY,
                        action=f"Resolve {len(blocked_by)} blocking dependencies",
                        priority=Priority.CRITICAL,
                        dependencies=self._extract_ids_or_names(blocked_by)
                    ))
        
        return hints
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get simplification metrics including Phase 3 HintOptimizer metrics"""
        total_processed = self._metrics["hints_processed"]
        
        base_metrics = {
            "hints_processed": total_processed,
            "complexity_reduced_chars": self._metrics["complexity_reduced"],
            "words_saved": self._metrics["words_saved"],
            "avg_complexity_reduction": (
                self._metrics["complexity_reduced"] / total_processed
                if total_processed > 0 else 0
            ),
            "estimated_processing_speedup_percent": min(
                (self._metrics["words_saved"] / max(total_processed * 10, 1)) * 100,
                50  # Cap at 50% improvement
            )
        }
        
        # Add Phase 3 HintOptimizer metrics if available
        if self.ultra_hints_enabled and self.hint_optimizer:
            hint_metrics = self.hint_optimizer.get_performance_metrics()
            base_metrics.update({
                "phase_3_enabled": True,
                "ultra_hints_processed": hint_metrics["hints_processed"],
                "ultra_reduction_percent": hint_metrics["average_reduction_percent"],
                "ultra_ai_speedup_percent": hint_metrics["estimated_ai_speedup_percent"],
                "ultra_processing_time_ms": hint_metrics["average_processing_time_ms"],
                "ultra_compression_ratio": hint_metrics.get("compression_ratio", 0),
            })
        else:
            base_metrics["phase_3_enabled"] = False
        
        return base_metrics
    
    def reset_metrics(self) -> None:
        """Reset metrics including Phase 3 HintOptimizer metrics"""
        self._metrics = {
            "hints_processed": 0,
            "complexity_reduced": 0,
            "words_saved": 0,
            "processing_time_saved_ms": 0
        }
        
        # Reset Phase 3 HintOptimizer metrics if available
        if self.ultra_hints_enabled and self.hint_optimizer:
            self.hint_optimizer.reset_metrics()