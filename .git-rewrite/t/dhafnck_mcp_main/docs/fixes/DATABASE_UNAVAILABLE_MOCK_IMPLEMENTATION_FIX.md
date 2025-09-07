# Database Unavailable - Mock Implementation Fix

## Executive Summary

**Issue**: MCP tools become unavailable when database (PostgreSQL/Supabase) is not configured, causing complete system failure.

**Solution**: Implement complete mock repositories and services that allow the system to function without a database.

**Date Fixed**: 2025-01-31
**Affected Version**: 2.1.0
**Fix Complexity**: High (requires changes across all architectural layers)

## Problem Analysis

### Symptoms
- All MCP tools show "No such tool available" error
- Server starts but reports 0 enabled tools
- Container health checks pass but functionality is broken
- Error: "Can't instantiate abstract class MockProjectRepository"

### Root Cause
The system was designed to require a database, but when database is unavailable:
1. Mock repositories were missing required abstract methods
2. Application facades failed to initialize
3. Tool registration silently failed
4. No graceful degradation path existed

## The Fix - Layer by Layer

### Layer 1: Infrastructure - Complete Mock Repositories

**File**: `src/fastmcp/task_management/infrastructure/repositories/mock_repository_factory.py`

```python
class MockProjectRepository(ProjectRepository):
    """Complete mock implementation with ALL abstract methods"""
    
    def __init__(self):
        self._projects = {}
        self._id_counter = 0
    
    # CRITICAL: Must implement ALL abstract methods from ProjectRepository
    async def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project
    
    async def find_by_id(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)
    
    async def find_by_name(self, name: str) -> Optional[Project]:
        for project in self._projects.values():
            if project.name == name:
                return project
        return None
    
    async def find_all(self) -> List[Project]:
        return list(self._projects.values())
    
    async def delete(self, project_id: str) -> bool:
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False
    
    async def count(self) -> int:
        return len(self._projects)
    
    async def exists(self, project_id: str) -> bool:
        return project_id in self._projects
    
    async def find_projects_with_agent(self, agent_id: str) -> List[Project]:
        """Return empty list for mock implementation"""
        return []
    
    async def find_projects_by_status(self, status: str) -> List[Project]:
        """Filter projects by status if they have the attribute"""
        results = []
        for project in self._projects.values():
            if hasattr(project, 'status') and project.status == status:
                results.append(project)
        return results
    
    async def get_project_health_summary(self, project_id: str) -> Dict[str, Any]:
        """Return mock health summary"""
        return {
            "project_id": project_id,
            "health": "good",
            "tasks_count": 0,
            "active_tasks": 0,
            "completed_tasks": 0
        }
    
    async def unassign_agent_from_tree(self, project_id: str) -> bool:
        """Mock successful unassignment"""
        return True
```

**Similar fixes required for**:
- MockGitBranchRepository
- MockTaskRepository  
- MockSubtaskRepository
- MockAgentRepository

### Layer 2: Application - Mock Context Services

**File**: `src/fastmcp/task_management/application/services/mock_unified_context_service.py`

```python
class MockUnifiedContextService:
    """Mock unified context service for database-less operation"""
    
    def __init__(self):
        self._contexts = {}
        self._global_context = None
        logger.warning("Using MockUnifiedContextService - context operations will not persist")
    
    def get_context(self, level: str, context_id: str, 
                   include_inherited: bool = True, 
                   force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get context with mock inheritance"""
        key = f"{level}:{context_id}"
        context = self._contexts.get(key)
        
        if not context and level == "global":
            # Auto-create global context if missing
            context = self._create_default_global_context()
        
        return context
    
    def _create_default_global_context(self) -> Dict[str, Any]:
        """Create default global context"""
        context = {
            "id": "global_singleton",
            "level": "global",
            "data": {
                "organization_name": "Default Organization",
                "global_settings": {}
            },
            "created_at": datetime.now().isoformat()
        }
        self._contexts["global:global_singleton"] = context
        return context
    
    # Implement all other required methods...
```

### Layer 3: Application - Fix Facade Factories

**File**: `src/fastmcp/task_management/application/factories/unified_context_facade_factory.py`

```python
class UnifiedContextFacadeFactory:
    def __init__(self, session_factory=None):
        self.session_factory = None
        self.unified_service = None
        
        # CRITICAL: Handle database unavailability gracefully
        if session_factory is None:
            try:
                db_config = get_db_config()
                session_factory = db_config.SessionLocal
                # Continue with normal database initialization...
            except Exception as e:
                logger.warning(f"Database not available, using mock context service: {e}")
                # Switch to mock implementation
                self._create_mock_service()
                return  # Early return - don't try database operations
        
        # Database initialization code here...
    
    def _create_mock_service(self):
        """Create mock service when database unavailable"""
        from ..services.mock_unified_context_service import MockUnifiedContextService
        self.unified_service = MockUnifiedContextService()
        logger.warning("Using MockUnifiedContextService - limited functionality")
```

**File**: `src/fastmcp/task_management/application/facades/task_application_facade.py`

```python
class TaskApplicationFacade:
    def __init__(self, task_repository, subtask_repository=None, 
                 context_service=None, git_branch_repository=None):
        # ... existing initialization ...
        
        # CRITICAL: Use mock context repository when database unavailable
        task_context_repository = None
        try:
            from ...infrastructure.repositories.task_context_repository import TaskContextRepository
            from ...infrastructure.database.database_config import get_db_config
            db_config = get_db_config()
            task_context_repository = TaskContextRepository(db_config.SessionLocal)
        except Exception as e:
            logger.warning(f"Could not initialize task context repository: {e}")
            # Fall back to mock implementation
            from ...infrastructure.repositories.mock_task_context_repository import MockTaskContextRepository
            task_context_repository = MockTaskContextRepository()
        
        # Use the repository (mock or real) in use cases
        self._complete_task_use_case = CompleteTaskUseCase(
            task_repository, 
            subtask_repository, 
            task_context_repository  # Will work with either mock or real
        )
```

