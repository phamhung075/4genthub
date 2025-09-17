# Context Update Examples for AI Agents

## Quick Reference: Context Update Commands

### 1. Global Context (User-scoped)
```python
# Update global context with organization standards
mcp__agenthub_http__manage_context(
    action="update",
    level="global",
    context_id=user_id,  # Your user ID
    data={
        "organization_standards": {
            "coding_style": "PEP 8 for Python, ESLint for JavaScript",
            "git_workflow": "GitFlow with feature branches",
            "testing_requirements": "Minimum 80% code coverage"
        },
        "security_policies": {
            "authentication": "JWT with refresh tokens",
            "data_encryption": "AES-256 for sensitive data"
        }
    }
)
```

### 2. Project Context
```python
# Update project context with technology decisions
mcp__agenthub_http__manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "team_preferences": {
            "review_required": True,
            "merge_strategy": "squash"
        },
        "technology_stack": {
            "frontend": ["React", "TypeScript", "Tailwind CSS"],
            "backend": ["Python", "FastAPI", "SQLAlchemy"],
            "database": ["PostgreSQL", "Redis"]
        },
        "project_workflow": {
            "phases": ["design", "develop", "test", "deploy"],
            "current_phase": "develop"
        },
        "local_standards": {
            "naming_convention": "camelCase for frontend, snake_case for backend",
            "component_structure": "atomic design pattern"
        }
    }
)
```

### 3. Branch Context
```python
# Update branch context with feature-specific information
mcp__agenthub_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "branch_workflow": {
            "feature_name": "user-authentication",
            "implementation_status": "in_progress",
            "dependencies_installed": ["jsonwebtoken", "bcrypt"],
            "api_endpoints_created": [
                "/api/v2/auth/login",
                "/api/v2/auth/logout",
                "/api/v2/auth/refresh"
            ]
        },
        "discovered_patterns": {
            "auth_flow": "JWT with httpOnly cookies",
            "session_management": "Redis for token blacklist"
        },
        "branch_decisions": {
            "token_expiry": "15 minutes for access, 7 days for refresh",
            "password_hashing": "bcrypt with 10 rounds"
        }
    }
)
```

### 4. Task Context
```python
# Update task context with specific implementation details
mcp__agenthub_http__manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "branch_id": branch_id,  # Required for task context
        "task_data": {
            "title": "Implement JWT authentication",
            "status": "in_progress",
            "progress_percentage": 60
        },
        "execution_context": {
            "files_modified": [
                "src/auth/jwt.service.ts",
                "src/auth/auth.controller.ts"
            ],
            "tests_added": [
                "jwt.service.spec.ts",
                "auth.e2e.spec.ts"
            ],
            "current_work": "Adding refresh token rotation"
        },
        "discovered_patterns": {
            "token_rotation": "Implemented sliding window refresh",
            "rate_limiting": "Using express-rate-limit middleware"
        },
        "implementation_notes": {
            "challenges": ["Cookie security in development mode"],
            "solutions": ["Added sameSite configuration per environment"],
            "next_steps": ["Add 2FA support", "Implement password reset"]
        }
    }
)
```

## Progressive Context Updates (Don't Overwrite!)

### ❌ WRONG - This overwrites existing data
```python
# DON'T DO THIS - Overwrites all existing context
mcp__agenthub_http__manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "discovered_patterns": {
            "new_pattern": "value"  # This replaces ALL discovered_patterns!
        }
    }
)
```

### ✅ CORRECT - Read, merge, then update
```python
# Step 1: Read existing context
existing = mcp__agenthub_http__manage_context(
    action="get",
    level="task",
    context_id=task_id,
    include_inherited=True
)

# Step 2: Merge new data with existing
updated_patterns = existing["context"].get("discovered_patterns", {})
updated_patterns["new_pattern"] = "value"  # Add to existing patterns

# Step 3: Update with merged data
mcp__agenthub_http__manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "discovered_patterns": updated_patterns,  # Preserves existing patterns
        "implementation_notes": {
            **existing["context"].get("implementation_notes", {}),
            "latest_discovery": "Found existing utility function"
        }
    }
)
```

