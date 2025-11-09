# DDD Architecture - Complete Guide

## Quick Reference

| Layer | Components | Key Pattern | Files |
|-------|-----------|-------------|-------|
| **Domain** | Entities, Value Objects, Domain Services, Events | Business logic lives here | `domain/entities/`, `domain/value_objects/`, `domain/services/` |
| **Application** | Facades, Use Cases, DTOs | Orchestration, transactions | `application/facades/`, `application/use_cases/`, `application/dtos/` |
| **Infrastructure** | Repositories, Database, Event Bus | Persistence, external integrations | `infrastructure/repositories/`, `infrastructure/database/` |
| **Interface** | MCP Controllers, API Endpoints | Protocol handling, validation | `interface/mcp_controllers/`, `interface/rest/` |

**Flow**: Client → Interface → Application → Domain → Infrastructure → Response

---

## Complete System Flow

### Request Flow (manage_task example)

| Step | Layer | Action | Result |
|------|-------|--------|--------|
| 1 | MCP Client | Send request | Request initiated |
| 2 | Transport | WebSocket/HTTP/2, generate request_id | Connection ready |
| 3 | FastMCP Server | Route to TaskController | Controller selected |
| 4 | Auth Middleware | Validate JWT, extract user context | Authorized user |
| 5 | Interface (Controller) | Parse params, validate types, create DTO | Valid DTO |
| 6 | Application (Facade) | Begin transaction, initialize audit | Transaction started |
| 7 | Application (Use Case) | Validate business rules, create entity | Task entity |
| 8 | Domain (Services) | Enforce invariants, emit events | Valid entity + events |
| 9 | Infrastructure (Repository) | Persist to database, generate UUID | Persisted task |
| 10 | Infrastructure (Event Bus) | Publish TaskCreatedEvent | Event propagated |
| 11 | Application (Facade) | Commit transaction, format response | Response DTO |
| 12 | Interface (Controller) | Add workflow guidance, serialize JSON | MCP response |
| 13 | Transport | Send response to client | Complete |

### Authentication Pipeline

| Stage | Process | Output |
|-------|---------|--------|
| Token Extraction | Extract JWT from headers | Raw token |
| Signature Verification | Validate RS256/HS256 | Verified token |
| Claims Validation | Check expiry, issuer, audience | Valid claims |
| User Context | Extract user_id, tenant_id, session metadata | User context object |
| MVP Mode | If AUTH_ENABLED=false: bypass, use default context | Development context |
| Authorization | Load permissions, check RBAC, rate limit | Authorized request |

---

## Domain Layer

### Entities

**Purpose**: Core business objects with identity and lifecycle

**Characteristics**:
- Has unique identifier (UUID)
- Has lifecycle (created, modified, deleted)
- Contains business logic
- Emits domain events on state changes

**Example** (Task Entity):
```python
@dataclass
class Task(Entity):
    id: TaskId  # Value object wrapping UUID
    title: str
    description: str
    status: TaskStatus  # Enum value object
    priority: Priority
    assignees: List[str]
    dependencies: List[TaskId]

    # Business logic methods
    def can_be_completed(self) -> bool:
        """Business rule: Task can only be completed if all dependencies are done."""
        return all(dep.is_completed() for dep in self.dependencies)

    def complete(self, summary: str) -> None:
        """Complete task with validation."""
        if not self.can_be_completed():
            raise DomainException("Cannot complete: dependencies not met")

        self.status = TaskStatus.DONE
        self.emit_event(TaskCompletedEvent(task_id=self.id, summary=summary))
```

**Key Principles**:
- Entities enforce business invariants
- State changes emit domain events
- No database logic in entities
- All business rules in domain layer

### Value Objects

**Purpose**: Immutable objects defined by their attributes, not identity

**Characteristics**:
- Immutable (no setters)
- Equality by value, not reference
- Self-validating
- No database identity

