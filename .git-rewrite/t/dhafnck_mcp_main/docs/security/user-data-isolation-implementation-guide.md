# User Data Isolation Implementation Guide

## Overview
This guide provides a comprehensive approach to implementing user-based data isolation in the DhafnckMCP system, ensuring that users can only access and modify their own data.

## Current Architecture Analysis

### Authentication System
- **Framework**: Supabase Authentication with JWT tokens
- **Location**: `/src/fastmcp/auth/`
- **Key Components**:
  - `supabase_auth.py`: Handles signup, login, email verification
  - `fastapi_auth.py`: OAuth2PasswordBearer implementation
  - `jwt_service.py`: JWT token generation and validation

### Current User Extraction
```python
# From fastapi_auth.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = jwt_service.verify_access_token(token)
    user_id = payload.get("sub")
    return user_repository.find_by_id(user_id)
```

## Implementation Strategy

### 1. Repository Layer Enhancement

#### Base Repository Pattern
Create a base repository that automatically includes user_id filtering:

```python
# src/fastmcp/task_management/infrastructure/repositories/base_user_scoped_repository.py
class BaseUserScopedRepository:
    def __init__(self, session: Session, user_id: str):
        self.session = session
        self.user_id = user_id
    
    def get_user_filter(self):
        """Returns SQLAlchemy filter for user_id"""
        return {"user_id": self.user_id}
```

#### Task Repository Update
```python
# src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py
class TaskRepository(BaseUserScopedRepository):
    def find_all(self, **filters):
        # Automatically add user_id to all queries
        user_filter = self.get_user_filter()
        combined_filters = {**filters, **user_filter}
        return self.session.query(Task).filter_by(**combined_filters).all()
    
    def create(self, task_data):
        # Automatically set user_id on creation
        task_data['user_id'] = self.user_id
        return super().create(task_data)
```

### 2. Application Layer Enhancement

#### Facade Pattern with User Context
```python
# src/fastmcp/task_management/application/facades/task_application_facade.py
class TaskApplicationFacade:
    def __init__(self, task_repository: TaskRepository, user_id: str):
        self.task_repository = task_repository
        self.user_id = user_id
        
        # Initialize use cases with user-scoped repository
        self._create_task_use_case = CreateTaskUseCase(
            task_repository.with_user(user_id)
        )
```

### 3. API Layer Enhancement

#### Protected Routes with User Context
```python
# src/fastmcp/server/routes/protected_task_routes.py
from fastapi import Depends
from ..auth.interface.fastapi_auth import get_current_user

@router.post("/tasks")
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user)
):
    # Create user-scoped facade
    facade = TaskApplicationFacade(
        task_repository=get_task_repository(),
        user_id=current_user.id
    )
    
    # All operations automatically scoped to user
    return facade.create_task(request)
```

### 4. Database Schema Updates

#### Add user_id to All Tables
```sql
-- database/migrations/003_add_user_isolation.sql
ALTER TABLE tasks ADD COLUMN user_id UUID NOT NULL;
ALTER TABLE projects ADD COLUMN user_id UUID NOT NULL;
ALTER TABLE git_branches ADD COLUMN user_id UUID NOT NULL;
ALTER TABLE contexts ADD COLUMN user_id UUID NOT NULL;
ALTER TABLE agents ADD COLUMN user_id UUID NOT NULL;

-- Add indexes for performance
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_git_branches_user_id ON git_branches(user_id);
CREATE INDEX idx_contexts_user_id ON contexts(user_id);
CREATE INDEX idx_agents_user_id ON agents(user_id);

-- Add foreign key constraints
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### 5. Row-Level Security (RLS) - Supabase

For Supabase deployments, implement RLS policies:

```sql
-- Enable RLS on tables
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE git_branches ENABLE ROW LEVEL SECURITY;

-- Create policies for tasks
CREATE POLICY "Users can view own tasks" ON tasks
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own tasks" ON tasks
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tasks" ON tasks
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tasks" ON tasks
    FOR DELETE USING (auth.uid() = user_id);
