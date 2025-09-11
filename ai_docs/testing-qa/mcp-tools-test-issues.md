# MCP Tools Test Issues

## Overview

Known issues, troubleshooting steps, and resolution status for MCP tool integration testing in the DhafnckMCP platform.

## 🔴 Critical MCP Tool Issues

### High Priority Issues

#### 1. MCP Connection Timeout
- **Status**: 🔴 ACTIVE
- **Affected Tools**: All MCP tools during startup
- **Symptom**: Connection timeout after 30 seconds
- **Error Message**: 
  ```
  Connection timeout: MCP server not responding within 30 seconds
  ```
- **Root Cause**: Server startup sequence timing
- **Workaround**: Retry connection after 60 seconds
- **Resolution Timeline**: Q4 2025

#### 2. Authentication Integration with MCP Tools
- **Status**: 🟡 IN PROGRESS (Post-2025-08-25 Modernization)
- **Affected Tools**: All authenticated MCP operations
- **Symptom**: MCP tools not respecting authentication context
- **Error Message**:
  ```
  UserAuthenticationRequiredError: Operation requires authenticated user
  ```
- **Root Cause**: MCP tool layer needs authentication context passing
- **Solution**: Update MCP tool wrappers to pass authentication context
- **Progress**: 60% complete

### Medium Priority Issues

#### 3. Task Management MCP Tools  
- **Status**: 🟡 PARTIAL
- **Affected Tools**: `manage_task`, `manage_subtask`, `manage_context`
- **Symptom**: Intermittent failures in task operations
- **Root Cause**: Context resolution timing issues
- **Workaround**: Add retry logic with exponential backoff
- **Resolution**: Architecture review needed

#### 4. Agent MCP Tool Integration
- **Status**: 🟡 IN PROGRESS  
- **Affected Tools**: `call_agent`, `manage_agent`
- **Symptom**: Agent state not properly synchronized
- **Root Cause**: Agent lifecycle management
- **Solution**: Implement proper agent state tracking

## 🟡 Known Issues by Tool Category

### Task Management Tools

#### `manage_task` Issues
- **Issue**: Context validation failures
  ```python
  # Error pattern
  ValidationError: Task completion requires context to be created first
  ```
- **Cause**: Context creation dependency not enforced
- **Solution**: Always create/update context before task completion
- **Test Pattern**:
  ```python
  @patch('task_service.get_current_user_id')
  def test_task_completion_with_context(self, mock_user_id):
      mock_user_id.return_value = "test-user"
      # Create context first
      context_result = manage_context(
          action="create",
          level="task", 
          context_id=task_id,
          data={"progress": "completed"}
      )
      # Then complete task
      task_result = manage_task(action="complete", task_id=task_id)
  ```

#### `manage_subtask` Issues  
- **Issue**: Parent task context not updated
- **Cause**: Subtask completion doesn't trigger parent updates
- **Solution**: Implement parent context update hooks
- **Status**: Under development

#### `manage_context` Issues
- **Issue**: Inheritance chain resolution timeouts
- **Cause**: Deep inheritance chains cause performance issues  
- **Solution**: Implement context caching strategy
- **Workaround**: Use `force_refresh=false` for non-critical operations

### Project Management Tools

#### `manage_project` Issues
- **Issue**: Health check failures
- **Symptom**: 
  ```
  ProjectHealthCheckError: Unable to validate project integrity
  ```
- **Cause**: Database connection pool exhaustion
- **Solution**: Implement connection pool monitoring
- **Workaround**: Restart application to reset connection pool

#### `manage_git_branch` Issues
- **Issue**: Branch context initialization delays
- **Cause**: Git branch creation doesn't immediately create context
- **Solution**: Add async context creation hooks
- **Test Pattern**:
  ```python
  def test_branch_creation_with_context(self):
      branch_result = manage_git_branch(
          action="create",
          project_id=project_id,
          git_branch_name="test-branch"  # Note: git_branch_id (UUID) preferred for API calls
      )
      # Wait for context creation
      time.sleep(0.5)
      context_result = manage_context(
          action="get",
          level="branch",
          context_id=branch_result.git_branch_id
      )
      assert context_result.success is True
  ```

