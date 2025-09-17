"""
Workflow analysis service for the Vision System.

This service analyzes task patterns, identifies bottlenecks,
suggests optimizations, and learns from historical data.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

from ...domain.entities.task import Task
from ...domain.entities.context import TaskContext
from ...domain.value_objects.progress import ProgressType
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.context_repository import ContextRepository
from ...infrastructure.event_store import EventStore, get_event_store
from ...domain.value_objects.progress import ProgressStatus

logger = logging.getLogger(__name__)


@dataclass
class WorkflowPattern:
    """Represents a detected workflow pattern."""
    
    pattern_name: str
    pattern_type: str  # bottleneck, optimization, success_pattern
    confidence: float
    description: str
    affected_tasks: List[UUID]
    recommendations: List[str]
    metrics: Dict[str, Any]


@dataclass
class WorkflowAnalysis:
    """Results of workflow analysis."""
    
    task_id: UUID
    analysis_timestamp: datetime
    patterns: List[WorkflowPattern]
    bottlenecks: List[Dict[str, Any]]
    optimization_opportunities: List[Dict[str, Any]]
    predicted_completion_time: Optional[timedelta]
    risk_factors: List[str]
    success_indicators: List[str]


class WorkflowAnalysisService:
    """
    Service for analyzing workflow patterns and providing insights.
    
    This service identifies bottlenecks, suggests optimizations,
    and learns from historical task data to improve future predictions.
    """
    
    def __init__(
        self,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[Any] = None,  # EventStore not implemented yet
        user_id: Optional[str] = None
    ):
        self.task_repository = task_repository
        self.context_repository = context_repository
        self.event_store = event_store
        self._user_id = user_id  # Store user context
        
        # Cache for analysis results
        self._analysis_cache: Dict[UUID, WorkflowAnalysis] = {}
        self._pattern_cache: Dict[str, WorkflowPattern] = {}

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

    def with_user(self, user_id: str) -> 'WorkflowAnalysisService':
        """Create a new service instance scoped to a specific user."""
        return WorkflowAnalysisService(
            self.task_repository,
            self.context_repository,
            self.event_store,
            user_id
        )
    
    async def analyze_task_workflow(
        self,
        task_id: UUID,
        include_related: bool = True
    ) -> WorkflowAnalysis:
        """
        Perform comprehensive workflow analysis for a task.
        
        Args:
            task_id: Task to analyze
            include_related: Whether to include related tasks in analysis
            
        Returns:
            WorkflowAnalysis with patterns, bottlenecks, and recommendations
        """
        # Check cache
        if task_id in self._analysis_cache:
            cached = self._analysis_cache[task_id]
            if (datetime.now(timezone.utc) - cached.analysis_timestamp) < timedelta(hours=1):
                return cached
        
        # Fetch task and context
        task = await self.task_repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        context = await self._get_task_context(task_id)
        
        # Gather related data
        related_tasks = []
        if include_related:
            related_tasks = await self._get_related_tasks(task)
        
        # Perform various analyses
        patterns = await self._detect_patterns(task, context, related_tasks)
        bottlenecks = await self._identify_bottlenecks(task, context)
        optimizations = await self._find_optimization_opportunities(task, context, patterns)
        completion_time = await self._predict_completion_time(task, related_tasks)
        risk_factors = self._assess_risk_factors(task, context, patterns)
        success_indicators = self._identify_success_indicators(task, context)
        
        # Create analysis result
        analysis = WorkflowAnalysis(
            task_id=task_id,
            analysis_timestamp=datetime.now(timezone.utc),
            patterns=patterns,
            bottlenecks=bottlenecks,
            optimization_opportunities=optimizations,
            predicted_completion_time=completion_time,
            risk_factors=risk_factors,
            success_indicators=success_indicators
        )
        
        # Cache result
        self._analysis_cache[task_id] = analysis
        
        return analysis
    
    async def _get_task_context(self, task_id: UUID) -> Optional[TaskContext]:
        """Get context for a task."""
        try:
            return await self.context_repository.get_by_task_id(task_id)
        except Exception:
            return None
    
    async def _get_related_tasks(self, task: Task) -> List[Task]:
        """Get tasks related to the given task."""
        related = []
        
        # Get tasks with similar labels
        if hasattr(task, 'labels') and task.labels:
            for label in task.labels[:2]:
                tasks = await self.task_repository.list(
                    labels=[label],
                    limit=20
                )
                related.extend(tasks)
        
        # Get parent/child tasks
        if hasattr(task, 'parent_id') and task.parent_id:
            parent = await self.task_repository.get(task.parent_id)
            if parent:
                related.append(parent)
        
        if hasattr(task, 'subtasks') and task.subtasks:
            for subtask_id in task.subtasks:
                subtask = await self.task_repository.get(subtask_id)
                if subtask:
                    related.append(subtask)
        
        # Remove duplicates and self
        seen = set()
        unique = []
        for t in related:
            if t.id not in seen and t.id != task.id:
                seen.add(t.id)
                unique.append(t)
        
        return unique
    
    async def _detect_patterns(
        self,
        task: Task,
        context: Optional[TaskContext],
        related_tasks: List[Task]
    ) -> List[WorkflowPattern]:
        """Detect workflow patterns."""
        patterns = []
        
        # Check for common patterns
        patterns.extend(self._detect_completion_patterns(task, related_tasks))
        patterns.extend(self._detect_blocker_patterns(task, related_tasks))
        patterns.extend(self._detect_collaboration_patterns(task, context))
        patterns.extend(self._detect_progress_patterns(task))
        
        return patterns
    
    def _detect_completion_patterns(
        self,
        task: Task,
        related_tasks: List[Task]
    ) -> List[WorkflowPattern]:
        """Detect patterns related to task completion."""
        patterns = []
        
        # Analyze completion times of similar tasks
        completed_similar = [
            t for t in related_tasks
            if t.status == "done" and hasattr(t, 'created_at') and hasattr(t, 'updated_at')
        ]
        
        if len(completed_similar) >= 3:
            completion_times = [
                (t.updated_at - t.created_at).total_seconds() / 3600  # hours
                for t in completed_similar
            ]
            
            avg_time = sum(completion_times) / len(completion_times)
            
            # Check if current task is taking longer
            if hasattr(task, 'created_at'):
                current_duration = (datetime.now(timezone.utc) - task.created_at).total_seconds() / 3600
                
                if current_duration > avg_time * 1.5:
                    pattern = WorkflowPattern(
                        pattern_name="extended_duration",
                        pattern_type="bottleneck",
                        confidence=0.8,
                        description=f"Task is taking {current_duration:.1f}h vs avg {avg_time:.1f}h",
                        affected_tasks=[task.id],
                        recommendations=[
                            "Review task scope for unnecessary complexity",
                            "Consider breaking down into smaller tasks",
                            "Check for hidden blockers or dependencies"
                        ],
                        metrics={
                            "current_duration_hours": current_duration,
                            "average_duration_hours": avg_time,
                            "sample_size": len(completed_similar)
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_blocker_patterns(
        self,
        task: Task,
        related_tasks: List[Task]
    ) -> List[WorkflowPattern]:
        """Detect patterns related to blockers."""
        patterns = []
        
        # Count blocked tasks in related set
        blocked_count = sum(1 for t in related_tasks if t.status == "blocked")
        total_count = len(related_tasks)
        
        if total_count > 5 and blocked_count / total_count > 0.3:
            pattern = WorkflowPattern(
                pattern_name="high_blocker_rate",
                pattern_type="bottleneck",
                confidence=0.85,
                description=f"{blocked_count}/{total_count} related tasks are blocked",
                affected_tasks=[t.id for t in related_tasks if t.status == "blocked"],
                recommendations=[
                    "Investigate common blocker themes",
                    "Schedule team discussion on blockers",
                    "Consider process improvements"
                ],
                metrics={
                    "blocked_count": blocked_count,
                    "total_count": total_count,
                    "blocker_rate": blocked_count / total_count
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_collaboration_patterns(
        self,
        task: Task,
        context: Optional[TaskContext]
    ) -> List[WorkflowPattern]:
        """Detect patterns suggesting collaboration needs."""
        patterns = []
        
        indicators = []
        
        # Check task age
        if hasattr(task, 'created_at'):
            age = datetime.now(timezone.utc) - task.created_at
            if age > timedelta(days=14) and task.status not in ["done", "cancelled"]:
                indicators.append("long_running")
        
        # Check for multiple assignees
        if hasattr(task, 'assignees') and len(task.assignees) > 2:
            indicators.append("multiple_assignees")
        
        # Check context for collaboration mentions
        if context and context.notes:
            collab_keywords = ["help", "stuck", "blocked", "review", "discuss"]
            notes_text = str(context.notes).lower()
            if any(keyword in notes_text for keyword in collab_keywords):
                indicators.append("collaboration_keywords")
        
        if len(indicators) >= 2:
            pattern = WorkflowPattern(
                pattern_name="collaboration_opportunity",
                pattern_type="optimization",
                confidence=0.75,
                description="Multiple indicators suggest collaboration would help",
                affected_tasks=[task.id],
                recommendations=[
                    "Schedule pair programming session",
                    "Request code review",
                    "Organize team discussion"
                ],
                metrics={
                    "indicators": indicators,
                    "indicator_count": len(indicators)
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_progress_patterns(self, task: Task) -> List[WorkflowPattern]:
        """Detect patterns in task progress."""
        patterns = []
        
        if not hasattr(task, 'progress_breakdown'):
            return patterns
        
        breakdown = task.progress_breakdown
        
        # Check for unbalanced progress
        if breakdown:
            progress_values = list(breakdown.values())
            if progress_values:
                max_progress = max(progress_values)
                min_progress = min(progress_values)
                
                if max_progress - min_progress > 0.6:
                    lagging_types = [
                        pt for pt, progress in breakdown.items()
                        if progress < 0.3 and max_progress > 0.7
                    ]
                    
                    if lagging_types:
                        pattern = WorkflowPattern(
                            pattern_name="unbalanced_progress",
                            pattern_type="optimization",
                            confidence=0.8,
                            description="Some progress types are significantly lagging",
                            affected_tasks=[task.id],
                            recommendations=[
                                f"Focus on lagging areas: {', '.join(lagging_types)}",
                                "Consider parallel work streams",
                                "Reassess task priorities"
                            ],
                            metrics={
                                "max_progress": max_progress,
                                "min_progress": min_progress,
                                "lagging_types": lagging_types
                            }
                        )
                        patterns.append(pattern)
        
        return patterns
    
    async def _identify_bottlenecks(
        self,
        task: Task,
        context: Optional[TaskContext]
    ) -> List[Dict[str, Any]]:
        """Identify workflow bottlenecks."""
        bottlenecks = []
        
        # Check for stalled progress
        if hasattr(task, 'progress_timeline') and task.progress_timeline:
            last_update = datetime.fromisoformat(task.progress_timeline[-1]['timestamp'])
            stall_duration = datetime.now(timezone.utc) - last_update
            
            if stall_duration > timedelta(hours=48):
                bottlenecks.append({
                    "type": "progress_stall",
                    "severity": "high",
                    "description": f"No progress for {stall_duration.days} days",
                    "impact": "Delayed completion",
                    "suggestions": [
                        "Review and update task status",
                        "Identify specific blockers",
                        "Consider task reassignment"
                    ]
                })
        
        # Check for dependency bottlenecks
        if hasattr(task, 'dependencies') and len(task.dependencies) > 3:
            blocked_deps = []
            for dep_id in task.dependencies:
                dep_task = await self.task_repository.get(dep_id)
                if dep_task and dep_task.status in ["blocked", "cancelled"]:
                    blocked_deps.append(dep_id)
            
            if blocked_deps:
                bottlenecks.append({
                    "type": "dependency_blocked",
                    "severity": "critical",
                    "description": f"{len(blocked_deps)} dependencies are blocked",
                    "impact": "Cannot proceed until resolved",
                    "suggestions": [
                        "Escalate blocked dependencies",
                        "Find alternative approaches",
                        "Re-evaluate dependency necessity"
                    ]
                })
        
        return bottlenecks
    
    async def _find_optimization_opportunities(
        self,
        task: Task,
        context: Optional[TaskContext],
        patterns: List[WorkflowPattern]
    ) -> List[Dict[str, Any]]:
        """Find workflow optimization opportunities."""
        opportunities = []
        
        # Check for subtask opportunities
        if not hasattr(task, 'subtasks') or not task.subtasks:
            if hasattr(task, 'estimated_effort'):
                # Parse effort (assuming format like "5d" or "40h")
                effort_str = task.estimated_effort
                if effort_str and (effort_str.endswith('d') or effort_str.endswith('h')):
                    effort_value = int(effort_str[:-1])
                    effort_unit = effort_str[-1]
                    
                    if (effort_unit == 'd' and effort_value > 3) or \
                       (effort_unit == 'h' and effort_value > 24):
                        opportunities.append({
                            "type": "task_decomposition",
                            "potential_impact": "high",
                            "description": "Large task could benefit from breakdown",
                            "benefits": [
                                "Better progress tracking",
                                "Easier to parallelize work",
                                "Reduced cognitive load"
                            ],
                            "implementation": [
                                "Identify logical components",
                                "Create subtasks for each component",
                                "Define clear interfaces between subtasks"
                            ]
                        })
        
        # Check for automation opportunities
        if context and context.notes:
            automation_keywords = ["manual", "repetitive", "every time", "copy", "paste"]
            notes_text = str(context.notes).lower()
            if any(keyword in notes_text for keyword in automation_keywords):
                opportunities.append({
                    "type": "automation",
                    "potential_impact": "medium",
                    "description": "Task involves repetitive manual work",
                    "benefits": [
                        "Reduced time investment",
                        "Fewer errors",
                        "Consistent results"
                    ],
                    "implementation": [
                        "Identify repetitive steps",
                        "Create scripts or tools",
                        "Document automation process"
                    ]
                })
        
        return opportunities
    
    async def _predict_completion_time(
        self,
        task: Task,
        related_tasks: List[Task]
    ) -> Optional[timedelta]:
        """Predict task completion time based on historical data."""
        if not hasattr(task, 'created_at'):
            return None
        
        # Get similar completed tasks
        completed_similar = [
            t for t in related_tasks
            if t.status == "done" and
            hasattr(t, 'created_at') and
            hasattr(t, 'updated_at') and
            hasattr(t, 'estimated_effort') and
            t.estimated_effort == getattr(task, 'estimated_effort', None)
        ]
        
        if not completed_similar:
            # Fallback to any completed similar tasks
            completed_similar = [
                t for t in related_tasks
                if t.status == "done" and
                hasattr(t, 'created_at') and
                hasattr(t, 'updated_at')
            ]
        
        if not completed_similar:
            return None
        
        # Calculate average completion time
        completion_times = [
            t.updated_at - t.created_at
            for t in completed_similar
        ]
        
        avg_completion = sum(
            ct.total_seconds() for ct in completion_times
        ) / len(completion_times)
        
        # Adjust based on current progress
        progress = getattr(task, 'progress', 0)
        current_duration = datetime.now(timezone.utc) - task.created_at
        
        if progress > 0:
            # Estimate total time based on current progress
            estimated_total = current_duration.total_seconds() / progress
            # Weighted average between historical and progress-based estimate
            final_estimate = (avg_completion * 0.6 + estimated_total * 0.4)
        else:
            final_estimate = avg_completion
        
        remaining = final_estimate - current_duration.total_seconds()
        
        if remaining > 0:
            return timedelta(seconds=remaining)
        else:
            # Task is overdue
            return timedelta(seconds=0)
    
    def _assess_risk_factors(
        self,
        task: Task,
        context: Optional[TaskContext],
        patterns: List[WorkflowPattern]
    ) -> List[str]:
        """Assess risk factors for task completion."""
        risks = []
        
        # Check priority vs progress
        if task.priority in ["urgent", "critical"] and getattr(task, 'progress', 0) < 0.3:
            risks.append("High priority task with low progress")
        
        # Check for bottleneck patterns
        bottleneck_patterns = [
            p for p in patterns
            if p.pattern_type == "bottleneck"
        ]
        if bottleneck_patterns:
            risks.append(f"{len(bottleneck_patterns)} bottleneck patterns detected")
        
        # Check for missing context
        if not context or not context.data:
            risks.append("Limited context information available")
        
        # Check for resource constraints
        if hasattr(task, 'assignees') and not task.assignees:
            risks.append("No assignees on task")
        
        # Check for complexity indicators
        if hasattr(task, 'dependencies') and len(task.dependencies) > 5:
            risks.append("High number of dependencies")
        
        return risks
    
    def _identify_success_indicators(
        self,
        task: Task,
        context: Optional[TaskContext]
    ) -> List[str]:
        """Identify positive indicators for task success."""
        indicators = []
        
        # Check progress momentum
        if hasattr(task, 'progress_timeline') and len(task.progress_timeline) > 3:
            recent_updates = task.progress_timeline[-3:]
            if all(
                u.get('status') == ProgressStatus.IN_PROGRESS.value
                for u in recent_updates
            ):
                indicators.append("Consistent progress momentum")
        
        # Check for good documentation
        if context and context.notes:
            if len(context.notes) > 3:
                indicators.append("Well-documented context")
        
        # Check for balanced progress
        if hasattr(task, 'progress_breakdown') and task.progress_breakdown:
            values = list(task.progress_breakdown.values())
            if values and max(values) - min(values) < 0.3:
                indicators.append("Balanced progress across all areas")
        
        # Check for clear requirements
        if context and context.data.get('requirements'):
            indicators.append("Clear requirements defined")
        
        return indicators
    
    async def get_workflow_recommendations(
        self,
        task_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get actionable workflow recommendations for a task.
        
        Args:
            task_id: Task to get recommendations for
            
        Returns:
            List of prioritized recommendations
        """
        analysis = await self.analyze_task_workflow(task_id)
        
        recommendations = []
        
        # Add recommendations from patterns
        for pattern in analysis.patterns:
            for rec in pattern.recommendations:
                recommendations.append({
                    "source": pattern.pattern_name,
                    "priority": "high" if pattern.confidence > 0.8 else "medium",
                    "recommendation": rec,
                    "confidence": pattern.confidence
                })
        
        # Add recommendations from bottlenecks
        for bottleneck in analysis.bottlenecks:
            for suggestion in bottleneck.get('suggestions', []):
                recommendations.append({
                    "source": f"bottleneck_{bottleneck['type']}",
                    "priority": bottleneck['severity'],
                    "recommendation": suggestion,
                    "confidence": 0.9
                })
        
        # Add recommendations from opportunities
        for opportunity in analysis.optimization_opportunities:
            impact_priority = {
                "high": "high",
                "medium": "medium",
                "low": "low"
            }
            priority = impact_priority.get(
                opportunity['potential_impact'],
                "medium"
            )
            
            recommendations.append({
                "source": f"optimization_{opportunity['type']}",
                "priority": priority,
                "recommendation": opportunity['description'],
                "confidence": 0.85,
                "implementation_steps": opportunity.get('implementation', [])
            })
        
        # Sort by priority and confidence
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(
            key=lambda r: (
                priority_order.get(r['priority'], 2),
                -r['confidence']
            )
        )
        
        return recommendations[:10]  # Return top 10 recommendations