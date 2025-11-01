#!/usr/bin/env python3
"""
Recreate Agent Management Tables

This script DROPS and recreates the agent_templates and user_agent_instances
tables to ensure they match the current ORM schema.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from fastmcp.agent_management.infrastructure.database.models import (
    AgentTemplateORM,
    UserAgentInstanceORM
)
from fastmcp.agent_management.infrastructure.repositories import ORMAgentTemplateRepository

print("=" * 80)
print("RECREATING AGENT MANAGEMENT TABLES")
print("=" * 80)

try:
    repository = ORMAgentTemplateRepository()
    with repository.get_db_session() as session:
        engine = session.get_bind()

        print(f"\nDatabase engine: {engine.url}")

        # Drop tables if they exist
        print("\n⚠️  Dropping existing agent management tables...")
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS user_agent_instances CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS agent_templates CASCADE"))
        print("✅ Old tables dropped")

        # Recreate tables with current ORM schema
        print("\n📝 Creating agent management tables with current schema...")
        AgentTemplateORM.__table__.create(engine)
        UserAgentInstanceORM.__table__.create(engine)
        print("✅ Tables created successfully")

        # Verify tables exist and show schema
        from sqlalchemy import inspect
        inspector = inspect(engine)

        print("\n📋 agent_templates columns:")
        for column in inspector.get_columns('agent_templates'):
            print(f"  - {column['name']}: {column['type']}")

        print("\n📋 user_agent_instances columns:")
        for column in inspector.get_columns('user_agent_instances'):
            print(f"  - {column['name']}: {column['type']}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("TABLE RECREATION COMPLETE")
print("=" * 80)
