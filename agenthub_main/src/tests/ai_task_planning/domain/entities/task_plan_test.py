"""Test suite for TaskPlan domain entity"""

import pytest
from datetime import datetime, timezone
from fastmcp.ai_task_planning.domain.entities.task_plan import (
    TaskPlan, PlannedTask, TaskDependency, AgentAssignment,
    TaskType, ExecutionPhase
)


class TestAgentAssignment:
    """Test cases for AgentAssignment"""
    
    def test_create_basic_agent_assignment(self):
        """Test creating agent assignment with primary agent only"""
        assignment = AgentAssignment(primary_agent="coding-agent")
        
        assert assignment.primary_agent == "coding-agent"
        assert assignment.supporting_agents == []
        assert assignment.effort_percentage == {"coding-agent": 100.0}
    
    def test_agent_assignment_with_support(self):
        """Test creating agent assignment with supporting agents"""
        assignment = AgentAssignment(
            primary_agent="frontend-agent",
            supporting_agents=["shadcn-ui-expert-agent", "css-expert-agent"],
            effort_percentage={
                "frontend-agent": 70.0,
                "shadcn-ui-expert-agent": 20.0,
                "css-expert-agent": 10.0
            }
        )
        
        assert assignment.primary_agent == "frontend-agent"
        assert len(assignment.supporting_agents) == 2
        assert "shadcn-ui-expert-agent" in assignment.supporting_agents
        assert assignment.effort_percentage["frontend-agent"] == 70.0
        assert assignment.effort_percentage["shadcn-ui-expert-agent"] == 20.0
    
    def test_agent_assignment_to_dict(self):
        """Test converting agent assignment to dictionary"""
        assignment = AgentAssignment(
            primary_agent="test-agent",
            supporting_agents=["helper-agent"],
            effort_percentage={"test-agent": 80.0, "helper-agent": 20.0}
        )
        
        data = assignment.to_dict()
        
        assert data['primary_agent'] == "test-agent"
        assert data['supporting_agents'] == ["helper-agent"]
        assert data['effort_percentage']['test-agent'] == 80.0


