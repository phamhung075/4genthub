# Backend-Frontend Type Comparison Matrix

**Generated:** 2025-10-27
**Task ID:** 9f30b79e-6cc7-406a-8ac1-d5d92a864097
**Purpose:** Discovery phase for API contract testing - identify type mismatches between backend Pydantic models and frontend TypeScript types

---

## Executive Summary

This document provides a comprehensive comparison of backend (Python/Pydantic) and frontend (TypeScript) type definitions for the agenthub system. The analysis focuses on critical fields that impact data integrity and frontend reliability.

### Key Findings:
- **8 Critical Mismatches** identified requiring fixes
- **15 Confirmed Matches** working correctly
- **Critical Fields:** project_id, subtask_count, completed_subtasks, field naming conventions

---

## 1. Task Type Comparison

### Backend: TaskResponse (task_response.py)

```python
@dataclass
class TaskResponse:
    # Core fields
    id: str                                    # UUID
    title: str
    description: str
    status: str
    priority: str
    details: str                              # Formatted progress_history text

    # Effort and assignment
    estimated_effort: str                     # Snake_case in entity
    assignees: List[str]                      # With @ prefix
    labels: List[str]

    # Relationships
    dependencies: List[str]                   # Task IDs
    subtasks: List[Dict[str, Any]]           # Full subtask objects
    git_branch_id: Optional[str]             # Links to branch → project
    context_id: Optional[str]
    context_data: Optional[Dict[str, Any]]
    dependency_relationships: Optional[DependencyRelationships]

    # Timestamps
    due_date: Optional[str]
    created_at: Optional[datetime]           # Serialized to ISO string
    updated_at: Optional[datetime]           # Serialized to ISO string

    # Progress tracking
    progress_percentage: int = 0             # 0-100
    progress_history: Optional[Dict[str, Any]]
    progress_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converts to JSON with field name transformations"""
        return {
            "estimatedEffort": self.estimated_effort,  # ⚠️ camelCase
            "dueDate": self.due_date,                   # ⚠️ camelCase
            "created_at": self.created_at.isoformat(),  # ISO 8601
            "updated_at": self.updated_at.isoformat(),  # ISO 8601
            # ... other fields
        }
```

### Frontend: Task (api.types.ts)

```typescript
export interface Task {
  // Core fields
  id: string;                              // ✅ Match
  title: string;                           // ✅ Match
  description?: string;                    // ✅ Match
  status: string;                          // ✅ Match
  priority: string;                        // ✅ Match
  details?: string;                        // ✅ Match

  // Effort and assignment
  estimated_effort?: string;               // ⚠️ Snake_case (backend sends camelCase)
  assignees?: string[];                    // ✅ Match
  labels?: string[];                       // ✅ Match

  // Relationships
  dependencies?: string[];                 // ✅ Match
  subtasks?: Subtask[] | string[];        // ✅ Match (can be IDs or objects)
  git_branch_id: string;                   // ✅ Match
  project_id: string;                      // ❌ MISSING IN BACKEND
  context_id?: string;                     // ✅ Match
  context_data?: Context;                  // ⚠️ Structure may differ

  // Computed fields
  has_dependencies: boolean;               // ⚠️ Not in backend response
  has_context: boolean;                    // ⚠️ Not in backend response
  parent_task_id?: string;                 // ⚠️ Only for subtasks

  // Timestamps
  due_date?: string;                       // ⚠️ Snake_case (backend sends camelCase)
  created_at?: string;                     // ✅ Match (ISO format)
  updated_at?: string;                     // ✅ Match (ISO format)

  // Progress tracking
  progress_percentage?: number;            // ✅ Match
  progress_history?: Record<string, any>;  // ✅ Match

  // MISSING FROM BACKEND:
  // subtask_count: number;                // ❌ Must count subtasks array
  // completed_subtasks: number;           // ❌ Must count done subtasks
}
```

---

## 2. Subtask Type Comparison

### Backend: SubtaskResponse (subtask_response.py)

