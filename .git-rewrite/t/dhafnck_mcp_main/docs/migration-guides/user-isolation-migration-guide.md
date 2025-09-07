# User Isolation Migration Guide

This guide walks through migrating the DhafnckMCP platform to support complete user-based data isolation (multi-tenancy).

## Prerequisites

- Database backup created
- Test environment available
- JWT authentication configured
- All tests passing on current codebase

## Migration Steps

### Phase 1: Database Schema Updates

#### 1.1 Run Database Migration

```bash
# For PostgreSQL/Supabase
python scripts/run_supabase_migration.py database/migrations/003_add_user_isolation.sql

# For local SQLite (development)
sqlite3 dhafnck_mcp.db < database/migrations/003_add_user_isolation_sqlite.sql
```

#### 1.2 Verify Migration

```sql
-- Check columns added
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'tasks' AND column_name = 'user_id';

-- Check indexes created
SELECT indexname FROM pg_indexes 
WHERE tablename = 'tasks' AND indexname LIKE '%user_id%';
```

#### 1.3 Backfill Existing Data

```sql
-- Assign existing data to system user
UPDATE tasks SET user_id = '00000000-0000-0000-0000-000000000000' 
WHERE user_id IS NULL;

UPDATE projects SET user_id = '00000000-0000-0000-0000-000000000000' 
WHERE user_id IS NULL;

-- Repeat for all tables
```

### Phase 2: Repository Layer Updates

#### 2.1 Update Repository Base Class

All repositories should inherit from `BaseUserScopedRepository`:

```python
# Before
class TaskRepository(BaseORMRepository):
    def __init__(self, session):
        super().__init__(Task, session)

# After  
from .base_user_scoped_repository import BaseUserScopedRepository

class TaskRepository(BaseUserScopedRepository):
    def __init__(self, session, user_id=None):
        super().__init__(session, user_id)
        self.model_class = Task
```

#### 2.2 Update Repository Methods

Ensure all query methods use `apply_user_filter`:

```python
def list_tasks(self, status=None):
    query = self.session.query(Task)
    
    # Apply user filter FIRST
    query = self.apply_user_filter(query)
    
    if status:
        query = query.filter(Task.status == status)
    
    return query.all()

def create_task(self, task_data):
    # User ID automatically injected
    task_data = self.set_user_id(task_data)
    
    task = Task(**task_data)
    self.session.add(task)
    self.session.commit()
    
    return task
```

#### 2.3 Add with_user Method

```python
def with_user(self, user_id):
    """Create a user-scoped instance"""
    return TaskRepository(self.session, user_id)
```

### Phase 3: Service Layer Updates

#### 3.1 Add User Context to Services

```python
# Before
class TaskApplicationService:
    def __init__(self, task_repository):
        self._task_repository = task_repository

# After
class TaskApplicationService:
    def __init__(self, task_repository, user_id=None):
        self._task_repository = task_repository
        self._user_id = user_id
        
    def _get_user_scoped_repository(self):
        if hasattr(self._task_repository, 'with_user') and self._user_id:
            return self._task_repository.with_user(self._user_id)
        return self._task_repository
    
    def with_user(self, user_id):
        return TaskApplicationService(self._task_repository, user_id)
```

#### 3.2 Update Use Case Initialization

```python
def __init__(self, task_repository, user_id=None):
    self._task_repository = task_repository
    self._user_id = user_id
    
    # Use scoped repository in use cases
    self._create_task_use_case = CreateTaskUseCase(
        self._get_user_scoped_repository()
    )
```

### Phase 4: API Layer Updates

#### 4.1 Create JWT Middleware

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
        return User(id=user_id)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401)
```

#### 4.2 Update API Routes

```python
# Before
@router.post("/tasks")
async def create_task(request: CreateTaskRequest, db = Depends(get_db)):
    repo = TaskRepository(db)
    service = TaskApplicationService(repo)
    return await service.create_task(request)

# After
@router.post("/api/v2/tasks")
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create user-scoped repository
    repo = TaskRepository(db, user_id=current_user.id)
    
    # Create user-scoped service
    service = TaskApplicationService(repo, user_id=current_user.id)
    
    # Execute with user context
    return await service.create_task(request)
```

### Phase 5: Frontend Updates

#### 5.1 Add JWT to API Calls

```typescript
// api.ts
export class API {
    private token: string;
    
    constructor(token: string) {
        this.token = token;
    }
    
