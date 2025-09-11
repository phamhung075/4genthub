# MCP Server Architecture Guide & Agent Instructions

## 🏗️ Complete Architecture Overview

```mermaid
graph TB
    Client[MCP Client] --> Interface[Interface Layer - Controllers]
    Interface --> Application[Application Layer - Facades/Use Cases]
    Application --> Domain[Domain Layer - Entities/Services]
    Application --> Infrastructure[Infrastructure Layer]
    
    Infrastructure --> Factory[Repository Factory]
    Factory --> |TEST MODE| SQLite[SQLite Repository]
    Factory --> |PROD MODE| Supabase[Supabase Repository]
    
    Infrastructure --> Cache{Cache Enabled?}
    Cache --> |YES| Redis[Redis Cache Layer]
    Cache --> |NO| Direct[Direct DB Access]
    
    Redis --> Supabase
    Direct --> Supabase
```

## 📋 Agent Instructions: Follow This Architecture

### 1. Request Flow Pattern

```python
# CORRECT FLOW:
MCP Request 
    → Controller (Interface Layer)
    → Facade (Application Layer)  
    → Use Case (Business Logic)
    → Repository Factory (Infrastructure)
    → Repository Implementation (Based on Config)
    → Cache Layer (If Enabled)
    → Database (Supabase/SQLite)
```

### 2. Layer Responsibilities

#### Interface Layer (Controllers)
```python
# src/fastmcp/task_management/interface/controllers/task_mcp_controller.py
class TaskMCPController:
    """
    RESPONSIBILITY: 
    - Receive MCP requests
    - Validate input
    - Format responses
    - Handle errors gracefully
    """
    def __init__(self):
        self.facade = TaskApplicationFacade()
        self.response_formatter = StandardResponseFormatter()
    
    async def manage_task(self, **params):
        try:
            # 1. Parse request
            request = self._parse_request(params)
            
            # 2. Call facade
            result = await self.facade.execute(request)
            
            # 3. Format response
            return self.response_formatter.format(result)
        except Exception as e:
            return self.response_formatter.error(e)
```

#### Application Layer (Facades & Use Cases)
```python
# src/fastmcp/task_management/application/facades/task_application_facade.py
class TaskApplicationFacade:
    """
    RESPONSIBILITY:
    - Orchestrate use cases
    - Manage transactions
    - Coordinate between services
    """
    def __init__(self):
        # Get repository from factory based on environment
        self.repo_factory = RepositoryFactory()
        self.cache_manager = CacheManager()
        
    async def create_task(self, request: CreateTaskRequest):
        # 1. Get appropriate repository
        repository = self.repo_factory.get_task_repository()
        
        # 2. Check cache if enabled
        if self.cache_manager.is_enabled:
            cached = await self.cache_manager.get(request.id)
            if cached:
                return cached
        
        # 3. Execute business logic
        use_case = CreateTaskUseCase(repository)
        result = await use_case.execute(request)
        
        # 4. Update cache if enabled
        if self.cache_manager.is_enabled:
            await self.cache_manager.set(result.id, result)
            
        return result
```

### 3. Repository Factory Pattern

```python
# src/fastmcp/task_management/infrastructure/repositories/repository_factory.py
class RepositoryFactory:
    """
    RESPONSIBILITY:
    - Decide which repository implementation to use
    - Based on environment configuration
    """
    
    @staticmethod
    def get_task_repository() -> TaskRepository:
        """
        Returns appropriate repository based on environment
        """
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        
        if env == 'test':
            # Use SQLite for testing
            return SQLiteTaskRepository()
        elif db_type == 'supabase':
            # Use Supabase for production
            return SupabaseTaskRepository()
        else:
            # Default to PostgreSQL
            return PostgreSQLTaskRepository()
    
    @staticmethod
    def get_context_repository() -> ContextRepository:
        """
        Returns context repository with cache support
        """
        base_repo = RepositoryFactory._get_base_context_repository()
        
        if os.getenv('REDIS_ENABLED', 'true').lower() == 'true':
            # Wrap with cache layer
            return CachedContextRepository(base_repo)
        else:
            # Direct database access
            return base_repo
```

### 4. Cache Strategy Pattern

```python
# src/fastmcp/task_management/infrastructure/cache/cache_strategy.py
class CacheStrategy:
    """
    RESPONSIBILITY:
    - Determine when to use cache
    - Handle cache invalidation
    """
    
    def __init__(self):
        self.redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        self.redis_client = self._init_redis() if self.redis_enabled else None
    
    def _init_redis(self):
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0))
            )
            client.ping()
            return client
        except:
            # Fallback to no cache
            return None
    
    async def get_or_fetch(self, key: str, fetch_func):
        """
        Cache-aside pattern
        """
        if self.redis_client:
            # Try cache first
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        
        # Fetch from database
        data = await fetch_func()
        
        # Store in cache if available
        if self.redis_client and data:
            self.redis_client.setex(
                key, 
                300,  # 5 minutes TTL
                json.dumps(data)
            )
        
        return data
    
    def invalidate(self, pattern: str):
        """
        Invalidate cache entries
        """
        if self.redis_client:
            for key in self.redis_client.scan_iter(pattern):
                self.redis_client.delete(key)
```

### 5. Repository Implementations