## Real-World Agent Workflow Example

### Coding Agent Working on Authentication Feature

```python
# 1. Start work - Read branch context to understand feature
branch_context = mcp__agenthub_http__manage_context(
    action="get",
    level="branch",
    context_id=branch_id,
    include_inherited=True
)

# 2. Create task and its context
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Add password reset functionality",
    description="Implement secure password reset with email verification"
)

# 3. Create task context for frontend visibility
mcp__agenthub_http__manage_context(
    action="create",
    level="task",
    context_id=task["task"]["id"],
    data={
        "branch_id": branch_id,
        "task_data": {
            "title": task["task"]["title"],
            "status": "in_progress"
        }
    }
)

# 4. As work progresses, update task context
mcp__agenthub_http__manage_context(
    action="update",
    level="task",
    context_id=task["task"]["id"],
    data={
        "execution_context": {
            "current_step": "Creating password reset token model",
            "files_created": ["models/PasswordResetToken.ts"],
            "database_changes": ["Added password_reset_tokens table"]
        }
    }
)

# 5. Document discoveries in branch context
mcp__agenthub_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "discovered_patterns": {
            "email_service": "Using SendGrid for transactional emails",
            "token_security": "One-time use tokens with 1-hour expiry"
        },
        "branch_decisions": {
            "reset_flow": "Email verification required before password change"
        }
    }
)

# 6. Complete task with summary
mcp__agenthub_http__manage_task(
    action="complete",
    task_id=task["task"]["id"],
    completion_summary="Implemented secure password reset with email verification, one-time tokens, and rate limiting",
    testing_notes="Added unit tests for token generation and e2e tests for reset flow"
)

# 7. Update task context with completion details
mcp__agenthub_http__manage_context(
    action="update",
    level="task",
    context_id=task["task"]["id"],
    data={
        "task_data": {
            "status": "completed",
            "completion_summary": "Password reset fully implemented and tested"
        },
        "implementation_notes": {
            "final_implementation": {
                "endpoints": ["/api/v2/auth/forgot-password", "/api/v2/auth/reset-password"],
                "security_measures": ["Rate limiting", "Token expiry", "One-time use"],
                "test_coverage": "95% for password reset module"
            }
        }
    }
)
```

## Context Delegation Example

When you discover something reusable, delegate it to a higher level:

```python
# Discovered a reusable authentication pattern in task
# Delegate to project level for other branches to use
mcp__agenthub_http__manage_context(
    action="delegate",
    level="task",
    context_id=task_id,
    delegate_to="project",
    delegate_data={
        "reusable_patterns": {
            "jwt_refresh_implementation": {
                "description": "Secure JWT refresh token rotation",
                "code_location": "src/auth/jwt.service.ts",
                "usage": "Import JWTService and use rotateRefreshToken method"
            }
        }
    },
    delegation_reason="Reusable authentication pattern for all features"
)
```

## Key Rules for AI Agents

1. **Always Read Before Update**: Get existing context before updating to preserve data
2. **Update Incrementally**: Add to existing data structures, don't replace them
3. **Use Appropriate Level**: 
   - Global: Organization-wide standards
   - Project: Project-specific decisions and tech stack
   - Branch: Feature-specific implementation details
   - Task: Granular work progress and discoveries
4. **Create Task Context**: Tasks need explicit context creation for frontend visibility
5. **Document Decisions**: Record why decisions were made, not just what
6. **Share Reusable Patterns**: Delegate useful patterns to higher levels

## Common Patterns

### Starting New Work
```python
# 1. Read project context
# 2. Read branch context  
# 3. Create task with context
# 4. Update as you work
# 5. Complete with summary
```

### Continuing Existing Work
```python
# 1. Read task context to understand progress
# 2. Read branch context for feature requirements
# 3. Continue implementation
# 4. Update context with new discoveries
# 5. Complete or handoff with detailed context
```

### Debugging/Investigation
```python
# 1. Read all context levels for background
# 2. Document investigation findings in task context
# 3. Update branch context with solutions
# 4. Delegate reusable fixes to project level
```