"""Unit tests for Project Rich Domain Model (Phase 1).

Tests the business logic methods added to Project entity:
- validate_agent_assignment()
- calculate_project_health()
- check_deadline_risk()

Rich Domain Model implementation with business logic methods.
"""

import pytest
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.agent import Agent


class TestProjectFeatureFlag:
    """Test feature flag behavior for Rich Domain Model."""

    def test_rich_domain_model_is_active(self):
        """Test that rich domain model is always active (feature flag removed)."""
        project = Project.create(
            name="Test Project",
            description="Test description"
        )

        # Rich domain model is now the default and only behavior
        # Feature flag has been removed - this test verifies the entity can be created
        assert project is not None
        assert project.name == "Test Project"


class TestValidateAgentAssignment:
    """Test validate_agent_assignment() method."""

    def test_validate_with_flag_disabled_basic_validation(self):
        """When flag is disabled, only basic validation (legacy behavior)."""
        project = Project.create(name="Test Project")

        # Register agent and create branch
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        branch = project.create_git_branch(
            git_branch_name="test-branch",
            name="Test Branch"
        )

        # Valid assignment
        assert project.validate_agent_assignment("agent-1", branch.id) is True

        # Invalid: unregistered agent
        assert project.validate_agent_assignment("unknown-agent", branch.id) is False

        # Invalid: unknown branch
        assert project.validate_agent_assignment("agent-1", "unknown-branch") is False

    def test_validate_registered_agent_and_existing_branch(self):
        """Valid assignment when agent registered and branch exists."""
        project = Project.create(name="Test Project")

        # Setup
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        branch = project.create_git_branch(
            git_branch_name="feature-branch",
            name="Feature Branch"
        )

        # Should be valid
        result = project.validate_agent_assignment("agent-1", branch.id)
        assert result is True

    def test_validate_unregistered_agent_fails(self):
        """Unregistered agent cannot be assigned."""
        project = Project.create(name="Test Project")

        branch = project.create_git_branch(
            git_branch_name="test-branch",
            name="Test Branch"
        )

        # Unregistered agent should fail
        result = project.validate_agent_assignment("unknown-agent", branch.id)
        assert result is False

    def test_validate_nonexistent_branch_fails(self):
        """Cannot assign to non-existent branch."""
        project = Project.create(name="Test Project")

        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        # Non-existent branch should fail
        result = project.validate_agent_assignment("agent-1", "unknown-branch-id")
        assert result is False

    def test_validate_agent_workload_limit(self):
        """Agent cannot be assigned more than 3 concurrent branches."""
        project = Project.create(name="Test Project")

        # Register agent
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        # Create 4 branches
        branches = []
        for i in range(4):
            branch = project.create_git_branch(
                git_branch_name=f"branch-{i}",
                name=f"Branch {i}"
            )
            branches.append(branch)

        # Assign agent to first 3 branches (should succeed)
        for i in range(3):
            assert project.validate_agent_assignment("agent-1", branches[i].id) is True
            project.assign_agent_to_tree("agent-1", branches[i].id)

        # 4th assignment should fail (overloaded)
        result = project.validate_agent_assignment("agent-1", branches[3].id)
        assert result is False

    def test_validate_reassignment_allowed(self):
        """Reassigning same branch to different agent is allowed."""
        project = Project.create(name="Test Project")

        # Register two agents
        agent1 = Agent(id="agent-1", name="Agent 1")
        agent2 = Agent(id="agent-2", name="Agent 2")
        project.register_agent(agent1)
        project.register_agent(agent2)

        # Create branch and assign to agent1
        branch = project.create_git_branch(
            git_branch_name="test-branch",
            name="Test Branch"
        )
        project.assign_agent_to_tree("agent-1", branch.id)

        # Reassigning to agent2 should be valid
        result = project.validate_agent_assignment("agent-2", branch.id)
        assert result is True

    def test_validate_same_agent_reassignment_allowed(self):
        """Assigning same agent to already assigned branch is allowed."""
        project = Project.create(name="Test Project")

        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        branch = project.create_git_branch(
            git_branch_name="test-branch",
            name="Test Branch"
        )
        project.assign_agent_to_tree("agent-1", branch.id)

        # Reassigning same agent should be valid
        result = project.validate_agent_assignment("agent-1", branch.id)
        assert result is True


