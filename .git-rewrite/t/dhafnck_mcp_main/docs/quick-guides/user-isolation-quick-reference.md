# User Isolation Quick Reference

## Core Concepts

**User Isolation**: Every user can only see and modify their own data
**Multi-tenancy**: Multiple users share the same application instance but with isolated data
**System Mode**: Special mode for admin operations that bypasses user filtering

## Quick Patterns

### Repository Pattern
```python
# Creating a user-scoped repository
repo = TaskRepository(session, user_id="user123")

# System mode (no filtering)
repo = TaskRepository(session, user_id=None)

# Creating scoped instance from existing
scoped_repo = repo.with_user("user456")
```

### Service Pattern
```python
# Creating a user-scoped service
service = TaskApplicationService(repo, user_id="user123")

# Creating scoped instance
scoped_service = service.with_user("user456")
```

### Route Pattern
```python
@router.post("/tasks")
async def create_task(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = TaskRepository(db, user_id=current_user.id)
    service = TaskApplicationService(repo, user_id=current_user.id)
    return await service.create_task(request)
```

## Common Operations

### Creating Data (Auto User Assignment)
```python
# Repository automatically adds user_id
task = repo.create_task({
    "title": "My Task"
    # user_id added automatically
})
```

### Querying Data (Auto Filtering)
```python
# Only returns current user's tasks
tasks = repo.list_tasks()

# SQL queries also filtered
result = repo.execute_sql("SELECT * FROM tasks")
# Becomes: SELECT * FROM tasks WHERE user_id = 'user123'
```

### Updating Data (Ownership Check)
```python
# Can only update own data
success = repo.update_task(task_id, {"status": "done"})
# Returns False if task belongs to different user
```

### Deleting Data (Ownership Check)
```python
# Can only delete own data
success = repo.delete_task(task_id)
# Returns False if task belongs to different user
```

## Key Classes

### BaseUserScopedRepository
```python
from base_user_scoped_repository import BaseUserScopedRepository

class MyRepository(BaseUserScopedRepository):
    def __init__(self, session, user_id=None):
        super().__init__(session, user_id)
```

**Key Methods:**
- `apply_user_filter(query)` - Add user filtering to any query
- `set_user_id(data)` - Inject user_id into data dict
- `ensure_user_ownership(entity)` - Verify entity belongs to user
- `with_user(user_id)` - Create scoped instance

### JWTAuthMiddleware
```python
from jwt_auth_middleware import JWTAuthMiddleware

middleware = JWTAuthMiddleware(secret_key="your-secret")
user_id = middleware.extract_user_from_token(token)
```

### UserContextManager
```python
from jwt_auth_middleware import UserContextManager

manager = UserContextManager(user_id="user123")
repo = manager.get_repository(TaskRepository, session)
service = manager.get_service(TaskApplicationService, repo=repo)
```

## Testing User Isolation

### Repository Test
```python
def test_isolation():
    user1_repo = TaskRepository(session, "user1")
    user2_repo = TaskRepository(session, "user2")
    
    task = user1_repo.create_task({"title": "Test"})
    
    # User 2 cannot see user 1's task
    assert len(user2_repo.list_tasks()) == 0
```

### Service Test
```python
def test_service_context():
    service = TaskApplicationService(repo, user_id="user1")
    assert service._user_id == "user1"
    
    scoped = service.with_user("user2")
    assert scoped._user_id == "user2"
```

### API Test
```python
def test_api_isolation():
    # Create as user1
    response1 = client.post("/tasks",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Task"})
    
    # Cannot access as user2
    response2 = client.get(f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token2}"})
    assert response2.status_code == 404
```

## Database Queries

### Check User Data
```sql
-- Count records per user
SELECT user_id, COUNT(*) FROM tasks GROUP BY user_id;

-- Find orphaned records
SELECT * FROM tasks WHERE user_id IS NULL;
```

### Performance Check
```sql
-- Verify index usage
EXPLAIN SELECT * FROM tasks WHERE user_id = 'user123';
```

## Environment Variables

```bash
# Disable user isolation (development only)
DISABLE_USER_ISOLATION=true

# System user ID
SYSTEM_USER_ID=00000000-0000-0000-0000-000000000000

# JWT Secret
JWT_SECRET_KEY=your-secret-key
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `User not authorized` | Missing user_id in repository | Pass user_id to repository constructor |
| `AttributeError: 'NoneType' object has no attribute 'id'` | Entity not found (wrong user) | Check user owns the entity |
| `Invalid token` | JWT expired or invalid | Refresh token or re-authenticate |
| `Cross-user data visible` | Repository not using filter | Ensure apply_user_filter is called |
| `Cannot create without user_id` | No user context | Pass user_id to service/repository |

## Debugging Tips

### 1. Check User Context
```python
print(f"Repository user_id: {repo.user_id}")
print(f"Service user_id: {service._user_id}")
print(f"System mode: {repo._is_system_mode}")
```

### 2. Verify Query Filtering
```python
# Log SQL queries
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 3. Test in System Mode
```python
# Bypass filtering for debugging
repo = TaskRepository(session, user_id=None)
all_tasks = repo.list_tasks()  # Returns ALL tasks
```

### 4. Check Token Claims
```python
import jwt
payload = jwt.decode(token, SECRET, algorithms=["HS256"])
print(f"User ID in token: {payload.get('sub')}")
```

## Migration Checklist

- [ ] Database migration run
- [ ] user_id columns added
- [ ] Indexes created
- [ ] Data backfilled
- [ ] Repositories updated
- [ ] Services updated
- [ ] Routes updated
- [ ] Frontend updated
- [ ] Tests updated
- [ ] Monitoring added

## Best Practices

1. **Always pass user_id** when creating repositories/services
2. **Use with_user()** to create scoped instances
3. **Test isolation** in all new features
4. **Log data access** for audit trail
5. **Cache scoped instances** for performance
6. **Never bypass filtering** in production
7. **Monitor access patterns** for anomalies

## Support

- Architecture docs: `/docs/architecture/user-isolation-architecture.md`
- Migration guide: `/docs/migration-guides/user-isolation-migration-guide.md`
- Test examples: `/src/tests/task_management/integration/test_repository_user_isolation.py`
- Base repository: `/src/fastmcp/task_management/infrastructure/repositories/base_user_scoped_repository.py`