```

## Implementation Steps

### Phase 1: Database Migration
1. Create migration script to add user_id columns
2. Backfill existing data with a default/system user_id
3. Add indexes and constraints
4. Enable RLS policies for Supabase

### Phase 2: Repository Layer
1. Create BaseUserScopedRepository class
2. Update all repository classes to extend from base
3. Modify all query methods to include user_id filter
4. Update create/update methods to set user_id

### Phase 3: Application Layer
1. Update facades to accept user_id parameter
2. Modify use cases to work with user-scoped repositories
3. Update context service for user isolation
4. Implement user context propagation

### Phase 4: API Layer
1. Add authentication dependency to all routes
2. Extract user_id from JWT token
3. Pass user_id to application layer
4. Update API documentation

### Phase 5: Testing
1. Create unit tests for user-scoped repositories
2. Add integration tests for data isolation
3. Implement end-to-end tests for multi-user scenarios
4. Performance testing with user filtering

## Security Considerations

### Token Validation
- Always validate JWT tokens on every request
- Check token expiration
- Verify token signature
- Handle token refresh properly

### Data Access Patterns
- Never allow direct database access without user context
- Implement audit logging for all data access
- Use prepared statements to prevent SQL injection
- Validate user_id consistency across related entities

### Error Handling
- Don't expose user existence in error messages
- Return generic 404 for unauthorized access attempts
- Log security violations for monitoring
- Implement rate limiting per user

## Testing Strategy

### Unit Tests
```python
def test_user_data_isolation():
    # Create repositories for different users
    user1_repo = TaskRepository(session, user_id="user1")
    user2_repo = TaskRepository(session, user_id="user2")
    
    # Create tasks for each user
    task1 = user1_repo.create({"title": "User 1 Task"})
    task2 = user2_repo.create({"title": "User 2 Task"})
    
    # Verify isolation
    user1_tasks = user1_repo.find_all()
    assert len(user1_tasks) == 1
    assert user1_tasks[0].id == task1.id
    
    user2_tasks = user2_repo.find_all()
    assert len(user2_tasks) == 1
    assert user2_tasks[0].id == task2.id
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_api_user_isolation():
    # Create two users
    user1_token = await create_test_user("user1@test.com")
    user2_token = await create_test_user("user2@test.com")
    
    # Create task as user1
    response1 = await client.post(
        "/api/tasks",
        json={"title": "User 1 Task"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    task1_id = response1.json()["id"]
    
    # Try to access user1's task as user2 (should fail)
    response2 = await client.get(
        f"/api/tasks/{task1_id}",
        headers={"Authorization": f"Bearer {user2_token}"}
    )
    assert response2.status_code == 404
```

## Monitoring and Compliance

### Audit Logging
```python
# Log all data access with user context
logger.info(f"User {user_id} accessed task {task_id}")
logger.warning(f"User {user_id} denied access to task {task_id}")
```

### Metrics to Track
- Data access patterns per user
- Failed authorization attempts
- Cross-user access attempts
- Performance impact of user filtering

### Compliance Reporting
- Generate user data access reports
- Track data retention per user
- Support GDPR data export/deletion
- Maintain audit trail for compliance

## Rollback Plan

If issues arise during implementation:

1. **Database**: Keep backup of schema before migration
2. **Code**: Use feature flags to enable/disable user isolation
3. **API**: Maintain backward compatibility with versioning
4. **Testing**: Run parallel systems during transition

## Performance Optimization

### Database Indexes
```sql
-- Composite indexes for common queries
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);
```

### Caching Strategy
```python
# Cache user-specific data with user_id in key
cache_key = f"user:{user_id}:tasks:list"
```

### Query Optimization
- Use database views for complex user-scoped queries
- Implement pagination for large result sets
- Consider partitioning tables by user_id for scale

## Conclusion

This implementation ensures complete data isolation between users while maintaining system performance and usability. The phased approach allows for gradual rollout with minimal disruption to existing functionality.

## Next Steps

1. Review and approve implementation plan
2. Create detailed technical specifications
3. Set up development environment with test users
4. Begin Phase 1 implementation
5. Schedule security review after each phase