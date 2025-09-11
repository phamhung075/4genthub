# Comprehensive Troubleshooting Guide

## Overview

This guide covers common issues, known problems, and systematic troubleshooting approaches for the DhafnckMCP system.

## Quick Diagnostic Commands

### System Health Check
```bash
# Check MCP server health
mcp__dhafnck_mcp_http__manage_connection(action="health_check")

# Check database connectivity
mcp__dhafnck_mcp_http__manage_project(action="list")

# Check context with inheritance
mcp__dhafnck_mcp_http__manage_context(action="get", level="task", context_id="your-task-id", include_inherited=True)

# Verify January 2025 fixes are working (all should succeed without errors)
# Test task creation (validates TaskId scoping fix)
mcp__dhafnck_mcp_http__manage_task(
    action="create", 
    git_branch_id="test-branch-id", 
    title="Health check task"
)

# Test context operations (validates async repository fixes)
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    task_id="test-task-id",
    data_title="Test context"
)
```

### Agent System Check
```bash
# Verify agent is active
mcp__dhafnck_mcp_http__call_agent(name_agent="@master_orchestrator_agent")

# Check agent assignments
mcp__dhafnck_mcp_http__manage_agent(action="list", project_id="your-project-id")
```

## Known Issues and Solutions

### 🆕 January 2025 Critical Fixes

> **✅ RESOLVED**: The following issues have been fixed and are no longer problems. This section is maintained for historical reference and to help diagnose similar issues in the future.
> 
> **📋 Complete Fix Documentation**: For detailed technical information about these fixes, see [Unified Context System Fixes - January 19, 2025](fixes/unified_context_system_fixes_2025_01_19.md)
>
> **🔄 Context System Update**: As of January 2025, `manage_hierarchical_context` has been deprecated. Use `manage_context` for all context operations. All examples in this guide have been updated to reflect this change.

#### ✅ TaskId Import Scoping Error (FIXED)

**Problem**: `UnboundLocalError: cannot access local variable 'TaskId' where it is not associated with a value`

**Root Cause**: Redundant import statements inside loops created variable scoping conflicts

**How It Was Fixed**:
- Removed redundant `TaskId` imports inside dependency conversion loops
- Import statements now remain at module level only
- Fixed in: `src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py`

**If You Encounter Similar Issues**:
```python
# ❌ WRONG: Import inside loop
for item in items:
    from module import Class  # Creates scoping issues
    result = Class(item)

# ✅ CORRECT: Import at module level
from module import Class

for item in items:
    result = Class(item)
```

#### ✅ Async Repository Pattern Mismatch (FIXED)

**Problem**: Tests expecting async methods but repository implementation was synchronous

**Root Cause**: Inconsistency between test patterns and repository implementation

**How It Was Fixed**:
- Converted all TaskContextRepository methods to async patterns
- Updated method signatures: `def method()` → `async def method()`
- Fixed in: `src/fastmcp/task_management/infrastructure/repositories/task_context_repository.py`

**If You Encounter Similar Issues**:
```python
# Ensure consistency between tests and implementation
# If tests use @pytest.mark.asyncio and await calls:
async def test_repository_method():
    result = await repository.create(entity)  # ✅

# Then repository must be async:
async def create(self, entity):  # ✅
    # implementation
```

#### ✅ Database Schema Mismatch (FIXED)

**Problem**: TaskContext table had outdated column structure (`parent_project_id` instead of `parent_branch_id`)

**Root Cause**: Database schema not updated to match 4-tier hierarchy (Global → Project → Branch → Task)

**How It Was Fixed**:
- Dropped and recreated `task_contexts` table with correct schema
- Updated foreign key references to point to `project_git_branchs` table
- Aligned with hierarchical context system requirements

**If You Encounter Similar Issues**:
```bash
# Check table schema matches model definitions
PRAGMA table_info(task_contexts);

# Look for correct foreign key references:
# parent_branch_id → project_git_branchs(id)
# parent_branch_context_id → branch_contexts(branch_id)
```

#### ✅ Context Manager Mock Configuration (FIXED)

**Problem**: SQLAlchemy errors "Incorrect number of values in identifier to formulate primary key"

**Root Cause**: Improper mock configuration for database context managers

**How It Was Fixed**:
- Fixed mock method names: `get_session` → `get_db_session`
- Properly mocked context manager `__enter__` and `__exit__` methods
- Updated expected method calls from `commit()` to `flush()`

**If You Encounter Similar Issues**:
```python
# ✅ CORRECT: Mock context manager properly
mock_session = Mock()
mock_context_manager = MagicMock()
mock_context_manager.__enter__ = Mock(return_value=mock_session)
mock_context_manager.__exit__ = Mock(return_value=None)
repository.get_db_session = Mock(return_value=mock_context_manager)
```

