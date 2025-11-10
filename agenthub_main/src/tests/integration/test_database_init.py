"""
Comprehensive integration tests for database_init.py module

This module provides comprehensive test coverage for database initialization functionality:
- DatabaseInitializer class initialization with SQLite and PostgreSQL
- Default project and branch creation
- User initialization workflows
- Table existence validation
- Connection handling and error scenarios
- Security scenarios (connection security, credential handling)
- Cleanup and teardown procedures

Target: 85%+ code coverage on database_init.py (86 lines)
"""

import os
import tempfile
import uuid
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from fastmcp.database_init import (
    DatabaseInitializer,
    initialize_database_for_current_user,
)


class TestDatabaseInitializerInit:
    """Test DatabaseInitializer initialization with different database types"""

    def test_init_with_explicit_database_url(self):
        """Test initialization with explicitly provided database URL"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        initializer = DatabaseInitializer(database_url=test_url)

        assert initializer.database_url == test_url

    @patch.dict(os.environ, {
        "DATABASE_TYPE": "postgresql",
        "DATABASE_HOST": "testhost",
        "DATABASE_PORT": "5433",
        "DATABASE_NAME": "customdb",
        "DATABASE_USER": "testuser",
        "DATABASE_PASSWORD": "testpass"
    })
    def test_init_postgresql_from_environment(self):
        """Test PostgreSQL URL construction from environment variables"""
        initializer = DatabaseInitializer()

        expected_url = "postgresql://testuser:testpass@testhost:5433/customdb"
        assert initializer.database_url == expected_url

    @patch.dict(os.environ, {
        "DATABASE_TYPE": "postgresql"
    }, clear=True)
    def test_init_postgresql_with_defaults(self):
        """Test PostgreSQL initialization uses default values when env vars missing"""
        # Set only DATABASE_TYPE, let others default
        os.environ["DATABASE_TYPE"] = "postgresql"

        initializer = DatabaseInitializer()

        # Should use default values
        assert "localhost" in initializer.database_url
        assert "5432" in initializer.database_url
        assert "postgresdb" in initializer.database_url
        assert "agenthub_user" in initializer.database_url
        assert "agenthub_password" in initializer.database_url

    @patch.dict(os.environ, {
        "DATABASE_TYPE": "sqlite",
        "DATABASE_URL": "sqlite:///custom_test.db"
    })
    def test_init_sqlite_from_environment(self):
        """Test SQLite initialization from DATABASE_URL"""
        initializer = DatabaseInitializer()

        assert initializer.database_url == "sqlite:///custom_test.db"

    @patch.dict(os.environ, {"DATABASE_TYPE": "other"}, clear=True)
    def test_init_other_database_type_uses_default(self):
        """Test non-PostgreSQL database types fall back to DATABASE_URL or default"""
        os.environ["DATABASE_TYPE"] = "other"

        initializer = DatabaseInitializer()

        # Should fall back to default SQLite
        assert "sqlite:///agenthub_dev.db" in initializer.database_url

    def test_init_no_environment_variables(self):
        """Test initialization with no environment variables uses PostgreSQL defaults"""
        with patch.dict(os.environ, {}, clear=True):
            initializer = DatabaseInitializer()

            # When DATABASE_TYPE is not set, it defaults to None and uses PostgreSQL construction
            # Should use default PostgreSQL settings
            assert "postgresql://" in initializer.database_url
            assert "agenthub_user" in initializer.database_url
            assert "localhost" in initializer.database_url


class TestCreateDefaultProject:
    """Test default project creation functionality"""

    @pytest.fixture
    def temp_sqlite_db(self):
        """Create a temporary SQLite database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)

        # Create required tables
        with engine.connect() as conn:
            # Create projects table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))

            # Create project_git_branchs table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_git_branchs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT NOT NULL,
                    priority TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    task_count INTEGER DEFAULT 0,
                    completed_task_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """))

            conn.commit()

        yield db_url

        # Cleanup
        try:
            os.unlink(db_path)
        except Exception:
            pass

    def test_create_default_project_new_user(self, temp_sqlite_db):
        """Test creating default project for a new user"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db)

        project_id = initializer.create_default_project(user_id)

        assert project_id is not None
        assert isinstance(project_id, str)

        # Verify project was created
        engine = create_engine(temp_sqlite_db)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name, description, user_id, status FROM projects WHERE id = :id"),
                {"id": project_id}
            )
            project = result.fetchone()

            assert project is not None
            assert project[0] == "My First Project"
            assert "Welcome to agenthub" in project[1]
            assert project[2] == user_id
            assert project[3] == "active"

    def test_create_default_project_creates_branch(self, temp_sqlite_db):
        """Test that default project creation also creates a main branch"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db)

        project_id = initializer.create_default_project(user_id)

        # Verify branch was created
        engine = create_engine(temp_sqlite_db)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT name, description, status, priority, task_count, completed_task_count
                    FROM project_git_branchs
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id}
            )
            branch = result.fetchone()

            assert branch is not None
            assert branch[0] == "main"
            assert branch[1] == "Main development branch"
            assert branch[2] == "active"
            assert branch[3] == "medium"
            assert branch[4] == 0  # task_count
            assert branch[5] == 0  # completed_task_count

    def test_create_default_project_existing_user(self, temp_sqlite_db):
        """Test that existing users don't get duplicate projects"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db)

        # Create first project
        first_project_id = initializer.create_default_project(user_id)

        # Try to create another - should return existing project ID
        second_project_id = initializer.create_default_project(user_id)

        assert first_project_id == second_project_id

        # Verify only one project exists
        engine = create_engine(temp_sqlite_db)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM projects WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            count = result.scalar()
            assert count == 1

    def test_create_default_project_transaction_rollback_on_error(self, temp_sqlite_db):
        """Test that transaction is rolled back on error"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db)

        # Patch to cause an error after project creation but before commit
        with patch('sqlalchemy.engine.base.Connection.execute') as mock_execute:
            # First call succeeds (SELECT check)
            # Second call fails (INSERT project)
            mock_execute.side_effect = [
                Mock(fetchone=Mock(return_value=None)),  # No existing project
                SQLAlchemyError("Simulated database error")
            ]

            project_id = initializer.create_default_project(user_id)

            # Should return None on error
            assert project_id is None

    def test_create_default_project_logs_error_on_exception(self, temp_sqlite_db, caplog):
        """Test that errors are properly logged"""
        import logging
        caplog.set_level(logging.ERROR)

        # Use invalid database URL to trigger error
        initializer = DatabaseInitializer(database_url="invalid://url")
        user_id = str(uuid.uuid4())

        project_id = initializer.create_default_project(user_id)

        assert project_id is None
        assert "Error creating default project" in caplog.text

    def test_create_default_project_with_special_characters_in_user_id(self, temp_sqlite_db):
        """Test project creation with special characters in user ID"""
        user_id = "user@example.com"
        initializer = DatabaseInitializer(database_url=temp_sqlite_db)

        project_id = initializer.create_default_project(user_id)

        assert project_id is not None

        # Verify user_id was stored correctly
        engine = create_engine(temp_sqlite_db)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT user_id FROM projects WHERE id = :id"),
                {"id": project_id}
            )
            stored_user_id = result.scalar()
            assert stored_user_id == user_id

    def test_create_default_project_timestamps(self, temp_sqlite_db):
        """Test that created_at and updated_at timestamps are set"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db)

        before_creation = datetime.now(UTC)
        project_id = initializer.create_default_project(user_id)
        after_creation = datetime.now(UTC)

        # Verify timestamps
        engine = create_engine(temp_sqlite_db)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT created_at, updated_at FROM projects WHERE id = :id"),
                {"id": project_id}
            )
            row = result.fetchone()
            created_at = row[0]
            updated_at = row[1]

            # Parse timestamps (SQLite returns them as strings)
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

            # Timestamps should be within the test execution window
            assert before_creation <= created_at <= after_creation
            assert before_creation <= updated_at <= after_creation


