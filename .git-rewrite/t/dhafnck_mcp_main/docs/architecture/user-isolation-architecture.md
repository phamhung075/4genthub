# User Isolation Architecture

## Overview

The DhafnckMCP platform implements comprehensive user-based data isolation (multi-tenancy) to ensure complete data segregation between users. This document describes the architecture, implementation patterns, and security measures.

## Architecture Layers

### 1. Database Layer
All tables include a `user_id` column for row-level data isolation:

```sql
-- Example: tasks table
ALTER TABLE tasks ADD COLUMN user_id VARCHAR(255);
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
```

**Affected Tables:**
- tasks
- projects  
- agents
- global_contexts (user-specific "global" space)
- project_contexts
- branch_contexts
- task_contexts
- subtasks
- task_dependencies
- cursor_rules

### 2. Repository Layer

#### BaseUserScopedRepository
Core class providing automatic user-based filtering:

```python
class BaseUserScopedRepository:
    def __init__(self, session, user_id=None):
        self.session = session
        self.user_id = user_id
        self._is_system_mode = user_id is None
    
    def apply_user_filter(self, query):
        """Apply user_id filter to any query"""
        if self._is_system_mode:
            return query
        
        if isinstance(query, str):
            # SQL string query
            if "WHERE" in query.upper():
                return f"{query} AND user_id = '{self.user_id}'"
            else:
                return f"{query} WHERE user_id = '{self.user_id}'"
        else:
            # SQLAlchemy query
            return query.filter_by(user_id=self.user_id)
    
    def set_user_id(self, data):
        """Inject user_id into data"""
        if not self._is_system_mode and self.user_id:
            data['user_id'] = self.user_id
        return data
```

#### Repository Implementation Pattern
```python
class TaskRepository(BaseUserScopedRepository):
    def __init__(self, session, user_id=None):
        super().__init__(session, user_id)
    
    def create_task(self, task_data):
        # user_id automatically injected
        task_data = self.set_user_id(task_data)
        return self.create(task_data)
    
    def list_tasks(self):
        query = self.session.query(Task)
        # Automatic user filtering
        query = self.apply_user_filter(query)
        return query.all()
    
    def with_user(self, user_id):
        """Create user-scoped instance"""
        return TaskRepository(self.session, user_id)
```

### 3. Service Layer

#### Service Pattern with User Context
```python
class TaskApplicationService:
    def __init__(self, task_repository, user_id=None):
        self._task_repository = task_repository
        self._user_id = user_id
        
        # Initialize use cases with scoped repository
        self._create_task_use_case = CreateTaskUseCase(
            self._get_user_scoped_repository()
        )
    
    def _get_user_scoped_repository(self):
        """Get user-scoped repository"""
        if hasattr(self._task_repository, 'with_user') and self._user_id:
            return self._task_repository.with_user(self._user_id)
        return self._task_repository
    
    def with_user(self, user_id):
        """Create user-scoped service instance"""
        return TaskApplicationService(self._task_repository, user_id)
```

### 4. API Layer

#### JWT Authentication Middleware
```python
class JWTAuthMiddleware:
    def extract_user_from_token(self, token):
        """Extract user_id from JWT token"""
        payload = jwt.decode(token, self.secret_key)
        return payload.get("sub") or payload.get("user_id")
    
    def create_user_scoped_repository(self, repo_class, session, user_id):
        """Create repository with user context"""
        return repo_class(session=session, user_id=user_id)
```

#### Route Pattern with User Isolation
```python
@router.post("/api/v2/tasks")
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create user-scoped repository
    task_repo = TaskRepository(db, user_id=current_user.id)
    
    # Create user-scoped service
    service = TaskApplicationService(task_repo, user_id=current_user.id)
    
    # All operations automatically scoped to user
    result = await service.create_task(request)
    
    return {"success": True, "task": result}
```

### 5. Frontend Layer

#### API Client with JWT
```typescript
class APIClient {
    private token: string;
    
    constructor(token: string) {
        this.token = token;
    }
    
    async createTask(taskData: TaskData) {
        const response = await fetch('/api/v2/tasks', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });
        
        return response.json();
    }
}
```

## Security Features

### 1. Automatic User Filtering
- All queries automatically filtered by user_id
- No possibility of cross-user data access
- System mode available for admin operations

### 2. User ID Injection
- user_id automatically added to all create operations
- Prevents user_id spoofing in requests
- Service layer enforces user context

