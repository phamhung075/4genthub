#!/usr/bin/env python3
"""
Create Agent Management Tables

This script creates the agent_templates and user_agent_instances tables
in the database using the ORM models.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

from fastmcp.agent_management.infrastructure.database.models import (
    AgentTemplateORM,
    UserAgentInstanceORM,
)
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
)

print("=" * 80)
print("CREATING AGENT MANAGEMENT TABLES")
print("=" * 80)

try:
    # Get a session via repository to ensure database connection is established
    repository = ORMAgentTemplateRepository()
    with repository.get_db_session() as session:
        engine = session.get_bind()

        print(f"\nDatabase engine: {engine.url}")

        # Create only the agent management tables
        print("\nCreating agent_templates and user_agent_instances tables...")

        # Create tables for agent management models
        AgentTemplateORM.__table__.create(engine, checkfirst=True)
        UserAgentInstanceORM.__table__.create(engine, checkfirst=True)

        print("✅ Tables created successfully!")

        # Verify tables exist
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print("\n📋 Existing tables:")
        for table in sorted(tables):
            print(f"  - {table}")

        if "agent_templates" in tables and "user_agent_instances" in tables:
            print("\n✅ Agent management tables confirmed!")
        else:
            print("\n⚠️  Some tables may be missing")

except Exception as e:
    print(f"\n❌ Error creating tables: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("TABLE CREATION COMPLETE")
print("=" * 80)
