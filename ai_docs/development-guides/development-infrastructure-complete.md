# Development Infrastructure - Complete Guide

## Quick Reference

| Category | Key Tools/Patterns | Location |
|----------|-------------------|----------|
| **Test System** | TDD, fixtures, assertions, marks | `agenthub_main/src/tests/` |
| **Docker** | Docker menu, build configs, hot reload | `docker-system/docker-menu.sh` |
| **Logging** | Structured logging, error handling | `fastmcp/task_management/infrastructure/logging` |
| **HMR Debug** | Vite plugin, WebSocket monitoring | `agenthub-frontend/vite.config.ts` |
| **Frontend UX** | Toasts, optimistic updates, error recovery | `agenthub-frontend/src/components/ui/` |

---

## Test System

### Test Organization

**Directory Structure**:
```
src/tests/
├── utils/                  # Centralized utilities
│   ├── database_utils.py   # Database operations
│   ├── mcp_client_utils.py # MCP protocol
│   ├── assertion_helpers.py # Domain assertions
│   └── test_patterns.py    # Standardized patterns
├── unit/                   # Isolated components
├── integration/            # Multi-component
├── e2e/                    # Full workflows
├── performance/            # Performance/load
└── conftest.py             # Global pytest config
```

**Test Categories**:

| Category | Purpose | Duration | Coverage Goal |
|----------|---------|----------|---------------|
| **Unit** | Isolated components | < 5 min | 80%+ |
| **Integration** | Component interactions | < 15 min | Key workflows |
| **E2E** | Complete workflows | < 30 min | Critical paths |
| **Performance** | Timing/resources | Optional | Response times |

### Patterns

**Database Pattern**:
```python
from tests.utils import create_test_project_data, TestDataBuilder, cleanup_test_data

# Simple
test_data = create_test_project_data()
create_database_records(test_data)
# ... test logic ...
cleanup_test_data(test_data)

# Custom builder
test_data = (TestDataBuilder()
            .with_project_name("Custom")
            .with_branch_name("feature-branch")
            .build())
```

**MCP Tool Pattern**:
```python
from tests.utils import MCPToolTestPattern

pattern = MCPToolTestPattern("manage_task")
pattern.test_successful_call(manage_task, {"action": "list"})
pattern.test_missing_required_parameter(manage_task, "action")
```

**Assertion Helpers**:
```python
from tests.utils import (
    assert_task_structure,
    assert_context_inheritance,
    assert_mcp_tool_response,
    assert_pagination_structure
)

assert_mcp_tool_response(result, expected_success=True)
assert_task_structure(result["task"], required_fields=["id", "title"])
assert_domain_event_structure(event, "TaskCreated")
```

### Pytest Marks and Fixtures

**Standard Marks**:
```python
@pytest.mark.unit          # Isolated
@pytest.mark.integration   # Multi-component
@pytest.mark.e2e          # Full workflows
@pytest.mark.performance  # Performance
@pytest.mark.database     # Requires DB
@pytest.mark.mcp          # MCP protocol
```

**Fixtures**:
```python
from tests.utils import test_project_data, valid_git_branch_id

def test_with_project_data(test_project_data):
    """Auto cleanup"""
    project_id = test_project_data.project_id
    branch_id = test_project_data.git_branch_id
```

### Running Tests

```bash
# All tests
pytest

# By category
pytest -m unit
pytest -m integration

# With coverage
pytest --cov=src --cov-report=html

# Single test
pytest path/to/test.py::test_function

# Verbose + debugging
pytest -v -s --pdb
```

### Coverage Analysis

```bash
# Generate report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# List tests
pytest --collect-only
pytest --collect-only -m unit
```

---

## Docker Development System

### Docker Menu Access

**Convenience Wrapper**:
```bash
./build-menu.sh               # Interactive menu
./build-menu.sh start-dev     # Start development
./build-menu.sh restart-dev   # Restart with changes
./build-menu.sh stop-dev      # Stop services
```

**Direct Access**:
```bash
./docker-system/docker-menu.sh
```

### Build Configurations

| Configuration | Database | Ports | Use Case |
|--------------|----------|-------|----------|
| **PostgreSQL Local** | Local PostgreSQL | 5432, 8000, 3800 | Full local development |
| **Supabase Cloud** | Remote Supabase | 8000, 3800 | Cloud integration |
| **Supabase + Redis** | Remote + Redis | 6379, 8000, 3800 | Production-like |
| **Development Mode** | Native Python | No Docker | Fastest iteration |