#### ✅ Import Path Conflicts (FIXED)

**Problem**: Import errors for UnifiedContextService and related classes

**Root Cause**: Inconsistent import paths between `hierarchical_context_service` and `unified_context_service`

**How It Was Fixed**:
- Updated all import statements to use correct unified context service paths
- Fixed factory import locations from infrastructure to application/factories
- Resolved in multiple files across the application layer

**If You Encounter Similar Issues**:
```python
# ✅ CORRECT: Use unified context service paths
from .unified_context_service import UnifiedContextService
from ..factories.unified_context_facade_factory import UnifiedContextFacadeFactory

# ❌ WRONG: Old hierarchical paths
from .hierarchical_context_service import UnifiedContextService
```

### 1. Task Completion Validation Issue ⚠️

**Problem**: Task completion fails with "Task completion requires context to be created first"

**Root Cause**: Task completion validation requires hierarchical context to exist before completion

**Solution**:
```bash
# ALWAYS update context before completing task
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="task",
    context_id="your-task-id",
    data={
        "progress": "Task implementation completed",
        "discoveries": ["Key findings during implementation"],
        "decisions": ["Technical decisions made"]
    }
)

# THEN complete the task
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id="your-task-id",
    completion_summary="Detailed completion summary",
    testing_notes="Testing performed and results"
)
```

**Prevention**: Always use the workflow pattern:
1. Update context during work
2. Complete task with detailed summary

### 2. Branch Context Initialization Issue

**Problem**: "Branch default_branch not found" error

**Root Cause**: git_branch_name parameter replaced with git_branch_id (UUID)

**Solution**:
```bash
# Use UUID instead of branch name
# WRONG:
git_branch_name="main"

# CORRECT:
git_branch_id="uuid-from-branch-creation"

# Get branch ID from project listing
branches = mcp__dhafnck_mcp_http__manage_git_branch(
    action="list",
    project_id="your-project-id"
)
```

### 3. Database Mode Configuration Issues

**Problem**: Server fails to start with database connection errors

**Diagnosis**:
```bash
# Check database file permissions
ls -la /data/dhafnck_mcp.db

# Check Docker container status
docker ps
docker logs dhafnck-mcp-container
```

**Solutions by Mode**:

#### Docker Container Mode
```bash
# Ensure database volume is mounted
docker run -v /path/to/data:/data dhafnck-mcp

# Check database file exists
docker exec -it container-name ls -la /data/dhafnck_mcp.db
```

#### Local Development Mode
```bash
# Ensure Docker database is accessible
# Database MUST be at /data/dhafnck_mcp.db
# Rebuild Docker container for code changes:
docker-compose down
docker-compose build
docker-compose up
```

#### MCP STDIN Mode
```bash
# Uses local database (dhafnck_mcp_local.db)
# This is expected and normal
# Database will be created automatically
```

### 4. Agent Role Switching Issues

**Problem**: Work attempted without proper agent role

**Error Messages**:
- "You have NO permission to work on projects if no agent role active"
- "You do NOT have permission to free run on projects"

**Solution**:
```bash
# ALWAYS switch to appropriate agent before work
mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# For different work types:
# Debug work: @debugger_agent
# Implementation: @coding_agent  
# Testing: @test_orchestrator_agent
# Planning: @task_planning_agent
# Security: @security_auditor_agent
```

### 5. Context Resolution Performance Issues

**Problem**: Slow context resolution or timeouts

**Diagnosis**:
```bash
# Check cache status
mcp__dhafnck_mcp_http__manage_context(
    action="get_health"
)

# Check resolved context with full inheritance
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="task",
    context_id="your-task-id"
)
```

**Solutions**:
```bash
# Clear cache if hit ratio is low
mcp__dhafnck_mcp_http__manage_context(
    action="cleanup_cache"
)

# Force refresh for specific context
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="task",
    context_id="your-task-id",
    force_refresh=true
)
```

### 6. Delegation Queue Issues

**Problem**: Patterns not being shared between projects

**Diagnosis**:
```bash
# Check context delegations (use manage_context with delegate action)
mcp__dhafnck_mcp_http__manage_context(
    action="list",
    level="project"  # Check at higher level for delegated items
)

# List contexts at project level to see delegated patterns
mcp__dhafnck_mcp_http__manage_context(
    action="list",
    level="project"
)
```

**Solutions**:
```bash
# Delegate context to higher level
mcp__dhafnck_mcp_http__manage_context(
    action="delegate",
    level="task",
    delegation_id="delegation-uuid"
)

# Remove delegated content by updating context
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    delegation_id="delegation-uuid",
    rejection_reason="Too specific for project scope"
)
```

## Systematic Troubleshooting Approach

