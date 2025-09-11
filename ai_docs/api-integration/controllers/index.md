# API Integration Controllers Documentation

## Overview

This documentation covers the comprehensive controller architecture of the DhafnckMCP project, which implements a sophisticated task management system using Domain-Driven Design (DDD) principles. The system features two distinct controller layers designed to handle different communication protocols and client interactions.

## Controller Architecture

The system employs a **dual-controller architecture** that maintains clear separation of concerns while ensuring consistent business logic across all interfaces:

### 1. MCP Controllers (Model Context Protocol)
- **Purpose**: Handle Claude AI and MCP client communications
- **Protocol**: MCP (Model Context Protocol) for AI agent interactions
- **Location**: `dhafnck_mcp_main/src/fastmcp/task_management/interface/mcp_controllers/`
- **Authentication**: Token-based with permission validation
- **Response Format**: MCP-compliant JSON responses

### 2. API Controllers (HTTP REST)
- **Purpose**: Handle frontend and direct HTTP API interactions
- **Protocol**: HTTP REST API for web applications
- **Location**: `dhafnck_mcp_main/src/fastmcp/task_management/interface/api_controllers/`
- **Authentication**: JWT tokens with role-based access control
- **Response Format**: Standard REST API JSON responses

### 3. Infrastructure Controllers
- **Purpose**: Handle cross-cutting concerns like security and access control
- **Location**: `dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/security/`

## Domain-Driven Design (DDD) Compliance

All controllers follow strict DDD principles:

- **Interface Layer**: Controllers serve as the interface layer, handling protocol-specific concerns
- **Application Layer**: Delegate to application facades for business logic
- **No Direct Access**: Controllers never directly access repositories or domain services
- **Separation of Concerns**: Clear boundaries between layers maintained
- **Facade Pattern**: Use of facade services for complex operations

## Core Architecture Patterns

### Modular Factory Pattern
Controllers use factory patterns for:
- **Operation Factories**: Handle different types of operations (CRUD, workflow, etc.)
- **Validation Factories**: Validate requests based on operation type
- **Response Factories**: Standardize response formats across protocols

### Two-Stage Validation
```python
# Stage 1: Schema validation (protocol level)
# Only 'action' parameter required at MCP schema level

# Stage 2: Business validation (application level)
# Action-specific parameters validated based on operation type
```

### Authentication Integration
- **Unified Authentication**: Single authentication helper used across all controllers
- **Permission Checking**: Resource-specific CRUD permissions
- **User Context**: Thread-safe user context propagation
- **Audit Trails**: Comprehensive logging for security compliance

## Available Controllers

### MCP Controllers

| Controller | Purpose | MCP Tool | Key Actions |
|------------|---------|----------|-------------|
| **Task MCP Controller** | Task lifecycle management | `manage_task` | create, read, update, delete, complete, list, search |
| **Agent MCP Controller** | Agent registration and assignment | `manage_agent` | register, assign, update, unregister, rebalance |
| **Project MCP Controller** | Project lifecycle operations | `manage_project` | create, read, update, health_check, cleanup |
| **Git Branch MCP Controller** | Branch and task tree management | `manage_git_branch` | create, read, update, delete, assign_agent, statistics |
| **Subtask MCP Controller** | Hierarchical task breakdown | `manage_subtask` | create, read, update, delete, complete, list |
| **Context MCP Controller** | Unified context management | `manage_context` | create, read, update, delete, resolve, delegate |
| **Dependency MCP Controller** | Task dependency management | `manage_dependency` | add, remove, list, validate |
| **Call Agent MCP Controller** | Dynamic agent invocation | `call_agent` | invoke specialized agents |
| **Connection MCP Controller** | System health monitoring | `manage_connection` | health_check |

### API Controllers

| Controller | Purpose | Endpoints | Key Operations |
|------------|---------|-----------|----------------|
| **Task API Controller** | Frontend task operations | `/api/tasks/*` | CRUD, workflow, search, statistics |
| **Agent API Controller** | Agent management via HTTP | `/api/agents/*` | registration, assignment, lifecycle |
| **Project API Controller** | Project management via HTTP | `/api/projects/*` | CRUD, health monitoring |
| **Branch API Controller** | Branch operations via HTTP | `/api/branches/*` | branch lifecycle, agent assignment |
| **Subtask API Controller** | Subtask management via HTTP | `/api/subtasks/*` | hierarchical task management |
| **Context API Controller** | Context operations via HTTP | `/api/context/*` | context CRUD, inheritance |
| **Auth API Controller** | Authentication endpoints | `/api/auth/*` | login, token validation, permissions |
| **Token API Controller** | Token management | `/api/tokens/*` | generation, validation, revocation |

### Infrastructure Controllers

| Controller | Purpose | Scope | Key Features |
|------------|---------|-------|--------------|
| **Access Controller** | Security and authorization | Cross-cutting | RBAC, resource permissions, audit |

## Inter-Controller Communication

### Facade Service Pattern
All controllers communicate through the **FacadeService**, which provides:
- **Unified Interface**: Single point of access to application services
- **Context Management**: Automatic user and session context handling
- **Transaction Management**: Coordinated database transactions
- **Error Handling**: Consistent error handling across all operations

### Communication Flow
```
Controller → FacadeService → ApplicationFacade → DomainService → Repository
```

### Context Propagation
- **Thread-Safe**: User context propagated through async operations
- **Multi-Tenant**: Complete isolation between user contexts
- **Session Management**: Automatic session handling for long-running operations

## Authentication and Authorization

### Unified Authentication
All controllers use a centralized authentication system:

