#!/usr/bin/env python3

import psycopg2
from psycopg2 import sql

# Connect to PostgreSQL as superuser to create database
conn_params = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',  # Connect to default database
    'user': 'dhafnck_user',
    'password': 'ChangeThisSecurePassword2025!'
}

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = True  # Need autocommit for CREATE DATABASE
    cursor = conn.cursor()
    
    # Check if test database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='dhafnck_mcp_test'")
    exists = cursor.fetchone()
    
    if not exists:
        # Create test database
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier('dhafnck_mcp_test')
        ))
        print("✅ Created database: dhafnck_mcp_test")
    else:
        print("✅ Database already exists: dhafnck_mcp_test")
    
    cursor.close()
    conn.close()
    
    print("✅ Test database is ready!")
    
except Exception as e:
    print(f"❌ Error creating database: {e}")
    print("Note: You may need to manually create the database.")
    print("Try: sudo -u postgres psql -c 'CREATE DATABASE dhafnck_mcp_test;'")