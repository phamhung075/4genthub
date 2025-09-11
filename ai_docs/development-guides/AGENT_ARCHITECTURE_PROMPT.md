# 🤖 Agent Architecture Implementation Guide

## Executive Summary for AI Agents

**YOUR MISSION**: Implement features following the correct DDD architecture with proper repository switching (SQLite for tests, Supabase for production), optional Redis caching, and clean separation of concerns.

## 📌 CRITICAL: System Has 61 Architecture Violations - MUST FIX

**Current Status**: 
- **Compliance Score**: 0/100 (Grade F - Critical Failure)
- **Total Violations**: 61 (14 HIGH, 47 MEDIUM)
- **Latest Report**: `compliance_reports/compliance_report_20250828_154945.md`

### ⚠️ MANDATORY: Multi-Agent Workflow for Code Fixes

**BEFORE implementing ANY feature, you MUST**:
1. **Check compliance reports** for current violations
2. **Create tasks** for fixing violations
3. **Assign to specialist agents** (debugger, coding, testing)
4. **IMPLEMENT ACTUAL CODE FIXES** (see Phase 1-4 below)
5. **Verify compliance** after fixes

### Quick Multi-Agent Process:
```python
# 1. Load Compliance Agent and check status
compliance_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@architecture_compliance_agent")

# 2. Create master task
master_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    title="Fix architecture violations",
    description="Fix all 61 violations to achieve DDD compliance"
)

# 3. Load appropriate agent for each violation type
debugger = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")  # For controllers
coding = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")      # For factory
tester = mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")  # For tests
```

## 🔄 Complete Multi-Agent Workflow Pattern

```mermaid
graph TD
    A[User Request] --> B[Orchestrator Agent]
    B --> C{Analyze Compliance}
    C --> D[Architecture Compliance Agent]
    D --> E[Task Planning Agent]
    E --> F[Create Tasks]
    F --> G[Assign to Specialist Agents]
    G --> H[Coding Agent]
    G --> I[Testing Agent]
    G --> J[Debugger Agent]
    H --> K[Update Context]
    I --> K
    J --> K
    K --> L[Complete Task]
    L --> M[Architecture Compliance Check]
    M --> N[Generate Compliance Report]
    N --> O[Update Documentation]
```

## 📋 Complete Multi-Agent Implementation Workflow

### Phase 1: Architecture Analysis and Compliance Check
```python
# Load Architecture Compliance Agent
compliance_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@architecture_compliance_agent")

# Analyze existing architecture
compliance_check = {
    "action": "analyze",
    "check_points": [
        "controller_layer_compliance",  # Controllers only call facades
        "facade_layer_compliance",      # Facades use repository factory
        "repository_factory_exists",    # Factory pattern implemented
        "cache_invalidation_present",   # Cache invalidation on mutations
        "layer_separation_maintained"   # No cross-layer violations
    ],
    "report_path": "compliance_reports/compliance_report_20250828_155335.md"
}

# Current violations: 61 (14 HIGH, 47 MEDIUM)
compliance_result = analyze_architecture_compliance(compliance_check)
```

