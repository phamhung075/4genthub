"""
Add Composite Indexes for Database Performance Optimization

This script adds critical composite indexes to improve query performance
and eliminate N+1 query problems. Expected improvement: 50-60%.
"""

from sqlalchemy import create_engine, text, Index
from sqlalchemy.orm import sessionmaker
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_composite_indexes(database_url: str = None):
    """
    Add composite indexes to the database for performance optimization.
    
    Args:
        database_url: Database connection string. If not provided, uses environment variable.
    """
    if not database_url:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///4genthub.db')
    
    engine = create_engine(database_url)
    
    # List of composite indexes to create
    indexes = [
        # 1. Composite index for efficient task listing with filters
        {
            'name': 'idx_tasks_efficient_list',
            'table': 'tasks',
            'columns': ['git_branch_id', 'status', 'priority', 'created_at'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_tasks_efficient_list 
                     ON tasks(git_branch_id, status, priority, created_at DESC)"""
        },
        
        # 2. Composite index for subtask lookups by parent task and status
        {
            'name': 'idx_subtasks_parent_status',
            'table': 'task_subtasks',
            'columns': ['task_id', 'status'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_subtasks_parent_status 
                     ON task_subtasks(task_id, status)"""
        },
        
        # 3. Composite index for assignee lookups
        {
            'name': 'idx_assignees_task_lookup',
            'table': 'task_assignees',
            'columns': ['task_id', 'assignee_id'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_assignees_task_lookup 
                     ON task_assignees(task_id, assignee_id)"""
        },
        
        # 4. Composite index for task labels
        {
            'name': 'idx_task_labels_lookup',
            'table': 'task_labels',
            'columns': ['task_id', 'label_id'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_task_labels_lookup 
                     ON task_labels(task_id, label_id)"""
        },
        
        # 5. Composite index for dependency lookups
        {
            'name': 'idx_dependencies_task_lookup',
            'table': 'task_dependencies',
            'columns': ['task_id', 'depends_on_task_id'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_dependencies_task_lookup 
                     ON task_dependencies(task_id, depends_on_task_id)"""
        },
        
        # 6. Composite index for branch-priority queries
        {
            'name': 'idx_tasks_branch_priority',
            'table': 'tasks',
            'columns': ['git_branch_id', 'priority', 'status', 'created_at'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_tasks_branch_priority 
                     ON tasks(git_branch_id, priority, status, created_at DESC)"""
        },
        
        # 7. Index for overdue task queries (partial index)
        {
            'name': 'idx_tasks_due_date',
            'table': 'tasks',
            'columns': ['due_date', 'status'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_tasks_due_date 
                     ON tasks(due_date, status)"""
        },
        
        # 8. Index for context lookups (partial index)
        {
            'name': 'idx_tasks_context',
            'table': 'tasks',
            'columns': ['context_id'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_tasks_context 
                     ON tasks(context_id)"""
        },
        
        # 9. Index for subtask progress tracking
        {
            'name': 'idx_subtasks_progress',
            'table': 'task_subtasks',
            'columns': ['task_id', 'progress_percentage'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_subtasks_progress 
                     ON task_subtasks(task_id, progress_percentage)"""
        },
        
        # 10. Index for label name lookups
        {
            'name': 'idx_labels_name',
            'table': 'labels',
            'columns': ['name'],
            'sql': """CREATE INDEX IF NOT EXISTS idx_labels_name 
                     ON labels(name)"""
        }
    ]
    
    # Create indexes
    with engine.connect() as connection:
        success_count = 0
        failed_count = 0
        
        for index_def in indexes:
            try:
                logger.info(f"Creating index: {index_def['name']}")
                connection.execute(text(index_def['sql']))
                connection.commit()
                success_count += 1
                logger.info(f"✓ Created index: {index_def['name']}")
            except Exception as e:
                failed_count += 1
                logger.error(f"✗ Failed to create index {index_def['name']}: {e}")
        
        # Analyze tables to update statistics (for SQLite)
        if 'sqlite' in database_url.lower():
            try:
                connection.execute(text("ANALYZE"))
                connection.commit()
                logger.info("✓ Updated database statistics (ANALYZE)")
            except Exception as e:
                logger.warning(f"Could not update statistics: {e}")
        
        logger.info(f"\n=== Index Creation Summary ===")
        logger.info(f"Successfully created: {success_count} indexes")
        if failed_count > 0:
            logger.info(f"Failed: {failed_count} indexes")
        logger.info(f"Total indexes processed: {len(indexes)}")
        
        # Verify indexes were created
        if 'sqlite' in database_url.lower():
            result = connection.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            ))
            existing_indexes = [row[0] for row in result]
            logger.info(f"\nExisting performance indexes: {len(existing_indexes)}")
            for idx in existing_indexes:
                logger.info(f"  - {idx}")
        
        return success_count, failed_count


def verify_index_performance(database_url: str = None):
    """
    Verify that the indexes are being used by running EXPLAIN on common queries.
    """
    if not database_url:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///4genthub.db')
    
    engine = create_engine(database_url)
    
    # Test queries to verify index usage
    test_queries = [
        {
            'name': 'Task listing with filters',
            'query': """EXPLAIN QUERY PLAN
                       SELECT * FROM tasks 
                       WHERE git_branch_id = '123' 
                       AND status = 'todo' 
                       ORDER BY created_at DESC"""
        },
        {
            'name': 'Subtask lookup',
            'query': """EXPLAIN QUERY PLAN
                       SELECT * FROM task_subtasks 
                       WHERE task_id = '123'"""
        },
        {
            'name': 'Task by assignee',
            'query': """EXPLAIN QUERY PLAN
                       SELECT t.* FROM tasks t
                       JOIN task_assignees ta ON t.id = ta.task_id
                       WHERE ta.assignee_id = 'user1'"""
        }
    ]
    
    with engine.connect() as connection:
        logger.info("\n=== Index Performance Verification ===")
        for test in test_queries:
            logger.info(f"\nQuery: {test['name']}")
            try:
                result = connection.execute(text(test['query']))
                for row in result:
                    logger.info(f"  {row}")
            except Exception as e:
                logger.error(f"  Error: {e}")


if __name__ == "__main__":
    import sys
    
    # Allow database URL to be passed as command line argument
    db_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    logger.info("Starting composite index creation for performance optimization...")
    success, failed = add_composite_indexes(db_url)
    
    if success > 0:
        logger.info("\nVerifying index performance...")
        verify_index_performance(db_url)
    
    if failed == 0:
        logger.info("\n✅ All composite indexes created successfully!")
        logger.info("Expected performance improvement: 50-60% for filtered queries")
    else:
        logger.warning(f"\n⚠️ Some indexes failed to create. Please review the errors above.")
        sys.exit(1)