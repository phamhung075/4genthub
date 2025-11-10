#!/usr/bin/env python3
"""
Generate PostgreSQL init schema SQL from actual database
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()


def get_database_url():
    """Get database URL from environment"""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    user = os.getenv("DATABASE_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD", "")
    database = os.getenv("DATABASE_NAME", "agenthub")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def generate_schema_sql(database_url):
    """Generate complete SQL schema from database"""
    engine = create_engine(database_url)
    inspector = inspect(engine)

    sql_lines = []

    # Header
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- AGENTHUB DATABASE SCHEMA - POSTGRESQL")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- AUTO-GENERATED from actual database schema")
    sql_lines.append(f"-- Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_lines.append("-- Database: PostgreSQL 12+")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("")
    sql_lines.append("-- Enable UUID extension for PostgreSQL")
    sql_lines.append('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    sql_lines.append("")

    # Get all tables
    table_names = inspector.get_table_names()

    # Skip system tables
    skip_tables = {'alembic_version', 'applied_migrations'}
    table_names = [t for t in table_names if t not in skip_tables]

    # Drop tables section
    sql_lines.append("-- Drop existing tables in reverse dependency order")
    for table_name in reversed(sorted(table_names)):
        sql_lines.append(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
    sql_lines.append("")

    # Create tables section
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- CREATE TABLES")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("")

    for table_name in sorted(table_names):
        sql_lines.append(f"-- Table: {table_name}")
        sql_lines.append(f"CREATE TABLE {table_name} (")

        columns = inspector.get_columns(table_name)
        pk = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk.get('constrained_columns', []))

        column_defs = []
        for col in columns:
            col_def = f"    {col['name']} "

            # Type
            col_type = str(col['type'])
            if col_type.startswith('VARCHAR'):
                col_def += "VARCHAR"
                # Extract length if present
                if '(' in col_type:
                    length = col_type.split('(')[1].split(')')[0]
                    if length != '11':  # Skip default length
                        col_def += f"({length})"
            elif col_type == 'TEXT':
                col_def += "TEXT"
            elif col_type == 'INTEGER':
                col_def += "INTEGER"
            elif col_type == 'BOOLEAN':
                col_def += "BOOLEAN"
            elif col_type == 'TIMESTAMP':
                col_def += "TIMESTAMP"
            elif col_type == 'UUID':
                col_def += "UUID"
            elif col_type.startswith('JSON'):
                col_def += "JSONB"
            elif col_type == 'DOUBLE_PRECISION':
                col_def += "DOUBLE PRECISION"
            else:
                col_def += col_type

            # Primary key
            if col['name'] in pk_columns:
                col_def += " PRIMARY KEY"
                if col_type == 'UUID':
                    col_def += " DEFAULT uuid_generate_v4()"
                elif col_type == 'INTEGER' and col.get('autoincrement'):
                    col_def += " DEFAULT nextval('..._seq'::regclass)"

            # Nullable
            if not col['nullable'] and col['name'] not in pk_columns:
                col_def += " NOT NULL"

            # Default
            if col.get('default') and col['name'] not in pk_columns:
                default_val = str(col['default'])
                if 'now()' in default_val or 'CURRENT_TIMESTAMP' in default_val:
                    col_def += " DEFAULT now()"
                elif default_val.startswith("'"):
                    col_def += f" DEFAULT {default_val}"
                elif default_val.startswith('nextval'):
                    pass  # Already handled in autoincrement
                elif '::' not in default_val:
                    col_def += f" DEFAULT {default_val}"

            column_defs.append(col_def)

        sql_lines.append(",\n".join(column_defs))
        sql_lines.append(");")
        sql_lines.append("")

    # Foreign keys section
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- FOREIGN KEYS")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("")

    for table_name in sorted(table_names):
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            sql_lines.append(f"-- Foreign keys for {table_name}")
            for fk in fks:
                local_cols = ', '.join(fk['constrained_columns'])
                ref_table = fk['referred_table']
                ref_cols = ', '.join(fk['referred_columns'])
                fk_name = fk.get('name', f"fk_{table_name}_{ref_table}")

                sql_lines.append(
                    f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} "
                    f"FOREIGN KEY ({local_cols}) REFERENCES {ref_table}({ref_cols})"
                )

                # Add ON DELETE if present
                if fk.get('ondelete'):
                    sql_lines[-1] += f" ON DELETE {fk['ondelete']}"

                sql_lines[-1] += ";"
            sql_lines.append("")

    # Indexes section
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- INDEXES")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("")

    for table_name in sorted(table_names):
        indexes = inspector.get_indexes(table_name)
        if indexes:
            sql_lines.append(f"-- Indexes for {table_name}")
            for idx in indexes:
                if idx['unique']:
                    sql_lines.append(
                        f"CREATE UNIQUE INDEX {idx['name']} ON {table_name} "
                        f"({', '.join(idx['column_names'])});"
                    )
                else:
                    sql_lines.append(
                        f"CREATE INDEX {idx['name']} ON {table_name} "
                        f"({', '.join(idx['column_names'])});"
                    )
            sql_lines.append("")

    # Unique constraints section
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- UNIQUE CONSTRAINTS")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("")

    for table_name in sorted(table_names):
        unique_constraints = inspector.get_unique_constraints(table_name)
        if unique_constraints:
            sql_lines.append(f"-- Unique constraints for {table_name}")
            for uc in unique_constraints:
                cols = ', '.join(uc['column_names'])
                sql_lines.append(
                    f"ALTER TABLE {table_name} ADD CONSTRAINT {uc['name']} "
                    f"UNIQUE ({cols});"
                )
            sql_lines.append("")

    # Footer
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("-- SCHEMA GENERATION COMPLETE")
    sql_lines.append("-- " + "=" * 80)
    sql_lines.append("")
    sql_lines.append("SELECT 'AGENTHUB POSTGRESQL DATABASE SCHEMA GENERATED' as status;")

    engine.dispose()
    return "\n".join(sql_lines)


def main():
    database_url = get_database_url()

    print("Generating PostgreSQL schema from database...")
    schema_sql = generate_schema_sql(database_url)

    # Save to file
    output_file = project_root / "agenthub_main" / "src" / "fastmcp" / "task_management" / "infrastructure" / "database" / "init_schema_postgresql.sql"

    with open(output_file, 'w') as f:
        f.write(schema_sql)

    print("\nSchema SQL generated and saved to:")
    print(f"  {output_file}")
    print(f"\nTotal size: {len(schema_sql)} bytes")
    print(f"Total lines: {len(schema_sql.splitlines())}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
