#!/usr/bin/env python3
"""
Unit tests for ContextIDDetector using ORM

Tests the ID detection functionality that determines whether a given ID
is a project ID, git branch ID, or task ID.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from fastmcp.task_management.interface.controllers.context_id_detector_orm import ContextIDDetector
from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch, Task


class TestContextIDDetectorORM:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test cases for ContextIDDetector using ORM"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session for testing"""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        return session
    
    def test_detect_project_id(self, mock_session):
        """Test detection of project ID"""
        project_id = "ae88dd28-1905-444d-81d0-e338297239a4"
        
        # Create mock project
        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        
        # Setup mock to return project for project query, None for others
        def query_side_effect(model):
            query_mock = Mock()
            if model == Project:
                query_mock.filter_by.return_value.first.return_value = mock_project
            else:
                query_mock.filter_by.return_value.first.return_value = None
            return query_mock
        
        mock_session.query.side_effect = query_side_effect
        
        # Test with mocked session
        with patch('fastmcp.task_management.interface.controllers.context_id_detector_orm.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            id_type, associated_project_id = ContextIDDetector.detect_id_type(project_id)
        
        # Assert
        assert id_type == "project"
        assert associated_project_id == project_id
    
    def test_detect_git_branch_id(self, mock_session):
        """Test detection of git branch ID"""
        branch_id = "529a5847-ceb7-4b06-9fc4-472865ec40d1"
        project_id = "ae88dd28-1905-444d-81d0-e338297239a4"
        
        # Create mock branch
        mock_branch = Mock(spec=ProjectGitBranch)
        mock_branch.id = branch_id
        mock_branch.project_id = project_id
        
        # Setup mock to return branch for branch query, None for others
        def query_side_effect(model):
            query_mock = Mock()
            if model == ProjectGitBranch:
                query_mock.filter_by.return_value.first.return_value = mock_branch
            else:
                query_mock.filter_by.return_value.first.return_value = None
            return query_mock
        
        mock_session.query.side_effect = query_side_effect
        
        # Test with mocked session
        with patch('fastmcp.task_management.interface.controllers.context_id_detector_orm.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            id_type, associated_project_id = ContextIDDetector.detect_id_type(branch_id)
        
        # Assert
        assert id_type == "git_branch"
        assert associated_project_id == project_id
    
    def test_detect_task_id(self, mock_session):
        """Test detection of task ID"""
        task_id = "d00a377e-535d-4518-9d2f-c952c9af8b2c"
        branch_id = "529a5847-ceb7-4b06-9fc4-472865ec40d1"
        project_id = "ae88dd28-1905-444d-81d0-e338297239a4"
        
        # Create mock task and branch
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = branch_id
        
        mock_branch = Mock(spec=ProjectGitBranch)
        mock_branch.id = branch_id
        mock_branch.project_id = project_id
        
        # Setup mock to return task for task query, branch for second query
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            query_mock = Mock()
            
            if call_count < 3 and model in [Project, ProjectGitBranch]:
                # First queries for project and branch return None
                query_mock.filter_by.return_value.first.return_value = None
            elif model == Task:
                # Task query returns the task
                query_mock.filter_by.return_value.first.return_value = mock_task
            elif model == ProjectGitBranch and call_count >= 3:
                # Second branch query (to get project from task's branch) returns branch
                query_mock.filter_by.return_value.first.return_value = mock_branch
            else:
                query_mock.filter_by.return_value.first.return_value = None
            
            call_count += 1
            return query_mock
        
        mock_session.query.side_effect = query_side_effect
        
        # Test with mocked session
        with patch('fastmcp.task_management.interface.controllers.context_id_detector_orm.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            id_type, associated_project_id = ContextIDDetector.detect_id_type(task_id)
        
        # Assert
        assert id_type == "task"
        assert associated_project_id == project_id
    
    def test_detect_unknown_id(self, mock_session):
        """Test detection of unknown ID"""
        unknown_id = "00000000-0000-0000-0000-000000000000"
        
        # Setup mock to return None for all queries
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Test with mocked session
        with patch('fastmcp.task_management.interface.controllers.context_id_detector_orm.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            id_type, associated_project_id = ContextIDDetector.detect_id_type(unknown_id)
        
        # Assert
        assert id_type == "unknown"
        assert associated_project_id is None
    
    def test_get_context_level_for_project_id(self):
        """Test getting context level for project ID"""
        project_id = "ae88dd28-1905-444d-81d0-e338297239a4"
        
        # Mock detect_id_type to return project
        with patch.object(ContextIDDetector, 'detect_id_type', return_value=("project", project_id)):
            level = ContextIDDetector.get_context_level_for_id(project_id)
        
        assert level == "project"
    
    def test_get_context_level_for_git_branch_id(self):
        """Test getting context level for git branch ID"""
        branch_id = "529a5847-ceb7-4b06-9fc4-472865ec40d1"
        project_id = "ae88dd28-1905-444d-81d0-e338297239a4"
        
        # Mock detect_id_type to return git_branch
        with patch.object(ContextIDDetector, 'detect_id_type', return_value=("git_branch", project_id)):
            level = ContextIDDetector.get_context_level_for_id(branch_id)
        
        assert level == "task"
    
    def test_get_context_level_for_task_id(self):
        """Test getting context level for task ID"""
        task_id = "d00a377e-535d-4518-9d2f-c952c9af8b2c"
        project_id = "ae88dd28-1905-444d-81d0-e338297239a4"
        
        # Mock detect_id_type to return task
        with patch.object(ContextIDDetector, 'detect_id_type', return_value=("task", project_id)):
            level = ContextIDDetector.get_context_level_for_id(task_id)
        
        assert level == "task"
    
    def test_get_context_level_for_unknown_id(self):
        """Test getting context level for unknown ID (defaults to task)"""
        unknown_id = "00000000-0000-0000-0000-000000000000"
        
        # Mock detect_id_type to return unknown
        with patch.object(ContextIDDetector, 'detect_id_type', return_value=("unknown", None)):
            level = ContextIDDetector.get_context_level_for_id(unknown_id)
        
        assert level == "task"
    
    def test_error_handling(self, mock_session):
        """Test error handling in ID detection"""
        error_id = "error-id"
        
        # Setup mock to raise an exception
        mock_session.query.side_effect = Exception("Database error")
        
        # Test with mocked session
        with patch('fastmcp.task_management.interface.controllers.context_id_detector_orm.get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            id_type, associated_project_id = ContextIDDetector.detect_id_type(error_id)
        
        # Should return unknown on error
        assert id_type == "unknown"
        assert associated_project_id is None
    
    def test_empty_context_id(self):
        """Test detection with empty or None context ID"""
        # Test with None
        id_type, associated_project_id = ContextIDDetector.detect_id_type(None)
        assert id_type == "unknown"
        assert associated_project_id is None
        
        # Test with empty string
        id_type, associated_project_id = ContextIDDetector.detect_id_type("")
        assert id_type == "unknown"
        assert associated_project_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])