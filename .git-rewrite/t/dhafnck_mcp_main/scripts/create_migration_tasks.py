#!/usr/bin/env python3
"""
Script to create comprehensive tasks for user isolation migration.
This creates tasks following TDD principles with proper subtasks.
"""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any

# Backend API URL
API_URL = "http://localhost:8000"

# System user ID for tasks
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

def create_task(title: str, description: str, priority: str = "high", subtasks: List[Dict] = None) -> Dict:
    """Create a task with optional subtasks."""
    task_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
        "user_id": SYSTEM_USER_ID,
        "metadata": {
            "migration": "user_isolation",
            "created_by": "migration_script",
            "tdd_required": True
        }
    }
    
    # Create main task
    response = requests.post(f"{API_URL}/tasks", json=task_data)
    if response.status_code != 200:
        print(f"Failed to create task: {title}")
        return None
    
    task = response.json()
    task_id = task.get("id")
    
    # Create subtasks if provided
    if subtasks and task_id:
        for subtask in subtasks:
            subtask_data = {
                "task_id": task_id,
                "title": subtask["title"],
                "description": subtask.get("description", ""),
                "status": "pending",
                "user_id": SYSTEM_USER_ID
            }
            sub_response = requests.post(f"{API_URL}/tasks/{task_id}/subtasks", json=subtask_data)
            if sub_response.status_code != 200:
                print(f"Failed to create subtask: {subtask['title']}")
    
    return task

