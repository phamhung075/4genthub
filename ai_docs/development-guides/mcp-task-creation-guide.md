# MCP Task Creation Complete Guide

## MCP Task Management Tool Syntax

### 1. Create Task with Full Context

```python
# EXACT MCP TOOL SYNTAX
result = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",  # REQUIRED - get from branch creation
    title="Implement Factory Pattern Refactoring",  # REQUIRED - clear, actionable
    assignees="coding-agent",  # REQUIRED - at least one agent
    description="Refactor operation factories to use abstract factory pattern",
    status="todo",  # Optional: todo|in_progress|blocked|review|testing|done
    priority="high",  # Optional: low|medium|high|urgent|critical
    estimated_effort="2 days",  # Optional: human-readable time estimate
    labels="refactoring,patterns,clean-code",  # Optional: comma-separated tags
    due_date="2024-12-31",  # Optional: ISO format date
    details="""
        ## 📋 Task Overview
        Refactor all operation factory classes to implement abstract factory pattern for better SOLID compliance.
        
        ## 🎯 Objectives
        1. Reduce code duplication by 70%
        2. Implement abstract factory base classes
        3. Improve testability and maintainability
        4. Achieve SOLID principle compliance
        
        ## 📁 Files to Analyze First
        - /dhafnck_mcp_main/src/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories/operation_factory.py
        - /dhafnck_mcp_main/src/fastmcp/task_management/application/factories/task_facade_factory.py
        - /dhafnck_mcp_main/src/fastmcp/task_management/application/services/repository_provider_service.py
        
        ## 🔧 Files to Modify
        
        ### 1. Create Abstract Base Factory
        **File**: `/dhafnck_mcp_main/src/fastmcp/task_management/application/factories/abstract_factory.py`
        **Action**: CREATE NEW
        ```python
        from abc import ABC, abstractmethod
        from typing import Dict, Any, Optional, TypeVar, Generic
        
        T = TypeVar('T')
        
        class AbstractFacadeFactory(ABC, Generic[T]):
            _instances: Dict[type, 'AbstractFacadeFactory'] = {}
            
            def __new__(cls, *args, **kwargs):
                if cls not in cls._instances:
                    cls._instances[cls] = super().__new__(cls)
                return cls._instances[cls]
            
            @abstractmethod
            def _create_facade_impl(self, user_id: str, **kwargs) -> T:
                pass
        ```
        
        ### 2. Refactor TaskFacadeFactory
        **File**: `/dhafnck_mcp_main/src/fastmcp/task_management/application/factories/task_facade_factory.py`
        **Changes**:
        - Line 16-34: Remove duplicate singleton implementation
        - Line 35: Extend from AbstractFacadeFactory
        - Line 84-151: Move to _create_facade_impl method
        
        ### 3. Create Parameter Filter Service
        **File**: `/dhafnck_mcp_main/src/fastmcp/task_management/application/services/parameter_filter_service.py`
        **Action**: CREATE NEW
        - Centralize parameter filtering logic
        - Remove hard-coded parameter lists from factories
        
        ### 4. Refactor Operation Factories
        **Files to Update**:
        - task_mcp_controller/factories/operation_factory.py
        - subtask_mcp_controller/factories/operation_factory.py
        - agent_mcp_controller/factories/operation_factory.py
        - project_mcp_controller/factories/operation_factory.py
        - git_branch_mcp_controller/factories/operation_factory.py
        
        **Common Changes**:
        - Extract common base class
        - Use parameter filter service
        - Implement handler registry pattern
        
        ## 🧪 Testing Requirements
        
        ### Unit Tests to Create
        - test_abstract_factory.py - Test singleton and caching
        - test_parameter_filter_service.py - Test filtering logic
        - test_refactored_operation_factory.py - Test new implementation
        
        ### Test Coverage Goals
        - Maintain 100% backward compatibility
        - Achieve 90% test coverage on new code
        - All existing tests must still pass
        
        ## ✅ Acceptance Criteria
        - [ ] All factory classes extend appropriate abstract base
        - [ ] Code duplication reduced by at least 70%
        - [ ] Parameter filtering centralized in service
        - [ ] All existing functionality preserved
        - [ ] Tests written and passing
        - [ ] Documentation updated
        - [ ] No breaking changes to public APIs
        
        ## 🔗 Dependencies
        - Must complete factory analysis first (completed)
        - Review existing factory implementations
        - Understand current usage patterns
        
        ## 📚 Reference Documentation
        - /ai_docs/reports-status/factory-check-status.md
        - /ai_docs/development-guides/factory-refactoring-templates.md
        - /ai_docs/development-guides/factory-refactoring-example.md
        
        ## 🛠️ Implementation Steps
        1. Create abstract base classes
        2. Create parameter filter service
        3. Refactor one factory as proof of concept
        4. Test thoroughly
        5. Apply pattern to remaining factories
        6. Update all imports and references
        7. Run full test suite
        8. Update documentation
    """,
    dependencies=[]  # Optional: list of task IDs this depends on
)

# Get the created task ID
task_id = result["task"]["id"]
print(f"Created task: {task_id}")
```

