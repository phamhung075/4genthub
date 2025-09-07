#!/usr/bin/env python3
"""Integration test for context operations after schema fix"""

import pytest
import uuid
from datetime import datetime
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from fastmcp.task_management.infrastructure.database.models import (
    GlobalContext, ProjectContext, BranchContext, TaskContext,
    GLOBAL_SINGLETON_UUID
)
from sqlalchemy.orm import Session


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db_config = get_db_config()
    session = Session(db_config.get_engine())
    yield session
    session.rollback()
    session.close()


def test_global_context_operations(db_session):
    """Test global context CRUD operations"""
    # Check global singleton exists
    global_ctx = db_session.query(GlobalContext).filter(
        GlobalContext.id == GLOBAL_SINGLETON_UUID
    ).first()
    
    if not global_ctx:
        # Create if doesn't exist
        global_ctx = GlobalContext(
            id=GLOBAL_SINGLETON_UUID,
            organization_id="00000000-0000-0000-0000-000000000002"
        )
        db_session.add(global_ctx)
        db_session.commit()
    
    assert global_ctx is not None
    assert global_ctx.id == GLOBAL_SINGLETON_UUID
    print("✅ Global context operations working")


def test_project_context_operations(db_session):
    """Test project context CRUD operations"""
    # Create a project context
    project_ctx = ProjectContext(
        id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        parent_global_id=GLOBAL_SINGLETON_UUID,
        data={"test": "data"},
        team_preferences={"theme": "dark"}
    )
    
    db_session.add(project_ctx)
    db_session.commit()
    
    # Query it back
    found = db_session.query(ProjectContext).filter(
        ProjectContext.id == project_ctx.id
    ).first()
    
    assert found is not None
    assert found.data == {"test": "data"}
    assert found.team_preferences == {"theme": "dark"}
    
    # Clean up
    db_session.delete(found)
    db_session.commit()
    
    print("✅ Project context operations working")


def test_branch_context_operations(db_session):
    """Test branch context CRUD operations"""
    # Create a project context first
    project_ctx = ProjectContext(
        id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        parent_global_id=GLOBAL_SINGLETON_UUID
    )
    db_session.add(project_ctx)
    db_session.commit()
    
    # Create a branch context
    branch_ctx = BranchContext(
        id=str(uuid.uuid4()),
        branch_id=str(uuid.uuid4()),
        parent_project_id=project_ctx.id,
        data={"branch": "test"},
        feature_flags={"new_feature": True}
    )
    
    db_session.add(branch_ctx)
    db_session.commit()
    
    # Query it back
    found = db_session.query(BranchContext).filter(
        BranchContext.id == branch_ctx.id
    ).first()
    
    assert found is not None
    assert found.data == {"branch": "test"}
    assert found.feature_flags == {"new_feature": True}
    assert found.parent_project_id == project_ctx.id
    
    # Clean up
    db_session.delete(found)
    db_session.delete(project_ctx)
    db_session.commit()
    
    print("✅ Branch context operations working")


def test_task_context_operations(db_session):
    """Test task context CRUD operations"""
    # Create hierarchy
    project_ctx = ProjectContext(
        id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        parent_global_id=GLOBAL_SINGLETON_UUID
    )
    db_session.add(project_ctx)
    
    branch_ctx = BranchContext(
        id=str(uuid.uuid4()),
        branch_id=str(uuid.uuid4()),
        parent_project_id=project_ctx.id
    )
    db_session.add(branch_ctx)
    db_session.commit()
    
    # Create a task context
    task_ctx = TaskContext(
        id=str(uuid.uuid4()),
        task_id=str(uuid.uuid4()),
        parent_branch_id=branch_ctx.branch_id,
        parent_branch_context_id=branch_ctx.id,
        data={"task": "implementation"},
        execution_context={"status": "running"}
    )
    
    db_session.add(task_ctx)
    db_session.commit()
    
    # Query it back
    found = db_session.query(TaskContext).filter(
        TaskContext.id == task_ctx.id
    ).first()
    
    assert found is not None
    assert found.data == {"task": "implementation"}
    assert found.execution_context == {"status": "running"}
    assert found.parent_branch_context_id == branch_ctx.id
    
    # Clean up
    db_session.delete(found)
    db_session.delete(branch_ctx)
    db_session.delete(project_ctx)
    db_session.commit()
    
    print("✅ Task context operations working")


def test_relationship_navigation(db_session):
    """Test navigating relationships between contexts"""
    # Create full hierarchy
    global_ctx = db_session.query(GlobalContext).filter(
        GlobalContext.id == GLOBAL_SINGLETON_UUID
    ).first()
    
    if not global_ctx:
        global_ctx = GlobalContext(
            id=GLOBAL_SINGLETON_UUID,
            organization_id="00000000-0000-0000-0000-000000000002"
        )
        db_session.add(global_ctx)
    
    project_ctx = ProjectContext(
        id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        parent_global_id=global_ctx.id
    )
    db_session.add(project_ctx)
    
    branch_ctx = BranchContext(
        id=str(uuid.uuid4()),
        branch_id=str(uuid.uuid4()),
        parent_project_id=project_ctx.id
    )
    db_session.add(branch_ctx)
    db_session.commit()
    
    # Navigate relationships
    # From global to project
    projects = db_session.query(ProjectContext).filter(
        ProjectContext.parent_global_id == global_ctx.id
    ).all()
    assert len(projects) >= 1
    
    # From project to branch
    branches = db_session.query(BranchContext).filter(
        BranchContext.parent_project_id == project_ctx.id
    ).all()
    assert len(branches) == 1
    assert branches[0].id == branch_ctx.id
    
    # Clean up
    db_session.delete(branch_ctx)
    db_session.delete(project_ctx)
    db_session.commit()
    
    print("✅ Relationship navigation working")


if __name__ == "__main__":
    # Run tests directly
    import sys
    import os
    
    # Set database type for testing
    os.environ['DATABASE_TYPE'] = os.environ.get('DATABASE_TYPE', 'sqlite')
    
    try:
        db_config = get_db_config()
        session = Session(db_config.get_engine())
        
        print("\n🧪 Running Context Operations Integration Tests\n")
        
        test_global_context_operations(session)
        test_project_context_operations(session)
        test_branch_context_operations(session)
        test_task_context_operations(session)
        test_relationship_navigation(session)
        
        print("\n✅ All context operation tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()