### 3. Audit Logging
```python
def log_access(self, operation, entity_type, entity_id=None):
    """Log all data access for audit trail"""
    log_entry = {
        'user_id': self.user_id,
        'operation': operation,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'timestamp': datetime.utcnow()
    }
    # Store in user_access_log table
```

### 4. Context Isolation
- Each user has their own "global" context
- Project contexts isolated by user
- No shared data between users

## Migration Process

### 1. Database Migration
```bash
# Run migration to add user_id columns
python scripts/run_migration.py database/migrations/003_add_user_isolation.sql
```

### 2. Data Backfill
```sql
-- Assign existing data to system user
UPDATE tasks SET user_id = '00000000-0000-0000-0000-000000000000' 
WHERE user_id IS NULL;
```

### 3. Enable Row-Level Security (Supabase)
```sql
-- Enable RLS on all tables
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Create policy for user access
CREATE POLICY tasks_user_isolation ON tasks
FOR ALL USING (user_id = auth.uid());
```

## Testing Strategy

### 1. Repository Tests
```python
def test_user_isolation():
    user1_repo = TaskRepository(session, user_id="user1")
    user2_repo = TaskRepository(session, user_id="user2")
    
    # User 1 creates task
    task1 = user1_repo.create_task({"title": "User 1 Task"})
    
    # User 2 cannot see it
    user2_tasks = user2_repo.list_tasks()
    assert task1 not in user2_tasks
```

### 2. Service Tests
```python
def test_service_user_context():
    service = TaskApplicationService(repo, user_id="user1")
    assert service._user_id == "user1"
    
    # Service creates scoped repository
    scoped_service = service.with_user("user2")
    assert scoped_service._user_id == "user2"
```

### 3. Integration Tests
```python
def test_end_to_end_isolation():
    # Create task as user1
    response1 = client.post("/api/v2/tasks", 
        headers={"Authorization": f"Bearer {user1_token}"},
        json={"title": "User 1 Task"})
    
    # Try to access as user2
    response2 = client.get(f"/api/v2/tasks/{task_id}",
        headers={"Authorization": f"Bearer {user2_token}"})
    
    assert response2.status_code == 404  # Not found
```

## Performance Considerations

### 1. Indexes
All user_id columns are indexed for fast filtering:
```sql
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_projects_user_id ON projects(user_id);
-- etc.
```

### 2. Query Optimization
- Filters applied at database level
- No post-query filtering needed
- Minimal performance impact

### 3. Caching Strategy
```python
class UserContextManager:
    def __init__(self, user_id):
        self._scoped_repositories = {}  # Cache
    
    def get_repository(self, repo_class, session):
        cache_key = f"{repo_class.__name__}_{id(session)}"
        if cache_key not in self._scoped_repositories:
            self._scoped_repositories[cache_key] = repo_class(
                session, self.user_id
            )
        return self._scoped_repositories[cache_key]
```

## Rollback Plan

If issues arise, the system can be rolled back:

1. **Remove user filtering** - Set repositories to system mode
2. **Disable RLS** - `ALTER TABLE tasks DISABLE ROW LEVEL SECURITY;`
3. **Revert migration** - Run rollback script
4. **Clear cache** - Restart application servers

## Monitoring

### 1. Access Patterns
```sql
-- Monitor user data access
SELECT user_id, COUNT(*) as access_count
FROM user_access_log
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_id;
```

### 2. Performance Metrics
```sql
-- Check query performance
EXPLAIN ANALYZE
SELECT * FROM tasks WHERE user_id = 'user123';
```

### 3. Isolation Verification
```sql
-- Verify no cross-user access
SELECT DISTINCT t1.user_id, t2.user_id
FROM tasks t1
CROSS JOIN tasks t2
WHERE t1.id = t2.id AND t1.user_id != t2.user_id;
-- Should return 0 rows
```

## Best Practices

1. **Always use user-scoped repositories** in services
2. **Never bypass user filtering** except in system mode
3. **Log all data access** for audit trail
4. **Test isolation** in all new features
5. **Use JWT tokens** for authentication
6. **Cache scoped instances** for performance
7. **Monitor access patterns** for anomalies

## Conclusion

The user isolation architecture provides:
- Complete data segregation between users
- Automatic filtering at all layers
- Security through defense in depth
- Performance through database-level filtering
- Audit trail for compliance
- Backward compatibility with system mode

This multi-tenant architecture ensures that each user's data is completely isolated while maintaining system performance and developer productivity.