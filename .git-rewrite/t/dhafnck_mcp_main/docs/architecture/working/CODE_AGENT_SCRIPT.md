# 💻 CODE AGENT SCRIPT - Implementation & Fixes

## Executive Summary for Code Agent

**YOUR MISSION**: Get tasks from planner agent and implement actual code fixes for architecture violations based on workplace.md.

## 🔄 Code Agent Workflow 

### Phase 1: Load Code Agent & Get Tasks

```python
# Load Coding Agent
code_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# Check for available tasks
available_tasks = mcp__dhafnck_mcp_http__manage_task(
    action="next",
    git_branch_id=branch_id,
    assigned_agent="@coding_agent",
    include_context=True
)

# If no tasks available, wait 5 minutes
if not available_tasks:
    print("⏱️ No coding tasks available. Waiting 5 minutes...")
    import time
    time.sleep(300)  # 5 minutes = 300 seconds
    available_tasks = mcp__dhafnck_mcp_http__manage_task(
        action="next",
        git_branch_id=branch_id,
        assigned_agent="@coding_agent"
    )
```

### Phase 2: Process Tasks by Priority

#### Priority 1: Fix Controller Violations (16 files)

```python
if available_tasks["task"]["title"].contains("Controller Violations"):
    # Mark task as in progress
    mcp__dhafnck_mcp_http__manage_task(
        action="update",
        task_id=available_tasks["task_id"],
        status="in_progress",
        details="Starting controller violation fixes"
    )
    
    # Fix each controller file
    controller_fixes = [
        {
            "file": "src/fastmcp/task_management/interface/controllers/git_branch_mcp_controller.py",
            "violations": ["lines 491, 579, 612"],
            "fix": {
                "remove": [
                    "from infrastructure.repositories.orm import GitBranchRepository",
                    "from infrastructure.repositories.orm import ProjectRepository",
                    "self.repository = GitBranchRepository()"
                ],
                "add": [
                    "from application.facades import GitBranchApplicationFacade",
                    "self.facade = GitBranchApplicationFacade()"
                ]
            }
        },
        {
            "file": "src/fastmcp/task_management/interface/controllers/task_mcp_controller.py", 
            "violations": ["lines 1550, 1578"],
            "fix": {
                "remove": [
                    "from infrastructure.database import SessionLocal",
                    "session = SessionLocal()"
                ],
                "add": [
                    "from application.facades import TaskApplicationFacade",
                    "self.facade = TaskApplicationFacade()"
                ]
            }
        },
        {
            "file": "src/fastmcp/task_management/interface/controllers/context_id_detector_orm.py",
            "violations": ["lines 9-10"],
            "fix": {
                "remove": [
                    "from infrastructure.database import SessionLocal",
                    "# All direct database code"
                ],
                "add": [
                    "from application.facades import ContextApplicationFacade",
                    "self.facade = ContextApplicationFacade()"
                ]
            }
        },
        {
            "file": "src/fastmcp/task_management/interface/controllers/subtask_mcp_controller.py",
            "violations": ["direct DB access"],
            "fix": {
                "remove": ["Direct database session creation"],
                "add": [
                    "from application.facades import SubtaskApplicationFacade",
                    "self.facade = SubtaskApplicationFacade()"
                ]
            }
        }
        # ... Continue for all 16 controller files
    ]
    
    for fix in controller_fixes:
        # Apply the fix using MultiEdit
        MultiEdit(
            file_path=fix["file"],
            edits=[
                {
                    "old_string": remove_line,
                    "new_string": ""
                } for remove_line in fix["fix"]["remove"]
            ] + [
                {
                    "old_string": "",
                    "new_string": add_line
                } for add_line in fix["fix"]["add"]
            ]
        )
        
        print(f"✅ Fixed controller: {fix['file']}")
    
    # Complete the controller task
    mcp__dhafnck_mcp_http__complete_task_with_update(
        task_id=available_tasks["task_id"],
        completion_summary="Fixed all 16 controller violations - removed direct DB/repo access",
        implementation_details="Replaced repository imports with facade imports in all controllers",
        files_modified=len(controller_fixes)
    )
```

#### Priority 1: Fix Repository Factory Pattern (27 files)