class TestInitializeForUser:
    """Test user initialization workflow"""

    @pytest.fixture
    def temp_sqlite_db_with_tables(self):
        """Create a temporary SQLite database with tables"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)

        # Create required tables
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_git_branchs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT NOT NULL,
                    priority TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    task_count INTEGER DEFAULT 0,
                    completed_task_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))

            conn.commit()

        yield db_url

        try:
            os.unlink(db_path)
        except Exception:
            pass

    def test_initialize_for_user_new_user(self, temp_sqlite_db_with_tables):
        """Test initializing database for a new user"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db_with_tables)

        result = initializer.initialize_for_user(user_id)

        assert result is True

    def test_initialize_for_user_existing_user(self, temp_sqlite_db_with_tables):
        """Test initializing database for user who already has projects"""
        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db_with_tables)

        # Initialize once
        first_result = initializer.initialize_for_user(user_id)
        assert first_result is True

        # Initialize again - should still succeed
        second_result = initializer.initialize_for_user(user_id)
        assert second_result is True

    def test_initialize_for_user_handles_errors(self):
        """Test error handling in user initialization"""
        user_id = str(uuid.uuid4())

        # Mock create_default_project to return None (indicating error)
        initializer = DatabaseInitializer(database_url="sqlite:///test.db")
        with patch.object(initializer, 'create_default_project', return_value=None):
            # When create_default_project returns None, initialize_for_user still returns True
            # because it handles the case where the user already has projects
            result = initializer.initialize_for_user(user_id)

            # The function returns True even when create_default_project returns None
            # (See lines 128-130 in database_init.py)
            assert result is True

    def test_initialize_for_user_logs_success(self, temp_sqlite_db_with_tables, caplog):
        """Test that successful initialization is logged"""
        import logging
        caplog.set_level(logging.INFO)

        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url=temp_sqlite_db_with_tables)

        initializer.initialize_for_user(user_id)

        assert f"Initializing database for user {user_id}" in caplog.text
        assert f"Database initialized for user {user_id}" in caplog.text

    def test_initialize_for_user_logs_errors(self, caplog):
        """Test that initialization errors are logged"""
        import logging
        caplog.set_level(logging.ERROR)

        user_id = str(uuid.uuid4())
        initializer = DatabaseInitializer(database_url="sqlite:///test.db")

        # Mock create_default_project to raise an exception
        with patch.object(initializer, 'create_default_project', side_effect=Exception("Test error")):
            result = initializer.initialize_for_user(user_id)

            assert result is False
            assert "Failed to initialize database for user" in caplog.text


