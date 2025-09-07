# 🔍 Code Flow Analysis Prompt for Architecture Compliance

## Agent Mission Statement
**YOUR TASK**: Analyze each code path (chemin) in the codebase to verify it follows the correct architectural flow. Ensure NO shortcuts, NO layer violations, and PROPER separation of concerns.

## 🎯 Analysis Checklist for Each Code Path

analyze dhafnck_mcp_main/docs/architecture/index.md for understand complete architecture (continue update if change anything)

### Step 1: Trace the Request Entry Point
```python
# For each MCP tool/endpoint, verify:
✓ Entry point is a Controller (Interface Layer)
✓ Controller ONLY accepts MCP parameters
✓ Controller NEVER directly accesses database
✓ Controller NEVER imports repository classes

# ANALYZE THIS PATH:
mcp_tool_entry → controller_method → ?
```

### Step 2: Verify Controller → Facade Communication
```python
# Check each controller method:
✓ Controller creates/uses a Facade instance
✓ Controller delegates ALL business logic to Facade
✓ Controller ONLY formats responses
✓ Controller handles exceptions from Facade

# CORRECT PATTERN:
class TaskMCPController:
    def __init__(self):
        self.facade = TaskApplicationFacade()  # ✓ Uses facade
        # self.repository = TaskRepository()   # ❌ NEVER do this
    
    def manage_task(self, **params):
        result = self.facade.execute(params)   # ✓ Delegates to facade
        return self.format_response(result)    # ✓ Only formats
```

### Step 3: Analyze Facade → Repository Factory Flow
```python
# Check each facade method:
✓ Facade uses RepositoryFactory to get repositories
✓ Facade NEVER instantiates repositories directly
✓ Facade coordinates between multiple services
✓ Facade manages transactions

# CORRECT PATTERN:
class TaskApplicationFacade:
    def create_task(self, request):
        # ✓ Uses factory
        repository = RepositoryFactory.get_task_repository()
        
        # ❌ NEVER do this
        # repository = SupabaseTaskRepository()
        # repository = SQLiteTaskRepository()
```

### Step 4: Validate Repository Factory Logic
```python
# Check RepositoryFactory implementation:
✓ Checks ENVIRONMENT variable
✓ Checks DATABASE_TYPE variable
✓ Checks REDIS_ENABLED variable
✓ Returns appropriate repository type
✓ Wraps with cache if enabled

# DECISION TREE TO VERIFY:
if ENVIRONMENT == 'test':
    return SQLiteRepository()  # No cache in tests
elif DATABASE_TYPE == 'supabase':
    repo = SupabaseRepository()
    if REDIS_ENABLED == 'true':
        return CachedRepository(repo)
    return repo
```

### Step 5: Verify Cache Invalidation
```python
# For each repository method that modifies data:
✓ CREATE operations invalidate relevant cache keys
✓ UPDATE operations invalidate entity and list caches
✓ DELETE operations invalidate all related caches
✓ Cache invalidation uses CacheInvalidationMixin

# CHECK THESE PATTERNS:
def create_task(self, task):
    result = super().create(task)
    self.invalidate_cache_for_entity(...)  # ✓ Must exist
    return result

def update_task(self, task):
    result = super().update(task)
    self.invalidate_cache_for_entity(...)  # ✓ Must exist
    return result
```

## 🔬 Code Path Analysis Commands

### 1. Find All Entry Points
```bash
# Find all MCP tool definitions
grep -r "class.*MCPController" src/fastmcp/task_management/interface/controllers/

# Find all MCP tool methods
grep -r "def manage_" src/fastmcp/task_management/interface/controllers/
```

### 2. Trace Controller Dependencies
```python
# For each controller, check imports:
from application.facades import SomeFacade  # ✓ Good
from infrastructure.repositories import SomeRepository  # ❌ Bad
from domain.repositories import RepositoryInterface  # ✓ OK (interface only)
```

### 3. Analyze Facade Dependencies
```python
# For each facade, check:
from infrastructure.repositories.repository_factory import RepositoryFactory  # ✓ Good
from infrastructure.repositories.orm.task_repository import ORMTaskRepository  # ❌ Bad
```

### 4. Verify Repository Selection
```python
# Check each repository factory method:
@staticmethod
def get_task_repository():
    # Must check environment variables
    env = os.getenv('ENVIRONMENT', 'production')  # ✓
    db_type = os.getenv('DATABASE_TYPE', 'supabase')  # ✓
    redis_enabled = os.getenv('REDIS_ENABLED', 'true')  # ✓
    
    # Must NOT hardcode
    return SupabaseTaskRepository()  # ❌ Never hardcode
```

## 📊 Analysis Report Template

Use this template to report findings for each code path:

```markdown
## Code Path Analysis: [Feature Name]

### Entry Point
- **MCP Tool**: `mcp__dhafnck_mcp_http__manage_[entity]`
- **Controller**: `[ControllerClass].[method_name]`
- **Location**: `src/fastmcp/task_management/interface/controllers/[file].py`

### Layer Compliance
| Layer | Component | Status | Issues |
|-------|-----------|--------|--------|
| Interface | Controller | ✅/❌ | [List any violations] |
| Application | Facade | ✅/❌ | [List any violations] |
| Domain | Repository Interface | ✅/❌ | [List any violations] |
| Infrastructure | Repository Factory | ✅/❌ | [List any violations] |

### Flow Verification
```
Actual Flow:
MCP Request 
  → [Controller].[method]
  → [Facade].[method]
  → [UseCase].[execute] (if exists)
  → RepositoryFactory.[get_repository]
  → [SelectedRepository].[method]
  → Cache/Database

Expected Flow: ✅ Matches / ❌ Violation at [step]
```

### Cache Invalidation Check
- [ ] CREATE invalidates cache
- [ ] UPDATE invalidates cache
- [ ] DELETE invalidates cache
- [ ] Uses CacheInvalidationMixin

### Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Fix recommendation]
2. [Fix recommendation]
```

## 🛠️ Automated Analysis Script

Create this script to automatically analyze code paths:

```python
# scripts/analyze_architecture_compliance.py

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Set

class ArchitectureAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []
        
    def analyze_controllers(self) -> Dict[str, List[str]]:
        """Find all controllers and their dependencies"""
        controllers_dir = self.project_root / "src/fastmcp/task_management/interface/controllers"
        violations = []
        
        for file in controllers_dir.glob("*.py"):
            with open(file) as f:
                content = f.read()
                
            # Check for direct repository imports
            if "from infrastructure.repositories" in content:
                if "repository_factory" not in content:
                    violations.append({
                        "file": str(file),
                        "type": "Direct Repository Import",
                        "line": self._find_line(content, "from infrastructure.repositories")
                    })
            
            # Check for direct database imports
            if "from infrastructure.database" in content:
                violations.append({
                    "file": str(file),
                    "type": "Direct Database Import",
                    "line": self._find_line(content, "from infrastructure.database")
                })
                
        return violations
    
    def analyze_facades(self) -> Dict[str, List[str]]:
        """Check facade implementations"""
        facades_dir = self.project_root / "src/fastmcp/task_management/application/facades"
        violations = []
        
        for file in facades_dir.glob("*.py"):
            with open(file) as f:
                content = f.read()
            
            # Check for hardcoded repository instantiation
            patterns = [
                r"SQLiteTaskRepository\(\)",
                r"SupabaseTaskRepository\(\)",
                r"ORMTaskRepository\(\)",
            ]
            
            for pattern in patterns:
                if re.search(pattern, content):
                    violations.append({
                        "file": str(file),
                        "type": "Hardcoded Repository",
                        "pattern": pattern
                    })
                    
        return violations
    
    def analyze_cache_invalidation(self) -> Dict[str, List[str]]:
        """Check if repositories properly invalidate cache"""
        repos_dir = self.project_root / "src/fastmcp/task_management/infrastructure/repositories"
        issues = []
        
        for file in repos_dir.glob("**/*.py"):
            if "test" in str(file):
                continue
                
            with open(file) as f:
                content = f.read()
            
            # Check methods that should invalidate cache
            modify_methods = ["create", "update", "delete", "save"]
            
            for method in modify_methods:
                if f"def {method}" in content:
                    # Check if invalidation exists after the method
                    method_block = self._extract_method(content, method)
                    if method_block and "invalidate" not in method_block:
                        issues.append({
                            "file": str(file),
                            "method": method,
                            "issue": "Missing cache invalidation"
                        })
                        
        return issues
    
    def check_repository_factory(self) -> Dict[str, bool]:
        """Verify repository factory implementation"""
        factory_files = list(self.project_root.glob("**/repository_factory.py"))
        checks = {
            "checks_environment": False,
            "checks_database_type": False,
            "checks_redis_enabled": False,
            "no_hardcoded_repos": True
        }
        
        for file in factory_files:
            with open(file) as f:
                content = f.read()
            
            if "os.getenv('ENVIRONMENT'" in content:
                checks["checks_environment"] = True
            if "os.getenv('DATABASE_TYPE'" in content:
                checks["checks_database_type"] = True
            if "os.getenv('REDIS_ENABLED'" in content:
                checks["checks_redis_enabled"] = True
            
            # Check for hardcoded repositories
            if "return SQLiteTaskRepository()" in content and "if" not in content:
                checks["no_hardcoded_repos"] = False
                
        return checks
    
    def generate_report(self):
        """Generate compliance report"""
        print("=" * 60)
        print("ARCHITECTURE COMPLIANCE ANALYSIS REPORT")
        print("=" * 60)
        
        # Analyze controllers
        print("\n📋 CONTROLLER ANALYSIS:")
        controller_violations = self.analyze_controllers()
        if controller_violations:
            for v in controller_violations:
                print(f"  ❌ {v['file']}: {v['type']}")
        else:
            print("  ✅ All controllers comply with architecture")
        
        # Analyze facades
        print("\n📋 FACADE ANALYSIS:")
        facade_violations = self.analyze_facades()
        if facade_violations:
            for v in facade_violations:
                print(f"  ❌ {v['file']}: {v['type']}")
        else:
            print("  ✅ All facades comply with architecture")
        
        # Check cache invalidation
        print("\n📋 CACHE INVALIDATION ANALYSIS:")
        cache_issues = self.analyze_cache_invalidation()
        if cache_issues:
            for issue in cache_issues:
                print(f"  ❌ {issue['file']}: {issue['method']} - {issue['issue']}")
        else:
            print("  ✅ All repositories properly invalidate cache")
        
        # Check repository factory
        print("\n📋 REPOSITORY FACTORY ANALYSIS:")
        factory_checks = self.check_repository_factory()
        for check, passed in factory_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
        
        print("\n" + "=" * 60)
        total_issues = len(controller_violations) + len(facade_violations) + len(cache_issues)
        if total_issues == 0:
            print("✅ ARCHITECTURE FULLY COMPLIANT")
        else:
            print(f"❌ FOUND {total_issues} ARCHITECTURE VIOLATIONS")
        print("=" * 60)

# Usage
if __name__ == "__main__":
    analyzer = ArchitectureAnalyzer(Path("/path/to/project"))
    analyzer.generate_report()
```