```python
# Authentication helper used across all controllers
user_id = get_authenticated_user_id(
    provided_user_id=user_id,
    operation_name=f"controller_action:{action}"
)
```

### Permission System
Resource-specific permissions for all operations:
- **Tasks**: `tasks:create`, `tasks:read`, `tasks:update`, `tasks:delete`
- **Projects**: `projects:create`, `projects:read`, `projects:update`, `projects:delete`
- **Agents**: `agents:register`, `agents:assign`, `agents:manage`
- **Contexts**: `contexts:create`, `contexts:read`, `contexts:update`

### Security Features
- **JWT Token Validation**: All requests validated
- **Role-Based Access Control**: Fine-grained permissions
- **Audit Logging**: All operations logged with user context
- **Request Sanitization**: All inputs sanitized for security

## Error Handling Strategy

### Standardized Error Responses
All controllers return consistent error formats:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "VALIDATION_ERROR",
  "operation": "create_task",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Error Categories
- **VALIDATION_ERROR**: Request validation failures
- **AUTHENTICATION_ERROR**: Authentication issues
- **PERMISSION_DENIED**: Authorization failures
- **OPERATION_FAILED**: Business logic errors
- **SYSTEM_ERROR**: Infrastructure problems

### User-Friendly Error Handling
- **No Internal Details**: Internal errors never exposed to users
- **Actionable Messages**: Clear guidance on resolving issues
- **Proper HTTP Status Codes**: RESTful status code usage
- **Consistent Formatting**: Same error structure across all controllers

## Performance and Optimization

### Caching Strategy
- **Response Caching**: Frequently accessed data cached
- **Context Caching**: User context cached for session duration
- **Smart Invalidation**: Cache invalidated on relevant updates

### Database Optimization
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Optimized queries for large datasets
- **Pagination**: Built-in pagination for list operations
- **Lazy Loading**: Related data loaded on demand

### Async Operations
- **Non-Blocking**: All I/O operations are async
- **Parallel Processing**: Independent operations executed in parallel
- **Context Preservation**: User context maintained across async boundaries

## Best Practices for Extending Controllers

### Adding New Controllers
1. **Follow DDD Patterns**: Maintain clear layer separation
2. **Use Facade Pattern**: Delegate to application facades
3. **Implement Authentication**: Use centralized auth helper
4. **Standardize Responses**: Use response factories
5. **Add Comprehensive Tests**: Unit and integration tests required

### Adding New Actions
1. **Update Validation Factory**: Add action-specific validation
2. **Update Operation Factory**: Add operation handler
3. **Update Response Factory**: Ensure proper response formatting
4. **Add Permission Checks**: Define required permissions
5. **Update Documentation**: Document new functionality

### Security Considerations
1. **Never Bypass Authentication**: All operations must authenticate
2. **Validate All Inputs**: Comprehensive input validation required
3. **Use Permission System**: Check resource-specific permissions
4. **Log All Operations**: Maintain audit trails
5. **Sanitize Responses**: Never expose internal details

## Testing Strategy

### Test Coverage Requirements
- **Unit Tests**: Individual controller methods (>90% coverage)
- **Integration Tests**: Cross-controller workflows (>80% coverage)
- **Security Tests**: Authentication and authorization (100% coverage)
- **Performance Tests**: Load testing for scalability

### Test Categories
- **Controller Tests**: Test controller logic isolation
- **Facade Integration**: Test controller-facade interactions
- **Authentication Tests**: Verify security implementation
- **Error Handling Tests**: Verify error response consistency

## API Documentation

Individual controller documentation is available in dedicated files:

- [Task Management API](./manage-task-api.md) - Complete task lifecycle operations
- [Agent Management API](./manage-agent-api.md) - Agent registration and assignment
- [Project Management API](./manage-project-api.md) - Project lifecycle and health monitoring
- [Git Branch Management API](./manage-git-branch-api.md) - Branch and task tree operations
- [Subtask Management API](./manage-subtask-api.md) - Hierarchical task breakdown
- [Context Management API](./manage-context-api.md) - Unified context operations
- [Dependency Management API](./manage-dependency-api.md) - Task dependency relationships
- [Connection Management API](./manage-connection-api.md) - System health and monitoring

## Quick Reference

### Common Code Patterns

#### MCP Controller Registration
```python
def register_tools(self, mcp: "FastMCP"):
    @mcp.tool(description="Tool description")
    def tool_function(
        action: Annotated[str, Field(description="Required action parameter")]
    ) -> Dict[str, Any]:
        return self.handle_action(action=action)
```

#### Authentication Pattern
```python
user_id = get_authenticated_user_id(
    provided_user_id=user_id,
    operation_name=f"controller:{action}"
)
log_authentication_details(user_id, f"controller:{action}")
```

#### Permission Check Pattern
```python
permission_result = self._check_permissions(action, user_id, resource_id)
if not permission_result[0]:
    return permission_result[1]  # Return permission denied error
```

#### Error Response Pattern
```python
return self._response_formatter.create_error_response(
    operation=action,
    error="Human-readable error message",
    error_code=ErrorCodes.VALIDATION_ERROR
)
```

## Support and Maintenance

For questions about controller implementation or to report issues:
- **Documentation Updates**: Keep this index current with any architectural changes
- **Security Reviews**: Regular security audits of authentication and authorization
- **Performance Monitoring**: Monitor controller performance and optimize as needed
- **Code Reviews**: All controller changes require peer review

---

**Last Updated**: 2025-01-15  
**Version**: 1.0  
**Maintainer**: DhafnckMCP Development Team