### Phase 2: Task Creation and Planning
```python
# Load Task Planning Agent
planning_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@task_planning_agent")

# Create master task for the feature
master_task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Fix 61 architecture violations for DDD compliance",
    description="Fix controllers, factories, facades, and cache",
    priority="critical"
)

# Create context for visibility
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=master_task["task"]["id"],
    git_branch_id=branch_id,
    data={
        "total_violations": 61,
        "controller_violations": 14,
        "factory_violations": 7,
        "facade_violations": 25,
        "cache_violations": 25
    }
)

# Break down into subtasks
subtasks = [
    {"title": "Fix 11 Controller Files", "agent": "@debugger_agent"},
    {"title": "Fix 7 Repository Factories", "agent": "@coding_agent"},
    {"title": "Fix 25 Facades", "agent": "@coding_agent"},
    {"title": "Add Cache to 25 Methods", "agent": "@coding_agent"},
    {"title": "Write Compliance Tests", "agent": "@test_orchestrator_agent"}
]

for subtask in subtasks:
    mcp__dhafnck_mcp_http__manage_subtask(
        action="create",
        task_id=master_task["task"]["id"],
        title=subtask["title"],
        assigned_agent=subtask["agent"]
    )
```

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                  MCP Request Entry                   │
└────────────────────┬─────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│         INTERFACE LAYER (Controllers)                │
│  • Receive MCP requests                              │
│  • Validate input parameters                         │
│  • Format responses                                  │
└────────────────────┬─────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│      APPLICATION LAYER (Facades & Use Cases)         │
│  • Orchestrate business logic                        │
│  • Manage transactions                               │
│  • Coordinate between services                       │
└────────────────────┬─────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│         DOMAIN LAYER (Entities & Services)           │
│  • Business rules and logic                          │
│  • Domain entities and value objects                 │
│  • Repository interfaces (abstractions)              │
└────────────────────┬─────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│     INFRASTRUCTURE LAYER (Implementations)           │
│                                                      │
│  ┌─────────────────────────────────────────┐         │
│  │         Repository Factory               │        │
│  │  Decides which implementation to use     │        │
│  └──────────────┬──────────────────────────┘         │
│                 ↓                                    │
│  ┌──────────────────────────────────────────┐        │
│  │     Environment Detection                │        │
│  └──────┬───────────────────┬───────────────┘        │
│         ↓                   ↓                        │
│    TEST MODE           PRODUCTION MODE               │
│         ↓                   ↓                        │
│  ┌──────────────┐   ┌──────────────┐                 │
│  │   SQLite     │   │   Supabase   │                 │
│  │  Repository  │   │  Repository  │                 │
│  └──────────────┘   └───────┬──────┘                 │
│                             ↓                        │
│                    ┌─────────────────┐               │
│                    │ Cache Enabled?  │               │
│                    └────┬──────┬─────┘               │
│                        YES     NO                    │
│                         ↓       ↓                    │
│                  ┌─────────┐  ┌──────────┐           │
│                  │  Redis  │  │  Direct  │           │
│                  │  Cache  │  │ Database │           │
│                  └─────────┘  └──────────┘           │
└──────────────────────────────────────────────────────┘
```

## 📋 Step-by-Step Implementation Guide

### Step 1: Understand the Request Flow

```python
# REQUEST FLOW PATTERN:
MCP Request → Controller → Facade → Use Case → Repository Factory → Repository → Cache/Database

# NEVER DO THIS:
MCP Request → Repository  # ❌ Skipping layers
Controller → Database     # ❌ Direct database access
```

### Step 2: Controller Implementation (Interface Layer)

```python
# src/fastmcp/task_management/interface/controllers/task_mcp_controller.py

class TaskMCPController:
    """
    RESPONSIBILITIES:
    - Receive and parse MCP requests
    - Validate input parameters
    - Call appropriate facade methods
    - Format responses in MCP format
    - Handle errors gracefully
    """
    
    def __init__(self):
        # Controllers ONLY talk to facades, never to repositories directly
        self.facade = TaskApplicationFacade()
        self.response_formatter = StandardResponseFormatter()
    
    async def manage_task(self, **params):
        """Handle MCP task management request"""
        try:
            # 1. Parse and validate request
            request = self._parse_request(params)
            
            # 2. Delegate to facade (business logic)
            result = await self.facade.execute(request)
            
            # 3. Format response for MCP
            return self.response_formatter.format_success(result)
            
        except ValidationException as e:
            return self.response_formatter.format_error(e)
```

### Step 3: Facade Implementation (Application Layer)

```python
# src/fastmcp/task_management/application/facades/task_application_facade.py

class TaskApplicationFacade:
    """
    RESPONSIBILITIES:
    - Orchestrate use cases
    - Manage transactions
    - Coordinate between multiple services
    - Use repository factory to get appropriate repository
    """
    
    def __init__(self):
        # Facades use factory to get repositories
        self.repo_factory = RepositoryFactory()
        self.cache_manager = CacheManager()
        
    async def create_task(self, request: CreateTaskRequest):
        """Create a new task with proper repository and caching"""
        
        # 1. Get appropriate repository based on environment
        repository = self.repo_factory.get_task_repository()
        
        # 2. Check cache if enabled
        if self.cache_manager.is_enabled:
            cached = await self.cache_manager.get(f"task:{request.id}")
            if cached:
                return cached
        
        # 3. Execute business logic via use case
        use_case = CreateTaskUseCase(repository)
        result = await use_case.execute(request)
        
        # 4. Update cache if enabled
        if self.cache_manager.is_enabled:
            await self.cache_manager.set(f"task:{result.id}", result, ttl=300)
            
        return result
```

### Step 4: Repository Factory Pattern (Critical!)

```python
# src/fastmcp/task_management/infrastructure/repositories/repository_factory.py

import os
from typing import Optional

