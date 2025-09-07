# Troubleshooting Guide Index

## Quick Problem Finder

Use this guide to quickly identify and resolve common issues with the DhafnckMCP system.

### 🔴 Critical Issues (System Down)

#### [MCP Tools Not Available](./MCP_TOOLS_MISSING_TROUBLESHOOTING_GUIDE.md)
**Symptoms**: 
- Error: "No such tool available: mcp__dhafnck_mcp_http__manage_task"
- Server running but 0 tools enabled
- All MCP tools inaccessible

**Quick Fix**: Run diagnostic script to identify failing layer, then apply layer-specific fixes.

#### [Database Connection Failures](../fixes/DATABASE_UNAVAILABLE_MOCK_IMPLEMENTATION_FIX.md)
**Symptoms**:
- "SUPABASE NOT PROPERLY CONFIGURED!"
- "Can't instantiate abstract class MockProjectRepository"
- Container restart loops

**Quick Fix**: Implement complete mock repositories with all abstract methods.

### 🟡 Functional Issues (Degraded Performance)

#### [Task Completion Failures](./COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md#task-completion-issues)
**Symptoms**:
- "Task completion requires context to be created first"
- Tasks stuck in "in_progress" state
- Context synchronization errors

**Quick Fix**: Enable auto-context creation in CompleteTaskUseCase.

#### [Context Hierarchy Problems](../HIERARCHICAL_CONTEXT_MIGRATION.md)
**Symptoms**:
- "Branch default_branch not found"
- Context inheritance not working
- Missing global context

**Quick Fix**: Use git_branch_id (UUID) instead of branch names.

### 🟢 Configuration Issues

#### [Docker Container Issues](./TROUBLESHOOTING.md#docker-issues)
**Symptoms**:
- Container unhealthy status
- Port binding failures
- Environment variable problems

**Quick Fix**: Check docker-compose.yml environment variables.

#### [Authentication Problems](./COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md#authentication-issues)
**Symptoms**:
- Token validation errors
- Rate limiting triggered
- MVP mode not working

**Quick Fix**: Set DHAFNCK_AUTH_ENABLED=false if no database.

## Diagnostic Tools

### Layer-by-Layer Diagnostic Script

Save this as `diagnose.py` and run to identify issues:

```python
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/path/to/dhafnck_mcp_main/src')

def test_layer(name, test_func):
    try:
        result = test_func()
        print(f"✅ {name}: PASS")
        return True
    except Exception as e:
        print(f"❌ {name}: FAIL - {e}")
        return False

# Test each architectural layer
def test_domain():
    from fastmcp.task_management.domain.entities.task import Task
    return "Domain OK"

def test_infrastructure():
    from fastmcp.task_management.infrastructure.repositories.project_repository_factory import ProjectRepositoryFactory
    repo = ProjectRepositoryFactory.create(None, "test")
    return "Infrastructure OK"

def test_application():
    from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
    facade = ProjectFacadeFactory().create_project_facade("test")
    return "Application OK"

def test_interface():
    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    tools = DDDCompliantMCPTools()
    return "Interface OK"

# Run tests
print("DIAGNOSTIC RESULTS:")
print("-" * 40)
layers = [
    ("1. Domain Layer", test_domain),
    ("2. Infrastructure Layer", test_infrastructure),
    ("3. Application Layer", test_application),
    ("4. Interface Layer", test_interface)
]

for name, test in layers:
    if not test_layer(name, test):
        print(f"\n🎯 Fix {name} first!")
        break
else:
    print("\n✅ All layers operational!")
```

### Quick Health Check

```bash
# Check if server is running
curl -s http://localhost:8000/health | python -m json.tool

# Check available tools
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' \
  | python -m json.tool | grep -c "manage_"

# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep dhafnck

# View recent errors
docker logs dhafnck-mcp-server --tail 50 | grep -i error
```

## Common Error Messages

| Error Message | Likely Cause | Quick Fix | Full Guide |
|--------------|--------------|-----------|------------|
| "No such tool available" | Tools not registered | Check mock repositories | [MCP Tools Guide](./MCP_TOOLS_MISSING_TROUBLESHOOTING_GUIDE.md) |
| "Can't instantiate abstract class" | Missing methods in mock | Implement all abstract methods | [Mock Implementation](../fixes/DATABASE_UNAVAILABLE_MOCK_IMPLEMENTATION_FIX.md) |
| "SUPABASE NOT PROPERLY CONFIGURED" | No database config | Use mock mode | [Database Guide](./COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md#database-configuration) |
| "Task completion requires context" | Context not created | Enable auto-context | [Context Guide](../HIERARCHICAL_CONTEXT_MIGRATION.md) |
| "Branch not found" | Using branch name instead of ID | Use git_branch_id | [Branch Guide](../CONTEXT_AUTO_DETECTION_FIX.md) |

## Emergency Recovery

If the system is completely broken:

1. **Stop everything**
   ```bash
   docker-compose down
   docker system prune -f
   ```

2. **Reset to known good state**
   ```bash
   git checkout main
   git pull origin main
   ```

3. **Rebuild from scratch**
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Verify recovery**
   ```bash
   ./diagnose.py  # Run diagnostic script
   curl http://localhost:8000/health
   ```

## Prevention Checklist

Before deploying changes:

- [ ] Run layer-by-layer diagnostic
- [ ] Test with database unavailable
- [ ] Verify all mock methods implemented
- [ ] Check Docker environment variables
- [ ] Test tool registration
- [ ] Verify health endpoint
- [ ] Check container logs for errors
- [ ] Test at least one MCP tool

## Getting Help

1. **Check existing guides** in this directory
2. **Run diagnostic script** to identify the issue
3. **Search error messages** in the codebase
4. **Check recent commits** for breaking changes
5. **Review Docker logs** for startup errors

## Related Documentation

- [Architecture Overview](../architecture-design/architecture.md)
- [Docker Deployment](../development-guides/docker-deployment.md)
- [Testing Guide](../testing/testing.md)
- [API Reference](../api-reference.md)

---

**Last Updated**: 2025-01-31
**Maintainer**: Development Team
**Emergency Contact**: Check .env for SUPPORT_EMAIL