**Examples**:
```python
@dataclass(frozen=True)
class TaskId:
    """Value object for Task ID with validation."""
    value: UUID

    @classmethod
    def create(cls) -> 'TaskId':
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> 'TaskId':
        try:
            return cls(value=UUID(id_str))
        except ValueError:
            raise ValueError(f"Invalid UUID format: {id_str}")

    def __str__(self) -> str:
        return str(self.value)

@dataclass(frozen=True)
class Priority:
    """Priority value object with business rules."""
    value: str  # low|medium|high|urgent|critical

    VALID_PRIORITIES = ["low", "medium", "high", "urgent", "critical"]

    def __post_init__(self):
        if self.value not in self.VALID_PRIORITIES:
            raise ValueError(f"Invalid priority: {self.value}")

    def is_higher_than(self, other: 'Priority') -> bool:
        """Compare priorities."""
        priority_order = {p: i for i, p in enumerate(self.VALID_PRIORITIES)}
        return priority_order[self.value] > priority_order[other.value]
```

**When to Use**:
- IDs, email addresses, dates
- Money, measurements
- Enums with validation
- Complex types (address, phone number)

### Domain Services

**Purpose**: Business logic that doesn't belong to a single entity

**Characteristics**:
- Stateless operations
- Multi-entity business rules
- Complex calculations
- Domain-level validations

**Example**:
```python
class DependencyManagementService:
    """Manages task dependencies and prevents cycles."""

    def can_add_dependency(self, task: Task, dependency: Task) -> bool:
        """Check if dependency can be added without creating cycle."""
        return not self._creates_cycle(task, dependency)

    def _creates_cycle(self, task: Task, dependency: Task) -> bool:
        """Detect circular dependencies using graph traversal."""
        visited = set()
        return self._dfs_cycle_check(dependency, task.id, visited)

    def _dfs_cycle_check(self, current: Task, target_id: TaskId, visited: set) -> bool:
        if current.id == target_id:
            return True
        if current.id in visited:
            return False

        visited.add(current.id)
        for dep in current.dependencies:
            if self._dfs_cycle_check(dep, target_id, visited):
                return True
        return False
```

### Domain Events

**Purpose**: Capture state changes for async processing and decoupling

**Event Types**:
- Entity lifecycle events (Created, Updated, Deleted)
- State transition events (StatusChanged, Completed)
- Business process events (DependencyAdded, AssigneeChanged)

**Example**:
```python
@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: str = None

@dataclass
class TaskCreatedEvent(DomainEvent):
    """Emitted when task is created."""
    task_id: str
    title: str
    assignees: List[str]
    priority: str

@dataclass
class TaskCompletedEvent(DomainEvent):
    """Emitted when task is completed."""
    task_id: str
    completion_summary: str
    completed_by: str
```

**Event Handlers**:
```python
class TaskEventHandler:
    """Handle task-related events."""

    def handle_task_created(self, event: TaskCreatedEvent):
        """Send notifications when task created."""
        # Notify assignees
        # Update project metrics
        # Trigger workflow automation
        pass

    def handle_task_completed(self, event: TaskCompletedEvent):
        """Update parent task progress when subtask completed."""
        # Recalculate parent progress
        # Check if all subtasks done
        # Emit parent completion if ready
        pass
```

---

## Application Layer

### Facades

**Purpose**: Coordinate use cases, manage transactions, provide unified interface

**Characteristics**:
- Transaction boundaries (begin/commit/rollback)
- Use case orchestration
- Event collection and dispatch
- Error handling and mapping

**Example**:
```python
class TaskApplicationFacade:
    """Facade for task operations."""

    def __init__(
        self,
        repository: TaskRepository,
        event_bus: EventBus,
        dependency_service: DependencyManagementService
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.dependency_service = dependency_service

    def create_task(self, dto: TaskCreateDTO) -> TaskResponseDTO:
        """Create task with full transaction management."""
        with self.repository.begin_transaction():
            try:
                # Execute use case
                use_case = CreateTaskUseCase(self.repository, self.dependency_service)
                task, events = use_case.execute(dto)

                # Commit transaction
                self.repository.commit()

                # Publish events (after commit)
                for event in events:
                    self.event_bus.publish(event)

                # Return response DTO
                return TaskResponseDTO.from_entity(task)

            except DomainException as e:
                self.repository.rollback()
                raise ApplicationException(f"Task creation failed: {str(e)}")
```

### Use Cases

**Purpose**: Single business operation, encapsulates specific workflow

**Characteristics**:
- One public method: `execute()`
- Coordinates domain services
- Enforces business rules
- Returns entity + events