### Agent Management Tools

#### `call_agent` Issues
- **Issue**: Agent loading timeouts  
- **Symptom**: Agent takes >60 seconds to load
- **Cause**: Cold start performance
- **Solution**: Implement agent pre-loading
- **Workaround**: Use cached agent instances

#### `manage_agent` Issues
- **Issue**: Agent assignment conflicts
- **Cause**: Multiple agents assigned to same resource
- **Solution**: Implement agent assignment validation
- **Status**: Architecture review pending

### Compliance and Logging Tools

#### `manage_compliance` Issues
- **Issue**: Compliance validation timeouts
- **Cause**: Complex policy evaluation
- **Solution**: Implement policy caching
- **Workaround**: Use simplified compliance checks for testing

#### `manage_logging` Issues  
- **Issue**: Log buffer overflow
- **Cause**: High-volume logging during tests
- **Solution**: Implement log rotation for tests
- **Test Pattern**:
  ```python
  def test_with_log_management(self):
      # Clear logs before test
      manage_logging(action="clear_test_logs")
      # Run test
      result = test_operation()
      # Verify logs
      logs = manage_logging(action="get_test_logs")
      assert len(logs) > 0
  ```

## 🟢 Resolved Issues

### Recently Resolved (2025-09-08)

#### 1. Authentication Context Missing
- **Issue**: MCP tools not receiving authentication context
- **Resolution**: Updated all MCP tool wrappers to pass user context
- **Verification**: All authenticated operations now work correctly

#### 2. Import Path Errors in MCP Tools
- **Issue**: MCP tools using deprecated import paths
- **Resolution**: Updated all MCP tools to use new value object paths
- **Verification**: No more `ModuleNotFoundError` in MCP operations

### Historical Resolutions

#### 1. Database Connection Issues (2025-01-19)
- **Issue**: MCP tools couldn't connect to database
- **Resolution**: Fixed database schema and connection configuration  
- **Verification**: All database-dependent MCP tools working

#### 2. Context System Integration (2025-01-19)
- **Issue**: MCP context tools using deprecated hierarchical system
- **Resolution**: Migrated to unified context system
- **Verification**: Context operations working with proper inheritance

## 📋 Testing Best Practices for MCP Tools

### Authentication Testing
```python
@patch('mcp_tool_wrapper.get_current_user_id')
def test_mcp_tool_with_auth(self, mock_user_id):
    """Test MCP tool with proper authentication."""
    mock_user_id.return_value = "test-user-123"
    
    result = manage_task(
        action="create",
        git_branch_id="test-branch-id", 
        title="Test task"
    )
    
    assert result["success"] is True
    assert "task_id" in result

def test_mcp_tool_without_auth_fails(self):
    """Test MCP tool fails without authentication."""
    with pytest.raises(UserAuthenticationRequiredError):
        manage_task(
            action="create",
            git_branch_id="test-branch-id",
            title="Test task"
        )
```

### Error Handling Testing
```python  
def test_mcp_tool_error_handling(self):
    """Test MCP tool error handling."""
    # Test invalid parameters
    result = manage_task(action="invalid_action")
    assert result["success"] is False
    assert "error" in result
    
    # Test missing required parameters  
    result = manage_task(action="create")
    assert result["success"] is False
    assert "required" in result["error"].lower()
```

### Performance Testing
```python
import time

def test_mcp_tool_performance(self):
    """Test MCP tool response times."""
    start_time = time.time()
    
    result = manage_task(
        action="create",
        git_branch_id="test-branch-id",
        title="Performance test"
    )
    
    end_time = time.time()
    response_time = end_time - start_time
    
    assert response_time < 5.0  # 5 second timeout
    assert result["success"] is True
```

