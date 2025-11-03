# Phase 2: Validation & Search Optimization

**Building on Phase 1 (workflow_guidance removal - 70% token savings)**

## 🎯 Three Additional Optimizations

| # | Optimization | Impact | Token Savings |
|---|--------------|--------|---------------|
| 1 | **REQUIRE progress_notes** on update | Data quality↑ | Context preservation |
| 2 | **REQUIRE completion_summary** on complete | Documentation↑ | Quality enforcement |
| 3 | **Minimal search results** | Response size↓ | 60-80% per search |

---

## 1️⃣ Make progress_notes REQUIRED for Updates

### Problem
```python
# Currently OPTIONAL - loses context
manage_task(action="update", task_id="xyz", status="in_progress")
# Result: No record of WHAT was done or WHY status changed
```

### Solution
```python
# Make REQUIRED - preserves context
manage_task(
    action="update",
    task_id="xyz",
    status="in_progress",
    details="Started JWT implementation"  # REQUIRED
)
```

### Implementation

**File**: `task_mcp_controller/validators/parameter_validator.py`

```python
def validate_update_parameters(self, action: str, **params) -> tuple[bool, dict | None]:
    """Validate parameters for update operations."""

    if action == "update":
        task_id = params.get("task_id")
        details = params.get("details")

        # RULE: progress tracking required for updates
        if not details or len(details.strip()) < 10:
            return False, self._response_formatter.create_error_response(
                operation="update",
                error="Missing required field: details (progress_notes). Updates must include progress description.",
                error_code=ErrorCodes.VALIDATION_ERROR,
                metadata={
                    "field": "details",
                    "requirement": "Minimum 10 characters describing what was done",
                    "example": "Completed JWT token signing, starting refresh token logic"
                }
            )

    return True, None
```

**Benefits**:
- ✅ Complete progress history preserved
- ✅ Better collaboration (team sees what happened)
- ✅ Audit trail for debugging
- ✅ Context survives session restarts

---

## 2️⃣ Make completion_summary REQUIRED for Complete

### Problem
```python
# Currently OPTIONAL - no documentation
manage_task(action="complete", task_id="xyz")
# Result: Task marked done but NO record of accomplishments
```

### Solution
```python
# Make REQUIRED - documents work
manage_task(
    action="complete",
    task_id="xyz",
    completion_summary="Implemented JWT auth with 2FA, refresh tokens, tests passing"  # REQUIRED
)
```

### Implementation

**File**: `task_mcp_controller/validators/business_validator.py:142-170`

```python
def validate_completion_requirements(
    self,
    task_data: dict[str, Any],
    completion_summary: str | None = None,
    testing_notes: str | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """Validate requirements for task completion."""

    # STRICT REQUIREMENT: All completed tasks MUST have summary
    if not completion_summary or len(completion_summary.strip()) < 20:
        return False, self._create_business_error(
            "missing_completion_summary",
            "Completion summary is REQUIRED (minimum 20 characters)",
            "Describe what was accomplished, not just 'done' or 'finished'",
            metadata={
                "requirement": "Detailed summary of accomplishments",
                "minimum_length": 20,
                "example": "Implemented JWT authentication with refresh tokens, added 2FA support via TOTP, all unit tests passing"
            }
        )

    # RECOMMENDED: High/critical tasks should include testing notes
    priority = task_data.get("priority", "medium")
    if priority.lower() in ["high", "critical"] and not testing_notes:
        logger.warning(
            f"High/critical task completed without testing notes - summary: {completion_summary[:50]}"
        )
        # Warning only - not blocking

    return True, None
```

**Benefits**:
- ✅ Permanent record of what was achieved
- ✅ Knowledge transfer for team
- ✅ Better retrospectives
- ✅ Quality documentation enforced

---

## 3️⃣ Minimal Search Results (80% Token Savings)

### Problem - Current Search Response
```json
{
  "tasks": [
    {
      "id": "abc-123",
      "title": "Implement auth",
      "description": "Build JWT-based...",  // ← 500 tokens
      "status": "todo",
      "priority": "high",
      "details": "=== Progress 1 ===\n...",  // ← 800 tokens
      "estimatedEffort": "3 days",
      "assignees": ["@coding-agent"],
      "labels": ["backend", "security"],
      "dependencies": [],
      "subtasks": [],
      "created_at": "2025-11-03...",
      "updated_at": "2025-11-03...",
      "git_branch_id": "xyz-789",
      "context_id": "abc-123",
      "progress_percentage": 0,
      "progress_history": {...},  // ← 600 tokens
      "progress_count": 1,
      "subtask_count": 0,
      "completed_subtasks": 0
    }
  ]
}
```
**Per-task tokens**: ~2,500 tokens
**10 search results**: ~25,000 tokens

### Solution - Minimal Search Response
```json
{
  "tasks": [
    {
      "id": "abc-123",
      "title": "Implement auth",
      "description": "Build JWT-based...",
      "status": "todo",
      "priority": "high"
    }
  ]
}
```
**Per-task tokens**: ~150 tokens
**10 search results**: ~1,500 tokens
**Savings**: **23,500 tokens (94%!)**

### Implementation

**File**: `application/dtos/task/task_list_response.py`

Add new method:

```python
def to_minimal_dict(self) -> dict[str, Any]:
    """
    Serialize to minimal dictionary for search operations (token optimization).

    Returns only: id, title, description, status, priority
    Use for: search results where user just needs to identify tasks
    Get full details via: manage_task(action="get", task_id="...")
    """
    return {
        "id": self.id,
        "title": self.title,
        "description": self.description if self.description else "",
        "status": self.status,
        "priority": self.priority
    }
```

