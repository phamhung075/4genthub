# Label Operations - API Documentation

**Last Updated**: 2025-10-22
**API Version**: 1.0
**Status**: Production Ready (Post-P0 Fix)

---

## Overview

Labels provide a flexible categorization system for tasks in agenthub. This document describes all label-related API operations, including creation, querying, filtering, and error handling.

---

## Table of Contents

1. [Creating Tasks with Labels](#creating-tasks-with-labels)
2. [Label Formats](#label-formats)
3. [Querying and Filtering](#querying-and-filtering)
4. [Label Management](#label-management)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

---

## Creating Tasks with Labels

### Basic Label Creation

Labels are specified during task creation using the `labels` parameter.

#### MCP Tool Usage

```python
# Single label
result = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    title="Implement user authentication",
    assignees="coding-agent,security-auditor-agent",
    labels="backend"  # Single label as string
)

# Multiple labels (comma-separated)
result = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    title="Build API endpoints",
    assignees="coding-agent",
    labels="backend,api,security"  # Multiple labels
)
```

#### Response Format

```json
{
  "success": true,
  "task": {
    "id": "a25d17f8-6780-41b4-8fa1-520daa12619e",
    "title": "Build API endpoints",
    "labels": [
      {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "name": "backend",
        "color": "#0066cc",
        "description": "",
        "created_at": "2025-10-22T19:00:00.000000+00:00",
        "updated_at": "2025-10-22T19:00:00.000000+00:00"
      },
      {
        "id": "e47ac10b-58cc-4372-a567-0e02b2c3d480",
        "name": "api",
        "color": "#0066cc",
        "description": "",
        "created_at": "2025-10-22T19:00:00.000000+00:00",
        "updated_at": "2025-10-22T19:00:00.000000+00:00"
      },
      {
        "id": "d47ac10b-58cc-4372-a567-0e02b2c3d481",
        "name": "security",
        "color": "#0066cc",
        "description": "",
        "created_at": "2025-10-22T19:00:00.000000+00:00",
        "updated_at": "2025-10-22T19:00:00.000000+00:00"
      }
    ]
  }
}
```

---

## Label Formats

### Supported Input Formats

Labels can be provided in multiple formats:

#### 1. String Format (Recommended)

```python
# Single label
labels="backend"

# Multiple labels (comma-separated, no spaces)
labels="backend,frontend,api"

# Complex names with hyphens
labels="api-integration,frontend-ui,db-optimization"
```

#### 2. Array Format

```python
# Python list
labels=["backend", "frontend", "api"]

# JSON array string
labels='["backend", "frontend", "api"]'
```

### Label Naming Rules

- **Allowed characters**: Letters, numbers, hyphens, underscores
- **Maximum length**: 100 characters
- **Case sensitive**: `Backend` and `backend` are different labels
- **Whitespace**: Automatically trimmed from start and end
- **Empty labels**: Not allowed, will be filtered out

#### Valid Label Names

```python
✅ "backend"
✅ "api-integration"
✅ "frontend_ui"
✅ "db-optimization-v2"
✅ "security-audit-2025"
```

#### Invalid Label Names

```python
❌ ""  # Empty string
❌ "   "  # Only whitespace
❌ "label with spaces"  # Spaces not allowed (use hyphens instead)
❌ "label@special"  # Special characters not allowed
```

---

## Querying and Filtering

### Filter Tasks by Label

```python
# Filter tasks by single label
result = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    labels="backend"  # Only tasks with "backend" label
)

# Filter by multiple labels (AND logic)
result = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    labels="backend,security"  # Tasks with BOTH labels
)
```

### Search Tasks by Label

```python
# Search across all text fields including label names
result = mcp__agenthub_http__manage_task(
    action="search",
    query="backend api",  # Matches tasks with these terms
    git_branch_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### Get All Labels

```python
# Retrieve all unique labels for a branch
result = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000"
)

# Extract unique labels from response
all_labels = set()
for task in result["tasks"]:
    for label in task.get("labels", []):
        all_labels.add(label["name"])
```

---

## Label Management

### Adding Labels to Existing Task

```python
# Update task to add new labels
result = mcp__agenthub_http__manage_task(
    action="update",
    task_id="a25d17f8-6780-41b4-8fa1-520daa12619e",
    labels="backend,api,security,testing"  # Overwrites existing labels
)
```

### Removing Labels from Task

```python
# Remove all labels
result = mcp__agenthub_http__manage_task(
    action="update",
    task_id="a25d17f8-6780-41b4-8fa1-520daa12619e",
    labels=""  # Empty string removes all labels
)

# Remove specific label (update with remaining labels)
# Current labels: backend, api, security
result = mcp__agenthub_http__manage_task(
    action="update",
    task_id="a25d17f8-6780-41b4-8fa1-520daa12619e",
    labels="backend,api"  # Removes "security" label
)
```

### Label Reuse

Labels are automatically reused across tasks:

```python
# Task 1
task1 = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Backend Task 1",
    assignees="coding-agent",
    labels="backend,api"
)

# Task 2 - Reuses existing "backend" and "api" labels
task2 = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Backend Task 2",
    assignees="coding-agent",
    labels="backend,api"  # Same labels, reused from Task 1
)

# Result: Only one "backend" and one "api" label in database
# Both tasks reference the same label entries
```

---

## Error Handling

### Common Errors and Solutions

#### 1. Missing Timestamps (System Error)

**Error**:
```json
{
  "success": false,
  "error": "Label validation failed",
  "details": "Label timestamps cannot be None. Use datetime.now(timezone.utc) to generate timestamps.",
  "error_type": "validation_error"
}
```

**Solution**: This is a system error. Report to development team. The application should always provide timestamps.

---

#### 2. Timezone-Naive Timestamps

**Error**:
```json
{
  "success": false,
  "error": "Label validation failed",
  "details": "Label timestamps must be timezone-aware. Use datetime.now(timezone.utc) instead of datetime.now(). Current timestamps are timezone-naive (missing tzinfo).",
  "error_type": "validation_error"
}
```

**Solution**: System error. All timestamps must be UTC-aware. If encountered, report the specific operation that triggered it.

---

#### 3. Non-UTC Timezone

**Error**:
```json
{
  "success": false,
  "error": "Label validation failed",
  "details": "Label timestamps must be in UTC timezone. Current timezone: created_at=America/New_York, updated_at=UTC. Convert to UTC using: timestamp.astimezone(timezone.utc)",
  "error_type": "validation_error"
}
```

**Solution**: System error. All timestamps must be in UTC. Report if encountered.

---

#### 4. Empty Label Name

**Error**:
```json
{
  "success": false,
  "error": "Label validation failed",
  "details": "Label name cannot be empty. Provide a valid label name (e.g., 'backend', 'security', 'api-integration')",
  "error_type": "validation_error"
}
```

**Solution**: Ensure label names are not empty strings or only whitespace.

```python
# ❌ Wrong
labels=""  # Empty
labels="backend,,frontend"  # Empty middle value

# ✅ Correct
labels="backend,frontend"  # No empty values
```

---

#### 5. Invalid Label Format

**Error**:
```json
{
  "success": false,
  "error": "Label validation failed",
  "details": "Label color must be in hex format (e.g., '#0066cc'). Current value: 'blue' is invalid.",
  "error_type": "validation_error"
}
```

**Solution**: Use hex color codes when specifying custom colors.

---

## Best Practices

### 1. Label Naming Conventions

```python
# ✅ Good naming conventions
"backend"           # Category
"api-integration"   # Feature area
"security-audit"    # Task type
"high-priority"     # Priority indicator
"v2.0"              # Version
"bug-fix"           # Type of work

# ❌ Avoid
"Backend Task"      # No spaces
"TO-DO"             # Too generic
"fix"               # Too vague
```

### 2. Consistent Label Usage

```python
# Define standard labels for your project
STANDARD_LABELS = {
    # Categories
    "backend", "frontend", "fullstack", "infrastructure",

    # Technologies
    "python", "typescript", "react", "postgresql",

    # Types
    "feature", "bug-fix", "enhancement", "refactor",

    # Priority
    "critical", "high-priority", "low-priority",

    # Status
    "blocked", "in-review", "needs-testing"
}

# Use consistently across all tasks
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Fix login bug",
    assignees="debugger-agent",
    labels="backend,bug-fix,critical"  # Standard labels
)
```

### 3. Label Organization

```python
# Group related labels with prefixes
"type:feature"
"type:bug-fix"
"type:enhancement"

