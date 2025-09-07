"""
Test Isolation Utilities

Provides utilities for test isolation, cleanup, and environment management.
Consolidated from various test isolation patterns across the project.
"""
from sqlalchemy import text
from contextlib import contextmanager
import logging
import uuid
import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any

logger = logging.getLogger(__name__)


class IsolatedTestEnvironmentConfig:
    """Configuration for isolated test environment"""
    def __init__(self, temp_dir, test_files):
        self.temp_dir = temp_dir
        self.test_files = test_files
        self.test_projects = {}

    def add_test_project(self, project_id, project_data):
        """Add a test project to the environment."""
        self.test_projects[project_id] = project_data


@contextmanager
def isolated_test_environment(test_id: str) -> Generator[IsolatedTestEnvironmentConfig, None, None]:
    """
    Create an isolated test environment with temporary files and cleanup.
    
    Args:
        test_id: Unique identifier for the test
        
    Yields:
        IsolatedTestEnvironmentConfig: Configuration object for the test environment
    """
    temp_dir = tempfile.mkdtemp(prefix=f'test_{test_id}_')
    
    config = IsolatedTestEnvironmentConfig(
        temp_dir=temp_dir,
        test_files={
            'projects': os.path.join(temp_dir, f'{test_id}_projects.test.json'),
            'tasks': os.path.join(temp_dir, f'{test_id}_tasks.test.json'),
            'agents': os.path.join(temp_dir, f'{test_id}_agents.test.json')
        }
    )
    
    try:
        yield config
    finally:
        # Cleanup temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Could not cleanup temp directory {temp_dir}: {e}")


def is_test_data_file(file_path: Path) -> bool:
    """
    Check if a file path represents a test data file.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if the path represents a test data file
    """
    file_path = Path(file_path)
    
    # Check for test file patterns
    return (
        file_path.name.endswith('.test.json') or
        file_path.name.endswith('.test.db') or
        'test' in file_path.name.lower() or
        'temp' in str(file_path).lower() or
        file_path.name.startswith('dhafnck_test_') or
        'pytest' in str(file_path).lower()
    )


def cleanup_test_data_files_only(test_root: Path) -> int:
    """
    Clean up only test data files, preserving source and configuration files.
    
    Args:
        test_root: Root directory to search for test files
        
    Returns:
        int: Number of files cleaned up
    """
    cleanup_count = 0
    test_root = Path(test_root)
    
    if not test_root.exists():
        return cleanup_count
    
    # Find and remove test data files
    for file_path in test_root.rglob("*"):
        if file_path.is_file() and is_test_data_file(file_path):
            try:
                file_path.unlink()
                cleanup_count += 1
            except Exception as e:
                logger.warning(f"Could not remove test file {file_path}: {e}")
    
    # Clean up empty test directories
    for dir_path in test_root.rglob("*"):
        if (dir_path.is_dir() and 
            'test' in dir_path.name.lower() and
            not any(dir_path.iterdir())):  # Empty directory
            try:
                dir_path.rmdir()
            except Exception as e:
                logger.warning(f"Could not remove empty test directory {dir_path}: {e}")
    
    return cleanup_count


def cleanup_test_data(session, preserve_defaults=True):
    """
    Clean up test data from PostgreSQL, preserving defaults.
    
    Call this before/after tests to ensure clean state.
    """
    try:
        if preserve_defaults:
            # Clean in dependency order to avoid FK violations
            
            # 1. Clean subtasks (except those belonging to default project)
            session.execute(text("""
                DELETE FROM subtasks WHERE task_id IN (
                    SELECT t.id FROM tasks t
                    JOIN project_git_branchs b ON t.git_branch_id = b.id
                    WHERE b.project_id != 'default_project'
                )
            """))
            
            # 2. Clean task contexts
            session.execute(text("""
                DELETE FROM task_contexts WHERE task_id IN (
                    SELECT t.id FROM tasks t
                    JOIN project_git_branchs b ON t.git_branch_id = b.id
                    WHERE b.project_id != 'default_project'
                )
            """))
            
            # 3. Clean tasks
            session.execute(text("""
                DELETE FROM tasks WHERE git_branch_id IN (
                    SELECT id FROM project_git_branchs 
                    WHERE project_id != 'default_project'
                )
            """))
            
            # 4. Clean branch contexts
            session.execute(text("""
                DELETE FROM branch_contexts WHERE branch_id IN (
                    SELECT id FROM project_git_branchs 
                    WHERE project_id != 'default_project'
                )
            """))
            
            # 5. Clean branches
            session.execute(text("""
                DELETE FROM project_git_branchs 
                WHERE project_id != 'default_project'
            """))
            
            # 6. Clean project contexts
            session.execute(text("""
                DELETE FROM project_contexts 
                WHERE project_id != 'default_project'
            """))
            
            # 7. Clean projects
            session.execute(text("""
                DELETE FROM projects 
                WHERE id != 'default_project'
            """))
            
            # 8. Clean non-singleton global contexts
            session.execute(text("""
                DELETE FROM global_contexts 
                WHERE id != 'global_singleton'
            """))
            
        else:
            # Full cleanup (careful with this!)
            tables = [
                'subtasks', 'task_contexts', 'tasks',
                'branch_contexts', 'project_git_branchs',
                'project_contexts', 'projects', 'global_contexts'
            ]
            for table in tables:
                session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        
        session.commit()
        logger.debug("Test data cleanup completed")
        
    except Exception as e:
        logger.warning(f"Cleanup error (rolling back): {e}")
        session.rollback()


