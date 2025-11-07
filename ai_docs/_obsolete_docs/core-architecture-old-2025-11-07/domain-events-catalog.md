# Domain Events Catalog

**Document Version**: 1.0
**Last Updated**: 2025-10-09
**Phase**: Phase 5 - Domain Events Pattern
**Status**: Active

## Table of Contents

1. [Overview](#overview)
2. [Event Infrastructure](#event-infrastructure)
3. [Event Categories](#event-categories)
4. [Task Lifecycle Events](#task-lifecycle-events)
5. [Agent Coordination Events](#agent-coordination-events)
6. [Project Lifecycle Events](#project-lifecycle-events)
7. [Context Management Events](#context-management-events)
8. [Event Naming Conventions](#event-naming-conventions)
9. [Related Documentation](#related-documentation)

## Overview

The Domain Events system implements an event-driven architecture following Domain-Driven Design (DDD) principles. Events capture state changes in domain aggregates and enable loose coupling between system components.

### Key Principles

- **Immutability**: All events are frozen dataclasses that cannot be modified after creation
- **Self-Contained**: Events include all data needed by handlers without external lookups
- **Timestamped**: Every event records when it occurred with UTC timezone
- **Identifiable**: Each event has a unique UUID for tracking and debugging
- **Traceable**: Events track the aggregate they relate to for audit trails

### Event System Statistics

- **Total Events**: 36 domain events across 4 categories
- **Base Classes**: 1 unified `BaseDomainEvent` class
- **Event Handlers**: 5 handler classes (1,392 lines of handler code)
- **Event Categories**: Task (7), Agent (17), Project (6), Context (6)

## Event Infrastructure

### BaseDomainEvent

**Location**: `agenthub_main/src/fastmcp/task_management/domain/events/base.py`

All domain events inherit from `BaseDomainEvent`, which provides:

```python
@dataclass(frozen=True)
class BaseDomainEvent(ABC):
    """Base class for all domain events following DDD principles."""

    # Event metadata (common to all events)
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    user_id: Optional[str] = None

    @property
    def event_type(self) -> str:
        """Return the type name of this event."""
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        # Handles UUID and datetime serialization automatically
```

### Common Properties

| Property | Type | Description | Auto-Generated |
|----------|------|-------------|----------------|
| `event_id` | UUID | Unique identifier for this event instance | Yes |
| `occurred_at` | datetime | UTC timestamp when event occurred | Yes |
| `aggregate_id` | Optional[str] | ID of the aggregate this event relates to | No |
| `aggregate_type` | Optional[str] | Type/name of the aggregate | No |
| `user_id` | Optional[str] | ID of user who triggered this event | No |

### Factory Function

```python
def create_domain_event(
    event_class: type,
    aggregate_id: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> BaseDomainEvent:
    """Factory function to create domain events with automatic metadata."""
```

## Event Categories

### Summary Table

| Category | Event Count | Primary Use Case | Handler |
|----------|-------------|------------------|---------|
| Task Lifecycle | 7 | Track task state changes | TaskEventHandlers |
| Agent Coordination | 17 | Multi-agent workflows | AgentEventHandlers |
| Project Lifecycle | 6 | Project management | ProjectEventHandlers |
| Context Management | 6 | Context operations | (Planned) |

## Task Lifecycle Events

**Location**: `domain/events/task_lifecycle_events.py`
**Handler**: `application/event_handlers/task_event_handlers.py` (374 lines)

### 1. TaskCreatedEvent

**When Raised**: When a new task is created in the system

**Properties**:
```python
@dataclass(frozen=True)
class TaskCreatedEvent(BaseDomainEvent):
    task_id: str                      # Unique task identifier
    branch_id: str                    # Git branch this task belongs to
    title: str                        # Task title
    status: str                       # Initial status (usually "todo")
    priority: str                     # Task priority level
    assignees: List[str]              # List of assigned agent IDs
    user_id: Optional[str]            # User who created the task
```

**Handler Actions**:
- Update project statistics
- Initialize task context
- Send notifications to assigned agents
- Trigger workflow automation

**Example**:
```python
event = TaskCreatedEvent(
    task_id="task-uuid-123",
    branch_id="branch-uuid-456",
    title="Implement authentication",
    status="todo",
    priority="high",
    assignees=["coding-agent", "security-auditor-agent"],
    user_id="user-789"
)
```

### 2. TaskUpdatedEvent

**When Raised**: When task properties are modified

**Properties**:
```python
@dataclass(frozen=True)
class TaskUpdatedEvent(BaseDomainEvent):
    task_id: str                      # Task being updated
    branch_id: str                    # Current branch
    old_status: Optional[str]         # Previous status (if changed)
    new_status: Optional[str]         # New status (if changed)
    old_branch_id: Optional[str]      # Previous branch (if moved)
    new_branch_id: Optional[str]      # New branch (if moved)
    changes: Dict[str, Any]           # All changed fields
    user_id: Optional[str]            # User who made changes
```

**Handler Actions**:
- Update statistics if status changed
- Re-index search data
- Notify affected agents of changes
- Update context with change history

### 3. TaskDeletedEvent

**When Raised**: When a task is removed from the system

**Properties**:
```python
@dataclass(frozen=True)
class TaskDeletedEvent(BaseDomainEvent):
    task_id: str                      # Task being deleted
    branch_id: str                    # Branch it belonged to
    status: str                       # Final status before deletion
    title: str                        # Task title (for audit trail)
    user_id: Optional[str]            # User who deleted the task
```

**Handler Actions**:
- Update project statistics
- Clean up related contexts
- Archive task data for audit
- Notify assigned agents

### 4. TaskStatusChangedEvent

**When Raised**: When task status transitions (todo → in_progress → done, etc.)

**Properties**:
```python
@dataclass(frozen=True)
class TaskStatusChangedEvent(BaseDomainEvent):
    task_id: str                      # Task with status change
    branch_id: str                    # Branch task belongs to
    old_status: str                   # Previous status
    new_status: str                   # New status
    user_id: Optional[str]            # User who changed status
```

**Handler Actions**:
- Update workflow state machines
- Trigger status-specific actions (e.g., review on completion)
- Update statistics and metrics
- Send status change notifications

### 5. TaskCompletedEvent ⭐ NEW

**When Raised**: When a task is marked as completed (rich completion context)

**Properties**:
```python
@dataclass(frozen=True)
class TaskCompletedEvent(BaseDomainEvent):
    task_id: str                      # Completed task
    branch_id: str                    # Branch task belongs to
    title: str                        # Task title
    completion_summary: str           # What was accomplished
    testing_notes: Optional[str]      # Testing performed
    completed_by: Optional[str]       # Agent/user who completed
    time_spent_minutes: Optional[int] # Time taken
    insights_found: List[str]         # Learnings from this task
```

**Handler Actions**:
- Update completion metrics
- Store insights in knowledge base
- Trigger downstream tasks
- Generate completion reports
- Update agent performance metrics

**Note**: This is a Phase 5 addition that provides richer context than generic status changes.

### 6. TaskRetrievedEvent

**When Raised**: When a task is fetched from the repository

**Properties**:
```python
@dataclass(frozen=True)
class TaskRetrievedEvent(BaseDomainEvent):
    task_id: str                      # Task being retrieved
    branch_id: Optional[str]          # Branch (if known)
    user_id: Optional[str]            # User retrieving task
```

**Handler Actions**:
- Track access patterns
- Update "last accessed" metadata
- Log for audit trail

### 7. TaskMovedToBranchEvent

**When Raised**: When a task is moved to a different git branch

**Properties**:
```python
@dataclass(frozen=True)
class TaskMovedToBranchEvent(BaseDomainEvent):
    task_id: str                      # Task being moved
    old_branch_id: str                # Source branch
    new_branch_id: str                # Destination branch
    user_id: Optional[str]            # User who moved task
```

**Handler Actions**:
- Update branch statistics
- Reindex task location
- Update context hierarchy
- Notify branch maintainers

## Agent Coordination Events

**Location**: `domain/events/agent_events.py`
**Handler**: `application/event_handlers/agent_event_handlers.py` (521 lines)

This is the largest event category with 17 events supporting multi-agent collaboration.

### Assignment & Workload Events (3 events)

#### 1. AgentAssigned

**When Raised**: When an agent is assigned to a task

**Properties**:
```python
@dataclass(frozen=True)
class AgentAssigned(BaseDomainEvent):
    agent_id: str                     # Agent being assigned
    task_id: str                      # Task being assigned to
    role: str                         # Agent's role on this task
    assigned_by: str                  # Who made the assignment
    responsibilities: List[str]       # Specific duties
    estimated_hours: Optional[float]  # Estimated effort
    due_date: Optional[datetime]      # Expected completion date
```

**Handler Actions**:
- Update agent workload metrics
- Send assignment notification
- Initialize agent-task context
- Check for workload imbalance

#### 2. AgentUnassigned

**When Raised**: When an agent is removed from a task

**Properties**:
```python
@dataclass(frozen=True)
class AgentUnassigned(BaseDomainEvent):
    agent_id: str                     # Agent being unassigned
    task_id: str                      # Task being unassigned from
    unassigned_by: str                # Who removed assignment
    reason: str                       # Why unassigned
    handoff_to_agent: Optional[str]   # Replacement agent (if any)
    handoff_notes: Optional[str]      # Transition notes
```

**Handler Actions**:
- Update agent workload
- Process handoff if specified
- Archive agent-task context
- Notify affected parties

#### 3. AgentWorkloadChanged ⭐ NEW

**When Raised**: When an agent's workload metrics change

**Properties**:
```python
@dataclass(frozen=True)
class AgentWorkloadChanged(BaseDomainEvent):
    agent_id: str                     # Agent with workload change
    old_task_count: int               # Previous task count
    new_task_count: int               # New task count
    old_workload_percentage: float    # Previous workload %
    new_workload_percentage: float    # New workload %
    reason: str                       # Why workload changed
```

**Handler Actions**:
- Track agent capacity
- Trigger rebalancing if needed
- Update agent availability status
- Alert on overload conditions

**Note**: Phase 5 addition for workload monitoring.

### Work Handoff Events (4 events)

#### 4. WorkHandoffRequested

**When Raised**: When one agent requests to hand off work to another

**Properties**:
```python
@dataclass(frozen=True)
class WorkHandoffRequested(BaseDomainEvent):
    handoff_id: str                   # Unique handoff identifier
    from_agent_id: str                # Agent handing off work
    to_agent_id: str                  # Agent receiving work
    task_id: str                      # Task being handed off
    work_summary: str                 # Summary of work done
    completed_items: List[str]        # What's complete
    remaining_items: List[str]        # What's left
    handoff_notes: str                # Additional context
```

**Handler Actions**:
- Notify receiving agent
- Create handoff record
- Schedule knowledge transfer
- Track handoff metrics

#### 5. WorkHandoffAccepted

**When Raised**: When an agent accepts a work handoff

**Properties**:
```python
@dataclass(frozen=True)
class WorkHandoffAccepted(BaseDomainEvent):
    handoff_id: str                   # Handoff being accepted
    accepted_by: str                  # Agent accepting work
    task_id: str                      # Task involved
    acceptance_notes: Optional[str]   # Agent's notes on acceptance
```

**Handler Actions**:
- Update task assignment
- Transfer ownership
- Close handoff request
- Update handoff success metrics

#### 6. WorkHandoffRejected

**When Raised**: When an agent rejects a work handoff

**Properties**:
```python
@dataclass(frozen=True)
class WorkHandoffRejected(BaseDomainEvent):
    handoff_id: str                   # Handoff being rejected
    rejected_by: str                  # Agent rejecting work
    task_id: str                      # Task involved
    rejection_reason: str             # Why rejected
```

**Handler Actions**:
- Notify original agent
- Find alternative agent
- Update handoff failure metrics
- Escalate if needed

#### 7. WorkHandoffCompleted

**When Raised**: When a work handoff is successfully completed

**Properties**:
```python
@dataclass(frozen=True)
class WorkHandoffCompleted(BaseDomainEvent):
    handoff_id: str                   # Completed handoff
    from_agent_id: str                # Original agent
    to_agent_id: str                  # New agent
    task_id: str                      # Task involved
    handoff_duration_hours: float     # Time taken for handoff
    knowledge_transfer_complete: bool # Transfer successful?
```

**Handler Actions**:
- Archive handoff record
- Update success metrics
- Document learnings
- Close related notifications

### Conflict Management Events (2 events)

#### 8. ConflictDetected

**When Raised**: When a conflict between agents is detected

**Properties**:
```python
@dataclass(frozen=True)
class ConflictDetected(BaseDomainEvent):
    conflict_id: str                  # Unique conflict identifier
    conflict_type: str                # Type: concurrent_edit, resource_contention, etc.
    involved_agents: List[str]        # Agents in conflict
    task_id: str                      # Related task
    description: str                  # Conflict description
    conflicting_elements: Dict[str, Any] # What's conflicting
    impact_assessment: str            # Severity: low, medium, high, critical
    suggested_resolution: Optional[str] # Suggested fix
```

**Handler Actions**:
- Alert involved agents
- Pause conflicting operations
- Suggest resolution strategy
- Escalate if critical

#### 9. ConflictResolved

**When Raised**: When a conflict is resolved

**Properties**:
```python
@dataclass(frozen=True)
class ConflictResolved(BaseDomainEvent):
    conflict_id: str                  # Resolved conflict
    resolution_strategy: str          # How resolved: merge, override, vote, escalate
    resolved_by: str                  # Who resolved it
    task_id: str                      # Related task
    resolution_details: str           # How it was resolved
    winning_agent: Optional[str]      # Winner (if applicable)
    compromise_details: Optional[Dict[str, Any]] # Compromise reached
```

**Handler Actions**:
- Resume operations
- Document resolution
- Update conflict metrics
- Close conflict tracking

### Collaboration Events (2 events)

#### 10. AgentCollaborationStarted

**When Raised**: When agents begin collaborating on work

**Properties**:
```python
@dataclass(frozen=True)
class AgentCollaborationStarted(BaseDomainEvent):
    collaboration_id: str             # Unique collaboration ID
    initiating_agent: str             # Agent starting collaboration
    collaborating_agents: List[str]   # All participating agents
    task_id: str                      # Task being collaborated on
    collaboration_type: str           # Type: general, pair_programming, review, brainstorming
    objectives: List[str]             # Collaboration goals
    expected_duration_hours: Optional[float] # Expected time
```

**Handler Actions**:
- Create collaboration context
- Set up communication channels
- Track collaboration metrics
- Schedule check-ins

#### 11. AgentCollaborationEnded

**When Raised**: When collaboration session ends

**Properties**:
```python
@dataclass(frozen=True)
class AgentCollaborationEnded(BaseDomainEvent):
    collaboration_id: str             # Ended collaboration
    task_id: str                      # Related task
    outcomes: List[str]               # What was achieved
    decisions_made: Dict[str, str]    # Decisions reached
    follow_up_actions: List[Dict[str, Any]] # Next steps
    duration_hours: float             # Actual time spent
```

**Handler Actions**:
- Archive collaboration notes
- Update task with outcomes
- Document decisions
- Schedule follow-ups

### Communication & Status Events (3 events)

#### 12. AgentStatusBroadcast

**When Raised**: When an agent broadcasts its status

**Properties**:
```python
@dataclass(frozen=True)
class AgentStatusBroadcast(BaseDomainEvent):
    agent_id: str                     # Broadcasting agent
    status: str                       # Status: available, busy, blocked, offline
    current_task_id: Optional[str]    # Current work (if any)
    current_activity: Optional[str]   # What agent is doing
    blocker_description: Optional[str] # What's blocking (if blocked)
    estimated_availability: Optional[datetime] # When available again
    workload_percentage: float        # Current workload level
```

**Handler Actions**:
- Update agent status dashboard
- Route new work appropriately
- Alert on blocked agents
- Update capacity planning

#### 13. AgentWorkloadRebalanced

**When Raised**: When workload is redistributed among agents

**Properties**:
```python
@dataclass(frozen=True)
class AgentWorkloadRebalanced(BaseDomainEvent):
    rebalance_id: str                 # Rebalance operation ID
    initiated_by: str                 # Who initiated rebalance
    agents_affected: List[str]        # All affected agents
    tasks_reassigned: Dict[str, str]  # task_id -> new_agent_id mappings
    reason: str                       # Why rebalanced
    workload_before: Dict[str, int]   # agent_id -> task_count before
    workload_after: Dict[str, int]    # agent_id -> task_count after
```

**Handler Actions**:
- Execute task reassignments
- Notify affected agents
- Update workload metrics
- Document rebalance rationale

#### 14. AgentCommunicationSent

**When Raised**: When an agent sends a message

**Properties**:
```python
@dataclass(frozen=True)
class AgentCommunicationSent(BaseDomainEvent):
    message_id: str                   # Unique message ID
    from_agent_id: str                # Sending agent
    to_agent_ids: List[str]           # Recipient agents
    message_type: str                 # Type: status_update, question, response, notification
    subject: str                      # Message subject
    priority: str                     # Priority: low, normal, high, urgent
    task_id: Optional[str]            # Related task (if any)
    requires_response: bool           # Response needed?
```

**Handler Actions**:
- Deliver message to recipients
- Track delivery status
- Set response reminders
- Archive communication

### Escalation Events (2 events)

#### 15. AgentEscalationRaised

**When Raised**: When an agent needs help from senior agent/manager

**Properties**:
```python
@dataclass(frozen=True)
class AgentEscalationRaised(BaseDomainEvent):
    escalation_id: str                # Unique escalation ID
    escalating_agent: str             # Agent requesting help
    escalated_to: str                 # Manager or senior agent
    task_id: str                      # Related task
    reason: str                       # Why escalating
    severity: str                     # Severity: low, medium, high, critical
    context: Dict[str, Any]           # Additional context
    requested_action: str             # What help is needed
    deadline: Optional[datetime]      # Response deadline
```

**Handler Actions**:
- Alert escalation target
- Track response time
- Provide context access
- Monitor resolution

#### 16. AgentEscalationResolved

**When Raised**: When an escalation is resolved

**Properties**:
```python
@dataclass(frozen=True)
class AgentEscalationResolved(BaseDomainEvent):
    escalation_id: str                # Resolved escalation
    resolved_by: str                  # Who resolved it
    task_id: str                      # Related task
    resolution: str                   # How resolved
    actions_taken: List[str]          # Steps taken
    guidance_provided: Optional[str]  # Advice given
```

**Handler Actions**:
- Notify original agent
- Document resolution
- Update escalation metrics
- Close escalation tracking

### Performance Event (1 event)

#### 17. AgentPerformanceEvaluated

**When Raised**: When agent performance is assessed

**Properties**:
```python
@dataclass(frozen=True)
class AgentPerformanceEvaluated(BaseDomainEvent):
    agent_id: str                     # Evaluated agent
    evaluation_id: str                # Evaluation ID
    evaluated_by: Optional[str]       # Evaluator (None if system-generated)
    task_id: Optional[str]            # Related task (if task-specific)
    quality_score: float              # Quality rating (0-1)
    timeliness_score: float           # Timeliness rating (0-1)
    collaboration_score: float        # Collaboration rating (0-1)
    overall_score: float              # Overall rating (0-1)
    strengths: List[str]              # Identified strengths
    areas_for_improvement: List[str]  # Improvement areas
```

**Handler Actions**:
- Update agent profile
- Track performance trends
- Trigger training if needed
- Inform agent of feedback

## Project Lifecycle Events

**Location**: `domain/events/project_lifecycle_events.py`
**Handler**: `application/event_handlers/project_event_handlers.py` (497 lines)

### 1. ProjectCreatedEvent

**When Raised**: When a new project is initialized

**Properties**:
```python
@dataclass(frozen=True)
class ProjectCreatedEvent(BaseDomainEvent):
    project_id: str                   # Unique project identifier
    name: str                         # Project name
    description: Optional[str]        # Project description
    status: str                       # Initial status (default: 'active')
```

**Handler Actions**:
- Initialize project structure
- Create default branches
- Set up project context
- Send creation notifications

### 2. ProjectUpdatedEvent

**When Raised**: When project properties are modified

**Properties**:
```python
@dataclass(frozen=True)
class ProjectUpdatedEvent(BaseDomainEvent):
    project_id: str                   # Project being updated
    old_name: Optional[str]           # Previous name (if changed)
    new_name: Optional[str]           # New name (if changed)
    old_status: Optional[str]         # Previous status (if changed)
    new_status: Optional[str]         # New status (if changed)
    old_description: Optional[str]    # Previous description (if changed)
    new_description: Optional[str]    # New description (if changed)
```

**Handler Actions**:
- Update project metadata
- Reindex project data
- Notify project members
- Update dashboards

### 3. ProjectDeletedEvent

**When Raised**: When a project is removed from the system

**Properties**:
```python
@dataclass(frozen=True)
class ProjectDeletedEvent(BaseDomainEvent):
    project_id: str                   # Deleted project
    name: str                         # Project name (for audit)
    branches_deleted: int             # Number of branches removed
    tasks_deleted: int                # Number of tasks removed
    subtasks_deleted: int             # Number of subtasks removed
    contexts_deleted: int             # Number of contexts removed
```

**Handler Actions**:
- Archive project data
- Clean up resources
- Update statistics
- Notify affected users

### 4. ProjectStatisticsUpdatedEvent

**When Raised**: When project metrics are recalculated

**Properties**:
```python
@dataclass(frozen=True)
class ProjectStatisticsUpdatedEvent(BaseDomainEvent):
    project_id: str                   # Project with updated stats
    branch_count: int                 # Total branches
    total_tasks: int                  # Total tasks
    completed_tasks: int              # Completed tasks
    in_progress_tasks: int            # In-progress tasks
    todo_tasks: int                   # Todo tasks
    overall_progress_percentage: float # Overall completion %
```

**Handler Actions**:
- Update project dashboards
- Trigger alerts on thresholds
- Update reports
- Check health status

### 5. ProjectHealthChanged ⭐ NEW

**When Raised**: When project health status changes

**Properties**:
```python
@dataclass(frozen=True)
class ProjectHealthChanged(BaseDomainEvent):
    project_id: str                   # Project with health change
    old_health_status: str            # Previous health status
    new_health_status: str            # New health status
    health_metrics: Dict[str, Any]    # Detailed health metrics
    reason: Optional[str]             # Why health changed
```

**Handler Actions**:
- Alert project stakeholders
- Trigger interventions if needed
- Update health dashboard
- Document health trends

**Note**: Phase 5 addition for proactive project monitoring.

### 6. ProjectArchived

**When Raised**: When a project is archived (soft delete)

**Properties**:
```python
@dataclass(frozen=True)
class ProjectArchived(BaseDomainEvent):
    project_id: str                   # Archived project
    name: str                         # Project name
    archived_by: str                  # User who archived
    reason: Optional[str]             # Why archived
```

**Handler Actions**:
- Move to archive storage
- Update project status
- Preserve audit trail
- Notify project members

## Context Management Events

**Location**: `domain/events/context_events.py`
**Handler**: (Planned - not yet implemented)

### 1. ContextCreated

**When Raised**: When a new context is created at any hierarchy level

**Properties**:
```python
@dataclass(frozen=True)
class ContextCreated(DomainEvent):
    context_id: str                   # Context identifier
    level: str                        # Level: global, project, branch, task
    created_by: str                   # User who created context
    created_at: datetime              # Creation timestamp
```

### 2. ContextUpdated

**When Raised**: When context data is modified

**Properties**:
```python
@dataclass(frozen=True)
class ContextUpdated(DomainEvent):
    context_id: str                   # Context being updated
    level: str                        # Context level
    updated_by: str                   # User making updates
    changes: Dict[str, Any]           # Changed fields
    updated_at: datetime              # Update timestamp
```

### 3. ContextDelegated

**When Raised**: When context data is delegated to a higher hierarchy level

**Properties**:
```python
@dataclass(frozen=True)
class ContextDelegated(DomainEvent):
    source_context_id: str            # Source context
    source_level: str                 # Source level
    target_level: str                 # Target level
    delegated_data: Dict[str, Any]    # Data being delegated
    delegation_reason: str            # Why delegated
    delegated_by: str                 # Who initiated delegation
    delegated_at: datetime            # Delegation timestamp
```

### 4. ContextInsightAdded

**When Raised**: When an insight is added to a context

**Properties**:
```python
@dataclass(frozen=True)
class ContextInsightAdded(DomainEvent):
    context_id: str                   # Context receiving insight
    level: str                        # Context level
    insight_content: str              # Insight text
    insight_category: str             # Category: technical, business, etc.
    importance: str                   # Importance level
    added_by: str                     # Who added insight
    added_at: datetime                # When added
```

### 5. ContextProgressAdded

**When Raised**: When progress update is added to context

**Properties**:
```python
@dataclass(frozen=True)
class ContextProgressAdded(DomainEvent):
    context_id: str                   # Context receiving progress
    level: str                        # Context level
    progress_content: str             # Progress description
    added_by: str                     # Who added progress
    added_at: datetime                # When added
```

### 6. ContextInheritanceResolved

**When Raised**: When context inheritance chain is resolved

**Properties**:
```python
@dataclass(frozen=True)
class ContextInheritanceResolved(DomainEvent):
    context_id: str                   # Context with resolved inheritance
    level: str                        # Context level
    inheritance_chain: list[str]      # Chain of inherited contexts
    resolved_by: str                  # Who resolved (system/user)
    resolved_at: datetime             # When resolved
```

## Event Naming Conventions

### Pattern: `{Aggregate}{Action}Event` or `{Aggregate}{Action}`

- **Aggregate**: The domain aggregate the event relates to (Task, Agent, Project, Context)
- **Action**: Past-tense verb describing what happened (Created, Updated, Deleted, Changed)
- **Event**: Suffix (optional for backward compatibility)

### Examples

✅ **Good Names**:
- `TaskCreatedEvent` - Clear aggregate and action
- `AgentAssigned` - Concise and descriptive
- `ProjectHealthChanged` - Specific state change
- `WorkHandoffCompleted` - Describes workflow state

❌ **Bad Names**:
- `TaskEvent` - Too generic
- `UpdateTask` - Imperative, not past tense
- `TaskWasUpdated` - Verbose
- `Change` - Missing aggregate

### Phase 5 New Events

Events added during Phase 5 standardization:
- `TaskCompletedEvent` - Rich completion context
- `AgentWorkloadChanged` - Workload tracking
- `ProjectHealthChanged` - Health monitoring
- `ProjectArchived` - Soft delete support

## Related Documentation

### Phase 5 Documentation
- [Domain Events Usage Guide](../development-guides/domain-events-usage-guide.md) - How to use events
- [Event Handlers Reference](../development-guides/event-handlers-reference.md) - Handler details
- [DDD Refactoring Task Roadmap](../development-guides/ddd-refactoring-task-roadmap.md) - Phase 5 plan

### DDD Architecture
- [DDD Compliance Review](../reports-status/ddd-compliance-review-2025-10-09.md) - Compliance status
- [DDD Refactoring Implementation Plan](../development-guides/ddd-refactoring-implementation-plan.md) - Overall strategy

### Code Locations
- Base Events: `agenthub_main/src/fastmcp/task_management/domain/events/base.py`
- Task Events: `agenthub_main/src/fastmcp/task_management/domain/events/task_lifecycle_events.py`
- Agent Events: `agenthub_main/src/fastmcp/task_management/domain/events/agent_events.py`
- Project Events: `agenthub_main/src/fastmcp/task_management/domain/events/project_lifecycle_events.py`
- Context Events: `agenthub_main/src/fastmcp/task_management/domain/events/context_events.py`
- Event Handlers: `agenthub_main/src/fastmcp/task_management/application/event_handlers/`

---

**Document Status**: Complete ✅
**Total Events Documented**: 36 events across 4 categories
**Next**: See [Domain Events Usage Guide](../development-guides/domain-events-usage-guide.md) for implementation patterns
