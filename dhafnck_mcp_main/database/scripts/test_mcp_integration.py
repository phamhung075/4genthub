#!/usr/bin/env python3
"""
MCP Tools Integration Test
=========================

Tests that MCP tools work correctly with the new database schema after migration.
This script simulates the operations that the MCP system performs to ensure
compatibility with the fresh database structure.

Usage:
    python test_mcp_integration.py [--create-sample] [--cleanup]
    
Arguments:
    --create-sample: Create sample data for testing
    --cleanup: Clean up test data after running
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add the project source to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from fastmcp.task_management.infrastructure.repositories.project_repository import ProjectRepository
    from fastmcp.task_management.infrastructure.repositories.git_branch_repository import GitBranchRepository
    from fastmcp.task_management.infrastructure.repositories.task_repository import TaskRepository
    from fastmcp.task_management.infrastructure.repositories.context_repository import ContextRepository
    from fastmcp.task_management.infrastructure.database.db_connection import get_database_connection
    from fastmcp.task_management.domain.models.project import Project
    from fastmcp.task_management.domain.models.task import Task
    from fastmcp.task_management.domain.models.git_branch import GitBranch
    from fastmcp.utilities.uuid_generator import generate_uuid
except ImportError as e:
    print(f"❌ Cannot import MCP modules: {e}")
    print("Make sure you're running from the correct directory and the MCP system is installed")
    sys.exit(1)


class MCPIntegrationTest:
    def __init__(self):
        self.db = None
        self.project_repo = None
        self.branch_repo = None
        self.task_repo = None
        self.context_repo = None
        self.test_user_id = "00000000-0000-0000-0000-000000000000"  # System user
        self.created_items = {}

    async def setup(self):
        """Initialize database connection and repositories"""
        try:
            self.db = await get_database_connection()
            self.project_repo = ProjectRepository(self.db)
            self.branch_repo = GitBranchRepository(self.db)
            self.task_repo = TaskRepository(self.db)
            self.context_repo = ContextRepository(self.db)
            print("✅ Connected to database and initialized repositories")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    async def test_project_operations(self):
        """Test project creation, retrieval, and updates"""
        print("\n🔧 Testing Project Operations...")
        
        try:
            # Create project
            project_data = {
                'name': 'MCP Integration Test Project',
                'description': 'Test project for verifying MCP tools integration',
                'user_id': self.test_user_id
            }
            
            project = await self.project_repo.create(project_data)
            self.created_items['project'] = project
            print(f"✅ Created project: {project.name} (ID: {project.id})")
            
            # Retrieve project
            retrieved = await self.project_repo.get(project.id, self.test_user_id)
            assert retrieved.name == project.name
            print("✅ Project retrieval works")
            
            # List projects
            projects = await self.project_repo.list(self.test_user_id)
            assert len(projects) >= 1
            print(f"✅ Project listing works ({len(projects)} projects)")
            
            # Update project
            updated_project = await self.project_repo.update(
                project.id, 
                {'description': 'Updated test description'}, 
                self.test_user_id
            )
            assert 'Updated test description' in updated_project.description
            print("✅ Project update works")
            
            return True
            
        except Exception as e:
            print(f"❌ Project operations failed: {e}")
            return False

    async def test_git_branch_operations(self):
        """Test git branch (task tree) operations"""
        print("\n🌿 Testing Git Branch Operations...")
        
        if 'project' not in self.created_items:
            print("❌ No project available for branch testing")
            return False
        
        project = self.created_items['project']
        
        try:
            # Create git branch
            branch_data = {
                'project_id': project.id,
                'name': 'test-integration-branch',
                'description': 'Test branch for MCP integration',
                'user_id': self.test_user_id
            }
            
            branch = await self.branch_repo.create(branch_data)
            self.created_items['branch'] = branch
            print(f"✅ Created git branch: {branch.name} (ID: {branch.id})")
            
            # List branches for project
            branches = await self.branch_repo.list_for_project(project.id, self.test_user_id)
            assert len(branches) >= 1
            print(f"✅ Branch listing works ({len(branches)} branches)")
            
            # Get branch by ID
            retrieved_branch = await self.branch_repo.get(branch.id, self.test_user_id)
            assert retrieved_branch.name == branch.name
            print("✅ Branch retrieval works")
            
            return True
            
        except Exception as e:
            print(f"❌ Git branch operations failed: {e}")
            return False

    async def test_task_operations(self):
        """Test task creation, retrieval, and management"""
        print("\n📋 Testing Task Operations...")
        
        if 'branch' not in self.created_items:
            print("❌ No git branch available for task testing")
            return False
        
        branch = self.created_items['branch']
        
        try:
            # Create task
            task_data = {
                'title': 'MCP Integration Test Task',
                'description': 'Test task for verifying MCP task management',
                'git_branch_id': branch.id,
                'user_id': self.test_user_id,
                'status': 'todo',
                'priority': 'medium'
            }
            
            task = await self.task_repo.create(task_data)
            self.created_items['task'] = task
            print(f"✅ Created task: {task.title} (ID: {task.id})")
            
            # List tasks for branch
            tasks = await self.task_repo.list_for_branch(branch.id, self.test_user_id)
            assert len(tasks) >= 1
            print(f"✅ Task listing works ({len(tasks)} tasks)")
            
            # Update task status
            updated_task = await self.task_repo.update(
                task.id,
                {'status': 'in_progress', 'details': 'Testing MCP integration'},
                self.test_user_id
            )
            assert updated_task.status == 'in_progress'
            print("✅ Task update works")
            
            # Search tasks
            search_results = await self.task_repo.search('Integration', self.test_user_id)
            assert len(search_results) >= 1
            print("✅ Task search works")
            
            return True
            
        except Exception as e:
            print(f"❌ Task operations failed: {e}")
            return False

    async def test_context_operations(self):
        """Test hierarchical context operations"""
        print("\n🔗 Testing Context Operations...")
        
        if 'project' not in self.created_items or 'task' not in self.created_items:
            print("❌ Missing project or task for context testing")
            return False
        
        project = self.created_items['project']
        task = self.created_items['task']
        
        try:
            # Create global context
            global_context_data = {
                'level': 'global',
                'user_id': self.test_user_id,
                'context_data': {
                    'test': 'mcp_integration',
                    'created_by': 'integration_test'
                }
            }
            
            global_context = await self.context_repo.create_global_context(
                self.test_user_id, 
                global_context_data['context_data']
            )
            print("✅ Created global context")
            
            # Create project context
            project_context_data = {
                'project_type': 'integration_test',
                'test_data': 'project_context_verification'
            }
            
            project_context = await self.context_repo.create_project_context(
                project.id,
                self.test_user_id,
                project_context_data
            )
            print("✅ Created project context")
            
            # Create task context
            task_context_data = {
                'task_type': 'integration_test',
                'test_progress': 'context_testing'
            }
            
            task_context = await self.context_repo.create_task_context(
                task.id,
                self.test_user_id,
                task_context_data
            )
            print("✅ Created task context")
            
            # Test context inheritance
            resolved_context = await self.context_repo.resolve_task_context(
                task.id,
                self.test_user_id
            )
            
            # Should include data from global, project, and task levels
            assert 'test' in resolved_context  # from global
            assert 'project_type' in resolved_context  # from project
            assert 'task_type' in resolved_context  # from task
            print("✅ Context inheritance works")
            
            return True
            
        except Exception as e:
            print(f"❌ Context operations failed: {e}")
            return False

    async def test_user_isolation(self):
        """Test that user isolation works correctly"""
        print("\n🔐 Testing User Isolation...")
        
        # Use a different test user
        different_user_id = generate_uuid()
        
        try:
            # Try to access project created by system user
            try:
                project = await self.project_repo.get(
                    self.created_items['project'].id, 
                    different_user_id
                )
                print("❌ User isolation failed - accessed other user's project")
                return False
            except Exception:
                print("✅ User isolation works - cannot access other user's project")
            
            # Try to list projects as different user
            projects = await self.project_repo.list(different_user_id)
            if len(projects) == 0:
                print("✅ User isolation works - different user sees no projects")
            else:
                print("❌ User isolation failed - different user sees projects")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ User isolation test failed: {e}")
            return False

    async def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            if 'project' in self.created_items:
                # Delete project (should cascade to branches and tasks)
                await self.project_repo.delete(
                    self.created_items['project'].id,
                    self.test_user_id
                )
                print("✅ Cleaned up project and related data")
            
            # Clean up global context
            try:
                await self.context_repo.delete_global_context(self.test_user_id)
                print("✅ Cleaned up global context")
            except:
                pass  # May not exist or already cleaned
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

    async def run_all_tests(self, create_sample=False, cleanup=True):
        """Run complete MCP integration test suite"""
        print("="*60)
        print("🧪 MCP TOOLS INTEGRATION TEST")
        print("="*60)
        
        # Setup
        if not await self.setup():
            return False
        
        test_results = []
        
        try:
            # Run tests
            test_results.append(await self.test_project_operations())
            test_results.append(await self.test_git_branch_operations())
            test_results.append(await self.test_task_operations())
            test_results.append(await self.test_context_operations())
            test_results.append(await self.test_user_isolation())
            
            # Summary
            passed = sum(test_results)
            total = len(test_results)
            
            print("\n" + "="*60)
            print("📊 TEST RESULTS SUMMARY")
            print("="*60)
            print(f"Tests passed: {passed}/{total}")
            
            if passed == total:
                print("🎉 ALL MCP INTEGRATION TESTS PASSED!")
                print("✅ Database schema is compatible with MCP tools")
                print("✅ User isolation is working correctly")
                print("✅ All repository operations functional")
                success = True
            else:
                print("❌ SOME TESTS FAILED")
                print("⚠️  Database may have issues with MCP tool compatibility")
                success = False
            
        finally:
            if cleanup:
                await self.cleanup_test_data()
            
            if self.db:
                await self.db.close()
        
        return success


async def main():
    parser = argparse.ArgumentParser(description="Test MCP tools integration")
    parser.add_argument("--create-sample", action="store_true", 
                       help="Create sample data for testing")
    parser.add_argument("--no-cleanup", action="store_true", 
                       help="Skip cleanup of test data")
    
    args = parser.parse_args()
    
    test_runner = MCPIntegrationTest()
    
    success = await test_runner.run_all_tests(
        create_sample=args.create_sample,
        cleanup=not args.no_cleanup
    )
    
    if success:
        print("\n🚀 MCP integration verified - system ready for use!")
        sys.exit(0)
    else:
        print("\n❌ MCP integration test failed - check database setup")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())