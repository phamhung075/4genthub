"""Unit tests for agent value objects."""

from datetime import UTC, datetime

import pytest

from fastmcp.task_management.domain.value_objects.agents import (
    AgentCapabilities,
    AgentExpertise,
    AgentPerformanceMetrics,
    AgentProfile,
    AgentRole,
    AgentStatus,
)


class TestAgentCapabilities:
    """Test cases for AgentCapabilities value object."""

    def test_create_agent_capabilities(self):
        """Test creating agent capabilities with valid data."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER,
            secondary_roles={AgentRole.REVIEWER, AgentRole.TESTER},
            expertise_areas={AgentExpertise.BACKEND, AgentExpertise.DATABASE},
            skill_levels={"python": 0.9, "sql": 0.8},
            max_task_complexity=8,
            preferred_task_types={"implementation", "bugfix"},
        )

        assert capabilities.primary_role == AgentRole.DEVELOPER
        assert AgentRole.REVIEWER in capabilities.secondary_roles
        assert AgentExpertise.BACKEND in capabilities.expertise_areas
        assert capabilities.skill_levels["python"] == 0.9
        assert capabilities.max_task_complexity == 8
        assert "implementation" in capabilities.preferred_task_types

    def test_can_handle_role(self):
        """Test role handling check."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, secondary_roles={AgentRole.REVIEWER}
        )

        assert capabilities.can_handle_role(AgentRole.DEVELOPER) is True
        assert capabilities.can_handle_role(AgentRole.REVIEWER) is True
        assert capabilities.can_handle_role(AgentRole.MANAGER) is False

    def test_expertise_match_score_full_match(self):
        """Test expertise match score with full match."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER,
            expertise_areas={AgentExpertise.BACKEND, AgentExpertise.DATABASE},
        )

        required = {AgentExpertise.BACKEND, AgentExpertise.DATABASE}
        assert capabilities.expertise_match_score(required) == 1.0

    def test_expertise_match_score_partial_match(self):
        """Test expertise match score with partial match."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER,
            expertise_areas={AgentExpertise.BACKEND, AgentExpertise.DATABASE},
        )

        required = {
            AgentExpertise.BACKEND,
            AgentExpertise.FRONTEND,
            AgentExpertise.CLOUD,
        }
        score = capabilities.expertise_match_score(required)
        assert abs(score - 1 / 3) < 0.001  # 1 out of 3 matches

    def test_expertise_match_score_no_requirements(self):
        """Test expertise match score with no requirements."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, expertise_areas={AgentExpertise.BACKEND}
        )

        assert capabilities.expertise_match_score(set()) == 1.0

    def test_skill_match_score_exact_match(self):
        """Test skill match score with exact skill levels."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, skill_levels={"python": 0.9, "sql": 0.8}
        )

        required = {"python": 0.9, "sql": 0.8}
        assert capabilities.skill_match_score(required) == 1.0

    def test_skill_match_score_exceeds_requirements(self):
        """Test skill match score when agent exceeds requirements."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, skill_levels={"python": 0.9, "sql": 0.8}
        )

        required = {"python": 0.7, "sql": 0.6}
        assert capabilities.skill_match_score(required) == 1.0

    def test_skill_match_score_below_requirements(self):
        """Test skill match score when agent is below requirements."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, skill_levels={"python": 0.6, "sql": 0.4}
        )

        required = {"python": 0.8, "sql": 0.8}
        score = capabilities.skill_match_score(required)
        # (0.6/0.8 + 0.4/0.8) / 2 = (0.75 + 0.5) / 2 = 0.625
        assert abs(score - 0.625) < 0.001

    def test_skill_match_score_missing_skills(self):
        """Test skill match score when agent lacks required skills."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, skill_levels={"python": 0.9}
        )

        required = {"python": 0.8, "java": 0.7}
        score = capabilities.skill_match_score(required)
        # (1.0 + 0.0/0.7) / 2 = 0.5
        assert score == 0.5

    def test_skill_match_score_no_requirements(self):
        """Test skill match score with no requirements."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, skill_levels={"python": 0.9}
        )

        assert capabilities.skill_match_score({}) == 1.0


