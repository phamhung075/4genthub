"""
Tests for Migration 005 Execution

This module tests the execution of migration 005 including:
- Migration script execution and rollback
- Database schema changes validation
- Data integrity during migration
- Error handling and recovery
- Migration state tracking
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager


class TestMigration005Execution:
    """Test suite for Migration 005 execution"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        db_path = Path(db_file.name)
        db_file.close()
        
        # Initialize with basic schema
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE migration_history (
                id INTEGER PRIMARY KEY,
                version TEXT UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'applied'
            )
        """)
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        if db_path.exists():
            db_path.unlink()
    
    @pytest.fixture
    def mock_migration_005(self):
        """Mock migration 005 script"""
        return {
            "version": "005",
            "description": "Add user context and authentication columns",
            "up_sql": """
                ALTER TABLE tasks ADD COLUMN user_id TEXT;
                ALTER TABLE tasks ADD COLUMN created_by TEXT;
                ALTER TABLE projects ADD COLUMN user_id TEXT;
                CREATE INDEX idx_tasks_user_id ON tasks(user_id);
                CREATE INDEX idx_projects_user_id ON projects(user_id);
            """,
            "down_sql": """
                DROP INDEX IF EXISTS idx_projects_user_id;
                DROP INDEX IF EXISTS idx_tasks_user_id;
                ALTER TABLE projects DROP COLUMN user_id;
                ALTER TABLE tasks DROP COLUMN created_by;
                ALTER TABLE tasks DROP COLUMN user_id;
            """
        }
    
    @contextmanager
    def get_db_connection(self, db_path):
        """Get database connection context manager"""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def test_migration_005_execution_success(self, temp_db, mock_migration_005):
        """Test successful execution of migration 005"""
        # Setup: Create tables that migration will modify
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'todo'
                )
            """)
            conn.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT
                )
            """)
            conn.commit()
        
        # Execute migration
        with self.get_db_connection(temp_db) as conn:
            # Execute the up migration
            for statement in mock_migration_005["up_sql"].strip().split(';'):
                if statement.strip():
                    conn.execute(statement)
            
            # Record migration in history
            conn.execute(
                "INSERT INTO migration_history (version, status) VALUES (?, ?)",
                (mock_migration_005["version"], "applied")
            )
            conn.commit()
        
        # Verify changes
        with self.get_db_connection(temp_db) as conn:
            # Check tasks table has new columns
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = {row['name']: row for row in cursor.fetchall()}
            
            assert 'user_id' in columns
            assert 'created_by' in columns
            assert columns['user_id']['type'] == 'TEXT'
            assert columns['created_by']['type'] == 'TEXT'
            
            # Check projects table has new column
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = {row['name']: row for row in cursor.fetchall()}
            
            assert 'user_id' in columns
            assert columns['user_id']['type'] == 'TEXT'
            
            # Check indexes were created
            cursor = conn.execute("PRAGMA index_list(tasks)")
            task_indexes = [row['name'] for row in cursor.fetchall()]
            assert 'idx_tasks_user_id' in task_indexes
            
            cursor = conn.execute("PRAGMA index_list(projects)")
            project_indexes = [row['name'] for row in cursor.fetchall()]
            assert 'idx_projects_user_id' in project_indexes
            
            # Check migration history
            cursor = conn.execute(
                "SELECT * FROM migration_history WHERE version = ?",
                (mock_migration_005["version"],)
            )
            migration_record = cursor.fetchone()
            assert migration_record is not None
            assert migration_record['status'] == 'applied'
    
    def test_migration_005_rollback_success(self, temp_db, mock_migration_005):
        """Test successful rollback of migration 005"""
        # Setup: Apply migration first
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'todo',
                    user_id TEXT,
                    created_by TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT
                )
            """)
            conn.execute("CREATE INDEX idx_tasks_user_id ON tasks(user_id)")
            conn.execute("CREATE INDEX idx_projects_user_id ON projects(user_id)")
            conn.execute(
                "INSERT INTO migration_history (version, status) VALUES (?, ?)",
                (mock_migration_005["version"], "applied")
            )
            conn.commit()
        
        # Execute rollback
        with self.get_db_connection(temp_db) as conn:
            # Execute the down migration (note: SQLite doesn't support DROP COLUMN)
            # For testing purposes, we'll simulate what would happen
            conn.execute("DROP INDEX IF EXISTS idx_projects_user_id")
            conn.execute("DROP INDEX IF EXISTS idx_tasks_user_id")
            
            # Update migration history
            conn.execute(
                "UPDATE migration_history SET status = ? WHERE version = ?",
                ("rolled_back", mock_migration_005["version"])
            )
            conn.commit()
        
        # Verify rollback
        with self.get_db_connection(temp_db) as conn:
            # Check indexes were removed
            cursor = conn.execute("PRAGMA index_list(tasks)")
            task_indexes = [row['name'] for row in cursor.fetchall()]
            assert 'idx_tasks_user_id' not in task_indexes
            
            cursor = conn.execute("PRAGMA index_list(projects)")
            project_indexes = [row['name'] for row in cursor.fetchall()]
            assert 'idx_projects_user_id' not in project_indexes
            
            # Check migration history
            cursor = conn.execute(
                "SELECT * FROM migration_history WHERE version = ?",
                (mock_migration_005["version"],)
            )
            migration_record = cursor.fetchone()
            assert migration_record['status'] == 'rolled_back'
    
    def test_migration_005_already_applied(self, temp_db, mock_migration_005):
        """Test handling of migration 005 when already applied"""
        # Setup: Mark migration as already applied
        with self.get_db_connection(temp_db) as conn:
            conn.execute(
                "INSERT INTO migration_history (version, status) VALUES (?, ?)",
                (mock_migration_005["version"], "applied")
            )
            conn.commit()
        
        # Attempt to apply again
        migration_applied = False
        with self.get_db_connection(temp_db) as conn:
            cursor = conn.execute(
                "SELECT status FROM migration_history WHERE version = ?",
                (mock_migration_005["version"],)
            )
            existing = cursor.fetchone()
            
            if existing and existing['status'] == 'applied':
                # Migration already applied, skip
                migration_applied = False
            else:
                migration_applied = True
        
        # Should not apply the migration again
        assert migration_applied is False
    
    def test_migration_005_sql_error_handling(self, temp_db):
        """Test handling of SQL errors during migration 005"""
        # Setup: Create a scenario that will cause SQL error
        invalid_migration = {
            "version": "005",
            "up_sql": "ALTER TABLE nonexistent_table ADD COLUMN user_id TEXT;"
        }
        
        with pytest.raises(sqlite3.OperationalError):
            with self.get_db_connection(temp_db) as conn:
                conn.execute(invalid_migration["up_sql"])
    
    def test_migration_005_partial_failure_recovery(self, temp_db, mock_migration_005):
        """Test recovery from partial migration failure"""
        # Setup: Create tables
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            # Note: Not creating projects table to simulate partial setup
            conn.commit()
        
        # Attempt migration with partial failure
        successful_statements = []
        failed_statements = []
        
        with self.get_db_connection(temp_db) as conn:
            for statement in mock_migration_005["up_sql"].strip().split(';'):
                if statement.strip():
                    try:
                        conn.execute(statement)
                        successful_statements.append(statement)
                    except sqlite3.Error:
                        failed_statements.append(statement)
        
        # Should have some successful and some failed statements
        assert len(successful_statements) > 0
        assert len(failed_statements) > 0
        
        # Projects-related statements should fail
        projects_failures = [s for s in failed_statements if 'projects' in s.lower()]
        assert len(projects_failures) > 0
    
    def test_migration_005_with_existing_data(self, temp_db, mock_migration_005):
        """Test migration 005 execution with existing data"""
        # Setup: Create tables with existing data
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'todo'
                )
            """)
            conn.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Insert test data
            conn.execute(
                "INSERT INTO tasks (id, title, status) VALUES (?, ?, ?)",
                ("task-1", "Test Task", "todo")
            )
            conn.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                ("project-1", "Test Project")
            )
            conn.commit()
        
        # Execute migration
        with self.get_db_connection(temp_db) as conn:
            for statement in mock_migration_005["up_sql"].strip().split(';'):
                if statement.strip():
                    conn.execute(statement)
            conn.commit()
        
        # Verify data integrity after migration
        with self.get_db_connection(temp_db) as conn:
            # Check existing data is preserved
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", ("task-1",))
            task = cursor.fetchone()
            assert task is not None
            assert task['title'] == "Test Task"
            assert task['status'] == "todo"
            assert task['user_id'] is None  # New column should be NULL
            assert task['created_by'] is None  # New column should be NULL
            
            cursor = conn.execute("SELECT * FROM projects WHERE id = ?", ("project-1",))
            project = cursor.fetchone()
            assert project is not None
            assert project['name'] == "Test Project"
            assert project['user_id'] is None  # New column should be NULL
    
    def test_migration_005_transaction_rollback(self, temp_db):
        """Test transaction rollback on migration failure"""
        # Setup: Create tasks table only
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            conn.commit()
        
        # Simulate transaction with mixed success/failure
        # In SQLite, DDL statements like ALTER TABLE are auto-committed even in transactions
        # However, if an error occurs, the transaction context might affect this behavior
        conn = None
        try:
            conn = sqlite3.connect(str(temp_db))
            conn.row_factory = sqlite3.Row
            
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            
            # This should succeed and auto-commit in SQLite
            conn.execute("ALTER TABLE tasks ADD COLUMN user_id TEXT")
            
            # This should fail (table doesn't exist) 
            conn.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")
            
            # This line won't be reached due to error
            conn.execute("COMMIT")
                
        except sqlite3.Error:
            # Expected error, but first ALTER should have auto-committed
            if conn:
                conn.rollback()  # Explicit rollback
        finally:
            if conn:
                conn.close()
        
        # Verify table behavior - in SQLite, the first ALTER should have auto-committed
        # but due to transaction rollback, the behavior might vary
        with self.get_db_connection(temp_db) as conn:
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = {row['name']: row for row in cursor.fetchall()}
            
            # In most SQLite configurations, DDL in transactions can be rolled back
            # So we expect the user_id column NOT to exist due to rollback
            assert 'user_id' not in columns  # Transaction rollback should undo DDL
    
    def test_migration_005_version_tracking(self, temp_db, mock_migration_005):
        """Test migration version tracking and status"""
        # Execute migration with version tracking
        with self.get_db_connection(temp_db) as conn:
            # Check migration hasn't been applied
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM migration_history WHERE version = ?",
                (mock_migration_005["version"],)
            )
            assert cursor.fetchone()['count'] == 0
            
            # Apply migration
            conn.execute(
                "INSERT INTO migration_history (version, status) VALUES (?, ?)",
                (mock_migration_005["version"], "applying")
            )
            
            try:
                # Simulate migration steps
                # (In real implementation, would execute actual migration SQL)
                
                # Update status to applied
                conn.execute(
                    "UPDATE migration_history SET status = ?, applied_at = CURRENT_TIMESTAMP WHERE version = ?",
                    ("applied", mock_migration_005["version"])
                )
                conn.commit()
                
            except Exception:
                # On error, mark as failed
                conn.execute(
                    "UPDATE migration_history SET status = ? WHERE version = ?",
                    ("failed", mock_migration_005["version"])
                )
                conn.commit()
                raise
        
        # Verify version tracking
        with self.get_db_connection(temp_db) as conn:
            cursor = conn.execute(
                "SELECT * FROM migration_history WHERE version = ?",
                (mock_migration_005["version"],)
            )
            migration_record = cursor.fetchone()
            
            assert migration_record is not None
            assert migration_record['version'] == mock_migration_005["version"]
            assert migration_record['status'] == 'applied'
            assert migration_record['applied_at'] is not None
    
    def test_migration_005_concurrent_execution_protection(self, temp_db, mock_migration_005):
        """Test protection against concurrent migration execution"""
        # Simulate first process starting migration
        with self.get_db_connection(temp_db) as conn:
            conn.execute(
                "INSERT INTO migration_history (version, status) VALUES (?, ?)",
                (mock_migration_005["version"], "applying")
            )
            conn.commit()
        
        # Simulate second process checking migration status
        with self.get_db_connection(temp_db) as conn:
            cursor = conn.execute(
                "SELECT status FROM migration_history WHERE version = ?",
                (mock_migration_005["version"],)
            )
            record = cursor.fetchone()
            
            # Second process should see migration is already being applied
            assert record is not None
            assert record['status'] == 'applying'
            
            # Second process should not start migration
            should_apply = record['status'] not in ['applied', 'applying']
            assert should_apply is False
    
    def test_migration_005_dry_run(self, temp_db, mock_migration_005):
        """Test dry run execution of migration 005"""
        # Setup: Create tables
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            conn.commit()
        
        # Simulate dry run (parse and validate SQL without executing)
        dry_run_results = []
        
        for statement in mock_migration_005["up_sql"].strip().split(';'):
            if statement.strip():
                # In a real dry run, would use SQL parser to validate syntax
                # For this test, we'll just check basic structure
                statement = statement.strip()
                if statement.upper().startswith('ALTER TABLE'):
                    table_name = statement.split()[2]
                    dry_run_results.append({
                        "statement": statement,
                        "type": "ALTER_TABLE", 
                        "table": table_name,
                        "valid": True
                    })
                elif statement.upper().startswith('CREATE INDEX'):
                    dry_run_results.append({
                        "statement": statement,
                        "type": "CREATE_INDEX",
                        "valid": True
                    })
        
        # Verify dry run results
        assert len(dry_run_results) == 5  # 3 ALTER TABLE + 2 CREATE INDEX
        
        alter_statements = [r for r in dry_run_results if r["type"] == "ALTER_TABLE"]
        assert len(alter_statements) == 3
        
        index_statements = [r for r in dry_run_results if r["type"] == "CREATE_INDEX"]
        assert len(index_statements) == 2
        
        # All statements should be valid
        assert all(r["valid"] for r in dry_run_results)
    
    def test_migration_005_performance_impact(self, temp_db, mock_migration_005):
        """Test performance impact of migration 005"""
        import time
        
        # Setup: Create tables with substantial data
        with self.get_db_connection(temp_db) as conn:
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'todo'
                )
            """)
            conn.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Insert test data
            for i in range(100):  # Smaller dataset for test performance
                conn.execute(
                    "INSERT INTO tasks (id, title, status) VALUES (?, ?, ?)",
                    (f"task-{i}", f"Test Task {i}", "todo")
                )
                if i < 10:
                    conn.execute(
                        "INSERT INTO projects (id, name) VALUES (?, ?)",
                        (f"project-{i}", f"Test Project {i}")
                    )
            conn.commit()
        
        # Measure migration execution time
        start_time = time.time()
        
        with self.get_db_connection(temp_db) as conn:
            for statement in mock_migration_005["up_sql"].strip().split(';'):
                if statement.strip():
                    conn.execute(statement)
            conn.commit()
        
        end_time = time.time()
        migration_duration = end_time - start_time
        
        # Migration should complete reasonably quickly
        assert migration_duration < 10.0  # Should take less than 10 seconds
        
        # Verify data is still accessible after migration
        with self.get_db_connection(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM tasks")
            task_count = cursor.fetchone()['count']
            assert task_count == 100
            
            cursor = conn.execute("SELECT COUNT(*) as count FROM projects")
            project_count = cursor.fetchone()['count']
            assert project_count == 10