class TestPlannedTask:
    """Test cases for PlannedTask"""
    
    def test_create_basic_planned_task(self):
        """Test creating a basic planned task"""
        task = PlannedTask(
            id="task_001",
            title="Implement login endpoint",
            description="Create REST endpoint for user login",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION
        )
        
        assert task.id == "task_001"
        assert task.title == "Implement login endpoint"
        assert task.task_type == TaskType.TASK
        assert task.phase == ExecutionPhase.IMPLEMENTATION
        assert task.status == "planned"
        assert task.priority == "medium"
        assert task.estimated_hours == 0.0
        assert task.parent_task_id is None
        assert isinstance(task.created_at, datetime)
    
    def test_planned_task_with_full_details(self):
        """Test creating planned task with all fields"""
        assignment = AgentAssignment(
            primary_agent="backend-agent",
            supporting_agents=["api-specialist-agent"]
        )
        
        task = PlannedTask(
            id="task_002",
            title="Create API Gateway",
            description="Implement API gateway with rate limiting",
            task_type=TaskType.FEATURE,
            phase=ExecutionPhase.ARCHITECTURE,
            agent_assignment=assignment,
            estimated_hours=16.0,
            estimated_complexity="complex",
            acceptance_criteria=[
                "Support JWT authentication",
                "Rate limiting per client",
                "Request/response logging"
            ],
            technical_requirements=[
                "Use Express.js middleware",
                "Redis for rate limiting"
            ],
            file_references=["gateway/index.js", "middleware/auth.js"],
            code_references={
                "auth/jwt.js": ["45-89", "120-150"]
            },
            priority="high",
            tags=["api", "gateway", "security"],
            risks=["Redis dependency", "Performance impact"],
            assumptions=["Redis available", "JWT tokens valid"]
        )
        
        assert task.estimated_hours == 16.0
        assert task.estimated_complexity == "complex"
        assert len(task.acceptance_criteria) == 3
        assert "Support JWT authentication" in task.acceptance_criteria
        assert len(task.technical_requirements) == 2
        assert len(task.file_references) == 2
        assert "auth/jwt.js" in task.code_references
        assert task.priority == "high"
        assert len(task.tags) == 3
        assert len(task.risks) == 2
        assert len(task.assumptions) == 2
    
    def test_add_subtask(self):
        """Test adding subtasks to a task"""
        parent_task = PlannedTask(
            id="task_parent",
            title="Parent Task",
            description="Main task",
            task_type=TaskType.STORY,
            phase=ExecutionPhase.IMPLEMENTATION
        )
        
        subtask = PlannedTask(
            id="task_child",
            title="Child Task",
            description="Subtask",
            task_type=TaskType.SUBTASK,
            phase=ExecutionPhase.IMPLEMENTATION
        )
        
        parent_task.add_subtask(subtask)
        
        assert "task_child" in parent_task.subtask_ids
        assert subtask.parent_task_id == "task_parent"
        
        # Test duplicate prevention
        parent_task.add_subtask(subtask)
        assert parent_task.subtask_ids.count("task_child") == 1
    
    def test_can_run_in_parallel_same_agent(self):
        """Test parallel execution check with same agent"""
        task1 = PlannedTask(
            id="task_1",
            title="Task 1",
            description="First task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("coding-agent")
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Task 2", 
            description="Second task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("coding-agent")
        )
        
        # Same agent can't work on both tasks
        assert not task1.can_run_in_parallel(task2)
    
    def test_can_run_in_parallel_file_conflict(self):
        """Test parallel execution check with file conflicts"""
        task1 = PlannedTask(
            id="task_1",
            title="Task 1",
            description="First task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            file_references=["file1.py", "file2.py"]
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Task 2",
            description="Second task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            file_references=["file2.py", "file3.py"]
        )
        
        # Shared file prevents parallel execution
        assert not task1.can_run_in_parallel(task2)
    
    def test_can_run_in_parallel_compatible_phases(self):
        """Test parallel execution with compatible phases"""
        task1 = PlannedTask(
            id="task_1",
            title="Implementation Task",
            description="Code implementation",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("coding-agent")
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Documentation Task",
            description="Write docs",
            task_type=TaskType.DOCUMENTATION,
            phase=ExecutionPhase.DEPLOYMENT,
            agent_assignment=AgentAssignment("doc-agent")
        )
        
        # Different agents and compatible phases
        assert task1.can_run_in_parallel(task2)
    
    def test_to_mcp_task_request(self):
        """Test converting to MCP task request format"""
        assignment = AgentAssignment(
            primary_agent="coding-agent",
            supporting_agents=["review-agent"]
        )
        
        task = PlannedTask(
            id="task_003",
            title="Implement Feature X",
            description="Add new feature X",
            task_type=TaskType.FEATURE,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=assignment,
            estimated_hours=8.0,
            estimated_complexity="medium",
            acceptance_criteria=["Feature works", "Tests pass"],
            technical_requirements=["Use TypeScript"],
            file_references=["src/feature.ts"],
            code_references={"utils.ts": ["10-20"]},
            priority="high",
            tags=["feature", "priority"],
            risks=["API changes"],
            assumptions=["API stable"]
        )
        
        request = task.to_mcp_task_request()
        
        assert request['title'] == "Implement Feature X"
        assert request['description'] == "Add new feature X"
        assert "coding-agent" in request['assignees']
        assert "review-agent" in request['assignees']
        assert request['priority'] == "high"
        assert request['estimated_effort'] == "8.0h"
        assert request['labels'] == ["feature", "priority"]
        assert "**Task Type**: feature" in request['details']
        assert "**Estimated Hours**: 8.0" in request['details']
        assert "- Feature works" in request['details']
        assert "- Use TypeScript" in request['details']
    
    def test_to_dict_serialization(self):
        """Test serializing planned task to dictionary"""
        assignment = AgentAssignment("test-agent")
        
        task = PlannedTask(
            id="task_ser",
            title="Serialization Test",
            description="Test task serialization",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.TESTING,
            agent_assignment=assignment,
            estimated_hours=2.0,
            mcp_task_id="mcp_123"
        )
        
        data = task.to_dict()
        
        assert data['id'] == "task_ser"
        assert data['title'] == "Serialization Test"
        assert data['task_type'] == "task"
        assert data['phase'] == "testing"
        assert data['agent_assignment']['primary_agent'] == "test-agent"
        assert data['estimated_hours'] == 2.0
        assert data['mcp_task_id'] == "mcp_123"
        assert 'created_at' in data


