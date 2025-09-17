"""
Test suite for test_helpers module
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid

from tests.unit.infrastructure.database.test_helpers import (
    DatabaseIsolation,
    DbTestAdapter,
    setup_test_database,
    cleanup_test_database,
    create_isolated_session,
    FixtureManager,
    create_task_fixture,
    create_project_fixture,
    create_agent_fixture,
    create_context_fixture,
    cleanup_fixtures,
    get_fixture_by_id,
    list_fixtures,
    MockRepository,
    MockRepositoryFactory,
    create_mock_task_repository,
    create_mock_project_repository,
    create_mock_agent_repository,
    create_mock_context_repository,
    configure_mock_responses,
    DataFactory,
    DataGenerator,
    generate_task_data,
    generate_project_data,
    generate_agent_data,
    generate_context_data,
    generate_subtask_data,
    generate_bulk_data,
    ensure_data_consistency,
    validate_generated_data
)


class TestDatabaseIsolation:
    """Test DatabaseIsolation class"""
    
    def test_create_test_database(self):
        """Test creating an isolated test database"""
        isolation = DatabaseIsolation()
        test_db = isolation.create_test_database("test_db")
        
        assert isinstance(test_db, DbTestAdapter)
        assert test_db.database_name == "test_db"
        assert test_db.is_isolated == True
        assert test_db.is_ready == True
        assert test_db.is_clean == True
        assert "sqlite:///" in test_db.connection_string
        assert "test_db" in test_db.connection_string
    
    def test_cleanup_database(self):
        """Test database cleanup"""
        isolation = DatabaseIsolation()
        test_db = isolation.create_test_database("cleanup_test")
        
        # Add some test data
        test_db.insert_test_data({"tasks": [{"id": "1", "title": "Test"}]})
        assert not test_db.is_clean
        
        # Cleanup
        isolation.cleanup_database(test_db)
        assert test_db.is_clean
        assert test_db.query_all("tasks") == []
    
    def test_get_production_connection_string(self):
        """Test getting production connection string"""
        isolation = DatabaseIsolation()
        
        # Test with environment variable
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://prod"}):
            isolation = DatabaseIsolation()
            assert isolation.get_production_connection_string() == "postgresql://prod"
        
        # Test without environment variable
        with patch.dict(os.environ, {}, clear=True):
            isolation = DatabaseIsolation()
            assert isolation.get_production_connection_string() == "sqlite:///production.db"


class TestDbTestAdapter:
    """Test DbTestAdapter class"""
    
    @pytest.fixture
    def adapter(self):
        """Create test adapter"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        adapter = DbTestAdapter(db_path)
        yield adapter
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def test_initialization(self, adapter):
        """Test adapter initialization"""
        assert adapter.database_name == "test"
        assert adapter.is_isolated == False
        assert adapter.is_ready == False
        assert adapter.is_clean == True
        assert "sqlite:///" in adapter.connection_string
    
    def test_get_session(self, adapter):
        """Test getting database session"""
        session = adapter.get_session()
        assert session is not None
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        assert hasattr(session, 'close')
    
    def test_insert_and_query_test_data(self, adapter):
        """Test inserting and querying test data"""
        # Insert data
        test_data = {
            "tasks": [
                {"id": "1", "title": "Task 1"},
                {"id": "2", "title": "Task 2"}
            ],
            "projects": [
                {"id": "p1", "name": "Project 1"}
            ]
        }
        adapter.insert_test_data(test_data)
        
        assert not adapter.is_clean
        
        # Query all
        tasks = adapter.query_all("tasks")
        assert len(tasks) == 2
        assert tasks[0]["title"] == "Task 1"
        
        projects = adapter.query_all("projects")
        assert len(projects) == 1
        assert projects[0]["name"] == "Project 1"
        
        # Query by ID
        task = adapter.query_by_id("tasks", "1")
        assert task is not None
        assert task["title"] == "Task 1"
        
        missing = adapter.query_by_id("tasks", "999")
        assert missing is None
    
    def test_delete_all(self, adapter):
        """Test deleting all records from a table"""
        # Insert data
        adapter.insert_test_data({"tasks": [{"id": "1"}, {"id": "2"}]})
        assert len(adapter.query_all("tasks")) == 2
        
        # Delete all
        adapter.delete_all("tasks")
        assert len(adapter.query_all("tasks")) == 0
    
    def test_reset(self, adapter):
        """Test resetting database"""
        # Insert data
        adapter.insert_test_data({
            "tasks": [{"id": "1"}],
            "projects": [{"id": "p1"}]
        })
        assert not adapter.is_clean
        
        # Reset
        adapter.reset()
        assert adapter.is_clean
        assert adapter.query_all("tasks") == []
        assert adapter.query_all("projects") == []
    
    def test_transaction_context_manager(self, adapter):
        """Test transaction context manager"""
        # Test successful transaction
        with adapter.transaction() as session:
            assert session is not None
            # Transaction should complete successfully
        
        # Test failed transaction
        with pytest.raises(Exception):
            with adapter.transaction() as session:
                raise Exception("Test error")


