"""
Test suite for GitBranch domain entity

Tests the git branch entity behavior and validation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.value_objects import (
    GitBranchID,
    ProjectID,
    GitBranchName,
    UserID,
    TaskID
)
from fastmcp.task_management.domain.exceptions import ValidationError


class TestGitBranchEntity:
    """Test suite for GitBranch domain entity"""

    def test_create_minimal_git_branch(self):
        """Test creating git branch with minimal required fields"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/test-branch"),
            user_id=UserID("user123")
        )
        
        assert branch.id is not None
        assert branch.project_id is not None
        assert branch.git_branch_name.value == "feature/test-branch"
        assert branch.user_id.value == "user123"
        assert branch.git_branch_description is None
        assert branch.is_active is True  # Default

    def test_create_git_branch_with_description(self):
        """Test creating git branch with description"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/user-authentication"),
            user_id=UserID("user123"),
            git_branch_description="Implement JWT-based authentication system"
        )
        
        assert branch.git_branch_description == "Implement JWT-based authentication system"

    def test_valid_branch_name_formats(self):
        """Test various valid branch name formats"""
        valid_names = [
            "main",
            "develop",
            "feature/new-feature",
            "bugfix/issue-123",
            "hotfix/security-patch",
            "release/v1.2.3",
            "feat/ABC-123-new-feature",
            "test_branch_123",
            "user/john/experiment",
            "deps/update-packages"
        ]
        
        for name in valid_names:
            branch = GitBranch(
                id=GitBranchID(str(uuid4())),
                project_id=ProjectID(str(uuid4())),
                git_branch_name=GitBranchName(name),
                user_id=UserID("user123")
            )
            assert branch.git_branch_name.value == name

    def test_invalid_branch_names(self):
        """Test invalid branch name formats"""
        invalid_names = [
            "",  # Empty
            " ",  # Whitespace only
            "feature branch",  # Contains space
            "feature@branch",  # Invalid character
            "feature#branch",  # Invalid character
            "feature:branch",  # Invalid character
            ".hidden",  # Starts with dot
            "branch.",  # Ends with dot
            "a" * 256,  # Too long (assuming 255 char limit)
            "feature//double-slash",  # Double slash
            "/leading-slash",  # Leading slash
            "trailing-slash/",  # Trailing slash
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                GitBranchName(name)

    def test_git_branch_timestamps(self):
        """Test timestamp fields"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/timestamps"),
            user_id=UserID("user123")
        )
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        branch.created_at = now
        branch.updated_at = now
        
        assert branch.created_at == now
        assert branch.updated_at == now

    def test_git_branch_active_status(self):
        """Test branch active/inactive status"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/active-test"),
            user_id=UserID("user123")
        )
        
        # Default is active
        assert branch.is_active is True
        
        # Archive branch
        branch.archive()
        assert branch.is_active is False
        assert branch.archived_at is not None
        
        # Restore branch
        branch.restore()
        assert branch.is_active is True
        assert branch.archived_at is None

    def test_git_branch_task_management(self):
        """Test managing tasks in branch"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/tasks"),
            user_id=UserID("user123")
        )
        
        # Add task IDs
        task1 = TaskID(str(uuid4()))
        task2 = TaskID(str(uuid4()))
        task3 = TaskID(str(uuid4()))
        
        branch.add_task(task1)
        branch.add_task(task2)
        branch.add_task(task3)
        
        assert len(branch.task_ids) == 3
        assert task1 in branch.task_ids
        assert task2 in branch.task_ids
        assert task3 in branch.task_ids
        
        # Remove task
        branch.remove_task(task2)
        assert len(branch.task_ids) == 2
        assert task2 not in branch.task_ids

    def test_git_branch_duplicate_task_prevention(self):
        """Test preventing duplicate task additions"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/no-duplicates"),
            user_id=UserID("user123")
        )
        
        task_id = TaskID(str(uuid4()))
        
        branch.add_task(task_id)
        branch.add_task(task_id)  # Try to add again
        
        # Should only have one instance
        assert len(branch.task_ids) == 1

    def test_git_branch_agent_assignments(self):
        """Test agent assignments to branch"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/agents"),
            user_id=UserID("user123")
        )
        
        # Assign agents
        branch.assign_agent("coding-agent")
        branch.assign_agent("test-orchestrator-agent")
        branch.assign_agent("security-auditor-agent")
        
        assert len(branch.assigned_agents) == 3
        assert "coding-agent" in branch.assigned_agents
        assert "test-orchestrator-agent" in branch.assigned_agents
        
        # Unassign agent
        branch.unassign_agent("test-orchestrator-agent")
        assert len(branch.assigned_agents) == 2
        assert "test-orchestrator-agent" not in branch.assigned_agents

    def test_git_branch_statistics(self):
        """Test branch statistics tracking"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/stats"),
            user_id=UserID("user123")
        )
        
        # Set statistics
        branch.total_tasks = 10
        branch.completed_tasks = 7
        branch.in_progress_tasks = 2
        branch.blocked_tasks = 1
        
        assert branch.total_tasks == 10
        assert branch.completed_tasks == 7
        assert branch.completion_percentage == 70
        
        # Test edge cases
        branch.total_tasks = 0
        assert branch.completion_percentage == 0

    def test_git_branch_metadata(self):
        """Test branch metadata"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/metadata"),
            user_id=UserID("user123"),
            metadata={
                "jira_ticket": "PROJ-123",
                "target_release": "v2.0",
                "feature_flag": "new_auth_system"
            }
        )
        
        assert branch.metadata["jira_ticket"] == "PROJ-123"
        assert branch.metadata["target_release"] == "v2.0"
        assert branch.metadata["feature_flag"] == "new_auth_system"

    def test_git_branch_serialization(self):
        """Test branch serialization to dict"""
        branch_id = GitBranchID(str(uuid4()))
        project_id = ProjectID(str(uuid4()))
        
        branch = GitBranch(
            id=branch_id,
            project_id=project_id,
            git_branch_name=GitBranchName("feature/serialization"),
            user_id=UserID("user123"),
            git_branch_description="Test serialization"
        )
        
        # Add some data
        branch.assign_agent("coding-agent")
        branch.add_task(TaskID(str(uuid4())))
        branch.total_tasks = 5
        branch.completed_tasks = 2
        
        branch_dict = branch.to_dict()
        
        assert branch_dict["id"] == branch_id.value
        assert branch_dict["project_id"] == project_id.value
        assert branch_dict["git_branch_name"] == "feature/serialization"
        assert branch_dict["user_id"] == "user123"
        assert branch_dict["git_branch_description"] == "Test serialization"
        assert branch_dict["is_active"] is True
        assert "coding-agent" in branch_dict["assigned_agents"]
        assert len(branch_dict["task_ids"]) == 1
        assert branch_dict["total_tasks"] == 5
        assert branch_dict["completed_tasks"] == 2

    def test_git_branch_stale_detection(self):
        """Test detecting stale branches"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/old-feature"),
            user_id=UserID("user123")
        )
        
        # Set old updated_at
        branch.updated_at = datetime.now(timezone.utc) - timedelta(days=45)
        
        # Check if stale (assuming 30 days threshold)
        assert branch.is_stale(days_threshold=30) is True
        assert branch.is_stale(days_threshold=60) is False
        
        # Recent branch
        branch.updated_at = datetime.now(timezone.utc) - timedelta(days=5)
        assert branch.is_stale(days_threshold=30) is False

    def test_git_branch_merge_status(self):
        """Test branch merge status tracking"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/merge-test"),
            user_id=UserID("user123")
        )
        
        # Default not merged
        assert branch.is_merged is False
        assert branch.merged_at is None
        
        # Mark as merged
        branch.mark_as_merged()
        assert branch.is_merged is True
        assert branch.merged_at is not None
        
        # Should also archive when merged
        assert branch.is_active is False

    def test_git_branch_protected_names(self):
        """Test protected branch names have special handling"""
        protected_names = ["main", "master", "develop", "production"]
        
        for name in protected_names:
            branch = GitBranch(
                id=GitBranchID(str(uuid4())),
                project_id=ProjectID(str(uuid4())),
                git_branch_name=GitBranchName(name),
                user_id=UserID("user123")
            )
            
            # Protected branches should have special flag
            assert branch.is_protected is True

    def test_git_branch_name_case_sensitivity(self):
        """Test branch name case handling"""
        branch1 = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("Feature/TestCase"),
            user_id=UserID("user123")
        )
        
        branch2 = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/testcase"),
            user_id=UserID("user123")
        )
        
        # Names should be preserved as-is
        assert branch1.git_branch_name.value == "Feature/TestCase"
        assert branch2.git_branch_name.value == "feature/testcase"
        assert branch1.git_branch_name.value != branch2.git_branch_name.value