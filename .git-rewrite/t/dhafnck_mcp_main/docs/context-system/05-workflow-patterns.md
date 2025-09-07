# Context System Workflow Patterns

## Overview

This guide presents common workflow patterns and best practices for using the context system effectively in various scenarios.

## Core Workflow Patterns

### 1. Task Development Workflow

Complete workflow from task creation to completion with manual context updates.

```python
# Phase 1: Task Creation
task = create_task(title="Implement user authentication")
manage_context(
    action="create",
    level="task",
    context_id=task.id,
    data={
        "title": task.title,
        "requirements": ["JWT tokens", "Refresh mechanism", "Secure storage"],
        "estimated_effort": "3 days"
    }
)

# Phase 2: Analysis & Discovery
# AI must manually report file reads and searches
read_file("auth/existing_code.py")
search_codebase("authentication")
# Manual context update required:
manage_context(
    action="add_progress",
    level="task",
    context_id=task.id,
    content="Analyzed existing auth code and found JWT utilities"
)

manage_context(
    action="add_insight",
    level="task",
    context_id=task.id,
    content="Found existing JWT utility in utils/auth.py",
    category="discovery"
)

# Phase 3: Implementation
# File edits must be manually reported
edit_file("auth/routes.py", jwt_implementation)
edit_file("auth/models.py", user_model)
# Manual context update required:
manage_context(
    action="update",
    level="task",
    context_id=task.id,
    data={
        "files_modified": ["auth/routes.py", "auth/models.py"],
        "implementation_notes": "Added JWT endpoints and user model"
    }
)

manage_context(
    action="add_progress",
    level="task",
    context_id=task.id,
    content="Implemented JWT token generation and validation"
)

# Phase 4: Testing
run_tests("auth/test_jwt.py")
# Manual context update required:
manage_context(
    action="add_progress",
    level="task",
    context_id=task.id,
    content="All JWT tests passing (15/15)"
)

# Phase 5: Pattern Delegation
manage_context(
    action="delegate",
    level="task",
    context_id=task.id,
    delegate_to="project",
    delegate_data={
        "jwt_pattern": {
            "implementation": jwt_code,
            "tests": test_code,
            "usage": "Standard JWT auth for all endpoints"
        }
    },
    delegation_reason="Reusable authentication pattern"
)

# Phase 6: Completion
complete_task(task.id, "JWT authentication fully implemented")
```

### 2. Multi-Agent Collaboration Pattern

How multiple agents work on the same context with real-time sync.

```python
# Agent A: Backend Developer
class BackendAgent:
    async def implement_api(self, task_id: str):
        # Pull latest context
        context = manage_context(
            action="get",
            level="task",
            context_id=task_id,
            include_inherited=True
        )
        
        # Work on API
        edit_file("api/auth.py", api_code)
        
        # Update progress (manual update syncs to cloud)
        manage_context(
            action="add_progress",
            level="task",
            context_id=task_id,
            content="API endpoints completed",
            agent="@backend_agent"
        )

# Agent B: Frontend Developer (receives notification)
class FrontendAgent:
    async def on_context_change(self, notification):
        if notification["changed_by"] == "@backend_agent":
            # Pull latest changes
            context = manage_context(
                action="get",
                level="task",
                context_id=notification["context_id"]
            )
            
            # Start frontend work based on API
            edit_file("frontend/auth.js", frontend_code)
            
            manage_context(
                action="add_progress",
                level="task",
                context_id=notification["context_id"],
                content="Frontend integrated with new API",
                agent="@frontend_agent"
            )

# Agent C: Test Engineer (monitors both)
class TestAgent:
    async def create_integration_tests(self, task_id: str):
        # Get complete context with all updates
        context = manage_context(
            action="resolve",
            level="task",
            context_id=task_id
        )
        
        # Create tests based on both implementations
        create_file("tests/integration/auth_test.py", test_code)
```

### 3. Feature Branch Workflow

Managing context across feature development lifecycle.

