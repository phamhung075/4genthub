#!/usr/bin/env python3
"""Check foreign key CASCADE settings in database"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from sqlalchemy import create_engine, inspect, text


def get_database_url():
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    user = os.getenv("DATABASE_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD", "your_secure_password_here")
    database = os.getenv("DATABASE_NAME", "agenthub")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(get_database_url())
inspector = inspect(engine)

print("\nForeign Keys in Database:")
print("=" * 100)

tables_to_check = ['subtasks', 'task_assignees', 'task_dependencies', 'task_labels', 'tasks', 'project_git_branchs', 'branch_contexts', 'task_contexts', 'project_contexts']

for table in sorted(tables_to_check):
    fks = inspector.get_foreign_keys(table)
    if fks:
        print(f"\nTable: {table}")
        print("-" * 100)
        for fk in fks:
            local_cols = ', '.join(fk['constrained_columns'])
            ref_table = fk['referred_table']
            ref_cols = ', '.join(fk['referred_columns'])
            on_delete = fk.get('ondelete') or 'NO ACTION'
            name = fk.get('name', 'unnamed')

            status = "✅" if on_delete == 'CASCADE' else "⚠️ "
            print(f"  {status} {local_cols:25} → {ref_table:30}({ref_cols:20}) ON DELETE {on_delete:15} ({name})")

engine.dispose()