## 🔄 Common Flow Patterns to Verify

### Pattern 1: Task Management Flow
```
mcp__dhafnck_mcp_http__manage_task
  → TaskMCPController.manage_task()
  → TaskApplicationFacade.execute_action()
  → CreateTaskUseCase.execute()
  → RepositoryFactory.get_task_repository()
  → [SQLite|Supabase|Cached]TaskRepository.create()
  → CacheInvalidationMixin.invalidate_cache_for_entity()
```

### Pattern 2: Context Management Flow
```
mcp__dhafnck_mcp_http__manage_context
  → ContextMCPController.manage_context()
  → UnifiedContextService.execute()
  → ContextRepositoryFactory.get_context_repository(level)
  → [Global|Project|Branch|Task]ContextRepository.create()
  → ContextCache.invalidate_context()
```

### Pattern 3: Project Management Flow
```
mcp__dhafnck_mcp_http__manage_project
  → ProjectMCPController.manage_project()
  → ProjectApplicationFacade.execute()
  → ProjectRepositoryFactory.create_repository()
  → ORMProjectRepository.create()
  → Cache invalidation (if enabled)
```

## ⚠️ Red Flags to Look For

1. **Layer Violations**
   - Controller importing repositories
   - Facade instantiating repositories directly
   - Domain layer depending on infrastructure

2. **Hardcoded Implementations**
   - `new SupabaseTaskRepository()`
   - `new SQLiteRepository()`
   - Direct Redis client usage without checking availability

3. **Missing Cache Invalidation**
   - UPDATE without invalidate
   - DELETE without invalidate
   - CREATE without invalidating list caches

4. **Environment Ignorance**
   - Not checking ENVIRONMENT variable
   - Not checking REDIS_ENABLED
   - Not using RepositoryFactory

5. **Transaction Mismanagement**
   - Multiple repository calls without transaction
   - Missing rollback on errors
   - Inconsistent state between cache and database

## 📝 Final Verification Steps

1. **Run the analysis script** on entire codebase
2. **Review each violation** and categorize severity
3. **Fix critical violations** first (layer violations)
4. **Add missing cache invalidations**
5. **Replace hardcoded repositories** with factory calls
6. **Test with different configurations**:
   - ENVIRONMENT=test (SQLite, no cache)
   - ENVIRONMENT=production, REDIS_ENABLED=true (Supabase + Redis)
   - ENVIRONMENT=production, REDIS_ENABLED=false (Supabase only)

## 🎯 Success Criteria

The code flow is compliant when:
- ✅ All requests follow: Controller → Facade → Repository Factory → Repository
- ✅ No layer violations exist
- ✅ All repositories use factory pattern
- ✅ Cache invalidation occurs after all data modifications
- ✅ System works with cache enabled AND disabled
- ✅ Test mode uses SQLite, production uses configured database
- ✅ No hardcoded repository implementations

Use this prompt to systematically analyze and fix architecture compliance issues throughout the codebase.