**Example**:
```python
class CreateTaskUseCase:
    """Use case for creating a new task."""

    def __init__(
        self,
        repository: TaskRepository,
        dependency_service: DependencyManagementService
    ):
        self.repository = repository
        self.dependency_service = dependency_service

    def execute(self, dto: TaskCreateDTO) -> Tuple[Task, List[DomainEvent]]:
        """Create task with business rule validation."""
        # Validate dependencies
        if dto.dependencies:
            for dep_id in dto.dependencies:
                dep_task = self.repository.find_by_id(dep_id)
                if not dep_task:
                    raise DomainException(f"Dependency {dep_id} not found")

        # Create task entity
        task = Task.create(
            title=dto.title,
            description=dto.description,
            priority=Priority(dto.priority),
            assignees=dto.assignees,
            dependencies=dto.dependencies
        )

        # Persist
        self.repository.save(task)

        # Return entity and events
        return task, task.collect_events()
```

### DTOs (Data Transfer Objects)

**Purpose**: Immutable data containers for layer communication

**Types**:
- Request DTOs (from Interface to Application)
- Response DTOs (from Application to Interface)
- Internal DTOs (within Application layer)

**Example**:
```python
@dataclass(frozen=True)
class TaskCreateDTO:
    """Request DTO for task creation."""
    title: str
    description: str
    priority: str
    assignees: List[str]
    dependencies: Optional[List[str]] = None
    estimated_effort: Optional[str] = None

@dataclass
class TaskResponseDTO:
    """Response DTO for task operations."""
    id: str
    title: str
    status: str
    priority: str
    progress_percentage: int
    assignees: List[str]
    created_at: str

    @classmethod
    def from_entity(cls, task: Task) -> 'TaskResponseDTO':
        """Convert entity to DTO."""
        return cls(
            id=str(task.id),
            title=task.title,
            status=task.status.value,
            priority=task.priority.value,
            progress_percentage=task.calculate_progress(),
            assignees=task.assignees,
            created_at=task.created_at.isoformat()
        )
```

---

## Infrastructure Layer

### Repositories

**Purpose**: Abstract data access, provide entity persistence

**Pattern**: Repository per aggregate root

**Interface** (in Domain):
```python
class TaskRepository(ABC):
    """Abstract repository interface in domain layer."""

    @abstractmethod
    def save(self, task: Task) -> None:
        """Save task entity."""
        pass

    @abstractmethod
    def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID."""
        pass

    @abstractmethod
    def find_by_status(self, status: TaskStatus) -> List[Task]:
        """Find tasks by status."""
        pass

    @abstractmethod
    def delete(self, task_id: TaskId) -> None:
        """Delete task."""
        pass
```

**Implementation** (in Infrastructure):
```python
class SQLAlchemyTaskRepository(TaskRepository):
    """SQLAlchemy implementation of task repository."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, task: Task) -> None:
        """Save task to database."""
        model = self._to_model(task)
        self.session.merge(model)  # INSERT or UPDATE

    def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID."""
        model = self.session.query(TaskModel).filter_by(id=str(task_id)).first()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: TaskModel) -> Task:
        """Convert ORM model to domain entity."""
        return Task(
            id=TaskId.from_string(model.id),
            title=model.title,
            description=model.description,
            status=TaskStatus(model.status),
            priority=Priority(model.priority),
            assignees=json.loads(model.assignees),
            created_at=model.created_at
        )

    def _to_model(self, task: Task) -> TaskModel:
        """Convert domain entity to ORM model."""
        return TaskModel(
            id=str(task.id),
            title=task.title,
            description=task.description,
            status=task.status.value,
            priority=task.priority.value,
            assignees=json.dumps(task.assignees),
            created_at=task.created_at
        )
```

### Repository Best Practices

| Practice | Example | Benefit |
|----------|---------|---------|
| **Interface in Domain** | `TaskRepository(ABC)` in domain | Domain doesn't depend on infrastructure |
| **Implementation in Infrastructure** | `SQLAlchemyTaskRepository` in infra | Swappable implementations |
| **Entity conversion** | `_to_entity()`, `_to_model()` methods | Clean separation ORM ↔ Domain |
| **Query methods** | `find_by_status()`, `find_by_assignee()` | Encapsulate database queries |
| **Transaction management** | `begin_transaction()`, `commit()`, `rollback()` | Consistent transaction handling |

---

## Interface Layer

### MCP Controllers

**Purpose**: Handle MCP protocol requests, validate parameters, coordinate application layer

