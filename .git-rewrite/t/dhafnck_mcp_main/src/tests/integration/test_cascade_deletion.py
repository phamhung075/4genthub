#!/usr/bin/env python3
"""
Test script to verify cascade deletion of related data when a project is deleted.
"""

import asyncio
import logging
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_cascade_deletion():
    """Test that deleting a project properly cascades to all related data"""
    
    # Import the MCP tools
    from src.fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    tools = DDDCompliantMCPTools()
    
    # Generate unique test project name
    test_project_name = f"test_cascade_{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating test project: {test_project_name}")
    
    try:
        # 1. Create a test project
        project_result = tools.manage_project(
            action="create",
            name=test_project_name,
            description="Test project for cascade deletion verification"
        )
        
        if not project_result.get("success"):
            logger.error(f"Failed to create project: {project_result}")
            return
        
        project_id = project_result["project"]["id"]
        logger.info(f"Created project with ID: {project_id}")
        
        # 2. Create a git branch
        branch_result = tools.manage_git_branch(
            action="create",
            project_id=project_id,
            git_branch_name="test-branch",
            git_branch_description="Test branch for cascade deletion"
        )
        
        if not branch_result.get("success"):
            logger.error(f"Failed to create branch: {branch_result}")
            return
            
        branch_id = branch_result["git_branch"]["id"]
        logger.info(f"Created branch with ID: {branch_id}")
        
        # 3. Create a task in the branch
        task_result = tools.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Test task for cascade deletion",
            description="This task should be deleted when project is deleted"
        )
        
        if not task_result.get("success"):
            logger.error(f"Failed to create task: {task_result}")
            return
            
        task_id = task_result["task"]["id"]
        logger.info(f"Created task with ID: {task_id}")
        
        # 4. Create a subtask
        subtask_result = tools.manage_subtask(
            action="create",
            task_id=task_id,
            title="Test subtask",
            description="This subtask should be deleted with the task"
        )
        
        if subtask_result.get("success"):
            subtask_id = subtask_result["subtask"]["id"]
            logger.info(f"Created subtask with ID: {subtask_id}")
        else:
            logger.warning(f"Could not create subtask: {subtask_result}")
            subtask_id = None
        
        # 5. Create contexts at different levels
        
        # Project context
        project_context_result = tools.manage_context(
            action="create",
            level="project",
            context_id=project_id,
            data={"test_data": "project context data", "created_at": datetime.now().isoformat()}
        )
        logger.info(f"Created project context: {project_context_result.get('success')}")
        
        # Branch context
        branch_context_result = tools.manage_context(
            action="create",
            level="branch",
            context_id=branch_id,
            data={"test_data": "branch context data", "created_at": datetime.now().isoformat()}
        )
        logger.info(f"Created branch context: {branch_context_result.get('success')}")
        
        # Task context
        task_context_result = tools.manage_context(
            action="create",
            level="task",
            context_id=task_id,
            data={"test_data": "task context data", "created_at": datetime.now().isoformat()}
        )
        logger.info(f"Created task context: {task_context_result.get('success')}")
        
        # 6. Verify all data exists before deletion
        logger.info("\n=== Verifying data exists before deletion ===")
        
        # Check project exists
        get_project = tools.manage_project(action="get", project_id=project_id)
        logger.info(f"Project exists: {get_project.get('success')}")
        
        # Check branch exists
        list_branches = tools.manage_git_branch(action="list", project_id=project_id)
        branch_count = len(list_branches.get("git_branchs", [])) if list_branches.get("success") else 0
        logger.info(f"Branches found: {branch_count}")
        
        # Check task exists
        list_tasks = tools.manage_task(action="list", git_branch_id=branch_id)
        task_count = len(list_tasks.get("tasks", [])) if list_tasks.get("success") else 0
        logger.info(f"Tasks found: {task_count}")
        
        # Check contexts exist
        project_ctx = tools.manage_context(action="get", level="project", context_id=project_id)
        logger.info(f"Project context exists: {project_ctx.get('success')}")
        
        branch_ctx = tools.manage_context(action="get", level="branch", context_id=branch_id)
        logger.info(f"Branch context exists: {branch_ctx.get('success')}")
        
        task_ctx = tools.manage_context(action="get", level="task", context_id=task_id)
        logger.info(f"Task context exists: {task_ctx.get('success')}")
        
        # 7. DELETE THE PROJECT (with force=True to skip safety checks)
        logger.info(f"\n=== Deleting project {project_id} ===")
        delete_result = tools.manage_project(
            action="delete",
            project_id=project_id,
            force=True  # Force deletion to test cascade
        )
        
        if not delete_result.get("success"):
            logger.error(f"Failed to delete project: {delete_result}")
            return
        
        logger.info(f"Project deleted successfully: {delete_result.get('message')}")
        if "statistics" in delete_result:
            stats = delete_result["statistics"]
            logger.info(f"Deletion statistics:")
            logger.info(f"  - Git branches deleted: {stats.get('git_branches_deleted', 0)}")
            logger.info(f"  - Tasks deleted: {stats.get('tasks_deleted', 0)}")
            logger.info(f"  - Subtasks deleted: {stats.get('subtasks_deleted', 0)}")
            logger.info(f"  - Contexts deleted: {stats.get('contexts_deleted', 0)}")
            logger.info(f"  - Errors: {stats.get('errors', [])}")
        
        # 8. Verify all data is deleted after project deletion
        logger.info("\n=== Verifying cascade deletion ===")
        
        # Check project is deleted
        get_project = tools.manage_project(action="get", project_id=project_id)
        project_deleted = not get_project.get("success") or get_project.get("error")
        logger.info(f"✓ Project deleted: {project_deleted}")
        
        # Check branch is deleted
        list_branches = tools.manage_git_branch(action="list", project_id=project_id)
        branches_deleted = not list_branches.get("success") or len(list_branches.get("git_branchs", [])) == 0
        logger.info(f"✓ Branches deleted: {branches_deleted}")
        
        # Check task is deleted
        get_task = tools.manage_task(action="get", task_id=task_id)
        task_deleted = not get_task.get("success") or get_task.get("error")
        logger.info(f"✓ Task deleted: {task_deleted}")
        
        # Check subtask is deleted
        if subtask_id:
            list_subtasks = tools.manage_subtask(action="list", task_id=task_id)
            subtasks_deleted = not list_subtasks.get("success") or len(list_subtasks.get("subtasks", [])) == 0
            logger.info(f"✓ Subtasks deleted: {subtasks_deleted}")
        
        # Check contexts are deleted
        project_ctx = tools.manage_context(action="get", level="project", context_id=project_id)
        project_ctx_deleted = not project_ctx.get("success") or project_ctx.get("error") or not project_ctx.get("context")
        logger.info(f"✓ Project context deleted: {project_ctx_deleted}")
        
        branch_ctx = tools.manage_context(action="get", level="branch", context_id=branch_id)
        branch_ctx_deleted = not branch_ctx.get("success") or branch_ctx.get("error") or not branch_ctx.get("context")
        logger.info(f"✓ Branch context deleted: {branch_ctx_deleted}")
        
        task_ctx = tools.manage_context(action="get", level="task", context_id=task_id)
        task_ctx_deleted = not task_ctx.get("success") or task_ctx.get("error") or not task_ctx.get("context")
        logger.info(f"✓ Task context deleted: {task_ctx_deleted}")
        
        # Summary
        logger.info("\n=== CASCADE DELETION TEST COMPLETE ===")
        all_deleted = all([
            project_deleted,
            branches_deleted, 
            task_deleted,
            project_ctx_deleted,
            branch_ctx_deleted,
            task_ctx_deleted
        ])
        
        if all_deleted:
            logger.info("✅ SUCCESS: All related data was properly deleted in cascade!")
        else:
            logger.error("❌ FAILURE: Some related data was not deleted properly")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        
        # Try to clean up if test failed
        try:
            logger.info("Attempting cleanup...")
            tools.manage_project(action="delete", project_id=project_id, force=True)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_cascade_deletion())