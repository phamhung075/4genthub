"""
Comprehensive Test for Branch Cascade Deletion

This test verifies that all related records are properly deleted when a branch is deleted,
ensuring no foreign key constraint violations and no orphaned data.
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastmcp.task_management.infrastructure.database.models import (
    Base, ProjectGitBranch, Project, Task, TaskSubtask, TaskAssignee, 
    TaskDependency, TaskLabel, Label, BranchContext, TaskContext,
    ContextDelegation, ContextInheritanceCache
)
from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture  
def test_user_id():
    """Test user ID for isolation"""
    return "test-user-123"


@pytest.fixture
def git_branch_repo(test_user_id, test_db):
    """Create git branch repository with test user"""
    repo = ORMGitBranchRepository(user_id=test_user_id)
    # Mock the get_db_session method to return our test session
    repo.get_db_session = lambda: test_db
    return repo


@pytest.fixture
def sample_data(test_db, test_user_id):
    """Create comprehensive sample data with all possible relationships"""
    
    # Create project
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        name="Test Project",
        description="Test project for cascade deletion",
        user_id=test_user_id,
        status="active"
    )
    test_db.add(project)
    
    # Create branch
    branch_id = str(uuid.uuid4())
    branch = ProjectGitBranch(
        id=branch_id,
        project_id=project_id,
        name="test-branch",
        description="Test branch for cascade deletion",
        user_id=test_user_id,
        status="active",
        priority="medium"
    )
    test_db.add(branch)
    
    # Create tasks
    task_ids = []
    for i in range(3):
        task_id = str(uuid.uuid4())
        task_ids.append(task_id)
        task = Task(
            id=task_id,
            title=f"Test Task {i+1}",
            description=f"Test task {i+1} description",
            git_branch_id=branch_id,
            user_id=test_user_id,
            status="todo",
            priority="medium"
        )
        test_db.add(task)
    
    # Create subtasks
    for task_id in task_ids:
        for j in range(2):
            subtask = TaskSubtask(
                id=str(uuid.uuid4()),
                task_id=task_id,
                title=f"Subtask {j+1} for {task_id[:8]}",
                user_id=test_user_id,
                status="todo",
                priority="medium"
            )
            test_db.add(subtask)
    
    # Create task assignees
    for task_id in task_ids:
        assignee = TaskAssignee(
            id=str(uuid.uuid4()),
            task_id=task_id,
            assignee_id=f"assignee-{task_id[:8]}",
            user_id=test_user_id
        )
        test_db.add(assignee)
    
    # Create task dependencies (task1 depends on task2, task2 depends on task3)
    if len(task_ids) >= 2:
        dependency1 = TaskDependency(
            task_id=task_ids[0],
            depends_on_task_id=task_ids[1],
            user_id=test_user_id,
            dependency_type="blocks"
        )
        test_db.add(dependency1)
        
        if len(task_ids) >= 3:
            dependency2 = TaskDependency(
                task_id=task_ids[1],
                depends_on_task_id=task_ids[2],
                user_id=test_user_id,
                dependency_type="blocks"
            )
            test_db.add(dependency2)
    
    # Create label and task labels
    label = Label(
        id="test-label-1",
        name="test-label",
        user_id=test_user_id,
        description="Test label"
    )
    test_db.add(label)
    
    for task_id in task_ids:
        task_label = TaskLabel(
            task_id=task_id,
            label_id="test-label-1",
            user_id=test_user_id
        )
        test_db.add(task_label)
    
    # Create branch context
    branch_context_id = str(uuid.uuid4())
    branch_context = BranchContext(
        id=branch_context_id,
        branch_id=branch_id,
        user_id=test_user_id,
        data={"test": "branch context data"}
    )
    test_db.add(branch_context)
    
    # Create task contexts
    for task_id in task_ids:
        # Direct task context (parent_branch_id)
        task_context1 = TaskContext(
            id=str(uuid.uuid4()),
            task_id=task_id,
            parent_branch_id=branch_id,
            user_id=test_user_id,
            data={"test": f"task context for {task_id}"}
        )
        test_db.add(task_context1)
        
        # Indirect task context (parent_branch_context_id)
        task_context2 = TaskContext(
            id=str(uuid.uuid4()),
            task_id=task_id,
            parent_branch_context_id=branch_context_id,
            user_id=test_user_id,
            data={"test": f"indirect task context for {task_id}"}
        )
        test_db.add(task_context2)
    
    # Create context delegation records
    delegation = ContextDelegation(
        id=str(uuid.uuid4()),
        source_level="branch",
        source_id=branch_id,
        target_level="project",
        target_id=project_id,
        delegated_data={"test": "delegated data"},
        delegation_reason="Test delegation",
        trigger_type="manual",
        user_id=test_user_id
    )
    test_db.add(delegation)
    
    # Create context inheritance cache
    cache = ContextInheritanceCache(
        id=str(uuid.uuid4()),
        context_id=branch_id,
        context_level="branch",
        resolved_context={"test": "cached context"},
        dependencies_hash="test-hash",
        resolution_path="branch",
        cache_size_bytes=100,
        expires_at=datetime.now(timezone.utc),
        user_id=test_user_id
    )
    test_db.add(cache)
    
    test_db.commit()
    
    return {
        "project_id": project_id,
        "branch_id": branch_id,
        "task_ids": task_ids,
        "branch_context_id": branch_context_id
    }


@pytest.mark.asyncio
async def test_comprehensive_branch_cascade_deletion(test_db, git_branch_repo, sample_data):
    """Test that branch deletion properly cascades to all related records"""
    
    branch_id = sample_data["branch_id"]
    task_ids = sample_data["task_ids"]
    branch_context_id = sample_data["branch_context_id"]
    
    # Database session is already mocked in the fixture
    
    # Verify all data exists before deletion
    assert test_db.query(ProjectGitBranch).filter(ProjectGitBranch.id == branch_id).count() == 1
    assert test_db.query(Task).filter(Task.git_branch_id == branch_id).count() == 3
    assert test_db.query(TaskSubtask).filter(TaskSubtask.task_id.in_(task_ids)).count() == 6  # 3 tasks * 2 subtasks
    assert test_db.query(TaskAssignee).filter(TaskAssignee.task_id.in_(task_ids)).count() == 3
    assert test_db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).count() == 2
    assert test_db.query(TaskLabel).filter(TaskLabel.task_id.in_(task_ids)).count() == 3
    assert test_db.query(BranchContext).filter(BranchContext.branch_id == branch_id).count() == 1
    assert test_db.query(TaskContext).filter(TaskContext.parent_branch_id == branch_id).count() == 3
    assert test_db.query(TaskContext).filter(TaskContext.parent_branch_context_id == branch_context_id).count() == 3
    assert test_db.query(ContextDelegation).filter(ContextDelegation.source_id == branch_id).count() == 1
    assert test_db.query(ContextInheritanceCache).filter(
        ContextInheritanceCache.context_id == branch_id,
        ContextInheritanceCache.context_level == "branch"
    ).count() == 1
    
    # Perform cascade deletion
    result = await git_branch_repo.delete_branch(branch_id)
    assert result is True
    
    # Verify all related data has been deleted
    assert test_db.query(ProjectGitBranch).filter(ProjectGitBranch.id == branch_id).count() == 0
    assert test_db.query(Task).filter(Task.git_branch_id == branch_id).count() == 0
    assert test_db.query(TaskSubtask).filter(TaskSubtask.task_id.in_(task_ids)).count() == 0
    assert test_db.query(TaskAssignee).filter(TaskAssignee.task_id.in_(task_ids)).count() == 0
    assert test_db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).count() == 0
    assert test_db.query(TaskLabel).filter(TaskLabel.task_id.in_(task_ids)).count() == 0
    assert test_db.query(BranchContext).filter(BranchContext.branch_id == branch_id).count() == 0
    assert test_db.query(TaskContext).filter(TaskContext.parent_branch_id == branch_id).count() == 0
    assert test_db.query(TaskContext).filter(TaskContext.parent_branch_context_id == branch_context_id).count() == 0
    assert test_db.query(ContextDelegation).filter(ContextDelegation.source_id == branch_id).count() == 0
    assert test_db.query(ContextInheritanceCache).filter(
        ContextInheritanceCache.context_id == branch_id,
        ContextInheritanceCache.context_level == "branch"
    ).count() == 0
    
    # Verify that unrelated data is preserved (label should still exist)
    assert test_db.query(Label).filter(Label.id == "test-label-1").count() == 1


@pytest.mark.asyncio
async def test_user_isolation_in_cascade_deletion(test_db, sample_data):
    """Test that cascade deletion respects user isolation"""
    
    branch_id = sample_data["branch_id"]
    different_user_id = "different-user-456"
    
    # Create repository for different user
    different_user_repo = ORMGitBranchRepository(user_id=different_user_id)
    different_user_repo.get_db_session = lambda: test_db
    
    # Different user should not be able to delete the branch
    result = await different_user_repo.delete_branch(branch_id)
    assert result is False
    
    # Verify branch still exists
    assert test_db.query(ProjectGitBranch).filter(ProjectGitBranch.id == branch_id).count() == 1


@pytest.mark.asyncio
async def test_cascade_deletion_with_no_user_id(test_db, sample_data):
    """Test cascade deletion when no user_id is provided"""
    
    branch_id = sample_data["branch_id"]
    
    # Create repository without user_id
    no_user_repo = ORMGitBranchRepository(user_id=None)
    no_user_repo.get_db_session = lambda: test_db
    
    # Should still work (for backward compatibility) but without user isolation
    result = await no_user_repo.delete_branch(branch_id)
    assert result is True
    
    # Verify branch is deleted
    assert test_db.query(ProjectGitBranch).filter(ProjectGitBranch.id == branch_id).count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])