def create_unique_id(prefix="test"):
    """Create a unique ID for test data to avoid conflicts."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@contextmanager
def isolated_test_data(session):
    """
    Context manager for test data isolation.
    
    Usage:
        with isolated_test_data(session) as test_ids:
            # test_ids.project_id, test_ids.branch_id, etc. are unique
            # Create your test data using these IDs
            pass
        # Data is automatically cleaned up
    """
    class TestIds:
        def __init__(self):
            self.project_id = create_unique_id("proj")
            self.branch_id = create_unique_id("branch")
            self.task_id = create_unique_id("task")
            self.context_id = create_unique_id("ctx")
            self.agent_id = create_unique_id("agent")
    
    test_ids = TestIds()
    created_ids = []
    
    try:
        yield test_ids
    finally:
        # Clean up any data created with these IDs
        try:
            session.execute(text("""
                DELETE FROM subtasks WHERE task_id = :task_id
            """), {'task_id': test_ids.task_id})
            
            session.execute(text("""
                DELETE FROM task_contexts WHERE task_id = :task_id
            """), {'task_id': test_ids.task_id})
            
            session.execute(text("""
                DELETE FROM tasks WHERE id = :task_id
            """), {'task_id': test_ids.task_id})
            
            session.execute(text("""
                DELETE FROM branch_contexts WHERE branch_id = :branch_id
            """), {'branch_id': test_ids.branch_id})
            
            session.execute(text("""
                DELETE FROM project_git_branchs WHERE id = :branch_id
            """), {'branch_id': test_ids.branch_id})
            
            session.execute(text("""
                DELETE FROM project_contexts WHERE project_id = :project_id
            """), {'project_id': test_ids.project_id})
            
            session.execute(text("""
                DELETE FROM projects WHERE id = :project_id
            """), {'project_id': test_ids.project_id})
            
            session.execute(text("""
                DELETE FROM global_contexts WHERE id = :context_id
            """), {'context_id': test_ids.context_id})
            
            session.commit()
        except Exception as e:
            logger.debug(f"Cleanup in context manager: {e}")
            session.rollback()


def use_on_conflict_for_insert(table, columns, values, conflict_columns=None):
    """
    Generate an INSERT statement with ON CONFLICT handling.
    
    This prevents duplicate key errors in PostgreSQL.
    """
    if conflict_columns is None:
        conflict_columns = ['id']
    
    columns_str = ', '.join(columns)
    values_placeholders = ', '.join(f':{col}' for col in columns)
    conflict_cols_str = ', '.join(conflict_columns)
    
    # For ON CONFLICT DO UPDATE, update all non-key columns
    update_cols = [col for col in columns if col not in conflict_columns]
    update_str = ', '.join(f'{col} = EXCLUDED.{col}' for col in update_cols)
    
    if update_str:
        query = f"""
            INSERT INTO {table} ({columns_str})
            VALUES ({values_placeholders})
            ON CONFLICT ({conflict_cols_str}) DO UPDATE SET {update_str}
        """
    else:
        # If only key columns, just do nothing on conflict
        query = f"""
            INSERT INTO {table} ({columns_str})
            VALUES ({values_placeholders})
            ON CONFLICT ({conflict_cols_str}) DO NOTHING
        """
    
    return query, values