#### PostgreSQL Repository (Local Development)
```python
# src/fastmcp/task_management/infrastructure/repositories/postgresql/postgresql_task_repository.py
class PostgreSQLTaskRepository(TaskRepository):
    """
    USED FOR: Local development with Docker PostgreSQL
    DATABASE: PostgreSQL container
    """
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/dhafnck_dev')
        self.engine = create_engine(self.database_url)
    
    async def create_task(self, task: Task) -> Task:
        # PostgreSQL implementation with SQLAlchemy
        pass
```

#### Supabase Repository (Production)
```python
# src/fastmcp/task_management/infrastructure/repositories/supabase/supabase_task_repository.py
class SupabaseTaskRepository(TaskRepository):
    """
    USED FOR: Production data persistence
    DATABASE: Supabase (PostgreSQL)
    """
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    async def create_task(self, task: Task) -> Task:
        # Supabase implementation
        result = self.client.table('tasks').insert(task.dict()).execute()
        return Task(**result.data[0])
```

#### Cached Repository Wrapper
```python
# src/fastmcp/task_management/infrastructure/repositories/cached_repository.py
class CachedContextRepository(ContextRepository):
    """
    WRAPPER: Adds caching to any repository
    """
    def __init__(self, base_repository: ContextRepository):
        self.base_repo = base_repository
        self.cache = CacheStrategy()
    
    async def get_context(self, context_id: str) -> Context:
        key = f"context:{context_id}"
        
        return await self.cache.get_or_fetch(
            key,
            lambda: self.base_repo.get_context(context_id)
        )
    
    async def update_context(self, context: Context) -> Context:
        # Update database
        result = await self.base_repo.update_context(context)
        
        # Invalidate cache
        self.cache.invalidate(f"context:{context.id}")
        self.cache.invalidate(f"context:*:inherit:{context.id}")
        
        return result
```

## 🔧 Environment Configuration

```bash
# .env file configuration

# Environment Mode
ENVIRONMENT=production  # 'development' for local PostgreSQL

# Database Configuration
DATABASE_TYPE=supabase  # or 'postgresql' for local development
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
SUPABASE_SERVICE_KEY=xxxxx

# PostgreSQL Configuration (Local Development)
DATABASE_URL=postgresql://user:pass@localhost:5432/dhafnck_dev

# Redis Configuration
REDIS_ENABLED=true  # or 'false' to disable cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## 📊 Decision Flow

```python
def get_repository_strategy():
    """
    Decision tree for repository selection
    """
    if ENVIRONMENT == 'test':
        return SQLiteRepository()  # Always use SQLite for tests
    
    if DATABASE_TYPE == 'supabase':
        repo = SupabaseRepository()
    elif DATABASE_TYPE == 'postgresql':
        repo = PostgreSQLRepository()
    else:
        raise ValueError("Invalid DATABASE_TYPE")
    
    if REDIS_ENABLED:
        return CachedRepository(repo)  # Wrap with cache
    else:
        return repo  # Direct database access
```

## 🚀 Implementation Checklist

### Phase 1: Core Architecture
- [ ] Implement RepositoryFactory with environment detection
- [ ] Create SQLiteRepository for testing
- [ ] Create SupabaseRepository for production
- [ ] Implement CacheStrategy with Redis on/off switch

### Phase 2: Facades & Use Cases
- [ ] Create ApplicationFacade for each domain
- [ ] Implement Use Cases with repository injection
- [ ] Add transaction management
- [ ] Implement error handling

### Phase 3: Cache Layer
- [ ] Implement CachedRepository wrapper
- [ ] Add cache invalidation logic
- [ ] Implement cache warming strategies
- [ ] Add cache metrics

### Phase 4: Testing
- [ ] Unit tests with SQLite
- [ ] Integration tests with Supabase
- [ ] Cache behavior tests
- [ ] Performance benchmarks

## 🎯 Best Practices

### 1. Repository Selection
```python
# ALWAYS use factory
repository = RepositoryFactory.get_task_repository()

# NEVER hardcode
repository = SupabaseTaskRepository()  # ❌ Wrong
```

### 2. Cache Management
```python
# ALWAYS check if cache is enabled
if cache_strategy.is_enabled:
    cache_strategy.invalidate(key)

# NEVER assume cache exists
redis_client.delete(key)  # ❌ Might fail
```

### 3. Error Handling
```python
# ALWAYS handle repository failures
try:
    result = await repository.create(entity)
except RepositoryException as e:
    # Fallback or retry logic
    pass
```

### 4. Transaction Boundaries
```python
# ALWAYS use facades for transactions
async with facade.transaction():
    await facade.create_task(task)
    await facade.update_context(context)
    # Both succeed or both fail
```

## 📝 Agent Instructions Summary

**When implementing features:**

1. **Start with Controller** → Receive MCP request
2. **Call Facade** → Orchestrate business logic
3. **Facade uses Factory** → Get appropriate repository
4. **Check Cache Strategy** → Use Redis if enabled
5. **Execute Repository** → SQLite (test) or Supabase (prod)
6. **Handle Cache Invalidation** → Clear related cache entries
7. **Return Formatted Response** → Standard format

**Environment Detection:**
- Test Mode → SQLite + No Cache
- Production + Redis → Supabase + Redis Cache
- Production - Redis → Supabase Direct

**Never:**
- Hardcode repository implementations
- Assume cache is always available
- Mix layers (controller calling repository directly)
- Forget cache invalidation on updates/deletes

This architecture ensures clean separation, testability, and flexibility for different environments.