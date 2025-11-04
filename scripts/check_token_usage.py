#!/usr/bin/env python3
"""
Check token usage statistics in the database
"""
import os
import sys
from sqlalchemy import create_engine, text
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agenthub_main', 'src'))

from fastmcp.task_management.infrastructure.database.database_config import get_db_config

def check_token_usage():
    """Check usage statistics for all tokens."""

    db_config = get_db_config()
    engine = db_config.engine

    with engine.connect() as conn:
        # Query all tokens with their usage data
        result = conn.execute(text("""
            SELECT
                id,
                name,
                usage_count,
                usage_stats,
                rate_limit,
                last_used_at,
                is_active
            FROM api_tokens
            WHERE is_active = true
            ORDER BY last_used_at DESC NULLS LAST
        """))

        print("\n" + "="*80)
        print("📊 TOKEN USAGE STATISTICS")
        print("="*80 + "\n")

        tokens = result.fetchall()

        if not tokens:
            print("❌ No active tokens found")
            return

        for token in tokens:
            token_id, name, usage_count, usage_stats, rate_limit, last_used, is_active = token

            print(f"🎫 Token: {name}")
            print(f"   ID: {token_id}")
            print(f"   Status: {'✅ Active' if is_active else '❌ Inactive'}")
            print(f"   Rate Limit: {rate_limit} requests/hour")
            print(f"   Last Used: {last_used or 'Never'}")
            print(f"\n   📈 Usage Statistics:")
            print(f"      Total Requests: {usage_count}")

            if usage_stats:
                print(f"\n      📊 Operation Breakdown:")
                # Sort by count descending
                sorted_ops = sorted(usage_stats.items(), key=lambda x: x[1], reverse=True)
                for operation, count in sorted_ops:
                    # Format operation name nicely
                    op_name = operation.replace('_', ' ').title()
                    percentage = (count / usage_count * 100) if usage_count > 0 else 0
                    print(f"         • {op_name}: {count} ({percentage:.1f}%)")
            else:
                print(f"         (No operation data yet)")

            print("\n" + "-"*80 + "\n")

if __name__ == "__main__":
    try:
        check_token_usage()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
