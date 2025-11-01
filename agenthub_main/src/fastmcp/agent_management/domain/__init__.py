"""Agent management domain layer - following DDD patterns."""

from .entities import AgentTemplate, UserAgentInstance
from .value_objects import (
    AgentTemplateId,
    AgentConfiguration,
    UserId,
    UserAgentInstanceId,
)
from .repositories import (
    AgentTemplateRepository,
    UserAgentInstanceRepository,
)
from .services import (
    AgentInstantiationService,
    AgentCustomizationService,
    AgentSharingService,
)

__all__ = [
    # Entities
    "AgentTemplate",
    "UserAgentInstance",
    # Value Objects
    "AgentTemplateId",
    "AgentConfiguration",
    "UserId",
    "UserAgentInstanceId",
    # Repository Interfaces
    "AgentTemplateRepository",
    "UserAgentInstanceRepository",
    # Domain Services
    "AgentInstantiationService",
    "AgentCustomizationService",
    "AgentSharingService",
]