### System Architecture

```
Docker Menu System v3.0
├── Build Optimization
│   ├── --no-cache builds
│   ├── BuildKit optimization
│   ├── Port conflict resolution
│   └── Python cache clearing
│
├── PostgreSQL Local ──── 5432, 8000, 3800
├── Supabase Cloud ────── Remote DB, 8000, 3800
├── Redis + Supabase ──── 6379, 8000, 3800
└── Development Mode ──── Native with hot reload
```

### Environment Configuration

**.env Requirements**:
```bash
# Database
DATABASE_TYPE=postgresql|supabase
DATABASE_URL=postgresql://user:pass@host:port/db

# Supabase (if using)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

# Authentication
AUTH_ENABLED=true|false
JWT_SECRET_KEY=your-secret-key

# Development
FASTMCP_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
ENV=development|production
```

### Hot Reload

**Backend**:
- Python files reload on change (FastAPI `--reload`)
- Docker volume mounts for real-time sync
- FastMCP development server

**Frontend**:
- Vite HMR (Hot Module Replacement)
- React Fast Refresh
- TypeScript incremental compilation

### Performance Optimizations

| Feature | Benefit |
|---------|---------|
| **--no-cache builds** | Fresh code changes |
| **BuildKit** | Parallel layer building |
| **Multi-stage builds** | Smaller images |
| **Memory limits** | 256M-512M per container |
| **Health checks** | Auto-restart on failures |

### Troubleshooting

**Port Conflicts**:
```bash
# Auto-stopped by menu
docker container prune -f
```

**Build Cache**:
```bash
# Use "Force Complete Rebuild"
find . -name "__pycache__" -exec rm -rf {} +
```

**Database Connection**:
- Verify .env configuration
- Check service health status
- Use database shell for debugging

---

## Error Handling & Logging

### Exception Hierarchy

```
TaskManagementException (Base)
├── ValidationException
├── ResourceNotFoundException
├── ResourceAlreadyExistsException
├── DatabaseException
│   ├── DatabaseConnectionException
│   └── DatabaseIntegrityException
├── ConcurrencyException
└── ConfigurationException

TaskDomainError (Base)
├── TaskNotFoundError
├── InvalidTaskStateError
├── TaskCompletionBlockedException
└── AutoRuleGenerationError
```

### Error Severity

| Level | Description | Examples |
|-------|-------------|----------|
| **LOW** | Retryable/ignorable | Validation errors |
| **MEDIUM** | Log and monitor | Not found errors |
| **HIGH** | Immediate attention | Database errors |
| **CRITICAL** | System-breaking | Configuration failures |

### Error Response Format

```json
{
  "success": false,
  "error": "User-friendly message",
  "error_code": "STANDARDIZED_CODE",
  "severity": "medium",
  "details": {
    "field": "affected_field",
    "resource_id": "identifier"
  },
  "request_id": "unique-id",
  "recoverable": true
}
```

### Logging Configuration

**Environment Variables**:
```bash
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
LOG_DIR=logs
LOG_FORMAT=text|json
```

**Initialization**:
```python
from fastmcp.task_management.infrastructure.logging import TaskManagementLogger, init_logging

init_logging()
logger = TaskManagementLogger.get_logger(__name__)

# Add context
ctx_logger = TaskManagementLogger.add_context(
    logger,
    user_id="user123",
    task_id="task456",
    operation="create_task"
)
ctx_logger.info("Task created")
```

### Structured Logging

**Log Files**:
1. `agenthub.log` - All levels (10MB rotation, 5 backups)
2. `agenthub_errors.log` - Errors only

**Log Levels**:
```python
logger.debug("Detailed diagnostic")
logger.info("General informational")
logger.warning("Unexpected but recoverable")
logger.error("Error, application continues", exc_info=True)
logger.critical("System might not recover", exc_info=True)
```

### Error Handling Patterns

**Decorator Pattern**:
```python
from fastmcp.task_management.interface.utils.error_handler import handle_operation_error

@handle_operation_error("task creation")
async def create_task(self, request: CreateTaskRequest):
    pass
```

**Log Operation**:
```python
from fastmcp.task_management.infrastructure.logging import log_operation

@log_operation("create_task")
async def create_task(self, task_id: str, **kwargs):
    # Auto-logs start, completion, errors
    pass
```

