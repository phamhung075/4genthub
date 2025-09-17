#!/usr/bin/env python3
"""
Database Setup Verification Script
==================================

Verifies that the database is properly set up after migration and tests
basic functionality to ensure MCP tools will work correctly.

Usage:
    python verify_database_setup.py [--supabase] [--local] [--detailed]
    
Arguments:
    --supabase: Verify Supabase database
    --local: Verify local PostgreSQL database  
    --detailed: Run detailed verification including sample data creation
"""

import os
import sys
import argparse
import psycopg2
import json
import uuid
from datetime import datetime
from urllib.parse import urlparse


def parse_database_url(db_url: str) -> dict:
    """Parse database URL into components"""
    parsed = urlparse(db_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password
    }


def verify_basic_schema(cursor) -> dict:
    """Verify basic schema structure"""
    results = {}
    
    # Check required tables exist
    required_tables = [
        'database_status', 'projects', 'project_git_branchs', 'tasks', 
        'subtasks', 'task_dependencies', 'agents',
        'global_contexts', 'project_contexts', 'branch_contexts', 'task_contexts',
        'user_access_log'
    ]
    
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    existing_tables = [row[0] for row in cursor.fetchall()]
    missing_tables = [t for t in required_tables if t not in existing_tables]
    
    results['tables'] = {
        'required': len(required_tables),
        'found': len(existing_tables),
        'missing': missing_tables,
        'all_tables': existing_tables
    }
    
    return results


def verify_user_isolation(cursor) -> dict:
    """Verify user isolation is properly implemented"""
    results = {}
    
    # Check user_id columns exist
    user_isolation_tables = [
        'projects', 'project_git_branchs', 'tasks', 'subtasks', 
        'task_dependencies', 'agents', 'global_contexts', 
        'project_contexts', 'branch_contexts', 'task_contexts'
    ]
    
    missing_user_id = []
    for table in user_isolation_tables:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = %s AND column_name = 'user_id'
        """, (table,))
        
        if not cursor.fetchone():
            missing_user_id.append(table)
    
    results['user_isolation'] = {
        'tables_checked': len(user_isolation_tables),
        'missing_user_id': missing_user_id,
        'isolation_complete': len(missing_user_id) == 0
    }
    
    return results


def verify_indexes(cursor) -> dict:
    """Verify performance indexes are created"""
    results = {}
    
    cursor.execute("""
        SELECT tablename, indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)
    
    indexes = cursor.fetchall()
    index_count = len(indexes)
    
    # Check for key indexes
    key_indexes = [
        'idx_projects_user_id', 'idx_tasks_user_id', 'idx_tasks_user_status',
        'idx_project_git_branchs_user_project', 'idx_subtasks_user_task'
    ]
    
    existing_index_names = [idx[1] for idx in indexes]
    missing_key_indexes = [idx for idx in key_indexes if idx not in existing_index_names]
    
    results['indexes'] = {
        'total_count': index_count,
        'missing_key_indexes': missing_key_indexes,
        'key_indexes_complete': len(missing_key_indexes) == 0
    }
    
    return results


def verify_foreign_keys(cursor) -> dict:
    """Verify foreign key constraints are properly set"""
    results = {}
    
    cursor.execute("""
        SELECT conname, conrelid::regclass AS table_name, 
               confrelid::regclass AS referenced_table
        FROM pg_constraint 
        WHERE contype = 'f' AND connamespace = 'public'::regnamespace
        ORDER BY conname
    """)
    
    foreign_keys = cursor.fetchall()
    
    # Check for key foreign keys
    expected_fks = [
        'fk_tasks_user', 'fk_projects_user', 'fk_project_git_branchs_user',
        'fk_tasks_git_branch', 'fk_subtasks_task', 'fk_subtasks_user'
    ]
    
    existing_fk_names = [fk[0] for fk in foreign_keys]
    missing_fks = [fk for fk in expected_fks if fk not in existing_fk_names]
    
    results['foreign_keys'] = {
        'total_count': len(foreign_keys),
        'missing_key_fks': missing_fks,
        'key_fks_complete': len(missing_fks) == 0
    }
    
    return results


def verify_functions(cursor) -> dict:
    """Verify utility functions are created"""
    results = {}
    
    cursor.execute("""
        SELECT routine_name FROM information_schema.routines
        WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
        ORDER BY routine_name
    """)
    
    functions = [row[0] for row in cursor.fetchall()]
    
    expected_functions = ['get_user_task_count', 'create_default_user_project']
    missing_functions = [f for f in expected_functions if f not in functions]
    
    results['functions'] = {
        'total_count': len(functions),
        'expected_functions': expected_functions,
        'missing_functions': missing_functions,
        'functions_complete': len(missing_functions) == 0
    }
    
    return results


