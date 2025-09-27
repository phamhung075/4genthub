"""Unit tests for Orchestrator Domain Service"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict
import logging

from fastmcp.task_management.domain.services.orchestrator import (
    Orchestrator, CapabilityBasedStrategy, OrchestrationStrategy
)
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.agent import Agent, AgentCapability, AgentStatus
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.work_session import WorkSession
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.priority import PriorityLevel


class TestCapabilityBasedStrategy:
    
    @pytest.fixture
    def strategy(self):
        return CapabilityBasedStrategy()
    
    @pytest.fixture
    def mock_project(self):
        project = Mock(spec=Project)
        project.git_branchs = {}
        project.agent_assignments = {}
        return project
    
    @pytest.fixture
    def mock_agent(self):
        agent = Mock(spec=Agent)
        agent.id = "agent-123"
        agent.is_available.return_value = True
        agent.has_capability = Mock(return_value=True)
        agent.preferred_languages = ["python", "javascript"]
        agent.get_workload_percentage.return_value = 20.0
        return agent
    
    @pytest.fixture
    def mock_git_branch(self):
        branch = Mock(spec=GitBranch)
        branch.id = "branch-123"
        
        # Create mock tasks
        task1 = Mock(spec=Task)
        task1.title = "Frontend UI development"
        task1.description = "Build React components"
        
        task2 = Mock(spec=Task)
        task2.title = "Backend API development"
        task2.description = "Create REST endpoints"
        
        branch.all_tasks = {
            "task1": task1,
            "task2": task2
        }
        return branch
    
    def test_assign_work_no_branches(self, strategy, mock_project):
        """Test work assignment with no branches"""
        available_agents = []
        assignments = strategy.assign_work(mock_project, available_agents)
        assert assignments == {}
    
    def test_assign_work_already_assigned(self, strategy, mock_project, mock_git_branch):
        """Test skipping already assigned branches"""
        mock_project.git_branchs = {"branch1": mock_git_branch}
        mock_project.agent_assignments = {"branch1": "agent-456"}
        
        assignments = strategy.assign_work(mock_project, [])
        assert assignments == {}
    
    def test_assign_work_success(self, strategy, mock_project, mock_git_branch, mock_agent):
        """Test successful work assignment"""
        mock_project.git_branchs = {"branch1": mock_git_branch}
        
        assignments = strategy.assign_work(mock_project, [mock_agent])
        assert assignments == {"branch1": "agent-123"}
    
    def test_find_best_agent_for_tree_no_available(self, strategy, mock_git_branch, mock_agent):
        """Test finding best agent when none available"""
        mock_agent.is_available.return_value = False
        result = strategy._find_best_agent_for_tree(mock_git_branch, [mock_agent])
        assert result is None
    
    def test_find_best_agent_for_tree_multiple_agents(self, strategy, mock_git_branch):
        """Test finding best agent among multiple options"""
        # Create agents with different scores
        agent1 = Mock(spec=Agent)
        agent1.id = "agent-1"
        agent1.is_available.return_value = True
        agent1.has_capability = Mock(return_value=True)
        agent1.preferred_languages = ["python"]
        agent1.get_workload_percentage.return_value = 50.0
        
        agent2 = Mock(spec=Agent)
        agent2.id = "agent-2"
        agent2.is_available.return_value = True
        agent2.has_capability = Mock(return_value=True)
        agent2.preferred_languages = ["javascript", "python"]
        agent2.get_workload_percentage.return_value = 20.0
        
        result = strategy._find_best_agent_for_tree(mock_git_branch, [agent1, agent2])
        # Agent2 should win due to lower workload and more language matches
        assert result == agent2
    
    def test_calculate_agent_tree_score_full_match(self, strategy, mock_agent, mock_git_branch):
        """Test score calculation with full capability match"""
        score = strategy._calculate_agent_tree_score(mock_agent, mock_git_branch)
        # Base (50) + capability match + language match + low workload
        assert score > 50.0
    
    def test_calculate_agent_tree_score_no_capabilities(self, strategy, mock_agent, mock_git_branch):
        """Test score calculation with no capability match"""
        mock_agent.has_capability.return_value = False
        score = strategy._calculate_agent_tree_score(mock_agent, mock_git_branch)
        # Should still have base score and workload bonus
        assert score >= 50.0
    
    def test_analyze_tree_requirements_frontend(self, strategy):
        """Test analyzing tree requirements for frontend work"""
        branch = Mock(spec=GitBranch)
        
        task = Mock(spec=Task)
        task.title = "Build React components"
        task.description = "Frontend UI development"
        branch.all_tasks = {"task1": task}
        
        requirements = strategy._analyze_tree_requirements(branch)
        
        assert AgentCapability.FRONTEND_DEVELOPMENT in requirements["capabilities"]
        assert "javascript" in requirements["languages"]
        assert "typescript" in requirements["languages"]
    
    def test_analyze_tree_requirements_backend(self, strategy):
        """Test analyzing tree requirements for backend work"""
        branch = Mock(spec=GitBranch)
        
        task = Mock(spec=Task)
        task.title = "Build API server"
        task.description = "Backend database integration"
        branch.all_tasks = {"task1": task}
        
        requirements = strategy._analyze_tree_requirements(branch)
        
        assert AgentCapability.BACKEND_DEVELOPMENT in requirements["capabilities"]
        assert "python" in requirements["languages"]
    
    def test_analyze_tree_requirements_devops(self, strategy):
        """Test analyzing tree requirements for DevOps work"""
        branch = Mock(spec=GitBranch)
        
        task = Mock(spec=Task)
        task.title = "Deploy to kubernetes"
        task.description = "Set up CI/CD pipeline"
        branch.all_tasks = {"task1": task}
        
        requirements = strategy._analyze_tree_requirements(branch)
        
        assert AgentCapability.DEVOPS in requirements["capabilities"]
    
    def test_analyze_tree_requirements_testing(self, strategy):
        """Test analyzing tree requirements for testing work"""
        branch = Mock(spec=GitBranch)
        
        task = Mock(spec=Task)
        task.title = "Write unit tests"
        task.description = "QA testing for quality assurance"
        branch.all_tasks = {"task1": task}
        
        requirements = strategy._analyze_tree_requirements(branch)
        
        assert AgentCapability.TESTING in requirements["capabilities"]


class TestOrchestrator:
    
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()
    
    @pytest.fixture
    def mock_project(self):
        project = Mock(spec=Project)
        project.id = "proj-123"
        project.git_branchs = {}
        project.agent_assignments = {}
        project.registered_agents = {}
        project.active_work_sessions = {}
        project.cross_tree_dependencies = {}
        project.assign_agent_to_tree = Mock()
        project.get_available_work_for_agent = Mock(return_value=[])
        project._find_git_branch = Mock(return_value=None)
        return project
    
    @pytest.fixture
    def mock_agent(self):
        agent = Mock(spec=Agent)
        agent.id = "agent-123"
        agent.status = AgentStatus.AVAILABLE
        agent.is_available.return_value = True
        agent.active_tasks = []
        return agent
    
    @pytest.fixture
    def mock_work_session(self):
        session = Mock(spec=WorkSession)
        session.id = "session-123"
        session.agent_id = "agent-123"
        session.task_id = "task-123"
        session.is_timeout_due.return_value = False
        session.resources_locked = []
        session.timeout_session = Mock()
        return session
    
    def test_orchestrate_project_basic(self, orchestrator, mock_project, mock_agent):
        """Test basic project orchestration"""
        mock_project.registered_agents = {"agent-123": mock_agent}
        
        with patch('fastmcp.task_management.domain.services.orchestrator.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            result = orchestrator.orchestrate_project(mock_project)
        
        assert result["project_id"] == "proj-123"
        assert result["orchestration_timestamp"] == "2024-01-01T12:00:00"
        assert result["new_assignments"] == {}
        assert result["agent_recommendations"] == {}
        assert result["conflicts_detected"] == 0
        assert result["active_sessions"] == 0
        assert result["available_agents"] == 1
    
    def test_orchestrate_project_with_offline_agents(self, orchestrator, mock_project):
        """Test orchestration filters offline agents"""
        offline_agent = Mock(spec=Agent)
        offline_agent.id = "agent-offline"
        offline_agent.status = AgentStatus.OFFLINE
        
        online_agent = Mock(spec=Agent)
        online_agent.id = "agent-online"
        online_agent.status = AgentStatus.AVAILABLE
        online_agent.is_available.return_value = True
        
        mock_project.registered_agents = {
            "agent-offline": offline_agent,
            "agent-online": online_agent
        }
        
        result = orchestrator.orchestrate_project(mock_project)
        assert result["available_agents"] == 1
    
    def test_orchestrate_project_with_new_assignments(self, orchestrator, mock_project, mock_agent):
        """Test orchestration with new work assignments"""
        mock_project.registered_agents = {"agent-123": mock_agent}
        
        # Mock strategy to return assignments
        mock_strategy = Mock()
        mock_strategy.assign_work.return_value = {"branch-1": "agent-123"}
        orchestrator.strategy = mock_strategy
        
        result = orchestrator.orchestrate_project(mock_project)
        
        assert result["new_assignments"] == {"branch-1": "agent-123"}
        mock_project.assign_agent_to_tree.assert_called_once_with("agent-123", "branch-1")
    
    def test_orchestrate_project_with_recommendations(self, orchestrator, mock_project, mock_agent):
        """Test orchestration with task recommendations"""
        task = Mock(spec=Task)
        task.id = Mock()
        task.id.value = "task-123"
        task.created_at = datetime.now(timezone.utc) - timedelta(days=1)  # Add proper datetime
        task.priority = Mock()
        task.priority.value = PriorityLevel.MEDIUM.label
        
        mock_project.registered_agents = {"agent-123": mock_agent}
        mock_project.get_available_work_for_agent.return_value = [task]
        
        result = orchestrator.orchestrate_project(mock_project)
        
        assert result["agent_recommendations"] == {"agent-123": "task-123"}
    
    def test_handle_timeout_sessions(self, orchestrator, mock_project, mock_work_session, mock_agent):
        """Test handling of timed out sessions"""
        mock_work_session.is_timeout_due.return_value = True
        mock_project.active_work_sessions = {"session-123": mock_work_session}
        mock_project.registered_agents = {"agent-123": mock_agent}
        
        orchestrator._handle_timeout_sessions(mock_project)
        
        mock_work_session.timeout_session.assert_called_once()
        assert "session-123" not in mock_project.active_work_sessions
        mock_agent.complete_task.assert_called_once_with("task-123", success=False)
    
    def test_detect_conflicts_resource_conflict(self, orchestrator, mock_project):
        """Test detection of resource conflicts"""
        session1 = Mock(spec=WorkSession)
        session1.id = "session-1"
        session1.resources_locked = ["resource-A", "resource-B"]
        
        session2 = Mock(spec=WorkSession)
        session2.id = "session-2"
        session2.resources_locked = ["resource-B", "resource-C"]
        
        mock_project.active_work_sessions = {
            "session-1": session1,
            "session-2": session2
        }
        
        conflicts = orchestrator._detect_conflicts(mock_project)
        
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "resource_conflict"
        assert conflicts[0]["resource"] == "resource-B"
        assert set(conflicts[0]["conflicting_sessions"]) == {"session-1", "session-2"}
    
    def test_resolve_conflicts_resource(self, orchestrator, mock_project):
        """Test resolution of resource conflicts"""
        older_session = Mock(spec=WorkSession)
        older_session.unlock_resource = Mock()
        
        mock_project.active_work_sessions = {"session-1": older_session}
        
        conflicts = [{
            "type": "resource_conflict",
            "resource": "resource-A",
            "conflicting_sessions": ["session-1", "session-2"]
        }]
        
        orchestrator._resolve_conflicts(mock_project, conflicts)
        
        older_session.unlock_resource.assert_called_once_with("resource-A")
    
    def test_coordinate_cross_tree_dependencies_missing(self, orchestrator, mock_project):
        """Test coordination with missing prerequisite"""
        mock_project.cross_tree_dependencies = {
            "task-1": ["task-2"]
        }
        mock_project._find_git_branch.side_effect = [Mock(), None]  # First found, second missing
        
        issues = orchestrator.coordinate_cross_tree_dependencies(mock_project)
        
        assert len(issues) == 1
        assert issues[0]["type"] == "missing_prerequisite"
        assert issues[0]["dependent_task"] == "task-1"
        assert issues[0]["missing_prerequisite"] == "task-2"
    
    def test_coordinate_cross_tree_dependencies_not_active(self, orchestrator, mock_project, mock_agent):
        """Test coordination with prerequisite not being worked on"""
        prerequisite_task = Mock(spec=Task)
        prerequisite_task.status = Mock()
        prerequisite_task.status.is_done.return_value = False
        
        prerequisite_tree = Mock(spec=GitBranch)
        prerequisite_tree.id = "tree-2"
        prerequisite_tree.get_task.return_value = prerequisite_task
        
        dependent_tree = Mock(spec=GitBranch)
        
        mock_project.cross_tree_dependencies = {
            "task-1": ["task-2"]
        }
        mock_project._find_git_branch.side_effect = [dependent_tree, prerequisite_tree]
        mock_project.agent_assignments = {"tree-2": "agent-123"}
        mock_project.registered_agents = {"agent-123": mock_agent}
        mock_agent.active_tasks = []  # Prerequisite not in active tasks
        
        issues = orchestrator.coordinate_cross_tree_dependencies(mock_project)
        
        assert len(issues) == 1
        assert issues[0]["type"] == "prerequisite_not_active"
        assert issues[0]["recommendation"] == "prioritize_prerequisite"
    
    def test_balance_workload_identifies_overloaded(self, orchestrator, mock_project):
        """Test workload balancing identifies overloaded agents"""
        agent1 = Mock(spec=Agent)
        agent1.id = "agent-1"
        agent1.get_workload_percentage.return_value = 85.0
        agent1.active_tasks = ["task-1"]
        
        agent2 = Mock(spec=Agent)
        agent2.id = "agent-2"
        agent2.get_workload_percentage.return_value = 30.0
        
        mock_project.registered_agents = {
            "agent-1": agent1,
            "agent-2": agent2
        }
        
        result = orchestrator.balance_workload(mock_project)
        
        assert result["workload_analysis"]["overloaded_agents"] == ["agent-1"]
        assert result["workload_analysis"]["underloaded_agents"] == ["agent-2"]
        assert result["workload_analysis"]["average_workload"] == 57.5
    
    def test_balance_workload_recommends_reassignment(self, orchestrator, mock_project):
        """Test workload balancing recommends task reassignment"""
        task = Mock(spec=Task)
        git_branch = Mock(spec=GitBranch)
        git_branch.id = "branch-1"
        git_branch.get_task.return_value = task
        
        overloaded_agent = Mock(spec=Agent)
        overloaded_agent.id = "agent-overloaded"
        overloaded_agent.get_workload_percentage.return_value = 85.0
        overloaded_agent.active_tasks = ["task-1"]
        
        underloaded_agent = Mock(spec=Agent)
        underloaded_agent.id = "agent-underloaded"
        underloaded_agent.get_workload_percentage.return_value = 30.0
        
        mock_project.registered_agents = {
            "agent-overloaded": overloaded_agent,
            "agent-underloaded": underloaded_agent
        }
        mock_project._find_git_branch.return_value = git_branch
        
        # Mock can_agent_handle_task to return True
        with patch.object(orchestrator, '_can_agent_handle_task', return_value=True):
            result = orchestrator.balance_workload(mock_project)
        
        recommendations = result["rebalancing_recommendations"]
        assert len(recommendations) == 1
        assert recommendations[0]["type"] == "reassign_task"
        assert recommendations[0]["from_agent"] == "agent-overloaded"
        assert recommendations[0]["to_agent"] == "agent-underloaded"
    
    def test_prioritize_tasks_for_agent_empty_list(self, orchestrator, mock_agent):
        """Test task prioritization with empty task list"""
        result = orchestrator._prioritize_tasks_for_agent(mock_agent, [])
        assert result is None
    
    def test_prioritize_tasks_for_agent_by_priority(self, orchestrator, mock_agent):
        """Test task prioritization by priority level"""
        mock_agent.priority_preference = PriorityLevel.HIGH.label
        
        critical_task = Mock(spec=Task)
        critical_task.priority = Mock()
        critical_task.priority.value = PriorityLevel.CRITICAL.label
        critical_task.priority.label = PriorityLevel.CRITICAL.label
        critical_task.created_at = datetime.now(timezone.utc)
        
        medium_task = Mock(spec=Task)
        medium_task.priority = Mock()
        medium_task.priority.value = PriorityLevel.MEDIUM.label
        medium_task.priority.label = PriorityLevel.MEDIUM.label
        medium_task.created_at = datetime.now(timezone.utc)
        
        tasks = [medium_task, critical_task]
        result = orchestrator._prioritize_tasks_for_agent(mock_agent, tasks)
        
        # Critical task should be selected
        assert result == critical_task
    
    def test_prioritize_tasks_for_agent_by_age(self, orchestrator, mock_agent):
        """Test task prioritization considers task age"""
        mock_agent.priority_preference = PriorityLevel.MEDIUM.label
        
        old_task = Mock(spec=Task)
        old_task.priority = Mock()
        old_task.priority.value = PriorityLevel.MEDIUM.label
        old_task.created_at = datetime.now(timezone.utc) - timedelta(days=10)
        
        new_task = Mock(spec=Task)
        new_task.priority = Mock()
        new_task.priority.value = PriorityLevel.MEDIUM.label
        new_task.created_at = datetime.now(timezone.utc)
        
        tasks = [new_task, old_task]
        result = orchestrator._prioritize_tasks_for_agent(mock_agent, tasks)
        
        # Older task should get slight priority
        assert result == old_task
    
    def test_can_agent_handle_task_frontend(self, orchestrator, mock_agent):
        """Test agent capability check for frontend tasks"""
        task = Mock(spec=Task)
        task.title = "Build React UI"
        task.description = "Frontend components"
        
        mock_agent.has_capability.return_value = True
        result = orchestrator._can_agent_handle_task(mock_agent, task)
        
        assert result is True
        mock_agent.has_capability.assert_called_with(AgentCapability.FRONTEND_DEVELOPMENT)
    
    def test_can_agent_handle_task_backend(self, orchestrator, mock_agent):
        """Test agent capability check for backend tasks"""
        task = Mock(spec=Task)
        task.title = "Create API endpoints"
        task.description = "Backend server development"
        
        mock_agent.has_capability.return_value = True
        result = orchestrator._can_agent_handle_task(mock_agent, task)
        
        assert result is True
        mock_agent.has_capability.assert_called_with(AgentCapability.BACKEND_DEVELOPMENT)
    
    def test_can_agent_handle_task_general(self, orchestrator, mock_agent):
        """Test agent can handle general tasks"""
        task = Mock(spec=Task)
        task.title = "General task"
        task.description = "Some general work"
        
        result = orchestrator._can_agent_handle_task(mock_agent, task)
        
        # Should return True for general tasks
        assert result is True