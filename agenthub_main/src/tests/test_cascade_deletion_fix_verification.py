#!/usr/bin/env python3
"""
Test script to verify the cascade deletion fixes work correctly.

This test verifies that the SQLAlchemy relationship cascade and database
foreign key cascade configurations properly delete task contexts when tasks are deleted.
"""

import uuid
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

# Import the ORM models
import sys
import os
sys.path.append(os.path.dirname(__file__) + '/..')

from fastmcp.task_management.infrastructure.database.models import (
    Task, TaskContext, Project, ProjectGitBranch
)
from fastmcp.task_management.infrastructure.database.database_config import Base


def test_sqlalchemy_cascade_deletion():
    """Test that SQLAlchemy relationship cascade deletes contexts."""

    print("🧪 Testing SQLAlchemy relationship cascade deletion...")

    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create test data
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="test-user")
        session.add(project)

        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="test-user"
        )
        session.add(git_branch)

        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Task for testing cascade",
            git_branch_id=branch_id,
            user_id="test-user"
        )
        session.add(task)

        # Create task context
        context_id = str(uuid.uuid4())
        context = TaskContext(
            id=context_id,
            task_id=task_id,
            data={"test": "data"},
            user_id="test-user"
        )
        session.add(context)
        session.commit()

        print(f"✅ Created task: {task_id}")
        print(f"✅ Created context: {context_id} -> task_id: {task_id}")

        # Verify context exists
        context_count_before = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Contexts before deletion: {context_count_before}")

        # Load task with relationships to trigger cascade
        task_with_relationships = session.query(Task).filter_by(id=task_id).first()
        print(f"✅ Task has context relationship: {task_with_relationships.task_context is not None}")

        # Delete using SQLAlchemy (should trigger relationship cascade)
        session.delete(task_with_relationships)
        session.commit()

        # Check if context was deleted via cascade
        context_count_after = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Contexts after deletion: {context_count_after}")

        if context_count_after == 0:
            print("🎉 SUCCESS: SQLAlchemy relationship cascade deletion works!")
            return True
        else:
            print("❌ FAILURE: SQLAlchemy relationship cascade deletion failed")
            remaining = session.query(TaskContext).filter_by(task_id=task_id).all()
            for ctx in remaining:
                print(f"   🚨 Orphaned context: {ctx.id}")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        session.close()


def test_database_foreign_key_cascade():
    """Test that database foreign key cascade works with enforcement enabled."""

    print("\n🧪 Testing database foreign key cascade deletion...")

    # Create in-memory SQLite database with foreign key enforcement
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key enforcement
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Ensure foreign key enforcement is on
    session.execute(text("PRAGMA foreign_keys = ON"))

    try:
        # Create test data
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="test-user")
        session.add(project)

        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="test-user"
        )
        session.add(git_branch)

        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Task for testing FK cascade",
            git_branch_id=branch_id,
            user_id="test-user"
        )
        session.add(task)

        # Create task context
        context_id = str(uuid.uuid4())
        context = TaskContext(
            id=context_id,
            task_id=task_id,
            data={"test": "data"},
            user_id="test-user"
        )
        session.add(context)
        session.commit()

        print(f"✅ Created task: {task_id}")
        print(f"✅ Created context: {context_id} -> task_id: {task_id}")

        # Verify context exists
        context_count_before = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Contexts before deletion: {context_count_before}")

        # Delete task directly (should trigger database FK cascade)
        task_to_delete = session.query(Task).filter_by(id=task_id).first()
        session.delete(task_to_delete)
        session.commit()

        # Check if context was deleted via database cascade
        context_count_after = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Contexts after deletion: {context_count_after}")

        if context_count_after == 0:
            print("🎉 SUCCESS: Database foreign key cascade deletion works!")
            return True
        else:
            print("❌ FAILURE: Database foreign key cascade deletion failed")
            remaining = session.query(TaskContext).filter_by(task_id=task_id).all()
            for ctx in remaining:
                print(f"   🚨 Orphaned context: {ctx.id}")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False
    finally:
        session.close()


def test_repository_manual_deletion_still_works():
    """Test that the existing manual deletion in repository still works as backup."""

    print("\n🧪 Testing repository manual deletion still works...")

    # Import repository
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
    from fastmcp.task_management.infrastructure.database.database_config import get_session

    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    # Create test session
    session = Session()

    try:
        # Create test data
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="test-user")
        session.add(project)

        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="test-user"
        )
        session.add(git_branch)

        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Task for testing repository deletion",
            git_branch_id=branch_id,
            user_id="test-user"
        )
        session.add(task)

        # Create task context
        context_id = str(uuid.uuid4())
        context = TaskContext(
            id=context_id,
            task_id=task_id,
            data={"test": "data"},
            user_id="test-user"
        )
        session.add(context)
        session.commit()

        print(f"✅ Created task: {task_id}")
        print(f"✅ Created context: {context_id} -> task_id: {task_id}")

        # Verify context exists
        context_count_before = session.query(TaskContext).filter_by(task_id=task_id).count()
        print(f"📊 Contexts before deletion: {context_count_before}")

        # Create repository instance with session
        repo = ORMTaskRepository(session=session, git_branch_id=branch_id, user_id="test-user")

        # Delete using repository method (includes manual context deletion)
        success = repo.delete_task(task_id)

        if success:
            # Check if context was deleted
            context_count_after = session.query(TaskContext).filter_by(task_id=task_id).count()
            print(f"📊 Contexts after deletion: {context_count_after}")

            if context_count_after == 0:
                print("🎉 SUCCESS: Repository manual deletion still works!")
                return True
            else:
                print("❌ FAILURE: Repository manual deletion failed")
                return False
        else:
            print("❌ FAILURE: Repository delete_task returned False")
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
    print("TASK CONTEXT CASCADE DELETION FIX VERIFICATION")
    print("=" * 70)

    test_results = []

    # Run all tests
    test_results.append(("SQLAlchemy Cascade", test_sqlalchemy_cascade_deletion()))
    test_results.append(("Database FK Cascade", test_database_foreign_key_cascade()))
    test_results.append(("Repository Manual Deletion", test_repository_manual_deletion_still_works()))

    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - CASCADE DELETION FIXES ARE WORKING!")
        print("✅ Both SQLAlchemy and database-level cascade deletion are properly configured")
        print("✅ Manual deletion continues to work as defensive programming")
    else:
        print("❌ SOME TESTS FAILED - CASCADE DELETION FIXES NEED INVESTIGATION")
    print("=" * 70)