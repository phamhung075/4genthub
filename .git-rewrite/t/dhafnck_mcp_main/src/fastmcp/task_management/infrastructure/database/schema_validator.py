"""
Database Schema Validator

This module provides functionality to validate ORM models against the actual database schema
at startup to detect mismatches early and prevent runtime errors.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from sqlalchemy import inspect, MetaData, Table
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import class_mapper
from sqlalchemy.exc import NoInspectionAvailable
import asyncio

from fastmcp.task_management.infrastructure.database.models import (
    Project,
    ProjectGitBranch,
    Task,
    TaskDependency,
    TaskSubtask,
    TaskAssignee,
    Agent,
    Label,
    TaskLabel,
    Template,
    GlobalContext,
    ProjectContext,
    BranchContext,
    TaskContext,
    ContextDelegation,
    ContextInheritanceCache
)

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates ORM models against actual database schema"""
    
    def __init__(self, engine: AsyncEngine):
        """
        Initialize the schema validator with a database engine.
        
        Args:
            engine: SQLAlchemy async engine
        """
        self.engine = engine
        self.models = [
            Project,
            ProjectGitBranch,
            Task,
            TaskDependency,
            TaskSubtask,
            TaskAssignee,
            Agent,
            Label,
            TaskLabel,
            Template,
            GlobalContext,
            ProjectContext,
            BranchContext,
            TaskContext,
            ContextDelegation,
            ContextInheritanceCache
        ]
        self.validation_results: List[Dict[str, Any]] = []
        
    async def validate_all(self) -> Dict[str, Any]:
        """
        Validate all ORM models against the database schema.
        
        Returns:
            Dictionary containing validation results and any issues found
        """
        logger.info("Starting database schema validation...")
        
        issues = []
        warnings = []
        validated_models = []
        
        # Handle both sync and async engines
        try:
            from sqlalchemy.ext.asyncio import AsyncEngine
            is_async = isinstance(self.engine, AsyncEngine)
        except ImportError:
            is_async = False
        
        if is_async:
            async with self.engine.connect() as conn:
                # Get database metadata
                metadata = MetaData()
                await conn.run_sync(metadata.reflect)
                
                for model_class in self.models:
                    try:
                        result = await self._validate_model(model_class, metadata, conn)
                        validated_models.append(model_class.__name__)
                        
                        if result['issues']:
                            issues.extend(result['issues'])
                        if result['warnings']:
                            warnings.extend(result['warnings'])
                            
                    except Exception as e:
                        error_msg = f"Failed to validate model {model_class.__name__}: {str(e)}"
                        logger.error(error_msg)
                        issues.append({
                            'model': model_class.__name__,
                            'type': 'validation_error',
                            'message': error_msg
                        })
        else:
            # For synchronous engines, use regular context manager
            with self.engine.connect() as conn:
                # Get database metadata
                metadata = MetaData()
                metadata.reflect(bind=conn)
                
                for model_class in self.models:
                    try:
                        # For sync connections, we need to handle validation differently
                        result = self._validate_model_sync(model_class, metadata, conn)
                        validated_models.append(model_class.__name__)
                        
                        if result['issues']:
                            issues.extend(result['issues'])
                        if result['warnings']:
                            warnings.extend(result['warnings'])
                            
                    except Exception as e:
                        error_msg = f"Failed to validate model {model_class.__name__}: {str(e)}"
                        logger.error(error_msg)
                        issues.append({
                            'model': model_class.__name__,
                            'type': 'validation_error',
                            'message': error_msg
                        })
        
        # Generate summary
        summary = {
            'total_models': len(self.models),
            'validated_models': len(validated_models),
            'issues_count': len(issues),
            'warnings_count': len(warnings),
            'status': 'PASS' if not issues else 'FAIL',
            'issues': issues,
            'warnings': warnings,
            'validated_models': validated_models
        }
        
        # Log results
        if issues:
            logger.error(f"Schema validation FAILED with {len(issues)} issues")
            for issue in issues:
                logger.error(f"  - {issue['model']}.{issue.get('column', '')}: {issue['message']}")
        else:
            logger.info(f"Schema validation PASSED for {len(validated_models)} models")
            
        if warnings:
            logger.warning(f"Schema validation found {len(warnings)} warnings")
            for warning in warnings:
                logger.warning(f"  - {warning['model']}.{warning.get('column', '')}: {warning['message']}")
        
        return summary
    
    async def _validate_model(self, model_class: Any, metadata: MetaData, conn: Any) -> Dict[str, Any]:
        """
        Validate a single ORM model against its database table.
        
        Args:
            model_class: The ORM model class to validate
            metadata: Database metadata
            conn: Database connection
            
        Returns:
            Dictionary containing validation results for the model
        """
        issues = []
        warnings = []
        
        try:
            # Get mapper for the model
            mapper = class_mapper(model_class)
            table_name = mapper.local_table.name
            
            # Check if table exists in database
            if table_name not in metadata.tables:
                issues.append({
                    'model': model_class.__name__,
                    'table': table_name,
                    'type': 'missing_table',
                    'message': f"Table '{table_name}' does not exist in database"
                })
                return {'issues': issues, 'warnings': warnings}
            
            db_table = metadata.tables[table_name]
            
            # Validate columns
            model_columns = {col.name: col for col in mapper.local_table.columns}
            db_columns = {col.name: col for col in db_table.columns}
            
            # Check for missing columns in database
            for col_name, model_col in model_columns.items():
                if col_name not in db_columns:
                    issues.append({
                        'model': model_class.__name__,
                        'table': table_name,
                        'column': col_name,
                        'type': 'missing_column',
                        'message': f"Column '{col_name}' defined in model but missing in database"
                    })
                else:
                    # Validate column types
                    db_col = db_columns[col_name]
                    type_issue = self._validate_column_type(model_col, db_col)
                    if type_issue:
                        warnings.append({
                            'model': model_class.__name__,
                            'table': table_name,
                            'column': col_name,
                            'type': 'type_mismatch',
                            'message': type_issue
                        })
            
            # Check for extra columns in database not in model
            for col_name in db_columns:
                if col_name not in model_columns:
                    warnings.append({
                        'model': model_class.__name__,
                        'table': table_name,
                        'column': col_name,
                        'type': 'extra_column',
                        'message': f"Column '{col_name}' exists in database but not in model"
                    })
            
            # Validate foreign keys
            model_fks = {fk.parent.name: fk for fk in mapper.local_table.foreign_keys}
            
            # Get database foreign keys using inspector
            inspector_result = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_foreign_keys(table_name)
            )
            
            db_fks = set()
            for fk in inspector_result:
                if 'constrained_columns' in fk:
                    for col in fk['constrained_columns']:
                        db_fks.add(col)
            
            # Check for missing foreign keys
            for fk_col in model_fks:
                if fk_col not in db_fks:
                    warnings.append({
                        'model': model_class.__name__,
                        'table': table_name,
                        'column': fk_col,
                        'type': 'missing_foreign_key',
                        'message': f"Foreign key constraint on '{fk_col}' defined in model but not in database"
                    })
            
        except NoInspectionAvailable:
            issues.append({
                'model': model_class.__name__,
                'type': 'inspection_error',
                'message': f"Cannot inspect model {model_class.__name__}"
            })
        except Exception as e:
            issues.append({
                'model': model_class.__name__,
                'type': 'validation_error',
                'message': str(e)
            })
        
        return {'issues': issues, 'warnings': warnings}
    
    def _validate_column_type(self, model_col: Any, db_col: Any) -> Optional[str]:
        """
        Compare column types between model and database.
        
        Args:
            model_col: Column from the ORM model
            db_col: Column from the database
            
        Returns:
            Error message if types don't match, None otherwise
        """
        # Get string representations of types
        model_type = str(model_col.type)
        db_type = str(db_col.type)
        
        # Normalize type names for comparison
        model_type_normalized = self._normalize_type(model_type)
        db_type_normalized = self._normalize_type(db_type)
        
        # Known compatible type mappings
        compatible_types = [
            ('UUID', 'UUID'),
            ('VARCHAR', 'VARCHAR'),
            ('TEXT', 'TEXT'),
            ('INTEGER', 'INTEGER'),
            ('BIGINT', 'BIGINT'),
            ('BOOLEAN', 'BOOLEAN'),
            ('TIMESTAMP', 'TIMESTAMP'),
            ('JSON', 'JSON'),
            ('JSONB', 'JSONB'),
            # PostgreSQL specific
            ('UUID', 'CHAR(36)'),  # UUID can be stored as CHAR(36)
            ('TEXT', 'VARCHAR'),   # TEXT and VARCHAR are often interchangeable
            ('TIMESTAMP', 'DATETIME'),  # For SQLite compatibility
        ]
        
        # Check if types are compatible
        for model_compat, db_compat in compatible_types:
            if model_type_normalized.startswith(model_compat) and db_type_normalized.startswith(db_compat):
                return None
            if model_type_normalized.startswith(db_compat) and db_type_normalized.startswith(model_compat):
                return None
        
        # Types don't match
        if model_type_normalized != db_type_normalized:
            return f"Type mismatch: Model has {model_type}, Database has {db_type}"
        
        return None
    
    def _normalize_type(self, type_str: str) -> str:
        """
        Normalize SQL type string for comparison.
        
        Args:
            type_str: SQL type string
            
        Returns:
            Normalized type string
        """
        # Remove parentheses and parameters
        normalized = type_str.upper()
        if '(' in normalized:
            normalized = normalized[:normalized.index('(')]
        
        # Map common type aliases
        type_aliases = {
            'CHAR': 'VARCHAR',
            'CHARACTER': 'VARCHAR',
            'CHARACTER VARYING': 'VARCHAR',
            'INT': 'INTEGER',
            'SMALLINT': 'INTEGER',
            'SERIAL': 'INTEGER',
            'BIGSERIAL': 'BIGINT',
            'DOUBLE PRECISION': 'FLOAT',
            'REAL': 'FLOAT',
            'DATETIME': 'TIMESTAMP',
            'TIMESTAMP WITHOUT TIME ZONE': 'TIMESTAMP',
            'TIMESTAMP WITH TIME ZONE': 'TIMESTAMP',
        }
        
        for alias, canonical in type_aliases.items():
            if normalized == alias:
                normalized = canonical
                break
        
        return normalized
    
    def _validate_model_sync(self, model_class: Any, metadata: MetaData, conn: Any) -> Dict[str, Any]:
        """
        Validate a single ORM model against its database table (synchronous version).
        
        Args:
            model_class: The ORM model class to validate
            metadata: Database metadata
            conn: Database connection (synchronous)
            
        Returns:
            Dictionary containing validation results for the model
        """
        issues = []
        warnings = []
        
        try:
            # Get mapper for the model
            mapper = class_mapper(model_class)
            table_name = mapper.local_table.name
            
            # Check if table exists in database
            if table_name not in metadata.tables:
                issues.append({
                    'model': model_class.__name__,
                    'table': table_name,
                    'type': 'missing_table',
                    'message': f"Table '{table_name}' does not exist in database"
                })
                return {'issues': issues, 'warnings': warnings}
            
            db_table = metadata.tables[table_name]
            
            # Validate columns
            model_columns = {col.name: col for col in mapper.local_table.columns}
            db_columns = {col.name: col for col in db_table.columns}
            
            # Check for missing columns in database
            for col_name, model_col in model_columns.items():
                if col_name not in db_columns:
                    issues.append({
                        'model': model_class.__name__,
                        'table': table_name,
                        'column': col_name,
                        'type': 'missing_column',
                        'message': f"Column '{col_name}' defined in model but missing in database"
                    })
                else:
                    # Validate column types
                    db_col = db_columns[col_name]
                    type_issue = self._validate_column_type(model_col, db_col)
                    if type_issue:
                        warnings.append({
                            'model': model_class.__name__,
                            'table': table_name,
                            'column': col_name,
                            'type': 'type_mismatch',
                            'message': type_issue
                        })
            
            # Check for extra columns in database not in model
            for col_name in db_columns:
                if col_name not in model_columns:
                    warnings.append({
                        'model': model_class.__name__,
                        'table': table_name,
                        'column': col_name,
                        'type': 'extra_column',
                        'message': f"Column '{col_name}' exists in database but not in model"
                    })
            
            # Validate foreign keys
            model_fks = {fk.parent.name: fk for fk in mapper.local_table.foreign_keys}
            
            # Get database foreign keys using inspector (synchronous)
            inspector = inspect(conn)
            inspector_result = inspector.get_foreign_keys(table_name)
            
            db_fks = set()
            for fk in inspector_result:
                if 'constrained_columns' in fk:
                    for col in fk['constrained_columns']:
                        db_fks.add(col)
            
            # Check for missing foreign keys
            for fk_col in model_fks:
                if fk_col not in db_fks:
                    warnings.append({
                        'model': model_class.__name__,
                        'table': table_name,
                        'column': fk_col,
                        'type': 'missing_foreign_key',
                        'message': f"Foreign key constraint on '{fk_col}' defined in model but not in database"
                    })
            
        except NoInspectionAvailable:
            issues.append({
                'model': model_class.__name__,
                'type': 'inspection_error',
                'message': f"Cannot inspect model {model_class.__name__}"
            })
        except Exception as e:
            issues.append({
                'model': model_class.__name__,
                'type': 'validation_error',
                'message': str(e)
            })
        
        return {'issues': issues, 'warnings': warnings}


async def validate_schema_on_startup(engine: AsyncEngine) -> bool:
    """
    Convenience function to run schema validation on application startup.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        True if validation passed, False otherwise
    """
    validator = SchemaValidator(engine)
    results = await validator.validate_all()
    
    if results['status'] == 'FAIL':
        logger.error("=" * 60)
        logger.error("DATABASE SCHEMA VALIDATION FAILED!")
        logger.error("=" * 60)
        logger.error("The following issues must be resolved:")
        for issue in results['issues']:
            logger.error(f"  • {issue['model']}: {issue['message']}")
        logger.error("=" * 60)
        logger.error("Suggested actions:")
        logger.error("  1. Run database migrations to update schema")
        logger.error("  2. Check ORM model definitions match database")
        logger.error("  3. Verify database connection and permissions")
        logger.error("=" * 60)
        return False
    
    if results['warnings']:
        logger.warning("=" * 60)
        logger.warning("Schema validation warnings:")
        for warning in results['warnings']:
            logger.warning(f"  • {warning['model']}: {warning['message']}")
        logger.warning("=" * 60)
    
    logger.info(f"✅ Schema validation successful for {results['validated_models']} models")
    return True