**Manual Handling**:
```python
try:
    result = await task_service.create_task(request)
except ValidationException as e:
    logger.warning(f"Validation failed: {e}")
    return {"success": False, "error": e.user_message}
except TaskDomainError as e:
    logger.error(f"Domain error: {e}", exc_info=True)
    raise
```

### HTTP Status Code Mapping

| Status | Error Types |
|--------|-------------|
| **400** | Validation, low severity domain errors |
| **404** | Resource not found |
| **409** | Medium severity, state conflicts |
| **422** | Input validation failures |
| **500** | Unexpected, high severity |
| **503** | Database, critical system issues |

### Error Recovery

**Automatic Retry**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def create_task_with_retry(request):
    return await task_service.create_task(request)
```

**Graceful Degradation**:
```python
async def get_task_details(task_id: str):
    task = await get_task(task_id)

    try:
        task["analytics"] = await get_task_analytics(task_id)
    except ExternalServiceException:
        logger.warning(f"Analytics unavailable for {task_id}")
        task["analytics"] = None

    return task
```

### January 2025 Critical Fixes ✅

| Issue | Status | Impact |
|-------|--------|--------|
| `UnboundLocalError: TaskId` | RESOLVED | Import scoping fixed |
| `TypeError: object is not awaitable` | RESOLVED | Async patterns fixed |
| `FOREIGN KEY constraint failed` | RESOLVED | Schema updated |
| `ModuleNotFoundError: hierarchical_context` | RESOLVED | Unified imports |

**Validation Commands**:
```bash
# Test TaskId scoping
mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="test-uuid",
    title="Validation",
    dependencies=["dep1", "dep2"]
)

# Test async patterns
mcp__agenthub_http__manage_context(
    action="create",
    task_id="test-uuid",
    data_title="Test"
)
```

---

## HMR (Hot Module Replacement) Debugging

### Server-Side Debugging

**HMR Debug Plugin** (vite.config.ts):
- File change detection with timestamps
- Module graph analysis
- WebSocket monitoring
- Error logging with context

**Output Format**:
```
🔥 [2025-10-16T06:18:04.664Z] HMR Update Triggered
   📄 File: /path/to/file.tsx
   🔗 Module graph connections: 0
   ↳ Module: /path/to/module.tsx
      Invalidated: yes
      Importers: 3
```

### Client-Side Debugging

**Event Listeners** (index.tsx):

| Event | Purpose |
|-------|---------|
| `vite:beforeUpdate` | Before HMR applies |
| `vite:afterUpdate` | After successful HMR |
| `vite:error` | HMR errors |
| `vite:beforeFullReload` | Full reload required |
| `vite:ws:connect` | WebSocket connected |
| `vite:ws:disconnect` | WebSocket lost |

**Browser Console**:
```
🔥 HMR Client Initialized
⚡ HMR Update Received
✅ HMR Update Applied
🔌 HMR WebSocket Connected
```

### Troubleshooting HMR

**WebSocket Connection Failed (WSL2)**:
```typescript
// vite.config.ts - Fix for WSL2
hmr: {
  protocol: 'ws',
  host: 'localhost',  // Client uses localhost
  port: 3800,
  clientPort: 3800
}
// Server host remains '0.0.0.0'
```

**Files Change But Browser Doesn't Update**:
1. Check server logs for "🔥 HMR Update Triggered"
   - No: Watch system issue, check permissions
2. Check browser for "⚡ HMR Update Received"
   - No: WebSocket connection issue
3. Check browser for "✅ HMR Update Applied"
   - No: Check for errors in console

**Full Page Reloads**:
- Look for "🔄 Full Page Reload Required"
- Common: CSS changes, config changes, certain imports

### HMR Configuration

```typescript
// vite.config.ts:86-108
server: {
  host: '0.0.0.0',
  port: 3800,
  hmr: {
    protocol: 'ws',
    host: 'localhost',
    port: 3800,
    overlay: true
  },
  watch: {
    usePolling: true,
    interval: 100
  },
  logLevel: 'info'
}
```

---

## Frontend UX Patterns

### Toast Notification System

**Features**:
- Multiple types: success, error, warning, info
- Auto-dismissal (customizable duration)
- Manual dismissal (close button)
- Action buttons (retry functionality)
- Smooth slide-in animations
- Dark/light theme support

**Usage**:
```typescript
import { useSuccessToast, useErrorToast } from './components/ui/toast';

const showSuccess = useSuccessToast();
const showError = useErrorToast();

