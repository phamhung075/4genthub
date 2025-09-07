"""Agent Value Objects for Multi-Agent Coordination"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class AgentRole(Enum):
    """Specialized agent roles for coordination"""
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    TESTER = "tester"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    ANALYST = "analyst"
    DESIGNER = "designer"
    DEVOPS = "devops"
    SECURITY = "security"
    DOCUMENTER = "documenter"

class AgentExpertise(Enum):
    """Areas of expertise for skill matching"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    CLOUD = "cloud"
    MOBILE = "mobile"
    AI_ML = "ai_ml"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    PROJECT_MANAGEMENT = "project_management"

@dataclass(frozen=True)
class AgentCapabilities:
    """Value object representing agent capabilities"""
    primary_role: AgentRole
    secondary_roles: Set[AgentRole] = field(default_factory=set)
    expertise_areas: Set[AgentExpertise] = field(default_factory=set)
    skill_levels: Dict[str, float] = field(default_factory=dict)  # skill -> proficiency (0-1)
    max_task_complexity: int = 5  # 1-10 scale
    preferred_task_types: Set[str] = field(default_factory=set)
    
    def can_handle_role(self, role: AgentRole) -> bool:
        """Check if agent can handle a specific role"""
        return role == self.primary_role or role in self.secondary_roles
    
    def expertise_match_score(self, required_expertise: Set[AgentExpertise]) -> float:
        """Calculate expertise match score (0-1)"""
        if not required_expertise:
            return 1.0
        
        matching = self.expertise_areas.intersection(required_expertise)
        return len(matching) / len(required_expertise)
    
    def skill_match_score(self, required_skills: Dict[str, float]) -> float:
        """Calculate skill match score based on proficiency levels"""
        if not required_skills:
            return 1.0
        
        total_score = 0.0
        for skill, required_level in required_skills.items():
            agent_level = self.skill_levels.get(skill, 0.0)
            if agent_level >= required_level:
                total_score += 1.0
            else:
                total_score += agent_level / required_level
        
        return total_score / len(required_skills)

@dataclass(frozen=True)
class AgentProfile:
    """Value object representing agent profile and preferences"""
    agent_id: str
    display_name: str
    capabilities: AgentCapabilities
    availability_score: float = 1.0  # 0-1, considers workload and status
    performance_score: float = 1.0  # 0-1, based on historical performance
    collaboration_style: str = "independent"  # independent, collaborative, supervisory
    communication_preferences: Set[str] = field(default_factory=set)  # sync, async, broadcast
    time_zone: str = "UTC"
    working_hours: Optional[Dict[str, str]] = None
    
    def overall_suitability_score(self, task_requirements: Dict) -> float:
        """Calculate overall suitability for a task"""
        # Extract requirements
        required_role = task_requirements.get("role")
        required_expertise = set(task_requirements.get("expertise", []))
        required_skills = task_requirements.get("skills", {})
        
        # Calculate component scores
        role_score = 1.0 if not required_role or self.capabilities.can_handle_role(required_role) else 0.0
        expertise_score = self.capabilities.expertise_match_score(required_expertise)
        skill_score = self.capabilities.skill_match_score(required_skills)
        
        # Weighted combination
        base_score = (role_score * 0.4) + (expertise_score * 0.3) + (skill_score * 0.3)
        
        # Apply modifiers
        final_score = base_score * self.availability_score * self.performance_score
        
        return min(1.0, max(0.0, final_score))

@dataclass(frozen=True)
class AgentStatus:
    """Value object representing current agent status"""
    agent_id: str
    is_available: bool
    current_workload: int
    max_workload: int
    active_tasks: List[str]
    last_activity: datetime
    status_message: Optional[str] = None
    estimated_availability: Optional[datetime] = None
    
    @property
    def workload_percentage(self) -> float:
        """Get workload as percentage"""
        if self.max_workload == 0:
            return 0.0
        return (self.current_workload / self.max_workload) * 100.0
    
    @property
    def can_accept_work(self) -> bool:
        """Check if agent can accept more work"""
        return self.is_available and self.current_workload < self.max_workload
    
    def capacity_score(self) -> float:
        """Calculate capacity score (0-1)"""
        if not self.is_available:
            return 0.0
        
        if self.max_workload == 0:
            return 0.0
        
        remaining_capacity = (self.max_workload - self.current_workload) / self.max_workload
        return max(0.0, min(1.0, remaining_capacity))

@dataclass
class AgentPerformanceMetrics:
    """Value object for tracking agent performance"""
    agent_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_completion_time: float = 0.0  # in hours
    quality_score: float = 1.0  # 0-1
    collaboration_score: float = 1.0  # 0-1
    reliability_score: float = 1.0  # 0-1
    feedback_scores: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate task success rate"""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total
    
    @property
    def overall_performance_score(self) -> float:
        """Calculate overall performance score"""
        return (
            self.success_rate * 0.3 +
            self.quality_score * 0.3 +
            self.collaboration_score * 0.2 +
            self.reliability_score * 0.2
        )
    
    def update_with_task_result(self, success: bool, completion_time: float, 
                               quality_rating: Optional[float] = None) -> None:
        """Update metrics with task result"""
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        # Update average completion time
        total_tasks = self.tasks_completed + self.tasks_failed
        self.average_completion_time = (
            (self.average_completion_time * (total_tasks - 1) + completion_time) / total_tasks
        )
        
        # Update quality score if provided
        if quality_rating is not None:
            self.feedback_scores.append(quality_rating)
            # Use recent feedback with more weight
            recent_scores = self.feedback_scores[-10:]  # Last 10 scores
            self.quality_score = sum(recent_scores) / len(recent_scores)