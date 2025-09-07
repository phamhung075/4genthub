#!/usr/bin/env python3
"""
Fix token_metadata field in api_tokens table.

This script ensures all token_metadata fields contain valid JSON dictionaries
instead of SQLAlchemy MetaData() objects or other invalid values.
"""

import os
import sys
import json
import sqlite3
import psycopg2
from psycopg2.extras import Json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def fix_sqlite_metadata(db_path: str):
    """Fix metadata in SQLite database."""
    if not os.path.exists(db_path):
        print(f"SQLite database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if api_tokens table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='api_tokens'"
        )
        if not cursor.fetchone():
            print("api_tokens table does not exist in SQLite database")
            return
        
        # Get all tokens with potentially bad metadata
        cursor.execute("SELECT id, token_metadata FROM api_tokens")
        tokens = cursor.fetchall()
        
        fixed_count = 0
        for token_id, metadata in tokens:
            try:
                # Try to parse the metadata
                if metadata:
                    parsed = json.loads(metadata) if isinstance(metadata, str) else metadata
                    if not isinstance(parsed, dict):
                        raise ValueError("Not a dict")
                    # Metadata is valid, skip
                    continue
            except (json.JSONDecodeError, ValueError, TypeError):
                # Invalid metadata, fix it
                cursor.execute(
                    "UPDATE api_tokens SET token_metadata = ? WHERE id = ?",
                    (json.dumps({}), token_id)
                )
                fixed_count += 1
                print(f"Fixed metadata for token {token_id}")
        
        conn.commit()
        print(f"Fixed {fixed_count} tokens in SQLite database")
        
    except Exception as e:
        print(f"Error fixing SQLite metadata: {e}")
        conn.rollback()
    finally:
        conn.close()


def fix_postgresql_metadata(connection_string: str):
    """Fix metadata in PostgreSQL database."""
    conn = None
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Check if api_tokens table exists
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'api_tokens')"
        )
        if not cursor.fetchone()[0]:
            print("api_tokens table does not exist in PostgreSQL database")
            conn.close()
            return
        
        # Get all tokens with potentially bad metadata
        cursor.execute("SELECT id, token_metadata FROM api_tokens")
        tokens = cursor.fetchall()
        
        fixed_count = 0
        for token_id, metadata in tokens:
            try:
                # Check if metadata is valid
                if metadata and isinstance(metadata, dict):
                    continue  # Valid metadata
                else:
                    raise ValueError("Invalid metadata")
            except (TypeError, ValueError):
                # Invalid metadata, fix it
                cursor.execute(
                    "UPDATE api_tokens SET token_metadata = %s WHERE id = %s",
                    (Json({}), token_id)
                )
                fixed_count += 1
                print(f"Fixed metadata for token {token_id}")
        
        conn.commit()
        print(f"Fixed {fixed_count} tokens in PostgreSQL database")
        
    except psycopg2.OperationalError as e:
        print(f"Could not connect to PostgreSQL: {e}")
    except Exception as e:
        print(f"Error fixing PostgreSQL metadata: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def main():
    """Main function to fix token metadata in all databases."""
    print("Fixing token metadata in databases...")
    
    # Fix SQLite databases
    sqlite_paths = [
        "/home/daihungpham/agentic-project/dhafnck_mcp_main/database/data/dhafnck_mcp_test.db",
        "/data/dhafnck_mcp.db",
        "./dhafnck_mcp.db",
    ]
    
    for path in sqlite_paths:
        if os.path.exists(path):
            print(f"\nFixing SQLite database: {path}")
            fix_sqlite_metadata(path)
    
    # Fix PostgreSQL if configured
    pg_host = os.getenv("DATABASE_HOST", "localhost")
    pg_port = os.getenv("DATABASE_PORT", "5432")
    pg_name = os.getenv("DATABASE_NAME", "dhafnck_mcp")
    pg_user = os.getenv("DATABASE_USER", "dhafnck_user")
    pg_pass = os.getenv("DATABASE_PASSWORD", "dev_password")
    
    if pg_host and pg_user:
        pg_connection = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_name}"
        print(f"\nFixing PostgreSQL database: {pg_name}")
        fix_postgresql_metadata(pg_connection)
    
    # Fix Supabase if configured
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url and "supabase.co" in supabase_url:
        # Extract project ID from URL
        project_id = supabase_url.split("//")[1].split(".")[0]
        supabase_host = f"db.{project_id}.supabase.co"
        supabase_connection = f"postgresql://postgres:{os.getenv('SUPABASE_DB_PASSWORD', '')}@{supabase_host}:5432/postgres"
        print(f"\nFixing Supabase database: {supabase_host}")
        fix_postgresql_metadata(supabase_connection)
    
    print("\nMetadata fix complete!")


if __name__ == "__main__":
    main()