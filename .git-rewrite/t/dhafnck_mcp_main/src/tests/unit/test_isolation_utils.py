"""
PostgreSQL Test Isolation Utilities

Simple utilities to help with test isolation in PostgreSQL.
"""
from sqlalchemy import text
from contextlib import contextmanager
import logging
import uuid

logger = logging.getLogger(__name__)


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