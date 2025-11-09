# Contract & Integration - Complete Reference

## Quick Reference

| Contract Type | Coverage | Pass Rate | Status |
|---------------|----------|-----------|--------|
| Task API | 16 checks | 100% | ✅ Excellent |
| Subtask API | 17 checks | 94% | ✅ Good |
| Context API | 19 checks | 21%* | ⚠️ Needs attention |
| Git Branch API | 21 checks | 100% | ✅ Excellent |
| Project API | 16 checks | 100% | ✅ Excellent |
| WebSocket API | 31 checks | 100% | ✅ Excellent |

**Total**: 120 contract validations | *Context API low due to missing factory method

---

## What Are Contract Checks?

Contract validations verify **API agreements between backend and frontend**, ensuring:

| Validation Type | Purpose | Example |
|----------------|---------|---------|
| **Data Structure** | Backend responses match frontend types | Task response includes all expected fields |
| **Field Presence** | Required fields always present | `id`, `title`, `status` never null |
| **Type Safety** | Data types consistent | UUIDs are strings, timestamps are ISO 8601 |
| **Enum Values** | Enums use agreed values | Status: "todo" \| "in_progress" \| "done" |
| **Format Validation** | Special formats match | UUIDs v4, ISO 8601 timestamps |
| **Naming Conventions** | Consistent field names | snake_case in Python, camelCase in TypeScript |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (Python/FastAPI)                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Domain     │ -> │  Application │ -> │     API      │ │
│  │   Entities   │    │     DTOs     │    │  Endpoints   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└───────────────────────────────┬─────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  CONTRACT CHECKS      │  <- Validates boundary
                    │  (Integration)        │
                    └───────────┬───────────┘
                                │
┌───────────────────────────────┴─────────────────────────────┐
│                  FRONTEND (React/TypeScript)                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   API Types  │ <- │  API Client  │ <- │  Components  │ │
│  │ (api.types)  │    │  (services)  │    │     (UI)     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Contract Validation Results

### Task API Contract ✅ 100%

| Validation | Status | Details |
|------------|--------|---------|
| Field presence | ✅ PASS | All required fields present |
| UUID format | ✅ PASS | Valid UUID v4 strings |
| Timestamp format | ✅ PASS | ISO 8601 format |
| Status enum | ✅ PASS | Matches frontend types |
| Priority enum | ✅ PASS | Matches frontend types |
| Nested objects | ✅ PASS | Dependencies, assignees correct |
| Optional fields | ✅ PASS | Nullable fields handled |
| Array fields | ✅ PASS | Labels, dependencies as arrays |

**Validated Operations**: create, get, list, update, search, next, add_dependency, complete

**Backend**: `task_mcp_controller.py`, `TaskDTO`, `TaskRepository`
**Frontend**: `src/types/taskTypes.ts`, `ApiTaskResponse`

### Subtask API Contract ✅ 94%

| Validation | Status | Details |
|------------|--------|---------|
| Field presence | ✅ PASS | All required fields present |
| UUID format | ✅ PASS | Valid UUID v4 strings |
| Timestamp format | ✅ PASS | ISO 8601 format |
| Progress tracking | ✅ PASS | progress_percentage 0-100 |
| Parent reference | ✅ PASS | task_id always present |
| Inheritance | ✅ PASS | Agent assignment from parent |
| Progress history | ⚠️ PARTIAL | Format inconsistencies (non-blocking) |

