# MCP Tools Missing - Complete Troubleshooting Guide

## Problem Description
**Symptom**: All MCP tools (manage_task, manage_project, manage_git_branch, etc.) show "No such tool available" error when accessed through the mcp__dhafnck_mcp_http__ prefix, even though the server is running and healthy.

**Error Message**: 
```
Error: No such tool available: mcp__dhafnck_mcp_http__manage_task
```

## Root Cause Analysis

This issue typically occurs when:
1. Database is unavailable (PostgreSQL/Supabase not configured)
2. Repository implementations are missing required abstract methods
3. Application layer facades fail to initialize
4. Tool registration fails silently during server startup

## Layer-by-Layer Diagnostic Approach

### Step 1: Create Diagnostic Script

First, create a diagnostic script to test each architectural layer independently:

```python
#!/usr/bin/env python3
"""
Layer-by-layer diagnostic script to identify where MCP tools registration fails
Save as: test_layer_by_layer.py
"""

import sys
import os
import traceback
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, '/path/to/dhafnck_mcp_main/src')
os.environ['DATABASE_TYPE'] = 'supabase'  # Or your database type

def test_layer(layer_name, test_func):
    """Test a specific layer and report results"""
    print(f"\n{'='*60}")
    print(f"Testing {layer_name}")
    print('='*60)
    try:
        result = test_func()
        print(f"✅ {layer_name} - SUCCESS")
        return True, result
    except Exception as e:
        print(f"❌ {layer_name} - FAILED")
        print(f"   Error: {e}")
        print(f"   Traceback:")
        traceback.print_exc()
        return False, str(e)

def test_domain_layer():
    """Test domain entities and interfaces"""
    from fastmcp.task_management.domain.entities.task import Task
    from fastmcp.task_management.domain.entities.project import Project
    from datetime import datetime
    
    task = Task(
        id="test-1", 
        title="Test Task", 
        description="Test", 
        git_branch_id="branch-1",
        status="pending",
        priority="medium",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return "Domain entities work"

def test_infrastructure_repositories():
    """Test repository factories"""
    from fastmcp.task_management.infrastructure.repositories.project_repository_factory import ProjectRepositoryFactory
    proj_repo = ProjectRepositoryFactory.create(repository_type=None, user_id="test")
    return f"Repository created: {type(proj_repo).__name__}"

def test_application_facades():
    """Test application layer facades"""
    from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
    factory = ProjectFacadeFactory()
    facade = factory.create_project_facade(user_id="test")
    return f"Facade created: {type(facade).__name__}"

def test_interface_controllers():
    """Test interface layer controllers"""
    from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController
    from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
    
    factory = ProjectFacadeFactory()
    controller = ProjectMCPController(factory)
    return f"Controller created: {type(controller).__name__}"

def test_ddd_tools_init():
    """Test DDDCompliantMCPTools initialization"""
    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    tools = DDDCompliantMCPTools()
    
    print(f"Task controller: {tools._task_controller is not None}")
    print(f"Project controller: {tools._project_controller is not None}")
    return tools

def main():
    """Run all layer tests"""
    print("\nLAYER-BY-LAYER DIAGNOSTIC TEST")
    print("="*60)
    
    tests = [
        ("1. Domain Layer", test_domain_layer),
        ("2. Infrastructure - Repositories", test_infrastructure_repositories),
        ("3. Application - Facades", test_application_facades),
        ("4. Interface - Controllers", test_interface_controllers),
        ("5. DDD Tools Initialization", test_ddd_tools_init),
    ]
    
    for name, test_func in tests:
        success, result = test_layer(name, test_func)
        if not success:
            print(f"\n⚠️  Stopping at {name} due to failure")
            print(f"🎯 FAILURE POINT: {name}")
            print("This is where you need to focus your fix!")
            break
    else:
        print("\n✅ All layers passed!")

if __name__ == "__main__":
    main()
```

### Step 2: Fix Mock Repository Implementations

If the Infrastructure layer fails with "Can't instantiate abstract class" errors, fix the mock repositories:

#### Fix MockProjectRepository

```python
# File: src/fastmcp/task_management/infrastructure/repositories/mock_repository_factory.py

class MockProjectRepository(ProjectRepository):
    """Mock implementation with ALL required abstract methods"""
    
    def __init__(self):
        self._projects = {}
    
    # Core CRUD operations
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
    
    # Additional required methods
    async def count(self) -> int:
        return len(self._projects)
    
    async def exists(self, project_id: str) -> bool:
        return project_id in self._projects
    
    async def find_projects_with_agent(self, agent_id: str) -> List[Project]:
        return []  # Mock implementation
    
    async def find_projects_by_status(self, status: str) -> List[Project]:
        results = []
        for project in self._projects.values():
            if hasattr(project, 'status') and project.status == status:
                results.append(project)
        return results
    
    async def get_project_health_summary(self, project_id: str) -> Dict[str, Any]:
        return {"health": "good", "project_id": project_id}
    
    async def unassign_agent_from_tree(self, project_id: str) -> bool:
        return True  # Mock success
```