```python
# 1. Create feature branch with context
branch = create_git_branch("feature/user-profiles")
manage_context(
    action="create",
    level="branch",
    context_id=branch.id,
    data={
        "feature_name": "User Profiles",
        "requirements": {
            "profile_fields": ["avatar", "bio", "preferences"],
            "privacy_settings": ["public", "private", "friends"],
            "api_endpoints": ["/profile", "/profile/edit", "/profile/settings"]
        },
        "technical_decisions": {
            "storage": "PostgreSQL with JSON fields",
            "caching": "Redis with 5min TTL",
            "image_handling": "S3 with CDN"
        }
    }
)

# 2. Create tasks under branch
tasks = [
    create_task("Design profile schema", branch.id),
    create_task("Implement profile API", branch.id),
    create_task("Create profile UI", branch.id),
    create_task("Add privacy controls", branch.id)
]

# Each task inherits branch context automatically
for task in tasks:
    context = manage_context(
        action="resolve",
        level="task",
        context_id=task.id
    )
    # context now includes branch requirements and decisions

# 3. Delegate discoveries back to branch
manage_context(
    action="delegate",
    level="task",
    context_id=tasks[0].id,  # From schema design task
    delegate_to="branch",
    delegate_data={
        "profile_schema": final_schema,
        "migration_script": migration_code
    },
    delegation_reason="Schema needed by all profile tasks"
)
```

### 4. Cross-Project Pattern Sharing

Sharing successful patterns across projects.

```python
# Project A: Discovers efficient caching pattern
manage_context(
    action="delegate",
    level="project",
    context_id="project-a",
    delegate_to="global",
    delegate_data={
        "redis_caching_pattern": {
            "implementation": cache_wrapper_code,
            "configuration": cache_config,
            "performance_metrics": {
                "cache_hit_rate": "92%",
                "response_time_improvement": "65%",
                "memory_usage": "moderate"
            },
            "use_cases": ["API responses", "Database queries", "Computed values"]
        }
    },
    delegation_reason="High-performance caching pattern for organization"
)

# Project B: Automatically inherits pattern
new_task = create_task("Implement API caching", project_b_id)
context = manage_context(
    action="resolve",
    level="task",
    context_id=new_task.id
)
# context includes redis_caching_pattern from global level

# Project B can use the pattern
cache_config = context["data"]["redis_caching_pattern"]["configuration"]
implement_caching(cache_config)
```

### 5. Progressive Context Enhancement

Building context through iterative development.

```python
# Initial context - minimal
manage_context(
    action="create",
    level="task",
    context_id=task_id,
    data={
        "title": "Build recommendation engine",
        "status": "planning"
    }
)

# After research - enhanced
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "algorithm_choices": {
            "collaborative_filtering": "Good for user similarity",
            "content_based": "Good for item features",
            "hybrid": "Best of both, more complex"
        },
        "selected_approach": "hybrid",
        "rationale": "Better results despite complexity"
    }
)

# After prototyping - more enhancement
manage_context(
    action="add_insight",
    level="task",
    context_id=task_id,
    content="Matrix factorization reduces computation by 70%",
    category="performance",
    importance="high"
)

# After implementation - final context
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "implementation_details": {
            "algorithm": "SVD with bias terms",
            "libraries": ["surprise", "numpy", "pandas"],
            "performance": "100ms per recommendation",
            "accuracy": "MAE: 0.72"
        },
        "deployment_notes": {
            "compute_requirements": "4 CPU cores, 8GB RAM",
            "scaling_strategy": "Horizontal with load balancer",
            "update_frequency": "Daily model retraining"
        }
    }
)
```

## Best Practices

### 1. Context Granularity

```python
# ❌ Too coarse - loses detail
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={"progress": "Working on authentication"}
)

# ✅ Appropriate detail - useful for others
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "progress": {
            "completed": ["JWT token generation", "Refresh token logic"],
            "in_progress": ["Session management"],
            "blocked": ["LDAP integration - waiting for credentials"],
            "next_steps": ["Add rate limiting", "Implement logout"]
        }
    }
)
```

### 2. Insight Categories

Use consistent categories for better organization:

```python
INSIGHT_CATEGORIES = {
    "performance": "Speed, efficiency, optimization discoveries",
    "security": "Vulnerabilities, best practices, audit findings", 
    "technical": "Implementation details, architecture decisions",
    "business": "Requirements, constraints, user feedback",
    "discovery": "Existing code, libraries, patterns found"
}

# Example usage
manage_context(
    action="add_insight",
    level="task",
    context_id=task_id,
    content="SQL query optimization reduced load time by 80%",
    category="performance",
    importance="high"
)
```

