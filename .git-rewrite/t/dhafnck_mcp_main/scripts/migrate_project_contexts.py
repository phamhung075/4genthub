#!/usr/bin/env python3
"""
Project Context Migration Script

This script finds all projects in the database that lack context records
and creates the necessary contexts to make them visible in the frontend.

Usage:
    python migrate_project_contexts.py [--dry-run] [--user-id USER_ID]
    
Features:
- Queries all projects from database
- Checks which ones lack contexts
- Creates contexts for projects missing them
- Handles global context requirement
- Reports success/failure for each migration
- Runnable both inside Docker and locally
- Support for user-specific migrations

The script creates a 4-tier context hierarchy:
GLOBAL → PROJECT → BRANCH → TASK
"""

import asyncio
import logging
import os
import sys
import argparse
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

# Add the src directory to Python path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    # Import required modules
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
    from fastmcp.task_management.infrastructure.database.models import (
        Project, ProjectContext, GlobalContext, BranchContext, TaskContext, 
        ProjectGitBranch, Task, GLOBAL_SINGLETON_UUID
    )
    from fastmcp.task_management.infrastructure.repositories.project_repository_factory import (
        GlobalRepositoryManager
    )
    from fastmcp.task_management.infrastructure.repositories.context_repository_factory import (
        ContextRepositoryFactory
    )
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migrate_project_contexts.log')
    ]
)
logger = logging.getLogger(__name__)


class ProjectContextMigrator:
    """Main migration class for project contexts"""
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize migrator with optional user scoping"""
        self.user_id = user_id or "migration-script"  # Default user for migration
        self.db_config = DatabaseConfig.get_instance()
        self.session = None
        self.context_factory = ContextRepositoryFactory()
        self.migration_stats = {
            'projects_processed': 0,
            'projects_with_contexts': 0,
            'projects_migrated': 0,
            'global_contexts_created': 0,
            'project_contexts_created': 0,
            'branch_contexts_created': 0,
            'task_contexts_created': 0,
            'errors': []
        }
        
    def _get_database_session(self):
        """Get database session"""
        if not self.session:
            self.db_config.initialize()
            Session = sessionmaker(bind=self.db_config.engine)
            self.session = Session()
        return self.session
        
    def close_session(self):
        """Close database session"""
        if self.session:
            self.session.close()
            self.session = None
            
    async def ensure_global_context_exists(self) -> bool:
        """Ensure global context exists for the user (user-scoped, not singleton)"""
        try:
            session = self._get_database_session()
            
            # Check if global context exists for this user (user-scoped)
            # Each user should have exactly ONE global context
            existing_global = session.query(GlobalContext).filter(
                GlobalContext.user_id == self.user_id
            ).first()
            
            if existing_global:
                logger.info(f"Global context already exists for user {self.user_id} with ID: {existing_global.id}")
                return True
                
            # Create user-scoped global context with unique ID
            global_context_id = str(uuid.uuid4())  # Unique ID per user, not singleton
            global_context = GlobalContext(
                id=global_context_id,
                organization_id="default",
                user_id=self.user_id,
                autonomous_rules={
                    "created_by": "migration-script",
                    "migration_date": datetime.utcnow().isoformat(),
                    "purpose": f"User-scoped global context for user {self.user_id}"
                },
                security_policies={},
                coding_standards={},
                workflow_templates={},
                delegation_rules={}
            )
            
            session.add(global_context)
            session.commit()
            
            self.migration_stats['global_contexts_created'] += 1
            logger.info(f"✅ Created user-scoped global context for user {self.user_id} with ID: {global_context_id}")
            return True
            
        except Exception as e:
            session.rollback() if session else None
            error_msg = f"Failed to create global context: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return False
            
    async def get_projects_without_contexts(self) -> List[Project]:
        """Get all projects that lack context records"""
        try:
            session = self._get_database_session()
            
            # Query projects with optional user filtering
            query = session.query(Project)
            if self.user_id != "migration-script":
                query = query.filter(Project.user_id == self.user_id)
                
            projects = query.all()
            
            # Check which projects lack project contexts
            projects_without_contexts = []
            for project in projects:
                has_context = session.query(ProjectContext).filter(
                    ProjectContext.project_id == project.id,
                    ProjectContext.user_id == project.user_id
                ).first() is not None
                
                if not has_context:
                    projects_without_contexts.append(project)
                    
            logger.info(f"Found {len(projects_without_contexts)} projects without contexts out of {len(projects)} total")
            return projects_without_contexts
            
        except Exception as e:
            error_msg = f"Failed to query projects: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return []
            
    async def create_project_context(self, project: Project) -> bool:
        """Create project context for a project"""
        try:
            session = self._get_database_session()
            
            # Get the user's global context (not singleton)
            user_global_context = session.query(GlobalContext).filter(
                GlobalContext.user_id == project.user_id
            ).first()
            
            if not user_global_context:
                logger.error(f"No global context found for user {project.user_id}")
                return False
            
            # Create project context linked to user's global context
            project_context = ProjectContext(
                id=str(uuid.uuid4()),
                project_id=project.id,
                parent_global_id=user_global_context.id,  # Use user's global context ID
                user_id=project.user_id,
                data={
                    "project_name": project.name,
                    "project_description": project.description,
                    "project_status": project.status,
                    "created_by": "migration-script",
                    "migration_date": datetime.utcnow().isoformat()
                },
                team_preferences={},
                technology_stack={},
                project_workflow={},
                local_standards={},
                global_overrides={},
                delegation_rules={}
            )
            
            session.add(project_context)
            session.commit()
            
            self.migration_stats['project_contexts_created'] += 1
            logger.info(f"✅ Created project context for project '{project.name}' ({project.id}) linked to user global context {user_global_context.id}")
            return True
            
        except Exception as e:
            session.rollback() if session else None
            error_msg = f"Failed to create project context for {project.name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return False
            
    async def create_branch_contexts(self, project: Project) -> int:
        """Create branch contexts for all branches in a project"""
        try:
            session = self._get_database_session()
            contexts_created = 0
            
            # Get project context
            project_context = session.query(ProjectContext).filter(
                ProjectContext.project_id == project.id,
                ProjectContext.user_id == project.user_id
            ).first()
            
            if not project_context:
                logger.warning(f"No project context found for project {project.name}")
                return 0
                
            # Get all branches for this project
            branches = session.query(ProjectGitBranch).filter(
                ProjectGitBranch.project_id == project.id
            ).all()
            
            for branch in branches:
                # Check if branch context already exists
                existing_context = session.query(BranchContext).filter(
                    BranchContext.branch_id == branch.id,
                    BranchContext.user_id == branch.user_id
                ).first()
                
                if existing_context:
                    continue  # Skip if context already exists
                    
                # Create branch context
                branch_context = BranchContext(
                    id=str(uuid.uuid4()),
                    branch_id=branch.id,
                    parent_project_id=project_context.id,
                    user_id=branch.user_id,
                    data={
                        "branch_name": branch.name,
                        "branch_description": branch.description,
                        "branch_status": branch.status,
                        "project_id": project.id,
                        "created_by": "migration-script",
                        "migration_date": datetime.utcnow().isoformat()
                    },
                    branch_workflow={},
                    feature_flags={},
                    active_patterns={},
                    local_overrides={},
                    delegation_rules={}
                )
                
                session.add(branch_context)
                contexts_created += 1
                
            if contexts_created > 0:
                session.commit()
                self.migration_stats['branch_contexts_created'] += contexts_created
                logger.info(f"✅ Created {contexts_created} branch contexts for project '{project.name}'")
                
            return contexts_created
            
        except Exception as e:
            session.rollback() if session else None
            error_msg = f"Failed to create branch contexts for {project.name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return 0
            
    async def create_task_contexts(self, project: Project) -> int:
        """Create task contexts for all tasks in a project"""
        try:
            session = self._get_database_session()
            contexts_created = 0
            
            # Get all branches for this project
            branches = session.query(ProjectGitBranch).filter(
                ProjectGitBranch.project_id == project.id
            ).all()
            
            for branch in branches:
                # Get branch context
                branch_context = session.query(BranchContext).filter(
                    BranchContext.branch_id == branch.id,
                    BranchContext.user_id == branch.user_id
                ).first()
                
                if not branch_context:
                    continue  # Skip if no branch context
                    
                # Get all tasks for this branch
                tasks = session.query(Task).filter(
                    Task.git_branch_id == branch.id
                ).all()
                
                for task in tasks:
                    # Check if task context already exists
                    existing_context = session.query(TaskContext).filter(
                        TaskContext.task_id == task.id,
                        TaskContext.user_id == task.user_id
                    ).first()
                    
                    if existing_context:
                        continue  # Skip if context already exists
                        
                    # Create task context
                    task_context = TaskContext(
                        id=str(uuid.uuid4()),
                        task_id=task.id,
                        parent_branch_id=branch.id,
                        parent_branch_context_id=branch_context.id,
                        user_id=task.user_id,
                        data={
                            "task_title": task.title,
                            "task_description": task.description,
                            "task_status": task.status,
                            "task_priority": task.priority,
                            "branch_id": branch.id,
                            "project_id": project.id,
                            "created_by": "migration-script",
                            "migration_date": datetime.utcnow().isoformat()
                        },
                        task_data={
                            "title": task.title,
                            "status": task.status,
                            "description": task.description
                        },
                        execution_context={},
                        discovered_patterns={},
                        local_decisions={},
                        delegation_queue={},
                        local_overrides={},
                        implementation_notes={},
                        delegation_triggers={}
                    )
                    
                    session.add(task_context)
                    contexts_created += 1
                    
            if contexts_created > 0:
                session.commit()
                self.migration_stats['task_contexts_created'] += contexts_created
                logger.info(f"✅ Created {contexts_created} task contexts for project '{project.name}'")
                
            return contexts_created
            
        except Exception as e:
            session.rollback() if session else None
            error_msg = f"Failed to create task contexts for {project.name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return 0
            
    async def migrate_project(self, project: Project, dry_run: bool = False) -> bool:
        """Migrate a single project to have full context hierarchy"""
        try:
            self.migration_stats['projects_processed'] += 1
            
            if dry_run:
                logger.info(f"🔍 DRY RUN: Would migrate project '{project.name}' ({project.id})")
                return True
                
            logger.info(f"🔄 Migrating project '{project.name}' ({project.id})")
            
            # Create project context
            if not await self.create_project_context(project):
                return False
                
            # Create branch contexts
            branch_count = await self.create_branch_contexts(project)
            
            # Create task contexts
            task_count = await self.create_task_contexts(project)
            
            self.migration_stats['projects_migrated'] += 1
            logger.info(
                f"✅ Successfully migrated project '{project.name}' "
                f"(branches: {branch_count}, tasks: {task_count})"
            )
            return True
            
        except Exception as e:
            error_msg = f"Failed to migrate project {project.name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return False
            
    async def run_migration(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run the complete migration process"""
        try:
            logger.info(f"🚀 Starting project context migration {'(DRY RUN)' if dry_run else ''}")
            logger.info(f"User scope: {self.user_id}")
            
            # Ensure global context exists
            if not dry_run:
                if not await self.ensure_global_context_exists():
                    return {
                        'success': False,
                        'error': 'Failed to ensure global context exists',
                        'stats': self.migration_stats
                    }
            
            # Get projects without contexts
            projects_to_migrate = await self.get_projects_without_contexts()
            
            if not projects_to_migrate:
                logger.info("✅ All projects already have contexts")
                return {
                    'success': True,
                    'message': 'All projects already have contexts',
                    'stats': self.migration_stats
                }
            
            # Migrate each project
            success_count = 0
            for project in projects_to_migrate:
                if await self.migrate_project(project, dry_run):
                    success_count += 1
                    
            # Final report
            total_projects = len(projects_to_migrate)
            logger.info(f"📊 Migration completed: {success_count}/{total_projects} projects migrated")
            
            return {
                'success': success_count == total_projects,
                'projects_migrated': success_count,
                'total_projects': total_projects,
                'stats': self.migration_stats
            }
            
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'stats': self.migration_stats
            }
        finally:
            self.close_session()
            
    def print_final_report(self, result: Dict[str, Any]):
        """Print final migration report"""
        print("\n" + "="*60)
        print("PROJECT CONTEXT MIGRATION REPORT")
        print("="*60)
        
        stats = result.get('stats', {})
        
        print(f"📊 Projects processed: {stats.get('projects_processed', 0)}")
        print(f"✅ Projects migrated: {stats.get('projects_migrated', 0)}")
        print(f"🌍 Global contexts created: {stats.get('global_contexts_created', 0)}")
        print(f"📁 Project contexts created: {stats.get('project_contexts_created', 0)}")
        print(f"🌿 Branch contexts created: {stats.get('branch_contexts_created', 0)}")
        print(f"📝 Task contexts created: {stats.get('task_contexts_created', 0)}")
        
        if stats.get('errors'):
            print(f"❌ Errors: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(stats['errors']) > 5:
                print(f"   ... and {len(stats['errors']) - 5} more errors")
        else:
            print("❌ Errors: 0")
            
        print("\n" + "="*60)
        
        if result.get('success'):
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        else:
            print("❌ MIGRATION COMPLETED WITH ERRORS")
            
        print("="*60)


async def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(description='Migrate project contexts for frontend visibility')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')
    parser.add_argument('--user-id', type=str, help='Migrate contexts for specific user only')
    
    args = parser.parse_args()
    
    try:
        # Create migrator
        migrator = ProjectContextMigrator(user_id=args.user_id)
        
        # Run migration
        result = await migrator.run_migration(dry_run=args.dry_run)
        
        # Print report
        migrator.print_final_report(result)
        
        # Exit with appropriate code
        sys.exit(0 if result.get('success') else 1)
        
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        print(f"❌ Script execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())