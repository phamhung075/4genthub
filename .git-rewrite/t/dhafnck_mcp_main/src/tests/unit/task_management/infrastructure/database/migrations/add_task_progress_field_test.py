"""
Test suite for add_task_progress_field migration
"""
import pytest
from unittest.mock import Mock, patch, call
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from fastmcp.task_management.infrastructure.database.migrations.add_task_progress_field import (
    upgrade,
    downgrade
)


class TestAddTaskProgressFieldMigration:
    """Test the add_task_progress_field migration"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    def test_upgrade_adds_progress_percentage_column(self, mock_session):
        """Test that upgrade adds the progress_percentage column with correct constraints"""
        # Call upgrade
        upgrade(mock_session)
        
        # Verify the correct SQL was executed
        expected_sql = """
        ALTER TABLE tasks 
        ADD COLUMN IF NOT EXISTS progress_percentage INTEGER DEFAULT 0
        CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
    """
        mock_session.execute.assert_called_once()
        actual_sql = mock_session.execute.call_args[0][0]
        
        # Normalize whitespace for comparison
        assert actual_sql.strip() == expected_sql.strip()
        
        # Verify commit was called
        mock_session.commit.assert_called_once()
    
    def test_downgrade_removes_progress_percentage_column(self, mock_session):
        """Test that downgrade removes the progress_percentage column"""
        # Call downgrade
        downgrade(mock_session)
        
        # Verify the correct SQL was executed
        expected_sql = "ALTER TABLE tasks DROP COLUMN IF EXISTS progress_percentage"
        mock_session.execute.assert_called_once_with(expected_sql)
        
        # Verify commit was called
        mock_session.commit.assert_called_once()
    
    def test_upgrade_handles_database_errors(self, mock_session):
        """Test that upgrade handles database errors appropriately"""
        # Configure mock to raise an error
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        # Should raise the exception (no error handling in migration)
        with pytest.raises(SQLAlchemyError) as exc_info:
            upgrade(mock_session)
        
        assert "Database error" in str(exc_info.value)
        # Commit should not be called on error
        mock_session.commit.assert_not_called()
    
    def test_downgrade_handles_database_errors(self, mock_session):
        """Test that downgrade handles database errors appropriately"""
        # Configure mock to raise an error
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        # Should raise the exception (no error handling in migration)
        with pytest.raises(SQLAlchemyError) as exc_info:
            downgrade(mock_session)
        
        assert "Database error" in str(exc_info.value)
        # Commit should not be called on error
        mock_session.commit.assert_not_called()
    
    def test_upgrade_idempotent(self, mock_session):
        """Test that upgrade can be run multiple times safely (IF NOT EXISTS)"""
        # Run upgrade multiple times
        upgrade(mock_session)
        upgrade(mock_session)
        upgrade(mock_session)
        
        # Should be called 3 times due to IF NOT EXISTS clause
        assert mock_session.execute.call_count == 3
        assert mock_session.commit.call_count == 3
    
    def test_downgrade_idempotent(self, mock_session):
        """Test that downgrade can be run multiple times safely (IF EXISTS)"""
        # Run downgrade multiple times
        downgrade(mock_session)
        downgrade(mock_session)
        downgrade(mock_session)
        
        # Should be called 3 times due to IF EXISTS clause
        assert mock_session.execute.call_count == 3
        assert mock_session.commit.call_count == 3
    
    def test_progress_percentage_constraints(self, mock_session):
        """Test that the progress_percentage column has proper constraints"""
        # Call upgrade
        upgrade(mock_session)
        
        # Get the SQL that was executed
        actual_sql = mock_session.execute.call_args[0][0]
        
        # Verify constraints are present
        assert "DEFAULT 0" in actual_sql
        assert "CHECK (progress_percentage >= 0 AND progress_percentage <= 100)" in actual_sql
        assert "INTEGER" in actual_sql
    


class TestMigrationIntegration:
    """Integration tests for the migration (would run against a test database)"""
    
    @pytest.mark.skip(reason="Requires database setup")
    def test_migration_on_real_database(self):
        """Test migration against a real test database"""
        # This would:
        # 1. Create a test database
        # 2. Create the tasks table
        # 3. Run upgrade()
        # 4. Verify column exists with constraints
        # 5. Insert test data to verify constraints work
        # 6. Run downgrade()
        # 7. Verify column is removed
        pass
    
    @pytest.mark.skip(reason="Requires database setup")
    def test_migration_data_preservation(self):
        """Test that existing data is preserved during migration"""
        # This would:
        # 1. Create tasks table with existing data
        # 2. Run upgrade()
        # 3. Verify existing tasks have progress_percentage = 0
        # 4. Update some tasks with progress values
        # 5. Run downgrade()
        # 6. Run upgrade() again
        # 7. Verify all tasks have progress_percentage = 0 again
        pass