def main():
    """Create all migration tasks."""
    print("Creating User Isolation Migration Tasks...")
    print("=" * 60)
    
    # Task 1: Repository Layer Updates
    print("\n1. Creating Repository Layer Tasks...")
    repo_subtasks = [
        {"title": "Write tests for TaskRepository user_id filtering", 
         "description": "Create comprehensive tests for user data isolation in TaskRepository"},
        {"title": "Update TaskRepository to use BaseUserScopedRepository",
         "description": "Ensure all queries filter by user_id"},
        {"title": "Write tests for ProjectRepository user_id filtering",
         "description": "Test project isolation between users"},
        {"title": "Update ProjectRepository for user isolation",
         "description": "Inherit from BaseUserScopedRepository and update queries"},
        {"title": "Write tests for all Context repositories",
         "description": "Test global, project, branch, and task context isolation"},
        {"title": "Update all Context repositories for user isolation",
         "description": "Add user_id filtering to all context levels"},
        {"title": "Write tests for AgentRepository user isolation",
         "description": "Test agent data isolation"},
        {"title": "Update AgentRepository with user_id filtering",
         "description": "Ensure agents are user-scoped"},
        {"title": "Write tests for SubtaskRepository",
         "description": "Test subtask isolation"},
        {"title": "Update SubtaskRepository for user isolation",
         "description": "Add user_id filtering"},
        {"title": "Write tests for CursorRulesRepository",
         "description": "Test cursor rules isolation"},
        {"title": "Update CursorRulesRepository with user filtering",
         "description": "Ensure cursor rules are user-scoped"}
    ]
    
    create_task(
        title="Repository Layer: Add User Isolation (TDD)",
        description="Update all repository classes to filter by user_id. Follow TDD: write tests first, then implement. Critical for data security.",
        priority="critical",
        subtasks=repo_subtasks
    )
    
    # Task 2: Service/Application Layer
    print("\n2. Creating Service Layer Tasks...")
    service_subtasks = [
        {"title": "Write tests for TaskService with user context",
         "description": "Test that TaskService properly handles user_id"},
        {"title": "Update TaskService to accept and pass user_id",
         "description": "Modify all methods to include user context"},
        {"title": "Write tests for ProjectService user context",
         "description": "Test project service user isolation"},
        {"title": "Update ProjectService with user_id handling",
         "description": "Pass user_id to repository layer"},
        {"title": "Write tests for ContextService (all levels)",
         "description": "Test context service with user isolation"},
        {"title": "Update ContextService for user scoping",
         "description": "Handle user_id for all context levels"},
        {"title": "Write tests for AgentService",
         "description": "Test agent service user isolation"},
        {"title": "Update AgentService with user context",
         "description": "Pass user_id through service layer"},
        {"title": "Update all remaining services",
         "description": "Ensure all services handle user_id properly"}
    ]
    
    create_task(
        title="Service Layer: Propagate User Context (TDD)",
        description="Update all service classes to accept and pass user_id to repositories. Write tests first following TDD.",
        priority="critical",
        subtasks=service_subtasks
    )
    
    # Task 3: API Routes and Authentication
    print("\n3. Creating API Routes Tasks...")
    api_subtasks = [
        {"title": "Write tests for authentication middleware",
         "description": "Test JWT validation and user_id extraction"},
        {"title": "Create authentication middleware",
         "description": "Implement JWT token validation and user extraction"},
        {"title": "Write tests for task routes with auth",
         "description": "Test authenticated task endpoints"},
        {"title": "Update task routes to extract user_id",
         "description": "Pass user_id from auth to service layer"},
        {"title": "Write tests for project routes",
         "description": "Test authenticated project endpoints"},
        {"title": "Update project routes with user auth",
         "description": "Add authentication to project endpoints"},
        {"title": "Write tests for context routes",
         "description": "Test all context endpoints with auth"},
        {"title": "Update context routes for user isolation",
         "description": "Add user_id handling to context endpoints"},
        {"title": "Update all remaining routes",
         "description": "Ensure all endpoints properly handle authentication"}
    ]
    
    create_task(
        title="API Routes: Add Authentication Layer (TDD)",
        description="Add authentication middleware and update all routes to extract and pass user_id. Critical for API security.",
        priority="critical",
        subtasks=api_subtasks
    )
    
    # Task 4: Database Models and Schemas
    print("\n4. Creating Database Schema Tasks...")
    db_subtasks = [
        {"title": "Write tests for SQLAlchemy models",
         "description": "Test that all models have user_id field"},
        {"title": "Update SQLAlchemy models with user_id",
         "description": "Add user_id to all model classes"},
        {"title": "Write tests for Pydantic schemas",
         "description": "Test schema validation with user_id"},
        {"title": "Update Pydantic schemas for user_id",
         "description": "Add user_id field to all schemas"},
        {"title": "Write migration verification tests",
         "description": "Test that migration completed successfully"},
        {"title": "Verify foreign key constraints",
         "description": "Ensure all FKs to auth.users work properly"}
    ]
    
    create_task(
        title="Database Models: Add User ID Fields (TDD)",
        description="Update all SQLAlchemy models and Pydantic schemas to include user_id field. Verify migration success.",
        priority="high",
        subtasks=db_subtasks
    )
    
    # Task 5: Frontend Updates
    print("\n5. Creating Frontend Tasks...")
    frontend_subtasks = [
        {"title": "Write tests for API client authentication",
         "description": "Test auth header injection in API calls"},
        {"title": "Update API client with auth headers",
         "description": "Add JWT token to all API requests"},
        {"title": "Write tests for task components",
         "description": "Test task components with user context"},
        {"title": "Update task components for user data",
         "description": "Handle user-scoped task data"},
        {"title": "Write tests for project components",
         "description": "Test project components with user isolation"},
        {"title": "Update project components",
         "description": "Display only user's projects"},
        {"title": "Write tests for context display",
         "description": "Test context components with user data"},
        {"title": "Update context components",
         "description": "Show only user's contexts"},
        {"title": "Implement authentication flow",
         "description": "Add login/logout and token management"}
    ]
    
    create_task(
        title="Frontend: Implement User Authentication (TDD)",
        description="Update React frontend to handle user authentication and display user-scoped data. Write tests first.",
        priority="high",
        subtasks=frontend_subtasks
    )
    
    # Task 6: Integration and E2E Tests
    print("\n6. Creating Integration Test Tasks...")
    test_subtasks = [
        {"title": "Write multi-user integration tests",
         "description": "Test data isolation between multiple users"},
        {"title": "Create cross-user access prevention tests",
         "description": "Verify users cannot access others' data"},
        {"title": "Write context inheritance tests",
         "description": "Test context inheritance with user boundaries"},
        {"title": "Create performance tests",
         "description": "Test query performance with user filtering"},
        {"title": "Write E2E authentication flow tests",
         "description": "Test complete auth flow from login to data access"},
        {"title": "Create security audit tests",
         "description": "Comprehensive security testing for data leaks"}
    ]
    
    create_task(
        title="Integration Tests: Verify User Isolation",
        description="Create comprehensive integration and E2E tests to verify user data isolation works correctly.",
        priority="critical",
        subtasks=test_subtasks
    )
    
    # Task 7: Migration Rollout and Verification
    print("\n7. Creating Migration Rollout Tasks...")
    rollout_subtasks = [
        {"title": "Run migration on test database",
         "description": "Apply user isolation migration to test DB"},
        {"title": "Verify migration success",
         "description": "Check all tables have user_id columns"},
        {"title": "Test data integrity",
         "description": "Verify existing data has proper user_id values"},
        {"title": "Create rollback plan",
         "description": "Document rollback procedure if needed"},
        {"title": "Run migration on staging",
         "description": "Apply to staging environment"},
        {"title": "Performance testing on staging",
         "description": "Test performance impact of user filtering"},
        {"title": "Run migration on production",
         "description": "Final production deployment"},
        {"title": "Post-migration verification",
         "description": "Verify production data integrity"}
    ]
    
    create_task(
        title="Migration Rollout: Deploy User Isolation",
        description="Execute user isolation migration across all environments with proper verification.",
        priority="critical",
        subtasks=rollout_subtasks
    )
    
    # Task 8: Documentation and Training
    print("\n8. Creating Documentation Tasks...")
    doc_subtasks = [
        {"title": "Document repository changes",
         "description": "Update docs for BaseUserScopedRepository pattern"},
        {"title": "Document service layer changes",
         "description": "Explain user context propagation"},
        {"title": "Document API authentication",
         "description": "API auth requirements and JWT usage"},
        {"title": "Create migration guide",
         "description": "Step-by-step migration instructions"},
        {"title": "Update API documentation",
         "description": "Update OpenAPI/Swagger docs"},
        {"title": "Create developer guide",
         "description": "Guide for working with user-scoped data"}
    ]
    
    create_task(
        title="Documentation: User Isolation Guide",
        description="Create comprehensive documentation for the user isolation feature and migration process.",
        priority="medium",
        subtasks=doc_subtasks
    )
    
    print("\n" + "=" * 60)
    print("✅ Migration tasks created successfully!")
    print("\nIMPORTANT: Follow TDD principles:")
    print("1. Write tests FIRST")
    print("2. Run tests (they should fail)")
    print("3. Implement the feature")
    print("4. Run tests again (they should pass)")
    print("5. Refactor if needed")
    print("\nStart with Repository Layer tasks as they are the foundation.")

if __name__ == "__main__":
    main()