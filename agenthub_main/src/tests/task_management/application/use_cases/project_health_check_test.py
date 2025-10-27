"""
Test suite for ProjectHealthCheck use case

Tests the business logic for checking project health and integrity.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastmcp.task_management.application.use_cases.project_health_check import ProjectHealthCheckUseCase
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects import (
    ProjectID,
    GitBranchID,
    GitBranchName,
    TaskID,
    TaskTitle,
    TaskStatus,
    TaskPriority,
    UserID
)
from fastmcp.task_management.domain.exceptions import ProjectNotFoundError


class TestProjectHealthCheckUseCase:
    """Test suite for ProjectHealthCheck use case"""

    @pytest.fixture
    def mock_project_repo(self):
        """Create mock project repository"""
        return Mock()

    @pytest.fixture
    def mock_git_branch_repo(self):
        """Create mock git branch repository"""
        return Mock()

    @pytest.fixture
    def mock_task_repo(self):
        """Create mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_health_analyzer(self):
        """Create mock health analyzer service"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer):
        """Create use case instance with mocks"""
        return ProjectHealthCheckUseCase(
            project_repository=mock_project_repo,
            git_branch_repository=mock_git_branch_repo,
            task_repository=mock_task_repo,
            health_analyzer=mock_health_analyzer
        )

    @pytest.fixture
    def sample_project(self):
        """Create sample project"""
        project = Project(
            id=ProjectID(str(uuid4())),
            name="E-commerce Platform",
            description="Full-stack e-commerce solution",
            user_id=UserID("user123")
        )
        project.created_at = datetime.now(timezone.utc) - timedelta(days=90)
        project.updated_at = datetime.now(timezone.utc) - timedelta(days=1)
        return project

    @pytest.fixture
    def sample_branches(self, sample_project):
        """Create sample git branches"""
        branches = []
        
        # Active branch
        b1 = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=sample_project.id,
            git_branch_name=GitBranchName("feature/payment-integration"),
            user_id=UserID("user123")
        )
        b1.is_active = True
        branches.append(b1)
        
        # Stale branch
        b2 = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=sample_project.id,
            git_branch_name=GitBranchName("feature/old-feature"),
            user_id=UserID("user123")
        )
        b2.is_active = True
        b2.updated_at = datetime.now(timezone.utc) - timedelta(days=45)  # Stale
        branches.append(b2)
        
        # Archived branch
        b3 = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=sample_project.id,
            git_branch_name=GitBranchName("feature/completed"),
            user_id=UserID("user123")
        )
        b3.is_active = False
        branches.append(b3)
        
        return branches

    @pytest.fixture
    def sample_tasks(self, sample_branches):
        """Create sample tasks across branches"""
        tasks = []
        
        # Tasks for active branch
        for i in range(5):
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_branches[0].id,
                title=TaskTitle(f"Payment task {i}"),
                status=TaskStatus.IN_PROGRESS if i < 2 else TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")],
                labels=["payment"]
            )
            tasks.append(task)
        
        # Blocked tasks
        blocked_task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=sample_branches[0].id,
            title=TaskTitle("Blocked payment validation"),
            status=TaskStatus.BLOCKED,
            priority=TaskPriority.URGENT,
            assignees=[UserID("user123")],
            labels=["payment"],
            blocked_reason="Waiting for API documentation",
            blocked_at=datetime.now(timezone.utc) - timedelta(days=7)
        )
        tasks.append(blocked_task)
        
        # Overdue task
        overdue_task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=sample_branches[0].id,
            title=TaskTitle("Overdue security audit"),
            status=TaskStatus.TODO,
            priority=TaskPriority.CRITICAL,
            assignees=[UserID("user123")],
            labels=["security"],
            due_date=datetime.now(timezone.utc) - timedelta(days=3)  # Overdue
        )
        tasks.append(overdue_task)
        
        return tasks

    def test_project_health_check_success(self, use_case, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer, sample_project, sample_branches, sample_tasks):
        """Test successful project health check"""
        # Arrange
        project_id = sample_project.id.value
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_project_id.return_value = sample_branches
        mock_task_repo.get_by_project_id.return_value = sample_tasks
        
        health_metrics = {
            'overall_health': 'good',
            'health_score': 75,
            'issues': [
                {'type': 'blocked_tasks', 'severity': 'medium', 'count': 1},
                {'type': 'stale_branch', 'severity': 'low', 'branch': 'feature/old-feature'},
                {'type': 'overdue_task', 'severity': 'high', 'task': 'Overdue security audit'}
            ],
            'recommendations': [
                'Resolve blocked tasks to improve flow',
                'Archive or update stale branches',
                'Address overdue critical tasks immediately'
            ]
        }
        mock_health_analyzer.analyze_project_health.return_value = health_metrics
        
        # Act
        result = use_case.execute(project_id=project_id)
        
        # Assert
        assert result['overall_health'] == 'good'
        assert result['health_score'] == 75
        assert len(result['issues']) == 3
        assert len(result['recommendations']) == 3
        
        # Verify service calls
        mock_project_repo.get_by_id.assert_called_once_with(ProjectID(project_id))
        mock_git_branch_repo.get_by_project_id.assert_called_once_with(sample_project.id)
        mock_task_repo.get_by_project_id.assert_called_once_with(sample_project.id)
        mock_health_analyzer.analyze_project_health.assert_called_once()

    def test_project_health_check_not_found(self, use_case, mock_project_repo):
        """Test health check for non-existent project"""
        # Arrange
        project_id = str(uuid4())
        
        mock_project_repo.get_by_id.side_effect = ProjectNotFoundError(f"Project {project_id} not found")
        
        # Act & Assert
        with pytest.raises(ProjectNotFoundError):
            use_case.execute(project_id=project_id)

    def test_project_health_check_perfect_health(self, use_case, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer, sample_project):
        """Test project with perfect health"""
        # Arrange
        project_id = sample_project.id.value
        
        # Healthy project setup
        healthy_branches = [
            GitBranch(
                id=GitBranchID(str(uuid4())),
                project_id=sample_project.id,
                git_branch_name=GitBranchName("main"),
                user_id=UserID("user123")
            )
        ]
        
        healthy_tasks = [
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=healthy_branches[0].id,
                title=TaskTitle("Completed task"),
                status=TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")],
                labels=[],
                progress_percentage=100
            )
            for _ in range(10)
        ]
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_project_id.return_value = healthy_branches
        mock_task_repo.get_by_project_id.return_value = healthy_tasks
        
        health_metrics = {
            'overall_health': 'excellent',
            'health_score': 100,
            'issues': [],
            'recommendations': ['Keep up the excellent work!']
        }
        mock_health_analyzer.analyze_project_health.return_value = health_metrics
        
        # Act
        result = use_case.execute(project_id=project_id)
        
        # Assert
        assert result['overall_health'] == 'excellent'
        assert result['health_score'] == 100
        assert len(result['issues']) == 0

    def test_project_health_check_critical_issues(self, use_case, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer, sample_project):
        """Test project with critical health issues"""
        # Arrange
        project_id = sample_project.id.value
        
        # Create problematic tasks
        problem_tasks = []
        
        # Many blocked tasks
        for i in range(10):
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Blocked task {i}"),
                status=TaskStatus.BLOCKED,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")],
                labels=[],
                blocked_reason="Various blockers",
                blocked_at=datetime.now(timezone.utc) - timedelta(days=14)
            )
            problem_tasks.append(task)
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_project_id.return_value = []
        mock_task_repo.get_by_project_id.return_value = problem_tasks
        
        health_metrics = {
            'overall_health': 'critical',
            'health_score': 20,
            'issues': [
                {'type': 'high_blocked_ratio', 'severity': 'critical', 'ratio': 100},
                {'type': 'long_blocked_tasks', 'severity': 'critical', 'count': 10},
                {'type': 'no_active_branches', 'severity': 'high'}
            ],
            'recommendations': [
                'Urgent: Resolve blocked tasks immediately',
                'Review project workflow and remove impediments',
                'Consider project restructuring or cancellation'
            ]
        }
        mock_health_analyzer.analyze_project_health.return_value = health_metrics
        
        # Act
        result = use_case.execute(project_id=project_id)
        
        # Assert
        assert result['overall_health'] == 'critical'
        assert result['health_score'] == 20
        assert any(issue['severity'] == 'critical' for issue in result['issues'])

    def test_project_health_check_with_metrics(self, use_case, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer, sample_project, sample_branches, sample_tasks):
        """Test health check with detailed metrics"""
        # Arrange
        project_id = sample_project.id.value
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_project_id.return_value = sample_branches
        mock_task_repo.get_by_project_id.return_value = sample_tasks
        
        health_metrics = {
            'overall_health': 'fair',
            'health_score': 65,
            'issues': [],
            'recommendations': [],
            'metrics': {
                'total_tasks': len(sample_tasks),
                'completed_tasks': 0,
                'blocked_tasks': 1,
                'overdue_tasks': 1,
                'active_branches': 2,
                'stale_branches': 1,
                'avg_task_age_days': 15,
                'completion_rate': 0,
                'velocity_trend': 'declining'
            }
        }
        mock_health_analyzer.analyze_project_health.return_value = health_metrics
        
        # Act
        result = use_case.execute(project_id=project_id, include_metrics=True)
        
        # Assert
        assert 'metrics' in result
        assert result['metrics']['total_tasks'] == len(sample_tasks)
        assert result['metrics']['blocked_tasks'] == 1
        assert result['metrics']['overdue_tasks'] == 1
        assert result['metrics']['velocity_trend'] == 'declining'

    def test_project_health_check_task_distribution(self, use_case, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer, sample_project):
        """Test health check analyzes task distribution"""
        # Arrange
        project_id = sample_project.id.value
        branches = [
            GitBranch(
                id=GitBranchID(str(uuid4())),
                project_id=sample_project.id,
                git_branch_name=GitBranchName(f"branch-{i}"),
                user_id=UserID("user123")
            )
            for i in range(3)
        ]
        
        # Uneven task distribution
        tasks = []
        # Branch 0: 20 tasks (overloaded)
        for i in range(20):
            tasks.append(Task(
                id=TaskID(str(uuid4())),
                git_branch_id=branches[0].id,
                title=TaskTitle(f"Task {i}"),
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")],
                labels=[]
            ))
        
        # Branch 1: 1 task (underutilized)
        tasks.append(Task(
            id=TaskID(str(uuid4())),
            git_branch_id=branches[1].id,
            title=TaskTitle("Single task"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")],
            labels=[]
        ))
        
        # Branch 2: 0 tasks (empty)
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_project_id.return_value = branches
        mock_task_repo.get_by_project_id.return_value = tasks
        
        health_metrics = {
            'overall_health': 'warning',
            'health_score': 60,
            'issues': [
                {'type': 'uneven_distribution', 'severity': 'medium', 'details': 'Tasks concentrated in single branch'},
                {'type': 'empty_branch', 'severity': 'low', 'branch': 'branch-2'}
            ],
            'recommendations': [
                'Distribute tasks more evenly across branches',
                'Consider archiving empty branches'
            ]
        }
        mock_health_analyzer.analyze_project_health.return_value = health_metrics
        
        # Act
        result = use_case.execute(project_id=project_id)
        
        # Assert
        assert result['overall_health'] == 'warning'
        assert any(issue['type'] == 'uneven_distribution' for issue in result['issues'])

    def test_project_health_check_assignee_workload(self, use_case, mock_project_repo, mock_git_branch_repo, mock_task_repo, mock_health_analyzer, sample_project):
        """Test health check analyzes assignee workload"""
        # Arrange
        project_id = sample_project.id.value
        
        # Create tasks with uneven assignee distribution
        tasks = []
        # user123: 15 tasks (overloaded)
        for i in range(15):
            tasks.append(Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task for user123 #{i}"),
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")],
                labels=[]
            ))
        
        # user456: 2 tasks (normal)
        for i in range(2):
            tasks.append(Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task for user456 #{i}"),
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user456")],
                labels=[]
            ))
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_project_id.return_value = []
        mock_task_repo.get_by_project_id.return_value = tasks
        
        health_metrics = {
            'overall_health': 'warning',
            'health_score': 70,
            'issues': [
                {'type': 'assignee_overload', 'severity': 'high', 'assignee': 'user123', 'task_count': 15}
            ],
            'recommendations': [
                'Redistribute tasks from overloaded assignees',
                'Consider adding more team members'
            ],
            'assignee_metrics': {
                'user123': {'tasks': 15, 'workload': 'overloaded'},
                'user456': {'tasks': 2, 'workload': 'normal'}
            }
        }
        mock_health_analyzer.analyze_project_health.return_value = health_metrics
        
        # Act
        result = use_case.execute(project_id=project_id)
        
        # Assert
        assert any(issue['type'] == 'assignee_overload' for issue in result['issues'])
        assert 'assignee_metrics' in result