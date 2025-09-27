"""
PostgreSQL Test Isolation Fixtures

Provides fixtures that ensure proper test isolation when using PostgreSQL.
Handles cleanup, transaction management, and data isolation between tests.
"""
import pytest
from contextlib import contextmanager
from sqlalchemy import text
from typing import Generator, Any
import logging

logger = logging.getLogger(__name__)


@contextmanager
def isolated_postgresql_test():
    """
    Context manager that ensures PostgreSQL test isolation.
    
    Features:
    - Cleans up existing test data before test
    - Uses savepoints for nested transactions
    - Rolls back all changes after test
    - Handles constraint violations gracefully
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    db_config = get_db_config()
    
    # Get a session for the entire test
    with db_config.get_session() as session:
        try:
            # Clean up any leftover test data (except defaults)
            _cleanup_test_data(session)
            
            # Start a savepoint for this test
            session.begin_nested()
            
            yield session
            
            # Rollback the savepoint
            session.rollback()
            
        except Exception as e:
            logger.error(f"Test isolation error: {e}")
            session.rollback()
            raise
        finally:
            # Ensure we're in a clean state
            try:
                session.rollback()
            except:
                pass


def _cleanup_test_data(session):
    """Clean up test data while preserving default test fixtures"""
    try:
        # Clean contexts (except global singleton)
        session.execute(text("""
            DELETE FROM task_contexts 
            WHERE task_id NOT IN (
                SELECT id FROM tasks WHERE git_branch_id IN (
                    SELECT id FROM project_git_branchs WHERE project_id = 'default_project'
                )
            )
        """))
        
        session.execute(text("""
            DELETE FROM branch_contexts 
            WHERE branch_id NOT IN (
                SELECT id FROM project_git_branchs WHERE project_id = 'default_project'
            )
        """))
        
        session.execute(text("""
            DELETE FROM project_contexts 
            WHERE project_id != 'default_project'
        """))
        
        session.execute(text("""
            DELETE FROM global_contexts 
            WHERE id != 'global_singleton'
        """))
        
        # Clean tasks and subtasks
        session.execute(text("""
            DELETE FROM subtasks WHERE task_id NOT IN (
                SELECT id FROM tasks WHERE git_branch_id IN (
                    SELECT id FROM project_git_branchs WHERE project_id = 'default_project'
                )
            )
        """))
        
        session.execute(text("""
            DELETE FROM tasks WHERE git_branch_id NOT IN (
                SELECT id FROM project_git_branchs WHERE project_id = 'default_project'
            )
        """))
        
        # Clean branches (except main branch of default project)
        session.execute(text("""
            DELETE FROM project_git_branchs 
            WHERE project_id != 'default_project' 
            OR (project_id = 'default_project' AND name != 'main')
        """))
        
        # Clean projects (except default)
        session.execute(text("""
            DELETE FROM projects WHERE id != 'default_project'
        """))
        
        session.commit()
        
    except Exception as e:
        logger.warning(f"Cleanup warning (non-critical): {e}")
        session.rollback()


@pytest.fixture
def clean_postgresql_db():
    """
    Fixture that provides a clean PostgreSQL database for each test.
    
    Usage:
        def test_something(clean_postgresql_db):
            session = clean_postgresql_db
            # Use session for test operations
    """
    with isolated_postgresql_test() as session:
        yield session


@pytest.fixture
def postgresql_transaction():
    """
    Fixture that runs entire test in a transaction that's rolled back.
    
    This is the most isolated approach - nothing persists after test.
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    db_config = get_db_config()
    engine = db_config.engine
    connection = engine.connect()
    transaction = connection.begin()
    
    # Configure session to use this specific connection
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=connection)
    session = Session()
    
    # Monkeypatch get_session to return our transactional session
    original_get_session = db_config.get_session
    db_config.get_session = lambda: session
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        # Restore original get_session
        db_config.get_session = original_get_session


@pytest.fixture(autouse=True)
def ensure_global_context_exists():
    """
    Ensures the global singleton context exists for tests that need it.
    
    This is autouse so it runs for every test that imports this module.
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    from datetime import datetime
    
    try:
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Ensure global singleton exists
            session.execute(text("""
                INSERT INTO global_contexts (
                    id, data, insights, progress_tracking, 
                    shared_patterns, implementation_notes, 
                    local_overrides, delegation_triggers,
                    created_at, updated_at
                ) VALUES (
                    'global_singleton', 
                    '{"organization": "default"}',
                    '[]', '{}', '{}', '{}', '{}', '{}',
                    :created_at, :updated_at
                ) ON CONFLICT (id) DO NOTHING
            """), {
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            session.commit()
    except Exception as e:
        logger.warning(f"Could not ensure global context: {e}")


def truncate_all_tables(exclude_defaults=True):
    """
    Truncate all tables for complete cleanup.
    
    Args:
        exclude_defaults: If True, preserves default test data
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    db_config = get_db_config()
    
    with db_config.get_session() as session:
        # Get all table names
        result = session.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            AND tablename NOT IN ('alembic_version')
        """))
        
        tables = [row.tablename for row in result]
        
        # Truncate in reverse dependency order
        table_order = [
            'subtasks', 'task_contexts', 'tasks',
            'branch_contexts', 'project_git_branchs', 
            'project_contexts', 'projects',
            'global_contexts', 'agents', 'rules'
        ]
        
        for table in table_order:
            if table in tables:
                if exclude_defaults and table in ['projects', 'project_git_branchs', 'global_contexts']:
                    # Use DELETE instead of TRUNCATE to preserve defaults
                    if table == 'projects':
                        session.execute(text(f"DELETE FROM {table} WHERE id != 'default_project'"))
                    elif table == 'project_git_branchs':
                        session.execute(text(f"DELETE FROM {table} WHERE project_id != 'default_project'"))
                    elif table == 'global_contexts':
                        session.execute(text(f"DELETE FROM {table} WHERE id != 'global_singleton'"))
                else:
                    session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        
        session.commit()