# AgentHub System Architecture - Complete Technical Reference

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Purpose**: Single source of truth for AgentHub system architecture covering frontend, backend, API, and MCP tools

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Stack](#architecture-stack)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [API Layer](#api-layer)
6. [MCP Tools System](#mcp-tools-system)
7. [WebSocket v2.0 Protocol](#websocket-v20-protocol)
8. [Authentication & Authorization](#authentication--authorization)
9. [Database Layer](#database-layer)
10. [Context Management](#context-management)
11. [Real-time Synchronization](#real-time-synchronization)
12. [Development Workflow](#development-workflow)
13. [Testing Strategy](#testing-strategy)
14. [Common Patterns](#common-patterns)

---

## System Overview

AgentHub is an enterprise-grade AI agent orchestration platform that enables intelligent task management, multi-agent coordination, and real-time collaboration between humans and AI agents.

**Core Capabilities**:
- Multi-agent task orchestration with 32+ specialized agents
- Real-time WebSocket synchronization (v2.0 protocol)
- 4-tier hierarchical context management (Global → Project → Branch → Task)
- Domain-Driven Design (DDD) architecture
- Keycloak-based authentication with JWT tokens
- PostgreSQL database with SQLAlchemy ORM
- React 19 + TypeScript frontend with React Query caching

---

## Architecture Stack

| Layer | Technology | Purpose | Port |
|-------|------------|---------|------|
| **Frontend** | React 19, TypeScript, Vite | User interface, real-time updates | 3800 |
| **Backend** | Python 3.14, FastAPI, FastMCP | Business logic, API endpoints | 8000 |
| **Database** | PostgreSQL (local), SQLite (fallback) | Data persistence | 5432 |
| **Auth** | Keycloak, JWT tokens | User authentication & authorization | - |
| **WebSocket** | FastAPI WebSocket, v2.0 protocol | Real-time notifications | 8000/ws |
| **Cache** | React Query (TanStack Query) | Frontend data caching | - |
| **Container** | Docker, docker-compose | Development environment | - |

**Data Flow Overview**:
```
User → React Frontend → API/MCP Tools → Backend Facade → Use Case → Repository → Database
                    ↓                                                              ↓
              WebSocket Client ← WebSocket Server ← Event Broadcaster ← Domain Events
                    ↓
            React Query Cache
```

---

## Frontend Architecture

### Technology Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| **Framework** | React 19 | UI rendering, component lifecycle |
| **Language** | TypeScript 5.x | Type safety, IDE support |
| **Build** | Vite | Fast dev server, optimized builds |
| **Styling** | Tailwind CSS | Utility-first CSS framework |
| **UI Components** | shadcn/ui | Accessible, customizable components |
| **State Management** | React Query (TanStack) | Server state, caching, synchronization |
| **WebSocket** | Native WebSocket API | Real-time communication |
| **Routing** | React Router v6 | Client-side navigation |
| **Forms** | React Hook Form | Form validation, submission |

### Directory Structure

```
agenthub-frontend/
├── src/
│   ├── api/                    # API client functions
│   │   ├── projects.ts        # Project CRUD operations
│   │   ├── tasks.ts           # Task CRUD operations
│   │   └── websocket.ts       # WebSocket connection management
│   ├── components/            # React components
│   │   ├── ProjectList/       # Project listing with lazy loading
│   │   ├── LazyTaskList/      # Task list with infinite scroll
│   │   ├── LazySubtaskList/   # Subtask management
│   │   └── ui/                # shadcn/ui components
│   ├── hooks/                 # Custom React hooks
│   │   ├── useRealtimeSync.ts # WebSocket synchronization
│   │   ├── useTaskWebSocket.ts # Task-specific WebSocket
│   │   └── useWebSocketV2.ts  # v2.0 protocol implementation
│   ├── services/              # Business logic services
│   │   ├── WebSocketClient.ts # WebSocket client wrapper
│   │   └── WebSocketAnimationService.ts # Animation timing
│   ├── types/                 # TypeScript type definitions
│   │   ├── index.ts           # Core types (Task, Project, etc.)
│   │   ├── websocket-protocol.ts # v2.0 protocol types
│   │   └── serviceTypes.ts    # Service layer types
│   ├── utils/                 # Utility functions
│   │   ├── responseValidator.ts # WebSocket message validation
│   │   └── queryClient.ts     # React Query configuration
│   ├── pages/                 # Page components
│   │   ├── ProjectsPage.tsx
│   │   ├── TasksPage.tsx
│   │   └── MyAgentsPage.tsx
│   └── App.tsx                # Root component
├── package.json               # Dependencies
└── vite.config.ts             # Vite configuration
```

### Key Architectural Patterns

#### 1. React Query Caching Strategy

**Cache Structure**:
```typescript
// Individual entity caches
['task', taskId, includeContext] → Task object
['project', projectId] → Project object
['branch', branchId] → GitBranch object

// List caches (filtered by parent)
['tasks'] → Task[] (all tasks)
['tasks', branchId] → Task[] (tasks for specific branch)
['projects'] → Project[] (all projects)
['branches', projectId] → GitBranch[] (branches for project)
```

**Cache Invalidation Rules**:
- CREATE operation → Invalidate parent list cache
- UPDATE operation → Update individual + list caches
- DELETE operation → Remove from individual + list caches
- COMPLETE operation → Update individual + list caches (merge strategy)

**Example**:
```typescript
// Task completion: merge minimal payload with existing data
queryClient.setQueryData(['task', taskId, false], (old: Task | undefined) => {
  if (!old) return taskData;
  return { ...old, ...taskData, status: 'done' }; // Merge, don't replace
});
```

#### 2. WebSocket Real-time Synchronization

**Architecture**:
```
WebSocket Server (Backend) → WebSocket Client → useRealtimeSync Hook → React Query Cache → UI Re-render
```

**Flow**:
1. Backend emits WebSocket event (e.g., `task.completed`)
2. `WebSocketClient.ts` receives message, validates payload
3. `useRealtimeSync.ts` processes event type, extracts data
4. React Query cache updated (setQueryData)
5. Components re-render with fresh data

**Key Files**:
- `src/hooks/useRealtimeSync.ts` - Main synchronization logic
- `src/services/WebSocketClient.ts` - Connection management
- `src/utils/responseValidator.ts` - Message validation

#### 3. Lazy Loading & Infinite Scroll

**Pattern**: Virtual scrolling + React Query pagination

**Example** (`LazyTaskListRefactored.tsx`):
```typescript
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: ['tasks', branchId],
  queryFn: ({ pageParam = 0 }) => fetchTasks(branchId, pageParam, 50),
  getNextPageParam: (lastPage, pages) => {
    return lastPage.length === 50 ? pages.length : undefined;
  }
});
```

**Benefits**:
- Loads 50 items at a time
- Fetches next page when user scrolls to bottom
- Reduces initial load time
- Improves performance for large lists

#### 4. Type Safety with TypeScript

**Type Hierarchy**:
```typescript
// Domain types (match backend entities)
interface Task {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done' | 'blocked';
  priority: 'low' | 'medium' | 'high' | 'urgent' | 'critical';
  git_branch_id: string;
  assignees: string[];
  created_at: string;
  updated_at: string;
  // ... other fields
}

// WebSocket payload types (minimal for performance)
interface TaskCompletePayload {
  id: string;
  title: string;
  status: 'done';
  completion_summary?: string;
  testing_notes?: string;
  completed_at?: string;
}
```

---

## Backend Architecture

### Domain-Driven Design (DDD) Structure

**4-Layer Architecture**:

```
agenthub_main/src/fastmcp/task_management/
├── domain/                     # Business rules (no dependencies)
│   ├── entities/              # Core business objects
│   │   ├── task.py           # Task aggregate root
│   │   ├── subtask.py        # Subtask entity
│   │   ├── project.py        # Project entity
│   │   └── git_branch.py     # GitBranch entity
│   ├── value_objects/         # Immutable values
│   │   ├── task_id.py        # UUID wrapper
│   │   └── priority.py       # Priority enum
│   └── repositories/          # Repository interfaces (abstract)
│       └── task_repository.py
├── application/               # Use cases & orchestration
│   ├── use_cases/            # Business operations
│   │   ├── create_task.py    # Task creation logic
│   │   ├── update_task.py    # Task update logic
│   │   └── complete_task.py  # Task completion logic
│   ├── facades/              # Simplified API layer
│   │   ├── task_application_facade.py
│   │   └── subtask_application_facade.py
│   └── services/             # Application services
│       ├── websocket_notification_service.py
│       └── websocket_payload_builder.py
├── infrastructure/            # External integrations
│   ├── repositories/         # Concrete repository implementations
│   │   └── sqlalchemy_task_repository.py
│   └── persistence/          # Database models
│       └── models.py         # SQLAlchemy ORM models
└── interface/                # API endpoints (FastAPI routes)
    └── routes/
        ├── task_routes.py
        └── websocket_routes.py
```

**Key Principles**:
- **Domain Layer**: Pure business logic, no framework dependencies
- **Application Layer**: Orchestrates use cases, calls domain + infrastructure
- **Infrastructure Layer**: Database, external APIs, WebSocket
- **Interface Layer**: HTTP/WebSocket endpoints, request/response mapping

### Use Case Pattern

**Structure**:
```python
# application/use_cases/create_task.py
class CreateTaskUseCase:
    def __init__(self, repository: TaskRepository, websocket_service: WebSocketService):
        self.repository = repository
        self.websocket_service = websocket_service

    async def execute(self, request: CreateTaskRequest) -> Task:
        # 1. Validate business rules
        # 2. Create domain entity
        task = Task.create(title=request.title, ...)

        # 3. Persist via repository
        await self.repository.save(task)

        # 4. Emit domain events
        await self.websocket_service.broadcast_task_created(task)

        return task
```

**Benefits**:
- Single Responsibility (one use case per operation)
- Testable (mock dependencies)
- Business logic isolated from infrastructure

### Repository Pattern

**Interface** (domain layer):
```python
# domain/repositories/task_repository.py
class TaskRepository(ABC):
    @abstractmethod
    async def save(self, task: Task) -> None: pass

    @abstractmethod
    async def find_by_id(self, task_id: TaskId) -> Optional[Task]: pass

    @abstractmethod
    async def find_by_branch(self, branch_id: str) -> List[Task]: pass
```

**Implementation** (infrastructure layer):
```python
# infrastructure/repositories/sqlalchemy_task_repository.py
class SQLAlchemyTaskRepository(TaskRepository):
    async def save(self, task: Task) -> None:
        # Map domain entity → SQLAlchemy model
        model = TaskModel.from_entity(task)
        self.session.add(model)
        await self.session.commit()
```

**Benefits**:
- Domain layer doesn't know about SQLAlchemy
- Easy to swap database (PostgreSQL ↔ SQLite)
- Testable with in-memory repository

---

## API Layer

### REST Endpoints

**Base URL**: `http://localhost:8000`

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/api/projects` | GET | List all projects | ✅ |
| `/api/projects` | POST | Create project | ✅ |
| `/api/projects/{id}` | GET | Get project details | ✅ |
| `/api/projects/{id}` | PUT | Update project | ✅ |
| `/api/projects/{id}` | DELETE | Delete project | ✅ |
| `/api/branches` | GET | List branches | ✅ |
| `/api/branches` | POST | Create branch | ✅ |
| `/api/tasks` | GET | List tasks (filtered by branch) | ✅ |
| `/api/tasks` | POST | Create task | ✅ |
| `/api/tasks/{id}` | GET | Get task details | ✅ |
| `/api/tasks/{id}/complete` | POST | Complete task | ✅ |
| `/api/subtasks` | GET | List subtasks (filtered by task) | ✅ |
| `/api/subtasks` | POST | Create subtask | ✅ |

**Request/Response Format**:
```typescript
// POST /api/tasks
Request: {
  title: string;
  description?: string;
  git_branch_id: string;
  assignees: string[];
  priority?: 'low' | 'medium' | 'high' | 'urgent' | 'critical';
}

Response: {
  success: boolean;
  data: {
    task: Task;
    message: string;
  };
  meta: {
    persisted: boolean;
    id: string;
    timestamp: string;
    operation: 'create';
  };
}
```

### MCP Tools Integration

**MCP Server**: `agenthub_http`
**Location**: `agenthub_main/src/fastmcp/server/mcp_entry_point.py`

**Tool Categories** (15 total):

| Category | Tools | Purpose |
|----------|-------|---------|
| **Task Management** | manage_task | CRUD operations, search, dependencies, AI planning |
| **Subtask Management** | manage_subtask | Subtask CRUD, progress tracking, completion |
| **Project Management** | manage_project | Project lifecycle, health checks, validation |
| **Branch Management** | manage_git_branch | Branch CRUD, agent assignment, statistics |
| **Context Management** | manage_context | 4-tier hierarchy, inheritance, delegation |
| **Agent Management** | manage_agent | Register, assign, update agents |

**Example MCP Tool Call**:
```python
# From Claude Code or CLI
response = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="uuid-here",
    title="Implement authentication",
    assignees="coding-agent",
    priority="high",
    description="Add JWT token validation"
)
```

**MCP Tool Architecture**:
```
MCP Tool → FastMCP Server → Application Facade → Use Case → Repository → Database
                                                    ↓
                                          WebSocket Broadcast
```

---

## MCP Tools System

### Tool: manage_task

**Actions** (15 total):

| Action | Required Parameters | Purpose |
|--------|---------------------|---------|
| `create` | git_branch_id, title, assignees | Create new task |
| `update` | task_id | Update task fields |
| `get` | task_id | Retrieve task details |
| `delete` | task_id | Remove task |
| `complete` | task_id, completion_summary | Mark task done |
| `list` | git_branch_id (optional) | List tasks with filters |
| `search` | query | Full-text search |
| `next` | git_branch_id | AI-recommended next task |
| `add_dependency` | task_id, dependency_id | Create task dependency |

**Workflow Example**:
```python
# 1. Create task
task = manage_task(
    action="create",
    git_branch_id="e8ea1bf5-fc3c-41ac-8167-0c7134795632",
    title="Fix auth bug",
    assignees="coding-agent,security-auditor-agent",
    priority="urgent",
    details="Fix validation in src/auth/login.ts:45-52"
)

# 2. Update progress
manage_task(
    action="update",
    task_id=task.id,
    status="in_progress",
    progress_percentage=50
)

# 3. Complete task
manage_task(
    action="complete",
    task_id=task.id,
    completion_summary="Fixed token validation logic",
    testing_notes="Added unit tests, manual testing passed"
)
```

### Tool: manage_subtask

**Key Features**:
- Auto-inherits assignees from parent task
- Progress tracking with timestamped history
- progress_percentage auto-maps to status (0=todo, 1-99=in_progress, 100=done)
- Parent task progress auto-calculated from subtask completion

**Example**:
```python
# Create subtask (inherits assignees automatically)
subtask = manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Design authentication schema",
    progress_notes="Starting work on user table design"
)

# Update with progress
manage_subtask(
    action="update",
    task_id=parent_task_id,
    subtask_id=subtask.id,
    progress_percentage=75,
    progress_notes="Schema designed, adding indexes"
)

# Complete subtask (updates parent progress automatically)
manage_subtask(
    action="complete",
    task_id=parent_task_id,
    subtask_id=subtask.id,
    completion_summary="Schema completed with compound indexes",
    insights_found="Discovered need for email index"
)
```

### Tool: manage_context

**4-Tier Hierarchy**:
```
GLOBAL (per user)
  ↓ inherits
PROJECT (per project)
  ↓ inherits
BRANCH (per git branch)
  ↓ inherits
TASK (per task)
```

**Actions**:

| Action | Purpose | Example |
|--------|---------|---------|
| `create` | Create context at any level | Organization-wide settings |
| `get` | Retrieve context for level | Get project context |
| `update` | Modify context data | Add feature flags |
| `resolve` | Get full inheritance chain | Task context + all parents |
| `delegate` | Move context between levels | Promote branch setting to project |

**Inheritance Example**:
```python
# 1. Create global context (user-level)
manage_context(
    action="create",
    level="global",
    context_id="user-123",
    data=json.dumps({
        "org_settings": {"security_level": "high"},
        "coding_standards": ["PEP8", "ESLint"]
    })
)

# 2. Create project context (inherits global)
manage_context(
    action="create",
    level="project",
    context_id=project_id,
    data=json.dumps({
        "tech_stack": ["React", "Python", "PostgreSQL"]
    })
)

# 3. Resolve task context (gets full chain)
resolved = manage_context(
    action="resolve",
    level="task",
    context_id=task_id,
    include_inherited="true"
)
# Returns: global + project + branch + task merged data
```

---

## WebSocket v2.0 Protocol

**Connection URL**: `ws://localhost:8000/ws`

### Message Structure

**Generic Format**:
```typescript
interface WebSocketMessage {
  event: string;                    // Event type (e.g., "task.created")
  data: Record<string, any>;        // Payload data
  metadata?: {
    source: 'user' | 'system';      // Who triggered the event
    timestamp: string;               // ISO 8601 timestamp
    operation: string;               // CRUD operation type
  };
}
```

### Event Types

| Event | Trigger | Payload Type | Purpose |
|-------|---------|--------------|---------|
| `task.created` | Task created | TaskCreatePayload | New task notification |
| `task.updated` | Task updated | TaskUpdatePayload | Task field changes |
| `task.completed` | Task completed | TaskCompletePayload | Task completion |
| `task.deleted` | Task deleted | TaskDeletePayload | Task removal |
| `subtask.created` | Subtask created | SubtaskCreatePayload | New subtask |
| `subtask.updated` | Subtask updated | SubtaskUpdatePayload | Subtask progress |
| `subtask.completed` | Subtask completed | SubtaskCompletePayload | Subtask done |
| `project.created` | Project created | ProjectPayload | New project |
| `branch.created` | Branch created | BranchPayload | New branch |

### Payload Examples

**Task Completion** (Minimal Payload):
```typescript
{
  "event": "task.completed",
  "data": {
    "id": "4e2c02fa-3576-4dc8-a381-f80ded0c7003",
    "title": "Test Task Lambda",
    "status": "done",
    "completion_summary": "Task completed successfully",
    "testing_notes": "All tests passing",
    "completed_at": "2025-11-07T21:49:57.509011+00:00"
  },
  "metadata": {
    "source": "system",
    "timestamp": "2025-11-07T21:49:57.509011+00:00",
    "operation": "complete"
  }
}
```

**Why Minimal?** - Reduces WebSocket message size (typically <500 bytes vs 2KB+), improves real-time performance

### Frontend WebSocket Handling

**Connection Management** (`src/services/WebSocketClient.ts`):
```typescript
class WebSocketClient {
  connect(url: string, token: string): void {
    this.ws = new WebSocket(`${url}?token=${token}`);
    this.ws.onmessage = (event) => this.handleMessage(event);
    this.ws.onerror = (error) => this.handleError(error);
    this.ws.onclose = () => this.handleClose();
  }

  handleMessage(event: MessageEvent): void {
    const message = JSON.parse(event.data);

    // Validate payload
    const validation = validateTask(message.data, message.event);
    if (!validation.isValid) {
      console.error('Validation failed:', validation.errors);
      return;
    }

    // Emit to subscribers
    this.emit(message.event, message.data);
  }
}
```

**Synchronization Hook** (`src/hooks/useRealtimeSync.ts`):
```typescript
function useRealtimeSync() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const client = WebSocketClient.getInstance();

    // Subscribe to task completion events
    client.on('task.completed', (data: TaskCompletePayload) => {
      const taskId = data.id;

      // Get git_branch_id from existing cache
      const tasks = queryClient.getQueryData<Task[]>(['tasks']);
      const existingTask = tasks?.find(t => t.id === taskId);
      const branchId = existingTask?.git_branch_id;

      // Update caches (merge, don't replace)
      queryClient.setQueryData(['task', taskId, false], (old: Task | undefined) => {
        if (!old) return { ...existingTask, ...data, status: 'done' };
        return { ...old, ...data, status: 'done' };
      });

      if (branchId) {
        queryClient.setQueryData<Task[]>(['tasks', branchId], (old) => {
          if (!old) return old;
          return old.map(t => t.id === taskId ? { ...t, ...data, status: 'done' } : t);
        });
      }
    });

    return () => client.disconnect();
  }, [queryClient]);
}
```

**Key Pattern**: Merge minimal payload with existing cached data to preserve fields like `git_branch_id`, `created_at`, `updated_at` that aren't in completion payload.

---

## Authentication & Authorization

### Keycloak Integration

**Source of Truth**: Keycloak manages all user authentication

**Flow**:
```
User Login → Keycloak → JWT Token → Frontend stores token → Backend validates token on each request
```

**Configuration**:
```python
# Backend: agenthub_main/src/fastmcp/server/config.py
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
```

### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "preferred_username": "username",
  "realm_access": {
    "roles": ["user", "admin"]
  },
  "exp": 1699999999,
  "iat": 1699999000
}
```

**Token Usage**:
```typescript
// Frontend: Add token to all API requests
const response = await fetch('/api/tasks', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

// Backend: Validate token on each request
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, KEYCLOAK_PUBLIC_KEY, algorithms=["RS256"])
    return payload["sub"]  # User UUID
```

### Multi-tenant Isolation

**Every entity linked to user**:
```python
# All queries filtered by user_id automatically
tasks = await repository.find_by_branch_and_user(branch_id, user_id)
projects = await repository.find_by_user(user_id)
```

**Database Level**:
```sql
-- User isolation at query level
SELECT * FROM tasks WHERE git_branch_id = ? AND user_id = ?;
```

---

## Database Layer

### ORM Models (SQLAlchemy)

**Location**: `agenthub_main/src/fastmcp/task_management/infrastructure/persistence/models.py`

**Key Models**:

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `TaskModel` | Task entity | id, title, status, priority, git_branch_id, user_id, assignees, created_at, updated_at |
| `SubtaskModel` | Subtask entity | id, task_id, title, status, progress_percentage, assignees, created_at |
| `ProjectModel` | Project entity | id, name, description, user_id, created_at |
| `GitBranchModel` | Git branch | id, project_id, git_branch_name, user_id, created_at |
| `ContextModel` | Context data | id, level, context_id, data (JSONB), user_id |

**Example ORM Model**:
```python
class TaskModel(Base):
    __tablename__ = 'tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.TODO)
    priority = Column(Enum(Priority), nullable=False, default=Priority.MEDIUM)
    git_branch_id = Column(UUID(as_uuid=True), ForeignKey('git_branches.id'), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    assignees = Column(ARRAY(String), nullable=False, default=[])
    progress_percentage = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    subtasks = relationship("SubtaskModel", back_populates="task", cascade="all, delete-orphan")
    git_branch = relationship("GitBranchModel", back_populates="tasks")
```

### Database Migrations

**Tool**: Alembic (SQLAlchemy migrations)

**Commands**:
```bash
# Generate migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Migration Files**: `agenthub_main/alembic/versions/`

### Source of Truth Hierarchy

```
1. PROMPT INPUT (User requirements) ↓
2. ORM MODEL (Domain definitions) ↓
3. DATABASE (Actual structure) ↓
4. TESTS (Verify behavior) ↓
5. CODE (Implementation)
```

**Rule**: When test fails, check ORM model first. Update code/tests to match ORM, never add compatibility layers.

---

## Context Management

### 4-Tier Hierarchy

```
GLOBAL (user-123)
  ├── security_policies: {...}
  ├── coding_standards: {...}
  └── workflow_templates: {...}
       ↓ inherits
PROJECT (project-uuid)
  ├── tech_stack: ["React", "Python"]
  ├── build_config: {...}
  └── project_standards: {...}
       ↓ inherits
BRANCH (branch-uuid)
  ├── feature_flags: {...}
  ├── branch_metadata: {...}
  └── sprint_info: {...}
       ↓ inherits
TASK (task-uuid)
  ├── task_data: {...}
  ├── progress: {...}
  └── completion_details: {...}
```

### Context Resolution

**resolve Action** - Merges entire hierarchy:
```python
resolved = manage_context(
    action="resolve",
    level="task",
    context_id=task_id,
    include_inherited="true"
)

# Returns merged context:
{
    "_inheritance": {
        "chain": ["global", "project", "branch", "task"],
        "resolved_at": "2025-11-07T19:07:48Z",
        "inheritance_depth": 4
    },
    # Global data
    "security_policies": {...},
    # Project data
    "tech_stack": [...],
    # Branch data
    "feature_flags": {...},
    # Task data
    "task_data": {...}
}
```

### Context Delegation

**Move context between levels**:
```python
# Promote branch-level setting to project-level
manage_context(
    action="delegate",
    level="branch",
    context_id=branch_id,
    delegate_to="project",
    delegate_data=json.dumps({
        "feature_flag_x": true  # Promote this setting
    }),
    delegation_reason="Feature flag proven successful, making project-wide"
)
```

---

## Real-time Synchronization

### Complete Flow

```
Backend Operation (task completion)
    ↓
Domain Event Emitted
    ↓
WebSocket Notification Service
    ↓
Build Minimal Payload (WebSocketPayloadBuilder)
    ↓
Broadcast to Connected Clients
    ↓
Frontend WebSocket Client Receives Message
    ↓
Validate Payload (responseValidator.ts)
    ↓
useRealtimeSync Hook Processes Event
    ↓
Update React Query Cache (merge strategy)
    ↓
React Components Re-render
    ↓
UI Updated (150ms animation delay)
```

### Key Files

| Layer | File | Responsibility |
|-------|------|----------------|
| **Backend** | `websocket_payload_builder.py` | Build minimal payloads |
| **Backend** | `websocket_notification_service.py` | Broadcast events |
| **Backend** | `websocket_routes.py` | WebSocket endpoint |
| **Frontend** | `WebSocketClient.ts` | Connection management |
| **Frontend** | `useRealtimeSync.ts` | Event processing, cache updates |
| **Frontend** | `responseValidator.ts` | Payload validation |
| **Frontend** | `WebSocketAnimationService.ts` | Animation timing |

### Cache Update Strategy

**Problem**: Minimal completion payload missing fields like `git_branch_id`, `created_at`

**Solution**: Merge minimal payload with existing cached data

```typescript
// ✅ CORRECT: Merge strategy
const existingTask = queryClient.getQueryData<Task>(['task', taskId, false]);
queryClient.setQueryData(['task', taskId, false], {
  ...existingTask,        // Preserve existing fields
  ...minimalPayload,      // Override with new data
  status: 'done'          // Explicit status update
});

// ❌ WRONG: Replace strategy (loses fields)
queryClient.setQueryData(['task', taskId, false], minimalPayload);
```

### Duplicate Notification Prevention

**Pattern**: Metadata-based filtering

```typescript
// Backend marks automatic updates
metadata: {
  source: 'system',  // vs 'user'
  operation: 'update'
}

// Frontend filters system-triggered updates
if (message.metadata?.source === 'system') {
  // Don't show toast (already shown when user initiated action)
  return;
}
```

---

## Development Workflow

### Local Setup

**Start Backend**:
```bash
cd agenthub_main
source .venv/bin/activate
python -m fastmcp.server.mcp_entry_point
# Backend running on http://localhost:8000
```

**Start Frontend**:
```bash
cd agenthub-frontend
npm install
npm run dev
# Frontend running on http://localhost:3800
```

**Docker Environment**:
```bash
./docker-system/docker-menu.sh
# Select option:
# - S: Start services
# - R: Restart (required after code changes)
# - D: Stop services
```

### Code Change Workflow

**Frontend Changes**:
1. Edit files in `agenthub-frontend/src/`
2. Vite HMR automatically reloads browser
3. Test changes immediately

**Backend Changes**:
1. Edit files in `agenthub_main/src/`
2. Kill backend process (Ctrl+C)
3. Restart: `python -m fastmcp.server.mcp_entry_point`
4. **OR** use Docker menu: `echo "R" | ./docker-system/docker-menu.sh`

**Why?** Python caches imported modules in memory - must restart process to load new code.

### Environment Variables

**File**: `.env` (project root)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agenthub

# Keycloak
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=agenthub-client
KEYCLOAK_CLIENT_SECRET=secret

# WebSocket
WEBSOCKET_URL=ws://localhost:8000/ws

# Development
DEBUG=True
LOG_LEVEL=INFO
```

### Git Workflow

**Branch Naming**:
- Feature: `feature/description`
- Fix: `fix/description`
- Docs: `docs/description`

**Commit Format** (Conventional Commits):
```bash
feat(auth): add JWT token validation
fix(ui): resolve task status update bug
docs: update system architecture documentation
test: add WebSocket integration tests
```

---

## Testing Strategy

### Test Structure

```
agenthub_main/src/tests/
├── unit/                          # Unit tests (isolated)
│   ├── domain/                   # Domain entity tests
│   ├── application/              # Use case tests
│   └── infrastructure/           # Repository tests
├── integration/                   # Integration tests (with DB)
│   ├── api/                      # API endpoint tests
│   └── websocket/                # WebSocket tests
├── e2e/                          # End-to-end tests
│   └── workflows/                # Complete user workflows
└── performance/                   # Performance tests
    └── load_tests/               # Load testing scenarios
```

### Frontend Tests

```
agenthub-frontend/src/tests/
├── components/                    # Component tests
│   ├── ProjectList.test.tsx
│   └── LazyTaskList.test.tsx
├── hooks/                        # Hook tests
│   ├── useRealtimeSync.test.tsx
│   └── useTaskWebSocket.test.tsx
├── services/                     # Service tests
│   └── WebSocketClient.test.ts
└── e2e/                          # E2E tests
    └── websocket-protocol-v2.test.tsx
```

### Test Commands

```bash
# Backend tests
cd agenthub_main
pytest src/tests/unit/              # Unit tests only
pytest src/tests/integration/       # Integration tests
pytest src/tests/                   # All tests
pytest -v -s                        # Verbose with output

# Frontend tests
cd agenthub-frontend
npm test                            # Run all tests
npm test -- --watch                 # Watch mode
npm test -- LazyTaskList            # Specific test file
```

### TDD Workflow Example

**WebSocket Completion Fix**:
1. Write failing test (`test_task_completion_updates_cache.tsx`)
2. Run test → ❌ Fails
3. Implement fix in `useRealtimeSync.ts`
4. Run test → ✅ Passes
5. Verify manually in browser
6. Commit with test + fix

---

## Common Patterns

### 1. Creating a New Task

**Frontend** (via API):
```typescript
const createTask = async (data: CreateTaskRequest) => {
  const response = await fetch('http://localhost:8000/api/tasks', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  return response.json();
};
```

**Via MCP Tool**:
```python
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Task title",
    assignees="coding-agent",
    priority="high"
)
```

**Backend Flow**:
```
TaskRoutes → TaskApplicationFacade → CreateTaskUseCase → TaskRepository → Database
                                              ↓
                                   WebSocketNotificationService
                                              ↓
                                        Frontend Cache
```

### 2. Real-time Status Update

**Backend** (after task completion):
```python
# 1. Update database
await repository.update_status(task_id, TaskStatus.DONE)

# 2. Build minimal payload
payload = WebSocketPayloadBuilder.build_lightweight_payload(task)

# 3. Broadcast event
await websocket_service.broadcast(
    event="task.completed",
    data=payload,
    metadata={"source": "system", "operation": "complete"}
)
```

**Frontend** (in useRealtimeSync.ts):
```typescript
client.on('task.completed', (data: TaskCompletePayload) => {
  // 1. Get existing task from cache
  const tasks = queryClient.getQueryData<Task[]>(['tasks']);
  const existingTask = tasks?.find(t => t.id === data.id);

  // 2. Merge minimal payload with existing data
  queryClient.setQueryData(['task', data.id, false], {
    ...existingTask,
    ...data,
    status: 'done'
  });

  // 3. Update list cache
  if (existingTask?.git_branch_id) {
    queryClient.setQueryData(['tasks', existingTask.git_branch_id], (old) =>
      old?.map(t => t.id === data.id ? { ...t, ...data, status: 'done' } : t)
    );
  }
});
```

### 3. Context Inheritance

**Setup hierarchy**:
```python
# 1. Global context
manage_context(action="create", level="global", context_id=user_id,
    data=json.dumps({"security_level": "high"}))

# 2. Project context (inherits global)
manage_context(action="create", level="project", context_id=project_id,
    data=json.dumps({"tech_stack": ["React"]}))

# 3. Resolve task context (gets full chain)
context = manage_context(action="resolve", level="task", context_id=task_id,
    include_inherited="true")
# Returns: {"security_level": "high", "tech_stack": ["React"], ...}
```

### 4. Agent Assignment

**Task with multiple agents**:
```python
task = manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Security audit",
    assignees="security-auditor-agent,coding-agent",  # Multiple agents
    priority="critical"
)

# Subtasks automatically inherit agents
subtask = manage_subtask(
    action="create",
    task_id=task.id,
    title="Review authentication code"
    # assignees automatically set to ["security-auditor-agent", "coding-agent"]
)
```

---

## Quick Reference

### Key Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3800 | http://localhost:3800 |
| Backend API | 8000 | http://localhost:8000 |
| WebSocket | 8000 | ws://localhost:8000/ws |
| PostgreSQL | 5432 | postgresql://localhost:5432 |

### Key Directories

| Path | Purpose |
|------|---------|
| `agenthub-frontend/src/` | Frontend React code |
| `agenthub_main/src/fastmcp/` | Backend Python code |
| `agenthub_main/src/tests/` | Backend tests |
| `agenthub-frontend/src/tests/` | Frontend tests |
| `ai_docs/` | Documentation |
| `.env` | Environment variables |

### Common Commands

```bash
# Start backend
python -m fastmcp.server.mcp_entry_point

# Start frontend
npm run dev

# Run backend tests
pytest src/tests/

# Run frontend tests
npm test

# Docker restart (after code changes)
echo "R" | ./docker-system/docker-menu.sh

# Check backend logs
tail -f logs/backend.log
```

---

## Additional Resources

- **Main Rules**: `CLAUDE.md` - Complete agent instructions
- **Local Rules**: `CLAUDE.local.md` - Environment-specific configuration
- **WebSocket v2.0 Fix**: `ai_docs/reports-status/websocket-v2-comprehensive-fix-2025-11-07.md`
- **MCP Validation**: `ai_docs/reports-status/mcp-tools-extended-validation-2025-11-07.md`
- **API Documentation**: `ai_docs/api-integration/`
- **Testing Documentation**: `ai_docs/testing-qa/`

---

**Document Status**: ✅ Complete
**Last Validated**: 2025-11-07
**Validation Results**: 100% MCP tools operational, WebSocket v2.0 working, all tests passing