    private getHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }
    
    async createTask(data: TaskData) {
        const response = await fetch('/api/v2/tasks', {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (response.status === 401) {
            // Token expired, refresh
            await this.refreshToken();
            return this.createTask(data);
        }
        
        return response.json();
    }
}
```

#### 5.2 Update State Management

```typescript
// store.ts
interface AppState {
    user: User | null;
    token: string | null;
    tasks: Task[];  // Now user-specific
}

// Actions
const fetchUserTasks = async () => {
    // Only fetches current user's tasks
    const tasks = await api.getTasks();
    dispatch({ type: 'SET_TASKS', tasks });
};
```

### Phase 6: Testing

#### 6.1 Repository Tests

```python
def test_user_isolation_in_repository():
    session = create_test_session()
    
    # Create repos for different users
    user1_repo = TaskRepository(session, user_id="user1")
    user2_repo = TaskRepository(session, user_id="user2")
    
    # User 1 creates task
    task1 = user1_repo.create_task({"title": "User 1 Task"})
    
    # User 2 cannot see it
    user2_tasks = user2_repo.list_tasks()
    assert len(user2_tasks) == 0
    
    # User 1 can see it
    user1_tasks = user1_repo.list_tasks()
    assert len(user1_tasks) == 1
```

#### 6.2 Service Tests

```python
def test_service_user_context_propagation():
    mock_repo = Mock()
    mock_repo.with_user = Mock(return_value=mock_repo)
    
    service = TaskApplicationService(mock_repo, user_id="user1")
    
    # Verify repository was scoped
    mock_repo.with_user.assert_called_with("user1")
```

#### 6.3 Integration Tests

```python
def test_api_user_isolation():
    # Get tokens for two users
    user1_token = login("user1@test.com", "password1")
    user2_token = login("user2@test.com", "password2")
    
    # Create task as user1
    response1 = client.post(
        "/api/v2/tasks",
        headers={"Authorization": f"Bearer {user1_token}"},
        json={"title": "User 1 Task"}
    )
    task_id = response1.json()["task"]["id"]
    
    # Try to access as user2
    response2 = client.get(
        f"/api/v2/tasks/{task_id}",
        headers={"Authorization": f"Bearer {user2_token}"}
    )
    
    assert response2.status_code == 404
```

### Phase 7: Deployment

#### 7.1 Staging Deployment

1. Deploy code to staging
2. Run migration on staging database
3. Run integration tests
4. Monitor for 24 hours

#### 7.2 Production Deployment

1. **Backup production database**
2. Deploy code (backward compatible)
3. Run migration
4. Monitor closely for issues
5. Run smoke tests

#### 7.3 Rollback Plan

If issues occur:

```bash
# 1. Revert code deployment
git revert <commit>
kubectl rollout undo deployment/api

# 2. Disable user filtering (hotfix)
export DISABLE_USER_ISOLATION=true

# 3. Rollback database (if needed)
psql < backup.sql
```

## Verification Checklist

- [ ] All tests passing
- [ ] Database migration successful
- [ ] Indexes created on user_id columns
- [ ] Existing data backfilled
- [ ] Repositories inherit from BaseUserScopedRepository
- [ ] Services accept and propagate user_id
- [ ] API routes extract user from JWT
- [ ] Frontend sends JWT with requests
- [ ] Integration tests confirm isolation
- [ ] No performance degradation
- [ ] Audit logging working
- [ ] Monitoring dashboards updated

## Common Issues and Solutions

### Issue 1: Missing user_id in existing data
**Solution**: Run backfill script to assign system user

### Issue 2: Performance degradation
**Solution**: Ensure indexes exist on all user_id columns

### Issue 3: Tests failing after migration
**Solution**: Update test fixtures to include user_id

### Issue 4: Frontend getting 401 errors
**Solution**: Ensure JWT token is included in all API calls

### Issue 5: Cross-user data visible
**Solution**: Check repository is using apply_user_filter

## Monitoring Post-Migration

```sql
-- Check data isolation
SELECT COUNT(DISTINCT user_id) as unique_users,
       COUNT(*) as total_records
FROM tasks;

-- Monitor query performance
SELECT query, mean_exec_time
FROM pg_stat_statements
WHERE query LIKE '%user_id%'
ORDER BY mean_exec_time DESC;

-- Audit access patterns
SELECT user_id, 
       DATE(created_at) as date,
       COUNT(*) as operations
FROM user_access_log
GROUP BY user_id, DATE(created_at);
```

## Support

For issues during migration:
1. Check logs for specific error messages
2. Verify migration ran successfully
3. Ensure all code updates deployed
4. Contact DevOps team if database issues

## Conclusion

This migration enables complete user data isolation while maintaining backward compatibility. Follow the phases in order and thoroughly test each phase before proceeding to the next.