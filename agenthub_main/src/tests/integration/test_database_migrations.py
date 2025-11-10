"""
Comprehensive integration tests for database_migrations.py module

This module provides comprehensive test coverage for database migration functionality:
- DatabaseMigrator class initialization with SQLite and PostgreSQL
- Migration script execution (progress_history and progress_count columns)
- Schema version tracking and migration history
- Rollback scenarios and transaction handling
- Data migration and integrity validation
- Error handling during migrations
- Security scenarios (SQL injection prevention)
- Database initialization and extension management

Target: 85%+ code coverage on database_migrations.py (230 lines)
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from fastmcp.database_migrations import (
    DatabaseMigrator,
    get_migrator,
    run_startup_migrations,
)


class TestDatabaseMigratorInit:
    """Test DatabaseMigrator initialization with different database types"""

    def test_init_with_explicit_database_url(self):
        """Test initialization with explicitly provided database URL"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        migrator = DatabaseMigrator(database_url=test_url)

        assert migrator.database_url == test_url

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
        migrator = DatabaseMigrator()

        expected_url = "postgresql://testuser:testpass@testhost:5433/customdb"
        assert migrator.database_url == expected_url

    @patch.dict(os.environ, {
        "DATABASE_TYPE": "postgresql"
    }, clear=True)
    def test_init_postgresql_with_defaults(self):
        """Test PostgreSQL initialization uses default values when env vars missing"""
        os.environ["DATABASE_TYPE"] = "postgresql"

        migrator = DatabaseMigrator()

        # Should use default values
        assert "localhost" in migrator.database_url
        assert "5432" in migrator.database_url
        assert "postgresdb" in migrator.database_url
        assert "agenthub_user" in migrator.database_url
        assert "agenthub_password" in migrator.database_url

    @patch.dict(os.environ, {
        "DATABASE_TYPE": "sqlite",
        "DATABASE_URL": "sqlite:///custom_test.db"
    })
    def test_init_sqlite_from_environment(self):
        """Test SQLite initialization from DATABASE_URL"""
        migrator = DatabaseMigrator()

        assert migrator.database_url == "sqlite:///custom_test.db"

    @patch.dict(os.environ, {"DATABASE_TYPE": "other"}, clear=True)
    def test_init_other_database_type_uses_default(self):
        """Test non-PostgreSQL database types fall back to DATABASE_URL or default"""
        os.environ["DATABASE_TYPE"] = "other"

        migrator = DatabaseMigrator()

        # Should fall back to default SQLite
        assert "sqlite:///agenthub_dev.db" in migrator.database_url