### 2. Create Subtasks for Detailed Work

```python
# Create subtask 1
subtask1 = mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=task_id,  # Parent task ID
    title="Create Abstract Factory Base Classes",
    description="Implement AbstractFacadeFactory and AbstractOperationFactory",
    status="todo",
    priority="high",
    assignees="coding-agent",  # Inherits from parent if not specified
    progress_notes="Starting with base class design"
)

# Create subtask 2
subtask2 = mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=task_id,
    title="Implement Parameter Filter Service",
    description="Create centralized parameter filtering service",
    status="todo",
    priority="high",
    progress_notes="Will replace hard-coded parameter lists"
)

# Create subtask 3
subtask3 = mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=task_id,
    title="Refactor TaskFacadeFactory",
    description="Update to extend AbstractFacadeFactory",
    status="todo",
    priority="medium",
    progress_notes="Proof of concept for pattern"
)
```

### 3. Update Task Progress

```python
# Start working on task
mcp__dhafnck_mcp_http__manage_task(
    action="update",
    task_id=task_id,
    status="in_progress",
    details="Started implementation, created abstract base classes"
)

# Update subtask progress
mcp__dhafnck_mcp_http__manage_subtask(
    action="update",
    task_id=task_id,
    subtask_id=subtask1["subtask"]["id"],
    progress_percentage=50,  # Automatically sets status based on %
    progress_notes="Base classes created, adding documentation",
    blockers="Need to verify singleton pattern thread safety"
)

# Complete a subtask
mcp__dhafnck_mcp_http__manage_subtask(
    action="complete",
    task_id=task_id,
    subtask_id=subtask1["subtask"]["id"],
    completion_summary="Abstract factory base classes implemented with singleton pattern",
    impact_on_parent="Foundation ready for refactoring concrete factories",
    insights_found="Thread-safe singleton requires lock for true safety"
)
```

### 4. Task Search and Discovery

```python
# Search for related tasks
search_result = mcp__dhafnck_mcp_http__manage_task(
    action="search",
    query="factory refactoring",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    limit=10
)

# List all tasks in branch
list_result = mcp__dhafnck_mcp_http__manage_task(
    action="list",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    status="in_progress",  # Optional filter
    priority="high",  # Optional filter
    limit=20
)

# Get next recommended task
next_task = mcp__dhafnck_mcp_http__manage_task(
    action="next",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    include_context=True  # Get AI insights
)
```

### 5. Complete Task with Full Summary