class TestTaskPlan:
    """Test cases for TaskPlan"""
    
    def test_create_basic_task_plan(self):
        """Test creating a basic task plan"""
        plan = TaskPlan(
            id="plan_001",
            planning_request_id="req_001",
            title="Authentication System Plan",
            description="Plan for implementing authentication"
        )
        
        assert plan.id == "plan_001"
        assert plan.planning_request_id == "req_001"
        assert plan.title == "Authentication System Plan"
        assert plan.tasks == []
        assert plan.dependencies == []
        assert plan.total_estimated_hours == 0.0
        assert plan.confidence_score == 0.0
        assert plan.risk_level == "medium"
        assert plan.created_by == "ai_task_planning_engine"
        assert plan.version == "1.0"
    
    def test_add_task_to_plan(self):
        """Test adding tasks to the plan"""
        plan = TaskPlan(
            id="plan_002",
            planning_request_id="req_002",
            title="Feature Plan",
            description="Plan for new feature"
        )
        
        task1 = PlannedTask(
            id="task_1",
            title="Design API",
            description="Design REST API",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.ARCHITECTURE,
            agent_assignment=AgentAssignment("architect-agent"),
            estimated_hours=4.0
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Implement API",
            description="Code the API",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment(
                "coding-agent",
                supporting_agents=["api-agent"],
                effort_percentage={"coding-agent": 80.0, "api-agent": 20.0}
            ),
            estimated_hours=12.0
        )
        
        plan.add_task(task1)
        plan.add_task(task2)
        
        assert len(plan.tasks) == 2
        assert plan.total_estimated_hours == 16.0
        assert "architect-agent" in plan.agent_workload
        assert plan.agent_workload["architect-agent"] == 4.0
        assert plan.agent_workload["coding-agent"] == 12.0
        assert plan.agent_workload["api-agent"] == 2.4  # 20% of 12 hours
        assert len(plan.required_agents) == 3
        assert ExecutionPhase.ARCHITECTURE in plan.execution_phases
        assert ExecutionPhase.IMPLEMENTATION in plan.execution_phases
        
        # Test duplicate prevention
        plan.add_task(task1)
        assert len(plan.tasks) == 2
    
    def test_add_dependency(self):
        """Test adding dependencies between tasks"""
        plan = TaskPlan(
            id="plan_003",
            planning_request_id="req_003",
            title="Dependency Plan",
            description="Plan with dependencies"
        )
        
        plan.add_dependency(
            dependent_task_id="task_2",
            prerequisite_task_id="task_1",
            dependency_type="finish_to_start",
            lag_time=2
        )
        
        assert len(plan.dependencies) == 1
        dep = plan.dependencies[0]
        assert dep.dependent_task_id == "task_2"
        assert dep.prerequisite_task_id == "task_1"
        assert dep.dependency_type == "finish_to_start"
        assert dep.lag_time == 2
    
    def test_get_task_by_id(self):
        """Test retrieving task by ID"""
        plan = TaskPlan(
            id="plan_004",
            planning_request_id="req_004",
            title="Search Plan",
            description="Plan for testing search"
        )
        
        task = PlannedTask(
            id="task_find",
            title="Findable Task",
            description="Task to find",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION
        )
        
        plan.add_task(task)
        
        found_task = plan.get_task_by_id("task_find")
        assert found_task is not None
        assert found_task.title == "Findable Task"
        
        not_found = plan.get_task_by_id("nonexistent")
        assert not_found is None
    
    def test_get_root_and_subtasks(self):
        """Test getting root tasks and subtasks"""
        plan = TaskPlan(
            id="plan_005",
            planning_request_id="req_005",
            title="Hierarchy Plan",
            description="Plan with task hierarchy"
        )
        
        # Create parent tasks
        epic = PlannedTask(
            id="epic_1",
            title="Epic Task",
            description="Top level epic",
            task_type=TaskType.EPIC,
            phase=ExecutionPhase.PLANNING
        )
        
        # Create child tasks
        story1 = PlannedTask(
            id="story_1",
            title="Story 1",
            description="First story",
            task_type=TaskType.STORY,
            phase=ExecutionPhase.IMPLEMENTATION,
            parent_task_id="epic_1"
        )
        
        story2 = PlannedTask(
            id="story_2",
            title="Story 2",
            description="Second story",
            task_type=TaskType.STORY,
            phase=ExecutionPhase.IMPLEMENTATION,
            parent_task_id="epic_1"
        )
        
        # Create grandchild task
        task1 = PlannedTask(
            id="task_1",
            title="Task 1",
            description="Implementation task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            parent_task_id="story_1"
        )
        
        plan.add_task(epic)
        plan.add_task(story1)
        plan.add_task(story2)
        plan.add_task(task1)
        
        # Test root tasks
        root_tasks = plan.get_root_tasks()
        assert len(root_tasks) == 1
        assert root_tasks[0].id == "epic_1"
        
        # Test subtasks
        epic_subtasks = plan.get_subtasks("epic_1")
        assert len(epic_subtasks) == 2
        assert any(task.id == "story_1" for task in epic_subtasks)
        assert any(task.id == "story_2" for task in epic_subtasks)
        
        story_subtasks = plan.get_subtasks("story_1")
        assert len(story_subtasks) == 1
        assert story_subtasks[0].id == "task_1"
    
    def test_find_parallel_execution_groups(self):
        """Test finding tasks that can run in parallel"""
        plan = TaskPlan(
            id="plan_006",
            planning_request_id="req_006",
            title="Parallel Plan",
            description="Plan for parallel execution"
        )
        
        # Tasks that can run in parallel (different agents, no file conflicts)
        task1 = PlannedTask(
            id="task_1",
            title="Frontend Work",
            description="UI implementation",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("frontend-agent"),
            file_references=["ui/component.tsx"]
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Backend Work",
            description="API implementation",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("backend-agent"),
            file_references=["api/endpoint.py"]
        )
        
        # Task that conflicts with task1 (same file)
        task3 = PlannedTask(
            id="task_3",
            title="UI Update",
            description="Update UI component",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("ui-agent"),
            file_references=["ui/component.tsx"]
        )
        
        plan.add_task(task1)
        plan.add_task(task2)
        plan.add_task(task3)
        
        groups = plan.find_parallel_execution_groups()
        
        # Should have at least 2 groups since task1 and task3 conflict
        assert len(groups) >= 2
        
        # task1 and task2 should be in same group (can run in parallel)
        group_with_task1 = next(g for g in groups if "task_1" in g)
        assert "task_2" in group_with_task1
        
        # task3 should be in different group from task1
        group_with_task3 = next(g for g in groups if "task_3" in g)
        assert "task_1" not in group_with_task3
    
    def test_validate_plan_circular_dependency(self):
        """Test plan validation with circular dependencies"""
        plan = TaskPlan(
            id="plan_007",
            planning_request_id="req_007",
            title="Invalid Plan",
            description="Plan with circular dependency"
        )
        
        # Add tasks
        task1 = PlannedTask(
            id="task_1",
            title="Task 1",
            description="First task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("agent1")
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Task 2",
            description="Second task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("agent2")
        )
        
        plan.add_task(task1)
        plan.add_task(task2)
        
        # Add circular dependency
        plan.add_dependency("task_1", "task_2")
        plan.add_dependency("task_2", "task_1")
        
        is_valid, errors = plan.validate_plan()
        
        assert not is_valid
        assert any("Circular dependency" in error for error in errors)
    
    def test_validate_plan_missing_task_reference(self):
        """Test plan validation with missing task references"""
        plan = TaskPlan(
            id="plan_008",
            planning_request_id="req_008",
            title="Invalid Plan",
            description="Plan with missing task reference"
        )
        
        task1 = PlannedTask(
            id="task_1",
            title="Task 1",
            description="Only task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("agent1")
        )
        
        plan.add_task(task1)
        
        # Add dependency referencing non-existent task
        plan.add_dependency("task_1", "task_missing")
        
        is_valid, errors = plan.validate_plan()
        
        assert not is_valid
        assert any("non-existent task: task_missing" in error for error in errors)
    
    def test_validate_plan_unassigned_tasks(self):
        """Test plan validation with unassigned tasks"""
        plan = TaskPlan(
            id="plan_009",
            planning_request_id="req_009",
            title="Invalid Plan",
            description="Plan with unassigned tasks"
        )
        
        task = PlannedTask(
            id="task_unassigned",
            title="Unassigned Task",
            description="Task without agent",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION
            # No agent_assignment
        )
        
        plan.add_task(task)
        
        is_valid, errors = plan.validate_plan()
        
        assert not is_valid
        assert any("without agent assignments" in error for error in errors)
        assert any("task_unassigned" in error for error in errors)
    
    def test_calculate_critical_path_simple(self):
        """Test critical path calculation with simple dependency chain"""
        plan = TaskPlan(
            id="plan_010",
            planning_request_id="req_010",
            title="Critical Path Plan",
            description="Plan for critical path testing"
        )
        
        # Create linear dependency chain: task1 -> task2 -> task3
        task1 = PlannedTask(
            id="task_1",
            title="Task 1",
            description="First task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            estimated_hours=4.0
        )
        
        task2 = PlannedTask(
            id="task_2",
            title="Task 2",
            description="Second task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            estimated_hours=6.0
        )
        
        task3 = PlannedTask(
            id="task_3",
            title="Task 3",
            description="Third task",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.TESTING,
            estimated_hours=2.0
        )
        
        plan.add_task(task1)
        plan.add_task(task2)
        plan.add_task(task3)
        
        plan.add_dependency("task_2", "task_1")
        plan.add_dependency("task_3", "task_2")
        
        critical_path = plan.calculate_critical_path()
        
        # In this simple case, task1 is the root of the critical path
        assert "task_1" in critical_path
    
    def test_to_dict_serialization(self):
        """Test serializing task plan to dictionary"""
        plan = TaskPlan(
            id="plan_ser",
            planning_request_id="req_ser",
            title="Serialization Plan",
            description="Test plan serialization",
            confidence_score=0.85,
            risk_level="low"
        )
        
        task = PlannedTask(
            id="task_ser",
            title="Serializable Task",
            description="Task for serialization",
            task_type=TaskType.TASK,
            phase=ExecutionPhase.IMPLEMENTATION,
            agent_assignment=AgentAssignment("test-agent"),
            estimated_hours=5.0
        )
        
        plan.add_task(task)
        plan.add_dependency("task_ser", "task_prereq")
        plan.execution_phases = [ExecutionPhase.PLANNING, ExecutionPhase.IMPLEMENTATION]
        plan.parallel_execution_groups = [["task_1", "task_2"], ["task_3"]]
        plan.critical_path = ["task_1", "task_3"]
        
        data = plan.to_dict()
        
        assert data['id'] == "plan_ser"
        assert data['planning_request_id'] == "req_ser"
        assert data['title'] == "Serialization Plan"
        assert data['confidence_score'] == 0.85
        assert data['risk_level'] == "low"
        assert len(data['tasks']) == 1
        assert data['tasks'][0]['id'] == "task_ser"
        assert len(data['dependencies']) == 1
        assert data['total_estimated_hours'] == 5.0
        assert data['execution_phases'] == ["planning", "implementation"]
        assert len(data['parallel_execution_groups']) == 2
        assert data['critical_path'] == ["task_1", "task_3"]
        assert "test-agent" in data['required_agents']
        assert data['created_by'] == "ai_task_planning_engine"
        assert data['version'] == "1.0"
        assert 'created_at' in data
    
    def test_task_type_enum_values(self):
        """Test TaskType enum values"""
        assert TaskType.EPIC.value == "epic"
        assert TaskType.FEATURE.value == "feature"
        assert TaskType.STORY.value == "story"
        assert TaskType.TASK.value == "task"
        assert TaskType.SUBTASK.value == "subtask"
        assert TaskType.BUG.value == "bug"
        assert TaskType.SPIKE.value == "spike"
        assert TaskType.DOCUMENTATION.value == "documentation"
        assert TaskType.TESTING.value == "testing"
        assert TaskType.REVIEW.value == "review"
    
    def test_execution_phase_enum_values(self):
        """Test ExecutionPhase enum values"""
        assert ExecutionPhase.PLANNING.value == "planning"
        assert ExecutionPhase.ARCHITECTURE.value == "architecture"
        assert ExecutionPhase.IMPLEMENTATION.value == "implementation"
        assert ExecutionPhase.TESTING.value == "testing"
        assert ExecutionPhase.REVIEW.value == "review"
        assert ExecutionPhase.DEPLOYMENT.value == "deployment"
        assert ExecutionPhase.MONITORING.value == "monitoring"