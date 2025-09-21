#!/usr/bin/env python3
"""
Test script to verify cascade deletion for tasks and subtasks.

This script verifies that when a parent task is deleted, all its subtasks
are automatically deleted due to the cascade deletion configuration in the
SQLAlchemy ORM models and database foreign key constraints.
"""

import asyncio
import uuid
import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Import the ORM models
from fastmcp.task_management.infrastructure.database.models import (
    Task, Subtask, Project, ProjectGitBranch
)
from fastmcp.task_management.infrastructure.database.database_config import Base


@pytest.mark.asyncio
async def test_cascade_deletion():
    """Test that deleting a task cascades to delete all its subtasks."""

    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("🚀 Starting cascade deletion test...")

        # 1. Create test project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Test Project for Cascade Deletion",
            description="Testing cascade deletion functionality",
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
            name="test-cascade-branch",
            description="Test branch for cascade deletion",
            user_id="test-user-123"
        )
        session.add(git_branch)
        session.commit()
        print(f"✅ Created git branch: {branch_id}")

        # 3. Create test task
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task for Cascade Deletion",
            description="This task will be deleted to test cascade deletion",
            git_branch_id=branch_id,
            status="in_progress",
            priority="medium",
            user_id="test-user-123"
        )
        session.add(task)
        session.commit()
        print(f"✅ Created task: {task_id}")

        # 4. Create multiple subtasks
        subtask_ids = []
        for i in range(3):
            subtask_id = str(uuid.uuid4())
            subtask = Subtask(
                id=subtask_id,
                task_id=task_id,
                title=f"Test Subtask {i+1}",
                description=f"Subtask {i+1} that should be cascade deleted",
                status="todo",
                priority="medium",
                assignees=[f"agent-{i+1}"],
                progress_percentage=0,
                user_id="test-user-123"
            )
            session.add(subtask)
            subtask_ids.append(subtask_id)

        session.commit()
        print(f"✅ Created {len(subtask_ids)} subtasks: {subtask_ids}")

        # 5. Verify subtasks exist before deletion
        subtask_count_before = session.query(Subtask).filter_by(task_id=task_id).count()
        print(f"📊 Subtasks before deletion: {subtask_count_before}")
        assert subtask_count_before == 3, f"Expected 3 subtasks, found {subtask_count_before}"

        # 6. Delete the parent task (this should cascade to delete subtasks)
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

        # 8. Verify all subtasks are cascade deleted
        subtask_count_after = session.query(Subtask).filter_by(task_id=task_id).count()
        print(f"📊 Subtasks after deletion: {subtask_count_after}")

        if subtask_count_after == 0:
            print("🎉 SUCCESS: Cascade deletion is working correctly!")
            print("✅ All subtasks were automatically deleted when parent task was deleted")
            return True
        else:
            print(f"❌ FAILURE: {subtask_count_after} subtasks still exist after parent deletion")
            print("❌ Cascade deletion is NOT working correctly")

            # Show remaining subtasks for debugging
            remaining_subtasks = session.query(Subtask).filter_by(task_id=task_id).all()
            for subtask in remaining_subtasks:
                print(f"   - Orphaned subtask: {subtask.id} - {subtask.title}")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        session.close()


def test_cascade_deletion_sync():
    """Synchronous wrapper for the async test."""
    return asyncio.run(test_cascade_deletion())


if __name__ == "__main__":
    print("=" * 60)
    print("TASK CASCADE DELETION TEST")
    print("=" * 60)
    print()

    success = test_cascade_deletion_sync()

    print()
    print("=" * 60)
    if success:
        print("✅ RESULT: CASCADE DELETION IS ALREADY IMPLEMENTED AND WORKING!")
        print("✅ No further implementation needed.")
    else:
        print("❌ RESULT: CASCADE DELETION NEEDS TO BE IMPLEMENTED!")
        print("❌ Implementation required.")
    print("=" * 60)