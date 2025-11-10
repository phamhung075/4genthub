#!/usr/bin/env python3
"""
Database Schema Inspector
Inspects the actual database schema and compares with ORM models
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Load environment variables
load_dotenv()


def get_database_url(use_local=True):
    """Get database URL from environment"""
    if use_local:
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432")
        user = os.getenv("DATABASE_USER", "postgres")
        password = os.getenv("DATABASE_PASSWORD", "")
        database = os.getenv("DATABASE_NAME", "agenthub")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        return os.getenv("SUPABASE_DATABASE_URL")


def inspect_database(database_url):
    """Inspect database schema"""
    print(f"\n{'='*80}")
    print("DATABASE SCHEMA INSPECTION")
    print(f"{'='*80}")
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'N/A'}\n")

    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)

        # Get all table names
        table_names = inspector.get_table_names()
        print(f"Found {len(table_names)} tables:\n")

        for idx, table_name in enumerate(sorted(table_names), 1):
            print(f"\n{idx}. TABLE: {table_name}")
            print(f"   {'-'*70}")

            # Get columns
            columns = inspector.get_columns(table_name)
            print(f"   Columns ({len(columns)}):")
            for col in columns:
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                default = f"DEFAULT {col['default']}" if col.get('default') else ""
                print(f"      • {col['name']:30} {col_type:20} {nullable:10} {default}")

            # Get primary keys
            pk = inspector.get_pk_constraint(table_name)
            if pk and pk.get('constrained_columns'):
                print(f"\n   Primary Key: {', '.join(pk['constrained_columns'])}")

            # Get foreign keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print(f"\n   Foreign Keys ({len(fks)}):")
                for fk in fks:
                    ref_table = fk['referred_table']
                    ref_cols = ', '.join(fk['referred_columns'])
                    local_cols = ', '.join(fk['constrained_columns'])
                    print(f"      • {local_cols} → {ref_table}({ref_cols})")

            # Get indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                print(f"\n   Indexes ({len(indexes)}):")
                for idx_info in indexes:
                    unique = "UNIQUE" if idx_info['unique'] else "INDEX"
                    cols = ', '.join(idx_info['column_names'])
                    print(f"      • {idx_info['name']:40} {unique:10} ({cols})")

            # Get unique constraints
            unique_constraints = inspector.get_unique_constraints(table_name)
            if unique_constraints:
                print(f"\n   Unique Constraints ({len(unique_constraints)}):")
                for uc in unique_constraints:
                    cols = ', '.join(uc['column_names'])
                    print(f"      • {uc['name']:40} ({cols})")

        print(f"\n{'='*80}")
        print("INSPECTION COMPLETE")
        print(f"{'='*80}\n")

        # Additional queries for useful information
        with engine.connect() as conn:
            # Get database size
            result = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
            db_size = result.scalar()
            print(f"Database Size: {db_size}")

            # Get table sizes
            print("\nTable Sizes:")
            result = conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    pg_total_relation_size(schemaname||'.'||tablename) AS raw_size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY raw_size DESC
            """))
            for row in result:
                print(f"   • {row[1]:40} {row[2]:>15}")

        engine.dispose()
        return True

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def compare_with_orm():
    """Compare database schema with ORM models"""
    print(f"\n{'='*80}")
    print("ORM MODEL INSPECTION")
    print(f"{'='*80}\n")

    try:
        from fastmcp.agent_management.domain.entities import (
            SharedAgentInstance,
            UserAgentInstance,
        )
        from fastmcp.task_management.domain.entities import (
            Context,
            GitBranch,
            Project,
            Subtask,
            Task,
        )

        orm_models = [
            Project, Task, GitBranch, Subtask, Context,
            UserAgentInstance, SharedAgentInstance
        ]

        for model in orm_models:
            table_name = model.__tablename__
            print(f"\nORM Model: {model.__name__} → Table: {table_name}")
            print(f"   {'-'*70}")

            # Get columns from SQLAlchemy model
            for col_name, col in model.__table__.columns.items():
                col_type = str(col.type)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = f"DEFAULT {col.default}" if col.default else ""
                pk = "PRIMARY KEY" if col.primary_key else ""
                fk = "FOREIGN KEY" if col.foreign_keys else ""
                print(f"      • {col_name:30} {col_type:20} {nullable:10} {pk:15} {fk:15} {default}")

        print(f"\n{'='*80}")

    except Exception as e:
        print(f"ERROR loading ORM models: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Inspect database schema")
    parser.add_argument("--local", action="store_true", default=True, help="Use local database (default)")
    parser.add_argument("--supabase", action="store_true", help="Use Supabase database")
    parser.add_argument("--orm", action="store_true", help="Show ORM model structure")
    parser.add_argument("--compare", action="store_true", help="Compare database with ORM models")

    args = parser.parse_args()

    # Determine which database to use
    use_local = not args.supabase
    database_url = get_database_url(use_local=use_local)

    # Inspect database
    success = inspect_database(database_url)

    # Show ORM models if requested
    if args.orm or args.compare:
        compare_with_orm()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