### Integration Testing
```python
def test_mcp_tool_integration_workflow(self):
    """Test complete workflow using multiple MCP tools."""
    # Create project
    project_result = manage_project(
        action="create",
        name="Test Project"
    )
    assert project_result["success"] is True
    
    # Create branch
    branch_result = manage_git_branch(
        action="create", 
        project_id=project_result["project_id"],
        git_branch_name="test-branch"  # Note: git_branch_id (UUID) preferred for API calls
    )
    assert branch_result["success"] is True
    
    # Create task
    task_result = manage_task(
        action="create",
        git_branch_id=branch_result["git_branch_id"],
        title="Test Task"
    )
    assert task_result["success"] is True
    
    # Verify integration
    tasks = manage_task(
        action="list",
        git_branch_id=branch_result["git_branch_id"] 
    )
    assert len(tasks["tasks"]) == 1
```

## 🚨 Troubleshooting Guide

### MCP Tool Connection Issues
1. **Check MCP Server Status**
   ```python
   result = manage_connection(action="health_check")
   if not result["success"]:
       # Server not responding
       # Restart MCP server
   ```

2. **Verify Authentication**
   ```python
   # Ensure user context is available
   user_id = get_current_user_id()
   if not user_id:
       # Authentication required
       raise UserAuthenticationRequiredError()
   ```

3. **Check Tool Parameters**
   ```python
   # Validate required parameters before MCP call
   required_params = ["action"]  # Tool-specific
   for param in required_params:
       if param not in request_data:
           raise ValidationError(f"Missing required parameter: {param}")
   ```

### Performance Issues
1. **Enable Debug Logging**
   ```python
   import logging
   logging.getLogger('mcp_tools').setLevel(logging.DEBUG)
   ```

2. **Monitor Response Times**
   ```python  
   import time
   start = time.time()
   result = mcp_tool_call()
   duration = time.time() - start
   if duration > 10.0:
       logger.warning(f"Slow MCP tool response: {duration}s")
   ```

3. **Check Resource Usage**
   ```bash
   # Monitor memory and CPU during tests
   top -p $(pgrep -f "mcp_server")
   ```

### Error Recovery
```python
def resilient_mcp_call(tool_function, max_retries=3):
    """Make MCP tool call with retry logic."""
    for attempt in range(max_retries):
        try:
            return tool_function()
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            # Log error and continue
            logger.error(f"MCP tool error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise e
```

## 📊 Test Execution Metrics

### MCP Tool Test Results Summary

| Tool Category | Total Tests | Passing | Failing | Success Rate |
|---------------|-------------|---------|---------|--------------|
| Task Management | 45 | 40 | 5 | 89% |
| Project Management | 25 | 22 | 3 | 88% |  
| Agent Management | 20 | 18 | 2 | 90% |
| Context Management | 35 | 30 | 5 | 86% |
| Compliance | 15 | 13 | 2 | 87% |
| Logging | 10 | 9 | 1 | 90% |

### Performance Benchmarks

| Tool | Average Response Time | 95th Percentile | Timeout Threshold |
|------|----------------------|-----------------|-------------------|
| manage_task | 1.2s | 3.5s | 30s |
| manage_project | 0.8s | 2.1s | 15s |
| manage_context | 2.1s | 5.2s | 30s |
| call_agent | 15.3s | 45.2s | 120s |

## 📚 Related Documentation

- [MCP Testing Report](MCP_TESTING_REPORT.md) - Detailed MCP testing results
- [Test Results and Issues](test-results-and-issues.md) - General test results
- [Testing Guide](testing.md) - Core testing strategies
- [Comprehensive Troubleshooting Guide](../troubleshooting-guides/COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md) - System troubleshooting

## 📞 Escalation Process

### Level 1: Self-Service
1. Check this document for known issues
2. Review test logs for error patterns
3. Try suggested workarounds

### Level 2: Team Support  
1. Create GitHub issue with full error details
2. Include reproduction steps and environment info
3. Tag appropriate team members

### Level 3: Architecture Review
1. Schedule architecture review meeting
2. Prepare impact analysis and proposed solutions
3. Get approval for breaking changes

---

*Last Updated: 2025-09-08 - Created comprehensive MCP tools test issues documentation*