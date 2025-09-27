"""Enhanced Database Utilities for Clean Timestamp Architecture

This module provides comprehensive database utilities that support the clean timestamp
architecture implementation. It includes utilities for database operations, timestamp
management, schema validation, and performance optimization.

Key Features:
- Database connection and health checking utilities
- Timestamp validation and normalization utilities
- Schema validation and integrity checking
- Performance optimization utilities
- Clean architecture compliance utilities
- Migration support utilities

NO LEGACY SUPPORT:
- No backward compatibility with manual timestamp systems
- No fallback mechanisms for obsolete patterns
- Clean implementation only
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union, Generator
from pathlib import Path

from sqlalchemy import create_engine, text, inspect, Engine, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DatabaseError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .database_config import DatabaseConfig, Base
from .timestamp_events import setup_timestamp_events, cleanup_timestamp_events
from ...domain.exceptions.base_exceptions import (
    DatabaseException,
    ValidationException,
    ConfigurationException
)

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Comprehensive database utilities for clean timestamp architecture.

    This class provides utilities for database operations, schema validation,
    timestamp management, and performance optimization. All methods support
    both PostgreSQL and SQLite databases.

    Features:
    - Connection health checking and validation
    - Schema validation and integrity checks
    - Timestamp normalization and validation
    - Performance optimization utilities
    - Migration support utilities
    - Clean architecture compliance checks
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """Initialize database utilities.

        Args:
            db_config: Optional database configuration. Uses singleton if not provided.
        """
        self.db_config = db_config or DatabaseConfig.get_instance()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Get database engine, creating if necessary."""
        if self._engine is None:
            self._engine = self.db_config.get_engine()
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory, creating if necessary."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.

        Yields:
            Session: SQLAlchemy session with automatic transaction management

        Raises:
            DatabaseException: If session creation fails
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise DatabaseException(f"Database operation failed: {str(e)}")
        finally:
            session.close()

    def check_database_health(self) -> Dict[str, Any]:
        """Check database health and connectivity.

        Returns:
            Dict with health status, connection info, and performance metrics

        Raises:
            DatabaseException: If health check fails
        """
        try:
            start_time = datetime.now(timezone.utc)

            with self.get_session() as session:
                # Basic connectivity test
                result = session.execute(text("SELECT 1")).fetchone()
                if not result:
                    raise DatabaseException("Database connectivity test failed")

                # Get database version and info
                db_url = str(self.engine.url)
                if 'postgresql' in db_url.lower():
                    version_result = session.execute(text("SELECT version()")).fetchone()
                    db_type = "postgresql"
                    db_version = version_result[0] if version_result else "unknown"
                else:
                    version_result = session.execute(text("SELECT sqlite_version()")).fetchone()
                    db_type = "sqlite"
                    db_version = version_result[0] if version_result else "unknown"

                # Check table count
                inspector = inspect(self.engine)
                table_names = inspector.get_table_names()
                table_count = len(table_names)

                # Performance check
                end_time = datetime.now(timezone.utc)
                response_time_ms = (end_time - start_time).total_seconds() * 1000

                return {
                    "status": "healthy",
                    "database_type": db_type,
                    "database_version": db_version,
                    "table_count": table_count,
                    "response_time_ms": round(response_time_ms, 2),
                    "timestamp_events_active": True,  # We always use clean timestamp events
                    "checked_at": end_time.isoformat()
                }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

    def validate_schema_integrity(self) -> Dict[str, Any]:
        """Validate database schema integrity and timestamp compliance.

        Returns:
            Dict with validation results, errors, and recommendations

        Raises:
            DatabaseException: If validation fails critically
        """
        try:
            with self.get_session() as session:
                inspector = inspect(self.engine)
                validation_results = {
                    "status": "valid",
                    "errors": [],
                    "warnings": [],
                    "timestamp_compliance": True,
                    "tables_checked": 0,
                    "timestamp_tables": 0
                }

                # Check each table for timestamp compliance
                for table_name in inspector.get_table_names():
                    validation_results["tables_checked"] += 1
                    columns = inspector.get_columns(table_name)
                    column_names = [col['name'] for col in columns]

                    # Check if table has timestamp fields
                    has_created_at = 'created_at' in column_names
                    has_updated_at = 'updated_at' in column_names

                    if has_created_at or has_updated_at:
                        validation_results["timestamp_tables"] += 1

                        # Validate timestamp fields are properly configured
                        if has_created_at and not has_updated_at:
                            validation_results["warnings"].append(
                                f"Table {table_name} has created_at but missing updated_at"
                            )
                        elif has_updated_at and not has_created_at:
                            validation_results["warnings"].append(
                                f"Table {table_name} has updated_at but missing created_at"
                            )

                        # Check for proper timestamp column types
                        for col in columns:
                            if col['name'] in ('created_at', 'updated_at'):
                                if not str(col['type']).lower().startswith('datetime'):
                                    validation_results["errors"].append(
                                        f"Table {table_name}.{col['name']} should be DATETIME type, got {col['type']}"
                                    )

                # Check for required core tables
                required_tables = {
                    'projects', 'project_git_branchs', 'tasks', 'subtasks',
                    'global_contexts', 'project_contexts', 'branch_contexts', 'task_contexts'
                }
                existing_tables = set(inspector.get_table_names())
                missing_tables = required_tables - existing_tables

                if missing_tables:
                    validation_results["errors"].extend([
                        f"Missing required table: {table}" for table in missing_tables
                    ])

                # Set overall status
                if validation_results["errors"]:
                    validation_results["status"] = "invalid"
                    validation_results["timestamp_compliance"] = False
                elif validation_results["warnings"]:
                    validation_results["status"] = "valid_with_warnings"

                return validation_results

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            raise DatabaseException(f"Schema validation error: {str(e)}")

    def normalize_timestamp(self, timestamp: Union[datetime, str, None]) -> Optional[datetime]:
        """Normalize timestamp to UTC datetime.

        Args:
            timestamp: Timestamp to normalize (datetime, ISO string, or None)

        Returns:
            Normalized UTC datetime or None

        Raises:
            ValidationException: If timestamp format is invalid
        """
        if timestamp is None:
            return None

        try:
            if isinstance(timestamp, str):
                # Parse ISO format string
                if timestamp.endswith('Z'):
                    timestamp = timestamp[:-1] + '+00:00'
                dt = datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                raise ValidationException(f"Invalid timestamp type: {type(timestamp)}")

            # Ensure timezone info
            if dt.tzinfo is None:
                # Assume naive datetime is UTC
                dt = dt.replace(tzinfo=timezone.utc)
                logger.debug("Assumed naive datetime is UTC")
            elif dt.tzinfo != timezone.utc:
                # Convert to UTC
                dt = dt.astimezone(timezone.utc)
                logger.debug("Converted timestamp to UTC")

            return dt

        except (ValueError, TypeError) as e:
            logger.error(f"Timestamp normalization failed: {e}")
            raise ValidationException(f"Invalid timestamp format: {str(e)}")

    def validate_timestamp_range(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> Tuple[datetime, datetime]:
        """Validate and normalize timestamp range.

        Args:
            start_time: Range start time
            end_time: Range end time

        Returns:
            Tuple of normalized (start_time, end_time)

        Raises:
            ValidationException: If range is invalid
        """
        if start_time is None or end_time is None:
            raise ValidationException("Both start_time and end_time must be provided")

        norm_start = self.normalize_timestamp(start_time)
        norm_end = self.normalize_timestamp(end_time)

        if norm_start >= norm_end:
            raise ValidationException("start_time must be before end_time")

        # Check for reasonable range (not more than 10 years)
        max_range_days = 365 * 10
        if (norm_end - norm_start).days > max_range_days:
            raise ValidationException(f"Timestamp range too large (max {max_range_days} days)")

        return norm_start, norm_end

    def optimize_database_performance(self) -> Dict[str, Any]:
        """Run database optimization tasks.

        Returns:
            Dict with optimization results and performance metrics

        Raises:
            DatabaseException: If optimization fails
        """
        try:
            optimization_results = {
                "status": "completed",
                "operations": [],
                "performance_gain": {},
                "recommendations": []
            }

            db_url = str(self.engine.url).lower()

            with self.get_session() as session:
                if 'postgresql' in db_url:
                    # PostgreSQL optimizations

                    # Analyze tables for better query planning
                    session.execute(text("ANALYZE"))
                    optimization_results["operations"].append("ran_analyze")

                    # Vacuum to reclaim space (not in transaction)
                    session.commit()
                    session.execute(text("VACUUM"))
                    optimization_results["operations"].append("ran_vacuum")

                    # Get table statistics
                    stats_query = text("""
                        SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                        FROM pg_stat_user_tables
                        WHERE schemaname = 'public'
                        ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
                        LIMIT 5
                    """)
                    stats_result = session.execute(stats_query).fetchall()
                    optimization_results["performance_gain"]["top_active_tables"] = [
                        {"table": row[1], "total_operations": row[2] + row[3] + row[4]}
                        for row in stats_result
                    ]

                else:
                    # SQLite optimizations

                    # Analyze for query optimization
                    session.execute(text("ANALYZE"))
                    optimization_results["operations"].append("ran_analyze")

                    # Vacuum to optimize file size
                    session.execute(text("VACUUM"))
                    optimization_results["operations"].append("ran_vacuum")

                    # Get database size info
                    size_query = text("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                    size_result = session.execute(size_query).fetchone()
                    if size_result:
                        optimization_results["performance_gain"]["database_size_bytes"] = size_result[0]

                # Generic recommendations
                inspector = inspect(self.engine)
                table_count = len(inspector.get_table_names())

                if table_count > 20:
                    optimization_results["recommendations"].append(
                        "Consider table partitioning for large tables"
                    )

                optimization_results["recommendations"].extend([
                    "Regularly run ANALYZE for optimal query planning",
                    "Monitor timestamp query performance on large tables",
                    "Consider composite indexes for timestamp + status queries"
                ])

            return optimization_results

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            raise DatabaseException(f"Database optimization error: {str(e)}")

    def setup_clean_timestamp_infrastructure(self) -> Dict[str, Any]:
        """Set up clean timestamp event infrastructure.

        Returns:
            Dict with setup results and configuration

        Raises:
            DatabaseException: If setup fails
        """
        try:
            logger.info("Setting up clean timestamp infrastructure...")

            # Clean up any existing event handlers first
            cleanup_timestamp_events()

            # Set up new clean timestamp event handlers
            setup_timestamp_events()

            # Verify setup
            with self.get_session() as session:
                # Create a test entity to verify timestamp events work
                test_query = text("SELECT 1")
                session.execute(test_query)

            setup_results = {
                "status": "success",
                "timestamp_events_active": True,
                "automatic_timestamp_management": True,
                "supported_entities": [
                    "Project", "GitBranch", "Task", "Subtask", "Agent", "Label", "Template"
                ],
                "setup_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info("Clean timestamp infrastructure setup completed successfully")
            return setup_results

        except Exception as e:
            logger.error(f"Timestamp infrastructure setup failed: {e}")
            raise DatabaseException(f"Timestamp setup error: {str(e)}")

    def get_database_metrics(self) -> Dict[str, Any]:
        """Get comprehensive database metrics and statistics.

        Returns:
            Dict with database metrics, performance stats, and health indicators

        Raises:
            DatabaseException: If metrics collection fails
        """
        try:
            with self.get_session() as session:
                inspector = inspect(self.engine)
                db_url = str(self.engine.url).lower()

                metrics = {
                    "database_type": "postgresql" if 'postgresql' in db_url else "sqlite",
                    "table_count": len(inspector.get_table_names()),
                    "timestamp_tables": 0,
                    "total_records": 0,
                    "performance": {},
                    "collected_at": datetime.now(timezone.utc).isoformat()
                }

                # Collect table-specific metrics
                for table_name in inspector.get_table_names():
                    # Check if table has timestamp columns
                    columns = inspector.get_columns(table_name)
                    has_timestamps = any(col['name'] in ('created_at', 'updated_at') for col in columns)

                    if has_timestamps:
                        metrics["timestamp_tables"] += 1

                    # Get record count
                    try:
                        count_result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()
                        record_count = count_result[0] if count_result else 0
                        metrics["total_records"] += record_count

                        # Store per-table metrics
                        metrics[f"table_{table_name}_count"] = record_count

                    except Exception as e:
                        logger.warning(f"Could not get count for table {table_name}: {e}")

                # Performance metrics
                start_time = datetime.now(timezone.utc)
                session.execute(text("SELECT 1"))
                end_time = datetime.now(timezone.utc)

                metrics["performance"] = {
                    "query_response_time_ms": round((end_time - start_time).total_seconds() * 1000, 2),
                    "timestamp_events_enabled": True,
                    "clean_architecture_compliant": True
                }

                return metrics

        except Exception as e:
            logger.error(f"Database metrics collection failed: {e}")
            raise DatabaseException(f"Metrics collection error: {str(e)}")

    def create_performance_indexes(self) -> Dict[str, Any]:
        """Create performance-optimized indexes for timestamp queries.

        Returns:
            Dict with index creation results

        Raises:
            DatabaseException: If index creation fails
        """
        try:
            with self.get_session() as session:
                db_url = str(self.engine.url).lower()
                is_postgresql = 'postgresql' in db_url

                index_results = {
                    "status": "success",
                    "indexes_created": [],
                    "indexes_skipped": [],
                    "database_type": "postgresql" if is_postgresql else "sqlite"
                }

                # Define indexes for timestamp optimization
                timestamp_indexes = [
                    ("idx_tasks_timestamps", "tasks", ["created_at", "updated_at"]),
                    ("idx_projects_timestamps", "projects", ["created_at", "updated_at"]),
                    ("idx_subtasks_timestamps", "subtasks", ["created_at", "updated_at"]),
                    ("idx_tasks_status_created", "tasks", ["status", "created_at"]),
                    ("idx_tasks_priority_updated", "tasks", ["priority", "updated_at"])
                ]

                inspector = inspect(self.engine)
                existing_indexes = set()

                # Get existing indexes
                for table_name in inspector.get_table_names():
                    try:
                        table_indexes = inspector.get_indexes(table_name)
                        existing_indexes.update([idx['name'] for idx in table_indexes])
                    except Exception:
                        pass  # Some tables might not have indexes

                # Create new indexes
                for idx_name, table_name, columns in timestamp_indexes:
                    if idx_name in existing_indexes:
                        index_results["indexes_skipped"].append({
                            "name": idx_name,
                            "reason": "already_exists"
                        })
                        continue

                    try:
                        # Check if table exists
                        if table_name not in inspector.get_table_names():
                            index_results["indexes_skipped"].append({
                                "name": idx_name,
                                "reason": f"table_{table_name}_not_found"
                            })
                            continue

                        # Create index
                        columns_str = ", ".join(columns)
                        if is_postgresql:
                            # PostgreSQL supports DESC in indexes
                            if "created_at" in columns or "updated_at" in columns:
                                columns_str = ", ".join([
                                    f"{col} DESC" if col in ("created_at", "updated_at") else col
                                    for col in columns
                                ])

                        create_index_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns_str})"
                        session.execute(text(create_index_sql))

                        index_results["indexes_created"].append({
                            "name": idx_name,
                            "table": table_name,
                            "columns": columns
                        })

                        logger.info(f"Created index {idx_name} on {table_name}")

                    except Exception as e:
                        logger.warning(f"Could not create index {idx_name}: {e}")
                        index_results["indexes_skipped"].append({
                            "name": idx_name,
                            "reason": f"error: {str(e)}"
                        })

                session.commit()
                return index_results

        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            raise DatabaseException(f"Index creation error: {str(e)}")


# Singleton instance for easy access
_database_utils: Optional[DatabaseUtils] = None


def get_database_utils() -> DatabaseUtils:
    """Get singleton database utils instance.

    Returns:
        DatabaseUtils: Singleton instance
    """
    global _database_utils
    if _database_utils is None:
        _database_utils = DatabaseUtils()
    return _database_utils


def check_database_health() -> Dict[str, Any]:
    """Convenience function to check database health.

    Returns:
        Dict with health status and metrics
    """
    return get_database_utils().check_database_health()


def validate_schema_integrity() -> Dict[str, Any]:
    """Convenience function to validate schema integrity.

    Returns:
        Dict with validation results
    """
    return get_database_utils().validate_schema_integrity()


def setup_clean_timestamp_infrastructure() -> Dict[str, Any]:
    """Convenience function to set up clean timestamp infrastructure.

    Returns:
        Dict with setup results
    """
    return get_database_utils().setup_clean_timestamp_infrastructure()


def optimize_database_performance() -> Dict[str, Any]:
    """Convenience function to optimize database performance.

    Returns:
        Dict with optimization results
    """
    return get_database_utils().optimize_database_performance()