class TestAgentProfile:
    """Test cases for AgentProfile value object."""

    def test_create_agent_profile(self):
        """Test creating agent profile with valid data."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER, expertise_areas={AgentExpertise.BACKEND}
        )

        profile = AgentProfile(
            agent_id="agent-123",
            display_name="Backend Developer",
            capabilities=capabilities,
            availability_score=0.8,
            performance_score=0.95,
            collaboration_style="collaborative",
            communication_preferences={"async", "broadcast"},
            time_zone="UTC",
            working_hours={"start": "09:00", "end": "17:00"},
        )

        assert profile.agent_id == "agent-123"
        assert profile.display_name == "Backend Developer"
        assert profile.capabilities == capabilities
        assert profile.availability_score == 0.8
        assert profile.performance_score == 0.95
        assert profile.collaboration_style == "collaborative"
        assert "async" in profile.communication_preferences
        assert profile.time_zone == "UTC"
        assert profile.working_hours["start"] == "09:00"

    def test_overall_suitability_score_perfect_match(self):
        """Test suitability score calculation for perfect match."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER,
            expertise_areas={AgentExpertise.BACKEND},
            skill_levels={"python": 0.9},
        )

        profile = AgentProfile(
            agent_id="agent-123",
            display_name="Backend Developer",
            capabilities=capabilities,
            availability_score=1.0,
            performance_score=1.0,
        )

        requirements = {
            "role": AgentRole.DEVELOPER,
            "expertise": [AgentExpertise.BACKEND],
            "skills": {"python": 0.8},
        }

        score = profile.overall_suitability_score(requirements)
        # role: 1.0 * 0.4 + expertise: 1.0 * 0.3 + skills: 1.0 * 0.3 = 1.0
        # Final: 1.0 * 1.0 * 1.0 = 1.0
        assert score == 1.0

    def test_overall_suitability_score_with_modifiers(self):
        """Test suitability score with availability and performance modifiers."""
        capabilities = AgentCapabilities(
            primary_role=AgentRole.DEVELOPER,
            expertise_areas={AgentExpertise.BACKEND},
            skill_levels={"python": 0.9},
        )

        profile = AgentProfile(
            agent_id="agent-123",
            display_name="Backend Developer",
            capabilities=capabilities,
            availability_score=0.5,
            performance_score=0.8,
        )

        requirements = {
            "role": AgentRole.DEVELOPER,
            "expertise": [AgentExpertise.BACKEND],
            "skills": {"python": 0.8},
        }

        score = profile.overall_suitability_score(requirements)
        # Base: 1.0, Final: 1.0 * 0.5 * 0.8 = 0.4
        assert score == 0.4

    def test_overall_suitability_score_wrong_role(self):
        """Test suitability score when role doesn't match."""
        capabilities = AgentCapabilities(primary_role=AgentRole.DEVELOPER)

        profile = AgentProfile(
            agent_id="agent-123", display_name="Developer", capabilities=capabilities
        )

        requirements = {"role": AgentRole.MANAGER}

        score = profile.overall_suitability_score(requirements)
        # role: 0.0 * 0.4 + expertise: 1.0 * 0.3 + skills: 1.0 * 0.3 = 0.6
        assert score == 0.6

    def test_overall_suitability_score_no_requirements(self):
        """Test suitability score with no specific requirements."""
        capabilities = AgentCapabilities(primary_role=AgentRole.DEVELOPER)

        profile = AgentProfile(
            agent_id="agent-123", display_name="Developer", capabilities=capabilities
        )

        score = profile.overall_suitability_score({})
        # All components default to 1.0
        assert score == 1.0


