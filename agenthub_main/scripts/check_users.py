#!/usr/bin/env python3
"""Check if there are existing users without token balances"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text

from fastmcp.task_management.infrastructure.database.database_config import (
    DatabaseConfig,
)


def check_users():
    """Check users and token balance initialization"""
    config = DatabaseConfig()
    engine = create_engine(config.database_url)

    with engine.connect() as conn:
        # Count users
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        print(f"Total users: {user_count}")

        # Count token balances
        result = conn.execute(text("SELECT COUNT(*) FROM user_token_balances"))
        balance_count = result.scalar()
        print(f"Token balances: {balance_count}")

        # Find users without balances
        result = conn.execute(text("""
            SELECT u.id, u.email, u.created_at
            FROM users u
            LEFT JOIN user_token_balances utb ON u.id = utb.user_id
            WHERE utb.id IS NULL
            LIMIT 10
        """))

        users_without_balances = list(result)
        if users_without_balances:
            print(f"\n⚠️  {len(users_without_balances)} users WITHOUT token balances:")
            for row in users_without_balances:
                print(f"  - {row[1]} (ID: {row[0][:8]}..., created: {row[2]})")
        else:
            print("\n✓ All users have token balances")

if __name__ == "__main__":
    check_users()