class TestDatabaseHelperFunctions:
    """Test database helper functions"""
    
    def test_setup_test_database(self):
        """Test setting up a test database"""
        # Test without name
        adapter = setup_test_database()
        assert isinstance(adapter, DbTestAdapter)
        assert adapter.is_ready == True
        assert os.environ.get("USE_TEST_DB") == "true"
        assert os.environ.get("DATABASE_PROVIDER") == "sqlite"
        
        # Cleanup
        cleanup_test_database(adapter)
        
        # Test with name
        adapter = setup_test_database("named_db")
        assert adapter.database_name == "named_db"
        assert "named_db" in adapter.connection_string
        
        # Cleanup
        cleanup_test_database(adapter)
    
    def test_cleanup_test_database(self):
        """Test cleaning up test database"""
        adapter = setup_test_database("cleanup_test")
        db_path = adapter.db_path
        
        assert os.path.exists(db_path)
        
        # Cleanup
        result = cleanup_test_database(adapter)
        assert result == True
        assert not os.path.exists(db_path)
        assert "USE_TEST_DB" not in os.environ
        assert "DATABASE_URL" not in os.environ
    
    def test_create_isolated_session(self):
        """Test creating isolated session"""
        session = create_isolated_session("session_test")
        assert session is not None
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        session.close()


class TestFixtureManager:
    """Test FixtureManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create fixture manager"""
        return FixtureManager()
    
    def test_create_task_fixture(self, manager):
        """Test creating task fixture"""
        task = manager.create('task', title="Test Task", status="todo")
        assert hasattr(task, 'id')
        assert task.title == "Test Task"
        assert task.status == "todo"
        assert task.priority == "medium"
    
    def test_create_project_fixture(self, manager):
        """Test creating project fixture"""
        project = manager.create('project', name="Test Project")
        assert hasattr(project, 'id')
        assert project.name == "Test Project"
        assert hasattr(project, 'created_at')
        assert hasattr(project, 'tasks')
        assert project.tasks == []
    
    def test_create_agent_fixture(self, manager):
        """Test creating agent fixture"""
        agent = manager.create('agent', name="@test_agent", capabilities=["coding"])
        assert hasattr(agent, 'id')
        assert agent.name == "@test_agent"
        assert agent.capabilities == ["coding"]
        assert hasattr(agent, 'assigned_tasks')
    
    def test_create_context_fixture(self, manager):
        """Test creating context fixture"""
        context = manager.create('context', level="task", data={"key": "value"})
        assert hasattr(context, 'id')
        assert context.level == "task"
        assert context.data == {"key": "value"}
        assert hasattr(context, 'created_at')
    
    def test_create_subtask_fixture(self, manager):
        """Test creating subtask fixture"""
        subtask = manager.create('subtask', task_id="parent-123", title="Subtask")
        assert hasattr(subtask, 'id')
        assert subtask.title == "Subtask"
        assert subtask.task_id == "parent-123"
        assert subtask.status == "todo"
        assert subtask.progress == 0
    
    def test_task_project_relationship(self, manager):
        """Test task-project relationship tracking"""
        project = manager.create('project', id="proj-1")
        task = manager.create('task', project_id="proj-1", title="Project Task")
        
        assert len(project.tasks) == 1
        assert project.tasks[0].title == "Project Task"
    
    def test_get_and_list_fixtures(self, manager):
        """Test getting and listing fixtures"""
        task1 = manager.create('task', title="Task 1")
        task2 = manager.create('task', title="Task 2")
        
        # Get by ID
        retrieved = manager.get(task1.id)
        assert retrieved.title == "Task 1"
        
        # List all
        all_fixtures = manager.list()
        assert len(all_fixtures) == 2
    
    def test_cleanup(self, manager):
        """Test fixture cleanup"""
        manager.create('task')
        manager.create('project')
        assert len(manager.list()) == 2
        
        manager.cleanup()
        assert len(manager.list()) == 0
        assert manager._id_counter == 0