```python
@dataclass
class SubtaskResponse:
    task_id: str                             # Parent task ID
    subtask: Dict[str, Any]                  # ⚠️ Nested structure
    progress: Dict[str, Any]
    agent_inheritance_applied: bool = False
    inherited_assignees: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Returns nested structure"""
        return {
            "task_id": self.task_id,
            "subtask": self.subtask,        # Frontend must unwrap this
            "progress": self.progress
        }
```

### Frontend: Subtask (api.types.ts)

```typescript
export interface Subtask {
  id: string;
  task_id: string;
  parent_task_id?: string;                // Conditional: omitted when nested
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignees?: string[];
  progress_percentage?: number;
  created_at?: string;
  updated_at?: string;
  progress_notes?: string;
  completion_summary?: string;
}
```

**Note:** Frontend api.ts already handles unwrapping the nested structure correctly.

---

## 3. Dependency Information Comparison

### Backend: DependencyRelationships (dependency_info.py)

```python
@dataclass
class DependencyRelationships:
    """Rich dependency information"""
    task_id: str

    # Direct dependencies
    depends_on: List[DependencyInfo]        # Tasks this depends on
    blocks: List[DependencyInfo]            # Tasks this blocks

    # Dependency chains
    upstream_chains: List[DependencyChain]
    downstream_chains: List[DependencyChain]

    # Summary
    total_dependencies: int
    completed_dependencies: int
    blocked_dependencies: int

    # Status
    can_start: bool
    is_blocked: bool
    is_blocking_others: bool

    # Guidance
    dependency_summary: str
    next_actions: List[str]
    blocking_reasons: List[str]

    @property
    def dependency_completion_percentage(self) -> float:
        """Computed property"""
        if self.total_dependencies == 0:
            return 100.0
        return (self.completed_dependencies / self.total_dependencies) * 100
```

### Frontend: Task Dependencies (Simplified)

```typescript
export interface Task {
  has_dependencies: boolean;               // ⚠️ Computed on frontend
  dependencies?: string[];                 // Array of task IDs only

  // MISSING: Rich dependency features from backend
  // - dependency_relationships: DependencyRelationships
  // - Blocking chains
  // - Workflow guidance
  // - Next actions suggestions
}
```

**Assessment:** Frontend uses simplified dependency model. Backend provides much richer data that could improve UX.

---

## 4. Context Type Comparison

### Backend: Context in TaskResponse

```python
# In TaskResponse:
context_id: Optional[str]
context_data: Optional[Dict[str, Any]]    # Generic dictionary

# Actual structure depends on TaskContext entity
# May include: metadata, progress, objective, dependencies, subtasks
```

### Frontend: Context (context.types.ts)

```typescript
export interface Context {
  id?: string;                            // Optional: omitted when embedded
  level?: string;                         // 'global', 'project', 'branch', 'task'
  context_data?: {
    metadata?: {
      [key: string]: any;                 // Conditional fields
    };
    progress?: {
      current_session_summary?: string;
      completion_percentage?: number;
      next_steps?: string[];
      completed_actions?: string[];
    };
    [key: string]: any;
  };
  created_at?: string;
  updated_at?: string;
}
```

**Assessment:** Need to verify actual API response structure matches frontend expectations.

---

## 5. Task List Item Comparison

### Backend: TaskListItemResponse (task_list_item_response.py)

```python
@dataclass
class TaskListItemResponse:
    """Minimal task for list views"""
    id: str
    title: str
    status: str
    priority: str
    progress_percentage: int = 0
    labels: List[str]                      # First 3 only
    due_date: Optional[str]
    updated_at: Optional[datetime]
    has_dependencies: bool = False
    is_blocked: bool = False
```

### Frontend: TaskSummary (taskTypes.ts)

