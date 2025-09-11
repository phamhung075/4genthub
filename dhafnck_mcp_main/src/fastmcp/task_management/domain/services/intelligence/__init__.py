"""Intelligence Layer Services - Phase 3 Implementation

This module contains the core ML/AI services for intelligent context selection,
semantic matching, and predictive loading capabilities.

Components:
- SemanticMatcher: Embedding-based context similarity matching
- ProgressiveExpander: Smart context expansion from Epic -> Feature -> Task
- PredictiveLoader: Pattern-based context preloading
- ContextPrioritizer: Multi-factor relevance scoring
- IntelligentContextSelector: Main orchestrator (as per task spec)
"""

from .semantic_matcher import SemanticMatcher
from .progressive_expander import ProgressiveExpander  
from .predictive_loader import PredictiveLoader
from .context_prioritizer import ContextPrioritizer
from .intelligent_context_selector import IntelligentContextSelector

__all__ = [
    'SemanticMatcher',
    'ProgressiveExpander', 
    'PredictiveLoader',
    'ContextPrioritizer',
    'IntelligentContextSelector'
]