```python
# Complete the main task
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id=task_id,
    completion_summary="""
        Successfully refactored all operation factories to use abstract factory pattern.
        
        ## Achievements:
        - Created AbstractFacadeFactory base class
        - Created AbstractOperationFactory base class
        - Implemented ParameterFilterService
        - Refactored 8 factory classes
        - Reduced code duplication by 72%
        
        ## Key Changes:
        - All factories now extend abstract bases
        - Singleton pattern centralized
        - Parameter filtering extracted to service
        - Handler registration now uses registry pattern
        
        ## Metrics:
        - Lines of code reduced: 450 lines
        - Cyclomatic complexity: -45%
        - Test coverage: 92%
        - SOLID compliance: 100%
    """,
    testing_notes="""
        - All existing tests pass
        - Added 25 new unit tests
        - Integration tests successful
        - Performance benchmarks show 5% improvement
        - No breaking changes detected
    """
)
```

### 6. Task Dependencies Management

```python
# Add dependency to existing task
mcp__dhafnck_mcp_http__manage_task(
    action="add_dependency",
    task_id=task_id,
    dependency_id="other-task-id"
)

# Remove dependency
mcp__dhafnck_mcp_http__manage_task(
    action="remove_dependency",
    task_id=task_id,
    dependency_id="other-task-id"
)

# Create task with dependencies
dependent_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
    title="Test Refactored Factories",
    assignees="@test-orchestrator-agent",
    dependencies=[task_id],  # Must wait for factory refactoring
    details="Test all refactored factory implementations"
)
```

## Complete Task Planning Example

### Scenario: Implement Authentication System

```python
# Step 1: Create main epic task
epic = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="auth-feature-branch-id",
    title="Epic: Implement Complete Authentication System",
    assignees="@system-architect-agent",
    priority="critical",
    estimated_effort="2 weeks",
    labels="epic,authentication,security",
    details="""
        ## Epic Overview
        Implement complete authentication system with JWT, OAuth2, and 2FA support.
        
        ## Features to Implement
        1. JWT-based authentication
        2. OAuth2 integration (Google, GitHub)
        3. Two-factor authentication
        4. Password reset flow
        5. Session management
        6. Role-based access control
        
        ## Success Metrics
        - Zero security vulnerabilities
        - <100ms authentication time
        - 99.9% uptime
        - Support 10,000 concurrent users
    """
)

# Step 2: Create feature tasks
jwt_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="auth-feature-branch-id",
    title="Implement JWT Authentication",
    assignees="coding-agent,@security-auditor-agent",
    priority="high",
    estimated_effort="3 days",
    labels="authentication,jwt,backend",
    dependencies=[epic["task"]["id"]],
    details="""
        [Detailed JWT implementation context from earlier example]
    """
)

oauth_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="auth-feature-branch-id",
    title="Implement OAuth2 Integration",
    assignees="coding-agent",
    priority="high",
    estimated_effort="2 days",
    labels="authentication,oauth,integration",
    dependencies=[jwt_task["task"]["id"]],  # Depends on JWT being done first
    details="""
        ## OAuth2 Implementation
        
        ### Providers to Support
        - Google OAuth2
        - GitHub OAuth2
        - Microsoft Azure AD
        
        ### Implementation Files
        - /src/auth/oauth_providers.py
        - /src/auth/oauth_callback.py
        - /src/config/oauth_config.py
        
        ### Environment Variables Needed
        - GOOGLE_CLIENT_ID
        - GOOGLE_CLIENT_SECRET
        - GITHUB_CLIENT_ID
        - GITHUB_CLIENT_SECRET
    """
)

# Step 3: Create subtasks for JWT task
jwt_subtasks = [
    {
        "title": "Design JWT Token Structure",
        "description": "Define token payload, claims, and expiration strategy"
    },
    {
        "title": "Implement Token Generation",
        "description": "Create token generation with RS256 algorithm"
    },
    {
        "title": "Implement Token Validation",
        "description": "Create middleware for token validation"
    },
    {
        "title": "Add Refresh Token Logic",
        "description": "Implement refresh token rotation"
    },
    {
        "title": "Create Auth Endpoints",
        "description": "Implement /login, /logout, /refresh endpoints"
    }
]

for subtask_data in jwt_subtasks:
    mcp__dhafnck_mcp_http__manage_subtask(
        action="create",
        task_id=jwt_task["task"]["id"],
        title=subtask_data["title"],
        description=subtask_data["description"],
        assignees="coding-agent",
        progress_notes="Not started"
    )

# Step 4: Create testing task
test_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="auth-feature-branch-id",
    title="Comprehensive Authentication Testing",
    assignees="@test-orchestrator-agent",
    priority="high",
    estimated_effort="2 days",
    labels="testing,authentication,quality",
    dependencies=[jwt_task["task"]["id"], oauth_task["task"]["id"]],
    details="""
        ## Test Coverage Requirements
        
        ### Unit Tests
        - Token generation and validation
        - Password hashing and verification
        - OAuth provider integration
        - Session management
        
        ### Integration Tests
        - Full authentication flow
        - Token refresh mechanism
        - OAuth callback handling
        - Rate limiting
        
        ### Security Tests
        - SQL injection attempts
        - XSS attempts
        - CSRF protection
        - Brute force protection
        
        ### Performance Tests
        - Load testing (10k concurrent users)
        - Token generation speed
        - Database query optimization
        
        ### Coverage Goal: 95%
    """
)

# Step 5: Create documentation task
docs_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="auth-feature-branch-id",
    title="Authentication System Documentation",
    assignees="@documentation-agent",
    priority="medium",
    estimated_effort="1 day",
    labels="documentation,authentication",
    dependencies=[test_task["task"]["id"]],
    details="""
        ## Documentation Requirements
        
        ### API Documentation
        - All endpoints with request/response examples
        - Error codes and meanings
        - Rate limiting information
        
        ### Integration Guide
        - How to integrate with frontend
        - Token storage best practices
        - Refresh token handling
        
        ### Security Documentation
        - Security features implemented
        - Best practices for users
        - Incident response procedures
        
        ### Files to Create
        - /docs/api/authentication.md
        - /docs/guides/auth-integration.md
        - /docs/security/auth-security.md
    """
)

print(f"""
Task Creation Summary:
- Epic Task: {epic["task"]["id"]}
- JWT Task: {jwt_task["task"]["id"]}
- OAuth Task: {oauth_task["task"]["id"]}
- Test Task: {test_task["task"]["id"]}
- Docs Task: {docs_task["task"]["id"]}

Total tasks created: 5
Total subtasks created: 5
Estimated total effort: 2 weeks
""")
```

