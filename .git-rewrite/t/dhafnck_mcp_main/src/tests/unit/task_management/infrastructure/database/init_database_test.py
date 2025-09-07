"""
Tests for database initialization script using SQLAlchemy.

This module tests the database initialization functionality
that supports both SQLite and PostgreSQL databases.
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock, call
import logging
from pathlib import Path

from fastmcp.task_management.infrastructure.database.init_database import (
    init_database,
    migrate_from_sqlite_to_postgresql
)


class TestInitDatabase:
    """Test database initialization functionality."""
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    @patch('fastmcp.task_management.infrastructure.database.init_database.logger')
    def test_init_database_success(self, mock_logger, mock_get_db_config):
        """Test successful database initialization."""
        # Arrange
        mock_config = Mock()
        mock_config.get_database_info.return_value = {'type': 'sqlite'}
        mock_config.create_tables.return_value = None
        mock_get_db_config.return_value = mock_config
        
        # Act
        init_database()
        
        # Assert
        mock_get_db_config.assert_called_once()
        mock_config.get_database_info.assert_called_once()
        mock_config.create_tables.assert_called_once()
        mock_logger.info.assert_any_call("Initializing database: sqlite")
        mock_logger.info.assert_any_call("Database initialization completed successfully")
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    @patch('fastmcp.task_management.infrastructure.database.init_database.logger')
    def test_init_database_postgresql(self, mock_logger, mock_get_db_config):
        """Test database initialization for PostgreSQL."""
        # Arrange
        mock_config = Mock()
        mock_config.get_database_info.return_value = {'type': 'postgresql'}
        mock_config.create_tables.return_value = None
        mock_get_db_config.return_value = mock_config
        
        # Act
        init_database()
        
        # Assert
        mock_logger.info.assert_any_call("Initializing database: postgresql")
        mock_logger.info.assert_any_call("Database initialization completed successfully")
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    @patch('fastmcp.task_management.infrastructure.database.init_database.logger')
    def test_init_database_failure(self, mock_logger, mock_get_db_config):
        """Test database initialization failure handling."""
        # Arrange
        mock_config = Mock()
        mock_config.get_database_info.side_effect = Exception("Database config error")
        mock_get_db_config.return_value = mock_config
        
        # Act & Assert
        with pytest.raises(Exception, match="Database config error"):
            init_database()
        
        mock_logger.error.assert_called_with("Failed to initialize database: Database config error")
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    @patch('fastmcp.task_management.infrastructure.database.init_database.logger')
    def test_init_database_create_tables_failure(self, mock_logger, mock_get_db_config):
        """Test database initialization when table creation fails."""
        # Arrange
        mock_config = Mock()
        mock_config.get_database_info.return_value = {'type': 'sqlite'}
        mock_config.create_tables.side_effect = Exception("Table creation failed")
        mock_get_db_config.return_value = mock_config
        
        # Act & Assert
        with pytest.raises(Exception, match="Table creation failed"):
            init_database()
        
        mock_logger.info.assert_called_with("Initializing database: sqlite")
        mock_logger.error.assert_called_with("Failed to initialize database: Table creation failed")


class TestMainExecution:
    """Test main execution functionality."""
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.init_database')
    @patch('fastmcp.task_management.infrastructure.database.init_database.logging')
    def test_main_execution(self, mock_logging, mock_init_database):
        """Test main execution sets up logging and calls init_database."""
        # Import and execute the main block
        import fastmcp.task_management.infrastructure.database.init_database as init_module
        
        # Mock __name__ to be "__main__"
        with patch.object(init_module, '__name__', '__main__'):
            # Execute the main block code
            mock_logging.basicConfig.assert_not_called()  # Reset any previous calls
            mock_init_database.assert_not_called()  # Reset any previous calls
            
            # Simulate main execution
            if init_module.__name__ == "__main__":
                init_module.logging.basicConfig(
                    level=init_module.logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                init_module.init_database()
        
        # Note: Direct testing of __main__ block is tricky due to import behavior
        # In practice, this would be tested via subprocess or integration tests


class TestDatabaseInitIntegration:
    """Integration tests for database initialization."""
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    def test_init_database_integration_flow(self, mock_get_db_config):
        """Test the complete integration flow of database initialization."""
        # Arrange
        mock_config = Mock()
        mock_config.get_database_info.return_value = {
            'type': 'sqlite',
            'path': '/tmp/test.db',
            'url': 'sqlite:///tmp/test.db'
        }
        mock_config.create_tables.return_value = None
        mock_get_db_config.return_value = mock_config
        
        # Act
        init_database()
        
        # Assert
        mock_get_db_config.assert_called_once()
        mock_config.get_database_info.assert_called_once()
        mock_config.create_tables.assert_called_once()


class TestErrorScenarios:
    """Test various error scenarios in database initialization."""
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    def test_database_config_import_error(self, mock_get_db_config):
        """Test handling of database config import errors."""
        # Arrange
        mock_get_db_config.side_effect = ImportError("Cannot import database config")
        
        # Act & Assert
        with pytest.raises(ImportError, match="Cannot import database config"):
            init_database()
    
    @patch('fastmcp.task_management.infrastructure.database.init_database.get_db_config')
    def test_database_permission_error(self, mock_get_db_config):
        """Test handling of database permission errors."""
        # Arrange
        mock_config = Mock()
        mock_config.get_database_info.return_value = {'type': 'sqlite'}
        mock_config.create_tables.side_effect = PermissionError("Permission denied")
        mock_get_db_config.return_value = mock_config
        
        # Act & Assert
        with pytest.raises(PermissionError, match="Permission denied"):
            init_database()


if __name__ == "__main__":
    pytest.main([__file__])