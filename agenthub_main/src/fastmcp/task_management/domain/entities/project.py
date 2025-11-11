"""Project Domain Entity"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..value_objects.git_branch_id import GitBranchId
from ..value_objects.project_id import ProjectId
from .agent import Agent
from .base.base_timestamp_entity import BaseTimestampEntity
from .git_branch import GitBranch

if TYPE_CHECKING:
    from ..repositories.git_branch_repository import GitBranchRepository
    from .task import Task
    from .work_session import WorkSession


@dataclass
class Project(BaseTimestampEntity):
    """Project aggregate root for multi-agent task orchestration

    Rich Domain Model: Contains business logic for project management, validation, and analysis.
    """

    id: ProjectId | None = None
    name: str = ""
    description: str = ""

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity."""
        return str(self.id) if self.id else "unknown"

    @classmethod
    def create(cls, name: str, description: str = "") -> Project:
        """Create a new project with auto-generated UUID"""
        project_id = ProjectId.generate_new()

        return cls(id=project_id, name=name, description=description)

    def __hash__(self):
        """Make Project hashable based on its id"""
        if not self.id:
            return hash(None)
        # Handle both value object and string types
        return hash(self.id.value if hasattr(self.id, "value") else self.id)

    # Multi-tree structure
    git_branchs: dict[str, GitBranch] = field(default_factory=dict)

    # Agent management
    registered_agents: dict[str, Agent] = field(default_factory=dict)
    agent_assignments: dict[str, str] = field(
        default_factory=dict
    )  # git_branch_id -> agent_id

    # Cross-tree dependencies
    cross_tree_dependencies: dict[str, set[str]] = field(
        default_factory=dict
    )  # task_id -> dependent_task_ids

    # Work coordination
    active_work_sessions: dict[str, WorkSession] = field(default_factory=dict)
    resource_locks: dict[str, str] = field(default_factory=dict)  # resource -> agent_id

    def _validate_entity(self) -> None:
        """Ensure project invariants hold."""
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty")

    async def create_git_branch_async(
        self,
        git_branch_repository: GitBranchRepository,
        branch_name: str,
        description: str = "",
    ) -> GitBranch:
        """Create a new git branch/task tree within the project using repository"""
        # Check if branch already exists
        project_id_str = str(self.id) if self.id else ""
        existing_branch = await git_branch_repository.find_by_name(
            project_id_str, branch_name
        )
        if existing_branch:
            raise ValueError(
                f"Git branch {branch_name} already exists in project {self.id}"
            )

        # Create new branch using repository
        git_branch = await git_branch_repository.create_branch(
            project_id=project_id_str, branch_name=branch_name, description=description
        )

        # Update local cache
        git_branch_id_str = (
            str(
                git_branch.id.value
                if hasattr(git_branch.id, "value")
                else git_branch.id
            )
            if git_branch.id
            else ""
        )
        self.git_branchs[git_branch_id_str] = git_branch
        self.touch("git_branch_added")
        return git_branch

    def create_git_branch(
        self, git_branch_name: str, name: str, description: str = ""
    ) -> GitBranch:
        """Create a new task tree/branch within the project (legacy method)"""
        # Check if branch name already exists in any git branch
        for git_branch in self.git_branchs.values():
            if git_branch.git_branch_name == git_branch_name:
                raise ValueError(f"Git branch {git_branch_name} already exists")

        # Generate unique ID for the git branch following clean relationship chain
        git_branch_id = GitBranchId.generate_new()

        git_branch = GitBranch(
            id=git_branch_id,
            name=name,
            description=description,
            project_id=str(self.id) if self.id else "",
            git_branch_name=git_branch_name,
        )

        git_branch_id_str = str(
            git_branch_id.value if hasattr(git_branch_id, "value") else git_branch_id
        )
        self.git_branchs[git_branch_id_str] = git_branch
        self.touch("git_branch_created")
        return git_branch

    def add_git_branch(self, git_branch: GitBranch) -> None:
        """Add a git branch to the project"""
        git_branch_id_str = (
            str(
                git_branch.id.value
                if hasattr(git_branch.id, "value")
                else git_branch.id
            )
            if git_branch.id
            else ""
        )
        self.git_branchs[git_branch_id_str] = git_branch
        self.touch("git_branch_added")

    def get_git_branch(self, branch_name: str) -> GitBranch | None:
        """Get a git branch by name"""
        for git_branch in self.git_branchs.values():
            if git_branch.name == branch_name:
                return git_branch
        return None

    def register_agent(self, agent: Agent) -> None:
        """Register an AI agent to work on this project"""
        # Handle both AgentId value object and string ID for backwards compatibility
        if agent.id:
            agent_id_str = str(
                agent.id.value if hasattr(agent.id, "value") else agent.id
            )
        else:
            agent_id_str = ""
        self.registered_agents[agent_id_str] = agent
        self.touch("agent_registered")

    def assign_agent_to_tree(self, agent_id: str, git_branch_id: str) -> None:
        """Assign an agent to work on a specific task tree"""
        # Convert git_branch_id to string if it's a GitBranchId value object
        git_branch_id_str = str(
            git_branch_id.value if hasattr(git_branch_id, "value") else git_branch_id
        )

        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not registered")
        if git_branch_id_str not in self.git_branchs:
            raise ValueError(f"Task tree {git_branch_id_str} not found")

        # Check if tree is already assigned
        if git_branch_id_str in self.agent_assignments:
            current_agent = self.agent_assignments[git_branch_id_str]
            if current_agent != agent_id:
                raise ValueError(
                    f"Task tree {git_branch_id_str} already assigned to agent {current_agent}"
                )

        self.agent_assignments[git_branch_id_str] = agent_id
        self.touch("agent_assigned_to_tree")

    def add_cross_tree_dependency(
        self, dependent_task_id: str, prerequisite_task_id: str
    ) -> None:
        """Add a dependency between tasks in different trees"""
        # Normalize task IDs for consistent storage
        dependent_task_id = self._normalize_task_id(dependent_task_id)
        prerequisite_task_id = self._normalize_task_id(prerequisite_task_id)

        # Validate that tasks exist and are in different trees
        dependent_tree = self._find_git_branch(dependent_task_id)
        prerequisite_tree = self._find_git_branch(prerequisite_task_id)

        if not dependent_tree or not prerequisite_tree:
            raise ValueError("One or both tasks not found in project")

        # Compare branch IDs as strings
        dependent_tree_id = (
            str(
                dependent_tree.id.value
                if hasattr(dependent_tree.id, "value")
                else dependent_tree.id
            )
            if dependent_tree.id
            else ""
        )
        prerequisite_tree_id = (
            str(
                prerequisite_tree.id.value
                if hasattr(prerequisite_tree.id, "value")
                else prerequisite_tree.id
            )
            if prerequisite_tree.id
            else ""
        )
        if dependent_tree_id == prerequisite_tree_id:
            raise ValueError(
                "Use regular task dependencies for tasks within the same tree"
            )

        # Add cross-tree dependency
        if dependent_task_id not in self.cross_tree_dependencies:
            self.cross_tree_dependencies[dependent_task_id] = set()

        self.cross_tree_dependencies[dependent_task_id].add(prerequisite_task_id)
        self.touch("cross_tree_dependency_added")

    def get_available_work_for_agent(self, agent_id: str) -> list[Task]:
        """Get available tasks for a specific agent based on their assignments and dependencies"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not registered")

        available_tasks = []

        # Find trees assigned to this agent
        assigned_trees = [
            git_branch_id
            for git_branch_id, assigned_agent in self.agent_assignments.items()
            if assigned_agent == agent_id
        ]

        for git_branch_id in assigned_trees:
            branch = self.git_branchs[git_branch_id]
            branch_tasks = branch.get_available_tasks()

            # Filter out tasks blocked by cross-tree dependencies
            for task in branch_tasks:
                task_id_str = str(
                    task.id.value if hasattr(task.id, "value") else task.id
                )
                if self._is_task_ready_for_work(task_id_str):
                    available_tasks.append(task)

        return available_tasks

    def start_work_session(
        self, agent_id: str, task_id: str, max_duration_hours: float | None = None
    ) -> WorkSession:
        """Start a work session for an agent on a specific task"""
        from .work_session import WorkSession

        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not registered")

        # Check if agent is assigned to the tree containing this task
        git_branch = self._find_git_branch(task_id)
        if not git_branch:
            raise ValueError(f"Task {task_id} not found")

        git_branch_id_str = (
            str(
                git_branch.id.value
                if hasattr(git_branch.id, "value")
                else git_branch.id
            )
            if git_branch.id
            else ""
        )
        if self.agent_assignments.get(git_branch_id_str) != agent_id:
            raise ValueError(
                f"Agent {agent_id} not assigned to tree {git_branch_id_str}"
            )

        # Create work session using factory method
        session = WorkSession.create_session(
            agent_id=agent_id,
            task_id=task_id,
            git_branch_name=git_branch_id_str,
            max_duration_hours=max_duration_hours,
        )

        self.active_work_sessions[session.id] = session
        self.touch("work_session_started")
        return session

    def _find_git_branch(self, task_id: str) -> GitBranch | None:
        """Find which git branch contains a specific task"""
        # Normalize task_id to canonical format for consistent comparison
        normalized_task_id = self._normalize_task_id(task_id)
        for branch in self.git_branchs.values():
            if branch.has_task(normalized_task_id):
                return branch
        return None

    def _normalize_task_id(self, task_id: str) -> str:
        """Normalize task_id to canonical UUID format"""
        if len(task_id) == 32 and "-" not in task_id:
            # Convert hex format to canonical
            return f"{task_id[:8]}-{task_id[8:12]}-{task_id[12:16]}-{task_id[16:20]}-{task_id[20:]}"
        return task_id

    def _is_task_ready_for_work(self, task_id: str) -> bool:
        """Check if a task is ready for work (all cross-tree dependencies satisfied)"""
        normalized_task_id = self._normalize_task_id(task_id)
        if normalized_task_id not in self.cross_tree_dependencies:
            return True  # No cross-tree dependencies

        # Check if all prerequisite tasks are completed
        for prerequisite_id in self.cross_tree_dependencies[normalized_task_id]:
            prerequisite_tree = self._find_git_branch(prerequisite_id)
            if not prerequisite_tree:
                return False  # Prerequisite task not found

            prerequisite_task = prerequisite_tree.get_task(prerequisite_id)
            if not prerequisite_task:
                return False  # Prerequisite task not found

            # Handle both Task entity and dict representation
            if hasattr(prerequisite_task, "status"):
                if not prerequisite_task.status.is_done():
                    return False  # Prerequisite not completed
            elif isinstance(prerequisite_task, dict):
                if prerequisite_task.get("status") != "done":
                    return False  # Prerequisite not completed
            else:
                return False  # Unknown prerequisite task format

        return True

    def get_orchestration_status(self) -> dict:
        """Get comprehensive status for orchestration dashboard"""
        return {
            "project_id": str(self.id) if self.id else "",
            "project_name": self.name,
            "total_branches": len(self.git_branchs),
            "registered_agents": len(self.registered_agents),
            "active_assignments": len(self.agent_assignments),
            "active_sessions": len(self.active_work_sessions),
            "cross_tree_dependencies": sum(
                len(deps) for deps in self.cross_tree_dependencies.values()
            ),
            "resource_locks": len(self.resource_locks),
            "branches": {
                git_branch_id: {
                    "name": branch.name,
                    "assigned_agent": self.agent_assignments.get(git_branch_id),
                    "total_tasks": branch.get_task_count(),
                    "completed_tasks": branch.get_completed_task_count(),
                    "progress": branch.get_progress_percentage(),
                }
                for git_branch_id, branch in self.git_branchs.items()
            },
            "agents": {
                agent_id: {
                    "name": agent.name,
                    "capabilities": [
                        cap.value for cap in agent.capabilities
                    ],  # Convert set to list
                    "assigned_trees": [
                        git_branch_id
                        for git_branch_id, assigned_agent in self.agent_assignments.items()
                        if assigned_agent == agent_id
                    ],
                    "active_sessions": [
                        session.id
                        for session in self.active_work_sessions.values()
                        if session.agent_id == agent_id
                    ],
                }
                for agent_id, agent in self.registered_agents.items()
            },
        }

    def coordinate_cross_tree_dependencies(self) -> dict:
        """Coordinate and validate cross-tree dependencies"""
        coordination_result = {
            "total_dependencies": sum(
                len(deps) for deps in self.cross_tree_dependencies.values()
            ),
            "validated_dependencies": 0,
            "blocked_tasks": [],
            "ready_tasks": [],
            "missing_prerequisites": [],
        }

        for dependent_task_id, prerequisite_ids in self.cross_tree_dependencies.items():
            # Check if dependent task exists
            dependent_tree = self._find_git_branch(dependent_task_id)
            if not dependent_tree:
                coordination_result["missing_prerequisites"].append(
                    {"task_id": dependent_task_id, "issue": "Dependent task not found"}
                )
                continue

            # Check each prerequisite
            all_prerequisites_met = True
            for prerequisite_id in prerequisite_ids:
                prerequisite_tree = self._find_git_branch(prerequisite_id)
                if not prerequisite_tree:
                    coordination_result["missing_prerequisites"].append(
                        {
                            "task_id": prerequisite_id,
                            "issue": "Prerequisite task not found",
                        }
                    )
                    all_prerequisites_met = False
                    continue

                prerequisite_task = prerequisite_tree.get_task(prerequisite_id)
                if not prerequisite_task:
                    all_prerequisites_met = False
                    continue

                # Handle both Task entity and dict representation
                task_not_done = False
                if hasattr(prerequisite_task, "status"):
                    task_not_done = not prerequisite_task.status.is_done()
                elif isinstance(prerequisite_task, dict):
                    task_not_done = prerequisite_task.get("status") != "done"
                else:
                    task_not_done = True  # Unknown format, assume not done

                if task_not_done:
                    all_prerequisites_met = False

            if all_prerequisites_met:
                coordination_result["ready_tasks"].append(dependent_task_id)
            else:
                coordination_result["blocked_tasks"].append(dependent_task_id)

            coordination_result["validated_dependencies"] += 1

        return coordination_result

    # Rich Domain Model Business Methods

    def validate_agent_assignment(self, agent_id: str, task_tree_id: str) -> bool:
        """
        Validate that an agent can be assigned to a task tree.

        Args:
            agent_id: Agent identifier to validate
            task_tree_id: Task tree (git branch) identifier (can be string or GitBranchId)

        Returns:
            bool: True if assignment is valid, False otherwise

        Business Rules:
        - Agent must be registered in the project
        - Task tree must exist in the project
        - If tree is already assigned, new agent must be different
        - Agent must not be overloaded (max 3 concurrent tree assignments)
        """
        # Convert task_tree_id to string if it's a GitBranchId value object
        if hasattr(task_tree_id, "value"):
            task_tree_id_str = str(task_tree_id.value)
        else:
            task_tree_id_str = str(task_tree_id)

        # Rule 1: Agent must be registered
        if agent_id not in self.registered_agents:
            return False

        # Rule 2: Task tree must exist
        if task_tree_id_str not in self.git_branchs:
            return False

        # Rule 3: If tree already assigned, check it's different agent
        if task_tree_id_str in self.agent_assignments:
            current_agent = self.agent_assignments[task_tree_id_str]
            if current_agent != agent_id:
                # Tree is being reassigned - this is allowed
                pass

        # Rule 4: Check agent workload (max 3 concurrent assignments)
        agent_current_assignments = sum(
            1
            for assigned_agent in self.agent_assignments.values()
            if assigned_agent == agent_id
        )

        # If assigning to new tree (not reassignment), check workload limit
        if task_tree_id_str not in self.agent_assignments:
            if agent_current_assignments >= 3:
                # Agent is overloaded
                return False

        return True

    def calculate_project_health(self) -> dict[str, Any]:
        """
        Calculate overall project health metrics.

        Returns:
            Dict with health score, status, and detailed metrics

        Health Metrics:
        - overall_health_score: 0-100 scale
        - health_status: "excellent", "good", "fair", "poor", "critical"
        - branch_completion_rate: percentage of branches with all tasks complete
        - agent_utilization: percentage of registered agents actively assigned
        - blocked_task_percentage: percentage of tasks blocked by dependencies
        - active_work_ratio: active sessions vs total tasks

        Scoring Algorithm:
        - Branch completion: 40% weight
        - Agent utilization: 20% weight
        - Low blocked tasks: 25% weight
        - Active work ratio: 15% weight
        """
        # Metric 1: Branch completion rate
        total_branches = len(self.git_branchs)
        if total_branches == 0:
            branch_completion_rate = 100.0
        else:
            completed_branches = sum(
                1
                for branch in self.git_branchs.values()
                if branch.get_progress_percentage() == 100.0
            )
            branch_completion_rate = (completed_branches / total_branches) * 100

        # Metric 2: Agent utilization
        total_agents = len(self.registered_agents)
        if total_agents == 0:
            agent_utilization = 0.0
        else:
            assigned_agents = len(set(self.agent_assignments.values()))
            agent_utilization = (assigned_agents / total_agents) * 100

        # Metric 3: Blocked task percentage
        total_tasks = sum(
            branch.get_task_count() for branch in self.git_branchs.values()
        )
        if total_tasks == 0:
            blocked_task_percentage = 0.0
        else:
            # Count tasks blocked by cross-tree dependencies
            blocked_tasks = len(self.cross_tree_dependencies)
            blocked_task_percentage = (blocked_tasks / total_tasks) * 100

        # Metric 4: Active work ratio
        active_sessions = len(self.active_work_sessions)
        if total_tasks == 0:
            active_work_ratio = 0.0
        else:
            active_work_ratio = (active_sessions / total_tasks) * 100

        # Calculate overall health score (0-100)
        health_score = (
            (branch_completion_rate * 0.40)  # 40% weight
            + (agent_utilization * 0.20)  # 20% weight
            + ((100 - blocked_task_percentage) * 0.25)  # 25% weight (inverted)
            + (
                min(active_work_ratio, 50) * 0.30
            )  # 15% weight (capped at 50% = full score)
        )

        # Determine health status based on score
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 75:
            health_status = "good"
        elif health_score >= 60:
            health_status = "fair"
        elif health_score >= 40:
            health_status = "poor"
        else:
            health_status = "critical"

        return {
            "overall_health_score": round(health_score, 2),
            "health_status": health_status,
            "metrics": {
                "branch_completion_rate": round(branch_completion_rate, 2),
                "agent_utilization": round(agent_utilization, 2),
                "blocked_task_percentage": round(blocked_task_percentage, 2),
                "active_work_ratio": round(active_work_ratio, 2),
            },
            "counts": {
                "total_branches": total_branches,
                "completed_branches": sum(
                    1
                    for branch in self.git_branchs.values()
                    if branch.get_progress_percentage() == 100.0
                ),
                "total_agents": total_agents,
                "assigned_agents": len(set(self.agent_assignments.values())),
                "total_tasks": total_tasks,
                "blocked_tasks": len(self.cross_tree_dependencies),
                "active_sessions": active_sessions,
            },
        }

    def check_deadline_risk(self) -> dict[str, str]:
        """
        Assess if project is at risk of missing deadlines.

        Returns:
            Dict with risk level, assessment, and recommendations

        Risk Assessment Criteria:
        - "no_risk": All branches on track (completion rate > 75%)
        - "low_risk": Minor delays possible (completion rate 50-75%)
        - "medium_risk": Significant delays likely (completion rate 25-50%)
        - "high_risk": Major delays certain (completion rate < 25%)
        - "critical_risk": Project stalled (no active work, completion < 10%)

        Factors considered:
        - Overall project completion rate
        - Active work sessions vs total tasks
        - Blocked tasks ratio
        - Agent utilization
        """
        # Calculate key metrics
        total_branches = len(self.git_branchs)
        if total_branches == 0:
            return {
                "risk_level": "no_risk",
                "assessment": "No branches in project",
                "recommendation": "Create branches and tasks to begin work",
            }

        # Overall completion rate
        total_tasks = sum(
            branch.get_task_count() for branch in self.git_branchs.values()
        )
        if total_tasks == 0:
            return {
                "risk_level": "no_risk",
                "assessment": "No tasks defined yet",
                "recommendation": "Define tasks to track progress",
            }

        completed_tasks = sum(
            branch.get_completed_task_count() for branch in self.git_branchs.values()
        )
        completion_rate = (completed_tasks / total_tasks) * 100

        # Active work indicator
        active_sessions = len(self.active_work_sessions)
        has_active_work = active_sessions > 0

        # Blocked tasks ratio
        blocked_tasks = len(self.cross_tree_dependencies)
        blocked_ratio = (blocked_tasks / total_tasks) * 100 if total_tasks > 0 else 0

        # Agent utilization
        total_agents = len(self.registered_agents)
        assigned_agents = (
            len(set(self.agent_assignments.values())) if self.agent_assignments else 0
        )
        agent_utilization = (
            (assigned_agents / total_agents) * 100 if total_agents > 0 else 0
        )

        # Determine risk level based on multiple factors

        # Critical risk: Project stalled
        if completion_rate < 10 and not has_active_work:
            return {
                "risk_level": "critical_risk",
                "assessment": f"Project is stalled with only {completion_rate:.1f}% completion and no active work",
                "recommendation": "Immediately assign agents to tasks and resume development",
                "metrics": {
                    "completion_rate": round(completion_rate, 2),
                    "active_sessions": active_sessions,
                    "blocked_ratio": round(blocked_ratio, 2),
                    "agent_utilization": round(agent_utilization, 2),
                },
            }

        # High risk: Major delays certain
        if completion_rate < 25 or (blocked_ratio > 50 and not has_active_work):
            return {
                "risk_level": "high_risk",
                "assessment": f"Project at high risk with {completion_rate:.1f}% completion",
                "recommendation": "Increase agent assignments, address blockers, and accelerate development",
                "metrics": {
                    "completion_rate": round(completion_rate, 2),
                    "active_sessions": active_sessions,
                    "blocked_ratio": round(blocked_ratio, 2),
                    "agent_utilization": round(agent_utilization, 2),
                },
            }

        # Medium risk: Significant delays likely
        if completion_rate < 50 or blocked_ratio > 30:
            return {
                "risk_level": "medium_risk",
                "assessment": f"Project shows moderate risk with {completion_rate:.1f}% completion",
                "recommendation": "Review and resolve blockers, ensure adequate agent coverage",
                "metrics": {
                    "completion_rate": round(completion_rate, 2),
                    "active_sessions": active_sessions,
                    "blocked_ratio": round(blocked_ratio, 2),
                    "agent_utilization": round(agent_utilization, 2),
                },
            }

        # Low risk: Minor delays possible
        if completion_rate < 75:
            return {
                "risk_level": "low_risk",
                "assessment": f"Project on track with {completion_rate:.1f}% completion",
                "recommendation": "Continue current pace, monitor for emerging blockers",
                "metrics": {
                    "completion_rate": round(completion_rate, 2),
                    "active_sessions": active_sessions,
                    "blocked_ratio": round(blocked_ratio, 2),
                    "agent_utilization": round(agent_utilization, 2),
                },
            }

        # No risk: All branches on track
        return {
            "risk_level": "no_risk",
            "assessment": f"Project in excellent shape with {completion_rate:.1f}% completion",
            "recommendation": "Maintain current trajectory to successful completion",
            "metrics": {
                "completion_rate": round(completion_rate, 2),
                "active_sessions": active_sessions,
                "blocked_ratio": round(blocked_ratio, 2),
                "agent_utilization": round(agent_utilization, 2),
            },
        }