class TestFixtureHelperFunctions:
    """Test fixture helper functions"""
    
    def test_create_task_fixture_function(self):
        """Test create_task_fixture helper"""
        task = create_task_fixture(title="Helper Task", priority="high")
        assert task.title == "Helper Task"
        assert task.priority == "high"
        assert task.status == "todo"
        
        # Cleanup
        cleanup_fixtures()
    
    def test_create_project_fixture_function(self):
        """Test create_project_fixture helper"""
        project = create_project_fixture(name="Helper Project")
        assert project.name == "Helper Project"
        assert hasattr(project, 'tasks')
        
        # Cleanup
        cleanup_fixtures()
    
    def test_get_fixture_by_id_function(self):
        """Test getting fixture by ID"""
        task = create_task_fixture()
        retrieved = get_fixture_by_id(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id
        
        # Cleanup
        cleanup_fixtures()
    
    def test_list_fixtures_function(self):
        """Test listing fixtures"""
        create_task_fixture()
        create_project_fixture()
        create_agent_fixture()
        
        # List all
        all_fixtures = list_fixtures()
        assert len(all_fixtures) == 3
        
        # List by type
        tasks = list_fixtures('task')
        assert len(tasks) == 1
        
        projects = list_fixtures('project')
        assert len(projects) == 1
        
        agents = list_fixtures('agent')
        assert len(agents) == 1
        
        # Cleanup
        cleanup_fixtures()


class TestMockRepository:
    """Test MockRepository class"""
    
    @pytest.fixture
    def repo(self):
        """Create mock repository"""
        return MockRepository('test')
    
    def test_create(self, repo):
        """Test creating records"""
        record = repo.create({"title": "Test"})
        assert 'id' in record
        assert record['title'] == "Test"
        assert repo.call_count('create') == 1
    
    def test_get(self, repo):
        """Test getting records"""
        # Create record
        record = repo.create({"id": "123", "title": "Test"})
        
        # Get record
        retrieved = repo.get("123")
        assert retrieved is not None
        assert retrieved['title'] == "Test"
        assert repo.call_count('get') == 1
        
        # Get non-existent
        missing = repo.get("999")
        assert missing is None
    
    def test_update(self, repo):
        """Test updating records"""
        # Create record
        record = repo.create({"id": "123", "title": "Original"})
        
        # Update record
        updated = repo.update("123", {"title": "Updated"})
        assert updated is not None
        assert updated['title'] == "Updated"
        assert repo.call_count('update') == 1
        
        # Update non-existent
        missing = repo.update("999", {"title": "Test"})
        assert missing is None
    
    def test_delete(self, repo):
        """Test deleting records"""
        # Create record
        repo.create({"id": "123"})
        
        # Delete record
        result = repo.delete("123")
        assert result == True
        assert repo.get("123") is None
        assert repo.call_count('delete') == 1
        
        # Delete non-existent
        result = repo.delete("999")
        assert result == False
    
    def test_list_with_filters(self, repo):
        """Test listing records with filters"""
        # Create records
        repo.create({"id": "1", "status": "todo"})
        repo.create({"id": "2", "status": "done"})
        repo.create({"id": "3", "status": "todo", "dependencies": ["1"]})
        
        # List all
        all_records = repo.list()
        assert len(all_records) == 3
        
        # Filter by status
        todos = repo.list(status="todo")
        assert len(todos) == 2
        
        # Filter by dependencies
        with_deps = repo.list(has_dependencies=True)
        assert len(with_deps) == 1
        
        # Limit and offset
        limited = repo.list(limit=2, offset=1)
        assert len(limited) == 2
    
    def test_search(self, repo):
        """Test searching records"""
        # Create records
        repo.create({"id": "1", "title": "Test Task"})
        repo.create({"id": "2", "title": "Another Item"})
        repo.create({"id": "3", "description": "task description"})
        
        # Search
        results = repo.search("task")
        assert len(results) == 2
        assert repo.call_count('search') == 1
    
    def test_bulk_create(self, repo):
        """Test bulk creating records"""
        records = [
            {"title": "Task 1"},
            {"title": "Task 2"},
            {"title": "Task 3"}
        ]
        
        created = repo.bulk_create(records)
        assert len(created) == 3
        assert repo.count() == 3
    
    def test_transaction(self, repo):
        """Test transaction context manager"""
        # Successful transaction
        with repo.transaction():
            repo.create({"id": "1"})
            repo.create({"id": "2"})
        assert repo.count() == 2
        
        # Failed transaction
        initial_count = repo.count()
        with pytest.raises(Exception):
            with repo.transaction():
                repo.create({"id": "3"})
                raise Exception("Rollback")
        # Data should be rolled back
        assert repo.count() == initial_count
    
    def test_configure_responses(self, repo):
        """Test configuring mock responses"""
        # Configure error response
        configure_mock_responses(repo, 'get', side_effect=Exception("DB Error"))
        with pytest.raises(Exception) as exc_info:
            repo.get("123")
        assert "DB Error" in str(exc_info.value)
        
        # Configure return value
        configure_mock_responses(repo, 'get', response={"id": "999", "title": "Mocked"})
        result = repo.get("any_id")
        assert result["id"] == "999"
        assert result["title"] == "Mocked"


class TestMockRepositoryFactory:
    """Test MockRepositoryFactory class"""
    
    def test_singleton_pattern(self):
        """Test factory is a singleton"""
        factory1 = MockRepositoryFactory()
        factory2 = MockRepositoryFactory()
        assert factory1 is factory2
    
    def test_create_repositories(self):
        """Test creating different repository types"""
        factory = MockRepositoryFactory()
        
        # Task repository
        task_repo = factory.create_task_repository()
        assert isinstance(task_repo, MockRepository)
        assert hasattr(task_repo, 'register')
        assert hasattr(task_repo, 'assign')
        
        # Project repository
        project_repo = factory.create_project_repository()
        assert isinstance(project_repo, MockRepository)
        
        # Agent repository
        agent_repo = factory.create_agent_repository()
        assert hasattr(agent_repo, 'register')
        assert hasattr(agent_repo, 'assign')
        
        # Context repository
        context_repo = factory.create_context_repository()
        assert hasattr(context_repo, 'resolve')
        assert hasattr(context_repo, 'delegate')
    
    def test_repository_reuse(self):
        """Test repositories are reused"""
        factory = MockRepositoryFactory()
        
        repo1 = factory.create_task_repository()
        repo2 = factory.create_task_repository()
        assert repo1 is repo2


class TestDataFactory:
    """Test DataFactory class"""
    
    @pytest.fixture
    def factory(self):
        """Create data factory"""
        return DataFactory(seed=42)
    
    def test_generate_task(self, factory):
        """Test generating task data"""
        task = factory.generate_task()
        assert 'id' in task
        assert 'title' in task
        assert 'status' in task
        assert 'priority' in task
        assert 'created_at' in task
        assert task['status'] in ['todo', 'in_progress', 'done', 'blocked']
        assert task['priority'] in ['low', 'medium', 'high', 'urgent', 'critical']
    
    def test_generate_task_with_overrides(self, factory):
        """Test generating task with overrides"""
        task = factory.generate_task(
            title="Custom Task",
            status="done",
            assignees=["user1", "user2"]
        )
        assert task['title'] == "Custom Task"
        assert task['status'] == "done"
        assert task['assignees'] == ["user1", "user2"]
    
    def test_generate_project(self, factory):
        """Test generating project data"""
        project = factory.generate_project()
        assert 'id' in project
        assert 'name' in project
        assert 'description' in project
        assert 'created_at' in project
        assert 'metadata' in project
    
    def test_generate_agent(self, factory):
        """Test generating agent data"""
        agent = factory.generate_agent()
        assert 'id' in agent
        assert 'name' in agent
        assert agent['name'].startswith('@agent_')
        assert 'capabilities' in agent
        assert agent['capabilities'] == ['coding', 'testing']
    
    def test_generate_context(self, factory):
        """Test generating context data"""
        context = factory.generate_context()
        assert 'id' in context
        assert 'level' in context
        assert 'context_id' in context
        assert 'data' in context
        assert context['level'] in ['global', 'project', 'branch', 'task']
    
    def test_generate_subtask(self, factory):
        """Test generating subtask data"""
        subtask = factory.generate_subtask("parent-123")
        assert 'id' in subtask
        assert 'title' in subtask
        assert subtask['task_id'] == "parent-123"
        assert subtask['status'] == "todo"
        assert subtask['progress'] == 0
    
    def test_generate_bulk(self, factory):
        """Test bulk generation"""
        tasks = factory.generate_bulk('task', 5, status="todo")
        assert len(tasks) == 5
        assert all(task['status'] == "todo" for task in tasks)
        
        projects = factory.generate_bulk('project', 3)
        assert len(projects) == 3
        assert all('name' in proj for proj in projects)


class TestDataGenerator:
    """Test DataGenerator class"""
    
    @pytest.fixture
    def generator(self):
        """Create data generator"""
        return DataGenerator()
    
    def test_generate_sequential_pattern(self, generator):
        """Test generating sequential data"""
        tasks = generator.generate('task', pattern='sequential', count=3)
        assert len(tasks) == 3
        assert tasks[0]['title'] == "Task 001"
        assert tasks[1]['title'] == "Task 002"
        assert tasks[2]['title'] == "Task 003"
    
    def test_generate_realistic_pattern(self, generator):
        """Test generating realistic data"""
        tasks = generator.generate('task', pattern='realistic', count=5)
        assert len(tasks) == 5
        assert all(task['title'] in ['Setup Database', 'Create API', 'Build UI', 'Write Tests'] 
                  for task in tasks)
        assert tasks[0]['status'] == 'todo'  # First task always todo
    
    def test_generate_random_pattern(self, generator):
        """Test generating random data"""
        tasks = generator.generate('task', pattern='random', count=3)
        assert len(tasks) == 3
        assert all('id' in task for task in tasks)
    
    def test_set_seed(self, generator):
        """Test setting random seed for reproducibility"""
        generator.set_seed(123)
        tasks1 = generator.generate('task', count=3)
        
        generator.reset()
        generator.set_seed(123)
        tasks2 = generator.generate('task', count=3)
        
        # Should generate same data with same seed
        assert tasks1[0]['status'] == tasks2[0]['status']


class TestDataHelperFunctions:
    """Test data generation helper functions"""
    
    def test_generate_task_data(self):
        """Test generate_task_data helper"""
        task = generate_task_data(title="Test Task", priority="high")
        assert task['title'] == "Test Task"
        assert task['priority'] == "high"
        assert 'id' in task
    
    def test_generate_project_data(self):
        """Test generate_project_data helper"""
        project = generate_project_data(name="Test Project")
        assert project['name'] == "Test Project"
        assert 'id' in project
    
    def test_generate_bulk_data(self):
        """Test generate_bulk_data helper"""
        # Basic bulk generation
        tasks = generate_bulk_data('task', 5, status="todo")
        assert len(tasks) == 5
        assert all(task['status'] == "todo" for task in tasks)
        
        # With dependencies
        tasks = generate_bulk_data('task', 3, create_dependencies=True)
        assert len(tasks) == 3
        assert tasks[0]['dependencies'] == []
        assert tasks[1]['dependencies'] == [tasks[0]['id']]
        assert tasks[2]['dependencies'] == [tasks[1]['id']]
        
        # With title pattern
        tasks = generate_bulk_data('task', 3, title_pattern="Step {index}")
        assert tasks[0]['title'] == "Step 1"
        assert tasks[1]['title'] == "Step 2"
        assert tasks[2]['title'] == "Step 3"
    
    def test_ensure_data_consistency(self):
        """Test ensure_data_consistency helper"""
        project = {"id": "proj-123"}
        tasks = [
            {"id": "1", "project_id": "proj-123"},
            {"id": "2", "project_id": "proj-123"}
        ]
        assert ensure_data_consistency(project, tasks) == True
        
        # Inconsistent data
        tasks.append({"id": "3", "project_id": "wrong-proj"})
        assert ensure_data_consistency(project, tasks) == False
    
    def test_validate_generated_data(self):
        """Test validate_generated_data helper"""
        # Valid task
        valid_task = {
            "id": "123",
            "title": "Test",
            "status": "todo"
        }
        assert validate_generated_data('task', valid_task) == True
        
        # Missing required field
        invalid_task = {"id": "123", "status": "todo"}
        assert validate_generated_data('task', invalid_task) == False
        
        # Invalid status
        invalid_status = {
            "id": "123",
            "title": "Test",
            "status": "invalid"
        }
        assert validate_generated_data('task', invalid_status) == False
        
        # Other types default to valid
        assert validate_generated_data('project', {}) == True