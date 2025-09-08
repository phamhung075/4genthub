"""Task Management Application Domain

This module provides application layer domain components specific to task management.
It bridges the application services with domain entities and repositories.

This is distinct from the core domain layer and provides application-specific 
domain objects and interfaces.
"""

# Re-export core domain components for application layer access
# Import what's available and skip what's missing
try:
    from ...domain.entities.task import Task
    from ...domain.entities.project import Project  
    from ...domain.entities.git_branch import GitBranch
except ImportError as e:
    pass

try:
    from ...domain.repositories.task_repository import TaskRepository
    from ...domain.repositories.project_repository import ProjectRepository
    from ...domain.repositories.git_branch_repository import GitBranchRepository
except ImportError as e:
    pass

try:
    from ...domain.enums.agent_roles import AgentRole
    from ...domain.enums.estimated_effort import EstimatedEffort, EffortLevel
    from ...domain.enums.common_labels import CommonLabel, LabelValidator
    # compliance_enums removed
except ImportError as e:
    pass