# MCP Authentication Fix Prompts - Implementation Guide

**Date:** 2025-09-05  
**Issue:** MCP Authentication Testing Blocker  
**Priority:** CRITICAL  
**Target:** Development Team

## Overview

This document provides specific implementation prompts to resolve the MCP authentication testing blocker. The issue prevents all MCP tool testing due to JWT authentication requirements without a testing bypass mechanism.

---

## PROMPT 1: Backend Authentication Bypass Implementation

### FOR: Backend Developer / Python Developer

```
URGENT TASK: Implement MCP Testing Authentication Bypass

ISSUE: All MCP tools fail with "No user ID was provided" due to JWT middleware blocking requests without valid tokens. Testing cannot proceed.

REQUIREMENTS:
1. Add MCP_AUTH_MODE environment variable to application settings
2. Modify JWTAuthMiddleware to detect testing mode for MCP requests
3. Bypass JWT validation for /mcp/ paths when MCP_AUTH_MODE=testing
4. Auto-assign test user ID for bypassed requests
5. Maintain security - only work in development/testing environments

IMPLEMENTATION LOCATION:
- File: 4genthub_main/src/infrastructure/auth/jwt_middleware.py
- File: 4genthub_main/src/config/settings.py

CODE TEMPLATE:
```python
# In settings.py
class Settings(BaseSettings):
    MCP_AUTH_MODE: str = "production"  # testing, production
    MCP_TEST_USER_ID: str = "test-user-12345"
    
    @property
    def is_mcp_testing_mode(self) -> bool:
        return self.MCP_AUTH_MODE.lower() == "testing"

# In jwt_middleware.py
async def __call__(self, request: Request, call_next):
    # Check for MCP testing bypass
    if (self.settings.is_mcp_testing_mode and 
        request.url.path.startswith('/mcp/')):
        # Bypass authentication for MCP tools in testing
        request.state.user_id = self.settings.MCP_TEST_USER_ID
        request.state.authenticated = True
        return await call_next(request)
    
    # Normal JWT validation continues...
```

ARCHITECTURE: Follow DDD pattern - Infrastructure layer modification
TESTING: Verify all MCP operations work with bypass enabled
SECURITY: Ensure bypass is disabled in production environments

EXPECTED RESULT: All MCP tools should work when MCP_AUTH_MODE=testing
```

---

## PROMPT 2: Docker Environment Configuration

### FOR: DevOps Engineer / Infrastructure Team

```
TASK: Configure MCP Testing Environment Variables

CONTEXT: MCP tools require authentication bypass for testing. Need environment configuration to support testing mode.

REQUIREMENTS:
1. Add MCP_AUTH_MODE=testing to docker-compose.yml
2. Add MCP_TEST_USER_ID environment variable
3. Create testing-specific Docker profile if needed
4. Update docker-menu.sh to support MCP testing mode
5. Document environment setup

FILES TO MODIFY:
- docker-compose.yml
- .env.example
- docker-system/docker-menu.sh

DOCKER-COMPOSE ADDITION:
```yaml
services:
  4genthub-backend:
    environment:
      - MCP_AUTH_MODE=${MCP_AUTH_MODE:-production}
      - MCP_TEST_USER_ID=${MCP_TEST_USER_ID:-test-user-12345}
```

.ENV.EXAMPLE ADDITION:
```
# MCP Testing Configuration
MCP_AUTH_MODE=testing
MCP_TEST_USER_ID=test-user-12345
```

DOCKER MENU OPTION:
Add option "T" - Enable MCP Testing Mode
- Sets MCP_AUTH_MODE=testing
- Rebuilds containers with testing configuration
- Displays testing status

EXPECTED RESULT: Easy switching between production and testing authentication modes
```

---

## PROMPT 3: Database User Management for Testing

### FOR: Database Developer / Backend Developer

```
TASK: Ensure Test User Exists in Database

ISSUE: MCP authentication bypass will use test-user-12345, but this user may not exist in the database, causing foreign key constraint errors.

REQUIREMENTS:
1. Create database migration or seed data for test user
2. Ensure test user has proper permissions for all operations
3. Handle both Keycloak and local authentication scenarios
4. Create test projects/branches if needed for comprehensive testing

IMPLEMENTATION OPTIONS:

Option A - Database Seed:
```python
# In database seeds
async def create_test_user():
    test_user = User(
        id="test-user-12345",
        username="mcp-test-user",
        email="mcp-test@example.com",
        is_active=True,
        created_at=datetime.utcnow()
    )
    await user_repository.create(test_user)
```

Option B - Auto-Creation in Middleware:
```python
# In JWT middleware bypass
async def ensure_test_user_exists(user_id: str):
    user = await user_repository.get_by_id(user_id)
    if not user:
        user = await user_repository.create(User(
            id=user_id,
            username="mcp-test-user",
            email="mcp-test@example.com"
        ))
    return user
```

ARCHITECTURE: Domain layer (User entity) + Infrastructure layer (Repository)
TESTING: Verify test user can create projects, branches, tasks, contexts
DATABASE: Ensure proper foreign key relationships work

EXPECTED RESULT: All MCP operations should work without foreign key errors
```

