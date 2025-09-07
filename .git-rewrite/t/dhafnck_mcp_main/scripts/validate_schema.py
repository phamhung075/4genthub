#!/usr/bin/env python3
"""
Schema Validation Script

This script compares SQLAlchemy models to actual database schema and reports mismatches.
Can be run during application startup or as a standalone script.

Usage:
    python validate_schema.py [--fix] [--database-url URL]
"""

import argparse
import logging
import sys
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp.task_management.infrastructure.database.models import Base
from fastmcp.task_management.infrastructure.database.database_config import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ColumnMismatch:
    """Represents a column mismatch between model and database"""
    table_name: str
    column_name: str
    issue_type: str  # 'missing_in_db', 'missing_in_model', 'type_mismatch', 'nullable_mismatch'
    model_info: Optional[str] = None
    db_info: Optional[str] = None
    severity: str = 'warning'  # 'error', 'warning', 'info'


class SchemaValidator:
    """Validates database schema against SQLAlchemy models"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.metadata = Base.metadata
        self.inspector = inspect(engine)
        self.mismatches: List[ColumnMismatch] = []
        
    def validate_all_tables(self) -> List[ColumnMismatch]:
        """Validate all tables and return list of mismatches"""
        logger.info("Starting schema validation...")
        self.mismatches.clear()
        
        # Get all tables from models
        model_tables = set(self.metadata.tables.keys())
        # Get all tables from database
        db_tables = set(self.inspector.get_table_names())
        
        logger.info(f"Model tables: {len(model_tables)}")
        logger.info(f"Database tables: {len(db_tables)}")
        
        # Check for missing tables
        missing_in_db = model_tables - db_tables
        missing_in_model = db_tables - model_tables
        
        for table_name in missing_in_db:
            self.mismatches.append(ColumnMismatch(
                table_name=table_name,
                column_name='*',
                issue_type='missing_table_in_db',
                model_info='Table defined in model',
                db_info='Table missing in database',
                severity='error'
            ))
        
        for table_name in missing_in_model:
            # Skip system tables and temporary tables
            if not self._is_system_table(table_name):
                self.mismatches.append(ColumnMismatch(
                    table_name=table_name,
                    column_name='*',
                    issue_type='missing_table_in_model',
                    model_info='Table missing in model',
                    db_info='Table exists in database',
                    severity='warning'
                ))
        
        # Check existing tables
        common_tables = model_tables & db_tables
        for table_name in common_tables:
            self._validate_table(table_name)
        
        logger.info(f"Schema validation completed. Found {len(self.mismatches)} issues.")
        return self.mismatches
    
    def _is_system_table(self, table_name: str) -> bool:
        """Check if table is a system table to ignore"""
        system_prefixes = [
            'sqlite_', 'pg_', 'information_schema', 'auth.', 
            'storage.', 'supabase_', '_prisma_', 'alembic_'
        ]
        return any(table_name.startswith(prefix) for prefix in system_prefixes)
    
    def _validate_table(self, table_name: str):
        """Validate a specific table"""
        logger.debug(f"Validating table: {table_name}")
        
        # Get model columns
        model_table = self.metadata.tables[table_name]
        model_columns = {col.name: col for col in model_table.columns}
        
        # Get database columns
        try:
            db_columns_info = self.inspector.get_columns(table_name)
            db_columns = {col['name']: col for col in db_columns_info}
        except Exception as e:
            logger.error(f"Failed to inspect table {table_name}: {e}")
            self.mismatches.append(ColumnMismatch(
                table_name=table_name,
                column_name='*',
                issue_type='inspect_error',
                model_info='Model exists',
                db_info=f'Failed to inspect: {e}',
                severity='error'
            ))
            return
        
        # Check for missing columns
        model_column_names = set(model_columns.keys())
        db_column_names = set(db_columns.keys())
        
        missing_in_db = model_column_names - db_column_names
        missing_in_model = db_column_names - model_column_names
        
        for column_name in missing_in_db:
            model_col = model_columns[column_name]
            self.mismatches.append(ColumnMismatch(
                table_name=table_name,
                column_name=column_name,
                issue_type='missing_in_db',
                model_info=f'{model_col.type} nullable={model_col.nullable}',
                db_info='Column missing in database',
                severity='error' if not model_col.nullable else 'warning'
            ))
        
        for column_name in missing_in_model:
            db_col = db_columns[column_name]
            self.mismatches.append(ColumnMismatch(
                table_name=table_name,
                column_name=column_name,
                issue_type='missing_in_model',
                model_info='Column missing in model',
                db_info=f"{db_col['type']} nullable={db_col.get('nullable', True)}",
                severity='info'  # Usually not critical
            ))
        
        # Check existing columns for mismatches
        common_columns = model_column_names & db_column_names
        for column_name in common_columns:
            self._validate_column(table_name, column_name, model_columns[column_name], db_columns[column_name])
    
    def _validate_column(self, table_name: str, column_name: str, model_col, db_col):
        """Validate a specific column"""
        # Check nullable mismatch (most important for user_id columns)
        model_nullable = model_col.nullable
        db_nullable = db_col.get('nullable', True)
        
        if model_nullable != db_nullable:
            severity = 'error' if column_name == 'user_id' else 'warning'
            self.mismatches.append(ColumnMismatch(
                table_name=table_name,
                column_name=column_name,
                issue_type='nullable_mismatch',
                model_info=f'nullable={model_nullable}',
                db_info=f'nullable={db_nullable}',
                severity=severity
            ))
    
    def get_critical_issues(self) -> List[ColumnMismatch]:
        """Get only critical issues that need immediate attention"""
        return [m for m in self.mismatches if m.severity == 'error']
    
    def get_user_id_issues(self) -> List[ColumnMismatch]:
        """Get issues specifically related to user_id columns"""
        return [m for m in self.mismatches if 'user_id' in m.column_name.lower()]
    
    def print_report(self):
        """Print a comprehensive validation report"""
        print("=" * 80)
        print("DATABASE SCHEMA VALIDATION REPORT")
        print("=" * 80)
        
        if not self.mismatches:
            print("✅ Schema validation passed! No issues found.")
            return
        
        # Group by severity
        errors = [m for m in self.mismatches if m.severity == 'error']
        warnings = [m for m in self.mismatches if m.severity == 'warning']
        info = [m for m in self.mismatches if m.severity == 'info']
        
        print(f"Found {len(self.mismatches)} total issues:")
        print(f"  🚨 {len(errors)} errors")
        print(f"  ⚠️  {len(warnings)} warnings")  
        print(f"  ℹ️  {len(info)} info items")
        print()
        
        # Print critical issues first
        if errors:
            print("🚨 CRITICAL ISSUES (MUST FIX):")
            print("-" * 40)
            for mismatch in errors:
                self._print_mismatch(mismatch)
            print()
        
        # Print user_id specific issues
        user_id_issues = self.get_user_id_issues()
        if user_id_issues:
            print("👤 USER_ID COLUMN ISSUES:")
            print("-" * 40)
            for mismatch in user_id_issues:
                self._print_mismatch(mismatch)
            print()
        
        # Print other warnings
        other_warnings = [w for w in warnings if 'user_id' not in w.column_name.lower()]
        if other_warnings:
            print("⚠️ OTHER WARNINGS:")
            print("-" * 40)
            for mismatch in other_warnings[:10]:  # Limit to first 10
                self._print_mismatch(mismatch)
            if len(other_warnings) > 10:
                print(f"  ... and {len(other_warnings) - 10} more warnings")
            print()
        
        # Summary
        print("RECOMMENDATIONS:")
        if errors:
            print("1. Fix critical errors immediately - they may cause application failures")
        if user_id_issues:
            print("2. Run the user isolation migration: 004_fix_user_isolation_missing_columns.sql")
        if warnings:
            print("3. Review warnings during next maintenance window")
        
        print("=" * 80)
    
    def _print_mismatch(self, mismatch: ColumnMismatch):
        """Print details of a single mismatch"""
        icon = {"error": "🚨", "warning": "⚠️", "info": "ℹ️"}[mismatch.severity]
        print(f"{icon} {mismatch.table_name}.{mismatch.column_name}")
        print(f"    Issue: {mismatch.issue_type}")
        if mismatch.model_info:
            print(f"    Model: {mismatch.model_info}")
        if mismatch.db_info:
            print(f"    Database: {mismatch.db_info}")


def get_database_engine() -> Engine:
    """Get database engine for validation"""
    try:
        db_manager = DatabaseManager()
        return db_manager.engine
    except Exception as e:
        logger.error(f"Failed to get database engine: {e}")
        # Fallback to default SQLite
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/dhafnck_mcp.db')
        return create_engine(database_url)


def run_validation(database_url: Optional[str] = None, fix_issues: bool = False) -> bool:
    """
    Run schema validation
    
    Args:
        database_url: Optional database URL override
        fix_issues: Whether to attempt to fix issues automatically
        
    Returns:
        True if validation passed (no critical issues), False otherwise
    """
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Get database engine
        if database_url:
            engine = create_engine(database_url)
        else:
            engine = get_database_engine()
        
        # Run validation
        validator = SchemaValidator(engine)
        mismatches = validator.validate_all_tables()
        
        # Print report
        validator.print_report()
        
        # Check if we have critical issues
        critical_issues = validator.get_critical_issues()
        
        if fix_issues and critical_issues:
            print("\n🔧 ATTEMPTING TO FIX ISSUES...")
            success = attempt_fixes(engine, critical_issues)
            if success:
                print("✅ Issues fixed successfully!")
            else:
                print("❌ Failed to fix some issues automatically")
        
        return len(critical_issues) == 0
        
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def attempt_fixes(engine: Engine, issues: List[ColumnMismatch]) -> bool:
    """
    Attempt to fix critical schema issues automatically
    
    Args:
        engine: Database engine
        issues: List of critical issues to fix
        
    Returns:
        True if all fixes succeeded, False otherwise
    """
    success = True
    
    with engine.connect() as conn:
        for issue in issues:
            if issue.issue_type == 'missing_in_db' and issue.column_name == 'user_id':
                try:
                    # Attempt to add user_id column
                    sql = f"ALTER TABLE {issue.table_name} ADD COLUMN user_id VARCHAR(255)"
                    conn.execute(text(sql))
                    print(f"✅ Added user_id column to {issue.table_name}")
                except Exception as e:
                    print(f"❌ Failed to add user_id to {issue.table_name}: {e}")
                    success = False
            
            elif issue.issue_type == 'nullable_mismatch' and issue.column_name == 'user_id':
                try:
                    # Attempt to make user_id NOT NULL (after backfilling)
                    table_name = issue.table_name
                    
                    # First backfill with system user
                    backfill_sql = f"""
                    UPDATE {table_name} 
                    SET user_id = '00000000-0000-0000-0000-000000000000' 
                    WHERE user_id IS NULL
                    """
                    conn.execute(text(backfill_sql))
                    
                    # Then set NOT NULL constraint
                    constraint_sql = f"ALTER TABLE {table_name} ALTER COLUMN user_id SET NOT NULL"
                    conn.execute(text(constraint_sql))
                    print(f"✅ Fixed user_id constraint on {table_name}")
                except Exception as e:
                    print(f"❌ Failed to fix user_id constraint on {table_name}: {e}")
                    success = False
        
        conn.commit()
    
    return success


def main():
    """Main entry point for command line usage"""
    parser = argparse.ArgumentParser(description='Validate database schema against SQLAlchemy models')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix critical issues automatically')
    parser.add_argument('--database-url', help='Database URL override')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    success = run_validation(args.database_url, args.fix)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()