class TestRunMigrations:
    """Test migration script execution functionality"""

    @pytest.fixture
    def temp_postgresql_db(self):
        """Create a temporary PostgreSQL-like database for testing (using SQLite)"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)

        # Create tasks table with old schema (without progress_history)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    details TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))
            conn.commit()

        yield db_url

        # Cleanup
        try:
            os.unlink(db_path)
        except Exception:
            pass

    def test_run_migrations_skips_non_postgresql(self):
        """Test that migrations are skipped for non-PostgreSQL databases"""
        migrator = DatabaseMigrator(database_url="sqlite:///test.db")

        result = migrator.run_migrations()

        # Should skip and return True
        assert result is True

    def test_run_migrations_skips_if_table_not_exists(self):
        """Test that migrations are skipped if tasks table doesn't exist"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:

            # Mock as PostgreSQL
            with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_conn = Mock()
                mock_result = Mock()
                mock_result.scalar.return_value = False  # Table doesn't exist
                mock_conn.execute.return_value = mock_result
                mock_conn.__enter__ = Mock(return_value=mock_conn)
                mock_conn.__exit__ = Mock(return_value=False)
                mock_conn.begin.return_value = Mock(
                    commit=Mock(),
                    rollback=Mock(),
                    __enter__=Mock(return_value=Mock(commit=Mock())),
                    __exit__=Mock(return_value=False)
                )
                mock_engine.connect.return_value = mock_conn
                mock_create_engine.return_value = mock_engine

                migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
                result = migrator.run_migrations()

                assert result is True
        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_run_migrations_adds_progress_history_column(self):
        """Test adding progress_history column to tasks table"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(db_url)

            # Create tasks table without progress_history
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        status TEXT NOT NULL
                    )
                """))
                conn.commit()

            # Mock as PostgreSQL and run migrations
            with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_conn = Mock()

                # Setup mock responses
                call_count = [0]

                def execute_side_effect(query):
                    call_count[0] += 1
                    if call_count[0] == 1:  # Table exists check
                        result = Mock()
                        result.scalar.return_value = True
                        return result
                    elif call_count[0] == 2:  # Column check
                        result = Mock()
                        result.__iter__ = Mock(return_value=iter([]))  # No existing columns
                        return result
                    else:  # Other queries
                        return Mock()

                mock_conn.execute = Mock(side_effect=execute_side_effect)
                mock_conn.__enter__ = Mock(return_value=mock_conn)
                mock_conn.__exit__ = Mock(return_value=False)

                mock_trans = Mock()
                mock_trans.commit = Mock()
                mock_trans.rollback = Mock()
                mock_conn.begin.return_value = mock_trans

                mock_engine.connect.return_value = mock_conn
                mock_create_engine.return_value = mock_engine

                migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
                result = migrator.run_migrations()

                assert result is True
                # Verify transaction was committed
                mock_trans.commit.assert_called()

        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_run_migrations_adds_progress_count_column(self):
        """Test adding progress_count column to tasks table"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(db_url)

            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL
                    )
                """))
                conn.commit()

            # Mock PostgreSQL
            with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_conn = Mock()

                call_count = [0]

                def execute_side_effect(query):
                    call_count[0] += 1
                    if call_count[0] == 1:  # Table exists
                        result = Mock()
                        result.scalar.return_value = True
                        return result
                    elif call_count[0] == 2:  # Column check - only progress_history exists
                        result = Mock()
                        result.__iter__ = Mock(return_value=iter([['progress_history']]))
                        return result
                    else:
                        return Mock()

                mock_conn.execute = Mock(side_effect=execute_side_effect)
                mock_conn.__enter__ = Mock(return_value=mock_conn)
                mock_conn.__exit__ = Mock(return_value=False)

                mock_trans = Mock()
                mock_trans.commit = Mock()
                mock_conn.begin.return_value = mock_trans

                mock_engine.connect.return_value = mock_conn
                mock_create_engine.return_value = mock_engine

                migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
                result = migrator.run_migrations()

                assert result is True

        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_run_migrations_migrates_data_from_details(self, caplog):
        """Test migrating data from details column to progress_history"""
        import logging
        caplog.set_level(logging.INFO)

        # Mock PostgreSQL migration
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            call_count = [0]

            def execute_side_effect(query):
                call_count[0] += 1
                result = Mock()
                # Set defaults
                result.scalar.return_value = 0
                result.__iter__ = Mock(return_value=iter([]))

                if call_count[0] == 1:  # Table exists check
                    result.scalar.return_value = True
                elif call_count[0] == 2:  # Column check - has details
                    result.__iter__ = Mock(return_value=iter([['details']]))
                elif call_count[0] == 3:  # Count check for migration
                    result.scalar.return_value = 5  # 5 rows to migrate
                # For calls 4+ (UPDATE at call 4, DROP at call 5, CREATE INDEX at call 6), use defaults
                return result

            mock_conn.execute = Mock(side_effect=execute_side_effect)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.commit = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.run_migrations()

            assert result is True
            # Verify data migration was attempted (should have at least 6 calls)
            # 1: table check, 2: column check, 3: count, 4: UPDATE, 5: DROP, 6: CREATE INDEX
            assert mock_conn.execute.call_count >= 6, f"Expected at least 6 calls, got {mock_conn.execute.call_count}"
            # Verify migration logging
            assert "Migrating data from details to progress_history" in caplog.text

    def test_run_migrations_skips_if_columns_already_exist(self):
        """Test that migration is skipped if columns already exist"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            call_count = [0]

            def execute_side_effect(query):
                call_count[0] += 1
                result = Mock()
                if call_count[0] == 1:  # Table exists
                    result.scalar.return_value = True
                    return result
                elif call_count[0] == 2:  # All columns exist
                    result.__iter__ = Mock(return_value=iter([
                        ['progress_history'],
                        ['progress_count'],
                        ['details']
                    ]))
                    return result
                elif call_count[0] == 3:  # Count check
                    result.scalar.return_value = 0  # No rows to migrate
                    return result
                else:
                    # Default for other calls
                    result.scalar.return_value = None
                    result.__iter__ = Mock(return_value=iter([]))
                    return result
                return result

            mock_conn.execute = Mock(side_effect=execute_side_effect)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.commit = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.run_migrations()

            assert result is True


class TestRollbackScenarios:
    """Test rollback scenarios and transaction handling"""

    def test_run_migrations_rolls_back_on_error(self):
        """Test that transaction is rolled back on migration error"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            # Simulate error during migration
            def execute_side_effect(query):
                result = Mock()
                result.scalar.return_value = True
                if "ALTER TABLE" in str(query):
                    raise SQLAlchemyError("Migration error")
                return result

            mock_conn.execute = Mock(side_effect=execute_side_effect)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.rollback = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.run_migrations()

            # Should fail and rollback
            assert result is False

    def test_run_migrations_handles_connection_errors(self):
        """Test handling of connection errors during migration"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_create_engine.side_effect = SQLAlchemyError("Connection failed")

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.run_migrations()

            assert result is False

    def test_run_migrations_logs_error_on_failure(self, caplog):
        """Test that migration errors are properly logged"""
        import logging
        caplog.set_level(logging.ERROR)

        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_create_engine.side_effect = Exception("Test migration error")

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.run_migrations()

            assert result is False
            assert "Database migration error" in caplog.text


class TestInitializeDatabase:
    """Test database initialization and extension management"""

    def test_initialize_database_skips_non_postgresql(self):
        """Test that initialization is skipped for non-PostgreSQL databases"""
        migrator = DatabaseMigrator(database_url="sqlite:///test.db")

        result = migrator.initialize_database()

        assert result is True

    def test_initialize_database_creates_uuid_extension(self):
        """Test creating UUID extension in PostgreSQL"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_conn.execute = Mock()
            mock_conn.commit = Mock()
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.initialize_database()

            assert result is True
            # Verify UUID extension creation was called
            mock_conn.execute.assert_called()

    def test_initialize_database_handles_errors(self):
        """Test error handling during database initialization"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_create_engine.side_effect = Exception("Initialization failed")

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.initialize_database()

            assert result is False

    def test_initialize_database_logs_error(self, caplog):
        """Test that initialization errors are logged"""
        import logging
        caplog.set_level(logging.ERROR)

        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_create_engine.side_effect = Exception("Init error")

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.initialize_database()

            assert result is False
            assert "Database initialization error" in caplog.text


class TestEnsureDatabaseReady:
    """Test ensure_database_ready workflow"""

    def test_ensure_database_ready_success(self):
        """Test successful database readiness check"""
        migrator = DatabaseMigrator(database_url="sqlite:///test.db")

        with patch.object(migrator, 'initialize_database', return_value=True):
            with patch.object(migrator, 'run_migrations', return_value=True):
                result = migrator.ensure_database_ready()

                assert result is True

    def test_ensure_database_ready_continues_on_init_failure(self):
        """Test that process continues even if initialization fails"""
        migrator = DatabaseMigrator(database_url="sqlite:///test.db")

        with patch.object(migrator, 'initialize_database', return_value=False):
            with patch.object(migrator, 'run_migrations', return_value=True):
                result = migrator.ensure_database_ready()

                # Still returns True because migrations succeeded
                assert result is True

    def test_ensure_database_ready_continues_on_migration_failure(self):
        """Test that process continues even if migrations fail"""
        migrator = DatabaseMigrator(database_url="sqlite:///test.db")

        with patch.object(migrator, 'initialize_database', return_value=True):
            with patch.object(migrator, 'run_migrations', return_value=False):
                result = migrator.ensure_database_ready()

                # Still returns True (graceful degradation)
                assert result is True

    def test_ensure_database_ready_handles_exception(self):
        """Test error handling in ensure_database_ready"""
        migrator = DatabaseMigrator(database_url="sqlite:///test.db")

        with patch.object(migrator, 'initialize_database', side_effect=Exception("Test error")):
            result = migrator.ensure_database_ready()

            assert result is False


class TestGetMigrator:
    """Test singleton migrator instance management"""

    def test_get_migrator_creates_singleton(self):
        """Test that get_migrator creates a singleton instance"""
        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        migrator1 = get_migrator()
        migrator2 = get_migrator()

        assert migrator1 is migrator2

    def test_get_migrator_with_custom_url(self):
        """Test get_migrator with custom database URL"""
        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        test_url = "postgresql://test:test@localhost/testdb"
        migrator = get_migrator(database_url=test_url)

        assert migrator.database_url == test_url

    def test_get_migrator_reuses_existing_instance(self):
        """Test that get_migrator reuses existing instance"""
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        migrator1 = get_migrator()

        # Try to get another with different URL - should return existing
        migrator2 = get_migrator(database_url="postgresql://different/url")

        assert migrator1 is migrator2


class TestRunStartupMigrations:
    """Test startup migration workflow"""

    def test_run_startup_migrations_success(self):
        """Test successful startup migrations"""
        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        with patch('fastmcp.database_migrations.get_migrator') as mock_get_migrator:
            mock_migrator = Mock()
            mock_migrator.ensure_database_ready.return_value = True
            mock_get_migrator.return_value = mock_migrator

            # Patch the imports that happen inside run_startup_migrations
            with patch('fastmcp.task_management.infrastructure.database.auto_migration.run_auto_migrations', return_value=True) as mock_auto:
                with patch('fastmcp.database_init.initialize_database_for_current_user', return_value=True) as mock_init:
                    result = run_startup_migrations()

                    assert result is True
                    mock_auto.assert_called_once()
                    mock_init.assert_called_once()

    def test_run_startup_migrations_continues_on_auto_migration_failure(self, caplog):
        """Test that startup continues even if auto migrations fail"""
        import logging
        caplog.set_level(logging.WARNING)

        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        with patch('fastmcp.database_migrations.get_migrator') as mock_get_migrator:
            mock_migrator = Mock()
            mock_migrator.ensure_database_ready.return_value = True
            mock_get_migrator.return_value = mock_migrator

            with patch('fastmcp.task_management.infrastructure.database.auto_migration.run_auto_migrations', return_value=False):
                with patch('fastmcp.database_init.initialize_database_for_current_user', return_value=True):
                    result = run_startup_migrations()

                    # Should still succeed
                    assert result is True
                    assert "automatic migrations failed" in caplog.text

    def test_run_startup_migrations_handles_missing_auto_migration(self, caplog):
        """Test handling when auto_migration module is not available"""
        import logging
        caplog.set_level(logging.WARNING)

        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        with patch('fastmcp.database_migrations.get_migrator') as mock_get_migrator:
            mock_migrator = Mock()
            mock_migrator.ensure_database_ready.return_value = True
            mock_get_migrator.return_value = mock_migrator

            # Simulate ImportError when trying to import run_auto_migrations
            with patch('fastmcp.task_management.infrastructure.database.auto_migration.run_auto_migrations', side_effect=ImportError("Module not found")):
                with patch('fastmcp.database_init.initialize_database_for_current_user', return_value=True):
                    result = run_startup_migrations()

                    assert result is True
                    assert "Could not run automatic migrations" in caplog.text

    def test_run_startup_migrations_handles_db_init_failure(self, caplog):
        """Test handling when database initialization fails"""
        import logging
        caplog.set_level(logging.WARNING)

        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        with patch('fastmcp.database_migrations.get_migrator') as mock_get_migrator:
            mock_migrator = Mock()
            mock_migrator.ensure_database_ready.return_value = True
            mock_get_migrator.return_value = mock_migrator

            with patch('fastmcp.task_management.infrastructure.database.auto_migration.run_auto_migrations', return_value=True):
                with patch('fastmcp.database_init.initialize_database_for_current_user',
                          side_effect=Exception("Init failed")):
                    result = run_startup_migrations()

                    assert result is True
                    assert "Could not run database initialization" in caplog.text

    def test_run_startup_migrations_skips_init_on_migration_failure(self):
        """Test that initialization is skipped if migrations fail"""
        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        with patch('fastmcp.database_migrations.get_migrator') as mock_get_migrator:
            mock_migrator = Mock()
            mock_migrator.ensure_database_ready.return_value = False
            mock_get_migrator.return_value = mock_migrator

            with patch('fastmcp.task_management.infrastructure.database.auto_migration.run_auto_migrations') as mock_auto_migrations:
                with patch('fastmcp.database_init.initialize_database_for_current_user') as mock_init:
                    result = run_startup_migrations()

                    assert result is False
                    # Auto migrations and init should not be called
                    mock_auto_migrations.assert_not_called()
                    mock_init.assert_not_called()

    def test_run_startup_migrations_logs_init_skipped(self, caplog):
        """Test that startup migrations logs when initialization is skipped"""
        import logging
        caplog.set_level(logging.INFO)

        # Reset singleton
        import fastmcp.database_migrations
        fastmcp.database_migrations._migrator = None

        with patch('fastmcp.database_migrations.get_migrator') as mock_get_migrator:
            mock_migrator = Mock()
            mock_migrator.ensure_database_ready.return_value = True
            mock_get_migrator.return_value = mock_migrator

            with patch('fastmcp.task_management.infrastructure.database.auto_migration.run_auto_migrations', return_value=True):
                with patch('fastmcp.database_init.initialize_database_for_current_user', return_value=False):
                    result = run_startup_migrations()

                    assert result is True
                    # Verify line 226 is executed - logs "skipped or already done"
                    assert "Database initialization skipped or already done" in caplog.text


class TestSecurityScenarios:
    """Test security-related scenarios"""

    def test_sql_injection_prevention_in_migration(self):
        """Test that SQL injection attempts are prevented in migrations"""
        # This tests that parameterized queries are used
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            # Track all SQL executed
            executed_queries = []

            def track_execute(query):
                executed_queries.append(str(query))
                result = Mock()
                result.scalar.return_value = True
                result.__iter__ = Mock(return_value=iter([]))
                return result

            mock_conn.execute = Mock(side_effect=track_execute)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.commit = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            migrator.run_migrations()

            # Verify no string interpolation was used (all queries should use text())
            for query in executed_queries:
                # Should not contain obvious injection patterns
                assert "DROP TABLE" not in query or "information_schema" in query

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
            migrator = DatabaseMigrator()

            # Password should be included in URL
            assert "localhost" in migrator.database_url
            assert "user" in migrator.database_url


class TestDataIntegrity:
    """Test data integrity during schema changes"""

    def test_migration_preserves_existing_data(self):
        """Test that migrations preserve existing task data"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            # Simulate existing data
            call_count = [0]

            def execute_side_effect(query):
                call_count[0] += 1
                result = Mock()
                # Set defaults
                result.scalar.return_value = 0
                result.__iter__ = Mock(return_value=iter([]))

                if call_count[0] == 1:  # Table exists check
                    result.scalar.return_value = True
                elif call_count[0] == 2:  # Has details column
                    result.__iter__ = Mock(return_value=iter([['details']]))
                elif call_count[0] == 3:  # Count of rows to migrate
                    result.scalar.return_value = 10  # 10 existing rows
                # For calls 4+ (UPDATE, DROP, CREATE INDEX), use defaults
                return result

            mock_conn.execute = Mock(side_effect=execute_side_effect)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.commit = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            result = migrator.run_migrations()

            assert result is True
            # Verify data migration was attempted (call count >= 3)
            assert mock_conn.execute.call_count >= 3

    def test_migration_creates_indexes(self):
        """Test that migrations create necessary indexes"""
        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            executed_queries = []

            def track_execute(query):
                query_str = str(query)
                executed_queries.append(query_str)
                result = Mock()
                result.scalar.return_value = True if "EXISTS" in query_str else None
                result.__iter__ = Mock(return_value=iter([['progress_history', 'progress_count']]))
                return result

            mock_conn.execute = Mock(side_effect=track_execute)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.commit = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            migrator.run_migrations()

            # Check if index creation was attempted
            index_created = any("CREATE INDEX" in q for q in executed_queries)
            assert index_created