"area:auth"
"area:api"
"area:ui"

"priority:critical"
"priority:high"
"priority:medium"
```

### 4. Performance Optimization

```python
# ✅ Efficient: Filter by label first, then other criteria
result = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id",
    labels="backend",  # Database-indexed filter
    status="in_progress"
)

# ❌ Less efficient: Retrieve all, filter in application
all_tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id"
)
filtered = [t for t in all_tasks if "backend" in [l["name"] for l in t["labels"]]]
```

---

## Examples

### Example 1: Feature Development Workflow

```python
# Step 1: Create epic with high-level labels
epic = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="User Authentication System",
    assignees="system-architect-agent",
    labels="feature,backend,security,high-priority"
)

# Step 2: Create implementation tasks with specific labels
backend_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Implement JWT authentication",
    assignees="coding-agent,security-auditor-agent",
    labels="backend,api,authentication,python",
    dependencies=epic["task"]["id"]
)

frontend_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Build login UI",
    assignees="shadcn-ui-expert-agent",
    labels="frontend,ui,authentication,react",
    dependencies=epic["task"]["id"]
)

# Step 3: Create testing task
test_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Authentication test suite",
    assignees="test-orchestrator-agent",
    labels="testing,integration,authentication",
    dependencies=f"{backend_task['task']['id']},{frontend_task['task']['id']}"
)

