# Repository Switching Strategy Guide

## Overview
This guide explains how the system automatically switches between different repository implementations based on environment configuration.

## Repository Selection Matrix

| Environment | DATABASE_TYPE | REDIS_ENABLED | Repository Used | Cache Layer |
|------------|---------------|---------------|-----------------|-------------|
| test | (ignored) | (ignored) | SQLiteRepository | None |
| production | supabase | true | SupabaseRepository | Redis Cache |
| production | supabase | false | SupabaseRepository | None |
| production | postgresql | true | PostgreSQLRepository | Redis Cache |
| production | postgresql | false | PostgreSQLRepository | None |

## Configuration Examples

### 1. Local Development (Testing)
```bash
# .env.test  
ENVIRONMENT=test
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/4genthub_test
# Test with PostgreSQL for consistency with production
```

### 2. Production with Supabase + Redis
```bash
# .env.production
ENVIRONMENT=production
DATABASE_TYPE=supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
REDIS_ENABLED=true
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_password
```

### 3. Production with Supabase (No Cache)
```bash
# .env.production.nocache
ENVIRONMENT=production
DATABASE_TYPE=supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
REDIS_ENABLED=false
# System works without cache, direct database access
```

## Repository Factory Implementation

```python
class RepositoryFactory:
    """Central factory that decides which repository to use"""
    
    @staticmethod
    def get_repository_for_entity(entity_type: str):
        """
        Generic method to get repository for any entity type
        """
        # Step 1: Determine base repository
        base_repo = RepositoryFactory._get_base_repository(entity_type)
        
        # Step 2: Wrap with cache if needed
        if RepositoryFactory._should_use_cache():
            return RepositoryFactory._wrap_with_cache(base_repo, entity_type)
        
        return base_repo
    
    @staticmethod
    def _get_base_repository(entity_type: str):
        """Select base repository based on environment"""
        env = os.getenv('ENVIRONMENT', 'production')
        
        if env == 'test':
            # Test mode: Always use SQLite
            return RepositoryFactory._create_sqlite_repository(entity_type)
        
        # Production mode: Check database type
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        
        if db_type == 'supabase':
            return RepositoryFactory._create_supabase_repository(entity_type)
        elif db_type == 'postgresql':
            return RepositoryFactory._create_postgresql_repository(entity_type)
        else:
            raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")
    
    @staticmethod
    def _should_use_cache() -> bool:
        """Determine if caching should be enabled"""
        # Never cache in test mode
        if os.getenv('ENVIRONMENT') == 'test':
            return False
        
        # Check Redis configuration
        redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        if not redis_enabled:
            return False
        
        # Try to connect to Redis
        try:
            redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD'),
                db=int(os.getenv('REDIS_DB', 0))
            )
            redis_client.ping()
            return True
        except:
            logger.warning("Redis not available, proceeding without cache")
            return False
    
    @staticmethod
    def _wrap_with_cache(base_repo, entity_type: str):
        """Wrap repository with caching layer"""
        cache_wrapper_map = {
            'task': CachedTaskRepository,
            'project': CachedProjectRepository,
            'context': CachedContextRepository,
            'agent': CachedAgentRepository,
        }
        
        wrapper_class = cache_wrapper_map.get(entity_type)
        if wrapper_class:
            return wrapper_class(base_repo)
        
        return base_repo  # No cache wrapper available
```

## Repository Switching Flow

```mermaid
graph TD
    Start[Request Arrives] --> CheckEnv{Check ENVIRONMENT}
    
    CheckEnv -->|test| SQLite[Create SQLite Repository]
    CheckEnv -->|production| CheckDB{Check DATABASE_TYPE}
    
    CheckDB -->|supabase| Supabase[Create Supabase Repository]
    CheckDB -->|postgresql| PostgreSQL[Create PostgreSQL Repository]
    
    SQLite --> NoCache[Return without cache]
    
    Supabase --> CheckRedis{REDIS_ENABLED?}
    PostgreSQL --> CheckRedis
    
    CheckRedis -->|false| DirectDB[Return Direct Repository]
    CheckRedis -->|true| TryRedis{Try Redis Connection}
    
    TryRedis -->|success| WrapCache[Wrap with Cache Layer]
    TryRedis -->|failure| Fallback[Log Warning & Return Direct]
    
    WrapCache --> Return[Return Cached Repository]
    DirectDB --> Return
    Fallback --> Return
    NoCache --> Return
```

## Implementation Examples

### Task Repository Factory
```python
# src/fastmcp/task_management/infrastructure/repositories/task_repository_factory.py

class TaskRepositoryFactory:
    def create_repository(self, project_id: str, git_branch_name: str, user_id: str):  # Note: Consider updating to git_branch_id (UUID)
        """Create task repository with automatic environment detection"""
        
        # Check if we're in test mode
        if os.getenv('ENVIRONMENT') == 'test':
            return SQLiteTaskRepository(
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id
            )
        
        # Production mode - check database configuration
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        
        if db_type == 'supabase':
            base_repo = SupabaseTaskRepository(
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id
            )
        else:
            # Fallback to ORM repository
            base_repo = ORMTaskRepository(
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id
            )
        
        # Check if caching should be enabled
        if self._should_enable_cache():
            return CachedTaskRepository(base_repo)
        
        return base_repo
```

