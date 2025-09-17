#!/usr/bin/env python3
"""
Script to clean all data from Supabase public schema
WARNING: This will delete ALL data from ALL tables in the public schema!
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Supabase connection details from environment
DATABASE_URL = os.getenv('SUPABASE_DATABASE_URL')
DB_HOST = os.getenv('SUPABASE_DB_HOST')
DB_PORT = os.getenv('SUPABASE_DB_PORT', '5432')
DB_NAME = os.getenv('SUPABASE_DB_NAME', 'postgres')
DB_USER = os.getenv('SUPABASE_DB_USER', 'postgres')
DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')

def get_connection():
    """Create a connection to Supabase database"""
    try:
        # Use DATABASE_URL if available, otherwise construct from parts
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL)
        else:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                sslmode='require'
            )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def get_all_tables(conn):
    """Get all tables in the public schema"""
    cursor = conn.cursor()
    query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename NOT LIKE 'pg_%' 
        AND tablename NOT LIKE 'sql_%'
        AND tablename NOT IN ('schema_migrations', 'migrations')
        ORDER BY tablename;
    """
    cursor.execute(query)
    tables = cursor.fetchall()
    cursor.close()
    return [table[0] for table in tables]

def get_table_count(conn, table_name):
    """Get the row count for a specific table"""
    cursor = conn.cursor()
    query = sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table_name))
    try:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    except Exception as e:
        cursor.close()
        return 0

def backup_table_data(conn, table_name):
    """Create a backup of table data (just print for now)"""
    cursor = conn.cursor()
    query = sql.SQL("SELECT * FROM public.{} LIMIT 5").format(sql.Identifier(table_name))
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            # Get column names
            col_names = [desc[0] for desc in cursor.description]
            print(f"\n  Sample data from {table_name} (first 5 rows):")
            print(f"  Columns: {col_names}")
            for i, row in enumerate(rows, 1):
                print(f"  Row {i}: {row}")
    except Exception as e:
        print(f"  Could not fetch sample data: {e}")
    finally:
        cursor.close()

def truncate_table(conn, table_name):
    """Truncate a single table"""
    cursor = conn.cursor()
    try:
        # Use TRUNCATE with CASCADE to handle foreign key constraints
        query = sql.SQL("TRUNCATE TABLE public.{} CASCADE").format(sql.Identifier(table_name))
        cursor.execute(query)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Failed to truncate {table_name}: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("=" * 60)
    print("SUPABASE DATA CLEANUP SCRIPT")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Database: {DB_HOST}/{DB_NAME}")
    print()
    
    # Connect to database
    print("🔌 Connecting to Supabase database...")
    conn = get_connection()
    print("✅ Connected successfully!")
    print()
    
    # Get all tables
    print("📋 Fetching all tables in public schema...")
    tables = get_all_tables(conn)
    
    if not tables:
        print("ℹ️  No tables found in public schema.")
        conn.close()
        return
    
    print(f"Found {len(tables)} table(s):")
    print()
    
    # Show table information
    total_rows = 0
    table_info = []
    for table in tables:
        count = get_table_count(conn, table)
        total_rows += count
        table_info.append((table, count))
        status = "⚠️  Has data" if count > 0 else "✓ Empty"
        print(f"  • {table}: {count} rows {status}")
    
    print()
    print(f"Total rows across all tables: {total_rows}")
    print()
    
    if total_rows == 0:
        print("ℹ️  All tables are already empty. Nothing to clean.")
        conn.close()
        return
    
    # Confirmation
    print("⚠️  WARNING: This will DELETE ALL DATA from the above tables!")
    print("⚠️  This action cannot be undone!")
    print()
    
    # Check for command-line argument to skip confirmation
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔥 Force flag detected. Proceeding with deletion...")
        confirmation = "DELETE ALL DATA"
    else:
        confirmation = input("Type 'DELETE ALL DATA' to confirm: ")
    
    if confirmation != "DELETE ALL DATA":
        print("\n❌ Operation cancelled. No data was deleted.")
        conn.close()
        return
    
    print("\n🗑️  Starting data cleanup...")
    print("=" * 60)
    
    # Clean each table
    success_count = 0
    failed_tables = []
    
    for table, original_count in table_info:
        if original_count > 0:
            print(f"\n📊 Processing table: {table}")
            print(f"  Original row count: {original_count}")
            
            # Show sample data before deletion
            backup_table_data(conn, table)
            
            # Truncate the table
            print(f"  🗑️  Truncating table...")
            if truncate_table(conn, table):
                new_count = get_table_count(conn, table)
                print(f"  ✅ Success! New row count: {new_count}")
                success_count += 1
            else:
                failed_tables.append(table)
    
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully cleaned: {success_count} table(s)")
    
    if failed_tables:
        print(f"❌ Failed to clean: {len(failed_tables)} table(s)")
        for table in failed_tables:
            print(f"  • {table}")
    
    # Verify final state
    print("\n📊 Final table states:")
    for table in tables:
        count = get_table_count(conn, table)
        status = "✅ Empty" if count == 0 else f"⚠️  Still has {count} rows"
        print(f"  • {table}: {status}")
    
    # Close connection
    conn.close()
    print("\n✅ Database connection closed.")
    print("🎉 Cleanup complete!")

if __name__ == "__main__":
    main()