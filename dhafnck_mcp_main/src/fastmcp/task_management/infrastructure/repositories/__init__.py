"""Infrastructure Repositories"""

# Legacy imports (commented out)
# from .json_task_repository import JsonTaskRepository, InMemoryTaskRepository

# Project repositories
from .orm.project_repository import ORMProjectRepository
from .project_repository_factory import ProjectRepositoryFactory, create_project_repository, get_default_repository

# Agent repositories
from .orm.agent_repository import ORMAgentRepository
from .agent_repository_factory import AgentRepositoryFactory, create_agent_repository, get_default_agent_repository

# Context repositories
# from .orm.hierarchical_context_repository import ORMHierarchicalContextRepository
# # Alias for backward compatibility
# ORMContextRepository = ORMHierarchicalContextRepository

__all__ = [
    # Project repositories
    "ORMProjectRepository",
    "ProjectRepositoryFactory", 
    "create_project_repository",
    "get_default_repository",
    
    # Agent repositories
    "ORMAgentRepository", 
    "AgentRepositoryFactory",
    "create_agent_repository",
    "get_default_agent_repository",
    
    # Context repositories
    # "ORMContextRepository",
] 