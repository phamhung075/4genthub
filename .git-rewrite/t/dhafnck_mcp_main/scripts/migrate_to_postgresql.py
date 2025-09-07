#!/usr/bin/env python3
"""
Migration script to PostgreSQL

This migration script helps transition legacy databases to 
PostgreSQL, which is the primary database system.

PostgreSQL provides superior performance, concurrent access, data integrity,
and production reliability.
"""

import os
import sys
import sqlite3
import psycopg2
import json
from typing import Dict, Any, List
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter


class DatabaseMigrator:
    """Migrate data from SQLite to PostgreSQL."""
    
    def __init__(self, sqlite_path: str, postgresql_url: str):
        self.sqlite_path = sqlite_path
        self.postgresql_url = postgresql_url
        
    def migrate(self):
        """Perform the migration."""
        print(f"Starting migration from {self.sqlite_path} to PostgreSQL...")
        
        # Connect to both databases
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        pg_conn = psycopg2.connect(self.postgresql_url)
        pg_conn.autocommit = True
        
        try:
            # Migrate tables in dependency order
            self._migrate_projects(sqlite_conn, pg_conn)
            self._migrate_project_git_branchs(sqlite_conn, pg_conn)
            self._migrate_tasks(sqlite_conn, pg_conn)
            self._migrate_global_contexts(sqlite_conn, pg_conn)
            self._migrate_project_contexts(sqlite_conn, pg_conn)
            self._migrate_task_contexts(sqlite_conn, pg_conn)
            
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            raise
        finally:
            sqlite_conn.close()
            pg_conn.close()
    
    def _migrate_projects(self, sqlite_conn, pg_conn):
        """Migrate projects table."""
        print("Migrating projects...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM projects")
        rows = cursor.fetchall()
        
        if not rows:
            print("No projects to migrate.")
            return
        
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            # Convert SQLite row to dict
            project = dict(row)
            
            # Parse JSON metadata
            metadata = json.loads(project.get('metadata', '{}'))
            
            pg_cursor.execute("""
                INSERT INTO projects (id, name, description, created_at, updated_at, user_id, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                project['id'],
                project['name'],
                project['description'],
                project['created_at'],
                project['updated_at'],
                project['user_id'],
                project['status'],
                json.dumps(metadata)
            ))
        
        print(f"Migrated {len(rows)} projects.")
    
    def _migrate_project_git_branchs(self, sqlite_conn, pg_conn):
        """Migrate project_git_branchs table."""
        print("Migrating project task trees...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM project_git_branchs")
        rows = cursor.fetchall()
        
        if not rows:
            print("No project task trees to migrate.")
            return
        
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            tree = dict(row)
            metadata = json.loads(tree.get('metadata', '{}'))
            
            pg_cursor.execute("""
                INSERT INTO project_git_branchs (
                    id, project_id, name, description, created_at, updated_at,
                    assigned_agent_id, priority, status, metadata, task_count, completed_task_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                tree['id'],
                tree['project_id'],
                tree['name'],
                tree['description'],
                tree['created_at'],
                tree['updated_at'],
                tree['assigned_agent_id'],
                tree['priority'],
                tree['status'],
                json.dumps(metadata),
                tree['task_count'],
                tree['completed_task_count']
            ))
        
        print(f"Migrated {len(rows)} project task trees.")
    
    def _migrate_tasks(self, sqlite_conn, pg_conn):
        """Migrate tasks table."""
        print("Migrating tasks...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()
        
        if not rows:
            print("No tasks to migrate.")
            return
        
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            task = dict(row)
            
            pg_cursor.execute("""
                INSERT INTO tasks (
                    id, title, description, git_branch_id, status, priority,
                    details, estimated_effort, due_date, created_at, updated_at, context_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                task['id'],
                task['title'],
                task['description'],
                task['git_branch_id'],
                task['status'],
                task['priority'],
                task['details'],
                task['estimated_effort'],
                task['due_date'],
                task['created_at'],
                task['updated_at'],
                task['context_id']
            ))
        
        print(f"Migrated {len(rows)} tasks.")
    
    def _migrate_global_contexts(self, sqlite_conn, pg_conn):
        """Migrate global_contexts table."""
        print("Migrating global contexts...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM global_contexts")
        rows = cursor.fetchall()
        
        if not rows:
            print("No global contexts to migrate.")
            return
        
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            context = dict(row)
            
            # Parse JSON fields
            autonomous_rules = json.loads(context.get('autonomous_rules', '{}'))
            security_policies = json.loads(context.get('security_policies', '{}'))
            coding_standards = json.loads(context.get('coding_standards', '{}'))
            workflow_templates = json.loads(context.get('workflow_templates', '{}'))
            delegation_rules = json.loads(context.get('delegation_rules', '{}'))
            
            pg_cursor.execute("""
                INSERT INTO global_contexts (
                    id, organization_id, autonomous_rules, security_policies,
                    coding_standards, workflow_templates, delegation_rules,
                    created_at, updated_at, version, last_propagated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                context['id'],
                context['organization_id'],
                json.dumps(autonomous_rules),
                json.dumps(security_policies),
                json.dumps(coding_standards),
                json.dumps(workflow_templates),
                json.dumps(delegation_rules),
                context['created_at'],
                context['updated_at'],
                context['version'],
                context['last_propagated']
            ))
        
        print(f"Migrated {len(rows)} global contexts.")
    
    def _migrate_project_contexts(self, sqlite_conn, pg_conn):
        """Migrate project_contexts table."""
        print("Migrating project contexts...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM project_contexts")
        rows = cursor.fetchall()
        
        if not rows:
            print("No project contexts to migrate.")
            return
        
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            context = dict(row)
            
            # Parse JSON fields
            team_preferences = json.loads(context.get('team_preferences', '{}'))
            technology_stack = json.loads(context.get('technology_stack', '{}'))
            project_workflow = json.loads(context.get('project_workflow', '{}'))
            local_standards = json.loads(context.get('local_standards', '{}'))
            global_overrides = json.loads(context.get('global_overrides', '{}'))
            delegation_rules = json.loads(context.get('delegation_rules', '{}'))
            
            pg_cursor.execute("""
                INSERT INTO project_contexts (
                    project_id, parent_global_id, team_preferences, technology_stack,
                    project_workflow, local_standards, global_overrides, delegation_rules,
                    created_at, updated_at, version, last_inherited, inheritance_disabled
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id) DO NOTHING
            """, (
                context['project_id'],
                context['parent_global_id'],
                json.dumps(team_preferences),
                json.dumps(technology_stack),
                json.dumps(project_workflow),
                json.dumps(local_standards),
                json.dumps(global_overrides),
                json.dumps(delegation_rules),
                context['created_at'],
                context['updated_at'],
                context['version'],
                context['last_inherited'],
                context['inheritance_disabled']
            ))
        
        print(f"Migrated {len(rows)} project contexts.")
    
    def _migrate_task_contexts(self, sqlite_conn, pg_conn):
        """Migrate task_contexts table."""
        print("Migrating task contexts...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM task_contexts")
        rows = cursor.fetchall()
        
        if not rows:
            print("No task contexts to migrate.")
            return
        
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            context = dict(row)
            
            # Parse JSON fields
            task_data = json.loads(context.get('task_data', '{}'))
            local_overrides = json.loads(context.get('local_overrides', '{}'))
            implementation_notes = json.loads(context.get('implementation_notes', '{}'))
            delegation_triggers = json.loads(context.get('delegation_triggers', '{}'))
            custom_inheritance_rules = json.loads(context.get('custom_inheritance_rules', '{}'))
            resolved_context = json.loads(context.get('resolved_context', 'null'))
            
            pg_cursor.execute("""
                INSERT INTO task_contexts (
                    task_id, parent_project_id, parent_project_context_id, task_data,
                    local_overrides, implementation_notes, delegation_triggers,
                    inheritance_disabled, force_local_only, custom_inheritance_rules,
                    resolved_context, resolved_at, dependencies_hash,
                    created_at, updated_at, version, last_inherited
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO NOTHING
            """, (
                context['task_id'],
                context['parent_project_id'],
                context['parent_project_context_id'],
                json.dumps(task_data),
                json.dumps(local_overrides),
                json.dumps(implementation_notes),
                json.dumps(delegation_triggers),
                context['inheritance_disabled'],
                context['force_local_only'],
                json.dumps(custom_inheritance_rules),
                json.dumps(resolved_context) if resolved_context else None,
                context['resolved_at'],
                context['dependencies_hash'],
                context['created_at'],
                context['updated_at'],
                context['version'],
                context['last_inherited']
            ))
        
        print(f"Migrated {len(rows)} task contexts.")


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate SQLite database to PostgreSQL')
    parser.add_argument('--sqlite-path', default='./dhafnck_mcp.db', help='Path to SQLite database')
    parser.add_argument('--postgresql-url', required=True, help='PostgreSQL connection URL')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.sqlite_path):
        print(f"SQLite database not found: {args.sqlite_path}")
        sys.exit(1)
    
    migrator = DatabaseMigrator(args.sqlite_path, args.postgresql_url)
    migrator.migrate()


if __name__ == "__main__":
    main()