class RepositoryFactory:
    """
    CRITICAL COMPONENT: Decides which repository implementation to use
    based on environment configuration.
    
    Decision Logic:
    - TEST MODE (ENVIRONMENT=test) → SQLite Repository
    - PRODUCTION MODE (DATABASE_TYPE=supabase) → Supabase Repository
    - CACHE ENABLED (REDIS_ENABLED=true) → Wrap with Redis Cache
    """
    
    @staticmethod
    def get_task_repository() -> TaskRepository:
        """
        Returns appropriate repository based on environment.
        This is the ONLY place where repository selection happens!
        """
        # 1. Check environment mode
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        
        # 2. Select base repository
        if env == 'test':
            # ALWAYS use SQLite for testing
            base_repo = SQLiteTaskRepository()
        elif db_type == 'supabase':
            # Production uses Supabase
            base_repo = SupabaseTaskRepository()
        elif db_type == 'postgresql':
            # Alternative production database
            base_repo = PostgreSQLTaskRepository()
        else:
            raise ValueError(f"Unknown DATABASE_TYPE: {db_type}")
        
        # 3. Check if Redis caching should be enabled
        redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        if redis_enabled and env != 'test':  # Never cache in test mode
            # Wrap repository with cache layer
            return CachedTaskRepository(base_repo)
        else:
            # Direct database access without cache
            return base_repo
    
    @staticmethod
    def get_context_repository() -> ContextRepository:
        """Similar pattern for context repositories"""
        base_repo = RepositoryFactory._get_base_context_repository()
        
        if os.getenv('REDIS_ENABLED', 'true').lower() == 'true':
            return CachedContextRepository(base_repo)
        else:
            return base_repo
```

### Step 5: Repository Implementations

#### SQLite Repository (Testing Only)

```python
# src/fastmcp/task_management/infrastructure/repositories/sqlite/sqlite_task_repository.py

class SQLiteTaskRepository(BaseORMRepository, TaskRepository):
    """
    PURPOSE: Used ONLY for testing
    DATABASE: Local SQLite file
    FEATURES: Fast, isolated, no external dependencies
    """
    
    def __init__(self):
        # PostgreSQL uses connection URL
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/dhafnck_dev')
        super().__init__(TaskModel)
    
    def create_task(self, task: Task) -> Task:
        """Create task in PostgreSQL database"""
        with self.get_db_session() as session:
            db_model = TaskModel(**task.to_dict())
            session.add(db_model)
            session.commit()
            return Task.from_model(db_model)
```

#### Supabase Repository (Production)

```python
# src/fastmcp/task_management/infrastructure/repositories/supabase/supabase_task_repository.py

class SupabaseTaskRepository(BaseORMRepository, TaskRepository):
    """
    PURPOSE: Production data persistence
    DATABASE: Supabase (PostgreSQL in cloud)
    FEATURES: Scalable, reliable, cloud-hosted
    """
    
    def __init__(self):
        # Supabase uses cloud PostgreSQL
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.client = create_client(self.supabase_url, self.supabase_key)
        super().__init__(TaskModel)
    
    def create_task(self, task: Task) -> Task:
        """Create task in Supabase"""
        result = self.client.table('tasks').insert(task.to_dict()).execute()
        return Task.from_dict(result.data[0])
```

#### Cached Repository Wrapper

```python
# src/fastmcp/task_management/infrastructure/repositories/cached_repository.py

