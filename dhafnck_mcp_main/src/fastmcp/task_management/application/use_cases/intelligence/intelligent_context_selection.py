"""Intelligent Context Selection Use Case

Application layer use case that orchestrates intelligent context selection
using the domain intelligence services. Provides the main interface for
MCP controllers to access intelligent context selection capabilities.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from ....domain.services.intelligence.intelligent_context_selector import (
    IntelligentContextSelector, SelectionResult, UserPreferences
)
from ....infrastructure.repositories.context_repository import ContextRepository
from ....infrastructure.repositories.task_repository import TaskRepository
from ....infrastructure.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)


@dataclass
class IntelligentSelectionRequest:
    """Request for intelligent context selection."""
    query: str
    max_tokens: int = 2000
    user_id: Optional[str] = None
    current_task_id: Optional[str] = None
    project_id: Optional[str] = None
    git_branch_id: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None
    aggressive_expansion: bool = False
    session_id: Optional[str] = None


@dataclass 
class IntelligentSelectionResponse:
    """Response from intelligent context selection."""
    selected_contexts: List[Dict[str, Any]]
    total_tokens_used: int
    selection_time_ms: float
    performance_metrics: Dict[str, Any]
    recommendations: List[str]
    success: bool = True
    error_message: Optional[str] = None


class IntelligentContextSelectionUseCase:
    """
    Use case for intelligent context selection.
    
    Orchestrates the intelligent context selection process by:
    1. Loading relevant contexts from repositories
    2. Applying intelligent selection algorithm
    3. Returning optimized context selection
    4. Recording usage patterns for learning
    """
    
    def __init__(
        self,
        context_repository: ContextRepository,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        intelligent_selector: Optional[IntelligentContextSelector] = None
    ):
        """
        Initialize the use case.
        
        Args:
            context_repository: Repository for context data
            task_repository: Repository for task data
            project_repository: Repository for project data
            intelligent_selector: Intelligent context selector (optional, will create if None)
        """
        self.context_repository = context_repository
        self.task_repository = task_repository
        self.project_repository = project_repository
        
        # Initialize intelligent selector
        if intelligent_selector is None:
            self.intelligent_selector = IntelligentContextSelector()
        else:
            self.intelligent_selector = intelligent_selector
        
        # Track initialization
        self._contexts_loaded = False
        self._last_context_refresh = None
        
        logger.info("IntelligentContextSelectionUseCase initialized")
    
    
    async def execute(self, request: IntelligentSelectionRequest) -> IntelligentSelectionResponse:
        """
        Execute intelligent context selection.
        
        Args:
            request: Selection request with query and parameters
            
        Returns:
            Selection response with optimized contexts
        """
        try:
            # Start session tracking if provided
            if request.session_id:
                self.intelligent_selector.start_session(request.session_id, request.user_id)
            
            # Load available contexts
            await self._ensure_contexts_loaded(
                project_id=request.project_id,
                git_branch_id=request.git_branch_id
            )
            
            # Get current context information
            current_task = None
            if request.current_task_id:
                current_task = await self._get_current_task(request.current_task_id)
            
            project_context = None
            if request.project_id:
                project_context = await self._get_project_context(request.project_id)
            
            # Convert user preferences
            user_preferences = None
            if request.user_preferences:
                user_preferences = UserPreferences(
                    preferred_context_types=request.user_preferences.get('preferred_context_types', []),
                    max_context_size=request.user_preferences.get('max_context_size', 2000),
                    priority_boost_keywords=request.user_preferences.get('priority_boost_keywords', []),
                    penalty_keywords=request.user_preferences.get('penalty_keywords', []),
                    agent_preferences=request.user_preferences.get('agent_preferences', {})
                )
            
            # Execute intelligent selection
            selection_result = self.intelligent_selector.select_context(
                query=request.query,
                max_tokens=request.max_tokens,
                user_preferences=user_preferences,
                current_task=current_task,
                project_context=project_context,
                aggressive_expansion=request.aggressive_expansion
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(selection_result, request)
            
            # Record selection for learning
            await self._record_selection_for_learning(request, selection_result)
            
            return IntelligentSelectionResponse(
                selected_contexts=selection_result.selected_contexts,
                total_tokens_used=selection_result.total_tokens_used,
                selection_time_ms=selection_result.selection_time_ms,
                performance_metrics={
                    'hit_rate_estimate': selection_result.hit_rate_estimate,
                    'size_reduction_percent': selection_result.size_reduction_percent,
                    'contexts_considered': selection_result.metadata.get('contexts_considered', 0),
                    'semantic_matches': selection_result.metadata.get('semantic_matches', 0),
                    'expansion_path': selection_result.metadata.get('expansion_path', [])
                },
                recommendations=recommendations,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error in intelligent context selection: {e}")
            return IntelligentSelectionResponse(
                selected_contexts=[],
                total_tokens_used=0,
                selection_time_ms=0.0,
                performance_metrics={},
                recommendations=[],
                success=False,
                error_message=str(e)
            )
    
    
    async def _ensure_contexts_loaded(
        self, 
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None
    ) -> None:
        """Ensure contexts are loaded into the intelligent selector."""
        # Check if we need to refresh contexts
        should_refresh = (
            not self._contexts_loaded or
            (self._last_context_refresh and 
             (datetime.now(timezone.utc) - self._last_context_refresh).total_seconds() > 300)  # 5 minutes
        )
        
        if not should_refresh:
            return
        
        logger.info("Loading contexts for intelligent selection")
        
        # Load contexts from repositories
        available_contexts = []
        
        # Load task contexts
        if git_branch_id:
            tasks = await self.task_repository.get_tasks_by_branch(git_branch_id)
            for task in tasks:
                context_data = {
                    'id': str(task.id),
                    'context_id': str(task.id),
                    'context_type': 'task',
                    'title': task.title,
                    'description': task.description,
                    'details': task.details,
                    'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                    'priority': task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                    'assignees': task.assignees,
                    'labels': task.labels,
                    'git_branch_id': str(task.git_branch_id),
                    'project_id': project_id,
                    'dependencies': [str(dep) for dep in task.dependencies] if task.dependencies else []
                }
                available_contexts.append(context_data)
        
        # Load project contexts
        if project_id:
            project = await self.project_repository.get_project_by_id(project_id)
            if project:
                project_context_data = {
                    'id': f"project_{project_id}",
                    'context_id': f"project_{project_id}",
                    'context_type': 'project',
                    'name': project.name,
                    'description': project.description,
                    'project_id': project_id
                }
                available_contexts.append(project_context_data)
        
        # Load branch contexts (simplified for now)
        if git_branch_id:
            branch_context_data = {
                'id': f"branch_{git_branch_id}",
                'context_id': f"branch_{git_branch_id}",
                'context_type': 'branch',
                'git_branch_id': git_branch_id,
                'project_id': project_id
            }
            available_contexts.append(branch_context_data)
        
        # Load global contexts (user-specific, simplified)
        global_context_data = {
            'id': 'global_context',
            'context_id': 'global_context', 
            'context_type': 'global',
            'organization_name': 'Default Organization'
        }
        available_contexts.append(global_context_data)
        
        # Load contexts into intelligent selector
        self.intelligent_selector.load_available_contexts(available_contexts)
        
        self._contexts_loaded = True
        self._last_context_refresh = datetime.now(timezone.utc)
        
        logger.info(f"Loaded {len(available_contexts)} contexts for intelligent selection")
    
    
    async def _get_current_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task context."""
        try:
            task = await self.task_repository.get_task_by_id(task_id)
            if task:
                return {
                    'id': str(task.id),
                    'task_id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                    'git_branch_id': str(task.git_branch_id),
                    'dependencies': [str(dep) for dep in task.dependencies] if task.dependencies else []
                }
        except Exception as e:
            logger.warning(f"Could not load current task {task_id}: {e}")
        
        return None
    
    
    async def _get_project_context(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project context."""
        try:
            project = await self.project_repository.get_project_by_id(project_id)
            if project:
                return {
                    'id': str(project.id),
                    'project_id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'priorities': {}  # Could be extended with project-specific priorities
                }
        except Exception as e:
            logger.warning(f"Could not load project context {project_id}: {e}")
        
        return None
    
    
    def _generate_recommendations(
        self, 
        selection_result: SelectionResult, 
        request: IntelligentSelectionRequest
    ) -> List[str]:
        """Generate recommendations based on selection results."""
        recommendations = []
        
        # Performance recommendations
        if selection_result.selection_time_ms > 150:  # Close to 200ms limit
            recommendations.append(
                "Selection time approaching limit. Consider reducing query complexity or token budget."
            )
        
        if selection_result.hit_rate_estimate < 0.7:
            recommendations.append(
                "Low relevance estimate. Try refining your query with more specific terms."
            )
        
        if selection_result.size_reduction_percent < 0.3:
            recommendations.append(
                "Limited context reduction achieved. Consider using a smaller token budget for more focused results."
            )
        
        # Context recommendations
        if len(selection_result.selected_contexts) == 0:
            recommendations.append(
                "No contexts selected. Try broadening your query or checking available contexts."
            )
        elif len(selection_result.selected_contexts) == 1:
            recommendations.append(
                "Only one context selected. Consider using aggressive expansion for more comprehensive results."
            )
        
        # Token usage recommendations
        token_utilization = selection_result.total_tokens_used / request.max_tokens
        if token_utilization < 0.5:
            recommendations.append(
                f"Token budget underutilized ({token_utilization:.1%}). Consider increasing expansion aggressiveness."
            )
        elif token_utilization > 0.9:
            recommendations.append(
                f"Token budget nearly exhausted ({token_utilization:.1%}). Consider increasing budget or reducing query scope."
            )
        
        return recommendations
    
    
    async def _record_selection_for_learning(
        self, 
        request: IntelligentSelectionRequest, 
        result: SelectionResult
    ) -> None:
        """Record selection for pattern learning."""
        try:
            # Record for predictive learning if session is active
            if request.session_id:
                # This could be enhanced to record more detailed patterns
                for context in result.selected_contexts:
                    context_id = context.get('id') or str(context.get('context_id', ''))
                    self.intelligent_selector.record_tool_usage('context_selection', context_id)
            
        except Exception as e:
            logger.warning(f"Could not record selection for learning: {e}")
    
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from the intelligent selector."""
        return self.intelligent_selector.get_performance_stats()
    
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Optimize performance based on collected metrics."""
        return self.intelligent_selector.optimize_performance()
    
    
    def refresh_contexts(self) -> None:
        """Force refresh of available contexts."""
        self._contexts_loaded = False
        self._last_context_refresh = None
        logger.info("Forced context refresh - contexts will reload on next selection")