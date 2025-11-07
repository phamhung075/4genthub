#!/usr/bin/env python3
"""
Deep verification of init_schema_postgresql.sql against actual database
Checks columns, types, constraints, indexes, and foreign keys
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()


def get_database_url():
    """Get database URL from environment"""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    user = os.getenv("DATABASE_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD", "")
    database = os.getenv("DATABASE_NAME", "agenthub")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def verify_critical_tables(database_url):
    """Verify critical tables have expected structure"""
    engine = create_engine(database_url)
    inspector = inspect(engine)

    print(f"\n{'='*80}")
    print(f"DETAILED TABLE VERIFICATION")
    print(f"{'='*80}\n")

    # Define critical tables and their expected columns
    critical_checks = {
        'tasks': {
            'columns': [
                'id', 'title', 'description', 'git_branch_id', 'status', 'priority',
                'progress_history', 'progress_count', 'estimated_effort', 'due_date',
                'created_at', 'updated_at', 'completed_at', 'completion_summary',
                'testing_notes', 'context_id', 'progress_percentage', 'progress_state',
                'user_id', 'ai_system_prompt', 'ai_request_prompt', 'ai_work_context',
                'ai_completion_criteria', 'ai_execution_history', 'ai_last_execution',
                'ai_model_preferences', 'completed_subtasks', 'subtask_count'
            ],
            'indexes': [
                'idx_task_branch', 'idx_task_status', 'idx_task_priority',
                'idx_task_created', 'idx_tasks_updated_at', 'idx_tasks_progress_count'
            ],
            'fks': ['git_branch_id']
        },
        'subtasks': {
            'columns': [
                'id', 'task_id', 'title', 'description', 'status', 'priority',
                'assignees', 'estimated_effort', 'progress_percentage', 'progress_state',
                'progress_notes', 'blockers', 'completion_summary', 'impact_on_parent',
                'insights_found', 'user_id', 'created_at', 'updated_at', 'completed_at',
                'ai_system_prompt', 'ai_request_prompt', 'ai_work_context',
                'ai_completion_criteria', 'ai_execution_history', 'ai_last_execution',
                'ai_model_preferences', 'progress_history', 'progress_count'
            ],
            'indexes': ['idx_subtask_task', 'idx_subtask_status', 'idx_subtasks_updated_at'],
            'fks': ['task_id']
        },
        'project_git_branchs': {
            'columns': [
                'id', 'project_id', 'name', 'description', 'created_at', 'updated_at',
                'assigned_agent_id', 'agent_id', 'priority', 'status', 'metadata',
                'task_count', 'completed_task_count', 'user_id'
            ],
            'indexes': ['idx_branches_updated_at', 'uq_branch_project'],
            'fks': ['project_id']
        },
        'projects': {
            'columns': [
                'id', 'name', 'description', 'created_at', 'updated_at',
                'user_id', 'status', 'metadata'
            ],
            'indexes': ['idx_projects_updated_at', 'uq_project_user'],
            'fks': []
        }
    }

    all_ok = True

    for table_name, checks in critical_checks.items():
        print(f"\n{'─'*80}")
        print(f"Table: {table_name}")
        print(f"{'─'*80}")

        # Check columns
        actual_columns = {col['name']: col for col in inspector.get_columns(table_name)}
        expected_columns = set(checks['columns'])
        actual_col_names = set(actual_columns.keys())

        missing_cols = expected_columns - actual_col_names
        extra_cols = actual_col_names - expected_columns

        if missing_cols:
            print(f"❌ Missing columns: {', '.join(sorted(missing_cols))}")
            all_ok = False
        elif extra_cols:
            print(f"⚠️  Extra columns: {', '.join(sorted(extra_cols))}")
        else:
            print(f"✅ All {len(expected_columns)} columns present")

        # Show important column types
        if table_name == 'tasks':
            print(f"\n   Key column types:")
            for col in ['id', 'git_branch_id', 'completed_subtasks', 'subtask_count']:
                if col in actual_columns:
                    col_info = actual_columns[col]
                    nullable = "NULL" if col_info['nullable'] else "NOT NULL"
                    default = f"DEFAULT {col_info['default']}" if col_info.get('default') else ""
                    print(f"      • {col}: {col_info['type']} {nullable} {default}")

        # Check indexes
        actual_indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
        # Also check unique constraints as they create indexes
        unique_constraints = {uc['name'] for uc in inspector.get_unique_constraints(table_name)}
        actual_indexes.update(unique_constraints)

        expected_indexes = set(checks['indexes'])
        missing_indexes = expected_indexes - actual_indexes

        if missing_indexes:
            print(f"⚠️  Missing indexes: {', '.join(sorted(missing_indexes))}")
        else:
            print(f"✅ All {len(expected_indexes)} expected indexes present")

        # Check foreign keys
        actual_fks = inspector.get_foreign_keys(table_name)
        actual_fk_cols = {fk['constrained_columns'][0] for fk in actual_fks if fk['constrained_columns']}
        expected_fk_cols = set(checks['fks'])

        missing_fks = expected_fk_cols - actual_fk_cols
        if missing_fks:
            print(f"❌ Missing foreign keys: {', '.join(sorted(missing_fks))}")
            all_ok = False
        elif expected_fk_cols:
            print(f"✅ All {len(expected_fk_cols)} foreign keys present")

        # Check CASCADE behavior for critical FKs
        if table_name in ['subtasks', 'task_assignees', 'task_dependencies']:
            for fk in actual_fks:
                if 'task_id' in fk['constrained_columns']:
                    if fk.get('ondelete') == 'CASCADE':
                        print(f"✅ CASCADE delete enabled on task_id")
                    else:
                        print(f"⚠️  CASCADE delete NOT enabled on task_id (found: {fk.get('ondelete')})")
                        all_ok = False

    engine.dispose()

    print(f"\n{'='*80}")
    if all_ok:
        print("✅ ALL CRITICAL TABLES VERIFIED SUCCESSFULLY")
    else:
        print("⚠️  SOME ISSUES FOUND - Review above")
    print(f"{'='*80}\n")

    return 0 if all_ok else 1


def main():
    database_url = get_database_url()
    return verify_critical_tables(database_url)


if __name__ == "__main__":
    sys.exit(main())