class TestEnsureTablesExist:
    """Test table existence validation"""

    @pytest.fixture
    def temp_sqlite_db_empty(self):
        """Create an empty temporary SQLite database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"

        yield db_url

        try:
            os.unlink(db_path)
        except Exception:
            pass

    @pytest.fixture
    def temp_sqlite_db_with_all_tables(self):
        """Create a temporary SQLite database with all required tables"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)

        with engine.connect() as conn:
            # Create all required tables
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_git_branchs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS subtasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """))

            conn.commit()

        yield db_url

        try:
            os.unlink(db_path)
        except Exception:
            pass

    def test_ensure_tables_exist_all_present_sqlite(self, temp_sqlite_db_with_all_tables):
        """Test table check succeeds when all tables exist (SQLite)"""
        initializer = DatabaseInitializer(database_url=temp_sqlite_db_with_all_tables)

        # Note: SQLite doesn't have information_schema, so this will fail
        # This tests the error handling path
        result = initializer.ensure_tables_exist()

        # For SQLite, the query will fail (no information_schema)
        # This is expected behavior - the method is designed for PostgreSQL
        assert result is False

    def test_ensure_tables_exist_all_present_postgresql(self):
        """Test table check with PostgreSQL (mocked)"""
        # Create initializer with explicit PostgreSQL URL
        initializer = DatabaseInitializer(database_url="postgresql://user:pass@localhost:5432/testdb")

        with patch('fastmcp.database_init.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.scalar.return_value = 4  # All 4 tables exist
            mock_conn.execute.return_value = mock_result
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            result = initializer.ensure_tables_exist()

            assert result is True

    def test_ensure_tables_exist_missing_tables(self):
        """Test table check fails when tables are missing"""
        initializer = DatabaseInitializer(database_url="postgresql://user:pass@localhost:5432/testdb")

        with patch('fastmcp.database_init.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.scalar.return_value = 2  # Only 2 of 4 tables exist
            mock_conn.execute.return_value = mock_result
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            result = initializer.ensure_tables_exist()

            assert result is False

    def test_ensure_tables_exist_handles_errors(self):
        """Test error handling in table existence check"""
        initializer = DatabaseInitializer(database_url="invalid://url")

        result = initializer.ensure_tables_exist()

        assert result is False

    def test_ensure_tables_exist_logs_warning_on_missing_tables(self, caplog):
        """Test that warning is logged when tables are missing"""
        import logging
        caplog.set_level(logging.WARNING)

        initializer = DatabaseInitializer(database_url="postgresql://user:pass@localhost:5432/testdb")

        with patch('fastmcp.database_init.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.scalar.return_value = 0  # No tables exist
            mock_conn.execute.return_value = mock_result
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            initializer.ensure_tables_exist()

            assert "Not all required tables exist" in caplog.text
            assert "run database migrations first" in caplog.text


class TestInitializeDatabaseForCurrentUser:
    """Test module-level initialization function"""

    @pytest.fixture
    def temp_sqlite_db_complete(self):
        """Create a complete temporary SQLite database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)

        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_git_branchs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT NOT NULL,
                    priority TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    task_count INTEGER DEFAULT 0,
                    completed_task_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))

            conn.commit()

        yield db_url

        try:
            os.unlink(db_path)
        except Exception:
            pass

    @patch.dict(os.environ, {"CURRENT_USER_ID": "test-user-123"})
    def test_initialize_database_for_current_user_with_user_id(self, temp_sqlite_db_complete):
        """Test initialization with CURRENT_USER_ID set"""
        with patch('fastmcp.database_init.DatabaseInitializer') as mock_init_class:
            mock_initializer = Mock()
            mock_initializer.ensure_tables_exist.return_value = True
            mock_initializer.initialize_for_user.return_value = True
            mock_init_class.return_value = mock_initializer

            result = initialize_database_for_current_user()

            assert result is True
            mock_initializer.initialize_for_user.assert_called_once_with("test-user-123")

    @patch.dict(os.environ, {}, clear=True)
    def test_initialize_database_for_current_user_uses_default(self):
        """Test initialization uses default user ID when not set"""
        with patch('fastmcp.database_init.DatabaseInitializer') as mock_init_class:
            mock_initializer = Mock()
            mock_initializer.ensure_tables_exist.return_value = True
            mock_initializer.initialize_for_user.return_value = True
            mock_init_class.return_value = mock_initializer

            result = initialize_database_for_current_user()

            assert result is True
            # Should use default user ID
            mock_initializer.initialize_for_user.assert_called_once_with("default-user-001")

    @patch.dict(os.environ, {"DEFAULT_USER_ID": "custom-default-user"})
    def test_initialize_database_for_current_user_custom_default(self):
        """Test initialization with custom default user ID"""
        with patch('fastmcp.database_init.DatabaseInitializer') as mock_init_class:
            mock_initializer = Mock()
            mock_initializer.ensure_tables_exist.return_value = True
            mock_initializer.initialize_for_user.return_value = True
            mock_init_class.return_value = mock_initializer

            result = initialize_database_for_current_user()

            assert result is True
            mock_initializer.initialize_for_user.assert_called_once_with("custom-default-user")

    def test_initialize_database_for_current_user_no_tables(self):
        """Test initialization skips when tables don't exist"""
        with patch('fastmcp.database_init.DatabaseInitializer') as mock_init_class:
            mock_initializer = Mock()
            mock_initializer.ensure_tables_exist.return_value = False
            mock_init_class.return_value = mock_initializer

            result = initialize_database_for_current_user()

            assert result is False
            # Should not call initialize_for_user when tables don't exist
            mock_initializer.initialize_for_user.assert_not_called()

    def test_initialize_database_for_current_user_handles_errors(self):
        """Test error handling in module-level function"""
        with patch('fastmcp.database_init.DatabaseInitializer') as mock_init_class:
            mock_init_class.side_effect = Exception("Initialization failed")

            result = initialize_database_for_current_user()

            assert result is False

    def test_initialize_database_for_current_user_logs_default_user(self, caplog):
        """Test that using default user is logged"""
        import logging
        caplog.set_level(logging.INFO)

        with patch.dict(os.environ, {}, clear=True):
            with patch('fastmcp.database_init.DatabaseInitializer') as mock_init_class:
                mock_initializer = Mock()
                mock_initializer.ensure_tables_exist.return_value = True
                mock_initializer.initialize_for_user.return_value = True
                mock_init_class.return_value = mock_initializer

                initialize_database_for_current_user()

                assert "Using default user ID" in caplog.text


