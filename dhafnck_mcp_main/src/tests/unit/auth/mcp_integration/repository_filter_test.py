"""
Tests for user-filtered repository wrappers
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastmcp.auth.mcp_integration.repository_filter import (
    UserFilteredRepository,
    UserFilteredTaskRepository,
    UserFilteredProjectRepository,
    UserFilteredContextRepository,
    create_user_filtered_repository
)


class ConcreteFilteredRepository(UserFilteredRepository):
    """Concrete implementation for testing abstract base class"""
    
    def find_by_id(self, entity_id):
        return None
    
    def find_all(self, **filters):
        return []
    
    def save(self, entity):
        return entity
    
    def delete(self, entity_id):
        return False


class TestUserFilteredRepository:
    """Test suite for base UserFilteredRepository functionality"""
    
    def test_initialization(self):
        """Test repository initialization"""
        base_repo = Mock()
        repo = ConcreteFilteredRepository(base_repo, "user_id")
        
        assert repo._base_repository == base_repo
        assert repo._user_id_field == "user_id"
    
    def test_get_current_user_id_with_user(self):
        """Test getting current user ID when authenticated"""
        repo = ConcreteFilteredRepository(Mock())
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            user_id = repo._get_current_user_id()
            assert user_id == "user-123"
    
    def test_get_current_user_id_without_user(self):
        """Test getting current user ID when not authenticated"""
        repo = ConcreteFilteredRepository(Mock())
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value=None):
            with pytest.raises(RuntimeError, match="No authenticated user in context"):
                repo._get_current_user_id()
    
    def test_add_user_filter(self):
        """Test adding user filter to existing filters"""
        repo = ConcreteFilteredRepository(Mock())
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            # Test with existing filters
            filters = repo._add_user_filter({"status": "active"})
            assert filters == {"status": "active", "user_id": "user-123"}
            
            # Test with None filters
            filters = repo._add_user_filter(None)
            assert filters == {"user_id": "user-123"}
            
            # Test with empty filters
            filters = repo._add_user_filter({})
            assert filters == {"user_id": "user-123"}


class TestUserFilteredTaskRepository:
    """Test suite for UserFilteredTaskRepository"""
    
    @pytest.fixture
    def base_repo(self):
        return Mock()
    
    @pytest.fixture
    def task_repo(self, base_repo):
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            return UserFilteredTaskRepository(base_repo)
    
    def test_find_by_id_own_task(self, task_repo, base_repo):
        """Test finding task that belongs to current user"""
        task = Mock(id="task-1", user_id="user-123")
        base_repo.find_by_id.return_value = task
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.find_by_id("task-1")
            assert result == task
            base_repo.find_by_id.assert_called_once_with("task-1")
    
    def test_find_by_id_other_users_task(self, task_repo, base_repo):
        """Test finding task that belongs to another user"""
        task = Mock(id="task-1", user_id="other-user")
        base_repo.find_by_id.return_value = task
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.find_by_id("task-1")
            assert result is None
    
    def test_find_by_id_not_found(self, task_repo, base_repo):
        """Test finding non-existent task"""
        base_repo.find_by_id.return_value = None
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.find_by_id("task-1")
            assert result is None
    
    def test_find_all(self, task_repo, base_repo):
        """Test finding all tasks with user filter"""
        tasks = [Mock(user_id="user-123"), Mock(user_id="user-123")]
        base_repo.find_all.return_value = tasks
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.find_all(status="active")
            assert result == tasks
            base_repo.find_all.assert_called_once_with(status="active", user_id="user-123")
    
    def test_find_by_git_branch_id(self, task_repo, base_repo):
        """Test finding tasks by git branch ID"""
        tasks = [
            Mock(user_id="user-123"),
            Mock(user_id="other-user"),
            Mock(user_id="user-123")
        ]
        base_repo.find_by_git_branch_id.return_value = tasks
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.find_by_git_branch_id("branch-1")
            assert len(result) == 2
            assert all(task.user_id == "user-123" for task in result)
    
    def test_save_new_task(self, task_repo, base_repo):
        """Test saving a new task"""
        task = Mock(id=None)
        saved_task = Mock(id="task-1", user_id="user-123")
        base_repo.save.return_value = saved_task
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.save(task)
            assert result == saved_task
            assert task.user_id == "user-123"
            base_repo.save.assert_called_once_with(task)
    
    def test_save_existing_task_own(self, task_repo, base_repo):
        """Test saving an existing task that belongs to user"""
        task = Mock(id="task-1", user_id="user-123")
        base_repo.save.return_value = task
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = task_repo.save(task)
            assert result == task
            base_repo.save.assert_called_once_with(task)
    
    def test_save_existing_task_other_user(self, task_repo, base_repo):
        """Test saving an existing task that belongs to another user"""
        task = Mock(id="task-1", user_id="other-user")
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            with pytest.raises(RuntimeError, match="Cannot save task belonging to another user"):
                task_repo.save(task)
    
    def test_delete_own_task(self, task_repo, base_repo):
        """Test deleting task that belongs to user"""
        task = Mock(id="task-1", user_id="user-123")
        base_repo.find_by_id.return_value = task
        base_repo.delete.return_value = True
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            with patch.object(task_repo, 'find_by_id', return_value=task):
                result = task_repo.delete("task-1")
                assert result is True
                base_repo.delete.assert_called_once_with("task-1")
    
    def test_delete_other_users_task(self, task_repo, base_repo):
        """Test deleting task that belongs to another user"""
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            with patch.object(task_repo, 'find_by_id', return_value=None):
                result = task_repo.delete("task-1")
                assert result is False
                base_repo.delete.assert_not_called()


class TestUserFilteredProjectRepository:
    """Test suite for UserFilteredProjectRepository"""
    
    @pytest.fixture
    def base_repo(self):
        return Mock()
    
    @pytest.fixture
    def project_repo(self, base_repo):
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            return UserFilteredProjectRepository(base_repo)
    
    def test_find_by_id_own_project(self, project_repo, base_repo):
        """Test finding project that belongs to current user"""
        project = Mock(id="proj-1", user_id="user-123")
        base_repo.find_by_id.return_value = project
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = project_repo.find_by_id("proj-1")
            assert result == project
    
    def test_save_new_project(self, project_repo, base_repo):
        """Test saving a new project"""
        project = Mock(id=None)
        saved_project = Mock(id="proj-1", user_id="user-123")
        base_repo.save.return_value = saved_project
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = project_repo.save(project)
            assert result == saved_project
            assert project.user_id == "user-123"


class TestUserFilteredContextRepository:
    """Test suite for UserFilteredContextRepository"""
    
    @pytest.fixture
    def base_repo(self):
        return Mock()
    
    @pytest.fixture
    def context_repo(self, base_repo):
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            return UserFilteredContextRepository(base_repo)
    
    def test_find_by_id_own_context(self, context_repo, base_repo):
        """Test finding context that belongs to current user"""
        context = Mock(id="ctx-1", user_id="user-123")
        base_repo.find_by_id.return_value = context
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = context_repo.find_by_id("ctx-1")
            assert result == context
    
    def test_find_by_id_global_context_with_user(self, context_repo, base_repo):
        """Test finding global context that belongs to user"""
        # Critical fix: Global contexts now have user_id for user isolation
        context = Mock(id="global_singleton", user_id="user-123", level="global")
        base_repo.find_by_id.return_value = context
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = context_repo.find_by_id("global_singleton")
            assert result == context
    
    def test_find_by_id_other_users_global_context(self, context_repo, base_repo):
        """Test finding global context that belongs to another user"""
        context = Mock(id="global_singleton", user_id="other-user", level="global")
        base_repo.find_by_id.return_value = context
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = context_repo.find_by_id("global_singleton")
            assert result is None
    
    def test_save_global_context(self, context_repo, base_repo):
        """Test saving global context sets user_id"""
        context = Mock(id="global_singleton", level="global")
        saved_context = Mock(id="global_singleton", user_id="user-123", level="global")
        base_repo.save.return_value = saved_context
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = context_repo.save(context)
            assert result == saved_context
            assert context.user_id == "user-123"
            base_repo.save.assert_called_once_with(context)
    
    def test_delete_global_context_not_allowed(self, context_repo, base_repo):
        """Test deleting global context is not allowed"""
        context = Mock(id="global_singleton", user_id="user-123", level="global")
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            with patch.object(context_repo, 'find_by_id', return_value=context):
                result = context_repo.delete("global_singleton")
                assert result is False
                base_repo.delete.assert_not_called()
    
    def test_find_all_includes_user_and_global_contexts(self, context_repo, base_repo):
        """Test find_all returns both user contexts and global contexts"""
        user_contexts = [Mock(user_id="user-123")]
        global_contexts = [Mock(user_id=None)]
        
        def side_effect(**kwargs):
            if kwargs.get('user_id') == "user-123":
                return user_contexts
            elif kwargs.get('user_id') is None:
                return global_contexts
            return []
        
        base_repo.find_all.side_effect = side_effect
        
        with patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id', return_value="user-123"):
            result = context_repo.find_all()
            assert len(result) == 2
            assert result == user_contexts + global_contexts


class TestCreateUserFilteredRepository:
    """Test suite for repository factory function"""
    
    def test_create_task_repository(self):
        """Test creating task repository"""
        base_repo = Mock()
        repo = create_user_filtered_repository('task', base_repo)
        assert isinstance(repo, UserFilteredTaskRepository)
        assert repo._base_repository == base_repo
    
    def test_create_project_repository(self):
        """Test creating project repository"""
        base_repo = Mock()
        repo = create_user_filtered_repository('project', base_repo)
        assert isinstance(repo, UserFilteredProjectRepository)
        assert repo._base_repository == base_repo
    
    def test_create_context_repository(self):
        """Test creating context repository"""
        base_repo = Mock()
        repo = create_user_filtered_repository('context', base_repo)
        assert isinstance(repo, UserFilteredContextRepository)
        assert repo._base_repository == base_repo
    
    def test_create_with_custom_user_id_field(self):
        """Test creating repository with custom user_id field"""
        base_repo = Mock()
        repo = create_user_filtered_repository('task', base_repo, 'owner_id')
        assert repo._user_id_field == 'owner_id'
    
    def test_create_unknown_type(self):
        """Test creating repository with unknown type"""
        base_repo = Mock()
        with pytest.raises(ValueError, match="Unknown repository type: invalid"):
            create_user_filtered_repository('invalid', base_repo)