# Step 4: Query all authentication tasks
auth_tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id",
    labels="authentication"
)

print(f"Found {len(auth_tasks['tasks'])} authentication tasks")
```

### Example 2: Bug Tracking

```python
# Report bug with appropriate labels
bug = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Login fails with special characters",
    assignees="debugger-agent",
    labels="bug-fix,backend,authentication,critical"
)

# Add investigation findings
mcp__agenthub_http__manage_task(
    action="update",
    task_id=bug["task"]["id"],
    details="Root cause: password validation not escaping special chars",
    labels="bug-fix,backend,authentication,critical,security"  # Added security
)

# After fix, update labels
mcp__agenthub_http__manage_task(
    action="update",
    task_id=bug["task"]["id"],
    status="done",
    labels="bug-fix,backend,authentication,resolved"  # Changed critical to resolved
)
```

### Example 3: Sprint Planning

```python
# Get all high-priority backend tasks for sprint
sprint_tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id",
    labels="backend,high-priority",
    status="todo"
)

# Assign to sprint with sprint label
for task in sprint_tasks["tasks"][:5]:  # Top 5 tasks
    current_labels = ",".join([l["name"] for l in task["labels"]])

    mcp__agenthub_http__manage_task(
        action="update",
        task_id=task["id"],
        labels=f"{current_labels},sprint-42"  # Add sprint label
    )

# Query sprint tasks
sprint_42_tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id",
    labels="sprint-42"
)
```

### Example 4: Technology Stack Tracking

```python
# Create tasks with technology labels
python_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Optimize database queries",
    assignees="coding-agent",
    labels="backend,python,postgresql,performance"
)

react_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Improve component rendering",
    assignees="shadcn-ui-expert-agent",
    labels="frontend,react,typescript,performance"
)

# Find all Python-related tasks
python_tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id",
    labels="python"
)

# Find all performance optimization tasks
perf_tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id="branch-id",
    labels="performance"
)
```

---

## API Reference Summary

### Task Creation with Labels

| Parameter | Type | Required | Format | Example |
|-----------|------|----------|--------|---------|
| `labels` | string or array | No | Comma-separated or JSON array | `"backend,api"` or `["backend", "api"]` |

### Label Object Structure

```typescript
interface Label {
  id: string;              // UUID
  name: string;            // Label name (max 100 chars)
  color: string;           // Hex color code (e.g., "#0066cc")
  description: string;     // Optional description
  created_at: string;      // ISO 8601 UTC timestamp
  updated_at: string;      // ISO 8601 UTC timestamp
}
```

### Supported Operations

| Operation | Action | Parameters | Description |
|-----------|--------|------------|-------------|
| Create with labels | `create` | `labels` | Create task with initial labels |
| Update labels | `update` | `task_id`, `labels` | Replace task labels |
| Filter by label | `list` | `labels` | Get tasks with specific labels |
| Search labels | `search` | `query` | Search across label names |
| Remove labels | `update` | `task_id`, `labels=""` | Remove all labels from task |

---

## Related Documentation

- **Integration Tests**: [label-integration-test-coverage.md](../testing-qa/label-integration-test-coverage.md)
- **Troubleshooting**: [label-timestamp-errors.md](../troubleshooting-guides/label-timestamp-errors.md)
- **Test Report**: [agenthub-mcp-tools-test-report-2025-10-22.md](../testing-qa/agenthub-mcp-tools-test-report-2025-10-22.md)

---

## Support

For issues or questions:
1. Check [troubleshooting guide](../troubleshooting-guides/label-timestamp-errors.md)
2. Review [test coverage documentation](../testing-qa/label-integration-test-coverage.md)
3. Report system errors to development team with full error details
