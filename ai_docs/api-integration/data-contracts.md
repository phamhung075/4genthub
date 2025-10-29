# Layer-to-Layer Communication Data Contracts

**Version**: 1.0
**Last Updated**: 2025-10-29
**Status**: Active Testing Phase

## Table of Contents
1. [Overview](#overview)
2. [Communication Architecture](#communication-architecture)
3. [Data Contract Maps](#data-contract-maps)
4. [Known Issues & Validation Rules](#known-issues--validation-rules)
5. [Testing Strategy](#testing-strategy)

---

## Overview

This document maps the complete data contracts across all communication layers in the agenthub system:
- **Backend (Python/FastAPI)** → DTOs/Response Models
- **REST API** → HTTP JSON Responses
- **WebSocket** → Real-time message protocol v2.0
- **Frontend (TypeScript/React)** → Type Definitions

**Critical Purpose**: Ensure NO NULL/undefined properties are transmitted across layers unless explicitly optional.

---

## Communication Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Frontend Layer (React/TypeScript)                        │
│  - Port: 3800                                             │
│  - Types: /agenthub-frontend/src/types/                   │
│  - WebSocket Client: /hooks/useWebSocketV2.ts            │
└────────────────────┬─────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   REST API    WebSocket v2.0   HTTP
   (fetch)     (ws://)          Headers
        │            │            │
        └────────────┼────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│  Backend Layer (Python/FastAPI/FastMCP)                   │
│  - Port: 8000                                             │
│  - DTOs: /agenthub_main/src/fastmcp/.../dtos/            │
│  - WebSocket Server: .../websocket/context_notifications.py│
│  - ORM: SQLAlchemy with PostgreSQL                        │
└───────────────────────────────────────────────────────────┘
```

---

## Data Contract Maps

### 1. Task Entity Contracts

#### Backend DTO: `TaskResponse`
**File**: `agenthub_main/src/fastmcp/task_management/application/dtos/task/task_response.py`

```python
@dataclass
class TaskResponse:
    # Required Fields (MUST NEVER BE NULL)
    id: str                                    # UUID
    title: str                                 # Max 200 chars
    description: str                           # Max 2000 chars (ORM model source of truth)
    status: str                                # Enum: todo|in_progress|blocked|review|testing|done|cancelled
    priority: str                              # Enum: low|medium|high|urgent|critical
    details: str                               # Formatted progress_history text
    estimated_effort: str                      # Human readable: "2 hours", "3 days"
    assignees: List[str]                       # Always list, @ prefix required
    labels: List[str]                          # Always list (may be empty)
    dependencies: List[str]                    # Always list of task IDs
    subtasks: List[Dict[str, Any]]             # Always list of subtask dicts

    # Computed/Derived Fields
    progress_percentage: int = 0               # 0-100, default 0 (NOT NULL)
    progress_count: int = 0                    # Number of progress entries
    subtask_count: int = 0                     # @property derived from len(subtasks)
    completed_subtasks: int = 0                # Count of done subtasks

    # Optional Fields (May be NULL)
    due_date: Optional[str]                    # ISO 8601 format
    created_at: Optional[datetime]             # Auto-generated
    updated_at: Optional[datetime]             # Auto-updated
    git_branch_id: Optional[str]               # Links to git_branch
    project_id: Optional[str]                  # Fetched via repository join
    context_id: Optional[str]                  # Task context identifier
    context_data: Optional[Dict[str, Any]]     # Full context object
    dependency_relationships: Optional[DependencyRelationships]  # Enhanced dependency info
    progress_history: Optional[Dict[str, Any]] # Full progress history structure
```

#### Frontend Type: `TaskSummary` & Full `Task`
**Files**:
- `agenthub-frontend/src/types/taskTypes.ts` (TaskSummary)
- `agenthub-frontend/src/types/api.types.ts` (Full Task response)

```typescript
// Lightweight list view type
export interface TaskSummary {
  id: string;                     // UUID - REQUIRED
  title: string;                  // REQUIRED
  status: string;                 // REQUIRED
  priority: string;               // REQUIRED
  assignees?: string[];           // Optional BUT if present MUST be array
  has_dependencies: boolean;      // REQUIRED
  has_context: boolean;           // REQUIRED
  created_at?: string;            // ISO 8601
  updated_at?: string;            // ISO 8601
  subtask_count?: number;         // Optional number (NOT null)
  completed_subtasks?: number;    // Optional number (NOT null)
}

// Full task type (matches TaskResponse.to_dict())
export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;             // Union type
  priority: TaskPriority;         // Union type
  details: string;
  estimatedEffort: string;
  assignees: string[];            // NEVER null, always array
  labels: string[];               // NEVER null, always array
  dependencies: string[];         // NEVER null, always array
  subtasks: any[];                // NEVER null, always array
  dueDate: string | null;         // Explicitly nullable
  created_at: string | null;
  updated_at: string | null;
  git_branch_id: string | null;
  project_id: string | null;
  context_id: string | null;
  context_data: Record<string, any> | null;
  dependency_relationships: any | null;
  progress_percentage: number;    // NEVER null, default 0
  progress_history: Record<string, any> | null;
  progress_count: number;         // NEVER null, default 0
  subtask_count: number;          // NEVER null (computed property)
  completed_subtasks: number;     // NEVER null, default 0
}
```

#### REST API Contract: GET /api/v2/tasks/{task_id}
**Response Format**:
```json
{
  "id": "uuid-string",
  "title": "string",
  "description": "string",
  "status": "todo|in_progress|done|...",
  "priority": "low|medium|high|urgent|critical",
  "details": "string (formatted progress history)",
  "estimatedEffort": "string",
  "assignees": ["@agent-1", "@agent-2"],
  "labels": [],
  "dependencies": [],
  "subtasks": [],
  "dueDate": "2025-10-29" | null,
  "created_at": "2025-10-29T10:00:00Z",
  "updated_at": "2025-10-29T10:00:00Z",
  "git_branch_id": "uuid-string" | null,
  "project_id": "uuid-string" | null,
  "context_id": "uuid-string" | null,
  "context_data": {} | null,
  "dependency_relationships": {} | null,
  "progress_percentage": 0,
  "progress_history": {},
  "progress_count": 0,
  "subtask_count": 0,
  "completed_subtasks": 0
}
```

**CRITICAL VALIDATION RULES**:
- `assignees` MUST be array, NEVER null or undefined
- `labels`, `dependencies`, `subtasks` MUST be arrays (may be empty [])
- `progress_percentage`, `progress_count`, `subtask_count`, `completed_subtasks` MUST be numbers, NEVER null
- `description` max length: 2000 characters (ORM model constraint)
- All UUID fields validated as proper UUID format

---

### 2. WebSocket Message Contracts

#### WebSocket Protocol v2.0 Message Structure
**File**: `agenthub-frontend/src/types/websocketTypes.ts`

```typescript
export interface WSMessage {
  id: string;                              // Message UUID
  version: '2.0';                          // ONLY v2.0 supported
  type: 'update' | 'bulk' | 'sync' | 'heartbeat' | 'error';
  timestamp: string;                       // ISO 8601
  sequence: number;                        // Message sequence number

  payload: {
    entity: string;                        // 'task' | 'subtask' | 'branch' | 'project'
    action: string;                        // 'created' | 'updated' | 'deleted'
    data: {
      id?: string;                         // Direct data ID access
      primary: { id?: string; [key: string]: any } | any[];  // Main entity data
      cascade?: {                          // Related entity updates
        branches?: any[];
        tasks?: any[];
        projects?: any[];
        subtasks?: any[];
        contexts?: any[];
      };
      [key: string]: any;
    };
  };

  metadata: {
    source: 'mcp-ai' | 'user' | 'system';
    userId?: string;
    sessionId?: string;
    correlationId?: string;
    batchId?: string;
    entity_type?: string;
    entity_id?: string;
    event_type?: string;
    task_title?: string;                   // Task-specific metadata
    parent_task_title?: string;
    subtask_title?: string;
    branch_title?: string;
    parent_branch_id?: string;
  };
}
```

#### WebSocket Backend Implementation
**File**: `agenthub_main/src/fastmcp/task_management/infrastructure/websocket/context_notifications.py`

```python
@dataclass
class ContextEvent:
    event_type: EventType                  # Enum: CREATED|UPDATED|DELETED|etc.
    level: str                             # 'global'|'user'|'project'|'branch'|'task'
    context_id: str                        # Context UUID
    user_id: str                           # User UUID
    timestamp: datetime                    # UTC timestamp
    data: Optional[Dict[str, Any]]         # Event payload data
    metadata: Dict[str, Any]               # Additional metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type.value,
            'level': self.level,
            'context_id': self.context_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }
```

**WebSocket Endpoint**: `ws://localhost:8000/ws/context/{client_id}`

**CRITICAL VALIDATION RULES**:
- All WebSocket messages MUST conform to v2.0 protocol
- `payload.data.primary` MUST match TaskResponse structure when entity='task'
- `payload.data.cascade` entities MUST also follow their respective contracts
- Frontend validates messages using `websocketValidator.ts` in DEV mode

---

### 3. Subtask Entity Contracts

#### Backend DTO: `SubtaskResponse`
**File**: `agenthub_main/src/fastmcp/task_management/application/dtos/subtask/subtask_response.py`

```python
@dataclass
class SubtaskResponse:
    # Required Fields
    id: str                                # UUID
    task_id: str                           # Parent task UUID
    title: str                             # Max 200 chars
    description: str                       # Max 2000 chars
    status: str                            # Same as task status enum
    priority: str                          # Same as task priority enum
    assignees: List[str]                   # Inherits from parent if empty
    progress_percentage: int = 0           # 0-100, default 0

    # Optional Fields
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    progress_notes: Optional[str]          # Brief progress description
```

#### Frontend Type: `SubtaskSummary`
**File**: `agenthub-frontend/src/types/taskTypes.ts`

```typescript
export interface SubtaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignees?: string[];          // Optional BUT if present MUST be array
  progress_percentage?: number;  // Optional number, NOT null
  created_at?: string;
  updated_at?: string;
}
```

---

## Known Issues & Validation Rules

### Issue 1: NULL/Undefined Array Properties
**Symptom**: Frontend receives `null` or `undefined` for array fields
**Root Cause**: Backend not initializing empty arrays
**Fix**: Backend DTOs ensure all array fields default to `[]`

```python
# WRONG:
assignees: List[str] = None  # Can be None

# RIGHT:
assignees: List[str] = field(default_factory=list)  # Always list
```

### Issue 2: progress_percentage NULL Instead of 0
**Symptom**: Frontend gets `null` instead of `0` for new tasks
**Root Cause**: Missing default value in DTO
**Fix**: Explicit `= 0` default in TaskResponse

```typescript
// Frontend expects:
progress_percentage: number  // NOT number | null

// Backend must provide:
progress_percentage: int = 0  // Never None
```

### Issue 3: Assignees Missing @ Prefix
**Symptom**: Frontend displays agent names without @ prefix
**Root Cause**: Backend stores without prefix in DB
**Fix**: TaskResponse.from_domain() adds @ prefix automatically

```python
# Fix in TaskResponse.from_domain()
assignees_with_prefix = [f"@{a}" if not a.startswith("@") else a for a in task_dict["assignees"]]
```

### Issue 4: subtask_count Synchronization
**Symptom**: `subtask_count` doesn't match `len(subtasks)`
**Root Cause**: Separate field that can become stale
**Fix**: Changed to @property that computes from `len(subtasks)`

```python
@property
def subtask_count(self) -> int:
    """Always accurate - computed from subtasks array"""
    return len(self.subtasks) if self.subtasks else 0
```

---

## Testing Strategy

### Test Layer 1: Backend Response Schema Tests
**Location**: `agenthub_main/src/tests/integration/response_validation/`

**Purpose**: Validate DTOs produce correct structure

```python
def test_task_response_has_all_required_fields():
    """Ensure no NULL values in required fields"""
    response = task_facade.get_task(task_id)
    assert response.id is not None
    assert response.assignees is not None
    assert isinstance(response.assignees, list)
    assert response.progress_percentage is not None
    assert isinstance(response.progress_percentage, int)
```

### Test Layer 2: REST API Contract Tests
**Location**: `agenthub_main/src/tests/integration/api_contract/`

**Purpose**: Validate HTTP responses match frontend expectations

```python
def test_get_task_returns_valid_structure(client):
    """Test actual API endpoint"""
    response = client.get(f"/api/v2/tasks/{task_id}")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["assignees"], list)
    assert isinstance(data["progress_percentage"], int)
    assert data["assignees"] is not None  # Never null
```

### Test Layer 3: WebSocket Message Tests
**Location**: `agenthub_main/src/tests/integration/websocket/`

**Purpose**: Validate WebSocket messages are complete

```python
async def test_task_update_websocket_complete():
    """Ensure WebSocket messages have all required fields"""
    async with websocket_client() as ws:
        # Trigger update
        await task_facade.update_task(task_id, title="New Title")

        # Receive message
        message = await ws.receive_json()

        # Validate structure
        assert message["version"] == "2.0"
        assert message["payload"]["entity"] == "task"
        assert message["payload"]["data"]["primary"]["assignees"] is not None
        assert isinstance(message["payload"]["data"]["primary"]["assignees"], list)
```

### Test Layer 4: Frontend Type Validation Tests
**Location**: `agenthub-frontend/src/__tests__/types/`

**Purpose**: TypeScript compile-time and runtime validation

```typescript
describe('Task Type Validation', () => {
  it('should reject null assignees', () => {
    const invalidTask = {
      id: '123',
      assignees: null,  // This should fail TypeScript compilation
    };

    expect(() => validateTask(invalidTask)).toThrow('assignees must be array');
  });

  it('should accept empty assignees array', () => {
    const validTask = {
      id: '123',
      assignees: [],  // Valid empty array
    };

    expect(validateTask(validTask)).toBe(true);
  });
});
```

---

## Validation Checklist

Before deploying any changes:

- [ ] All array fields return `[]` not `null`
- [ ] All numeric fields return `0` not `null` for defaults
- [ ] Assignees always have `@` prefix
- [ ] `subtask_count` matches `len(subtasks)`
- [ ] WebSocket messages conform to v2.0 protocol
- [ ] Backend DTOs match Frontend TypeScript types
- [ ] Integration tests pass for all communication layers
- [ ] WebSocket validator passes in DEV mode
- [ ] No NULL properties in required fields

---

## Related Documentation

- [Communication Layer Diagram](../core-architecture/communication-layers.md)
- [WebSocket Protocol v2.0 Spec](../api-integration/websocket-protocol-v2.md)
- [Testing Infrastructure](../testing-qa/layer-to-layer-testing.md)
- [ORM Models](../core-architecture/orm-models.md)

---

**Maintained by**: Test Orchestrator Agent
**Review Cycle**: Every Sprint
**Last Verified**: 2025-10-29
