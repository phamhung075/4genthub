#!/usr/bin/env python3
"""
Create test data for context injection system testing
"""

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.database.models import (
    Project, ProjectGitBranch, Task, TaskSubtask, ProjectContext, TaskContext
)

def create_test_data():
    """Create sample data for testing context injection"""
    
    session = get_session()
    
    try:
        print("Creating test data...")
        
        # 1. Create a test project
        project = Project(
            id=str(uuid.uuid4()),
            name="Context Injection Test Project",
            description="Test project for validating context injection system",
            user_id="test-user-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(project)
        print(f"✅ Created project: {project.name}")
        
        # 2. Create a git branch
        git_branch = ProjectGitBranch(
            id=str(uuid.uuid4()),
            name="feature/context-injection",
            description="Implementing real-time context injection for hooks",
            project_id=project.id,
            user_id="test-user-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(git_branch)
        print(f"✅ Created git branch: {git_branch.name}")
        
        # 3. Create multiple tasks with different statuses
        tasks_data = [
            {
                "title": "Implement JWT authentication for hooks",
                "status": "completed",
                "priority": "high",
                "details": "Create separate JWT authentication system for hook-to-MCP communication"
            },
            {
                "title": "Add context injection middleware",
                "status": "in_progress",
                "priority": "high",
                "details": "Implement middleware to inject relevant context into hook requests"
            },
            {
                "title": "Optimize MCP query performance",
                "status": "todo",
                "priority": "medium",
                "details": "Ensure context queries complete within 500ms performance target"
            },
            {
                "title": "Add caching layer for context",
                "status": "todo",
                "priority": "medium",
                "details": "Implement Redis caching for frequently accessed context data"
            },
            {
                "title": "Write comprehensive tests",
                "status": "todo",
                "priority": "low",
                "details": "Create unit and integration tests for context injection system"
            }
        ]
        
        for task_data in tasks_data:
            task = Task(
                id=str(uuid.uuid4()),
                title=task_data["title"],
                description=task_data["details"][:100],  # Use first 100 chars of details for description
                status=task_data["status"],
                priority=task_data["priority"],
                details=task_data["details"],
                git_branch_id=git_branch.id,
                user_id="test-user-001",
                estimated_effort="2 hours",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(task)
            print(f"✅ Created task: {task.title} ({task.status})")
            
            # Add subtasks for in-progress task
            if task.status == "in_progress":
                subtasks = [
                    {"title": "Design context detection logic", "status": "completed"},
                    {"title": "Implement MCP query engine", "status": "completed"},
                    {"title": "Add context formatting", "status": "in_progress"},
                    {"title": "Test with real MCP data", "status": "todo"}
                ]
                
                for st_data in subtasks:
                    subtask = TaskSubtask(
                        id=str(uuid.uuid4()),
                        title=st_data["title"],
                        description=st_data["title"],  # Use title as description for simplicity
                        status=st_data["status"],
                        task_id=task.id,
                        user_id="test-user-001",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(subtask)
                    print(f"  ✅ Created subtask: {subtask.title}")
        
        # 4. Create project context
        project_context = ProjectContext(
            id=str(uuid.uuid4()),
            project_id=project.id,
            data={
                "name": "Context Injection Project",
                "description": "Building real-time context injection system for Claude hooks",
                "status": "in_progress",
                "branch": git_branch.name,
                "environment": "development",
                "features": ["jwt_auth", "context_injection", "performance_optimization"]
            },
            project_info={
                "name": project.name,
                "description": project.description,
                "version": "1.0.0",
                "status": "active"
            },
            user_id="test-user-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(project_context)
        print(f"✅ Created project context with data: {list(project_context.data.keys())}")
        
        # Commit all changes
        session.commit()
        print("\n✅ All test data created successfully!")
        
        # Show summary
        print("\n📊 Test Data Summary:")
        print(f"  - 1 Project")
        print(f"  - 1 Git Branch")
        print(f"  - {len(tasks_data)} Tasks (1 completed, 1 in_progress, 3 todo)")
        print(f"  - 4 Subtasks")
        print(f"  - 1 Project context with rich data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = create_test_data()
    exit(0 if success else 1)