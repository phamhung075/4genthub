"""
Dependency Management Engine - Intelligent dependency analysis and management system

This module provides an AI-enhanced dependency management system that extends the existing
MCP dependency framework with intelligent analysis, automated detection, and execution optimization.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.application.dtos.task.dependency_info import (
    DependencyInfo, DependencyChain, DependencyRelationships
)
from fastmcp.task_management.application.services.dependency_resolver_service import DependencyResolverService

logger = logging.getLogger(__name__)


class SuggestionType(Enum):
    """Types of dependency suggestions"""
    CONTENT = "content"          # Based on content analysis (keywords, file refs)
    PATTERN = "pattern"          # Based on historical patterns (ML)
    SEMANTIC = "semantic"        # Based on semantic analysis (NLP)
    RESOURCE = "resource"        # Based on resource conflicts (agents)
    TEMPORAL = "temporal"        # Based on temporal relationships


class SuggestionStatus(Enum):
    """Status of dependency suggestions"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AUTO_APPLIED = "auto_applied"


@dataclass
class DependencyHint:
    """Hint for a potential dependency relationship"""
    task_id: str
    suggested_dependency_id: str
    confidence_score: float
    suggestion_reason: str
    suggestion_type: SuggestionType
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate confidence score"""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be between 0 and 1, got {self.confidence_score}")


@dataclass
class DependencySuggestion:
    """A suggestion for adding a dependency relationship"""
    hint: DependencyHint
    target_task_info: Optional[DependencyInfo] = None
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EnhancedDependencyRelationships:
    """Enhanced dependency relationships including AI suggestions"""
    basic_relationships: DependencyRelationships
    ai_suggestions: List[DependencySuggestion] = field(default_factory=list)
    suggestion_summary: str = ""
    optimization_score: float = 0.0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class ContentAnalyzer:
    """Analyzes task content to identify potential dependencies"""
    
    # Keywords that suggest dependencies
    DEPENDENCY_KEYWORDS = {
        'before': 1.0,
        'after': 1.0, 
        'requires': 0.9,
        'depends on': 0.9,
        'needs': 0.8,
        'blocks': 1.0,
        'blocked by': 1.0,
        'prerequisite': 0.9,
        'follows': 0.8,
        'precedes': 0.8,
        'implements': 0.7,
        'uses': 0.6,
        'extends': 0.7,
        'inherits from': 0.8,
        'based on': 0.6
    }
    
    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository
    
    def analyze_task_content(self, task) -> List[DependencyHint]:
        """
        Analyze task content to identify potential dependencies
        
        Args:
            task: Task entity to analyze
            
        Returns:
            List of dependency hints based on content analysis
        """
        hints = []
        
        try:
            # Combine all text content
            content_text = self._extract_text_content(task)
            
            # Get all tasks for cross-reference
            all_tasks = self._get_all_tasks_for_analysis(task)
            
            # Analyze keywords
            keyword_hints = self._analyze_dependency_keywords(task, content_text, all_tasks)
            hints.extend(keyword_hints)
            
            # Analyze file references
            file_hints = self._analyze_file_dependencies(task, content_text, all_tasks)
            hints.extend(file_hints)
            
            # Analyze agent assignments
            agent_hints = self._analyze_agent_dependencies(task, all_tasks)
            hints.extend(agent_hints)
            
            logger.info(f"Content analysis found {len(hints)} dependency hints for task {task.id}")
            
        except Exception as e:
            logger.error(f"Error analyzing task content for {task.id}: {e}")
        
        return hints
    
    def _extract_text_content(self, task) -> str:
        """Extract all text content from task for analysis"""
        content_parts = []
        
        if task.title:
            content_parts.append(task.title)
        if task.description:
            content_parts.append(task.description)
        if task.details:
            content_parts.append(task.details)
        
        return " ".join(content_parts).lower()
    
    def _get_all_tasks_for_analysis(self, current_task) -> List:
        """Get all tasks except current one for dependency analysis"""
        try:
            all_tasks = self.task_repository.find_all()
            # Filter out current task
            return [t for t in all_tasks if str(t.id) != str(current_task.id)]
        except Exception as e:
            logger.error(f"Error fetching tasks for analysis: {e}")
            return []
    
    def _analyze_dependency_keywords(self, task, content_text: str, all_tasks: List) -> List[DependencyHint]:
        """Analyze content for dependency keywords"""
        hints = []
        
        for keyword, base_score in self.DEPENDENCY_KEYWORDS.items():
            if keyword in content_text:
                # Look for task references near keywords
                for other_task in all_tasks:
                    other_title_lower = other_task.title.lower()
                    
                    # Check if other task's title appears near keyword
                    if other_title_lower in content_text:
                        # Calculate position-based confidence
                        keyword_pos = content_text.find(keyword)
                        title_pos = content_text.find(other_title_lower)
                        
                        if abs(keyword_pos - title_pos) < 100:  # Within 100 characters
                            proximity_score = max(0.5, 1.0 - abs(keyword_pos - title_pos) / 100)
                            confidence = base_score * proximity_score
                            
                            hint = DependencyHint(
                                task_id=str(task.id),
                                suggested_dependency_id=str(other_task.id),
                                confidence_score=min(confidence, 0.95),  # Cap at 95%
                                suggestion_reason=f"Found '{keyword}' near task '{other_task.title}' in content",
                                suggestion_type=SuggestionType.CONTENT,
                                evidence={
                                    "keyword": keyword,
                                    "proximity": abs(keyword_pos - title_pos),
                                    "base_score": base_score,
                                    "proximity_score": proximity_score
                                }
                            )
                            hints.append(hint)
        
        return hints
    
    def _analyze_file_dependencies(self, task, content_text: str, all_tasks: List) -> List[DependencyHint]:
        """Analyze file references to identify dependencies"""
        hints = []
        
        # Extract file paths from content (simple pattern matching)
        import re
        file_patterns = [
            r'[/\w\-\.]+\.(py|js|ts|tsx|jsx|java|cpp|h|sql|yaml|yml|json|xml|html|css)',
            r'src/[/\w\-\.]+',
            r'tests?/[/\w\-\.]+',
            r'docs?/[/\w\-\.]+',
            r'config/[/\w\-\.]+'
        ]
        
        found_files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, content_text, re.IGNORECASE)
            found_files.update(matches)
        
        if found_files:
            for other_task in all_tasks:
                other_content = self._extract_text_content(other_task)
                
                # Check for common file references
                common_files = []
                for file_path in found_files:
                    if file_path.lower() in other_content:
                        common_files.append(file_path)
                
                if common_files:
                    # Calculate confidence based on number of shared files
                    confidence = min(0.8, len(common_files) * 0.2)
                    
                    hint = DependencyHint(
                        task_id=str(task.id),
                        suggested_dependency_id=str(other_task.id),
                        confidence_score=confidence,
                        suggestion_reason=f"Tasks share {len(common_files)} file references: {', '.join(common_files[:3])}",
                        suggestion_type=SuggestionType.CONTENT,
                        evidence={
                            "shared_files": common_files,
                            "file_count": len(common_files)
                        }
                    )
                    hints.append(hint)
        
        return hints
    
    def _analyze_agent_dependencies(self, task, all_tasks: List) -> List[DependencyHint]:
        """Analyze agent assignments to identify resource dependencies"""
        hints = []
        
        if not task.assignees:
            return hints
        
        task_agents = set(task.assignees)
        
        for other_task in all_tasks:
            if not other_task.assignees:
                continue
                
            other_agents = set(other_task.assignees)
            shared_agents = task_agents.intersection(other_agents)
            
            if shared_agents:
                # Higher confidence for more shared agents
                confidence = min(0.7, len(shared_agents) * 0.3)
                
                # Check if other task is earlier (temporal hint)
                if hasattr(other_task, 'created_at') and hasattr(task, 'created_at'):
                    if other_task.created_at < task.created_at:
                        confidence += 0.1  # Slight boost for temporal order
                
                hint = DependencyHint(
                    task_id=str(task.id),
                    suggested_dependency_id=str(other_task.id),
                    confidence_score=min(confidence, 0.8),
                    suggestion_reason=f"Tasks share {len(shared_agents)} agent(s): {', '.join(list(shared_agents)[:2])}",
                    suggestion_type=SuggestionType.RESOURCE,
                    evidence={
                        "shared_agents": list(shared_agents),
                        "agent_overlap": len(shared_agents) / len(task_agents.union(other_agents))
                    }
                )
                hints.append(hint)
        
        return hints


class DependencyManagementEngine:
    """
    Main orchestrator for intelligent dependency management
    
    This engine extends the existing DependencyResolverService with AI-powered features:
    - Automated dependency detection from task content
    - Machine learning-based pattern recognition
    - Semantic analysis of task relationships
    - Graph optimization and execution planning
    """
    
    def __init__(
        self,
        dependency_resolver: DependencyResolverService,
        task_repository: TaskRepository,
        user_id: Optional[str] = None
    ):
        self.dependency_resolver = dependency_resolver
        self.task_repository = task_repository
        self.user_id = user_id
        
        # Initialize analyzers
        self.content_analyzer = ContentAnalyzer(task_repository)
        
        # Performance tracking
        self.performance_metrics = {
            "analysis_time": 0.0,
            "suggestions_generated": 0,
            "suggestions_accepted": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info("DependencyManagementEngine initialized")
    
    def with_user(self, user_id: str) -> 'DependencyManagementEngine':
        """Create a new engine instance scoped to a specific user"""
        return DependencyManagementEngine(
            self.dependency_resolver.with_user(user_id),
            self.task_repository,
            user_id
        )
    
    async def resolve_dependencies_with_ai(self, task_id: str) -> EnhancedDependencyRelationships:
        """
        Resolve dependencies with AI enhancements
        
        Args:
            task_id: ID of task to analyze
            
        Returns:
            Enhanced dependency relationships with AI suggestions
        """
        start_time = datetime.now()
        
        try:
            # Get basic dependency relationships first (backward compatibility)
            basic_relationships = self.dependency_resolver.resolve_dependencies(task_id)
            
            # Generate AI suggestions
            ai_suggestions = await self._generate_ai_suggestions(task_id)
            
            # Calculate optimization metrics
            optimization_score = self._calculate_optimization_score(basic_relationships, ai_suggestions)
            
            # Generate summary
            suggestion_summary = self._generate_suggestion_summary(ai_suggestions)
            
            # Update performance metrics
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.performance_metrics["analysis_time"] = analysis_time
            self.performance_metrics["suggestions_generated"] = len(ai_suggestions)
            
            return EnhancedDependencyRelationships(
                basic_relationships=basic_relationships,
                ai_suggestions=ai_suggestions,
                suggestion_summary=suggestion_summary,
                optimization_score=optimization_score,
                performance_metrics=self.performance_metrics.copy()
            )
            
        except Exception as e:
            logger.error(f"Error in AI dependency resolution for task {task_id}: {e}")
            
            # Fallback to basic resolution
            basic_relationships = self.dependency_resolver.resolve_dependencies(task_id)
            return EnhancedDependencyRelationships(
                basic_relationships=basic_relationships,
                ai_suggestions=[],
                suggestion_summary="AI analysis failed, showing basic dependencies only",
                optimization_score=0.0,
                performance_metrics={"error": str(e)}
            )
    
    def suggest_dependencies(self, task_id: str) -> List[DependencySuggestion]:
        """
        Generate dependency suggestions for a task
        
        Args:
            task_id: ID of task to analyze
            
        Returns:
            List of dependency suggestions with confidence scores
        """
        try:
            # Get the task
            task = self.task_repository.find_by_id(TaskId(task_id))
            if not task:
                raise TaskNotFoundError(f"Task {task_id} not found")
            
            # Generate hints from content analysis
            content_hints = self.content_analyzer.analyze_task_content(task)
            
            # Convert hints to suggestions with additional task info
            suggestions = []
            for hint in content_hints:
                # Get info about suggested dependency task
                try:
                    dep_task = self.task_repository.find_by_id(TaskId(hint.suggested_dependency_id))
                    if dep_task:
                        dep_info = DependencyInfo(
                            task_id=hint.suggested_dependency_id,
                            title=dep_task.title,
                            status=dep_task.status.value,
                            priority=dep_task.priority.value,
                            completion_percentage=dep_task.overall_progress,
                            is_blocking=False,
                            is_blocked=False,  # Will be calculated if needed
                            estimated_effort=dep_task.estimated_effort,
                            assignees=dep_task.assignees.copy() if dep_task.assignees else [],
                            updated_at=dep_task.updated_at
                        )
                        
                        suggestion = DependencySuggestion(
                            hint=hint,
                            target_task_info=dep_info
                        )
                        suggestions.append(suggestion)
                except Exception as e:
                    logger.warning(f"Could not get info for suggested dependency {hint.suggested_dependency_id}: {e}")
            
            # Sort by confidence score (highest first)
            suggestions.sort(key=lambda s: s.hint.confidence_score, reverse=True)
            
            # Limit to top suggestions to avoid overwhelming users
            return suggestions[:10]
            
        except Exception as e:
            logger.error(f"Error generating dependency suggestions for task {task_id}: {e}")
            return []
    
    async def _generate_ai_suggestions(self, task_id: str) -> List[DependencySuggestion]:
        """Generate AI-powered dependency suggestions (async for future ML integration)"""
        # For now, use content analysis (synchronous)
        # Future: Add async ML model inference, semantic analysis, etc.
        return self.suggest_dependencies(task_id)
    
    def _calculate_optimization_score(
        self, 
        basic_relationships: DependencyRelationships, 
        ai_suggestions: List[DependencySuggestion]
    ) -> float:
        """Calculate a score indicating how much the AI suggestions could improve the task"""
        if not ai_suggestions:
            return 0.0
        
        # Simple scoring based on suggestion confidence and existing dependencies
        high_confidence_suggestions = [s for s in ai_suggestions if s.hint.confidence_score > 0.7]
        existing_deps = len(basic_relationships.depends_on)
        
        # Score factors
        suggestion_score = sum(s.hint.confidence_score for s in high_confidence_suggestions) / len(ai_suggestions)
        coverage_score = min(1.0, len(high_confidence_suggestions) / max(1, existing_deps))
        
        return (suggestion_score + coverage_score) / 2
    
    def _generate_suggestion_summary(self, suggestions: List[DependencySuggestion]) -> str:
        """Generate human-readable summary of AI suggestions"""
        if not suggestions:
            return "No AI suggestions available"
        
        high_conf = len([s for s in suggestions if s.hint.confidence_score > 0.7])
        medium_conf = len([s for s in suggestions if 0.4 < s.hint.confidence_score <= 0.7])
        
        parts = []
        if high_conf:
            parts.append(f"{high_conf} high-confidence suggestion(s)")
        if medium_conf:
            parts.append(f"{medium_conf} medium-confidence suggestion(s)")
        
        total = len(suggestions)
        if parts:
            return f"Found {total} AI suggestions: {', '.join(parts)}"
        else:
            return f"Found {total} low-confidence AI suggestions"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the engine"""
        return self.performance_metrics.copy()
    
    def reset_performance_metrics(self):
        """Reset performance metrics"""
        self.performance_metrics = {
            "analysis_time": 0.0,
            "suggestions_generated": 0,
            "suggestions_accepted": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        logger.info("Performance metrics reset")