### Step 1: System Health Assessment
```bash
# 1. Check MCP connection
health = mcp__dhafnck_mcp_http__manage_connection(action="health_check")

# 2. Verify database connectivity
projects = mcp__dhafnck_mcp_http__manage_project(action="list")

# 3. Check agent system
agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@master_orchestrator_agent")
```

### Step 2: Context Validation
```bash
# 1. Get resolved context with inheritance
resolved_context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="task",
    context_id="your-task-id"
)

# 2. Check for missing contexts
if validation.errors:
    # Create missing contexts
    mcp__dhafnck_mcp_http__manage_context(
        action="create",
        level="project",
        context_id="project-id",
        data={"title": "Project Title"}
    )
```

### Step 3: Data Integrity Check
```bash
# 1. Verify project structure
project = mcp__dhafnck_mcp_http__manage_project(
    action="get",
    project_id="your-project-id"
)

# 2. Check branch associations
branches = mcp__dhafnck_mcp_http__manage_git_branch(
    action="list",
    project_id="your-project-id"
)

# 3. Validate task relationships
tasks = mcp__dhafnck_mcp_http__manage_task(
    action="list",
    git_branch_id="your-branch-id"
)
```

### Step 4: Performance Analysis
```bash
# 1. Check cache performance
cache_status = mcp__dhafnck_mcp_http__manage_context(
    action="get_health"
)

# 2. Monitor resolution times
# Look for resolution_timing in responses

# 3. Check project-level contexts for delegations
project_contexts = mcp__dhafnck_mcp_http__manage_context(
    action="list",
    level="project"
)
```

## Error Categories and Solutions

### Database Errors

#### "Database locked" Error
```bash
# Solution: Restart application
# For Docker: docker-compose restart
# For local: Stop server, wait 5 seconds, restart
```

#### "Table doesn't exist" Error
```bash
# Solution: Run database migrations
# Check that DATABASE_URL is correct
# Verify database initialization
```

#### "Foreign key constraint failed" Error
```bash
# Solution: Check entity relationships
# Ensure parent entities exist before creating children
# Verify git_branch_id is valid UUID, not branch name
```

### Context Errors

#### "Context resolution failed" Error
```bash
# Diagnosis:
context_check = mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="task",
    context_id="failing-task-id"
)

# Solutions based on validation results:
if "missing_parent" in validation.errors:
    # Create missing parent context
elif "circular_dependency" in validation.errors:
    # Break circular reference
elif "cache_inconsistency" in validation.errors:
    # Clear cache and rebuild
```

#### "Invalid context level" Error
```bash
# Solution: Use valid levels
# Valid: "global", "project", "branch", "task"
# Invalid: "user", "organization", "team"
```

### Agent Errors

#### "Agent not available" Error
```bash
# Solution: Use available agents
available_agents = [
    "@master_orchestrator_agent",
    "@coding_agent", 
    "@debugger_agent",
    "@test_orchestrator_agent",
    "@task_planning_agent",
    "@ui_designer_agent",
    "@security_auditor_agent",
    "@documentation_agent"
]
```

#### "Agent operation timeout" Error
```bash
# Solution: Switch to debugger agent
mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")

# Investigate timeout cause
# Check system resources
# Verify network connectivity
```

### Task Errors

#### "Task not found" Error
```bash
# Diagnosis: Check task exists
tasks = mcp__dhafnck_mcp_http__manage_task(
    action="search",
    query="task-title-or-description"
)

# Solution: Use correct task ID from search results
```

#### "Invalid task status transition" Error
```bash
# Valid transitions:
# todo → in_progress → done
# any_status → blocked
# blocked → in_progress
# any_status → cancelled

# Solution: Use valid status progression
```

## Performance Optimization Guide

### Cache Optimization
```bash
# Monitor cache performance
cache_metrics = get_cache_metrics()

# Optimal thresholds:
# hit_ratio > 80%: Good performance
# hit_ratio < 50%: Cache issues, cleanup needed
# miss_ratio high: Check invalidation patterns

# Actions:
if cache_metrics.hit_ratio < 0.5:
    mcp__dhafnck_mcp_http__manage_context(
        action="cleanup_cache"
    )
```

### Database Performance
```bash
# Check for orphaned records
# Verify index usage
# Monitor query performance

# Solutions:
# Regular cleanup of obsolete data
# Proper indexing on UUID columns
# Connection pooling optimization
```

### Memory Management
```bash
# Monitor memory usage
# Check for memory leaks in long-running operations
# Verify proper cleanup of async resources

# Solutions:
# Regular garbage collection
# Proper async context management
# Resource cleanup in finally blocks
```

## Emergency Recovery Procedures

