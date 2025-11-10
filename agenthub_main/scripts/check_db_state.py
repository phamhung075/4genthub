#!/usr/bin/env python3
"""Check database state for token balance migration"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, inspect, text

from fastmcp.task_management.infrastructure.database.database_config import (
    DatabaseConfig,
)


def check_database_state():
    """Check current database state"""
    config = DatabaseConfig()
    engine = create_engine(config.database_url)

    with engine.connect() as conn:
        # Check alembic_version
        print("=== ALEMBIC VERSION ===")
        try:
            result = conn.execute(text("SELECT * FROM alembic_version"))
            for row in result:
                print(f"Current version: {row[0]}")
        except Exception as e:
            print(f"No alembic_version table: {e}")

        # Check if user_token_balances exists
        print("\n=== TABLE user_token_balances ===")
        inspector = inspect(engine)
        if 'user_token_balances' in inspector.get_table_names():
            print("✓ Table EXISTS")

            # Check columns
            columns = inspector.get_columns('user_token_balances')
            print(f"\nColumns ({len(columns)}):")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")

            # Check constraints
            print("\nForeign Keys:")
            for fk in inspector.get_foreign_keys('user_token_balances'):
                print(f"  - {fk}")

            print("\nIndexes:")
            for idx in inspector.get_indexes('user_token_balances'):
                print(f"  - {idx}")

            # Check data
            result = conn.execute(text("SELECT COUNT(*) FROM user_token_balances"))
            count = result.scalar()
            print(f"\nRows: {count}")

            if count > 0:
                result = conn.execute(text("""
                    SELECT id, user_id, available_tokens, monthly_quota
                    FROM user_token_balances
                    LIMIT 5
                """))
                print("\nSample data:")
                for row in result:
                    print(f"  ID: {row[0][:8]}..., User: {row[1][:8]}..., Tokens: {row[2]}, Quota: {row[3]}")
        else:
            print("✗ Table DOES NOT EXIST")

if __name__ == "__main__":
    check_database_state()
