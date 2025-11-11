#!/usr/bin/env python3
"""
Verify init_schema_postgresql.sql matches actual database
"""

import os
import re
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


def parse_sql_file(sql_file_path):
    """Parse SQL file and extract table names"""
    with open(sql_file_path) as f:
        content = f.read()

    # Extract CREATE TABLE statements
    create_table_pattern = r"CREATE TABLE\s+(\w+)\s*\("
    tables = set(re.findall(create_table_pattern, content, re.IGNORECASE))

    return tables


def get_actual_tables(database_url):
    """Get actual tables from database"""
    engine = create_engine(database_url)
    inspector = inspect(engine)

    # Get all tables except system tables
    skip_tables = {"alembic_version", "applied_migrations"}
    actual_tables = set(inspector.get_table_names())
    actual_tables = {t for t in actual_tables if t not in skip_tables}

    engine.dispose()
    return actual_tables


def verify_table_columns(sql_file_path, database_url):
    """Verify columns in each table match between SQL file and database"""
    issues = []

    with open(sql_file_path) as f:
        sql_content = f.read()

    engine = create_engine(database_url)
    inspector = inspect(engine)

    # Extract tables from SQL
    sql_tables = parse_sql_file(sql_file_path)

    for table_name in sorted(sql_tables):
        try:
            # Get actual database columns
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}

            # Extract columns from SQL for this table
            table_section_pattern = f"CREATE TABLE {table_name}\\s*\\((.+?)\\);"
            match = re.search(
                table_section_pattern, sql_content, re.DOTALL | re.IGNORECASE
            )

            if not match:
                issues.append(
                    f"❌ Table {table_name}: Could not find CREATE TABLE statement in SQL"
                )
                continue

            table_def = match.group(1)

            # Extract column names from SQL (rough parsing)
            column_lines = [
                line.strip()
                for line in table_def.split("\n")
                if line.strip() and not line.strip().startswith("--")
            ]
            sql_columns = set()

            for line in column_lines:
                # Skip constraint lines
                if any(
                    keyword in line.upper()
                    for keyword in [
                        "PRIMARY KEY",
                        "FOREIGN KEY",
                        "UNIQUE",
                        "CHECK",
                        "CONSTRAINT",
                    ]
                ):
                    if not line.split()[0].replace(",", "").isidentifier():
                        continue

                # Extract column name (first word)
                parts = line.split()
                if parts:
                    col_name = parts[0].replace(",", "")
                    if col_name.isidentifier():
                        sql_columns.add(col_name)

            # Compare
            db_col_names = set(db_columns.keys())

            # Check for missing columns in SQL
            missing_in_sql = db_col_names - sql_columns
            if missing_in_sql:
                issues.append(
                    f"⚠️  Table {table_name}: Columns missing in SQL: {', '.join(sorted(missing_in_sql))}"
                )

            # Check for extra columns in SQL
            extra_in_sql = sql_columns - db_col_names
            if extra_in_sql:
                issues.append(
                    f"⚠️  Table {table_name}: Extra columns in SQL: {', '.join(sorted(extra_in_sql))}"
                )

        except Exception as e:
            issues.append(f"❌ Table {table_name}: Error - {str(e)}")

    engine.dispose()
    return issues


def main():
    print(f"\n{'=' * 80}")
    print("VERIFY INIT SCHEMA SQL vs ACTUAL DATABASE")
    print(f"{'=' * 80}\n")

    sql_file_path = (
        project_root
        / "agenthub_main"
        / "src"
        / "fastmcp"
        / "task_management"
        / "infrastructure"
        / "database"
        / "init_schema_postgresql.sql"
    )

    if not sql_file_path.exists():
        print(f"❌ SQL file not found: {sql_file_path}")
        return 1

    database_url = get_database_url()

    print(f"SQL File: {sql_file_path}")
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'N/A'}\n")

    # Step 1: Compare table lists
    print("Step 1: Comparing table lists...")
    print("-" * 80)

    sql_tables = parse_sql_file(sql_file_path)
    actual_tables = get_actual_tables(database_url)

    print(f"Tables in SQL file: {len(sql_tables)}")
    print(f"Tables in database: {len(actual_tables)}\n")

    # Check for missing tables
    missing_in_sql = actual_tables - sql_tables
    if missing_in_sql:
        print("❌ Tables in database but NOT in SQL file:")
        for table in sorted(missing_in_sql):
            print(f"   • {table}")
        print()
    else:
        print("✅ All database tables are in SQL file\n")

    # Check for extra tables
    extra_in_sql = sql_tables - actual_tables
    if extra_in_sql:
        print("⚠️  Tables in SQL file but NOT in database:")
        for table in sorted(extra_in_sql):
            print(f"   • {table}")
        print()
    else:
        print("✅ No extra tables in SQL file\n")

    # Step 2: Verify column structure
    print("\nStep 2: Verifying column structure...")
    print("-" * 80)

    column_issues = verify_table_columns(sql_file_path, database_url)

    if column_issues:
        print(f"\nFound {len(column_issues)} column issues:\n")
        for issue in column_issues:
            print(issue)
    else:
        print("\n✅ All table columns match!\n")

    # Summary
    print(f"\n{'=' * 80}")
    print("VERIFICATION SUMMARY")
    print(f"{'=' * 80}\n")

    total_issues = len(missing_in_sql) + len(extra_in_sql) + len(column_issues)

    if total_issues == 0:
        print("✅ PERFECT MATCH!")
        print("   The init_schema_postgresql.sql file matches the actual database.\n")
        return 0
    else:
        print(f"⚠️  Found {total_issues} issues:")
        print(f"   • Tables missing in SQL: {len(missing_in_sql)}")
        print(f"   • Extra tables in SQL: {len(extra_in_sql)}")
        print(f"   • Column issues: {len(column_issues)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