#### Fix MockGitBranchRepository

```python
class MockGitBranchRepository(GitBranchRepository):
    """Mock implementation with ALL required abstract methods"""
    
    def __init__(self):
        self._branches = {}
    
    async def save(self, branch: GitBranch) -> GitBranch:
        self._branches[branch.id] = branch
        return branch
    
    async def find_by_id(self, branch_id: str) -> Optional[GitBranch]:
        return self._branches.get(branch_id)
    
    async def find_all(self) -> List[GitBranch]:
        return list(self._branches.values())
    
    async def delete(self, branch_id: str) -> bool:
        if branch_id in self._branches:
            del self._branches[branch_id]
            return True
        return False
    
    async def find_by_project_id(self, project_id: str) -> List[GitBranch]:
        results = []
        for branch in self._branches.values():
            if branch.project_id == project_id:
                results.append(branch)
        return results
    
    async def find_by_name_and_project(self, name: str, project_id: str) -> Optional[GitBranch]:
        for branch in self._branches.values():
            if branch.name == name and branch.project_id == project_id:
                return branch
        return None
    
    async def count(self) -> int:
        return len(self._branches)
    
    async def exists(self, branch_id: str) -> bool:
        return branch_id in self._branches
```

### Step 3: Fix Application Layer - Context Services

If the Application layer fails with context service errors:

#### Create MockUnifiedContextService

```python
# File: src/fastmcp/task_management/application/services/mock_unified_context_service.py

class MockUnifiedContextService:
    """Mock unified context service for database-less operation"""
    
    def __init__(self):
        self._contexts = {}
        logger.warning("Using MockUnifiedContextService - context operations will not persist")
    
    def get_context(self, level: str, context_id: str, 
                   include_inherited: bool = True, force_refresh: bool = False):
        key = f"{level}:{context_id}"
        return self._contexts.get(key)
    
    def create_context(self, level: str, context_id: str, 
                      data: Dict[str, Any], parent_id: Optional[str] = None):
        key = f"{level}:{context_id}"
        context = {
            "id": context_id,
            "level": level,
            "data": data,
            "parent_id": parent_id,
            "created_at": datetime.now().isoformat()
        }
        self._contexts[key] = context
        return context
    
    def update_context(self, level: str, context_id: str, 
                      data: Dict[str, Any], merge: bool = True):
        key = f"{level}:{context_id}"
        if key not in self._contexts:
            return self.create_context(level, context_id, data)
        
        context = self._contexts[key]
        if merge:
            context["data"].update(data)
        else:
            context["data"] = data
        return context
    
    # Add all other required methods...
```

#### Fix UnifiedContextFacadeFactory

```python
# File: src/fastmcp/task_management/application/factories/unified_context_facade_factory.py

class UnifiedContextFacadeFactory:
    def __init__(self, session_factory=None):
        self.session_factory = None
        self.unified_service = None
        
        # Handle database unavailability gracefully
        if session_factory is None:
            try:
                db_config = get_db_config()
                session_factory = db_config.SessionLocal
            except Exception as e:
                logger.warning(f"Database not available, using mock context service: {e}")
                self._create_mock_service()
                return
        
        # Continue with normal initialization if database available...
    
    def _create_mock_service(self):
        """Create a mock unified service for database-less operation"""
        from ..services.mock_unified_context_service import MockUnifiedContextService
        self.unified_service = MockUnifiedContextService()
        logger.warning("Using MockUnifiedContextService")
```

### Step 4: Fix Interface Layer - Tool Registration

If tools initialize but don't register:

#### Fix DDDCompliantMCPTools

```python
# File: src/fastmcp/task_management/interface/ddd_compliant_mcp_tools.py

class DDDCompliantMCPTools:
    def __init__(self):
        logger.info("Initializing DDD-compliant MCP tools...")
        
        # Initialize session factory with graceful database handling
        self._session_factory = None
        try:
            from ..infrastructure.database.database_config import get_db_config
            db_config = get_db_config()
            self._session_factory = db_config.SessionLocal
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
            logger.warning("Tools will be registered with limited functionality")
        
        # Initialize all controllers regardless of database availability
        self._initialize_controllers()
    
    def _initialize_controllers(self):
        """Initialize all controllers with fallback to mock implementations"""
        try:
            # Project controller
            from ..application.factories.project_facade_factory import ProjectFacadeFactory
            self._project_facade_factory = ProjectFacadeFactory()
            from .controllers.project_mcp_controller import ProjectMCPController
            self._project_controller = ProjectMCPController(self._project_facade_factory)
            
            # Task controller - with mock repositories if needed
            # ... initialize other controllers
            
        except Exception as e:
            logger.error(f"Failed to initialize controllers: {e}")
            # Set controllers to None so registration can skip them
            self._project_controller = None
            self._task_controller = None
```

### Step 5: Docker Container Fixes

If the container keeps restarting or tools don't appear:

#### Rebuild Docker Image