**File**: `interface/mcp_controllers/task_mcp_controller/handlers/search_handler.py:71-120`

Update search handler:

```python
def search_tasks(
    self,
    facade: TaskApplicationFacade,
    query: str | None,
    git_branch_id: str | None,
    limit: int | None,
) -> dict[str, Any]:
    """Handle task search operations with minimal response."""

    if not query:
        return self._response_formatter.create_error_response(
            operation="search_tasks",
            error="Missing required field: query",
            error_code=ErrorCodes.VALIDATION_ERROR,
        )

    try:
        request = SearchTasksRequest(
            query=query,
            git_branch_id=git_branch_id,
            limit=limit or 10,
        )

        result = facade.search_tasks(request)

        # OPTIMIZATION: Return minimal fields for search results
        if result.get("success") and "tasks" in result:
            tasks = result["tasks"]

            # Convert to minimal representation (only 5 essential fields)
            minimal_tasks = []
            for task in tasks:
                minimal_tasks.append({
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "description": task.get("description", ""),
                    "status": task.get("status"),
                    "priority": task.get("priority")
                })

            result["tasks"] = minimal_tasks

            # Add helpful metadata
            result["search_metadata"] = {
                "query": query,
                "git_branch_id": git_branch_id,
                "total_results": len(minimal_tasks),
                "tip": "Use manage_task(action='get', task_id='...') for full details"
            }

        return result

    except Exception as e:
        logger.error(f"Error in search_tasks: {str(e)}")
        return self._response_formatter.create_error_response(
            operation="search_tasks",
            error=f"Search failed: {str(e)}",
            error_code=ErrorCodes.OPERATION_FAILED,
        )
```

**Same for Subtask Search**:

**File**: `interface/mcp_controllers/subtask_mcp_controller/subtask_mcp_controller.py`

Apply identical minimal response pattern to `list` operation.

---

## 📊 Combined Impact

### Before All Optimizations
```
Single Task Search (10 results):
- workflow_guidance: 1,500 tokens × 10 = 15,000
- Full task data: 2,500 tokens × 10 = 25,000
Total: 40,000 tokens per search
```

### After Phase 1 Only (workflow_guidance removed)
```
Single Task Search (10 results):
- Full task data: 2,500 tokens × 10 = 25,000
Total: 25,000 tokens per search
Savings: 15,000 tokens (38%)
```

### After Phase 2 (minimal search + validation)
```
Single Task Search (10 results):
- Minimal task data: 150 tokens × 10 = 1,500
Total: 1,500 tokens per search
Savings: 38,500 tokens (96%!)
```

---

## 🚀 Implementation Priority

| Priority | Optimization | Reason |
|----------|--------------|--------|
| **HIGH** | Minimal search results | Immediate 96% savings on search |
| **MEDIUM** | REQUIRE completion_summary | Quality enforcement |
| **LOW** | REQUIRE progress_notes | Nice-to-have, can add warnings first |

---

## ✅ Testing Plan

### 1. Test Required progress_notes
```python
# Should FAIL
manage_task(action="update", task_id="xyz", status="in_progress")

# Should SUCCEED
manage_task(
    action="update",
    task_id="xyz",
    status="in_progress",
    details="Started implementation"
)
```

### 2. Test Required completion_summary
```python
# Should FAIL
manage_task(action="complete", task_id="xyz")

# Should SUCCEED
manage_task(
    action="complete",
    task_id="xyz",
    completion_summary="Feature implemented with tests"
)
```

### 3. Test Minimal Search
```python
# Search should return minimal fields
result = manage_task(action="search", query="auth", git_branch_id="xyz")

# Verify response structure
assert "tasks" in result["data"]
for task in result["data"]["tasks"]:
    assert set(task.keys()) == {"id", "title", "description", "status", "priority"}
    assert "progress_history" not in task
    assert "context_data" not in task
```

---

## 📝 Migration Notes

### Breaking Changes
None - these are additions/restrictions, not removals

### Warnings to Add First (Gradual Rollout)
1. Week 1: Log warnings for missing progress_notes
2. Week 2: Log warnings for missing completion_summary
3. Week 3: Make both REQUIRED (blocking errors)
4. Week 4: Roll out minimal search immediately (no breaking change)

---

## 🎯 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Search token savings** | 90%+ | Compare before/after search responses |
| **Progress documentation** | 100% | All updates have progress_notes |
| **Completion documentation** | 100% | All completions have summaries |
| **User complaints** | 0 | No workflow disruptions |

---

## Files to Modify

### Phase 2.1: Minimal Search (HIGH PRIORITY)
1. ✅ `task_list_response.py` - Add `to_minimal_dict()` method
2. ✅ `search_handler.py` - Use minimal serialization for search
3. ✅ `subtask_mcp_controller.py` - Apply to subtask list/search

### Phase 2.2: Required Fields (MEDIUM PRIORITY)
4. ⏳ `parameter_validator.py` - Validate progress_notes on update
5. ⏳ `business_validator.py` - Enforce completion_summary (already has validation at line 142, make it STRICT)

### Phase 2.3: Testing
6. ⏳ Unit tests for new validations
7. ⏳ Integration test for minimal search

---

## Rollback Plan

If issues arise:
1. **Minimal search**: Revert to full serialization (1-line change)
2. **Required fields**: Change from error to warning (1-line change)
3. **Emergency**: Set `ENABLE_STRICT_VALIDATION=false` env var

---

## Next Steps

1. ✅ Implement minimal search (highest impact, no risk)
2. ⏳ Add warnings for missing fields (week 1)
3. ⏳ Make fields required after warning period
4. ⏳ Measure token savings and document results
