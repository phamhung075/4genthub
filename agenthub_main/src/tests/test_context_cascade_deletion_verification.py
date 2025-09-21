#!/usr/bin/env python3
"""
Test script to verify cascade deletion for task contexts.

This script specifically tests if task contexts are properly deleted
when the parent task is deleted, addressing the missing CASCADE configuration.
"""

import uuid
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Import the ORM models
from fastmcp.task_management.infrastructure.database.models import (
    Task, TaskContext, Project, ProjectGitBranch
)
from fastmcp.task_management.infrastructure.database.database_config import Base


def test_task_context_cascade_deletion():
    """Test that deleting a task also deletes its associated context."""

    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("🚀 Starting task context cascade deletion test...")

        # 1. Create test project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Test Project for Context Cascade Deletion",
            description="Testing context cascade deletion functionality",
            user_id="test-user-123"
        )
        session.add(project)
        session.commit()
        print(f"✅ Created project: {project_id}")

        # 2. Create test git branch
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-context-cascade-branch",
            description="Test branch for context cascade deletion",
            user_id="test-user-123"
        )
        session.add(git_branch)
        session.commit()
        print(f"✅ Created git branch: {branch_id}")

        # 3. Create test task
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task for Context Cascade Deletion",
            description="This task will be deleted to test context cascade deletion",
            git_branch_id=branch_id,
            status="in_progress",
            priority="medium",
            user_id="test-user-123",
            context_id=task_id  # Task context uses same ID as task
        )
        session.add(task)
        session.commit()
        print(f"✅ Created task: {task_id}")

        # 4. Create task context
        task_context = TaskContext(
            id=task_id,  # Primary key
            task_id=task_id,  # Foreign key to task
            parent_branch_id=branch_id,
            data={"test_data": "some context data", "progress": 50},
            task_data={"status": "in_progress", "notes": "working on implementation"},
            user_id="test-user-123"
        )
        session.add(task_context)
        session.commit()
        print(f"✅ Created task context: {task_id}")

        # 5. Verify task context exists before deletion
        context_count_before = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Task contexts before deletion: {context_count_before}")
        assert context_count_before == 1, f"Expected 1 task context, found {context_count_before}"

        # 6. Delete the parent task (check if this cascades to delete context)
        print("🗑️ Deleting parent task...")
        task_to_delete = session.query(Task).filter_by(id=task_id).first()
        assert task_to_delete is not None, "Task not found before deletion"

        session.delete(task_to_delete)
        session.commit()
        print(f"✅ Deleted task: {task_id}")

        # 7. Verify task is deleted
        task_after_delete = session.query(Task).filter_by(id=task_id).first()
        assert task_after_delete is None, "Task still exists after deletion"
        print("✅ Verified task is deleted")

        # 8. Verify task context is cascade deleted (THIS IS THE KEY TEST)
        context_count_after = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Task contexts after deletion: {context_count_after}")

        if context_count_after == 0:
            print("🎉 SUCCESS: Context cascade deletion is working correctly!")
            print("✅ Task context was automatically deleted when parent task was deleted")
            return True
        else:
            print(f"❌ FAILURE: {context_count_after} task contexts still exist after parent deletion")
            print("❌ Context cascade deletion is NOT working correctly")
            print("❌ This confirms the missing ondelete='CASCADE' issue!")

            # Show remaining contexts for debugging
            remaining_contexts = session.query(TaskContext).filter_by(task_id=task_id).all()
            for context in remaining_contexts:
                print(f"   - Orphaned context: {context.id} - task_id: {context.task_id}")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("TASK CONTEXT CASCADE DELETION TEST")
    print("=" * 70)
    print()

    success = test_task_context_cascade_deletion()

    print()
    print("=" * 70)
    if success:
        print("✅ RESULT: CONTEXT CASCADE DELETION IS WORKING!")
        print("✅ No fix needed.")
    else:
        print("❌ RESULT: CONTEXT CASCADE DELETION IS BROKEN!")
        print("❌ Fix required: Add ondelete='CASCADE' to TaskContext.task_id foreign key")
        print("❌ Location: models.py line 466")
    print("=" * 70)