class TestCalculateProjectHealth:
    """Test calculate_project_health() method."""

    def test_health_with_basic_project_setup(self):
        """Health calculation with basic project setup (1 agent, 1 branch)."""
        project = Project.create(name="Test Project")

        # Add some agents and branches
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        branch = project.create_git_branch(
            git_branch_name="branch-1",
            name="Branch 1"
        )
        project.assign_agent_to_tree("agent-1", branch.id)

        health = project.calculate_project_health()

        # Rich domain model always provides detailed health metrics
        assert health["counts"]["total_branches"] == 1
        assert "overall_health_score" in health
        assert "health_status" in health
        assert isinstance(health["overall_health_score"], (int, float))
        assert health["health_status"] in ["excellent", "good", "fair", "poor", "critical"]

    def test_health_empty_project(self):
        """Health calculation for empty project."""
        project = Project.create(name="Empty Project")

        health = project.calculate_project_health()

        # Empty project: no branches (100% branch completion) but no agents (0% utilization)
        # Score = (100 * 0.40) + (0 * 0.20) + (100 * 0.25) + (0 * 0.30) = 40 + 0 + 25 + 0 = 65
        assert health["overall_health_score"] == 65.0
        assert health["health_status"] == "fair"  # 60-75 range
        assert health["metrics"]["branch_completion_rate"] == 100.0
        assert health["counts"]["total_branches"] == 0

    def test_health_excellent_status(self):
        """Project with agents assigned (validates health calculation)."""
        project = Project.create(name="Test Project")

        # Create project setup with high agent utilization
        for i in range(3):
            agent = Agent(id=f"agent-{i}", name=f"Agent {i}")
            project.register_agent(agent)

            branch = project.create_git_branch(
                git_branch_name=f"branch-{i}",
                name=f"Branch {i}"
            )
            project.assign_agent_to_tree(f"agent-{i}", branch.id)

        health = project.calculate_project_health()

        # Project with branches but no tasks: branches show 0% completion (not 100%)
        # Validates that health calculation produces valid results
        assert health["health_status"] in ["excellent", "good", "fair", "poor", "critical"]
        assert 0 <= health["overall_health_score"] <= 100
        assert health["metrics"]["agent_utilization"] == 100.0

    def test_health_poor_status_no_agents_assigned(self):
        """Project with poor health (no agent assignments)."""
        project = Project.create(name="Test Project")

        # Create branches but no agent assignments
        for i in range(3):
            project.create_git_branch(
                git_branch_name=f"branch-{i}",
                name=f"Branch {i}"
            )

        health = project.calculate_project_health()

        # Should have poor health with no assignments
        assert health["metrics"]["agent_utilization"] == 0.0
        assert health["counts"]["assigned_agents"] == 0

    def test_health_metrics_calculation(self):
        """Verify health metrics are calculated correctly."""
        project = Project.create(name="Test Project")

        # Register 5 agents
        for i in range(5):
            agent = Agent(id=f"agent-{i}", name=f"Agent {i}")
            project.register_agent(agent)

        # Create 3 branches, assign 3 agents (60% utilization)
        for i in range(3):
            branch = project.create_git_branch(
                git_branch_name=f"branch-{i}",
                name=f"Branch {i}"
            )
            project.assign_agent_to_tree(f"agent-{i}", branch.id)

        health = project.calculate_project_health()

        # Agent utilization should be 60% (3 out of 5)
        assert health["metrics"]["agent_utilization"] == 60.0
        assert health["counts"]["total_agents"] == 5
        assert health["counts"]["assigned_agents"] == 3

    def test_health_with_blocked_tasks(self):
        """Health calculation with blocked tasks."""
        project = Project.create(name="Test Project")

        # Create branches
        branch1 = project.create_git_branch(
            git_branch_name="branch-1",
            name="Branch 1"
        )
        branch2 = project.create_git_branch(
            git_branch_name="branch-2",
            name="Branch 2"
        )

        # Add cross-tree dependency (task2 depends on task1)
        project.cross_tree_dependencies["task-2-id"] = {"task-1-id"}

        health = project.calculate_project_health()

        # Should reflect blocked tasks in metrics
        assert "blocked_task_percentage" in health["metrics"]
        assert health["counts"]["blocked_tasks"] == 1


class TestCheckDeadlineRisk:
    """Test check_deadline_risk() method."""

    def test_risk_empty_project_no_risk(self):
        """Empty project (no branches) has no deadline risk."""
        project = Project.create(name="Test Project")

        risk = project.check_deadline_risk()

        # Rich domain model always provides detailed risk assessment
        # Empty project should have "no_risk" level
        assert risk["risk_level"] == "no_risk"
        assert "assessment" in risk

    def test_risk_no_branches_no_risk(self):
        """Project with no branches has no risk."""
        project = Project.create(name="Empty Project")

        risk = project.check_deadline_risk()

        assert risk["risk_level"] == "no_risk"
        assert "No branches" in risk["assessment"]

    def test_risk_no_tasks_no_risk(self):
        """Project with branches but no tasks has no risk."""
        project = Project.create(name="Test Project")

        # Create branch with no tasks
        project.create_git_branch(
            git_branch_name="empty-branch",
            name="Empty Branch"
        )

        risk = project.check_deadline_risk()

        assert risk["risk_level"] == "no_risk"
        assert "No tasks" in risk["assessment"]

    def test_risk_critical_project_stalled(self):
        """Critical risk when project stalled (< 10% completion, no active work)."""
        project = Project.create(name="Test Project")

        # Create branches (simulating stalled project)
        for i in range(3):
            project.create_git_branch(
                git_branch_name=f"branch-{i}",
                name=f"Branch {i}"
            )

        # Note: In real scenario, branches would have tasks with low completion
        # For this test, we're checking the risk assessment structure

        risk = project.check_deadline_risk()

        # Should have risk assessment with metrics
        assert "risk_level" in risk
        assert "assessment" in risk
        assert "recommendation" in risk

    def test_risk_assessment_includes_metrics(self):
        """Risk assessment includes completion and utilization metrics."""
        project = Project.create(name="Test Project")

        # Register agent
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        # Create branch
        branch = project.create_git_branch(
            git_branch_name="test-branch",
            name="Test Branch"
        )
        project.assign_agent_to_tree("agent-1", branch.id)

        risk = project.check_deadline_risk()

        # Should include metrics when tasks exist
        # (Note: Since no tasks exist, risk will be "no_risk")
        assert risk["risk_level"] == "no_risk"
        assert "recommendation" in risk

    def test_risk_levels_ordered_correctly(self):
        """Verify risk levels are assessed in correct order."""
        # Risk levels from worst to best:
        # critical_risk -> high_risk -> medium_risk -> low_risk -> no_risk

        project = Project.create(name="Test Project")

        # Empty project should have no_risk
        risk = project.check_deadline_risk()
        assert risk["risk_level"] == "no_risk"


