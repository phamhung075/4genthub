"""Test helpers for database operations

This module provides utilities for setting up and tearing down test databases.
"""

import os
import tempfile
import uuid
import random
from typing import Optional, Dict, Any, List, Generator
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter


class DatabaseIsolation:
    """Manages database isolation for tests"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self):
        self.databases = {}
        self.production_connection_string = os.environ.get("DATABASE_URL", "sqlite:///production.db")
    
    def create_test_database(self, name: str) -> 'DbTestAdapter':
        """Create an isolated test database"""
        temp_dir = tempfile.mkdtemp(prefix=f"test_{name}_")
        db_path = os.path.join(temp_dir, f"{name}.db")
        
        adapter = DbTestAdapter(db_path)
        adapter.database_name = name
        adapter.is_isolated = True
        adapter.connection_string = f"sqlite:///{db_path}"
        adapter.is_ready = True
        adapter.is_clean = True
        
        self.databases[name] = adapter
        return adapter
    
    def cleanup_database(self, test_db: 'DbTestAdapter'):
        """Clean up test database"""
        test_db.delete_all("tasks")
        test_db.is_clean = True
    
    def get_production_connection_string(self) -> str:
        """Get production connection string"""
        return self.production_connection_string


class DbTestAdapter:
    """Adapter for test database operations"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.database_name = os.path.basename(db_path).replace('.db', '')
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.is_isolated = False
        self.is_ready = False
        self.is_clean = True
        self.connection_string = f"sqlite:///{db_path}"
        self._test_data = {}
    
    def get_session(self) -> Session:
        """Get a database session"""
        session = self.SessionLocal()
        # Note: is_active is a read-only property in SQLAlchemy
        # It automatically reflects the session's actual state
        return session
    
    def insert_test_data(self, data: Dict[str, List[Dict[str, Any]]]):
        """Insert test data into database"""
        for table, records in data.items():
            if table not in self._test_data:
                self._test_data[table] = []
            self._test_data[table].extend(records)
        self.is_clean = False
    
    def query_all(self, table: str) -> List[Dict[str, Any]]:
        """Query all records from a table"""
        return self._test_data.get(table, [])
    
    def query_by_id(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Query record by ID"""
        records = self._test_data.get(table, [])
        for record in records:
            if record.get('id') == record_id:
                return record
        return None
    
    def delete_all(self, table: str):
        """Delete all records from a table"""
        if table in self._test_data:
            self._test_data[table] = []
    
    def reset(self):
        """Reset the database to clean state"""
        self._test_data = {}
        self.is_clean = True
    
    def get_connection_string(self) -> str:
        """Get connection string for this database"""
        return self.connection_string
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


def setup_test_database(db_name: Optional[str] = None) -> DbTestAdapter:
    """Setup a test database for integration tests
    
    Args:
        db_name: Optional database name. If not provided, a temporary one is created.
        
    Returns:
        DbTestAdapter: Adapter for interacting with the test database
    """
    # Set test environment variables
    os.environ["USE_TEST_DB"] = "true"
    os.environ["DATABASE_PROVIDER"] = "sqlite"
    
    # Create unique temporary database for each test
    if db_name is None:
        temp_dir = tempfile.mkdtemp(prefix="dhafnck_test_")
        db_path = os.path.join(temp_dir, "test.db")
    else:
        # Create unique path even when name provided to ensure isolation
        temp_dir = tempfile.mkdtemp(prefix=f"dhafnck_{db_name}_")
        db_path = os.path.join(temp_dir, f"{db_name}.db")
    
    # Set the test database path
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    
    # Create the test adapter directly
    adapter = DbTestAdapter(db_path)
    adapter.database_name = db_name or "test_db"
    adapter.is_ready = True
    
    # Initialize the database schema if needed
    try:
        from fastmcp.task_management.infrastructure.database.models import Base
        Base.metadata.create_all(bind=adapter.engine)
    except:
        pass  # Models might not exist yet
    
    # Return the test adapter  
    return adapter


def cleanup_test_database(adapter: DbTestAdapter) -> bool:
    """Cleanup test database after tests
    
    Args:
        adapter: The test database adapter to cleanup
        
    Returns:
        bool: True if cleanup was successful
    """
    # Close any open sessions
    adapter.engine.dispose()
    
    # Reset in-memory data
    adapter.reset()
    
    # Remove the database file if it exists
    if os.path.exists(adapter.db_path):
        os.remove(adapter.db_path)
    
    # Remove temp directory if it was created
    parent_dir = os.path.dirname(adapter.db_path)
    if parent_dir.startswith(tempfile.gettempdir()) and "dhafnck_test_" in parent_dir:
        try:
            os.rmdir(parent_dir)
        except OSError:
            pass  # Directory not empty or other error
    
    # Clear test environment variables
    if "USE_TEST_DB" in os.environ:
        del os.environ["USE_TEST_DB"]
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
    
    return True


def create_isolated_session(db_name: str) -> Session:
    """Create an isolated database session for testing
    
    Args:
        db_name: Name for the test database
        
    Returns:
        Session: An isolated SQLAlchemy session
    """
    adapter = setup_test_database(db_name)
    session = adapter.get_session()
    # Note: is_active is a read-only property that reflects actual state
    return session


# Fixture Management
class FixturesBase:
    """Test fixture management"""
    pass


class FixtureManager:
    """Manages test fixtures"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self):
        self.fixtures = {}
        self._id_counter = 0
    
    def create(self, fixture_type: str, **kwargs) -> Dict[str, Any]:
        """Create a fixture"""
        self._id_counter += 1
        fixture_id = f"{fixture_type}-{self._id_counter}"
        
        if fixture_type == 'task':
            fixture = self._create_task_fixture(fixture_id, **kwargs)
        elif fixture_type == 'project':
            fixture = self._create_project_fixture(fixture_id, **kwargs)
        elif fixture_type == 'agent':
            fixture = self._create_agent_fixture(fixture_id, **kwargs)
        elif fixture_type == 'context':
            fixture = self._create_context_fixture(fixture_id, **kwargs)
        elif fixture_type == 'subtask':
            fixture = self._create_subtask_fixture(fixture_id, **kwargs)
        else:
            fixture = {'id': fixture_id, 'type': fixture_type, **kwargs}
        
        self.fixtures[fixture_id] = fixture
        
        # Also store by actual ID if provided and different from fixture_id
        actual_id = getattr(fixture, 'id', None)
        if actual_id and actual_id != fixture_id:
            self.fixtures[actual_id] = fixture
        
        return fixture
    
    def _create_task_fixture(self, fixture_id: str, **kwargs) -> Dict[str, Any]:
        """Create a task fixture"""
        task = type('Task', (), {
            'id': kwargs.get('id', fixture_id),
            'title': kwargs.get('title', f'Task {fixture_id}'),
            'status': kwargs.get('status', 'todo'),
            'priority': kwargs.get('priority', 'medium'),
            'description': kwargs.get('description', ''),
            'project_id': kwargs.get('project_id'),
            'assignees': kwargs.get('assignees', []),
            'dependencies': kwargs.get('dependencies', [])
        })()
        
        # Track in parent project if specified
        if task.project_id and task.project_id in self.fixtures:
            project = self.fixtures[task.project_id]
            if not hasattr(project, 'tasks'):
                project.tasks = []
            project.tasks.append(task)
        
        return task
    
    def _create_project_fixture(self, fixture_id: str, **kwargs) -> Dict[str, Any]:
        """Create a project fixture"""
        return type('Project', (), {
            'id': kwargs.get('id', fixture_id),
            'name': kwargs.get('name', f'Project {fixture_id}'),
            'created_at': datetime.now(),
            'tasks': []
        })()
    
    def _create_agent_fixture(self, fixture_id: str, **kwargs) -> Dict[str, Any]:
        """Create an agent fixture"""
        return type('Agent', (), {
            'id': kwargs.get('id', fixture_id),
            'name': kwargs.get('name', f'@agent_{fixture_id}'),
            'project_id': kwargs.get('project_id'),
            'capabilities': kwargs.get('capabilities', []),
            'assigned_tasks': []
        })()
    
    def _create_context_fixture(self, fixture_id: str, **kwargs) -> Dict[str, Any]:
        """Create a context fixture"""
        return type('Context', (), {
            'id': fixture_id,
            'level': kwargs.get('level', 'task'),
            'context_id': kwargs.get('context_id', fixture_id),
            'data': kwargs.get('data', {}),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })()
    
    def _create_subtask_fixture(self, fixture_id: str, **kwargs) -> Dict[str, Any]:
        """Create a subtask fixture"""
        return type('Subtask', (), {
            'id': kwargs.get('id', fixture_id),
            'title': kwargs.get('title', f'Subtask {fixture_id}'),
            'task_id': kwargs.get('task_id', kwargs.get('parent_id')),
            'status': kwargs.get('status', 'todo'),
            'progress': kwargs.get('progress', 0)
        })()
    
    def get(self, fixture_id: str) -> Optional[Any]:
        """Get a fixture by ID"""
        return self.fixtures.get(fixture_id)
    
    def list(self) -> List[Any]:
        """List all fixtures"""
        return list(self.fixtures.values())
    
    def cleanup(self):
        """Clean up all fixtures"""
        self.fixtures = {}
        self._id_counter = 0


# Global fixture storage for helper functions
_global_fixtures = {}


def create_task_fixture(**kwargs) -> Any:
    """Create a task fixture"""
    fixture_id = kwargs.get('id', str(uuid.uuid4()))
    task = type('Task', (), {
        'id': fixture_id,
        'title': kwargs.get('title', f'Task {fixture_id}'),
        'status': kwargs.get('status', 'todo'),
        'priority': kwargs.get('priority', 'medium'),
        'description': kwargs.get('description', ''),
        'project_id': kwargs.get('project_id'),
        'assignees': kwargs.get('assignees', []),
        'dependencies': kwargs.get('dependencies', [])
    })()
    _global_fixtures[fixture_id] = task
    return task


def create_project_fixture(**kwargs) -> Any:
    """Create a project fixture"""
    fixture_id = kwargs.get('id', str(uuid.uuid4()))
    project = type('Project', (), {
        'id': fixture_id,
        'name': kwargs.get('name', f'Project {fixture_id}'),
        'created_at': datetime.now(),
        'tasks': []
    })()
    _global_fixtures[fixture_id] = project
    return project


def create_agent_fixture(**kwargs) -> Any:
    """Create an agent fixture"""
    fixture_id = kwargs.get('id', str(uuid.uuid4()))
    agent = type('Agent', (), {
        'id': fixture_id,
        'name': kwargs.get('name', f'@agent_{fixture_id}'),
        'project_id': kwargs.get('project_id'),
        'capabilities': kwargs.get('capabilities', []),
        'assigned_tasks': []
    })()
    _global_fixtures[fixture_id] = agent
    return agent


def create_context_fixture(**kwargs) -> Any:
    """Create a context fixture"""
    fixture_id = str(uuid.uuid4())
    context = type('Context', (), {
        'id': fixture_id,
        'level': kwargs.get('level', 'task'),
        'context_id': kwargs.get('context_id', fixture_id),
        'data': kwargs.get('data', {}),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    })()
    _global_fixtures[fixture_id] = context
    return context


def cleanup_fixtures():
    """Clean up all fixtures"""
    global _global_fixtures
    _global_fixtures = {}


def get_fixture_by_id(fixture_id: str) -> Optional[Any]:
    """Get a fixture by ID"""
    return _global_fixtures.get(fixture_id)


def list_fixtures(fixture_type: Optional[str] = None) -> List[Any]:
    """List all fixtures, optionally filtered by type"""
    if fixture_type is None:
        return list(_global_fixtures.values())
    
    # Filter by type based on attributes
    filtered = []
    for fixture in _global_fixtures.values():
        if fixture_type == 'task' and hasattr(fixture, 'title') and hasattr(fixture, 'status'):
            filtered.append(fixture)
        elif fixture_type == 'project' and hasattr(fixture, 'name') and hasattr(fixture, 'tasks'):
            filtered.append(fixture)
        elif fixture_type == 'agent' and hasattr(fixture, 'capabilities'):
            filtered.append(fixture)
        elif fixture_type == 'context' and hasattr(fixture, 'level'):
            filtered.append(fixture)
    return filtered


# Mock Repository Classes
class MockRepository:
    """Base mock repository class"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self, repository_type: str):
        self.repository_type = repository_type
        self._data = {}
        self._call_counts = {}
        self._responses = {}
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a record"""
        if 'create' in self._responses:
            response = self._responses['create']
            if isinstance(response, Exception):
                raise response
            return response
        
        record_id = data.get('id', str(uuid.uuid4()))
        record = {'id': record_id, **data}
        self._data[record_id] = record
        self._increment_call_count('create')
        return record
    
    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a record by ID"""
        self._increment_call_count('get')
        if 'get' in self._responses:
            response = self._responses['get']
            if isinstance(response, list) and len(response) > 0:
                return response.pop(0)
            elif isinstance(response, Exception):
                raise response
            return response
        return self._data.get(record_id)
    
    def update(self, record_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record"""
        self._increment_call_count('update')
        if record_id in self._data:
            self._data[record_id].update(updates)
            return self._data[record_id]
        return None
    
    def delete(self, record_id: str) -> bool:
        """Delete a record"""
        self._increment_call_count('delete')
        if record_id in self._data:
            del self._data[record_id]
            return True
        return False
    
    def list(self, **filters) -> List[Dict[str, Any]]:
        """List records with optional filters"""
        self._increment_call_count('list')
        results = list(self._data.values())
        
        # Apply filters
        if 'status' in filters and filters['status']:
            results = [r for r in results if r.get('status') == filters['status']]
        if 'has_dependencies' in filters and filters['has_dependencies']:
            results = [r for r in results if r.get('dependencies')]
        if 'limit' in filters:
            offset = filters.get('offset', 0)
            limit = filters['limit']
            results = results[offset:offset + limit]
        
        return results
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search records"""
        self._increment_call_count('search')
        results = []
        for record in self._data.values():
            if query.lower() in str(record).lower():
                results.append(record)
        return results
    
    def reset(self):
        """Reset the repository"""
        self._data = {}
        self._call_counts = {}
        self._responses = {}
    
    def bulk_create(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk create records"""
        created = []
        for record_data in records:
            created.append(self.create(record_data))
        return created
    
    def count(self) -> int:
        """Count records"""
        return len(self._data)
    
    def call_count(self, method: str) -> int:
        """Get call count for a method"""
        return self._call_counts.get(method, 0)
    
    def _increment_call_count(self, method: str):
        """Increment call count for a method"""
        if method not in self._call_counts:
            self._call_counts[method] = 0
        self._call_counts[method] += 1
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        # Simple implementation - just yield self for now
        backup = dict(self._data)
        try:
            yield self
        except:
            self._data = backup
            raise
    
    def rollback(self):
        """Rollback changes (used in transaction)"""
        # This would be called within transaction context
        pass


class MockRepositoryFactory:
    """Factory for creating mock repositories"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._repositories = {}
        return cls._instance
    
    def create_task_repository(self) -> MockRepository:
        """Create a mock task repository"""
        if 'task' not in self._repositories:
            repo = MockRepository('task')
            # Add task-specific methods
            repo.register = lambda *args, **kwargs: repo.create(kwargs)
            repo.assign = lambda *args, **kwargs: {'success': True}
            repo.unassign = lambda *args, **kwargs: {'success': True}
            self._repositories['task'] = repo
        return self._repositories['task']
    
    def create_project_repository(self) -> MockRepository:
        """Create a mock project repository"""
        if 'project' not in self._repositories:
            self._repositories['project'] = MockRepository('project')
        return self._repositories['project']
    
    def create_agent_repository(self) -> MockRepository:
        """Create a mock agent repository"""
        if 'agent' not in self._repositories:
            repo = MockRepository('agent')
            # Add agent-specific methods
            repo.register = lambda *args, **kwargs: repo.create(kwargs)
            repo.assign = lambda *args, **kwargs: {'success': True}
            repo.unassign = lambda *args, **kwargs: {'success': True}
            self._repositories['agent'] = repo
        return self._repositories['agent']
    
    def create_context_repository(self) -> MockRepository:
        """Create a mock context repository"""
        if 'context' not in self._repositories:
            repo = MockRepository('context')
            # Add context-specific methods
            repo.resolve = lambda *args, **kwargs: repo.get(args[0]) if args else None
            repo.delegate = lambda *args, **kwargs: {'success': True}
            self._repositories['context'] = repo
        return self._repositories['context']


def create_mock_task_repository() -> MockRepository:
    """Create a mock task repository"""
    return MockRepository('task')


def create_mock_project_repository() -> MockRepository:
    """Create a mock project repository"""
    return MockRepository('project')


def create_mock_agent_repository() -> MockRepository:
    """Create a mock agent repository"""
    repo = MockRepository('agent')
    # Add agent-specific methods
    repo.register = lambda *args, **kwargs: repo.create(kwargs)
    repo.assign = lambda *args, **kwargs: {'success': True}
    repo.unassign = lambda *args, **kwargs: {'success': True}
    return repo


def create_mock_context_repository() -> MockRepository:
    """Create a mock context repository"""
    repo = MockRepository('context')
    # Add context-specific methods
    repo.resolve = lambda *args, **kwargs: repo.get(args[0]) if args else None
    repo.delegate = lambda *args, **kwargs: {'success': True}
    return repo


def configure_mock_responses(repo: MockRepository, method: str, response=None, side_effect=None):
    """Configure mock responses for a repository"""
    if side_effect is not None:
        if isinstance(side_effect, Exception):
            repo._responses[method] = side_effect
        elif isinstance(side_effect, list):
            repo._responses[method] = side_effect
        else:
            repo._responses[method] = side_effect
    elif response is not None:
        repo._responses[method] = response


# Test Data Factory Classes
class DataFactory:
    """Factory for generating test data"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed:
            random.seed(seed)
        self._id_counter = 0
    
    def generate_task(self, **overrides) -> Dict[str, Any]:
        """Generate task data"""
        self._id_counter += 1
        task_id = overrides.get('id', f'task-{self._id_counter}')
        
        return {
            'id': task_id,
            'title': overrides.get('title', f'Task {task_id}'),
            'status': overrides.get('status', random.choice(['todo', 'in_progress', 'done', 'blocked'])),
            'priority': overrides.get('priority', random.choice(['low', 'medium', 'high', 'urgent', 'critical'])),
            'description': overrides.get('description', f'Description for {task_id}'),
            'created_at': overrides.get('created_at', datetime.now().isoformat()),
            'updated_at': overrides.get('updated_at', datetime.now().isoformat()),
            'assignees': overrides.get('assignees', []),
            'dependencies': overrides.get('dependencies', []),
            'project_id': overrides.get('project_id'),
            **{k: v for k, v in overrides.items() if k not in ['id', 'title', 'status', 'priority', 'description', 'created_at', 'updated_at', 'assignees', 'dependencies', 'project_id']}
        }
    
    def generate_project(self, **overrides) -> Dict[str, Any]:
        """Generate project data"""
        self._id_counter += 1
        project_id = overrides.get('id', f'project-{self._id_counter}')
        
        return {
            'id': project_id,
            'name': overrides.get('name', f'Project {project_id}'),
            'description': overrides.get('description', f'Description for {project_id}'),
            'created_at': overrides.get('created_at', datetime.now().isoformat()),
            'metadata': overrides.get('metadata', {}),
            **{k: v for k, v in overrides.items() if k not in ['id', 'name', 'description', 'created_at', 'metadata']}
        }
    
    def generate_agent(self, **overrides) -> Dict[str, Any]:
        """Generate agent data"""
        self._id_counter += 1
        agent_id = overrides.get('id', f'agent-{self._id_counter}')
        
        return {
            'id': agent_id,
            'name': overrides.get('name', f'@agent_{agent_id}'),
            'project_id': overrides.get('project_id'),
            'capabilities': overrides.get('capabilities', ['coding', 'testing']),
            **{k: v for k, v in overrides.items() if k not in ['id', 'name', 'project_id', 'capabilities']}
        }
    
    def generate_context(self, **overrides) -> Dict[str, Any]:
        """Generate context data"""
        self._id_counter += 1
        context_id = overrides.get('context_id', f'context-{self._id_counter}')
        
        return {
            'id': context_id,
            'level': overrides.get('level', random.choice(['global', 'project', 'branch', 'task'])),
            'context_id': context_id,
            'data': overrides.get('data', {}),
            'created_at': overrides.get('created_at', datetime.now().isoformat()),
            **{k: v for k, v in overrides.items() if k not in ['id', 'level', 'context_id', 'data', 'created_at']}
        }
    
    def generate_subtask(self, parent_id: str, **overrides) -> Dict[str, Any]:
        """Generate subtask data"""
        self._id_counter += 1
        subtask_id = overrides.get('id', f'subtask-{self._id_counter}')
        
        return {
            'id': subtask_id,
            'title': overrides.get('title', f'Subtask {subtask_id}'),
            'task_id': parent_id,
            'status': overrides.get('status', 'todo'),
            'progress': overrides.get('progress', 0),
            **{k: v for k, v in overrides.items() if k not in ['id', 'title', 'task_id', 'status', 'progress']}
        }
    
    def generate_bulk(self, data_type: str, count: int, **kwargs) -> List[Dict[str, Any]]:
        """Generate bulk data"""
        results = []
        for i in range(count):
            if data_type == 'task':
                results.append(self.generate_task(**kwargs))
            elif data_type == 'project':
                results.append(self.generate_project(**kwargs))
            elif data_type == 'agent':
                results.append(self.generate_agent(**kwargs))
            elif data_type == 'context':
                results.append(self.generate_context(**kwargs))
        return results


class DataGenerator:
    """Advanced data generator with patterns"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self):
        self._counter = 0
        self._seed = None
    
    def generate(self, data_type: str, pattern: str = 'random', count: int = 1, **kwargs) -> List[Dict[str, Any]]:
        """Generate data with patterns"""
        factory = DataFactory(self._seed)
        
        if pattern == 'sequential':
            # Generate sequential data
            results = []
            for i in range(count):
                if data_type == 'task':
                    results.append(factory.generate_task(
                        title=f'Task {i+1:03d}',
                        **kwargs
                    ))
            return results
        elif pattern == 'realistic':
            # Generate realistic data
            results = []
            for i in range(count):
                if data_type == 'task':
                    results.append(factory.generate_task(
                        title=random.choice(['Setup Database', 'Create API', 'Build UI', 'Write Tests']),
                        status='todo' if i == 0 else random.choice(['todo', 'in_progress', 'done']),
                        **kwargs
                    ))
            return results
        else:
            # Random pattern
            return factory.generate_bulk(data_type, count, **kwargs)
    
    def set_seed(self, seed: int):
        """Set random seed"""
        self._seed = seed
        random.seed(seed)
    
    def reset(self):
        """Reset generator state"""
        self._counter = 0
        self._seed = None


# Helper functions for test data generation
def generate_task_data(**kwargs) -> Dict[str, Any]:
    """Generate task test data"""
    factory = DataFactory()
    return factory.generate_task(**kwargs)


def generate_project_data(**kwargs) -> Dict[str, Any]:
    """Generate project test data"""
    factory = DataFactory()
    return factory.generate_project(**kwargs)


def generate_agent_data(**kwargs) -> Dict[str, Any]:
    """Generate agent test data"""
    factory = DataFactory()
    return factory.generate_agent(**kwargs)


def generate_context_data(**kwargs) -> Dict[str, Any]:
    """Generate context test data"""
    factory = DataFactory()
    return factory.generate_context(**kwargs)


def generate_subtask_data(**kwargs) -> Dict[str, Any]:
    """Generate subtask test data"""
    factory = DataFactory()
    task_id = kwargs.pop('task_id', 'parent-task')
    return factory.generate_subtask(task_id, **kwargs)


def generate_bulk_data(data_type: str, count: int, **kwargs) -> List[Dict[str, Any]]:
    """Generate bulk test data"""
    factory = DataFactory()
    results = []
    
    # Handle special kwargs
    create_dependencies = kwargs.pop('create_dependencies', False)
    title_pattern = kwargs.pop('title_pattern', None)
    
    for i in range(count):
        if title_pattern:
            kwargs['title'] = title_pattern.replace('{index}', str(i+1))
        
        if data_type == 'task':
            task = factory.generate_task(**kwargs)
            # Add dependencies to later tasks
            if create_dependencies and i > 0 and results:
                task['dependencies'] = [results[i-1]['id']]
            results.append(task)
        else:
            results.append(factory.generate_bulk(data_type, 1, **kwargs)[0])
    
    return results


def ensure_data_consistency(project: Dict[str, Any], tasks: List[Dict[str, Any]]) -> bool:
    """Ensure data consistency across generated data"""
    # Check all tasks belong to the project
    for task in tasks:
        if task.get('project_id') != project['id']:
            return False
    return True


def validate_generated_data(data_type: str, data: Dict[str, Any]) -> bool:
    """Validate generated data"""
    if data_type == 'task':
        required_fields = ['id', 'title', 'status']
        valid_statuses = ['todo', 'in_progress', 'done', 'blocked']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                return False
        
        # Check valid status
        if data.get('status') not in valid_statuses:
            return False
        
        return True
    
    return True  # Default to valid for other types


# Aliases for test imports (backward compatibility)
TestDatabaseAdapter = DbTestAdapter
TestDataFactory = DataFactory
TestFixtures = FixturesBase