```typescript
export interface TaskSummary {
  id: string;                             // ✅ Match
  title: string;                          // ✅ Match
  status: string;                         // ✅ Match
  priority: string;                       // ✅ Match
  assignees?: string[];                   // ⚠️ Not in backend list response
  has_dependencies: boolean;              // ✅ Match
  has_context: boolean;                   // ⚠️ Not in backend list response
  created_at?: string;                    // ⚠️ Not in backend list response
  updated_at?: string;                    // ✅ Match
}
```

**Assessment:** Frontend TaskSummary expects fields not in minimal backend response.

---

## 🚨 Critical Mismatches Summary

### MISMATCH #1: project_id Missing in Backend ⚠️ CRITICAL

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Field | `git_branch_id: Optional[str]` | `project_id: string` (required) |
| Impact | Frontend cannot filter/group by project without querying branch → project | HIGH |
| Fix | Add computed `project_id` field to TaskResponse by querying git_branch → project | Required |

**Why this matters:** Frontend needs project_id for:
- Filtering tasks by project
- Grouping tasks in project views
- Navigation and breadcrumbs
- Permission checks

**Solution:** Query git_branch table to get project_id and include in response.

---

### MISMATCH #2: subtask_count Missing in Backend ⚠️ CRITICAL

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Field | `subtasks: List[Dict[str, Any]]` | Expects `subtask_count: number` |
| Impact | Frontend must count len(subtasks) - inefficient with large arrays | MEDIUM |
| Fix | Add computed `subtask_count: int` field to TaskResponse | Required |

**Why this matters:** Mentioned in Issue #1 requirements as critical field for UI display.

**Solution:** Add `subtask_count = len(self.subtasks)` to TaskResponse.to_dict()

---

### MISMATCH #3: completed_subtasks Missing in Backend ⚠️ CRITICAL

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Field | Full subtasks array only | Expects `completed_subtasks: number` |
| Impact | Frontend must iterate and count status='done' | MEDIUM |
| Fix | Add computed `completed_subtasks: int` field | Required |

**Why this matters:** Needed for progress indicators and completion tracking.

**Solution:** Count subtasks with status='done' and include in response.

---

### MISMATCH #4: SubtaskResponse Structure ✅ HANDLED

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Structure | Nested: `{task_id, subtask: {...}, progress}` | Expects flat subtask object |
| Impact | Frontend must unwrap `.subtask` field | LOW |
| Status | Frontend api.ts already handles this correctly | No fix needed |

---

### MISMATCH #5: estimatedEffort vs estimated_effort ⚠️ NAMING

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Entity field | `estimated_effort` (snake_case) | `estimated_effort` (snake_case) |
| JSON serialization | `estimatedEffort` (camelCase in to_dict) | Expects `estimated_effort` (snake_case) |
| Impact | Inconsistent - backend sends camelCase but types use snake_case | MEDIUM |
| Fix | Frontend should use `estimatedEffort` to match actual API | Recommended |

**Recommendation:** Update frontend types to match actual JSON response (camelCase).

---

### MISMATCH #6: dueDate vs due_date ⚠️ NAMING

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Entity field | `due_date` (snake_case) | `due_date` (snake_case) |
| JSON serialization | `dueDate` (camelCase in to_dict) | Expects `due_date` (snake_case) |
| Impact | Inconsistent naming convention | MEDIUM |
| Fix | Frontend should use `dueDate` to match actual API | Recommended |

**Recommendation:** Update frontend types to match actual JSON response (camelCase).

---

### MISMATCH #7: Dependency Relationships Structure ⚠️ FEATURE GAP

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Structure | Rich DependencyRelationships with chains, workflow guidance | Flat `dependencies: string[]` |
| Impact | Frontend missing workflow guidance features | LOW (works, but limited) |
| Fix | Optional: Add full dependency_relationships support to frontend | Future enhancement |

**Assessment:** Current simplified view works. Rich features could improve UX in future.

---

### MISMATCH #8: Context Data Structure ⚠️ NEEDS VERIFICATION

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Type | `Dict[str, Any]` (generic) | Structured `Context` interface |
| Impact | May not parse correctly if structure differs | MEDIUM |
| Fix | Verify actual API response matches Context interface | Required |