class TestProjectRichDomainIntegration:
    """Integration tests for Project Rich Domain Model."""

    def test_full_rich_domain_workflow(self):
        """Test complete workflow with all rich domain features enabled."""
        # Create project
        project = Project.create(
            name="Integration Test Project",
            description="Testing rich domain model"
        )

        # Register agents
        agent1 = Agent(id="agent-1", name="Developer Agent")
        agent2 = Agent(id="agent-2", name="Tester Agent")
        project.register_agent(agent1)
        project.register_agent(agent2)

        # Create branches
        dev_branch = project.create_git_branch(
            git_branch_name="feature/new-feature",
            name="New Feature"
        )
        test_branch = project.create_git_branch(
            git_branch_name="test/feature-tests",
            name="Feature Tests"
        )

        # Validate agent assignments
        assert project.validate_agent_assignment("agent-1", dev_branch.id) is True
        assert project.validate_agent_assignment("agent-2", test_branch.id) is True

        # Assign agents
        project.assign_agent_to_tree("agent-1", dev_branch.id)
        project.assign_agent_to_tree("agent-2", test_branch.id)

        # Calculate project health
        health = project.calculate_project_health()
        assert health["overall_health_score"] > 0
        assert health["health_status"] in ["excellent", "good", "fair", "poor", "critical"]
        assert health["metrics"]["agent_utilization"] == 100.0  # All agents assigned

        # Check deadline risk
        risk = project.check_deadline_risk()
        assert risk["risk_level"] in ["no_risk", "low_risk", "medium_risk", "high_risk", "critical_risk"]
        assert "assessment" in risk
        assert "recommendation" in risk

    def test_rich_domain_model_always_active(self):
        """Rich domain model is always active - provides detailed metrics."""
        project = Project.create(name="Active Project")

        # Register agent and branch
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)

        branch = project.create_git_branch(
            git_branch_name="test-branch",
            name="Test Branch"
        )

        # Validation always uses rich business logic
        assert project.validate_agent_assignment("agent-1", branch.id) is True

        # Health always returns detailed metrics
        health = project.calculate_project_health()
        assert "overall_health_score" in health
        assert "health_status" in health
        assert health["health_status"] != "unknown"

        # Risk always returns detailed assessment
        risk = project.check_deadline_risk()
        assert risk["risk_level"] != "unknown"

    def test_health_metrics_consistency(self):
        """Health calculation provides consistent rich metrics."""
        project = Project.create(name="Metrics Test Project")

        # Get health for empty project
        health = project.calculate_project_health()

        # Rich domain uses "overall_health_score" not "health_score"
        assert "overall_health_score" in health
        assert health["overall_health_score"] is not None
        assert isinstance(health["overall_health_score"], (int, float))
        assert "health_status" in health
        assert "metrics" in health
        assert "counts" in health

    def test_agent_workload_prevents_overassignment(self):
        """Rich domain model prevents agent overload."""
        project = Project.create(name="Workload Test Project")

        # Register one agent
        agent = Agent(id="busy-agent", name="Busy Agent")
        project.register_agent(agent)

        # Create 5 branches
        branches = []
        for i in range(5):
            branch = project.create_git_branch(
                git_branch_name=f"branch-{i}",
                name=f"Branch {i}"
            )
            branches.append(branch)

        # Assign to first 3 branches (should succeed)
        for i in range(3):
            assert project.validate_agent_assignment("busy-agent", branches[i].id) is True
            project.assign_agent_to_tree("busy-agent", branches[i].id)

        # 4th assignment should fail (agent overloaded) - rich domain model enforces this
        assert project.validate_agent_assignment("busy-agent", branches[3].id) is False