```python
elif available_tasks["task"]["title"].contains("Repository Factories"):
    # Create central working factory
    central_factory_code = '''
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
        
        print(f"[RepositoryFactory] ENV={env}, DB={db_type}, REDIS={redis_enabled}")
        
        # Select repository based on environment
        if env == 'test':
            from .sqlite import SQLiteTaskRepository
            base_repo = SQLiteTaskRepository()
        elif db_type == 'supabase':
            from .supabase import SupabaseTaskRepository
            base_repo = SupabaseTaskRepository()
        elif db_type == 'postgresql':
            from .postgresql import PostgreSQLTaskRepository
            base_repo = PostgreSQLTaskRepository()
        else:
            raise ValueError(f"Unknown DATABASE_TYPE: {db_type}")
        
        # Wrap with cache if enabled
        if redis_enabled and env != 'test':
            from .cached import CachedTaskRepository
            return CachedTaskRepository(base_repo)
        else:
            return base_repo
    
    @staticmethod
    def get_project_repository():
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        if env == 'test':
            from .sqlite import SQLiteProjectRepository
            base_repo = SQLiteProjectRepository()
        elif db_type == 'supabase':
            from .supabase import SupabaseProjectRepository
            base_repo = SupabaseProjectRepository()
        else:
            from .postgresql import PostgreSQLProjectRepository
            base_repo = PostgreSQLProjectRepository()
        
        if redis_enabled and env != 'test':
            from .cached import CachedProjectRepository
            return CachedProjectRepository(base_repo)
        return base_repo
    
    @staticmethod
    def get_context_repository():
        # Similar implementation for context
        env = os.getenv('ENVIRONMENT', 'production')
        if env == 'test':
            from .sqlite import SQLiteContextRepository
            return SQLiteContextRepository()
        else:
            from .supabase import SupabaseContextRepository
            return SupabaseContextRepository()
    
    @staticmethod
    def get_git_branch_repository():
        # Similar implementation for git branch
        env = os.getenv('ENVIRONMENT', 'production')
        if env == 'test':
            from .sqlite import SQLiteGitBranchRepository
            return SQLiteGitBranchRepository()
        else:
            from .supabase import SupabaseGitBranchRepository
            return SupabaseGitBranchRepository()
'''
    
    # Create the central factory
    Write(
        file_path="src/fastmcp/task_management/infrastructure/repositories/repository_factory.py",
        content=central_factory_code
    )
    
    # Fix all 27 broken factory files
    broken_factories = [
        "task_repository_factory.py",
        "project_repository_factory.py",
        "context_repository_factory.py",
        "git_branch_repository_factory.py",
        # ... all 27 factory files
    ]
    
    for factory_file in broken_factories:
        # Update each factory to use the central factory
        Edit(
            file_path=f"src/fastmcp/task_management/infrastructure/repositories/{factory_file}",
            old_string="def create():\n    return TaskRepository()",
            new_string="def create():\n    from .repository_factory import RepositoryFactory\n    return RepositoryFactory.get_task_repository()"
        )
        
        print(f"✅ Fixed factory: {factory_file}")
    
    # Complete the factory task
    mcp__dhafnck_mcp_http__complete_task_with_update(
        task_id=available_tasks["task_id"],
        completion_summary="Fixed all 27 repository factories - now check environment variables",
        implementation_details="Created central RepositoryFactory with environment checking logic",
        files_modified=28  # 27 factories + 1 new central factory
    )
```

#### Priority 2: Add Cache Invalidation (32 methods)