**Action:** Create contract test to verify context_data structure.

---

## ✅ Confirmed Matches

These fields match correctly between backend and frontend:

1. ✅ `id: string/str` - UUID format
2. ✅ `title: string/str` - Task title
3. ✅ `description: string/str` (optional) - Task description
4. ✅ `status: string/str` - Task status enum
5. ✅ `priority: string/str` - Priority enum
6. ✅ `assignees: string[]/List[str]` - Agent names with @ prefix
7. ✅ `labels: string[]/List[str]` - Labels array
8. ✅ `progress_percentage: number/int` - 0-100 percentage
9. ✅ `created_at: string/datetime` - ISO 8601 format
10. ✅ `updated_at: string/datetime` - ISO 8601 format
11. ✅ `git_branch_id: string/str` - Branch UUID
12. ✅ `context_id: string/str` (optional) - Context UUID
13. ✅ `details: string/str` - Formatted progress history
14. ✅ `progress_history: Record<string,any>/Dict[str,Any]` - Progress entries
15. ✅ `progress_count: number/int` - Number of progress entries

---

## Contract Test Requirements

Based on this analysis, the following contract tests are required:

### Backend Contract Tests (Python/pytest)

1. **test_task_response_includes_project_id**
   - Verify project_id field is populated from git_branch
   - Ensure it's always present (not null)

2. **test_task_response_includes_subtask_count**
   - Verify subtask_count matches len(subtasks)
   - Test with 0, 1, and multiple subtasks

3. **test_task_response_includes_completed_subtasks**
   - Verify completed_subtasks counts status='done' correctly
   - Test various subtask completion states

4. **test_task_response_uses_camelCase_for_effort_and_date**
   - Verify JSON contains estimatedEffort (not estimated_effort)
   - Verify JSON contains dueDate (not due_date)

5. **test_assignees_have_at_prefix**
   - Verify all assignees start with @
   - Test creation, update, and list operations

6. **test_timestamps_are_iso8601_format**
   - Verify created_at and updated_at are valid ISO strings
   - Test with timezone-aware datetimes

7. **test_subtask_response_structure**
   - Verify structure includes task_id, subtask, progress
   - Verify unwrapping subtask field works correctly

8. **test_context_data_structure_matches_frontend**
   - Verify context_data has expected structure
   - Test metadata, progress, and optional fields

### Frontend Contract Tests (TypeScript/Jest or Vitest)

1. **test_task_api_returns_all_required_fields**
   - Mock API response
   - Verify all required Task fields present
   - Verify types match TypeScript definitions

2. **test_subtask_api_returns_valid_subtasks**
   - Verify Subtask type matches API response
   - Test nested and flat response formats

3. **test_field_naming_matches_actual_api**
   - Verify estimatedEffort (not estimated_effort)
   - Verify dueDate (not due_date)

4. **test_computed_fields_present**
   - Verify subtask_count in response
   - Verify completed_subtasks in response
   - Verify project_id in response

### WebSocket Contract Tests

1. **test_task_created_message_format**
2. **test_task_updated_message_format**
3. **test_task_completed_message_format**
4. **test_subtask_created_message_format**
5. **test_context_synced_message_format**

---

## Next Steps

1. ✅ **Discovery Phase Complete** - This document
2. ⏳ **Create Contract Tests** - Implement tests listed above
3. ⏳ **Run Tests & Document Failures** - Identify actual failures
4. ⏳ **Fix Mismatches** - Update backend or frontend as needed
5. ⏳ **Add to CI/CD** - Prevent regressions

---

## References

- Backend DTOs: `/agenthub_main/src/fastmcp/task_management/application/dtos/`
- Frontend Types: `/agenthub-frontend/src/types/`
- Original Task: `9f30b79e-6cc7-406a-8ac1-d5d92a864097`
- Related Issues: #1 (subtask_count), #3 (project_id), #4 (timestamps), #5 (estimated_effort), #6 (assignees)