### Complete System Reset
```bash
# 1. Stop all services
docker-compose down

# 2. Backup current database
cp /data/dhafnck_mcp.db /data/dhafnck_mcp.db.backup

# 3. Clear cache
rm -rf /tmp/dhafnck_cache/*

# 4. Restart with clean state
docker-compose up --build
```

### Data Recovery
```bash
# 1. Check backup availability
ls -la /data/*.backup

# 2. Restore from backup if needed
cp /data/dhafnck_mcp.db.backup /data/dhafnck_mcp.db

# 3. Verify data integrity
mcp__dhafnck_mcp_http__manage_project(action="list")
```

### Context System Recovery
```bash
# 1. Validate all contexts
# Run validation on all active tasks
for task_id in active_tasks:
    mcp__dhafnck_mcp_http__manage_context(
        action="resolve",
        level="task",
        context_id=task_id
    )

# 2. Rebuild missing contexts
# Create missing parent contexts
# Re-establish inheritance chains

# 3. Clear and rebuild cache
mcp__dhafnck_mcp_http__manage_context(
    action="cleanup_cache"
)
```

## Monitoring and Maintenance

### Daily Health Checks
```bash
# 1. System health
mcp__dhafnck_mcp_http__manage_connection(action="health_check")

# 2. Database size and performance
du -h /data/dhafnck_mcp.db

# 3. Cache performance
cache_status = get_cache_status()

# 4. Error rate monitoring
error_metrics = get_error_metrics()
```

### Weekly Maintenance
```bash
# 1. Database cleanup
mcp__dhafnck_mcp_http__manage_project(
    action="cleanup_obsolete",
    project_id="project-id"
)

# 2. Cache optimization
mcp__dhafnck_mcp_http__manage_context(
    action="cleanup_cache"
)

# 3. Review delegated patterns at project level
mcp__dhafnck_mcp_http__manage_context(
    action="list",
    level="project"
)
```

### Monthly Health Assessment
```bash
# 1. Full system validation
# 2. Performance trend analysis
# 3. Capacity planning review
# 4. Security audit
# 5. Backup verification
```

## Getting Help

### Log Analysis
```bash
# Check application logs
docker logs dhafnck-mcp-container

# Look for patterns:
# ERROR: Database connection failed
# WARNING: Context resolution slow
# INFO: Cache hit ratio low
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up

# Check debug output for detailed trace
```

### Support Information
When reporting issues, include:
1. Error message (exact text)
2. Steps to reproduce
3. System health check results
4. Recent log entries
5. Database mode configuration
6. Agent role and context information

### Common Support Scenarios

#### "My task won't complete"
1. Check context exists: manage_context(action="get")
2. Update context before completion
3. Verify all subtasks are completed
4. Check for validation errors

#### "Agent switching isn't working"
1. Verify agent name has @ prefix
2. Check available agents list
3. Ensure no permission errors
4. Try @master_orchestrator_agent as fallback

#### "Context data isn't inheriting"
1. Validate inheritance chain
2. Check parent contexts exist
3. Clear cache and retry
4. Verify hierarchy structure

#### "Performance is slow"
1. Check cache hit ratio
2. Validate context structure
3. Monitor database query time
4. Clean up obsolete data

## Validating January 2025 Fixes

### Quick Validation Tests
If you suspect any of the January 2025 fixes have regressed, run these tests:

```bash
# 1. Test TaskId scoping (should not show UnboundLocalError)
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="test-branch-uuid",
    title="TaskId validation test",
    dependencies=["dep1", "dep2"]  # Tests dependency processing
)

# 2. Test async repository patterns (should not show async/sync mismatch errors)
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    task_id="test-task-uuid",
    data_title="Async test context"
)

# 3. Test database schema (should not show foreign key errors)
# Create task with proper branch reference
task_result = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="valid-branch-uuid",
    title="Schema validation test"
)

# 4. Test import path resolution (should not show ModuleNotFoundError)
# Any context operation should work without import errors
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="task",
    context_id="test-task-uuid"
)
```

### Expected Results
All tests above should complete successfully without:
- ❌ `UnboundLocalError: cannot access local variable 'TaskId'`
- ❌ `TypeError: object is not awaitable` or `RuntimeWarning: coroutine was never awaited`
- ❌ `FOREIGN KEY constraint failed`
- ❌ `ModuleNotFoundError: No module named 'hierarchical_context_service'`
- ❌ `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column`

If any of these errors appear, the fixes may have regressed and need investigation.

---

This comprehensive guide should help diagnose and resolve most issues encountered in the DhafnckMCP system. For persistent issues, follow the systematic troubleshooting approach and use the emergency recovery procedures when necessary.

**Document Version**: 2.0  
**Last Updated**: January 19, 2025  
**Major Updates**: Added January 2025 critical fixes section and validation procedures