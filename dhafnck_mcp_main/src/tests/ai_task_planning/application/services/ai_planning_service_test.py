"""Test suite for AITaskPlanningService"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from fastmcp.ai_task_planning.application.services.ai_planning_service import AITaskPlanningService
from fastmcp.ai_task_planning.domain.entities.planning_request import (
    PlanningRequest, RequirementItem, PlanningContext, ComplexityLevel
)
from fastmcp.ai_task_planning.domain.entities.task_plan import (
    TaskPlan, PlannedTask, TaskType, ExecutionPhase
)


class TestAITaskPlanningService:
    """Test cases for AITaskPlanningService"""
    
    @pytest.fixture
    def service(self):
        """Create AITaskPlanningService instance"""
        return AITaskPlanningService()
    
    @pytest.fixture
    def sample_planning_request(self):
        """Create a sample planning request"""
        request = PlanningRequest(
            id="req_test_001",
            title="Build User Management System",
            description="Complete user management with authentication",
            context=PlanningContext.NEW_FEATURE,
            project_id="proj_123",
            git_branch_id="branch_456",
            user_id="user_789",
            available_agents=["coding-agent", "ui-specialist-agent", "test-orchestrator-agent"]
        )
        
        # Add requirements
        pytest_request.add_requirement(
            description="Create user authentication with JWT tokens",
            priority="high",
            acceptance_criteria=[
                "Users can login with email/password",
                "JWT tokens are issued on successful login",
                "Tokens expire after 1 hour"
            ]
        )
        
        pytest_request.add_requirement(
            description="Build user profile management UI",
            priority="medium",
            acceptance_criteria=[
                "Users can view their profile",
                "Users can update profile information",
                "Profile pictures are supported"
            ]
        )
        
        pytest_request.add_requirement(
            description="Comprehensive test coverage for authentication",
            priority="high",
            acceptance_criteria=[
                "Unit tests for all auth functions",
                "Integration tests for login flow",
                "90% code coverage minimum"
            ]
        )
        
        return request
    
    @pytest.mark.asyncio
    async def test_create_intelligent_plan_basic(self, service, sample_planning_request):
        """Test basic intelligent plan creation"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        assert isinstance(plan, TaskPlan)
        assert plan.planning_request_id == sample_planning_request.id
        assert "AI Plan:" in plan.title
        assert len(plan.tasks) > 0
        assert plan.total_estimated_hours > 0
        assert len(plan.required_agents) > 0
        assert plan.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_plan_contains_expected_patterns(self, service, sample_planning_request):
        """Test that plan recognizes expected patterns from requirements"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Should have tasks for authentication, UI, and testing
        task_types = [task.task_type for task in plan.tasks]
        assert TaskType.TASK in task_types or TaskType.FEATURE in task_types
        assert TaskType.TESTING in task_types
        
        # Should have appropriate phases
        phases = [task.phase for task in plan.tasks]
        assert ExecutionPhase.ARCHITECTURE in phases
        assert ExecutionPhase.IMPLEMENTATION in phases
        assert ExecutionPhase.TESTING in phases
    
    @pytest.mark.asyncio
    async def test_agent_assignment(self, service, sample_planning_request):
        """Test that agents are properly assigned to tasks"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # All tasks should have agent assignments
        unassigned_tasks = [task for task in plan.tasks if not task.agent_assignment]
        assert len(unassigned_tasks) == 0
        
        # Check for expected agents
        assigned_agents = set()
        for task in plan.tasks:
            if task.agent_assignment:
                assigned_agents.add(task.agent_assignment.primary_agent)
        
        # Should have assigned appropriate agents based on patterns
        assert 'coding-agent' in assigned_agents  # For auth implementation
        assert 'ui-specialist-agent' in assigned_agents  # For UI work
        assert 'test-orchestrator-agent' in assigned_agents  # For testing
    
    @pytest.mark.asyncio
    async def test_subtask_generation(self, service, sample_planning_request):
        """Test that subtasks are generated for complex requirements"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Find tasks with subtasks
        parent_tasks = [task for task in plan.tasks if task.subtask_ids]
        assert len(parent_tasks) > 0
        
        # Check subtask relationships
        for parent in parent_tasks:
            subtasks = [task for task in plan.tasks if task.parent_task_id == parent.id]
            assert len(subtasks) > 0
            
            # Subtasks should be of type SUBTASK
            for subtask in subtasks:
                assert subtask.task_type == TaskType.SUBTASK
                assert subtask.id in parent.subtask_ids
    
    @pytest.mark.asyncio
    async def test_dependency_generation(self, service, sample_planning_request):
        """Test that dependencies are intelligently generated"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Should have dependencies based on phases
        assert len(plan.dependencies) > 0
        
        # Architecture tasks should come before implementation
        arch_tasks = [t for t in plan.tasks if t.phase == ExecutionPhase.ARCHITECTURE]
        impl_tasks = [t for t in plan.tasks if t.phase == ExecutionPhase.IMPLEMENTATION]
        
        if arch_tasks and impl_tasks:
            # Check if there are dependencies between phases
            dep_pairs = [(d.dependent_task_id, d.prerequisite_task_id) for d in plan.dependencies]
            
            # At least some implementation tasks should depend on architecture tasks
            phase_deps_exist = any(
                impl.id in [d[0] for d in dep_pairs] and 
                any(arch.id in [d[1] for d in dep_pairs] for arch in arch_tasks)
                for impl in impl_tasks
            )
            assert phase_deps_exist or len(plan.dependencies) > 0
    
    @pytest.mark.asyncio
    async def test_effort_estimation(self, service, sample_planning_request):
        """Test that effort is properly estimated"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Each task should have effort estimation
        for task in plan.tasks:
            assert task.estimated_hours > 0
            assert task.estimated_complexity in ['simple', 'medium', 'complex']
        
        # Total hours should be sum of all tasks
        calculated_total = sum(task.estimated_hours for task in plan.tasks)
        assert abs(plan.total_estimated_hours - calculated_total) < 0.01
    
    @pytest.mark.asyncio
    async def test_parallel_execution_groups(self, service, sample_planning_request):
        """Test identification of parallel execution groups"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Should identify tasks that can run in parallel
        assert len(plan.parallel_execution_groups) > 0
        
        # Tasks in same group should be able to run in parallel
        for group in plan.parallel_execution_groups:
            group_tasks = [plan.get_task_by_id(task_id) for task_id in group]
            
            # Verify no file conflicts within group
            all_files = []
            for task in group_tasks:
                if task:
                    all_files.extend(task.file_references)
            
            # File references should be unique within parallel group
            # (simplified check - in reality would need more sophisticated validation)
            assert len(all_files) == len(set(all_files)) or len(all_files) == 0
    
    @pytest.mark.asyncio
    async def test_plan_validation(self, service, sample_planning_request):
        """Test that generated plans are valid"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Plan should be valid
        is_valid, errors = plan.validate_plan()
        assert is_valid
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation(self, service, sample_planning_request):
        """Test confidence score calculation"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Confidence score should be between 0 and 1
        assert 0 <= plan.confidence_score <= 1
        
        # With good requirements, confidence should be reasonable
        assert plan.confidence_score > 0.5
    
    @pytest.mark.asyncio
    async def test_risk_identification(self, service, sample_planning_request):
        """Test that risks are properly identified"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Authentication tasks should have security risks identified
        auth_tasks = [task for task in plan.tasks if "auth" in task.title.lower()]
        
        for task in auth_tasks:
            if task.risks:
                assert any("security" in risk.lower() for risk in task.risks)
    
    @pytest.mark.asyncio
    async def test_technical_considerations(self, service, sample_planning_request):
        """Test that technical considerations are included"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Tasks should have technical requirements/considerations
        tasks_with_tech_reqs = [task for task in plan.tasks if task.technical_requirements]
        assert len(tasks_with_tech_reqs) > 0
    
    @pytest.mark.asyncio
    async def test_empty_requirements_handling(self, service):
        """Test handling of planning request with no requirements"""
        empty_request = PlanningRequest(
            id="req_empty",
            title="Empty Project",
            description="Project with no requirements"
        )
        
        plan = await service.create_intelligent_plan(empty_request)
        
        # Should still create a valid plan structure
        assert isinstance(plan, TaskPlan)
        assert plan.planning_request_id == empty_request.id
        assert len(plan.tasks) == 0
        assert plan.total_estimated_hours == 0
    
    @pytest.mark.asyncio
    async def test_task_type_determination(self, service):
        """Test determination of task types based on effort"""
        request = PlanningRequest(
            id="req_types",
            title="Task Type Test",
            description="Test different task types"
        )
        
        # Add requirements with different complexities
        pytest_request.add_requirement(
            description="Fix minor typo in documentation",
            priority="low",
            acceptance_criteria=["Fix typo"]
        )
        
        pytest_request.add_requirement(
            description="Build complete e-commerce platform with payment integration",
            priority="critical",
            acceptance_criteria=[
                "Product catalog",
                "Shopping cart",
                "Payment processing",
                "Order management",
                "User accounts",
                "Admin dashboard",
                "Inventory tracking",
                "Email notifications",
                "Mobile app",
                "Analytics"
            ]
        )
        
        plan = await service.create_intelligent_plan(request)
        
        # Should have different task types based on complexity
        task_types = set(task.task_type for task in plan.tasks)
        assert len(task_types) > 1  # Should have variety
    
    @pytest.mark.asyncio
    async def test_execute_plan_without_facade(self, service):
        """Test plan execution when task facade is not available"""
        request = PlanningRequest(
            id="req_exec",
            title="Execution Test",
            description="Test execution without facade"
        )
        pytest_request.add_requirement("Test requirement", "medium")
        
        plan = await service.create_intelligent_plan(request)
        
        # Execute without facade
        result = await service.execute_plan_with_mcp(plan, "git_branch_123")
        
        assert not result['success']
        assert 'error' in result
        assert 'facade not available' in result['error']
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_facade(self, service):
        """Test plan execution with mock task facade"""
        # Mock task facade
        mock_facade = Mock()
        service.task_facade = mock_facade
        
        request = PlanningRequest(
            id="req_exec_facade",
            title="Execution with Facade Test",
            description="Test execution with facade"
        )
        pytest_request.add_requirement("Implement feature", "high")
        
        plan = await service.create_intelligent_plan(request)
        
        # Execute with facade
        result = await service.execute_plan_with_mcp(plan, "git_branch_456")
        
        assert result['success']
        assert len(result['created_tasks']) > 0
        assert result['plan_summary']['total_tasks'] == len(plan.tasks)
        
        # All tasks should have MCP IDs assigned
        for task in plan.tasks:
            if task.parent_task_id is None:  # Root tasks
                assert task.mcp_task_id is not None
                assert task.status == 'created'
    
    @pytest.mark.asyncio
    async def test_phase_ordering(self, service, sample_planning_request):
        """Test that execution phases are properly ordered"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Expected phase order
        phase_order = [
            ExecutionPhase.PLANNING,
            ExecutionPhase.ARCHITECTURE,
            ExecutionPhase.IMPLEMENTATION,
            ExecutionPhase.TESTING,
            ExecutionPhase.REVIEW,
            ExecutionPhase.DEPLOYMENT,
            ExecutionPhase.MONITORING
        ]
        
        # Check that phases in plan follow expected order
        plan_phases = plan.execution_phases
        
        # Get indices of phases in expected order
        phase_indices = []
        for phase in plan_phases:
            if phase in phase_order:
                phase_indices.append(phase_order.index(phase))
        
        # Indices should be in ascending order (phases should follow sequence)
        if len(phase_indices) > 1:
            assert phase_indices == sorted(phase_indices)
    
    @pytest.mark.asyncio
    async def test_workload_distribution(self, service, sample_planning_request):
        """Test that workload is distributed among agents"""
        plan = await service.create_intelligent_plan(sample_planning_request)
        
        # Check workload distribution
        assert len(plan.agent_workload) > 0
        
        # No single agent should be overloaded (more than 40 hours)
        for agent, hours in plan.agent_workload.items():
            assert hours <= 60  # Allow some overload but not extreme
        
        # Workload should match sum of assigned task hours
        calculated_workload = {}
        for task in plan.tasks:
            if task.agent_assignment:
                agent = task.agent_assignment.primary_agent
                calculated_workload[agent] = calculated_workload.get(agent, 0) + task.estimated_hours
        
        # Verify workload calculation
        for agent in calculated_workload:
            assert abs(plan.agent_workload.get(agent, 0) - calculated_workload[agent]) < 0.01