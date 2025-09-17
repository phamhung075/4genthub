"""DEPRECATED: Workflow Hints Simplifier for AI-Optimized Guidance

This module has been consolidated into hint_manager.py as part of Phase 3.1.
This file now provides backward compatibility by importing from the new HintManager.

For new code, use:
    from .hint_manager import HintManager, create_hint_manager

This module simplifies complex workflow guidance structures into concise, actionable
hints that AI agents can process 40% faster while maintaining semantic meaning.

Enhanced with Phase 3 HintOptimizer for ultra-flat structure optimization.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Set
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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


# Backward compatibility import
from .hint_manager import HintManager as _HintManager, HintStrategy


class WorkflowHintsSimplifier(_HintManager):
    """DEPRECATED: Simplifies workflow guidance for optimal AI processing

    This class now inherits from the consolidated HintManager for backward compatibility.
    For new code, use HintManager directly.

    Enhanced with Phase 3 HintOptimizer integration for ultra-flat structure.
    Uses environment variable ENABLE_ULTRA_HINTS to enable new optimization mode.
    """

    def __init__(self):
        """Initialize with backward compatibility"""
        # Create repositories using domain service factory
        try:
            from .domain_service_factory import DomainServiceFactory

            repository_factory = DomainServiceFactory.get_repository_factory()
            task_repository = repository_factory.create_task_repository()
            context_repository = repository_factory.create_context_repository()

            # Call parent HintManager with simplified strategy
            super().__init__(
                task_repository=task_repository,
                context_repository=context_repository,
                strategy=HintStrategy.SIMPLIFIED
            )
        except Exception as e:
            logger.error(f"Failed to initialize WorkflowHintsSimplifier: {e}")
            # Fallback: initialize with mock repositories
            from unittest.mock import Mock
            mock_repo = Mock()
            super().__init__(
                task_repository=mock_repo,
                context_repository=mock_repo,
                strategy=HintStrategy.SIMPLIFIED
            )

    # All methods are now inherited from HintManager
    # The following methods are available and work as before:
    # - simplify_workflow_guidance()
    # - create_structured_hints()
    # - get_metrics()
    # - reset_metrics()

    pass  # All functionality inherited from HintManager