class CachedTaskRepository(TaskRepository):
    """
    PURPOSE: Add caching layer to any repository
    CACHE: Redis (when enabled)
    PATTERN: Cache-aside with write-through invalidation
    """
    
    def __init__(self, base_repository: TaskRepository):
        self.base_repo = base_repository
        self.cache = CacheStrategy()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task with cache-aside pattern"""
        
        # 1. Try cache first
        cache_key = f"task:{task_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return Task.from_dict(cached)
        
        # 2. Fetch from database
        task = self.base_repo.get_task(task_id)
        
        # 3. Update cache if found
        if task and self.cache.is_enabled:
            self.cache.set(cache_key, task.to_dict(), ttl=300)
        
        return task
    
    def update_task(self, task: Task) -> Task:
        """Update task with cache invalidation"""
        
        # 1. Update in database
        result = self.base_repo.update_task(task)
        
        # 2. Invalidate cache entries
        self.cache.invalidate(f"task:{task.id}")
        self.cache.invalidate(f"task:list:*")  # Invalidate list caches
        
        return result
```

### Step 6: Cache Strategy Implementation

```python
# src/fastmcp/task_management/infrastructure/cache/cache_strategy.py

class CacheStrategy:
    """
    PURPOSE: Intelligent caching with Redis
    FEATURES:
    - Automatic enable/disable based on environment
    - Graceful fallback if Redis unavailable
    - TTL management
    - Pattern-based invalidation
    """
    
    def __init__(self):
        self.redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        self.redis_client = self._init_redis() if self.redis_enabled else None
    
    def _init_redis(self):
        """Initialize Redis with fallback"""
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD'),
                db=int(os.getenv('REDIS_DB', 0))
            )
            # Test connection
            client.ping()
            return client
        except Exception as e:
            print(f"Redis not available: {e}")
            # Graceful fallback - system works without cache
            return None
    
    @property
    def is_enabled(self) -> bool:
        """Check if caching is actually available"""
        return self.redis_client is not None
    
    def get(self, key: str) -> Optional[dict]:
        """Get from cache if available"""
        if not self.is_enabled:
            return None
        
        try:
            cached = self.redis_client.get(key)
            return json.loads(cached) if cached else None
        except:
            return None  # Fail silently
    
    def set(self, key: str, value: dict, ttl: int = 300):
        """Set cache with TTL if available"""
        if not self.is_enabled:
            return
        
        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
        except:
            pass  # Fail silently
    
    def invalidate(self, pattern: str):
        """Invalidate cache entries by pattern"""
        if not self.is_enabled:
            return
        
        try:
            for key in self.redis_client.scan_iter(pattern):
                self.redis_client.delete(key)
        except:
            pass  # Fail silently
```

## 🔧 Environment Configuration

```bash
# .env file - Controls entire system behavior

# ENVIRONMENT MODE (determines repository selection)
ENVIRONMENT=production  # Options: 'production', 'test'

# DATABASE TYPE (for production mode)
DATABASE_TYPE=supabase  # Options: 'supabase', 'postgresql', 'sqlite'

# SUPABASE CONFIGURATION (production database)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
SUPABASE_SERVICE_KEY=xxxxx

# REDIS CACHE CONFIGURATION
REDIS_ENABLED=true     # Set to 'false' to disable caching completely
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=dev_redis_password_123
REDIS_DB=0

# PostgreSQL CONFIGURATION (local development)
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/dhafnck_mcp_dev
```

## 🎯 Decision Tree for Agents

```python
def determine_repository_configuration():
    """
    Decision logic for repository and cache configuration
    """
    
    # 1. Check database type
    if DATABASE_TYPE == 'supabase':
        # Production: Supabase managed PostgreSQL
        repository = SupabaseRepository()
    elif DATABASE_TYPE == 'postgresql':
        # Local development: PostgreSQL Docker
        repository = PostgreSQLRepository()
    else:
        raise ConfigurationError(f"Invalid DATABASE_TYPE: {DATABASE_TYPE}. Use 'postgresql' or 'supabase'.")
    
    # 2. Check environment for cache configuration
    if ENVIRONMENT == 'test':
        cache = None  # No caching in tests
    else:
    
    # 3. Check if caching should be enabled
    if REDIS_ENABLED == 'true':
        # Try to connect to Redis
        if redis_connection_successful():
            repository = CachedRepository(repository)
        else:
            # Redis not available, continue without cache
            print("Warning: Redis not available, running without cache")
    
    return repository
```

## ⚠️ Critical Rules for Agents

### NEVER DO:
1. **Hardcode repository implementations**
   ```python
   # ❌ WRONG - Never do this
   repository = SupabaseTaskRepository()
   
   # ✅ CORRECT - Always use factory
   repository = RepositoryFactory.get_task_repository()
   ```

2. **Assume cache is always available**
   ```python
   # ❌ WRONG - Will crash if Redis is down
   redis_client.set(key, value)
   
   # ✅ CORRECT - Check if cache is enabled
   if cache_strategy.is_enabled:
       cache_strategy.set(key, value)
   ```

3. **Mix architectural layers**
   ```python
   # ❌ WRONG - Controller directly accessing repository
   class Controller:
       def handle(self):
           repo = TaskRepository()  # Direct repository access
   
   # ✅ CORRECT - Controller uses facade
   class Controller:
       def handle(self):
           self.facade.execute()  # Delegate to facade
   ```

4. **Forget cache invalidation**
   ```python
   # ❌ WRONG - Update without invalidating cache
   def update_task(self, task):
       self.db.update(task)
   
   # ✅ CORRECT - Always invalidate after updates
   def update_task(self, task):
       self.db.update(task)
       self.cache.invalidate(f"task:{task.id}")
   ```

### ALWAYS DO:
1. **Follow the layer hierarchy**
   - Controller → Facade → Use Case → Repository Factory → Repository

2. **Use environment variables for configuration**
   - Never hardcode database connections or cache settings

3. **Handle cache failures gracefully**
   - System must work even if Redis is unavailable

4. **Invalidate cache on data changes**
   - CREATE, UPDATE, DELETE must invalidate relevant cache entries

5. **Use factory pattern for repository selection**
   - Let RepositoryFactory decide which implementation to use

## 📊 Implementation Checklist

When implementing a new feature, follow this checklist:

- [ ] Create Controller in `/interface/controllers/`
- [ ] Create Facade in `/application/facades/`
- [ ] Create Use Case in `/application/use_cases/`
- [ ] Define Repository Interface in `/domain/repositories/`
- [ ] Implement SQLite Repository in `/infrastructure/repositories/sqlite/`
- [ ] Implement Supabase Repository in `/infrastructure/repositories/supabase/`
- [ ] Add to RepositoryFactory in `/infrastructure/repositories/repository_factory.py`
- [ ] Implement Cache Strategy in `/infrastructure/cache/`
- [ ] Add Cache Invalidation logic
- [ ] Configure environment variables
- [ ] Write tests using SQLite repository
- [ ] Test production with Supabase
- [ ] Test with Redis enabled and disabled

## 🚀 Quick Implementation Example

Here's a complete example of implementing a new "Project" feature:

```python
# 1. Controller (interface layer)
# src/fastmcp/task_management/interface/controllers/project_mcp_controller.py
class ProjectMCPController:
    def __init__(self):
        self.facade = ProjectApplicationFacade()
    
    def manage_project(self, action: str, **params):
        if action == "create":
            return self.facade.create_project(params)

# 2. Facade (application layer)
# src/fastmcp/task_management/application/facades/project_application_facade.py
class ProjectApplicationFacade:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def create_project(self, request):
        repository = self.repo_factory.get_project_repository()
        use_case = CreateProjectUseCase(repository)
        return use_case.execute(request)

# 3. Repository Factory
# src/fastmcp/task_management/infrastructure/repositories/repository_factory.py
class RepositoryFactory:
    @staticmethod
    def get_project_repository():
        env = os.getenv('ENVIRONMENT', 'production')
        
        if env == 'test':
            base_repo = SQLiteProjectRepository()
        else:
            base_repo = SupabaseProjectRepository()
        
        if os.getenv('REDIS_ENABLED', 'true') == 'true':
            return CachedProjectRepository(base_repo)
        return base_repo

# 4. SQLite Repository (testing)
# src/fastmcp/task_management/infrastructure/repositories/sqlite/sqlite_project_repository.py
class SQLiteProjectRepository(ProjectRepository):
    def create_project(self, project):
        # SQLite implementation
        pass

# 5. Supabase Repository (production)
# src/fastmcp/task_management/infrastructure/repositories/supabase/supabase_project_repository.py
class SupabaseProjectRepository(ProjectRepository):
    def create_project(self, project):
        # Supabase implementation
        pass

# 6. Cached Repository Wrapper
# src/fastmcp/task_management/infrastructure/repositories/cached_project_repository.py
class CachedProjectRepository(ProjectRepository):
    def __init__(self, base_repo):
        self.base_repo = base_repo
        self.cache = CacheStrategy()
    
    def create_project(self, project):
        result = self.base_repo.create_project(project)
        self.cache.invalidate("projects:*")
        return result
```

## 📈 Performance Considerations

### With Redis Enabled (REDIS_ENABLED=true)
- **Read Performance**: ~1-5ms (cache hit), ~50-100ms (cache miss)
- **Write Performance**: ~50-100ms + cache invalidation overhead
- **Memory Usage**: Higher due to Redis cache
- **Best For**: High read/write ratio applications

### Without Redis (REDIS_ENABLED=false)
- **Read Performance**: ~50-100ms (direct database)
- **Write Performance**: ~50-100ms (no cache overhead)
- **Memory Usage**: Lower, no cache storage
- **Best For**: Low traffic or write-heavy applications

### Test Mode (ENVIRONMENT=test)
- **Database**: SQLite (local file)
- **Cache**: Always disabled
- **Performance**: Fast for testing
- **Isolation**: Complete test isolation

## 🔍 Debugging Guide

### How to verify correct repository is being used:

```python
# Add logging to RepositoryFactory
import logging
logger = logging.getLogger(__name__)

class RepositoryFactory:
    @staticmethod
    def get_task_repository():
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        redis_enabled = os.getenv('REDIS_ENABLED', 'true')
        
        logger.info(f"Repository selection: ENV={env}, DB={db_type}, REDIS={redis_enabled}")
        
        # ... repository selection logic ...
        
        logger.info(f"Selected repository: {repository.__class__.__name__}")
        return repository
```

### Common Issues and Solutions:

1. **Cache not invalidating**
   - Check REDIS_ENABLED environment variable
   - Verify Redis connection is successful
   - Ensure invalidation code is not commented out

2. **Wrong database being used**
   - Check ENVIRONMENT variable
   - Verify DATABASE_TYPE is set correctly
   - Check RepositoryFactory logic

3. **Tests using production database**
   - Ensure ENVIRONMENT=test for test runs
   - Check test configuration files

## 🔧 ACTUAL CODE FIXES REQUIRED - PHASE 1-4

### PHASE 1: Fix Controller Violations (11 files, 14 HIGH violations)

**File: `git_branch_mcp_controller.py` (Lines 491, 579, 612)**
```python
# ❌ REMOVE THIS (Current violation):
from infrastructure.repositories.orm import GitBranchRepository
from infrastructure.repositories.orm import ProjectRepository
self.repository = GitBranchRepository()

# ✅ REPLACE WITH THIS:
from application.facades import GitBranchApplicationFacade
self.facade = GitBranchApplicationFacade()
# Then use: self.facade.execute(request) instead of repository calls
```

**File: `task_mcp_controller.py` (Lines 1550, 1578)**
```python
# ❌ REMOVE THIS:
from infrastructure.database import SessionLocal
session = SessionLocal()

# ✅ REPLACE WITH THIS:
from application.facades import TaskApplicationFacade
self.facade = TaskApplicationFacade()
# Use facade methods, not direct database
```

### PHASE 2: Implement Working Repository Factory

**CREATE NEW: `infrastructure/repositories/repository_factory.py`**
```python
import os
from typing import Optional

class RepositoryFactory:
    """WORKING factory that actually checks environment variables"""
    
    @staticmethod
    def get_task_repository():
        # THIS IS WHAT'S MISSING - Environment checking!
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        # Select repository based on environment
        if env == 'test':
            from .sqlite import SQLiteTaskRepository
            base_repo = SQLiteTaskRepository()
        elif db_type == 'supabase':
            from .supabase import SupabaseTaskRepository
            base_repo = SupabaseTaskRepository()
        else:
            from .postgresql import PostgreSQLTaskRepository
            base_repo = PostgreSQLTaskRepository()
        
        # Wrap with cache if enabled
        if redis_enabled and env != 'test':
            from .cached import CachedTaskRepository
            return CachedTaskRepository(base_repo)
        
        return base_repo
```

**FIX EXISTING: All 7 broken factory files**
```python
# ❌ CURRENT (ALL 7 factories have this problem):
def create():
    return TaskRepository()  # Always returns same thing!

# ✅ FIX TO:
def create():
    return RepositoryFactory.get_task_repository()  # Use central factory
```

### PHASE 3: Update Facades to Use Factory (25 files)

**File: `task_application_facade.py` (Line 82)**
```python
# ❌ REMOVE:
self.repository = MockTaskContextRepository()  # Hardcoded

# ✅ REPLACE:
from infrastructure.repositories import RepositoryFactory
self.repository = RepositoryFactory.get_task_repository()
```

### PHASE 4: Add Cache Invalidation (25 methods)

**ADD to all mutation methods:**
```python
def create_task(self, task):
    result = self.base_repo.create_task(task)
    # ADD THIS:
    if self.cache:
        self.cache.invalidate(f"tasks:list:*")
        self.cache.invalidate(f"tasks:branch:{task.branch_id}")
    return result

def update_task(self, task):
    result = self.base_repo.update_task(task)
    # ADD THIS:
    if self.cache:
        self.cache.invalidate(f"task:{task.id}")
        self.cache.invalidate("tasks:list:*")
    return result

def delete_task(self, task_id):
    result = self.base_repo.delete_task(task_id)
    # ADD THIS:
    if self.cache:
        self.cache.invalidate(f"task:{task_id}")
        self.cache.invalidate("tasks:*")
    return result
```

## 🎓 Summary for AI Agents

**Remember these key points:**

1. **Architecture Flow**: Controller → Facade → Use Case → Repository Factory → Repository → Database/Cache
2. **Repository Selection**: Factory pattern decides based on environment
3. **Cache Management**: Optional Redis layer with graceful fallback
4. **Test Isolation**: SQLite for tests, Supabase for production
5. **Cache Invalidation**: MUST invalidate on CREATE, UPDATE, DELETE

**Your implementation should:**
- ✅ Use RepositoryFactory for all repository creation
- ✅ Check cache availability before using
- ✅ Invalidate cache after data changes
- ✅ Follow the architectural layers strictly
- ✅ Handle cache failures gracefully

**Never:**
- ❌ Hardcode repository implementations
- ❌ Skip architectural layers
- ❌ Assume cache is always available
- ❌ Forget cache invalidation
- ❌ Mix test and production databases

## 🚨 MANDATORY: Architecture Compliance Verification

### Current Compliance Status (V5 Analysis - 61 Violations)
- **Score**: 0/100 (Critical Failure)
- **Controller violations**: 11 files (14 HIGH)
- **Factory broken**: 7 factories don't check environment
- **Facade violations**: 25 files don't use factory
- **Cache missing**: 25 methods lack invalidation

### Required Actions BEFORE ANY New Feature:
1. **Fix controllers** - Remove all direct DB/repository access
2. **Fix factories** - Add environment checking logic
3. **Fix facades** - Use RepositoryFactory not hardcoded repos
4. **Add cache invalidation** - On all create/update/delete

### Multi-Agent Execution Order:
```python
# Step 1: Analyze current violations
compliance = mcp__dhafnck_mcp_http__call_agent(name_agent="@architecture_compliance_agent")
# Check compliance_reports/compliance_report_20250828_154945.md

# Step 2: Fix controllers (14 HIGH violations)
debugger = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
# Fix all 11 controller files using Phase 1 code above

# Step 3: Implement factory (7 broken factories)
coding = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
# Create central RepositoryFactory with environment checking
# Update all 7 existing factories to use it

# Step 4: Update facades (25 violations)
# Replace hardcoded repositories with factory calls

# Step 5: Add cache invalidation (25 methods)
# Add invalidation to all mutation methods

# Step 6: Test compliance
tester = mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
# Run architecture compliance tests

# Step 7: Verify score improved
# Target: 100/100 compliance score
```

### Compliance Test Script:
```python
# tests/test_architecture_compliance.py
def test_no_direct_db_in_controllers():
    """Controllers must not import database or repositories"""
    for controller in Path('interface/controllers').glob('*.py'):
        content = controller.read_text()
        assert 'from infrastructure.database' not in content
        assert 'from infrastructure.repositories' not in content
        assert 'SessionLocal()' not in content

def test_facades_use_factory():
    """All facades must use RepositoryFactory"""
    for facade in Path('application/facades').glob('*.py'):
        content = facade.read_text()
        if 'Repository()' in content:
            assert 'RepositoryFactory' in content

def test_factory_checks_environment():
    """Factory must check ENVIRONMENT variable"""
    factory = Path('infrastructure/repositories/repository_factory.py')
    content = factory.read_text()
    assert "os.getenv('ENVIRONMENT'" in content
    assert "os.getenv('DATABASE_TYPE'" in content
    assert "os.getenv('REDIS_ENABLED'" in content

def test_cache_invalidation_exists():
    """All mutation methods must invalidate cache"""
    for repo in Path('infrastructure/repositories').rglob('*repository.py'):
        content = repo.read_text()
        if 'def create' in content:
            assert 'invalidate' in content
        if 'def update' in content:
            assert 'invalidate' in content
        if 'def delete' in content:
            assert 'invalidate' in content
```

### Success Criteria:
- ✅ 0 controller violations (currently 14)
- ✅ All 7 factories check environment (currently 0)
- ✅ All 25 facades use factory (currently 0)
- ✅ All 25 mutation methods invalidate cache (currently 0)
- ✅ Compliance score: 100/100 (currently 0/100)

## 🤖 Multi-Agent Execution Checklist

### Pre-Implementation (Analysis Phase)
```python
# 1. Check current compliance status
compliance = mcp__dhafnck_mcp_http__call_agent(name_agent="@architecture_compliance_agent")
# Review: compliance_reports/compliance_report_20250828_155335.md

# 2. Create master task
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    title="Fix 61 architecture violations",
    priority="critical"
)

# 3. Create context for tracking
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task["id"],
    data={"violations": 61, "target_score": 100}
)
```

### Implementation Phase (Code Fixes)
```python
# Phase 1: Fix Controllers (14 HIGH violations)
debugger = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
# Apply controller fixes from Phase 1 section above

# Phase 2: Fix Factories (7 broken factories)  
coding = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
# Implement RepositoryFactory with environment checking

# Phase 3: Fix Facades (25 violations)
# Update all facades to use RepositoryFactory

# Phase 4: Add Cache (25 methods)
# Add invalidation to all mutation methods

# Phase 5: Test Compliance
tester = mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
# Run compliance tests
```

### Post-Implementation (Verification)
```python
# 1. Run compliance check
final_check = analyze_architecture_compliance()

# 2. Verify score improved
assert final_check["score"] == 100

# 3. Update context with results
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    data={
        "compliance_fixed": True,
        "final_score": 100,
        "violations_remaining": 0
    }
)

# 4. Complete task
mcp__dhafnck_mcp_http__complete_task_with_update(
    task_id=task["id"],
    completion_summary="Fixed all 61 violations, compliance score now 100/100"
)
```

## 🚀 Automated Compliance Check Script

Save this as `scripts/check_and_fix_compliance.py`:

```python
#!/usr/bin/env python
"""
Automated architecture compliance checker and fixer
Run this to check violations and apply fixes
"""

import os
import sys
from pathlib import Path

class ComplianceChecker:
    def __init__(self):
        self.violations = []
        self.score = 0
        
    def check_controllers(self):
        """Check for controller violations"""
        controller_path = Path('src/fastmcp/task_management/interface/controllers')
        for file in controller_path.glob('*.py'):
            content = file.read_text()
            if 'from infrastructure.database' in content:
                self.violations.append(f"Controller {file.name}: Direct DB import")
            if 'from infrastructure.repositories' in content:
                self.violations.append(f"Controller {file.name}: Direct repo import")
            if 'SessionLocal()' in content:
                self.violations.append(f"Controller {file.name}: Creates DB session")
    
    def check_factories(self):
        """Check if factories use environment variables"""
        factory_path = Path('src/fastmcp/task_management/infrastructure/repositories')
        for file in factory_path.glob('*factory.py'):
            content = file.read_text()
            checks_needed = [
                "os.getenv('ENVIRONMENT'",
                "os.getenv('DATABASE_TYPE'",
                "os.getenv('REDIS_ENABLED'"
            ]
            for check in checks_needed:
                if check not in content:
                    self.violations.append(f"Factory {file.name}: Missing {check}")
    
    def check_facades(self):
        """Check if facades use repository factory"""
        facade_path = Path('src/fastmcp/task_management/application/facades')
        for file in facade_path.glob('*.py'):
            content = file.read_text()
            if 'Repository()' in content and 'RepositoryFactory' not in content:
                self.violations.append(f"Facade {file.name}: Not using factory")
    
    def check_cache_invalidation(self):
        """Check for cache invalidation in mutations"""
        repo_path = Path('src/fastmcp/task_management/infrastructure/repositories')
        for file in repo_path.rglob('*repository.py'):
            content = file.read_text()
            mutations = ['def create', 'def update', 'def delete']
            for mutation in mutations:
                if mutation in content and 'invalidate' not in content:
                    self.violations.append(f"Repo {file.name}: No cache invalidation in {mutation}")
    
    def calculate_score(self):
        """Calculate compliance score"""
        if not self.violations:
            self.score = 100
        else:
            # Deduct points based on violations
            self.score = max(0, 100 - (len(self.violations) * 2))
    
    def run_check(self):
        """Run all compliance checks"""
        print("🔍 Running Architecture Compliance Check...")
        
        self.check_controllers()
        self.check_factories()
        self.check_facades()
        self.check_cache_invalidation()
        self.calculate_score()
        
        print(f"\n📊 Compliance Score: {self.score}/100")
        print(f"Total Violations: {len(self.violations)}")
        
        if self.violations:
            print("\n❌ Violations Found:")
            for i, violation in enumerate(self.violations, 1):
                print(f"  {i}. {violation}")
            print("\n⚠️ Run fixes using the code provided in AGENT_ARCHITECTURE_PROMPT.md")
        else:
            print("\n✅ All compliance checks passed!")
        
        return self.score == 100

if __name__ == "__main__":
    checker = ComplianceChecker()
    success = checker.run_check()
    sys.exit(0 if success else 1)
```

## 📊 Implementation Tracking Dashboard

| Phase | Task | Current Status | Target | Agent |
|-------|------|----------------|---------|-------|
| 1 | Fix Controllers | 14 violations | 0 | @debugger_agent |
| 2 | Fix Factories | 7 broken | 7 working | @coding_agent |
| 3 | Fix Facades | 25 violations | 0 | @coding_agent |
| 4 | Add Cache | 25 missing | 25 added | @coding_agent |
| 5 | Test Compliance | 0/100 score | 100/100 | @test_orchestrator_agent |

This architecture ensures clean separation, testability, flexibility, and performance optimization while maintaining simplicity and reliability.