## Best Practices for MCP Task Creation

### 1. Always Include File Context
```python
details="""
    ## Files to Read First
    - /src/current/implementation.py - Understand existing code
    - /docs/requirements.md - Business requirements
    
    ## Files to Modify
    - /src/current/implementation.py
      - Line 45-67: Refactor validation logic
      - Line 120: Add new parameter
    
    ## Files to Create
    - /src/new/feature.py - New feature implementation
    - /tests/test_feature.py - Test coverage
"""
```

### 2. Use Proper Agent Assignment
```python
# Single agent
assignees="coding-agent"

# Multiple agents
assignees="coding-agent,@security-auditor-agent"

# Specialized agents based on task type
if "bug" in title:
    assignees="debugger-agent"
elif "test" in title:
    assignees="@test-orchestrator-agent"
elif "UI" in title:
    assignees="@ui-specialist-agent"
```

### 3. Track Progress Properly
```python
# Use progress percentage for automatic status updates
progress_percentage=0    # -> status: todo
progress_percentage=25   # -> status: in_progress
progress_percentage=100  # -> status: done

# Add meaningful progress notes
progress_notes="Completed authentication logic, working on token refresh"
```

### 4. Complete Tasks with Context
```python
# Always provide comprehensive completion summary
completion_summary="Detailed summary of what was accomplished"
testing_notes="What tests were run and results"
```

## Summary

This guide provides the complete MCP task management syntax with:
- Exact function signatures for all operations
- Full context templates for tasks
- File helper information
- Progress tracking methods
- Dependency management
- Real-world examples
- Best practices

Use this guide to create well-structured, trackable tasks in the MCP system with complete context for successful implementation.