#!/usr/bin/env python3
"""
Fix project user_id to match current authenticated user
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# Database connection
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "dhafnck_mcp"
DB_USER = "dhafnck_user"
DB_PASSWORD = "dhafnck_password"

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fix-project-user.py <your-email>")
        print("Example: python3 fix-project-user.py q987@yopmail.com")
        sys.exit(1)

    user_email = sys.argv[1]

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check current projects
        print("🔍 Current projects in database:")
        cur.execute("SELECT id, name, user_id FROM projects")
        projects = cur.fetchall()
        for project in projects:
            print(f"  Project: {project[1]} (ID: {project[0]})")
            print(f"  User ID: {project[2]}")

        # Check if user exists
        print(f"\n🔍 Checking for user with email: {user_email}")
        cur.execute("SELECT id, email FROM users WHERE email = %s", (user_email,))
        user = cur.fetchone()

        if user:
            user_id = user[0]
            print(f"✅ Found user: {user_email} with ID: {user_id}")

            # Update projects to this user
            print(f"\n🔧 Updating all projects to user {user_email}...")
            cur.execute("UPDATE projects SET user_id = %s", (user_id,))
            updated = cur.rowcount
            conn.commit()
            print(f"✅ Updated {updated} project(s)")

            # Also update related entities
            print("\n🔧 Updating related entities...")

            # Update git_branches
            cur.execute("UPDATE git_branches SET user_id = %s", (user_id,))
            print(f"  Updated {cur.rowcount} git branches")

            # Update tasks
            cur.execute("UPDATE tasks SET user_id = %s", (user_id,))
            print(f"  Updated {cur.rowcount} tasks")

            # Update contexts
            cur.execute("UPDATE contexts SET user_id = %s", (user_id,))
            print(f"  Updated {cur.rowcount} contexts")

            conn.commit()
            print("\n✅ All entities updated successfully!")

        else:
            print(f"❌ User with email {user_email} not found in database")
            print("\n💡 Creating user...")

            # For Keycloak users, we need to get the ID from the token
            print("⚠️  To create the user, we need the user ID from your Keycloak token.")
            print("Please provide your token or login first to create the user record.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()