class TestConnectionHandling:
    """Test database connection handling and error scenarios"""

    def test_connection_error_handling(self):
        """Test handling of connection errors"""
        initializer = DatabaseInitializer(database_url="postgresql://invalid:invalid@nonexistent:9999/db")
        user_id = str(uuid.uuid4())

        # Should handle connection error gracefully
        result = initializer.create_default_project(user_id)
        assert result is None

    def test_connection_timeout_handling(self):
        """Test handling of connection timeout"""
        # Use a non-routable IP to trigger timeout
        initializer = DatabaseInitializer(database_url="postgresql://user:pass@192.0.2.1:5432/db")

        result = initializer.ensure_tables_exist()
        assert result is False

    def test_invalid_credentials_handling(self):
        """Test handling of invalid credentials"""
        initializer = DatabaseInitializer(database_url="postgresql://baduser:badpass@localhost:5432/db")

        result = initializer.ensure_tables_exist()
        assert result is False


class TestSecurityScenarios:
    """Test security-related scenarios"""

    def test_password_special_characters_in_url(self):
        """Test that passwords with special characters are handled correctly"""
        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "testdb",
            "DATABASE_USER": "user",
            "DATABASE_PASSWORD": "p@ss!w0rd#$%"
        }):
            initializer = DatabaseInitializer()

            # Password should be included in URL (actual encoding is handled by SQLAlchemy)
            assert "localhost" in initializer.database_url
            assert "user" in initializer.database_url

    def test_sql_injection_prevention_in_user_id(self):
        """Test that SQL injection attempts in user_id are prevented"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(db_url)

            # Create tables
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS project_git_branchs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        priority TEXT,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        task_count INTEGER DEFAULT 0,
                        completed_task_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.commit()

            # Try SQL injection in user_id
            malicious_user_id = "'; DROP TABLE projects; --"
            initializer = DatabaseInitializer(database_url=db_url)

            # Should handle safely due to parameterized queries
            project_id = initializer.create_default_project(malicious_user_id)

            # Project should be created (injection prevented)
            assert project_id is not None

            # Verify tables still exist
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            assert "projects" in tables

        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_user_id(self):
        """Test handling of empty user ID"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(db_url)

            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS project_git_branchs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        priority TEXT,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        task_count INTEGER DEFAULT 0,
                        completed_task_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.commit()

            initializer = DatabaseInitializer(database_url=db_url)

            # Empty string user_id should still work (database will accept it)
            project_id = initializer.create_default_project("")

            # Should create project with empty user_id
            assert project_id is not None

        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_very_long_user_id(self):
        """Test handling of very long user IDs"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(db_url)

            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS project_git_branchs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        priority TEXT,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        task_count INTEGER DEFAULT 0,
                        completed_task_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.commit()

            initializer = DatabaseInitializer(database_url=db_url)

            # Very long user ID (1000 characters)
            long_user_id = "user" * 250
            project_id = initializer.create_default_project(long_user_id)

            assert project_id is not None

        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_unicode_user_id(self):
        """Test handling of Unicode characters in user ID"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(db_url)

            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS project_git_branchs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id TEXT NOT NULL,
                        priority TEXT,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        task_count INTEGER DEFAULT 0,
                        completed_task_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

                conn.commit()

            initializer = DatabaseInitializer(database_url=db_url)

            # Unicode user ID
            unicode_user_id = "用户-ユーザー-사용자"
            project_id = initializer.create_default_project(unicode_user_id)

            assert project_id is not None

            # Verify stored correctly
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT user_id FROM projects WHERE id = :id"),
                    {"id": project_id}
                )
                stored_user_id = result.scalar()
                assert stored_user_id == unicode_user_id

        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass
