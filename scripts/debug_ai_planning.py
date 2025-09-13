#!/usr/bin/env python3
"""Debug script to understand AI planning service output"""

import sys
import os
import asyncio

# Add the src path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dhafnck_mcp_main', 'src'))

from fastmcp.ai_task_planning.application.services.ai_planning_service import AITaskPlanningService
from fastmcp.ai_task_planning.domain.entities.planning_request import (
    PlanningRequest, RequirementItem, PlanningContext, ComplexityLevel
)
from fastmcp.ai_task_planning.domain.entities.task_plan import TaskType, ExecutionPhase

async def debug_ai_planning():
    """Debug the AI planning service to see what it generates"""
    
    # Create a sample planning request similar to the test
    planning_request = PlanningRequest(
        id="req_test_001",
        title="Build User Management System",
        description="Complete user management with authentication",
        context=PlanningContext.NEW_FEATURE,
        project_id="proj_123",
        git_branch_id="branch_456",
        user_id="user_789",
        available_agents=["coding-agent", "ui-specialist-agent", "test-orchestrator-agent"]
    )
    
    # Add requirements using the same pattern as the test
    planning_request.add_requirement(
        description="Create user authentication with JWT tokens",
        priority="high",
        acceptance_criteria=[
            "Users can login with email/password",
            "JWT tokens are issued on successful login", 
            "Tokens expire after 1 hour"
        ]
    )
    
    planning_request.add_requirement(
        description="Build user profile management UI",
        priority="medium",
        acceptance_criteria=[
            "Users can view their profile",
            "Users can update profile information",
            "Profile pictures are supported"
        ]
    )
    
    planning_request.add_requirement(
        description="Comprehensive test coverage for authentication", 
        priority="high",
        acceptance_criteria=[
            "Unit tests for all auth functions",
            "Integration tests for login flow",
            "90% code coverage minimum"
        ]
    )
    
    # Create the service
    service = AITaskPlanningService()
    
    try:
        # Generate the plan
        print("🔄 Generating AI task plan...")
        plan = await service.create_intelligent_plan(planning_request)
        
        print(f"\n📋 Generated plan: {plan.title}")
        print(f"📊 Total tasks: {len(plan.tasks)}")
        print(f"⏱️ Estimated hours: {plan.total_estimated_hours}")
        print(f"🤖 Required agents: {plan.required_agents}")
        print(f"📈 Confidence: {plan.confidence_score}")
        
        print("\n🎯 Task Types Found:")
        task_types = [task.task_type for task in plan.tasks]
        for task_type in set(task_types):
            count = task_types.count(task_type)
            print(f"  - {task_type.value}: {count} tasks")
        
        print("\n⚡ Execution Phases Found:")
        phases = [task.phase for task in plan.tasks]
        for phase in set(phases):
            count = phases.count(phase)
            print(f"  - {phase.value}: {count} tasks")
        
        print("\n📝 Individual Tasks:")
        for i, task in enumerate(plan.tasks, 1):
            print(f"  {i}. {task.title}")
            print(f"     Type: {task.task_type.value}")
            print(f"     Phase: {task.phase.value}")
            print(f"     Agent: {task.agent_assignment.primary_agent if task.agent_assignment else 'UNASSIGNED'}")
            print(f"     Hours: {task.estimated_hours}")
            print()
        
        # Check what the test is expecting
        print("🔍 Test Expectations vs Reality:")
        print(f"  TaskType.TASK in types: {TaskType.TASK in task_types}")
        print(f"  TaskType.FEATURE in types: {TaskType.FEATURE in task_types}")
        print(f"  TaskType.TESTING in types: {TaskType.TESTING in task_types}")
        print(f"  ExecutionPhase.ARCHITECTURE in phases: {ExecutionPhase.ARCHITECTURE in phases}")
        print(f"  ExecutionPhase.IMPLEMENTATION in phases: {ExecutionPhase.IMPLEMENTATION in phases}")
        print(f"  ExecutionPhase.TESTING in phases: {ExecutionPhase.TESTING in phases}")
        
        # Show which assertions would fail
        print("\n❌ Test Assertion Analysis:")
        if not (TaskType.TASK in task_types or TaskType.FEATURE in task_types):
            print("  FAIL: TaskType.TASK or TaskType.FEATURE not found")
        if TaskType.TESTING not in task_types:
            print("  FAIL: TaskType.TESTING not found")
        if ExecutionPhase.ARCHITECTURE not in phases:
            print("  FAIL: ExecutionPhase.ARCHITECTURE not found")
        if ExecutionPhase.IMPLEMENTATION not in phases:
            print("  FAIL: ExecutionPhase.IMPLEMENTATION not found")
        if ExecutionPhase.TESTING not in phases:
            print("  FAIL: ExecutionPhase.TESTING not found")
            
    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_ai_planning())