// Success
showSuccess('Operation completed', 'Item updated.');

// Error with retry
showError('Network error', 'Failed to connect', {
  label: 'Retry',
  onClick: () => retryOperation()
});
```

### Optimistic UI Updates

**Flow Pattern**:
1. User clicks action button
2. UI immediately updates (optimistic)
3. Backend operation attempted
4. **Success**: Keep UI updated, show success toast
5. **Failure**: Rollback UI, show error toast with retry

**Implementation**:
```typescript
const handleDeleteBranch = async () => {
  // Backup for rollback
  const backupProjects = [...projects];

  // Optimistic update
  setProjects(prev => /* remove branch */);

  try {
    const result = await deleteBranch(branchId);
    if (result.success) {
      showSuccessToast('Branch deleted');
    } else {
      // Rollback
      setProjects(backupProjects);
      showErrorToast('Failed', result.error, {
        label: 'Retry',
        onClick: () => handleDeleteBranch()
      });
    }
  } catch (error) {
    // Rollback on network error
    setProjects(backupProjects);
    showErrorToast('Network error', error.message);
  }
};
```

### Enhanced Loading States

**Visual Feedback**:
```typescript
// Track loading
const [deletingBranches, setDeletingBranches] = useState<Set<string>>(new Set());

// Mark loading
setDeletingBranches(prev => new Set(prev).add(branchId));

// Show spinner
{deletingBranches.has(branch.id) ? (
  <div className="animate-spin h-3 w-3 border-2" />
) : (
  <Trash2 className="w-3 h-3" />
)}
```

### Best Practices

**Optimistic Updates**:
- Use for operations likely to succeed
- Ensure rollback capability
- When users expect immediate feedback

**Toast Guidelines**:
- Success: Brief and positive (5 seconds)
- Errors: Clear and actionable (8 seconds)
- Always provide retry for recoverable errors

**Error Recovery**:
1. Detect error (API or network)
2. Rollback UI immediately
3. Show clear error message
4. Enable retry or alternatives
5. Log technical details for debugging

---

## MCP Server Architecture

### Core Structure

```
agenthub_main/src/fastmcp/server/
├── mcp_entry_point.py      # Dual auth entry
├── server.py               # FastMCP core
├── connection_manager.py   # Connection state
├── middleware.py           # Auth & request
├── http_server.py         # HTTP transport
└── dependencies.py        # DI
```

### Key Components

**MCP Entry Point**:
- Dual Authentication (JWT + MCP session)
- Environment configuration
- Database initialization
- Middleware stack
- Transport selection (stdio/streamable-http)

**Tool Registration**:
```python
from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
ddd_tools = DDDCompliantMCPTools()
ddd_tools.register_tools(server)
```

**Authentication Middleware**:
```python
middleware_stack = [
    Middleware(DualAuthMiddleware),      # JWT
    Middleware(RequestContextMiddleware), # Context
    Middleware(DebugLoggingMiddleware)   # Logging
]
```

### Frontend-Backend Communication

```
Frontend (React/TypeScript)
├── api.ts            # Main API
├── apiV2.ts          # Authenticated
├── mcpTokenService.ts # Tokens
└── authContext.tsx    # Auth state
     │
     │ HTTP/REST
     ▼
Backend (Python/FastMCP)
├── HTTP Server (8000)
├── MCP Server
└── Dual Auth
```

**API Layers**:

| API | Base URL | Auth | Isolation | Use Case |
|-----|----------|------|-----------|----------|
| **V1** | `/mcp/` | Optional | None | Anonymous/fallback |
| **V2** | `/api/v2/` | JWT required | User-scoped | Authenticated |

---

## Performance Monitoring

### Log Analysis

```bash
# Find errors for task
grep -i "task_id.*task123" logs/agenthub.log | grep ERROR

# Database errors
grep "DATABASE_ERROR" logs/agenthub_errors.log

# Real-time
tail -f logs/agenthub.log | jq '.'
```

### Operation Duration

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Completed create_task in 0.145s",
  "operation": "create_task",
  "duration_ms": 145
}
```

### Docker Performance

- Real-time container resource usage
- System memory and disk utilization
- Connection statistics and health

---

## Related Documentation
- [DDD Architecture Complete](./ddd-architecture-complete.md)
- [Development Workflow Complete](./development-workflow-complete.md)
- [Complete Operations Guide](../operations/complete-operations-guide.md)
