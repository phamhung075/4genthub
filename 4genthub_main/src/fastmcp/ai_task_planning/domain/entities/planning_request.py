"""Planning Request Domain Entity

Represents a high-level request for AI-powered task planning.
Contains all information needed to generate an intelligent task breakdown.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum

class ComplexityLevel(Enum):
    """Task complexity classification"""
    TRIVIAL = "trivial"       # Single action, <5 min
    SIMPLE = "simple"         # Single agent, <1 hour  
    MODERATE = "moderate"     # Multiple steps, <1 day
    COMPLEX = "complex"       # Multiple agents, days
    EPIC = "epic"            # Multiple features, weeks

class PlanningContext(Enum):
    """Context for the planning request"""
    NEW_FEATURE = "new_feature"
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    MAINTENANCE = "maintenance"
    RESEARCH = "research"
    INTEGRATION = "integration"

@dataclass
class RequirementItem:
    """Individual requirement within a planning request"""
    id: str
    description: str
    priority: str = "medium"  # low, medium, high, critical
    acceptance_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    estimated_complexity: Optional[ComplexityLevel] = None

@dataclass
class PlanningRequest:
    """
    Represents a request for AI task planning.
    
    This entity captures all information needed to generate an intelligent
    task breakdown and execution plan.
    """
    id: str
    title: str
    description: str
    requirements: List[RequirementItem] = field(default_factory=list)
    context: PlanningContext = PlanningContext.NEW_FEATURE
    
    # Context information
    project_id: Optional[str] = None
    git_branch_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Constraints and preferences
    deadline: Optional[datetime] = None
    available_agents: List[str] = field(default_factory=list)
    preferred_approach: Optional[str] = None
    risk_tolerance: str = "medium"  # low, medium, high
    
    # Reference information  
    related_tasks: List[str] = field(default_factory=list)
    documentation_refs: List[str] = field(default_factory=list)
    code_references: Dict[str, List[str]] = field(default_factory=dict)  # file -> line ranges
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def add_requirement(self, description: str, priority: str = "medium", 
                       acceptance_criteria: Optional[List[str]] = None) -> RequirementItem:
        """Add a new requirement to the planning request"""
        req_id = f"{self.id}_req_{len(self.requirements) + 1}"
        requirement = RequirementItem(
            id=req_id,
            description=description,
            priority=priority,
            acceptance_criteria=acceptance_criteria or []
        )
        self.requirements.append(requirement)
        return requirement
    
    def add_code_reference(self, file_path: str, line_ranges: List[str]):
        """Add code reference with specific line ranges"""
        if file_path not in self.code_references:
            self.code_references[file_path] = []
        self.code_references[file_path].extend(line_ranges)
    
    def estimate_overall_complexity(self) -> ComplexityLevel:
        """Estimate overall complexity based on requirements"""
        if not self.requirements:
            return ComplexityLevel.SIMPLE
        
        complexity_scores = {
            ComplexityLevel.TRIVIAL: 1,
            ComplexityLevel.SIMPLE: 2, 
            ComplexityLevel.MODERATE: 3,
            ComplexityLevel.COMPLEX: 4,
            ComplexityLevel.EPIC: 5
        }
        
        # Calculate based on requirements
        total_score = 0
        for req in self.requirements:
            if req.estimated_complexity:
                total_score += complexity_scores[req.estimated_complexity]
            else:
                # Basic heuristics for unestimated requirements
                if len(req.acceptance_criteria) > 5:
                    total_score += 4  # Complex
                elif len(req.acceptance_criteria) > 2:
                    total_score += 3  # Moderate  
                else:
                    total_score += 2  # Simple
        
        avg_score = total_score / len(self.requirements)
        
        if avg_score >= 4.5:
            return ComplexityLevel.EPIC
        elif avg_score >= 3.5:
            return ComplexityLevel.COMPLEX
        elif avg_score >= 2.5:
            return ComplexityLevel.MODERATE
        elif avg_score >= 1.5:
            return ComplexityLevel.SIMPLE
        else:
            return ComplexityLevel.TRIVIAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'requirements': [
                {
                    'id': req.id,
                    'description': req.description,
                    'priority': req.priority,
                    'acceptance_criteria': req.acceptance_criteria,
                    'constraints': req.constraints,
                    'related_files': req.related_files,
                    'estimated_complexity': req.estimated_complexity.value if req.estimated_complexity else None
                } for req in self.requirements
            ],
            'context': self.context.value,
            'project_id': self.project_id,
            'git_branch_id': self.git_branch_id,
            'user_id': self.user_id,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'available_agents': self.available_agents,
            'preferred_approach': self.preferred_approach,
            'risk_tolerance': self.risk_tolerance,
            'related_tasks': self.related_tasks,
            'documentation_refs': self.documentation_refs,
            'code_references': self.code_references,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanningRequest':
        """Create from dictionary"""
        requirements = [
            RequirementItem(
                id=req['id'],
                description=req['description'],
                priority=req.get('priority', 'medium'),
                acceptance_criteria=req.get('acceptance_criteria', []),
                constraints=req.get('constraints', []),
                related_files=req.get('related_files', []),
                estimated_complexity=ComplexityLevel(req['estimated_complexity']) if req.get('estimated_complexity') else None
            ) for req in data.get('requirements', [])
        ]
        
        return cls(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            requirements=requirements,
            context=PlanningContext(data.get('context', 'new_feature')),
            project_id=data.get('project_id'),
            git_branch_id=data.get('git_branch_id'),
            user_id=data.get('user_id'),
            deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
            available_agents=data.get('available_agents', []),
            preferred_approach=data.get('preferred_approach'),
            risk_tolerance=data.get('risk_tolerance', 'medium'),
            related_tasks=data.get('related_tasks', []),
            documentation_refs=data.get('documentation_refs', []),
            code_references=data.get('code_references', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now(timezone.utc).isoformat())),
            created_by=data.get('created_by'),
            tags=data.get('tags', [])
        )