**Issues Found**: Progress history array format varies between operations (minor, doesn't break UI)

### Context API Contract ⚠️ 21%

| Validation | Status | Details |
|------------|--------|---------|
| Field presence | ✅ PASS | Basic fields present |
| Hierarchy validation | ❌ FAIL | Missing TaskContext factory method |
| Inheritance chain | ⚠️ PARTIAL | Global→Project works, Branch→Task broken |
| Delegation | ❌ FAIL | Cannot create from factory |
| Data structure | ✅ PASS | JSON data field correct |

**Root Cause**: Missing `TaskContext.create()` factory method in test fixtures
**Impact**: Cannot fully validate task-level context in integration checks
**Resolution**: Add factory method to `factories.py` for task context

### Git Branch API Contract ✅ 100%

| Validation | Status | Details |
|------------|--------|---------|
| Field presence | ✅ PASS | All required fields present |
| UUID format | ✅ PASS | Valid UUID v4 strings |
| Project reference | ✅ PASS | project_id always present |
| Statistics | ✅ PASS | Task counts, progress correct |
| Agent assignment | ✅ PASS | Assigned agents array correct |

**Validated Operations**: create, get, list, update, assign_agent, get_statistics, delete

### Project API Contract ✅ 100%

| Validation | Status | Details |
|------------|--------|---------|
| Field presence | ✅ PASS | All required fields present |
| UUID format | ✅ PASS | Valid UUID v4 strings |
| Health metrics | ✅ PASS | Orchestration status correct |
| Branch counting | ✅ PASS | branch_count accurate |
| Task counting | ✅ PASS | task_count accurate |

**Validated Operations**: create, get, list, update, project_health_check, delete

### WebSocket API Contract ✅ 100%

| Validation | Status | Details |
|------------|--------|---------|
| Message format | ✅ PASS | All messages follow v2.0 protocol |
| Event types | ✅ PASS | CREATE, UPDATE, DELETE, COMPLETE |
| Payload structure | ✅ PASS | Timestamps, metadata correct |
| Entity types | ✅ PASS | Project, Branch, Task, Subtask all correct |
| Real-time sync | ✅ PASS | Frontend cache updates triggered |

**Protocol**: WebSocket Protocol v2.0 (TypeScript + Python Pydantic models)
**Files**: `websocket-protocol.ts`, `websocket_protocol.py`

---

## Type Comparison Matrix

### Backend → Frontend Mapping

| Backend (Python) | Frontend (TypeScript) | Validation | Notes |
|------------------|----------------------|------------|-------|
| `str` (UUID) | `string` | ✅ Valid | UUID v4 format verified |
| `datetime` | `string` (ISO 8601) | ✅ Valid | Timezone-aware UTC |
| `Optional[str]` | `string \| null` | ✅ Valid | Nullable fields handled |
| `List[str]` | `string[]` | ✅ Valid | Arrays match |
| `Dict[str, Any]` | `Record<string, any>` | ✅ Valid | JSON data field |
| Enum `TaskStatus` | Union type | ✅ Valid | Values aligned |
| `int` (0-100) | `number` | ✅ Valid | Range validation |

### Common Mismatches (Resolved)

| Issue | Backend | Frontend | Resolution |
|-------|---------|----------|------------|
| Timestamp format | `datetime` object | `string` | Auto-converted to ISO 8601 |
| Null vs undefined | `None` | `undefined` | Mapped to `null` in JSON |
| Empty arrays | `[]` | `null` sometimes | Consistent `[]` everywhere |
| UUID format | String UUID | String | Validation added |

---

## Layer-to-Layer Validation

### Domain → Application

**Validates**: Entities → DTOs transformation

| Entity | DTO | Validation | Pass Rate |
|--------|-----|------------|-----------|
| Task | TaskDTO | ✅ All fields map | 100% |
| Subtask | SubtaskDTO | ✅ All fields map | 100% |
| Project | ProjectDTO | ✅ All fields map | 100% |
| GitBranch | GitBranchDTO | ✅ All fields map | 100% |
| Context | ContextDTO | ⚠️ Partial (factory issue) | 85% |

### Application → Interface

**Validates**: DTOs → API responses

| DTO | API Response | Validation | Pass Rate |
|-----|--------------|------------|-----------|
| TaskDTO | JSON response | ✅ Schema match | 100% |
| SubtaskDTO | JSON response | ✅ Schema match | 100% |
| ProjectDTO | JSON response | ✅ Schema match | 100% |
| GitBranchDTO | JSON response | ✅ Schema match | 100% |

### Interface → Frontend

**Validates**: API responses → TypeScript types

| API Response | TypeScript Type | Validation | Pass Rate |
|--------------|----------------|------------|-----------|
| Task JSON | `ApiTaskResponse` | ✅ Type-safe | 100% |
| Subtask JSON | `ApiSubtaskResponse` | ✅ Type-safe | 100% |
| Project JSON | `ApiProjectResponse` | ✅ Type-safe | 100% |
| Branch JSON | `ApiBranchResponse` | ✅ Type-safe | 100% |

---

## Integration Coverage

### Label Operations ✅

**Coverage**: Label attachment, detachment, filtering

| Operation | Backend | Frontend | Integration | Status |
|-----------|---------|----------|-------------|--------|
| Attach label | ✅ Working | ✅ Working | ✅ Validated | Production ready |
| Detach label | ✅ Working | ✅ Working | ✅ Validated | Production ready |
| Filter by label | ✅ Working | ✅ Working | ✅ Validated | Production ready |
| List labels | ✅ Working | ✅ Working | ✅ Validated | Production ready |

**Files**: `label_operations.md`, `label-integration-test-coverage.md`

### Server Startup ✅

**Coverage**: MCP server initialization, health checks

| Check | Validation | Status |
|-------|------------|--------|
| FastMCP server starts | ✅ PASS | Starts in <2s |
| Health endpoint responds | ✅ PASS | Returns 200 OK |
| Database connection | ✅ PASS | Pool initialized |
| Authentication ready | ✅ PASS | Keycloak connected |
| WebSocket server | ✅ PASS | Port 8000 listening |

**Files**: `server-startup-test-implementation.md`

---

## Validation Patterns

### Pattern 1: Field Presence

```python
def test_task_response_has_required_fields():
    response = create_task(...)
    assert "id" in response
    assert "title" in response
    assert "status" in response
    assert "created_at" in response
```

### Pattern 2: Type Validation

```python
def test_task_id_is_valid_uuid():
    response = create_task(...)
    task_id = response["id"]
    assert UUID(task_id)  # Raises if invalid UUID
```

### Pattern 3: Enum Values

```python
def test_task_status_enum():
    response = create_task(...)
    assert response["status"] in [
        "todo", "in_progress", "done", "blocked"
    ]
```

### Pattern 4: Nested Objects

```python
def test_task_dependencies_structure():
    response = get_task(...)
    dependencies = response["dependencies"]
    assert isinstance(dependencies, list)
    for dep in dependencies:
        assert "id" in dep
        assert "title" in dep
```

---

## Gap Analysis

### Known Gaps

| Gap | Impact | Priority | Resolution |
|-----|--------|----------|------------|
| Context API factory | Cannot validate task contexts | HIGH | Add factory method |
| Progress history format | Minor inconsistencies | LOW | Standardize format |
| WebSocket error cases | Missing error validations | MEDIUM | Add error scenarios |
| Bulk operations | No bulk create validation | LOW | Add bulk operation checks |

### Improvement Plan

1. **Week 1**: Add TaskContext factory method, validate task-level contexts
2. **Week 2**: Standardize progress history format across all operations
3. **Week 3**: Add WebSocket error case validation (disconnect, timeout, malformed)
4. **Week 4**: Add bulk operation contract validation

---

## Execution Commands

```bash
# Run all contract checks
pytest agenthub_main/src/tests/integration/test_contract_*.py -v

# Run specific API contracts
pytest -k "test_task_contract" -v
pytest -k "test_websocket_contract" -v

# Run layer-to-layer checks
pytest -k "test_layer_to_layer" -v

# With detailed output
pytest -v -s --tb=short

# Generate contract report
pytest --json-report --json-report-file=contract_report.json
```

---

## Troubleshooting

### Issue: Contract Check Fails

**Symptoms**: Check fails with field missing or wrong type

**Diagnosis**:
1. Check backend response format: `print(json.dumps(response, indent=2))`
2. Check frontend type definition: `src/types/*.ts`
3. Check DTO mapping: `*_dto.py`

**Common Causes**:
- Backend added/removed field but frontend type not updated
- Frontend expects camelCase but backend returns snake_case
- Nullable field not marked as optional in TypeScript

### Issue: Context API Low Pass Rate

**Symptoms**: Context validation checks fail at 21%

**Root Cause**: Missing `TaskContext.create()` factory method

**Resolution**: Add factory method to `tests/factories.py`:
```python
@staticmethod
def create(task_id: UUID, **kwargs) -> TaskContext:
    return TaskContext(
        id=uuid4(),
        task_id=task_id,
        data=kwargs.get("data", {}),
        ...
    )
```

---

## Related Documentation
- [MCP Validation Complete](./mcp-tools-validation-complete.md)
- [QA Strategy & Planning](./qa-strategy-planning-complete.md)
- [WebSocket Protocol v2.0](../core-architecture/agenthub-system-architecture.md#websocket)
- [API Integration Guide](../api-integration/)