### 3. Delegation Guidelines

Know when to delegate patterns:

```python
# ✅ Good delegation - reusable pattern
manage_context(
    action="delegate",
    level="task",
    context_id=task_id,
    delegate_to="project",
    delegate_data={
        "error_handling_middleware": {
            "code": middleware_code,
            "usage": "Wrap all API endpoints",
            "benefits": "Consistent error responses"
        }
    },
    delegation_reason="Standard error handling for all APIs"
)

# ❌ Poor delegation - too specific
manage_context(
    action="delegate",
    level="task",
    context_id=task_id,
    delegate_to="global",
    delegate_data={
        "user_123_preferences": {
            "theme": "dark",
            "language": "en"
        }
    },
    delegation_reason="User preferences"  # Too specific!
)
```

### 4. Progress Tracking Patterns

```python
class ProgressTracker:
    """Manual progress tracking helper"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.checkpoints = []
    
    async def checkpoint(self, name: str, details: Dict = None):
        """Manually record progress checkpoint"""
        self.checkpoints.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        })
        
        # Manual context update required - AI must call this
        await manage_context(
            action="add_progress",
            level="task",
            context_id=self.task_id,
            content=f"Checkpoint: {name}",
            agent=current_agent()
        )
    
    async def complete_phase(self, phase: str, summary: str):
        """Mark phase completion"""
        await manage_context(
            action="update",
            level="task",
            context_id=self.task_id,
            data={
                f"phase_{phase}": {
                    "status": "completed",
                    "summary": summary,
                    "checkpoints": self.checkpoints,
                    "duration": self._calculate_duration()
                }
            }
        )
        self.checkpoints = []  # Reset for next phase

# Usage
tracker = ProgressTracker(task_id)
await tracker.checkpoint("Database schema created")
await tracker.checkpoint("API endpoints defined", {"count": 12})
await tracker.complete_phase("design", "All components designed")
```

### 5. Context-Driven Decision Making

```python
async def make_technical_decision(task_id: str, decision_type: str):
    """Make decisions based on inherited context"""
    
    # Get full context
    context = await manage_context(
        action="resolve",
        level="task",
        context_id=task_id
    )
    
    # Extract relevant constraints
    constraints = {
        "global": context["data"].get("technology_standards", {}),
        "project": context["data"].get("project_architecture", {}),
        "branch": context["data"].get("feature_requirements", {}),
        "task": context["data"].get("specific_needs", {})
    }
    
    # Make informed decision
    if decision_type == "database":
        if constraints["global"].get("preferred_db") == "PostgreSQL":
            decision = "PostgreSQL"
        elif constraints["project"].get("existing_db"):
            decision = constraints["project"]["existing_db"]
        else:
            decision = "SQLite"  # Default
    
    # Document decision in context
    await manage_context(
        action="update",
        level="task",
        context_id=task_id,
        data={
            "technical_decisions": {
                decision_type: {
                    "choice": decision,
                    "rationale": f"Based on constraints: {constraints}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }
    )
    
    return decision
```

## Anti-Patterns to Avoid

### 1. Context Hoarding
```python
# ❌ Keeping everything at task level
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "jwt_implementation": jwt_code,  # Should be delegated
        "error_handler": error_code,     # Should be delegated
        "db_schema": schema_code,        # Should be delegated
        "my_progress": "50%"             # OK to keep
    }
)
```

### 2. Forgetting to Update
```python
# ❌ Doing work without updating context
edit_file("important.py", new_code)
run_tests("test_important.py")
# Context never updated!

# ✅ Remember to update context manually
edit_file("important.py", new_code)
run_tests("test_important.py")
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "progress": "Updated important.py and tests passing",
        "files_modified": ["important.py"]
    }
)
```

### 3. Over-Inheriting
```python
# ❌ Relying too heavily on inheritance
context = manage_context(action="resolve", level="task", context_id=task_id)
database_choice = context["data"]["database"]  # What if not set?

# ✅ Defensive coding with defaults
database_choice = context["data"].get("database", "PostgreSQL")  # Safe default
```