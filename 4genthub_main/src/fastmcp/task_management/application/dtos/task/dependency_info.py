"""DTOs for enhanced task dependency information"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class DependencyInfo:
    """Information about a single task dependency"""
    task_id: str
    title: str
    status: str
    priority: str
    completion_percentage: float = 0.0
    is_blocking: bool = False
    is_blocked: bool = False
    estimated_effort: Optional[str] = None
    assignees: List[str] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.assignees is None:
            self.assignees = []


@dataclass
class DependencyChain:
    """Represents a chain of task dependencies"""
    chain_id: str
    tasks: List[DependencyInfo]
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    chain_status: str  # 'not_started', 'in_progress', 'blocked', 'completed'
    estimated_completion: Optional[str] = None
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage for the chain"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def is_blocked(self) -> bool:
        """Check if the chain is blocked"""
        return self.blocked_tasks > 0
    
    @property
    def next_task(self) -> Optional[DependencyInfo]:
        """Get the next task that can be worked on"""
        for task in self.tasks:
            if task.status == 'todo' and not task.is_blocked:
                return task
        return None


@dataclass
class DependencyRelationships:
    """Complete dependency relationship information for a task"""
    task_id: str
    
    # Direct dependencies
    depends_on: List[DependencyInfo]
    blocks: List[DependencyInfo]
    
    # Dependency chains
    upstream_chains: List[DependencyChain]
    downstream_chains: List[DependencyChain]
    
    # Summary information
    total_dependencies: int
    completed_dependencies: int
    blocked_dependencies: int
    
    # Status indicators
    can_start: bool
    is_blocked: bool
    is_blocking_others: bool
    
    # Workflow information
    dependency_summary: str
    next_actions: List[str]
    blocking_reasons: List[str]
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.blocks is None:
            self.blocks = []
        if self.upstream_chains is None:
            self.upstream_chains = []
        if self.downstream_chains is None:
            self.downstream_chains = []
        if self.next_actions is None:
            self.next_actions = []
        if self.blocking_reasons is None:
            self.blocking_reasons = []
    
    @property
    def dependency_completion_percentage(self) -> float:
        """Calculate completion percentage of dependencies"""
        if self.total_dependencies == 0:
            return 100.0
        return (self.completed_dependencies / self.total_dependencies) * 100
    
    def get_blocking_chain_info(self) -> Dict[str, Any]:
        """Get information about what's blocking this task"""
        blocking_info = {
            'is_blocked': self.is_blocked,
            'blocking_tasks': [],
            'blocking_chains': [],
            'resolution_suggestions': []
        }
        
        # Find blocking tasks
        for dep in self.depends_on:
            if dep.status not in ['done', 'cancelled']:
                blocking_info['blocking_tasks'].append({
                    'task_id': dep.task_id,
                    'title': dep.title,
                    'status': dep.status,
                    'priority': dep.priority
                })
        
        # Find blocking chains
        for chain in self.upstream_chains:
            if chain.is_blocked or chain.chain_status != 'completed':
                blocking_info['blocking_chains'].append({
                    'chain_id': chain.chain_id,
                    'status': chain.chain_status,
                    'completion_percentage': chain.completion_percentage,
                    'next_task': chain.next_task.title if chain.next_task else None
                })
        
        # Generate resolution suggestions
        if blocking_info['blocking_tasks']:
            blocking_info['resolution_suggestions'].append(
                f"Complete {len(blocking_info['blocking_tasks'])} blocking task(s)"
            )
        
        if blocking_info['blocking_chains']:
            blocking_info['resolution_suggestions'].append(
                f"Resolve {len(blocking_info['blocking_chains'])} blocked chain(s)"
            )
        
        return blocking_info
    
    def get_workflow_guidance(self) -> Dict[str, Any]:
        """Get workflow guidance based on dependency status"""
        guidance = {
            'can_start_immediately': self.can_start,
            'recommended_actions': [],
            'priority_suggestions': [],
            'estimated_wait_time': None
        }
        
        if self.can_start:
            guidance['recommended_actions'].append("Task is ready to start - no blocking dependencies")
        else:
            guidance['recommended_actions'].extend([
                f"Wait for {len(self.depends_on)} dependencies to complete",
                "Consider working on dependency tasks first",
                "Check if any dependencies can be parallelized"
            ])
        
        if self.is_blocking_others:
            guidance['priority_suggestions'].append(
                f"High priority - blocking {len(self.blocks)} other task(s)"
            )
        
        return guidance