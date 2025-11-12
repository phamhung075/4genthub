#!/usr/bin/env python3
"""
Database Schema Comparison Tool
Compares actual database schema with ORM models and generates migration suggestions
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.schema import Table

# Load environment variables
load_dotenv()


@dataclass
class ColumnDifference:
    """Represents a difference in a column"""

    column_name: str
    difference_type: (
        str  # 'missing_in_db', 'missing_in_orm', 'type_mismatch', 'nullable_mismatch'
    )
    db_value: Any = None
    orm_value: Any = None


@dataclass
class TableDifference:
    """Represents differences in a table"""

    table_name: str
    differences: list[ColumnDifference]
    missing_indexes: list[str] = None
    extra_indexes: list[str] = None


def get_database_url():
    """Get database URL from environment"""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    user = os.getenv("DATABASE_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD", "")
    database = os.getenv("DATABASE_NAME", "agenthub")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_orm_tables():
    """Get all ORM table definitions"""
    orm_tables = {}

    try:
        # Import from task management models
        from fastmcp.task_management.infrastructure.database.models import (
            Agent,
            APIToken,
            BranchContext,
            ContextDelegation,
            ContextInheritanceCache,
            GlobalContext,
            Label,
            MissedNotification,
            Project,
            ProjectContext,
            ProjectGitBranch,
            Subtask,
            Task,
            TaskAssignee,
            TaskContext,
            TaskDependency,
            TaskLabel,
            Template,
        )

        orm_tables.update(
            {
                "projects": Project.__table__,
                "tasks": Task.__table__,
                "project_git_branchs": ProjectGitBranch.__table__,
                "subtasks": Subtask.__table__,
                "task_dependencies": TaskDependency.__table__,
                "labels": Label.__table__,
                "task_labels": TaskLabel.__table__,
                "task_assignees": TaskAssignee.__table__,
                "templates": Template.__table__,
                "agents": Agent.__table__,
                "global_contexts": GlobalContext.__table__,
                "project_contexts": ProjectContext.__table__,
                "branch_contexts": BranchContext.__table__,
                "task_contexts": TaskContext.__table__,
                "context_delegations": ContextDelegation.__table__,
                "context_inheritance_cache": ContextInheritanceCache.__table__,
                "missed_notifications": MissedNotification.__table__,
                "api_tokens": APIToken.__table__,
            }
        )
    except Exception as e:
        print(f"Warning loading task management models: {str(e)}")

    try:
        # Import from agent management models
        from fastmcp.agent_management.infrastructure.database.models import (
            AgentImportHistoryORM,
            AgentTemplateORM,
            UserAgentInstanceORM,
        )

        orm_tables.update(
            {
                "user_agent_instances": UserAgentInstanceORM.__table__,
                "agent_templates": AgentTemplateORM.__table__,
                "agent_import_history": AgentImportHistoryORM.__table__,
            }
        )
    except Exception as e:
        print(f"Warning loading agent management models: {str(e)}")

    try:
        # Import from auth models
        from fastmcp.auth.infrastructure.database.models import User

        orm_tables["users"] = User.__table__
    except Exception as e:
        print(f"Warning loading auth models: {str(e)}")

    if not orm_tables:
        print("ERROR: No ORM tables could be loaded")

    return orm_tables


def compare_columns(db_columns: dict, orm_table: Table) -> list[ColumnDifference]:
    """Compare columns between database and ORM"""
    differences = []

    # Get ORM columns
    orm_columns = {col.name: col for col in orm_table.columns}

    # Check for missing columns in database
    for col_name, orm_col in orm_columns.items():
        if col_name not in db_columns:
            differences.append(
                ColumnDifference(
                    column_name=col_name,
                    difference_type="missing_in_db",
                    orm_value=f"{orm_col.type} {'NOT NULL' if not orm_col.nullable else 'NULL'}",
                )
            )

    # Check for extra columns in database
    for col_name, db_col in db_columns.items():
        if col_name not in orm_columns:
            differences.append(
                ColumnDifference(
                    column_name=col_name,
                    difference_type="missing_in_orm",
                    db_value=f"{db_col['type']} {'NOT NULL' if not db_col['nullable'] else 'NULL'}",
                )
            )
        else:
            # Compare types and nullable
            orm_col = orm_columns[col_name]
            db_type = str(db_col["type"]).upper()
            orm_type = str(orm_col.type).upper()

            # Normalize types for comparison
            type_mappings = {
                "VARCHAR": "STRING",
                "TEXT": "TEXT",
                "INTEGER": "INTEGER",
                "BOOLEAN": "BOOLEAN",
                "TIMESTAMP": "DATETIME",
                "UUID": "UUID",
                "JSON": "JSON",
                "JSONB": "JSON",
                "DOUBLE PRECISION": "FLOAT",
            }

            db_normalized = type_mappings.get(db_type.split("(")[0], db_type)
            orm_normalized = type_mappings.get(orm_type.split("(")[0], orm_type)

            if db_normalized != orm_normalized:
                differences.append(
                    ColumnDifference(
                        column_name=col_name,
                        difference_type="type_mismatch",
                        db_value=db_type,
                        orm_value=orm_type,
                    )
                )

            if db_col["nullable"] != orm_col.nullable:
                differences.append(
                    ColumnDifference(
                        column_name=col_name,
                        difference_type="nullable_mismatch",
                        db_value="NULL" if db_col["nullable"] else "NOT NULL",
                        orm_value="NULL" if orm_col.nullable else "NOT NULL",
                    )
                )

    return differences


def generate_migration_sql(differences: list[TableDifference]) -> str:
    """Generate SQL migration script from differences"""
    sql_statements = []

    sql_statements.append("-- Generated Migration Script")
    sql_statements.append(
        f"-- Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    sql_statements.append("-- WARNING: Review carefully before executing!")
    sql_statements.append("")

    for table_diff in differences:
        if not table_diff.differences:
            continue

        sql_statements.append(f"\n-- Table: {table_diff.table_name}")
        sql_statements.append("BEGIN;")

        for col_diff in table_diff.differences:
            if col_diff.difference_type == "missing_in_db":
                # Add column
                sql_statements.append(
                    f"ALTER TABLE {table_diff.table_name} "
                    f"ADD COLUMN {col_diff.column_name} {col_diff.orm_value};"
                )
            elif col_diff.difference_type == "missing_in_orm":
                # Column exists in DB but not ORM - suggest dropping
                sql_statements.append(
                    "-- WARNING: Column exists in DB but not in ORM model"
                )
                sql_statements.append(
                    f"-- ALTER TABLE {table_diff.table_name} "
                    f"DROP COLUMN {col_diff.column_name};"
                )
            elif col_diff.difference_type == "type_mismatch":
                # Alter column type
                sql_statements.append(
                    f"-- Type mismatch: DB has {col_diff.db_value}, ORM expects {col_diff.orm_value}"
                )
                sql_statements.append(
                    f"-- ALTER TABLE {table_diff.table_name} "
                    f"ALTER COLUMN {col_diff.column_name} TYPE {col_diff.orm_value.split()[0]};"
                )
            elif col_diff.difference_type == "nullable_mismatch":
                # Alter nullable constraint
                if col_diff.orm_value == "NOT NULL":
                    sql_statements.append(
                        f"ALTER TABLE {table_diff.table_name} "
                        f"ALTER COLUMN {col_diff.column_name} SET NOT NULL;"
                    )
                else:
                    sql_statements.append(
                        f"ALTER TABLE {table_diff.table_name} "
                        f"ALTER COLUMN {col_diff.column_name} DROP NOT NULL;"
                    )

        sql_statements.append("COMMIT;")

    return "\n".join(sql_statements)


def main():
    print(f"\n{'=' * 80}")
    print("DATABASE SCHEMA COMPARISON")
    print(f"{'=' * 80}\n")

    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    inspector = inspect(engine)

    # Get ORM tables
    orm_tables = get_orm_tables()
    if not orm_tables:
        print("ERROR: Could not load ORM tables")
        return 1

    print(f"Comparing {len(orm_tables)} ORM tables with database...\n")

    all_differences = []

    for table_name, orm_table in sorted(orm_tables.items()):
        try:
            # Get database columns
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}

            # Compare columns
            differences = compare_columns(db_columns, orm_table)

            if differences:
                all_differences.append(
                    TableDifference(table_name=table_name, differences=differences)
                )

                print(f"TABLE: {table_name}")
                print(f"   {'─' * 70}")
                for diff in differences:
                    if diff.difference_type == "missing_in_db":
                        print(
                            f"   ❌ Column missing in DB: {diff.column_name} ({diff.orm_value})"
                        )
                    elif diff.difference_type == "missing_in_orm":
                        print(
                            f"   ⚠️  Column in DB but not ORM: {diff.column_name} ({diff.db_value})"
                        )
                    elif diff.difference_type == "type_mismatch":
                        print(f"   ⚠️  Type mismatch: {diff.column_name}")
                        print(f"       DB: {diff.db_value}")
                        print(f"       ORM: {diff.orm_value}")
                    elif diff.difference_type == "nullable_mismatch":
                        print(f"   ⚠️  Nullable mismatch: {diff.column_name}")
                        print(f"       DB: {diff.db_value}")
                        print(f"       ORM: {diff.orm_value}")
                print()
        except Exception as e:
            print(f"   ERROR comparing {table_name}: {str(e)}")
            print()

    engine.dispose()

    # Generate migration script
    if all_differences:
        print(f"\n{'=' * 80}")
        print("MIGRATION SCRIPT")
        print(f"{'=' * 80}\n")

        migration_sql = generate_migration_sql(all_differences)
        print(migration_sql)

        # Save to file
        migration_file = project_root / "scripts" / "generated_migration.sql"
        with open(migration_file, "w") as f:
            f.write(migration_sql)

        print(f"\n\nMigration script saved to: {migration_file}")
        print(f"\nFound {len(all_differences)} tables with differences")
        print(f"Total differences: {sum(len(d.differences) for d in all_differences)}")
    else:
        print("\n✅ No differences found! Database schema matches ORM models.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