---

## PROMPT 4: MCP Integration Testing Framework

### FOR: Test Engineer / QA Engineer

```
TASK: Create Automated MCP Integration Test Suite

CONTEXT: Once authentication bypass is implemented, we need comprehensive automated testing to prevent future regressions.

REQUIREMENTS:
1. Create pytest-based MCP integration test suite
2. Test all MCP operations (project, branch, task, context, agent management)
3. Verify authentication bypass works correctly
4. Test both success and failure scenarios
5. Include performance benchmarks

TEST STRUCTURE:
```python
# tests/integration/test_mcp_integration.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def mcp_testing_client():
    # Configure client with MCP_AUTH_MODE=testing
    app.dependency_overrides[get_settings] = lambda: Settings(MCP_AUTH_MODE="testing")
    return TestClient(app)

class TestMCPAuthentication:
    def test_mcp_auth_bypass_enabled(self, mcp_testing_client):
        # Test authentication bypass works
        response = mcp_testing_client.post("/mcp/manage_project", 
                                         json={"action": "list"})
        assert response.status_code != 401
        
    def test_mcp_production_mode_blocks(self, production_client):
        # Test production mode still requires auth
        response = production_client.post("/mcp/manage_project",
                                        json={"action": "list"})
        assert response.status_code == 401

class TestMCPOperations:
    def test_project_management_workflow(self, mcp_testing_client):
        # Test complete project workflow
        # create → list → update → health_check
        
    def test_task_management_workflow(self, mcp_testing_client):
        # Test complete task workflow
        # create → update → complete → search
```

COVERAGE: Aim for 100% MCP operation coverage
AUTOMATION: Integrate with CI/CD pipeline
REPORTING: Generate detailed test reports for each MCP operation

EXPECTED RESULT: Comprehensive test suite preventing MCP regressions
```

---

## PROMPT 5: Documentation and Setup Guide

### FOR: Technical Writer / Documentation Team

```
TASK: Create MCP Testing Setup Documentation

PURPOSE: Document the MCP testing environment setup for future developers and testers.

REQUIREMENTS:
1. Update README.md with MCP testing section
2. Create step-by-step setup guide
3. Document troubleshooting steps
4. Include testing examples

DOCUMENTATION STRUCTURE:

## MCP Testing Environment Setup

### Prerequisites
- Docker and docker-compose installed
- Project environment configured

### Quick Setup
```bash
# 1. Enable MCP testing mode
echo "MCP_AUTH_MODE=testing" >> .env
echo "MCP_TEST_USER_ID=test-user-12345" >> .env

# 2. Rebuild containers
cd docker-system
./docker-menu.sh
# Select option "R" for rebuild

# 3. Verify MCP testing works
# Test any MCP operation - should not require authentication
```

### Verification Steps
1. Test project creation: Should work without authentication errors
2. Test task management: Should create/update/complete successfully
3. Test context operations: Should inherit properly
4. Check logs: No authentication errors in backend logs

### Troubleshooting
- If still getting auth errors: Check MCP_AUTH_MODE environment variable
- If foreign key errors: Verify test user exists in database
- If Docker issues: Rebuild containers with testing configuration

### Production Safety
- Never use MCP_AUTH_MODE=testing in production
- Production deployments should always use proper JWT authentication
- Test user should not exist in production databases
```

LOCATIONS:
- Update: README.md (add MCP Testing section)
- Create: ai_docs/setup-guides/mcp-testing-setup.md
- Update: ai_docs/index.md (add testing guide reference)

EXPECTED RESULT: Clear setup instructions for MCP testing environment
```

---

## Implementation Priority

### Phase 1 (CRITICAL - Immediate)
1. **Backend Authentication Bypass** (Prompt 1)
2. **Docker Environment Configuration** (Prompt 2)

### Phase 2 (HIGH - Within 24 hours)
3. **Database User Management** (Prompt 3)
4. **Verification Testing** (Manual verification of all MCP operations)

### Phase 3 (MEDIUM - Within 1 week)  
5. **Automated Integration Tests** (Prompt 4)
6. **Documentation Updates** (Prompt 5)

## Success Criteria

✅ All MCP operations work without authentication errors  
✅ Testing mode can be easily enabled/disabled  
✅ Production security is maintained  
✅ Test user exists and has proper permissions  
✅ Comprehensive test suite prevents regressions  
✅ Documentation enables easy setup for new developers  

## Post-Implementation Testing

Once fixes are implemented, run the comprehensive MCP testing suite:

```bash
# Enable testing mode
export MCP_AUTH_MODE=testing
export MCP_TEST_USER_ID=test-user-12345

# Run comprehensive tests
python -m pytest tests/integration/test_mcp_comprehensive.py -v

# Or use the test orchestrator agent
# (All 7 phases should now pass successfully)
```

---

**Created by:** test-orchestrator-agent  
**Issue Reference:** mcp-authentication-testing-blocker-2025-09-05.md  
**Implementation Target:** Development Team  
**Expected Resolution:** 24-48 hours