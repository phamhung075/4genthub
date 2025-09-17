"""Task Performance Optimizer

This module provides optimizations for task loading performance including:
- Query optimization strategies
- Caching implementation
- Pagination improvements
- Index recommendations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import json
from functools import lru_cache
from sqlalchemy import text, Index
from sqlalchemy.orm import Session, selectinload, joinedload, subqueryload

logger = logging.getLogger(__name__)


class TaskPerformanceOptimizer:
    """Optimizer for task loading performance"""
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize performance optimizer
        
        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default 5 minutes)
        """
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._query_stats: Dict[str, Dict] = {}
    
    def optimize_task_query(self, session: Session, base_query, filters: Dict[str, Any]) -> Any:
        """Optimize task query with proper loading strategies
        
        Args:
            session: Database session
            base_query: Base SQLAlchemy query
            filters: Query filters
            
        Returns:
            Optimized query
        """
        # Use selectinload for collections to avoid N+1 queries
        # This is more efficient than joinedload for multiple collections
        optimized_query = base_query.options(
            selectinload('assignees'),
            selectinload('labels').selectinload('label'),
            selectinload('subtasks'),
            selectinload('dependencies')
        )
        
        # Add query hints for better execution plan
        optimized_query = optimized_query.execution_options(
            synchronize_session="fetch"
        )
        
        return optimized_query
    
    def get_cache_key(self, operation: str, **params) -> str:
        """Generate cache key for operation
        
        Args:
            operation: Operation name
            **params: Operation parameters
            
        Returns:
            Cache key string
        """
        # Create deterministic cache key
        key_data = {
            'operation': operation,
            'params': params
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if not expired
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        if cache_key in self._cache:
            value, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.debug(f"Cache hit for key: {cache_key}")
                return value
            else:
                # Remove expired entry
                del self._cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key}")
        return None
    
    def set_cache(self, cache_key: str, value: Any) -> None:
        """Set value in cache
        
        Args:
            cache_key: Cache key
            value: Value to cache
        """
        self._cache[cache_key] = (value, datetime.now())
        logger.debug(f"Cached value for key: {cache_key}")
        
        # Clean old entries if cache grows too large
        if len(self._cache) > 1000:
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if now - timestamp >= timedelta(seconds=self.cache_ttl)
        ]
        for key in expired_keys:
            del self._cache[key]
        logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def analyze_query_performance(self, session: Session) -> Dict[str, Any]:
        """Analyze query performance and provide recommendations
        
        Args:
            session: Database session
            
        Returns:
            Performance analysis and recommendations
        """
        analysis = {
            'slow_queries': [],
            'missing_indexes': [],
            'recommendations': []
        }
        
        # Check for slow queries (PostgreSQL specific)
        try:
            result = session.execute(text("""
                SELECT query, calls, mean_exec_time, total_exec_time
                FROM pg_stat_statements
                WHERE query LIKE '%tasks%'
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """))
            
            for row in result:
                if row.mean_exec_time > 100:  # Over 100ms
                    analysis['slow_queries'].append({
                        'query': row.query[:100],
                        'avg_time_ms': row.mean_exec_time,
                        'total_calls': row.calls
                    })
        except Exception as e:
            logger.debug(f"Could not analyze pg_stat_statements: {e}")
        
        # Check for missing indexes
        try:
            result = session.execute(text("""
                SELECT schemaname, tablename, attname, n_distinct, correlation
                FROM pg_stats
                WHERE tablename = 'tasks'
                AND n_distinct > 100
                AND correlation < 0.1
            """))
            
            for row in result:
                analysis['missing_indexes'].append({
                    'table': row.tablename,
                    'column': row.attname,
                    'cardinality': row.n_distinct
                })
        except Exception as e:
            logger.debug(f"Could not analyze index statistics: {e}")
        
        # Generate recommendations
        if len(analysis['slow_queries']) > 0:
            analysis['recommendations'].append(
                "Consider adding query result caching for frequently accessed data"
            )
        
        if len(analysis['missing_indexes']) > 0:
            analysis['recommendations'].append(
                "Add indexes on frequently filtered columns"
            )
        
        # Check table statistics
        try:
            result = session.execute(text("""
                SELECT relname, n_live_tup, n_dead_tup, last_vacuum, last_autovacuum
                FROM pg_stat_user_tables
                WHERE relname = 'tasks'
            """))
            
            for row in result:
                if row.n_dead_tup > row.n_live_tup * 0.2:
                    analysis['recommendations'].append(
                        f"Table 'tasks' has {row.n_dead_tup} dead tuples. Consider running VACUUM"
                    )
        except Exception as e:
            logger.debug(f"Could not analyze table statistics: {e}")
        
        return analysis
    
    def create_optimized_indexes(self, session: Session) -> List[str]:
        """Create optimized indexes for task queries
        
        Args:
            session: Database session
            
        Returns:
            List of created indexes
        """
        created_indexes = []
        
        # Composite indexes for common query patterns
        index_definitions = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_branch_status ON tasks(git_branch_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_branch_priority ON tasks(git_branch_id, priority)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_branch_created ON tasks(git_branch_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_task_assignees_composite ON task_assignees(task_id, assignee_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_labels_composite ON task_labels(task_id, label_id)",
            "CREATE INDEX IF NOT EXISTS idx_subtasks_task_status ON task_subtasks(task_id, status)"
        ]
        
        for index_sql in index_definitions:
            try:
                session.execute(text(index_sql))
                session.commit()
                index_name = index_sql.split("INDEX IF NOT EXISTS ")[1].split(" ON")[0]
                created_indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                session.rollback()
        
        return created_indexes
    
    def optimize_response_payload(self, tasks: List[Dict]) -> List[Dict]:
        """Optimize response payload size
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Optimized task list with reduced payload
        """
        optimized_tasks = []
        
        for task in tasks:
            # Remove unnecessary fields for list views
            optimized_task = {
                'id': task.get('id'),
                'title': task.get('title'),
                'status': task.get('status'),
                'priority': task.get('priority'),
                'progress_percentage': task.get('progress_percentage', 0),
                'assignees_count': len(task.get('assignees', [])),
                'labels': [label['name'] if isinstance(label, dict) else label 
                          for label in task.get('labels', [])],
                'due_date': task.get('due_date'),
                'updated_at': task.get('updated_at'),
                'has_dependencies': len(task.get('dependencies', [])) > 0,
                'is_blocked': any(dep.get('status') != 'done' 
                                for dep in task.get('dependencies', []))
            }
            
            # Only include description preview for long descriptions
            description = task.get('description', '')
            if len(description) > 200:
                optimized_task['description_preview'] = description[:197] + '...'
            
            optimized_tasks.append(optimized_task)
        
        return optimized_tasks
    
    def get_pagination_metadata(self, total_count: int, limit: int, offset: int) -> Dict:
        """Generate pagination metadata
        
        Args:
            total_count: Total number of items
            limit: Items per page
            offset: Current offset
            
        Returns:
            Pagination metadata
        """
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        return {
            'total_count': total_count,
            'current_page': current_page,
            'total_pages': total_pages,
            'limit': limit,
            'offset': offset,
            'has_next': offset + limit < total_count,
            'has_prev': offset > 0,
            'next_offset': min(offset + limit, total_count) if offset + limit < total_count else None,
            'prev_offset': max(offset - limit, 0) if offset > 0 else None
        }


# Singleton instance
_optimizer_instance = None


def get_performance_optimizer() -> TaskPerformanceOptimizer:
    """Get singleton instance of performance optimizer
    
    Returns:
        TaskPerformanceOptimizer instance
    """
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = TaskPerformanceOptimizer()
    return _optimizer_instance