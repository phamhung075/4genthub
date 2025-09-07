#!/usr/bin/env python3
"""
Manually create missing database tables with correct UUID types
"""

import os
import sys
from pathlib import Path

# Set up environment for PostgreSQL
os.environ['DATABASE_TYPE'] = 'postgresql'
os.environ['DATABASE_URL'] = 'postgresql://dhafnck_user:dhafnck_password@localhost:5432/dhafnck_mcp'

# Add the project to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.database.database_config import get_db_config
from sqlalchemy import text

def create_tables_manually():
    """Create missing database tables with correct types"""
    print("🔧 Creating missing database tables manually...")
    
    try:
        # Get database configuration
        db = get_db_config()
        print("✅ Database connection established")
        
        with db.get_session() as session:
            # Create project_git_branchs table
            print("📋 Creating project_git_branchs table...")
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS project_git_branchs (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    git_branch_name TEXT NOT NULL,
                    git_branch_description TEXT DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    assigned_agent_id TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'todo',
                    metadata JSONB DEFAULT '{}',
                    task_count INTEGER DEFAULT 0,
                    completed_task_count INTEGER DEFAULT 0,
                    UNIQUE(id, project_id)
                );
            """))
            
            # Create indexes for project_git_branchs
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_project_git_branchs_project_id ON project_git_branchs(project_id);
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_project_git_branchs_status ON project_git_branchs(status);
            """))
            
            print("✅ project_git_branchs table created")
            
            # Create task_subtasks table  
            print("📋 Creating task_subtasks table...")
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS task_subtasks (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'todo',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    assignees JSONB DEFAULT '[]',
                    estimated_effort TEXT,
                    progress_percentage INTEGER DEFAULT 0,
                    progress_notes TEXT DEFAULT '',
                    blockers TEXT DEFAULT '',
                    completion_summary TEXT DEFAULT '',
                    impact_on_parent TEXT DEFAULT '',
                    insights_found JSONB DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    completed_at TIMESTAMP WITH TIME ZONE
                );
            """))
            
            # Create indexes for task_subtasks
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_subtasks_task_id ON task_subtasks(task_id);
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_subtasks_status ON task_subtasks(status);
            """))
            
            print("✅ task_subtasks table created")
            
            # Create other missing tables that might be needed
            print("📋 Creating additional tables...")
            
            # task_assignees table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS task_assignees (
                    id SERIAL PRIMARY KEY,
                    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    assignee_id TEXT NOT NULL,
                    role TEXT DEFAULT 'contributor',
                    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(task_id, assignee_id)
                );
            """))
            
            # task_dependencies table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    id SERIAL PRIMARY KEY,
                    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    depends_on_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    dependency_type TEXT DEFAULT 'blocks',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(task_id, depends_on_task_id),
                    CHECK(task_id != depends_on_task_id)
                );
            """))
            
            # task_labels table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS task_labels (
                    id SERIAL PRIMARY KEY,
                    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    label_name TEXT NOT NULL,
                    label_color TEXT DEFAULT '#gray',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(task_id, label_name)
                );
            """))
            
            # agents table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    capabilities JSONB DEFAULT '[]',
                    status TEXT DEFAULT 'available',
                    availability_score FLOAT DEFAULT 1.0,
                    last_active_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
            """))
            
            # labels table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS labels (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    color TEXT DEFAULT '#gray',
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            
            # Commit all changes
            session.commit()
            print("✅ All tables created and committed")
            
            # Verify tables were created
            result = session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
            all_tables = [row[0] for row in result.fetchall()]
            print(f"📋 Total tables now: {len(all_tables)}")
            print(f"📋 All tables: {all_tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Manual Database Schema Creation Tool")
    print("=" * 60)
    
    success = create_tables_manually()
    
    if success:
        print("\n🎉 SUCCESS: All database tables are now available!")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: Could not create all required tables")
        sys.exit(1)