class TestAgentStatus:
    """Test cases for AgentStatus value object."""

    def test_create_agent_status(self):
        """Test creating agent status with valid data."""
        now = datetime.now(UTC)
        status = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=3,
            max_workload=5,
            active_tasks=["task-1", "task-2", "task-3"],
            last_activity=now,
            status_message="Working on critical tasks",
            estimated_availability=now,
        )

        assert status.agent_id == "agent-123"
        assert status.is_available is True
        assert status.current_workload == 3
        assert status.max_workload == 5
        assert len(status.active_tasks) == 3
        assert status.last_activity == now
        assert status.status_message == "Working on critical tasks"

    def test_workload_percentage(self):
        """Test workload percentage calculation."""
        status = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=3,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status.workload_percentage == 60.0

    def test_workload_percentage_zero_max(self):
        """Test workload percentage when max workload is zero."""
        status = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=0,
            max_workload=0,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status.workload_percentage == 0.0

    def test_can_accept_work(self):
        """Test work acceptance check."""
        status_available = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=3,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status_available.can_accept_work is True

        status_full = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=5,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status_full.can_accept_work is False

        status_unavailable = AgentStatus(
            agent_id="agent-123",
            is_available=False,
            current_workload=0,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status_unavailable.can_accept_work is False

    def test_capacity_score(self):
        """Test capacity score calculation."""
        status = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=2,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        # (5-2)/5 = 0.6
        assert status.capacity_score() == 0.6

    def test_capacity_score_unavailable(self):
        """Test capacity score when unavailable."""
        status = AgentStatus(
            agent_id="agent-123",
            is_available=False,
            current_workload=0,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status.capacity_score() == 0.0

    def test_capacity_score_zero_max_workload(self):
        """Test capacity score with zero max workload."""
        status = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=0,
            max_workload=0,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        assert status.capacity_score() == 0.0


class TestAgentPerformanceMetrics:
    """Test cases for AgentPerformanceMetrics value object."""

    def test_create_performance_metrics(self):
        """Test creating performance metrics with default values."""
        metrics = AgentPerformanceMetrics(agent_id="agent-123")

        assert metrics.agent_id == "agent-123"
        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 0
        assert metrics.average_completion_time == 0.0
        assert metrics.quality_score == 1.0
        assert metrics.collaboration_score == 1.0
        assert metrics.reliability_score == 1.0
        assert len(metrics.feedback_scores) == 0

    def test_success_rate_with_tasks(self):
        """Test success rate calculation with completed tasks."""
        metrics = AgentPerformanceMetrics(
            agent_id="agent-123", tasks_completed=8, tasks_failed=2
        )

        assert metrics.success_rate == 0.8

    def test_success_rate_no_tasks(self):
        """Test success rate with no tasks."""
        metrics = AgentPerformanceMetrics(agent_id="agent-123")
        assert metrics.success_rate == 1.0

    def test_overall_performance_score(self):
        """Test overall performance score calculation."""
        metrics = AgentPerformanceMetrics(
            agent_id="agent-123",
            tasks_completed=9,
            tasks_failed=1,
            quality_score=0.8,
            collaboration_score=0.9,
            reliability_score=0.85,
        )

        # success_rate: 0.9 * 0.3 = 0.27
        # quality: 0.8 * 0.3 = 0.24
        # collaboration: 0.9 * 0.2 = 0.18
        # reliability: 0.85 * 0.2 = 0.17
        # Total: 0.86
        assert abs(metrics.overall_performance_score - 0.86) < 0.001

    def test_update_with_successful_task(self):
        """Test updating metrics with successful task."""
        metrics = AgentPerformanceMetrics(
            agent_id="agent-123", tasks_completed=2, average_completion_time=4.0
        )

        metrics.update_with_task_result(
            success=True, completion_time=6.0, quality_rating=0.9
        )

        assert metrics.tasks_completed == 3
        assert metrics.tasks_failed == 0
        # (4.0 * 2 + 6.0) / 3 = 14/3 ≈ 4.67
        assert abs(metrics.average_completion_time - 14 / 3) < 0.001
        assert len(metrics.feedback_scores) == 1
        assert metrics.feedback_scores[0] == 0.9
        assert metrics.quality_score == 0.9

    def test_update_with_failed_task(self):
        """Test updating metrics with failed task."""
        metrics = AgentPerformanceMetrics(
            agent_id="agent-123", tasks_failed=1, average_completion_time=5.0
        )

        metrics.update_with_task_result(success=False, completion_time=3.0)

        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 2
        # (5.0 * 1 + 3.0) / 2 = 4.0
        assert metrics.average_completion_time == 4.0

    def test_quality_score_with_multiple_ratings(self):
        """Test quality score calculation with multiple ratings."""
        metrics = AgentPerformanceMetrics(agent_id="agent-123")

        # Add 15 ratings to test the "last 10" logic
        for i in range(15):
            rating = 0.5 if i < 5 else 0.9  # First 5 are 0.5, rest are 0.9
            metrics.update_with_task_result(
                success=True, completion_time=1.0, quality_rating=rating
            )

        # Should use only last 10 ratings (all 0.9)
        assert metrics.quality_score == 0.9
        assert len(metrics.feedback_scores) == 15
        assert metrics.tasks_completed == 15

    def test_frozen_dataclasses(self):
        """Test that frozen dataclasses are immutable."""
        capabilities = AgentCapabilities(primary_role=AgentRole.DEVELOPER)

        with pytest.raises(AttributeError):
            capabilities.primary_role = AgentRole.TESTER

        profile = AgentProfile(
            agent_id="agent-123", display_name="Developer", capabilities=capabilities
        )

        with pytest.raises(AttributeError):
            profile.agent_id = "agent-456"

        status = AgentStatus(
            agent_id="agent-123",
            is_available=True,
            current_workload=0,
            max_workload=5,
            active_tasks=[],
            last_activity=datetime.now(UTC),
        )

        with pytest.raises(AttributeError):
            status.is_available = False