**Responsibilities**:
- Parameter parsing and type coercion
- Validation (format, required fields)
- DTO construction
- Facade invocation
- Response formatting
- Error handling and mapping

**Example**:
```python
class TaskMCPController:
    """MCP controller for task operations."""

    def __init__(self, facade: TaskApplicationFacade):
        self.facade = facade

    def handle_request(self, action: str, **params):
        """Route request to appropriate handler."""
        if action == "create":
            return self._handle_create(params)
        elif action == "update":
            return self._handle_update(params)
        # ... other actions

    def _handle_create(self, params: dict):
        """Handle task creation."""
        # Validate required parameters
        self._validate_required(params, ["git_branch_id", "title", "assignees"])

        # Parse and coerce types
        assignees = self._parse_array(params.get("assignees"))
        priority = params.get("priority", "medium")

        # Construct DTO
        dto = TaskCreateDTO(
            git_branch_id=params["git_branch_id"],
            title=params["title"],
            description=params.get("description", ""),
            priority=priority,
            assignees=assignees
        )

        try:
            # Call application layer
            response = self.facade.create_task(dto)

            # Format MCP response
            return {
                "success": True,
                "task": response.to_dict(),
                "workflow_guidance": self._generate_guidance(response)
            }
        except ApplicationException as e:
            return {
                "success": False,
                "error": {
                    "message": str(e),
                    "code": "TASK_CREATE_FAILED"
                }
            }
```

---

## Avoiding MRO Conflicts

### Problem: Multiple Inheritance Diamond

**Scenario**: Entity inherits from both `BaseEntity` and `SyncMixin`

```python
# ❌ WRONG - Creates MRO conflict
class Task(BaseEntity, SyncMixin):
    pass

# Both have __init__, Python can't determine order
```

### Solution: Composition over Inheritance

```python
# ✅ CORRECT - Use composition
class Task(BaseEntity):
    def __init__(self, **kwargs):
        super().__init__()
        self.sync_manager = SyncManager()  # Composition

    def sync(self):
        """Delegate to sync manager."""
        self.sync_manager.sync(self)
```

### MRO Resolution Rules

| Pattern | MRO Order | Use When |
|---------|-----------|----------|
| **Single inheritance** | Clear linear order | One parent class |
| **Multiple inheritance** | Left-to-right, depth-first | Mixins with no __init__ conflicts |
| **Composition** | No MRO issues | Complex inheritance hierarchies |

**Best Practice**: Prefer composition for cross-cutting concerns (logging, sync, validation)

---

## Common Patterns

### Pattern: Aggregate Root

**Definition**: Entity that serves as entry point to a cluster of related entities

**Rules**:
- Only aggregate root has repository
- External objects hold references only to aggregate root
- Aggregate enforces invariants across all entities in cluster

**Example**: Task (aggregate root) contains Subtasks (not directly accessible)

### Pattern: Factory

**Purpose**: Encapsulate complex object creation

```python
class TaskFactory:
    """Factory for creating tasks with validation."""

    @staticmethod
    def create_from_dto(dto: TaskCreateDTO) -> Task:
        """Create task with full validation."""
        # Validate business rules
        if len(dto.title) > 200:
            raise ValueError("Title too long")

        # Create value objects
        task_id = TaskId.create()
        priority = Priority(dto.priority)
        status = TaskStatus.TODO

        # Create entity
        return Task(
            id=task_id,
            title=dto.title,
            description=dto.description,
            priority=priority,
            status=status,
            assignees=dto.assignees
        )
```

### Pattern: Specification

**Purpose**: Encapsulate business rules for querying

```python
class TaskSpecification(ABC):
    """Base class for task specifications."""

    @abstractmethod
    def is_satisfied_by(self, task: Task) -> bool:
        pass

class HighPriorityTaskSpec(TaskSpecification):
    """Specification for high priority tasks."""

    def is_satisfied_by(self, task: Task) -> bool:
        return task.priority.value in ["high", "urgent", "critical"]

# Usage
spec = HighPriorityTaskSpec()
high_priority_tasks = [t for t in tasks if spec.is_satisfied_by(t)]
```

---

## Related Documentation
- [Development Workflow Complete](./development-workflow-complete.md)
- [Testing & Infrastructure Complete](./testing-infrastructure-complete.md)
- [Complete Operations Guide](../operations/complete-operations-guide.md)
