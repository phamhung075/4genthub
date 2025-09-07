# Scripts Directory

This directory contains utility scripts for database operations, maintenance, and system administration.

## Directory Structure

### `/database/`
Database utility scripts for schema management and data operations:
- `check_table_schema.py` - Check actual database table schema
- `create_tables_manual.py` - Manually create database tables
- `create_missing_tables.py` - Create any missing database tables

### Root Scripts
- `fix_task_counts.py` - Fix task_count synchronization issues in git branches
- `init_database.py` - Initialize database with schema
- `migrate_project_contexts.py` - **NEW**: Create missing contexts for existing projects to make them visible in frontend

## Usage

All scripts should be run from the project root with proper environment configuration:

```bash
# Set environment variables
export DATABASE_TYPE=postgresql
export DATABASE_URL=postgresql://user:password@localhost:5432/dhafnck_mcp

# Run a script
python dhafnck_mcp_main/scripts/database/check_table_schema.py

# Run project context migration (with dry-run first)
python dhafnck_mcp_main/scripts/migrate_project_contexts.py --dry-run
python dhafnck_mcp_main/scripts/migrate_project_contexts.py
```

## Project Context Migration

The `migrate_project_contexts.py` script fixes the issue where existing projects are invisible in the frontend due to missing context records.

### Features
- Queries all projects and identifies those lacking contexts
- Creates complete 4-tier context hierarchy (GLOBAL → PROJECT → BRANCH → TASK)
- Handles global context requirement automatically
- Supports dry-run mode for safe testing
- Runnable both inside Docker containers and locally
- Detailed reporting of migration progress and statistics

### Usage Examples
```bash
# Test what would be migrated (safe)
python dhafnck_mcp_main/scripts/migrate_project_contexts.py --dry-run

# Migrate all projects for current user
python dhafnck_mcp_main/scripts/migrate_project_contexts.py

# Migrate projects for specific user
python dhafnck_mcp_main/scripts/migrate_project_contexts.py --user-id "user123"

# Inside Docker container
docker exec -it dhafnck-backend python scripts/migrate_project_contexts.py --dry-run
```

## Important Notes

- Always backup your database before running schema modification scripts
- Ensure proper environment variables are set before execution
- These scripts are for administrative use only