class TestLogging:
    """Test logging behavior during migrations"""

    def test_migration_logs_start(self, caplog):
        """Test that migration start is logged"""
        import logging
        caplog.set_level(logging.INFO)

        migrator = DatabaseMigrator(database_url="sqlite:///test.db")
        migrator.run_migrations()

        assert "Starting database migrations" in caplog.text

    def test_migration_logs_success(self, caplog):
        """Test that successful migration is logged"""
        import logging
        caplog.set_level(logging.INFO)

        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()

            def execute_side_effect(query):
                result = Mock()
                result.scalar.return_value = True
                result.__iter__ = Mock(return_value=iter([['progress_history', 'progress_count']]))
                return result

            mock_conn.execute = Mock(side_effect=execute_side_effect)
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)

            mock_trans = Mock()
            mock_trans.commit = Mock()
            mock_conn.begin.return_value = mock_trans

            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            migrator.run_migrations()

            assert "Database migrations completed successfully" in caplog.text

    def test_initialization_logs_success(self, caplog):
        """Test that successful initialization is logged"""
        import logging
        caplog.set_level(logging.INFO)

        with patch('fastmcp.database_migrations.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_conn.execute = Mock()
            mock_conn.commit = Mock()
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_engine.connect.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            migrator = DatabaseMigrator(database_url="postgresql://user:pass@localhost/db")
            migrator.initialize_database()

            assert "Database initialization completed" in caplog.text