def verify_rls_policies(cursor) -> dict:
    """Verify Row Level Security policies (Supabase)"""
    results = {}
    
    try:
        cursor.execute("""
            SELECT schemaname, tablename, policyname, permissive
            FROM pg_policies 
            WHERE schemaname = 'public'
            ORDER BY tablename, policyname
        """)
        
        policies = cursor.fetchall()
        
        # Check if RLS is enabled on key tables
        cursor.execute("""
            SELECT tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('projects', 'tasks', 'subtasks')
        """)
        
        rls_status = cursor.fetchall()
        
        results['rls'] = {
            'policies_count': len(policies),
            'rls_enabled_tables': [t[0] for t in rls_status if t[1]],
            'rls_available': len(policies) > 0 or len([t for t in rls_status if t[1]]) > 0
        }
        
    except Exception as e:
        # RLS might not be available (non-Supabase)
        results['rls'] = {
            'policies_count': 0,
            'rls_enabled_tables': [],
            'rls_available': False,
            'note': 'RLS not available or not configured'
        }
    
    return results


def test_basic_operations(cursor, detailed=False) -> dict:
    """Test basic database operations"""
    results = {}
    test_data = {}
    
    if not detailed:
        results['basic_operations'] = {'note': 'Skipped - use --detailed flag'}
        return results
    
    try:
        # Test system user operations (if it exists)
        system_user_id = '00000000-0000-0000-0000-000000000000'
        
        # Create test project
        project_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO projects (id, user_id, name, description) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (project_id, system_user_id, 'Test Project', 'Verification test project'))
        
        test_data['project_id'] = project_id
        
        # Create test branch
        branch_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO project_git_branchs (id, project_id, user_id, name, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (branch_id, project_id, system_user_id, 'test-branch', 'Test branch'))
        
        test_data['branch_id'] = branch_id
        
        # Create test task
        task_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO tasks (id, git_branch_id, user_id, title, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (task_id, branch_id, system_user_id, 'Test Task', 'Verification test task'))
        
        test_data['task_id'] = task_id
        
        # Create test contexts
        cursor.execute("""
            INSERT INTO global_contexts (user_id, context_data)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (system_user_id, json.dumps({'test': 'verification'})))
        
        cursor.execute("""
            INSERT INTO project_contexts (project_id, user_id, context_data)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING  
        """, (project_id, system_user_id, json.dumps({'test': 'project_context'})))
        
        # Test queries
        cursor.execute("SELECT COUNT(*) FROM projects WHERE user_id = %s", (system_user_id,))
        project_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (system_user_id,))
        task_count = cursor.fetchone()[0]
        
        # Test function
        cursor.execute("SELECT get_user_task_count(%s)", (system_user_id,))
        function_result = cursor.fetchone()[0]
        
        results['basic_operations'] = {
            'project_created': True,
            'branch_created': True, 
            'task_created': True,
            'contexts_created': True,
            'project_count': project_count,
            'task_count': task_count,
            'function_test': function_result == task_count,
            'test_data': test_data,
            'success': True
        }
        
    except Exception as e:
        results['basic_operations'] = {
            'success': False,
            'error': str(e),
            'test_data': test_data
        }
    
    return results


def cleanup_test_data(cursor, test_data: dict):
    """Clean up test data created during verification"""
    if not test_data:
        return
    
    try:
        system_user_id = '00000000-0000-0000-0000-000000000000'
        
        if 'project_id' in test_data:
            cursor.execute("DELETE FROM projects WHERE id = %s", (test_data['project_id'],))
            
        cursor.execute("DELETE FROM global_contexts WHERE user_id = %s AND context_data->>'test' = 'verification'", (system_user_id,))
        
        print("🧹 Cleaned up test data")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up all test data: {e}")


def print_verification_results(results: dict):
    """Print formatted verification results"""
    print("\n" + "="*60)
    print("🔍 DATABASE VERIFICATION RESULTS")
    print("="*60)
    
    # Schema verification
    schema = results.get('schema', {})
    tables = schema.get('tables', {})
    
    if tables.get('missing'):
        print(f"❌ Missing tables: {', '.join(tables['missing'])}")
    else:
        print(f"✅ All required tables present ({tables.get('found', 0)} tables)")
    
    # User isolation
    isolation = results.get('user_isolation', {})
    if isolation.get('isolation_complete'):
        print("✅ User isolation properly implemented")
    else:
        print(f"❌ User isolation incomplete - missing user_id: {', '.join(isolation.get('missing_user_id', []))}")
    
    # Indexes
    indexes = results.get('indexes', {})
    if indexes.get('key_indexes_complete'):
        print(f"✅ Key performance indexes created ({indexes.get('total_count', 0)} total)")
    else:
        print(f"⚠️  Missing key indexes: {', '.join(indexes.get('missing_key_indexes', []))}")
    
    # Foreign keys  
    fks = results.get('foreign_keys', {})
    if fks.get('key_fks_complete'):
        print(f"✅ Foreign key constraints properly set ({fks.get('total_count', 0)} total)")
    else:
        print(f"❌ Missing key foreign keys: {', '.join(fks.get('missing_key_fks', []))}")
    
    # Functions
    functions = results.get('functions', {})
    if functions.get('functions_complete'):
        print(f"✅ Utility functions created ({functions.get('total_count', 0)} total)")
    else:
        print(f"⚠️  Missing functions: {', '.join(functions.get('missing_functions', []))}")
    
    # RLS
    rls = results.get('rls', {})
    if rls.get('rls_available'):
        print(f"✅ Row Level Security configured ({rls.get('policies_count', 0)} policies)")
    else:
        print("⚠️  Row Level Security not configured (normal for local dev)")
    
    # Basic operations
    ops = results.get('basic_operations', {})
    if ops.get('success'):
        print("✅ Basic database operations working")
        print(f"   - Projects: {ops.get('project_count', 0)}")
        print(f"   - Tasks: {ops.get('task_count', 0)}")  
        print(f"   - Functions: {'✅' if ops.get('function_test') else '❌'}")
    elif 'note' in ops:
        print(f"⏭️  Basic operations: {ops['note']}")
    else:
        print(f"❌ Basic operations failed: {ops.get('error', 'Unknown error')}")
    
    # Overall status
    print("\n" + "="*60)
    
    critical_checks = [
        tables.get('missing') == [],
        isolation.get('isolation_complete'),
        fks.get('key_fks_complete')
    ]
    
    if all(critical_checks):
        print("🎉 DATABASE VERIFICATION PASSED")
        print("✅ Database is ready for development and MCP tools")
    else:
        print("⚠️  DATABASE VERIFICATION FAILED")
        print("❌ Critical issues found - database may not work properly")
    
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Verify database setup")
    parser.add_argument("--supabase", action="store_true", help="Verify Supabase database")
    parser.add_argument("--local", action="store_true", help="Verify local database")
    parser.add_argument("--detailed", action="store_true", help="Run detailed verification with sample data")
    
    args = parser.parse_args()
    
    # Determine database URL
    if args.supabase:
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            print("❌ SUPABASE_DB_URL environment variable not set")
            sys.exit(1)
    elif args.local:
        db_url = os.getenv("LOCAL_DB_URL", "postgresql://postgres:postgres@localhost:5432/4genthub")
    else:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL environment variable not set")
            print("Use --supabase or --local flag, or set DATABASE_URL")
            sys.exit(1)
    
    # Parse database configuration
    try:
        db_config = parse_database_url(db_url)
    except Exception as e:
        print(f"❌ Invalid database URL: {e}")
        sys.exit(1)
    
    print(f"🔍 Verifying database: {db_config['host']}/{db_config['database']}")
    
    # Run verification
    all_results = {}
    test_data = {}
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Run all verifications
            all_results.update(verify_basic_schema(cursor))
            all_results.update(verify_user_isolation(cursor))
            all_results.update(verify_indexes(cursor))
            all_results.update(verify_foreign_keys(cursor))
            all_results.update(verify_functions(cursor))
            all_results.update(verify_rls_policies(cursor))
            
            # Test basic operations if detailed
            ops_results = test_basic_operations(cursor, args.detailed)
            all_results.update(ops_results)
            
            if args.detailed and 'basic_operations' in ops_results:
                test_data = ops_results['basic_operations'].get('test_data', {})
        
        # Print results
        print_verification_results(all_results)
        
        # Cleanup test data if created
        if test_data:
            with conn.cursor() as cursor:
                cleanup_test_data(cursor, test_data)
        
    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()