```python
elif available_tasks["task"]["title"].contains("Cache Invalidation"):
    # Create cached repository wrapper
    cached_wrapper_code = '''
import json
import redis
from typing import Optional

class CachedTaskRepository:
    """Wrapper that adds caching to any repository"""
    
    def __init__(self, base_repository):
        self.base_repo = base_repository
        self.redis_client = self._init_redis()
        self.ttl = 300  # 5 minutes default
    
    def _init_redis(self):
        """Initialize Redis connection with fallback"""
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=True
            )
            client.ping()
            return client
        except:
            return None  # Graceful fallback
    
    def create_task(self, task):
        """Create with cache invalidation"""
        result = self.base_repo.create_task(task)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.redis_client:
            self._invalidate_pattern("tasks:list:*")
            self._invalidate_pattern(f"tasks:branch:{task.branch_id}")
            self._invalidate_pattern("tasks:project:*")
        
        return result
    
    def update_task(self, task):
        """Update with cache invalidation"""
        result = self.base_repo.update_task(task)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.redis_client:
            self._invalidate_key(f"task:{task.id}")
            self._invalidate_pattern("tasks:list:*")
            self._invalidate_pattern(f"tasks:branch:{task.branch_id}")
        
        return result
    
    def delete_task(self, task_id):
        """Delete with cache invalidation"""
        result = self.base_repo.delete_task(task_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.redis_client:
            self._invalidate_key(f"task:{task_id}")
            self._invalidate_pattern("tasks:*")
        
        return result
    
    def _invalidate_key(self, key):
        """Delete specific cache key"""
        if self.redis_client:
            self.redis_client.delete(key)
    
    def _invalidate_pattern(self, pattern):
        """Delete all keys matching pattern"""
        if self.redis_client:
            for key in self.redis_client.scan_iter(pattern):
                self.redis_client.delete(key)
'''
    
    # Create cached repository wrappers for each entity
    cached_entities = ["Task", "Project", "Context", "GitBranch", "Subtask"]
    
    for entity in cached_entities:
        Write(
            file_path=f"src/fastmcp/task_management/infrastructure/repositories/cached/cached_{entity.lower()}_repository.py",
            content=cached_wrapper_code.replace("Task", entity).replace("task", entity.lower())
        )
        
        print(f"✅ Created cached wrapper: Cached{entity}Repository")
    
    # Update facades to use cached repositories through factory
    facade_updates = [
        "task_application_facade.py",
        "project_application_facade.py", 
        "context_application_facade.py",
        # ... all facade files
    ]
    
    for facade_file in facade_updates:
        Edit(
            file_path=f"src/fastmcp/task_management/application/facades/{facade_file}",
            old_string="self.repository = MockTaskContextRepository()",
            new_string="from infrastructure.repositories import RepositoryFactory\nself.repository = RepositoryFactory.get_task_repository()"
        )
        
        print(f"✅ Updated facade: {facade_file}")
    
    # Complete the cache task
    mcp__dhafnck_mcp_http__complete_task_with_update(
        task_id=available_tasks["task_id"],
        completion_summary="Added cache invalidation to all 32 mutation methods",
        implementation_details="Created cached repository wrappers with invalidation logic",
        files_modified=len(cached_entities) + len(facade_updates)
    )
```

### Phase 3: Update Context & Progress

```python
# Update context with implementation progress
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "code_fixes_applied": True,
        "controllers_fixed": 16,
        "factories_fixed": 27,
        "cache_added": 32,
        "estimated_compliance_improvement": "Expected 60-80 point increase",
        "next_phase": "testing_verification"
    }
)

print("✅ Code implementation phase complete!")
print("📝 All violation fixes applied")
print("🔄 Test agent should now verify compliance")
```

### Phase 4: Wait Logic for Next Tasks

```python
# Check for more tasks, wait if none available
def wait_for_tasks():
    """Wait 5 minutes if no tasks available"""
    next_task = mcp__dhafnck_mcp_http__manage_task(
        action="next",
        git_branch_id=branch_id,
        assigned_agent="@coding_agent"
    )
    
    if not next_task:
        print("⏱️ No more coding tasks. Waiting 5 minutes...")
        import time
        time.sleep(300)  # 5 minutes
        
        # Check again after wait
        next_task = mcp__dhafnck_mcp_http__manage_task(
            action="next", 
            git_branch_id=branch_id,
            assigned_agent="@coding_agent"
        )
        
        if not next_task:
            print("✅ All coding tasks completed")
            return None
    
    return next_task

# Continue processing tasks until all complete
while True:
    next_task = wait_for_tasks()
    if not next_task:
        break
    
    # Process the next task
    # ... (repeat Phase 2 logic)
```

## 📊 Success Criteria for Code Phase

- ✅ All controller violations fixed (16 files)
- ✅ All repository factories working (27 files)  
- ✅ Cache invalidation added (32 methods)
- ✅ All facades updated to use factory
- ✅ Context updated with progress
- ✅ Tasks marked complete with details

## 🎯 Expected Compliance Improvement

After code fixes:
- **Before**: 20/100 compliance score
- **Expected**: 80-90/100 compliance score
- **Remaining**: Test verification needed for 100/100

The code agent implements all the actual fixes identified by the analyze agent and prepares the system for test verification.