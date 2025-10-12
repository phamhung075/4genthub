"""
Domain Events - Standardized Event System

All events follow the BaseDomainEvent pattern with:
- Immutability (frozen dataclasses)
- Self-contained data
- Automatic timestamping and ID generation
- Consistent serialization
"""

# Base event class
from .base import BaseDomainEvent, DomainEvent, create_domain_event

# Task lifecycle events (standardized in Phase 5)
from .task_lifecycle_events import (
    TaskCreatedEvent,
    TaskUpdatedEvent,
    TaskDeletedEvent,
    TaskStatusChangedEvent,
    TaskCompletedEvent,
    TaskRetrievedEvent,
    TaskMovedToBranchEvent,
)

# Backward compatibility aliases for task_events.py consumers
TaskCreated = TaskCreatedEvent
TaskUpdated = TaskUpdatedEvent
TaskDeleted = TaskDeletedEvent
TaskCompleted = TaskCompletedEvent
TaskRetrieved = TaskRetrievedEvent

# Agent events
from .agent_events import (
    AgentAssigned,
    AgentUnassigned,
    AgentWorkloadChanged,
    WorkHandoffRequested,
    WorkHandoffAccepted,
    WorkHandoffRejected,
    WorkHandoffCompleted,
    ConflictDetected,
    ConflictResolved,
    AgentCollaborationStarted,
    AgentCollaborationEnded,
    AgentStatusBroadcast,
    AgentWorkloadRebalanced,
    AgentEscalationRaised,
    AgentEscalationResolved,
    AgentCommunicationSent,
    AgentPerformanceEvaluated,
)

# Project events
from .project_lifecycle_events import (
    ProjectCreatedEvent,
    ProjectUpdatedEvent,
    ProjectDeletedEvent,
    ProjectStatisticsUpdatedEvent,
    ProjectHealthChanged,
    ProjectArchived,
)

# Context events
from .context_events import (
    ContextCreated,
    ContextUpdated,
    ContextDelegated,
    ContextInsightAdded,
    ContextProgressAdded,
    ContextInheritanceResolved,
)

__all__ = [
    # Base
    'BaseDomainEvent',
    'DomainEvent',
    'create_domain_event',

    # Task lifecycle events (standardized)
    'TaskCreatedEvent',
    'TaskUpdatedEvent',
    'TaskDeletedEvent',
    'TaskStatusChangedEvent',
    'TaskCompletedEvent',
    'TaskRetrievedEvent',
    'TaskMovedToBranchEvent',

    # Task events (backward compatibility aliases)
    'TaskCreated',
    'TaskUpdated',
    'TaskRetrieved',
    'TaskDeleted',
    'TaskCompleted',

    # Agent events
    'AgentAssigned',
    'AgentUnassigned',
    'AgentWorkloadChanged',
    'WorkHandoffRequested',
    'WorkHandoffAccepted',
    'WorkHandoffRejected',
    'WorkHandoffCompleted',
    'ConflictDetected',
    'ConflictResolved',
    'AgentCollaborationStarted',
    'AgentCollaborationEnded',
    'AgentStatusBroadcast',
    'AgentWorkloadRebalanced',
    'AgentEscalationRaised',
    'AgentEscalationResolved',
    'AgentCommunicationSent',
    'AgentPerformanceEvaluated',

    # Project events
    'ProjectCreatedEvent',
    'ProjectUpdatedEvent',
    'ProjectDeletedEvent',
    'ProjectStatisticsUpdatedEvent',
    'ProjectHealthChanged',
    'ProjectArchived',

    # Context events
    'ContextCreated',
    'ContextUpdated',
    'ContextDelegated',
    'ContextInsightAdded',
    'ContextProgressAdded',
    'ContextInheritanceResolved',
] 