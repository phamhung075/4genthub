"""Test suite for add_user_id_to_project_contexts migration.

Tests the database migration script including:
- Upgrade functionality (adding user_id column)
- Downgrade functionality (removing user_id column)
- SQL execution validation
- Migration safety and idempotency
"""

import pytest
from unittest.mock import Mock, MagicMock, call
from sqlalchemy.orm import Session
from sqlalchemy import text

from fastmcp.task_management.infrastructure.database.migrations.add_user_id_to_project_contexts import (
    upgrade,
    downgrade
)


class TestAddUserIdToProjectContextsMigration:
    """Test cases for the add_user_id_to_project_contexts migration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.mock_session.execute.return_value = None
        self.mock_session.commit.return_value = None
    
    def test_upgrade_adds_user_id_column(self):
        """Test that upgrade function adds user_id column to project_contexts table."""
        upgrade(self.mock_session)
        
        # Verify SQL execution
        self.mock_session.execute.assert_called_once()
        executed_sql = self.mock_session.execute.call_args[0][0]
        
        # Check that it's a text object with correct SQL
        assert isinstance(executed_sql, type(text("")))
        sql_string = str(executed_sql)
        
        # Verify SQL contains expected elements
        assert "ALTER TABLE project_contexts" in sql_string
        assert "ADD COLUMN IF NOT EXISTS user_id" in sql_string
        assert "VARCHAR" in sql_string
        
        # Verify commit was called
        self.mock_session.commit.assert_called_once()
    
    def test_upgrade_sql_structure(self):
        """Test the structure of the upgrade SQL statement."""
        upgrade(self.mock_session)
        
        executed_sql = self.mock_session.execute.call_args[0][0]
        sql_string = str(executed_sql).strip()
        
        # Check SQL structure
        assert sql_string.startswith("ALTER TABLE project_contexts")
        assert "ADD COLUMN IF NOT EXISTS user_id VARCHAR" in sql_string
        
        # Verify it uses IF NOT EXISTS for safety
        assert "IF NOT EXISTS" in sql_string
    
    def test_upgrade_idempotency(self):
        """Test that upgrade can be run multiple times safely."""
        # Run upgrade multiple times
        upgrade(self.mock_session)
        upgrade(self.mock_session)
        upgrade(self.mock_session)
        
        # Each call should execute the same SQL with IF NOT EXISTS
        assert self.mock_session.execute.call_count == 3
        assert self.mock_session.commit.call_count == 3
        
        # All calls should have the same SQL with IF NOT EXISTS clause
        for call_args in self.mock_session.execute.call_args_list:
            sql_string = str(call_args[0][0])
            assert "IF NOT EXISTS" in sql_string
    
    def test_downgrade_removes_user_id_column(self):
        """Test that downgrade function removes user_id column from project_contexts table."""
        downgrade(self.mock_session)
        
        # Verify SQL execution
        self.mock_session.execute.assert_called_once()
        executed_sql = self.mock_session.execute.call_args[0][0]
        
        # Check that it's a text object with correct SQL
        assert isinstance(executed_sql, type(text("")))
        sql_string = str(executed_sql)
        
        # Verify SQL contains expected elements
        assert "ALTER TABLE project_contexts" in sql_string
        assert "DROP COLUMN IF EXISTS user_id" in sql_string
        
        # Verify commit was called
        self.mock_session.commit.assert_called_once()
    
    def test_downgrade_sql_structure(self):
        """Test the structure of the downgrade SQL statement."""
        downgrade(self.mock_session)
        
        executed_sql = self.mock_session.execute.call_args[0][0]
        sql_string = str(executed_sql).strip()
        
        # Check SQL structure
        assert "ALTER TABLE project_contexts DROP COLUMN IF EXISTS user_id" in sql_string
        
        # Verify it uses IF EXISTS for safety
        assert "IF EXISTS" in sql_string
    
    def test_downgrade_idempotency(self):
        """Test that downgrade can be run multiple times safely."""
        # Run downgrade multiple times
        downgrade(self.mock_session)
        downgrade(self.mock_session)
        downgrade(self.mock_session)
        
        # Each call should execute the same SQL with IF EXISTS
        assert self.mock_session.execute.call_count == 3
        assert self.mock_session.commit.call_count == 3
        
        # All calls should have the same SQL with IF EXISTS clause
        for call_args in self.mock_session.execute.call_args_list:
            sql_string = str(call_args[0][0])
            assert "IF EXISTS" in sql_string
    
    def test_upgrade_and_downgrade_are_reversible(self):
        """Test that upgrade and downgrade operations are reversible."""
        # Run upgrade then downgrade
        upgrade(self.mock_session)
        downgrade(self.mock_session)
        
        # Verify both operations were executed
        assert self.mock_session.execute.call_count == 2
        assert self.mock_session.commit.call_count == 2
        
        # Check the SQL statements
        calls = self.mock_session.execute.call_args_list
        
        # First call should be ADD COLUMN
        upgrade_sql = str(calls[0][0][0])
        assert "ADD COLUMN IF NOT EXISTS user_id" in upgrade_sql
        
        # Second call should be DROP COLUMN
        downgrade_sql = str(calls[1][0][0])
        assert "DROP COLUMN IF EXISTS user_id" in downgrade_sql
    
    def test_upgrade_handles_session_exceptions(self):
        """Test upgrade behavior when session operations fail."""
        # Mock session to raise exception on execute
        self.mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            upgrade(self.mock_session)
        
        assert "Database error" in str(exc_info.value)
        
        # Verify execute was called but commit was not
        self.mock_session.execute.assert_called_once()
        self.mock_session.commit.assert_not_called()
    
    def test_downgrade_handles_session_exceptions(self):
        """Test downgrade behavior when session operations fail."""
        # Mock session to raise exception on commit
        self.mock_session.commit.side_effect = Exception("Commit failed")
        
        with pytest.raises(Exception) as exc_info:
            downgrade(self.mock_session)
        
        assert "Commit failed" in str(exc_info.value)
        
        # Verify execute was called
        self.mock_session.execute.assert_called_once()
    
    def test_migration_uses_text_objects(self):
        """Test that migration uses SQLAlchemy text objects for raw SQL."""
        upgrade(self.mock_session)
        
        executed_arg = self.mock_session.execute.call_args[0][0]
        
        # Should be a SQLAlchemy text object
        assert isinstance(executed_arg, type(text("")))
        
        # Test downgrade as well
        self.mock_session.reset_mock()
        downgrade(self.mock_session)
        
        executed_arg = self.mock_session.execute.call_args[0][0]
        assert isinstance(executed_arg, type(text("")))
    
    def test_migration_column_specification(self):
        """Test that the user_id column is specified correctly."""
        upgrade(self.mock_session)
        
        executed_sql = self.mock_session.execute.call_args[0][0]
        sql_string = str(executed_sql)
        
        # Verify column type specification
        assert "user_id VARCHAR" in sql_string
        
        # Verify it's nullable (no NOT NULL constraint)
        assert "NOT NULL" not in sql_string
    
    def test_migration_table_specification(self):
        """Test that the migration targets the correct table."""
        # Test upgrade
        upgrade(self.mock_session)
        upgrade_sql = str(self.mock_session.execute.call_args[0][0])
        assert "project_contexts" in upgrade_sql
        
        # Test downgrade
        self.mock_session.reset_mock()
        downgrade(self.mock_session)
        downgrade_sql = str(self.mock_session.execute.call_args[0][0])
        assert "project_contexts" in downgrade_sql
    
    def test_migration_safety_clauses(self):
        """Test that migration includes safety clauses to prevent errors."""
        # Test upgrade safety
        upgrade(self.mock_session)
        upgrade_sql = str(self.mock_session.execute.call_args[0][0])
        assert "IF NOT EXISTS" in upgrade_sql
        
        # Test downgrade safety
        self.mock_session.reset_mock()
        downgrade(self.mock_session)
        downgrade_sql = str(self.mock_session.execute.call_args[0][0])
        assert "IF EXISTS" in downgrade_sql
    
    def test_migration_session_lifecycle(self):
        """Test that migration properly manages session lifecycle."""
        # Test upgrade session management
        upgrade(self.mock_session)
        
        # Should call execute then commit
        assert self.mock_session.execute.call_count == 1
        assert self.mock_session.commit.call_count == 1
        
        # Reset and test downgrade
        self.mock_session.reset_mock()
        downgrade(self.mock_session)
        
        # Should call execute then commit
        assert self.mock_session.execute.call_count == 1
        assert self.mock_session.commit.call_count == 1
    
    def test_migration_functions_exist(self):
        """Test that required migration functions are available."""
        # Import should work without errors
        from fastmcp.task_management.infrastructure.database.migrations.add_user_id_to_project_contexts import (
            upgrade,
            downgrade
        )
        
        # Functions should be callable
        assert callable(upgrade)
        assert callable(downgrade)
    
    def test_migration_module_structure(self):
        """Test the migration module structure and imports."""
        # Test that module can be imported
        import fastmcp.task_management.infrastructure.database.migrations.add_user_id_to_project_contexts as migration_module
        
        # Should have upgrade and downgrade functions
        assert hasattr(migration_module, 'upgrade')
        assert hasattr(migration_module, 'downgrade')
        
        # Should have required imports
        assert hasattr(migration_module, 'Session')
        assert hasattr(migration_module, 'text')
        assert hasattr(migration_module, 'Column')
        assert hasattr(migration_module, 'String')
    
    def test_migration_can_run_standalone(self):
        """Test that migration file can be executed standalone."""
        # This tests the __main__ block functionality
        import fastmcp.task_management.infrastructure.database.migrations.add_user_id_to_project_contexts as migration_module
        
        # Should have the Base declarative_base
        assert hasattr(migration_module, 'Base')
        
        # Base should be properly configured
        from sqlalchemy.orm import declarative_base
        assert isinstance(migration_module.Base, type(declarative_base()))
    
    def test_migration_sql_formatting(self):
        """Test that migration SQL is properly formatted."""
        upgrade(self.mock_session)
        
        executed_sql = self.mock_session.execute.call_args[0][0]
        sql_string = str(executed_sql).strip()
        
        # Should be properly formatted (no extra whitespace issues)
        lines = [line.strip() for line in sql_string.split('\n') if line.strip()]
        
        # Should have the main ALTER TABLE statement
        assert any("ALTER TABLE project_contexts" in line for line in lines)
        assert any("ADD COLUMN IF NOT EXISTS user_id VARCHAR" in line for line in lines)