```bash
# 1. Rebuild the Docker image with fixes
cd /path/to/dhafnck_mcp_main
docker build -t dhafnck/mcp-server:latest -f docker/Dockerfile .

# 2. Stop and remove old container
docker stop dhafnck-mcp-server
docker rm dhafnck-mcp-server

# 3. Run with correct environment variables
docker run -d \
  --name dhafnck-mcp-server \
  -p 8000:8000 \
  -v dhafnck-data:/data \
  -e DATABASE_TYPE=supabase \
  -e FASTMCP_TRANSPORT=streamable-http \
  -e FASTMCP_HOST=0.0.0.0 \
  -e DHAFNCK_AUTH_ENABLED=false \
  dhafnck/mcp-server:latest
```

### Step 6: Verify Tool Registration

Test if tools are being registered internally:

```python
# Test script to verify tool registration
docker exec dhafnck-mcp-server python -c "
import sys
sys.path.insert(0, '/app/src')

# Mock MCP server to capture registrations
class MockMCP:
    def __init__(self):
        self.tools = {}
    
    def tool(self, name=None, description=None):
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            print(f'Registered: {tool_name}')
            return func
        return decorator
    
    def resource(self, name=None):
        def decorator(func):
            return func
        return decorator
    
    def add_resource(self, resource):
        pass

# Test registration
from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
mock_mcp = MockMCP()
tools = DDDCompliantMCPTools()
tools.register_tools(mock_mcp)

print(f'\nTotal tools registered: {len(mock_mcp.tools)}')
print('Tools:', list(mock_mcp.tools.keys()))
"
```

Expected output:
```
Registered: manage_task
Registered: manage_subtask
Registered: manage_project
Registered: manage_git_branch
Registered: manage_agent
Registered: manage_rule
Registered: call_agent
Registered: manage_compliance

Total tools registered: 8
Tools: ['manage_task', 'manage_subtask', 'manage_project', ...]
```

## Common Issues and Solutions

### Issue 1: "Can't instantiate abstract class"
**Error**: `Can't instantiate abstract class MockProjectRepository without an implementation for abstract methods`

**Solution**: Implement ALL abstract methods from the parent interface. Check the abstract base class and ensure every method is implemented in the mock.

### Issue 2: "Database not available"
**Error**: `SUPABASE NOT PROPERLY CONFIGURED!`

**Solution**: This is expected when running without database. Ensure mock implementations are being used:
- MockProjectRepository
- MockTaskRepository
- MockUnifiedContextService
- MockTaskContextRepository

### Issue 3: "Tools registered but not accessible"
**Symptom**: Tools register successfully internally but aren't available through mcp__ prefix

**Possible Causes**:
1. FastMCP HTTP bridge not exposing tools
2. Tool registration happening after server starts
3. Middleware blocking tool discovery

**Debug Steps**:
```bash
# Check server health
curl http://localhost:8000/health

# Test MCP endpoint directly
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Check container logs
docker logs dhafnck-mcp-server --tail 100 | grep -i "tool"
```

## Prevention Checklist

To prevent this issue in the future:

1. **Always implement complete mock repositories**
   - [ ] All abstract methods implemented
   - [ ] Return appropriate mock data
   - [ ] Handle edge cases gracefully

2. **Ensure graceful database degradation**
   - [ ] Check for database availability
   - [ ] Fall back to mock implementations
   - [ ] Log warnings but don't fail

3. **Test each layer independently**
   - [ ] Domain layer entities
   - [ ] Infrastructure repositories
   - [ ] Application facades
   - [ ] Interface controllers
   - [ ] Tool registration

4. **Docker configuration**
   - [ ] Set FASTMCP_TRANSPORT=streamable-http
   - [ ] Set FASTMCP_HOST=0.0.0.0
   - [ ] Disable auth if no database
   - [ ] Mount data volumes correctly

5. **Monitoring**
   - [ ] Check health endpoint regularly
   - [ ] Monitor tool count in health response
   - [ ] Watch container logs for errors
   - [ ] Test tool availability after deployment

## Recovery Procedure

If tools disappear after a change:

1. **Run diagnostic script** to identify failing layer
2. **Fix the specific layer** that's failing
3. **Test the fix** in isolation
4. **Rebuild Docker image** with fixes
5. **Restart container** with correct environment
6. **Verify tools** are available
7. **Document the fix** for future reference

## Related Documentation

- [Architecture Overview](../architecture-design/architecture.md)
- [Domain-Driven Design](../architecture-design/domain-driven-design.md)
- [Docker Deployment Guide](../development-guides/docker-deployment.md)
- [Testing Guide](../testing/testing.md)

## Contact

If this guide doesn't resolve your issue:
1. Check recent commits for breaking changes
2. Review environment variables in docker-compose.yml
3. Ensure all dependencies are installed
4. Contact the development team with diagnostic output

---

**Last Updated**: 2025-01-31
**Version**: 1.0.0
**Status**: Complete troubleshooting guide for MCP tools availability issues