### Layer 4: Interface - Graceful Tool Registration

**File**: `src/fastmcp/task_management/interface/ddd_compliant_mcp_tools.py`

```python
class DDDCompliantMCPTools:
    def __init__(self):
        logger.info("Initializing DDD-compliant MCP tools...")
        
        # CRITICAL: Don't fail if database is unavailable
        self._session_factory = None
        try:
            from ..infrastructure.database.database_config import get_db_config
            db_config = get_db_config()
            self._session_factory = db_config.SessionLocal
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
            logger.warning("Tools will be registered with limited functionality")
            logger.warning("Some operations may fail without a configured database")
            # DON'T raise exception - continue with initialization
        
        # Initialize controllers regardless of database availability
        self._initialize_controllers()
    
    def register_tools(self, mcp):
        """Register all available tools"""
        logger.info("Registering DDD-compliant MCP tools...")
        
        # Register each tool with error handling
        if self._task_controller:
            try:
                self._register_task_tools(mcp)
            except Exception as e:
                logger.error(f"Failed to register task tools: {e}")
        
        if self._project_controller:
            try:
                self._register_project_tools(mcp)
            except Exception as e:
                logger.error(f"Failed to register project tools: {e}")
        
        # Continue registering other tools...
        
        logger.info("DDD-compliant MCP tools registered successfully")
```

## Docker Configuration

### Environment Variables for Database-less Operation

```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      - DATABASE_TYPE=supabase  # Or postgresql
      - FASTMCP_TRANSPORT=streamable-http  # CRITICAL for HTTP mode
      - FASTMCP_HOST=0.0.0.0  # CRITICAL for container networking
      - DHAFNCK_AUTH_ENABLED=false  # Disable auth without database
      - ENABLE_MOCK_REPOSITORIES=true  # Force mock mode
```

### Dockerfile Considerations

```dockerfile
# Ensure all mock implementations are included
COPY src/fastmcp/task_management/infrastructure/repositories/mock_*.py \
     /app/src/fastmcp/task_management/infrastructure/repositories/

COPY src/fastmcp/task_management/application/services/mock_*.py \
     /app/src/fastmcp/task_management/application/services/
```

## Testing the Fix

### Unit Test for Mock Repositories

```python
# test_mock_repositories.py
def test_mock_project_repository_has_all_methods():
    """Ensure mock has all required abstract methods"""
    from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
    from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockProjectRepository
    
    # Get all abstract methods from interface
    abstract_methods = [
        method for method in dir(ProjectRepository)
        if not method.startswith('_') and 
        callable(getattr(ProjectRepository, method))
    ]
    
    # Create mock instance
    mock_repo = MockProjectRepository()
    
    # Verify all methods exist
    for method in abstract_methods:
        assert hasattr(mock_repo, method), f"Missing method: {method}"
        assert callable(getattr(mock_repo, method)), f"Method not callable: {method}"
```

### Integration Test

```python
# test_system_without_database.py
def test_system_works_without_database():
    """Test complete system initialization without database"""
    import os
    os.environ['DATABASE_TYPE'] = 'supabase'
    os.environ['ENABLE_MOCK_REPOSITORIES'] = 'true'
    
    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    
    # Should not raise any exceptions
    tools = DDDCompliantMCPTools()
    
    # Verify controllers initialized
    assert tools._task_controller is not None
    assert tools._project_controller is not None
    
    # Test registration
    class MockMCP:
        def __init__(self):
            self.tools = {}
        
        def tool(self, name=None, description=None):
            def decorator(func):
                self.tools[name or func.__name__] = func
                return func
            return decorator
    
    mock_mcp = MockMCP()
    tools.register_tools(mock_mcp)
    
    # Verify tools registered
    assert len(mock_mcp.tools) > 0
    assert 'manage_task' in mock_mcp.tools
    assert 'manage_project' in mock_mcp.tools
```

## Rollback Plan

If this fix causes issues:

1. **Revert mock implementations** to previous versions
2. **Re-enable database requirement** in DDDCompliantMCPTools
3. **Add DATABASE_REQUIRED flag** to force database mode
4. **Document database as hard requirement**

## Monitoring

After deploying this fix, monitor:

1. **Health endpoint**: Should show tools count > 0
2. **Container logs**: No "abstract class" errors
3. **Tool availability**: All tools accessible via MCP
4. **Memory usage**: Mock stores shouldn't grow unbounded
5. **Performance**: Mock operations should be fast

## Lessons Learned

1. **Always implement complete interfaces** - Every abstract method must be implemented
2. **Design for graceful degradation** - System should work with reduced functionality
3. **Layer isolation is critical** - Each layer should handle its own failures
4. **Mock implementations need maintenance** - Keep them in sync with interfaces
5. **Test each layer independently** - Helps identify exact failure points

## Future Improvements

1. **Add interface validation tests** - Automatically check mock completeness
2. **Create mock data generators** - Provide realistic test data
3. **Add persistence to mocks** - Optional file-based storage
4. **Implement mock data limits** - Prevent memory exhaustion
5. **Add mock operation metrics** - Track usage patterns

---

**Author**: System Architecture Team
**Review Status**: Implemented and Tested
**Production Ready**: Yes (with limitations noted)