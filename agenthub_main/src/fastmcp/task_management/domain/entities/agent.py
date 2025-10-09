"""Agent Domain Entity"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .base.base_timestamp_entity import BaseTimestampEntity
from ..value_objects.agent_id import AgentId


class AgentStatus(Enum):
    """Agent status enumeration"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    PAUSED = "paused"


class AgentCapability(Enum):
    """Agent capability enumeration"""
    FRONTEND_DEVELOPMENT = "frontend_development"
    BACKEND_DEVELOPMENT = "backend_development"
    DEVOPS = "devops"
    TESTING = "testing"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    PROJECT_MANAGEMENT = "project_management"
    DATA_ANALYSIS = "data_analysis"


@dataclass
class Agent(BaseTimestampEntity):
    """Agent entity representing an AI agent that can work on tasks

    Rich Domain Model: Contains business logic for agent management, capability matching, and workload analysis.
    Controlled by FEATURE_RICH_DOMAIN_MODEL flag for zero-downtime migration (Strangler Fig Pattern).
    """

    # Required fields must have defaults since parent has defaults
    id: AgentId | None = None
    name: str = ""
    description: str = ""

    # Feature flag for Rich Domain Model (Strangler Fig Pattern)
    FEATURE_RICH_DOMAIN_MODEL: bool = False

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity."""
        return str(self.id) if self.id else "unknown"

    def _validate_entity(self) -> None:
        """Validate entity business rules."""
        if not self.id:
            raise ValueError("Agent must have an ID")
        if not self.name:
            raise ValueError("Agent must have a name")

    # Agent capabilities and preferences
    capabilities: Set[AgentCapability] = field(default_factory=set)
    specializations: List[str] = field(default_factory=list)  # More specific specializations
    preferred_languages: List[str] = field(default_factory=list)  # Programming languages
    preferred_frameworks: List[str] = field(default_factory=list)  # Frameworks/tools
    
    # Agent status and availability
    status: AgentStatus = AgentStatus.AVAILABLE
    max_concurrent_tasks: int = 1
    current_workload: int = 0
    
    # Work preferences and constraints
    work_hours: Optional[Dict[str, str]] = None  # {"start": "09:00", "end": "17:00"}
    timezone: str = "UTC"
    priority_preference: str = "high"  # Prefers high, medium, or low priority tasks
    
    # Performance metrics
    completed_tasks: int = 0
    average_task_duration: Optional[float] = None  # Hours
    success_rate: float = 100.0  # Percentage
    
    # Current assignments
    assigned_projects: Set[str] = field(default_factory=set)
    assigned_trees: Set[str] = field(default_factory=set)
    active_tasks: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize entity - timestamps handled by BaseTimestampEntity"""
        super().__post_init__()

    def _validate_entity(self) -> None:
        """Ensure agent core fields are present."""
        if not self.id:
            raise ValueError("Agent id cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("Agent name cannot be empty")
    
    def add_capability(self, capability: AgentCapability) -> None:
        """Add a capability to the agent"""
        self.capabilities.add(capability)
        self.touch("capability_added")
    
    def remove_capability(self, capability: AgentCapability) -> None:
        """Remove a capability from the agent"""
        self.capabilities.discard(capability)
        self.touch("capability_removed")
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities
    
    def can_handle_task(self, task_requirements: Dict) -> bool:
        """Check if agent can handle a task based on requirements"""
        # Check capabilities
        required_capabilities = task_requirements.get("capabilities", [])
        for req_cap in required_capabilities:
            if isinstance(req_cap, str):
                try:
                    req_cap = AgentCapability(req_cap)
                except ValueError:
                    continue  # Skip unknown capabilities
            
            if req_cap not in self.capabilities:
                return False
        
        # Check programming languages
        required_languages = task_requirements.get("languages", [])
        if required_languages:
            if not any(lang in self.preferred_languages for lang in required_languages):
                return False
        
        # Check frameworks
        required_frameworks = task_requirements.get("frameworks", [])
        if required_frameworks:
            if not any(fw in self.preferred_frameworks for fw in required_frameworks):
                return False
        
        return True
    
    def is_available(self) -> bool:
        """Check if agent is available for new work"""
        return (self.status == AgentStatus.AVAILABLE and 
                self.current_workload < self.max_concurrent_tasks)
    
    def assign_to_project(self, project_id: str) -> None:
        """Assign agent to a project"""
        self.assigned_projects.add(project_id)
        self.touch("project_assignment_added")
    
    def assign_to_tree(self, git_branch_name: str) -> None:
        """Assign agent to a task tree"""
        self.assigned_trees.add(git_branch_name)
        self.touch("tree_assignment_added")

    def unassign_from_tree(self, git_branch_name: str) -> None:
        """Unassign agent from a task tree"""
        if git_branch_name in self.assigned_trees:
            self.assigned_trees.remove(git_branch_name)
            self.touch("tree_assignment_removed")

    def unassign_from_all_trees(self) -> None:
        """Unassign agent from all task trees"""
        if self.assigned_trees:
            self.assigned_trees.clear()
            self.touch("all_tree_assignments_removed")

    def start_task(self, task_id: str) -> None:
        """Start working on a task"""
        if not self.is_available():
            raise ValueError(f"Agent {self.id} is not available for new tasks")
        
        self.active_tasks.add(task_id)
        self.current_workload += 1
        
        if self.current_workload >= self.max_concurrent_tasks:
            self.status = AgentStatus.BUSY

        self.touch("task_started")
    
    def complete_task(self, task_id: str, success: bool = True) -> None:
        """Complete a task and update metrics"""
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not assigned to agent {self.id}")
        
        self.active_tasks.remove(task_id)
        self.current_workload = max(0, self.current_workload - 1)
        self.completed_tasks += 1
        
        # Update success rate
        if success:
            # Weighted average favoring recent performance
            self.success_rate = (self.success_rate * 0.9) + (100.0 * 0.1)
        else:
            self.success_rate = (self.success_rate * 0.9) + (0.0 * 0.1)
        
        # Update status if no longer busy
        if self.current_workload < self.max_concurrent_tasks and self.status == AgentStatus.BUSY:
            self.status = AgentStatus.AVAILABLE

        self.touch("task_completed")
    
    def pause_work(self) -> None:
        """Pause agent work"""
        self.status = AgentStatus.PAUSED
        self.touch("agent_paused")
    
    def resume_work(self) -> None:
        """Resume agent work"""
        if self.current_workload >= self.max_concurrent_tasks:
            self.status = AgentStatus.BUSY
        else:
            self.status = AgentStatus.AVAILABLE
        self.touch("agent_resumed")
    
    def go_offline(self) -> None:
        """Set agent offline"""
        self.status = AgentStatus.OFFLINE
        self.touch("agent_offline")
    
    def go_online(self) -> None:
        """Set agent online and available"""
        self.status = AgentStatus.AVAILABLE
        self.touch("agent_online")
    
    def get_workload_percentage(self) -> float:
        """Get current workload as percentage of capacity"""
        if self.max_concurrent_tasks == 0:
            return 100.0
        return (self.current_workload / self.max_concurrent_tasks) * 100.0
    
    def get_agent_profile(self) -> Dict:
        """Get comprehensive agent profile"""
        return {
            "id": str(self.id) if self.id else "",
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "specializations": self.specializations,
            "preferred_languages": self.preferred_languages,
            "preferred_frameworks": self.preferred_frameworks,
            "workload": {
                "current": self.current_workload,
                "max": self.max_concurrent_tasks,
                "percentage": self.get_workload_percentage(),
                "available": self.is_available()
            },
            "performance": {
                "completed_tasks": self.completed_tasks,
                "success_rate": self.success_rate,
                "average_duration": self.average_task_duration
            },
            "assignments": {
                "projects": list(self.assigned_projects),
                "trees": list(self.assigned_trees),
                "active_tasks": list(self.active_tasks)
            },
            "preferences": {
                "work_hours": self.work_hours,
                "timezone": self.timezone,
                "priority_preference": self.priority_preference
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def calculate_task_suitability_score(self, task_requirements: Dict) -> float:
        """Calculate how suitable this agent is for a specific task (0-100)"""
        if not self.can_handle_task(task_requirements):
            return 0.0
        
        score = 50.0  # Base score for meeting requirements
        
        # Bonus for availability
        if self.is_available():
            score += 20.0
        
        # Bonus for low workload
        workload_bonus = (1.0 - (self.current_workload / self.max_concurrent_tasks)) * 10.0
        score += workload_bonus
        
        # Bonus for high success rate
        success_bonus = (self.success_rate / 100.0) * 10.0
        score += success_bonus
        
        # Bonus for matching priority preference
        task_priority = task_requirements.get("priority", "medium")
        if task_priority == self.priority_preference:
            score += 10.0
        
        return min(100.0, score)
    
    # Rich Domain Model Business Methods (Strangler Fig Pattern)
    # These methods are controlled by FEATURE_RICH_DOMAIN_MODEL flag

    def validate_capability_match(self, task_requirements: List[str]) -> bool:
        """
        Validate that agent's capabilities match task requirements.

        Args:
            task_requirements: List of required capability strings

        Returns:
            bool: True if agent has all required capabilities, False otherwise

        Business Rules (when FEATURE_RICH_DOMAIN_MODEL=True):
        - All required capabilities must be present in agent's capabilities
        - Case-insensitive matching
        - Handles both string and enum representations
        - Empty requirements list returns True (no requirements)

        Legacy behavior (when FEATURE_RICH_DOMAIN_MODEL=False):
        - Uses existing can_handle_task() method with dict format
        """
        if not self.FEATURE_RICH_DOMAIN_MODEL:
            # Legacy behavior: use existing method
            task_dict = {"capabilities": task_requirements}
            return self.can_handle_task(task_dict)

        # Rich Domain Model: enhanced capability matching

        # Empty requirements = no restrictions
        if not task_requirements:
            return True

        # Convert agent capabilities to lowercase strings for comparison
        agent_caps_strings = {cap.value.lower() for cap in self.capabilities}

        # Check each requirement
        for req in task_requirements:
            req_lower = req.lower().replace(" ", "_")

            # Try to match as capability enum value
            matched = False
            for cap in self.capabilities:
                if cap.value.lower() == req_lower:
                    matched = True
                    break

            # Also check against specializations
            if not matched:
                for spec in self.specializations:
                    if spec.lower() == req_lower:
                        matched = True
                        break

            # If no match found, requirement not met
            if not matched:
                return False

        return True

    def calculate_workload_score(self) -> float:
        """
        Calculate current workload as a score (0.0 to 1.0).

        Returns:
            float: Workload score where:
                - 0.0 = completely idle (no tasks)
                - 0.5 = moderate workload (half capacity)
                - 1.0 = fully loaded (at max capacity)
                - >1.0 = overloaded (exceeds capacity)

        Business Rules (when FEATURE_RICH_DOMAIN_MODEL=True):
        - Score = current_workload / max_concurrent_tasks
        - Accounts for agent status (offline = 1.0, paused = current score)
        - Handles zero max_concurrent_tasks gracefully
        - Returns exact ratio for precise load balancing

        Legacy behavior (when FEATURE_RICH_DOMAIN_MODEL=False):
        - Uses existing get_workload_percentage() / 100
        """
        if not self.FEATURE_RICH_DOMAIN_MODEL:
            # Legacy behavior: use existing percentage method
            return self.get_workload_percentage() / 100.0

        # Rich Domain Model: comprehensive workload calculation

        # Special cases based on status
        if self.status == AgentStatus.OFFLINE:
            return 1.0  # Offline = fully unavailable

        if self.status == AgentStatus.PAUSED:
            # Paused agents still have workload, just not accepting new work
            if self.max_concurrent_tasks == 0:
                return 1.0
            return self.current_workload / self.max_concurrent_tasks

        # Normal calculation
        if self.max_concurrent_tasks == 0:
            # Zero capacity = always fully loaded
            return 1.0

        workload_score = self.current_workload / self.max_concurrent_tasks

        return workload_score

    def check_availability(self) -> Dict[str, Any]:
        """
        Check if agent is available for new work with detailed status.

        Returns:
            Dict containing:
                - available: bool - Can accept new work
                - status: str - Current agent status
                - workload_score: float - Current workload (0.0-1.0+)
                - current_tasks: int - Number of active tasks
                - capacity: int - Maximum concurrent tasks
                - blocking_reasons: List[str] - Why agent is unavailable (if applicable)
                - estimated_capacity: int - How many more tasks can be accepted

        Business Rules (when FEATURE_RICH_DOMAIN_MODEL=True):
        - Available if: status=AVAILABLE AND workload < max capacity
        - Provides detailed blocking reasons when unavailable
        - Calculates remaining capacity
        - Includes workload score for prioritization

        Legacy behavior (when FEATURE_RICH_DOMAIN_MODEL=False):
        - Uses existing is_available() method with basic info
        """
        if not self.FEATURE_RICH_DOMAIN_MODEL:
            # Legacy behavior: basic availability check
            return {
                "available": self.is_available(),
                "status": self.status.value,
                "current_workload": self.current_workload,
                "max_concurrent_tasks": self.max_concurrent_tasks
            }

        # Rich Domain Model: comprehensive availability analysis

        blocking_reasons = []
        is_available = True

        # Check status
        if self.status == AgentStatus.OFFLINE:
            is_available = False
            blocking_reasons.append("Agent is offline")
        elif self.status == AgentStatus.PAUSED:
            is_available = False
            blocking_reasons.append("Agent is paused")
        elif self.status == AgentStatus.BUSY:
            # Busy doesn't necessarily mean unavailable if under capacity
            if self.current_workload >= self.max_concurrent_tasks:
                is_available = False
                blocking_reasons.append("Agent is at maximum capacity")

        # Check workload even if status is AVAILABLE
        if self.status == AgentStatus.AVAILABLE:
            if self.current_workload >= self.max_concurrent_tasks:
                is_available = False
                blocking_reasons.append("Agent workload at maximum capacity")

        # Calculate workload score
        workload_score = self.calculate_workload_score()

        # Calculate remaining capacity
        if is_available:
            estimated_capacity = max(0, self.max_concurrent_tasks - self.current_workload)
        else:
            estimated_capacity = 0

        return {
            "available": is_available,
            "status": self.status.value,
            "workload_score": round(workload_score, 3),
            "current_tasks": self.current_workload,
            "capacity": self.max_concurrent_tasks,
            "blocking_reasons": blocking_reasons,
            "estimated_capacity": estimated_capacity,
            "active_task_ids": list(self.active_tasks),
            "performance_metrics": {
                "completed_tasks": self.completed_tasks,
                "success_rate": round(self.success_rate, 2),
                "average_duration_hours": self.average_task_duration
            }
        }

    @classmethod
    def create_agent(
        cls,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[AgentCapability] = None,
        specializations: List[str] = None,
        preferred_languages: List[str] = None
    ) -> 'Agent':
        """Factory method to create a new agent"""
        # Convert string id to AgentId value object
        agent_id_vo = AgentId(agent_id) if isinstance(agent_id, str) else agent_id

        agent = cls(
            id=agent_id_vo,
            name=name,
            description=description,
            capabilities=set(capabilities or []),
            specializations=specializations or [],
            preferred_languages=preferred_languages or []
        )
        return agent 