### Context Repository Factory
```python
# src/fastmcp/task_management/infrastructure/repositories/context_repository_factory.py

class ContextRepositoryFactory:
    @staticmethod
    def create_global_context_repository(user_id: str):
        """Create global context repository"""
        if os.getenv('ENVIRONMENT') == 'test':
            return MockGlobalContextRepository(user_id)
        
        return GlobalContextRepository(user_id)
    
    @staticmethod
    def create_project_context_repository(project_id: str, user_id: str):
        """Create project context repository"""
        if os.getenv('ENVIRONMENT') == 'test':
            return MockProjectContextRepository(project_id, user_id)
        
        return ProjectContextRepository(project_id, user_id)
```

## Testing Different Configurations

### 1. Test SQLite Repository
```python
# tests/test_sqlite_repository.py
def test_sqlite_repository():
    os.environ['ENVIRONMENT'] = 'test'
    
    factory = RepositoryFactory()
    repo = factory.get_task_repository()
    
    assert isinstance(repo, SQLiteTaskRepository)
    assert not isinstance(repo, CachedTaskRepository)
```

### 2. Test Supabase with Cache
```python
# tests/test_supabase_cached.py
def test_supabase_with_cache():
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['DATABASE_TYPE'] = 'supabase'
    os.environ['REDIS_ENABLED'] = 'true'
    
    factory = RepositoryFactory()
    repo = factory.get_task_repository()
    
    assert isinstance(repo, CachedTaskRepository)
    assert isinstance(repo.base_repo, SupabaseTaskRepository)
```

### 3. Test Supabase without Cache
```python
# tests/test_supabase_direct.py
def test_supabase_without_cache():
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['DATABASE_TYPE'] = 'supabase'
    os.environ['REDIS_ENABLED'] = 'false'
    
    factory = RepositoryFactory()
    repo = factory.get_task_repository()
    
    assert isinstance(repo, SupabaseTaskRepository)
    assert not isinstance(repo, CachedTaskRepository)
```

## Docker Compose Configurations

### Development (PostgreSQL)
```yaml
# docker-compose.dev.yml
services:
  app:
    environment:
      - ENVIRONMENT=development
      - DATABASE_TYPE=postgresql
      - DATABASE_URL=postgresql://dev_user:dev_password@postgres:5432/4genthub_dev
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: 4genthub_dev
```

### Production (Supabase + Redis)
```yaml
# docker-compose.prod.yml
services:
  app:
    environment:
      - ENVIRONMENT=production
      - DATABASE_TYPE=supabase
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - REDIS_ENABLED=true
      - REDIS_HOST=redis
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Production (Supabase Only)
```yaml
# docker-compose.prod.nocache.yml
services:
  app:
    environment:
      - ENVIRONMENT=production
      - DATABASE_TYPE=supabase
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - REDIS_ENABLED=false
```

## Monitoring Repository Selection

### Logging Configuration
```python
# src/fastmcp/task_management/infrastructure/repositories/repository_factory.py

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RepositoryFactory:
    @staticmethod
    def get_task_repository():
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        redis_enabled = os.getenv('REDIS_ENABLED', 'true')
        
        logger.info(f"""
        Repository Selection:
        - Environment: {env}
        - Database Type: {db_type}
        - Redis Enabled: {redis_enabled}
        """)
        
        # ... selection logic ...
        
        logger.info(f"Selected Repository: {repository.__class__.__name__}")
        return repository
```

### Health Check Endpoint
```python
# src/fastmcp/server/routes/health.py

@app.get("/health/repositories")
def check_repository_configuration():
    """Health check endpoint showing repository configuration"""
    return {
        "environment": os.getenv('ENVIRONMENT', 'production'),
        "database_type": os.getenv('DATABASE_TYPE', 'supabase'),
        "redis_enabled": os.getenv('REDIS_ENABLED', 'true'),
        "repositories": {
            "task": RepositoryFactory.get_task_repository().__class__.__name__,
            "project": RepositoryFactory.get_project_repository().__class__.__name__,
            "context": RepositoryFactory.get_context_repository().__class__.__name__,
        }
    }
```

## Troubleshooting

### Issue: Wrong Repository Being Used
1. Check environment variables: `env | grep -E 'ENVIRONMENT|DATABASE_TYPE|REDIS'`
2. Check application logs for repository selection messages
3. Verify configuration file is being loaded
4. Use health check endpoint to verify configuration

### Issue: Cache Not Working
1. Verify REDIS_ENABLED=true
2. Check Redis connection: `redis-cli ping`
3. Check Redis logs: `docker logs redis_container`
4. Verify Redis credentials in environment

### Issue: Test Using Production Database
1. Ensure ENVIRONMENT=test in test configuration
2. Check test runner environment variables
3. Verify test fixtures set correct environment

## Best Practices

1. **Always use factory pattern** - Never instantiate repositories directly
2. **Environment-based configuration** - Use environment variables for all settings
3. **Graceful fallbacks** - System should work even if Redis is unavailable
4. **Clear logging** - Log repository selection for debugging
5. **Health checks** - Provide endpoints to verify configuration
6. **Test all combinations** - Test with cache on/off, different databases

## Summary

The repository switching strategy provides:
- **Flexibility**: Easy switching between databases
- **Performance**: Optional caching layer
- **Testability**: Isolated test environment
- **Reliability**: Graceful degradation without cache
- **Simplicity**: Single configuration point

By following this guide, the system automatically selects the appropriate repository based on environment configuration, ensuring optimal performance and reliability in all scenarios.