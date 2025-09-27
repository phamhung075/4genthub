"""
Unit tests for WorkflowAnalysisService.

This module tests the workflow analysis, pattern detection, bottleneck identification,
optimization opportunities, and recommendation functionality.
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any, Optional

from fastmcp.task_management.application.services.workflow_analysis_service import (
    WorkflowAnalysisService,
    WorkflowPattern,
    WorkflowAnalysis
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.context import TaskContext
from fastmcp.task_management.domain.value_objects.progress import ProgressType, ProgressStatus


class TestWorkflowPattern:
    """Test suite for WorkflowPattern dataclass"""
    
    def test_workflow_pattern_creation(self):
        """Test creating a WorkflowPattern"""
        task_id = uuid.uuid4()
        pattern = WorkflowPattern(
            pattern_name="test_pattern",
            pattern_type="bottleneck",
            confidence=0.85,
            description="Test pattern description",
            affected_tasks=[task_id],
            recommendations=["Fix this", "Improve that"],
            metrics={"metric1": 1.0, "metric2": "value"}
        )
        
        assert pattern.pattern_name == "test_pattern"
        assert pattern.pattern_type == "bottleneck"
        assert pattern.confidence == 0.85
        assert pattern.description == "Test pattern description"
        assert pattern.affected_tasks == [task_id]
        assert pattern.recommendations == ["Fix this", "Improve that"]
        assert pattern.metrics == {"metric1": 1.0, "metric2": "value"}


class TestWorkflowAnalysis:
    """Test suite for WorkflowAnalysis dataclass"""
    
    def test_workflow_analysis_creation(self):
        """Test creating a WorkflowAnalysis"""
        task_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)
        pattern = WorkflowPattern(
            pattern_name="test",
            pattern_type="optimization",
            confidence=0.8,
            description="Test",
            affected_tasks=[],
            recommendations=[],
            metrics={}
        )
        
        analysis = WorkflowAnalysis(
            task_id=task_id,
            analysis_timestamp=timestamp,
            patterns=[pattern],
            bottlenecks=[{"type": "test_bottleneck"}],
            optimization_opportunities=[{"type": "test_optimization"}],
            predicted_completion_time=timedelta(hours=8),
            risk_factors=["High complexity"],
            success_indicators=["Good progress"]
        )
        
        assert analysis.task_id == task_id
        assert analysis.analysis_timestamp == timestamp
        assert len(analysis.patterns) == 1
        assert analysis.patterns[0] == pattern
        assert len(analysis.bottlenecks) == 1
        assert len(analysis.optimization_opportunities) == 1
        assert analysis.predicted_completion_time == timedelta(hours=8)
        assert analysis.risk_factors == ["High complexity"]
        assert analysis.success_indicators == ["Good progress"]


class TestWorkflowAnalysisServiceInitialization:
    """Test suite for WorkflowAnalysisService initialization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        self.event_store = Mock()
    
    def test_initialization_minimal(self):
        """Test initialization with minimal parameters"""
        service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        assert service.task_repository == self.task_repository
        assert service.context_repository == self.context_repository
        assert service.event_store is None
        assert service._user_id is None
        assert service._analysis_cache == {}
        assert service._pattern_cache == {}
    
    def test_initialization_full(self):
        """Test initialization with all parameters"""
        user_id = "test_user"
        service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store,
            user_id=user_id
        )
        
        assert service.event_store == self.event_store
        assert service._user_id == user_id
    
    def test_with_user_creates_new_instance(self):
        """Test that with_user creates a new service instance"""
        service = WorkflowAnalysisService(self.task_repository, self.context_repository)
        user_id = "new_user"
        
        user_service = service.with_user(user_id)
        
        assert user_service != service
        assert user_service._user_id == user_id
        assert user_service.task_repository == self.task_repository
        assert user_service.context_repository == self.context_repository


class TestUserScopedRepository:
    """Test suite for user-scoped repository functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=Mock(),
            user_id="test_user"
        )
    
    def test_get_user_scoped_repository_with_user_method(self):
        """Test getting user-scoped repository with with_user method"""
        mock_repo = Mock()
        user_scoped_repo = Mock()
        mock_repo.with_user.return_value = user_scoped_repo
        
        result = self.service._get_user_scoped_repository(mock_repo)
        
        assert result == user_scoped_repo
        mock_repo.with_user.assert_called_once_with("test_user")
    
    def test_get_user_scoped_repository_with_user_id_attribute(self):
        """Test getting user-scoped repository with user_id attribute"""
        # Create a mock repository instance with spec to avoid hasattr issues
        mock_repo = Mock(spec=['user_id', 'session'])
        mock_repo.user_id = "different_user"
        mock_repo.session = Mock()
        
        # Create a mock repository class
        MockRepoClass = Mock()
        new_repo = Mock()
        MockRepoClass.return_value = new_repo
        
        # Patch type() to return our mock class
        with patch('builtins.type', return_value=MockRepoClass):
            result = self.service._get_user_scoped_repository(mock_repo)
            
            # Should create new repository with correct user_id
            MockRepoClass.assert_called_once_with(mock_repo.session, user_id="test_user")
            assert result == new_repo
    
    def test_get_user_scoped_repository_no_user_context(self):
        """Test getting user-scoped repository with no user context"""
        service = WorkflowAnalysisService(self.task_repository, Mock())
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        # Should return original repository
        assert result == mock_repo
    
    def test_get_user_scoped_repository_none(self):
        """Test getting user-scoped repository with None"""
        result = self.service._get_user_scoped_repository(None)
        
        assert result is None


class TestWorkflowAnalysis:
    """Test suite for workflow analysis functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        
        self.service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        self.task_id = uuid.uuid4()
        self.task = self._create_mock_task()
        self.context = self._create_mock_context()
    
    def _create_mock_task(self) -> Mock:
        """Create a mock task"""
        task = Mock(spec=Task)
        task.id = self.task_id
        task.status = "in_progress"
        task.priority = "medium"
        task.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        task.labels = ["frontend", "testing"]
        task.subtasks = []
        task.assignees = ["user1"]
        task.dependencies = []
        task.progress = 0.5
        task.estimated_effort = "2d"
        task.progress_breakdown = {"implementation": 0.7, "testing": 0.3}
        task.progress_timeline = [
            {"timestamp": "2024-01-01T10:00:00Z", "status": "advancing"},
            {"timestamp": "2024-01-01T15:00:00Z", "status": "advancing"}
        ]
        return task
    
    def _create_mock_context(self) -> Mock:
        """Create a mock context"""
        context = Mock(spec=TaskContext)
        context.notes = "Task notes with some help needed"
        context.data = {"requirements": ["req1", "req2"]}
        return context
    
    @pytest.mark.asyncio
    async def test_analyze_task_workflow_task_not_found(self):
        """Test workflow analysis when task is not found"""
        self.task_repository.get.return_value = None
        
        with pytest.raises(ValueError, match="Task not found"):
            await self.service.analyze_task_workflow(self.task_id)
    
    @pytest.mark.asyncio
    async def test_analyze_task_workflow_success(self):
        """Test successful workflow analysis"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        # Mock the internal analysis methods
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_detect_patterns', return_value=[]):
                with patch.object(self.service, '_identify_bottlenecks', return_value=[]):
                    with patch.object(self.service, '_find_optimization_opportunities', return_value=[]):
                        with patch.object(self.service, '_predict_completion_time', return_value=timedelta(hours=4)):
                            with patch.object(self.service, '_assess_risk_factors', return_value=["test risk"]):
                                with patch.object(self.service, '_identify_success_indicators', return_value=["test indicator"]):
                                    result = await self.service.analyze_task_workflow(self.task_id)
        
        assert isinstance(result, WorkflowAnalysis)
        assert result.task_id == self.task_id
        assert result.predicted_completion_time == timedelta(hours=4)
        assert result.risk_factors == ["test risk"]
        assert result.success_indicators == ["test indicator"]
    
    @pytest.mark.asyncio
    async def test_analyze_task_workflow_cached(self):
        """Test workflow analysis returns cached result"""
        # Set up cache with recent analysis
        cached_analysis = WorkflowAnalysis(
            task_id=self.task_id,
            analysis_timestamp=datetime.now(timezone.utc) - timedelta(minutes=30),  # Recent
            patterns=[],
            bottlenecks=[],
            optimization_opportunities=[],
            predicted_completion_time=None,
            risk_factors=[],
            success_indicators=[]
        )
        self.service._analysis_cache[self.task_id] = cached_analysis
        
        result = await self.service.analyze_task_workflow(self.task_id)
        
        assert result == cached_analysis
        # Should not call repositories since cached
        self.task_repository.get.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_task_workflow_cache_expired(self):
        """Test workflow analysis when cache is expired"""
        # Set up cache with old analysis
        old_analysis = WorkflowAnalysis(
            task_id=self.task_id,
            analysis_timestamp=datetime.now(timezone.utc) - timedelta(hours=2),  # Expired
            patterns=[],
            bottlenecks=[],
            optimization_opportunities=[],
            predicted_completion_time=None,
            risk_factors=[],
            success_indicators=[]
        )
        self.service._analysis_cache[self.task_id] = old_analysis
        
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_detect_patterns', return_value=[]):
                with patch.object(self.service, '_identify_bottlenecks', return_value=[]):
                    with patch.object(self.service, '_find_optimization_opportunities', return_value=[]):
                        with patch.object(self.service, '_predict_completion_time', return_value=None):
                            with patch.object(self.service, '_assess_risk_factors', return_value=[]):
                                with patch.object(self.service, '_identify_success_indicators', return_value=[]):
                                    result = await self.service.analyze_task_workflow(self.task_id)
        
        # Should perform new analysis, not return cached
        assert result != old_analysis
        self.task_repository.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_task_workflow_without_related_tasks(self):
        """Test workflow analysis without including related tasks"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        with patch.object(self.service, '_detect_patterns', return_value=[]):
            with patch.object(self.service, '_identify_bottlenecks', return_value=[]):
                with patch.object(self.service, '_find_optimization_opportunities', return_value=[]):
                    with patch.object(self.service, '_predict_completion_time', return_value=None):
                        with patch.object(self.service, '_assess_risk_factors', return_value=[]):
                            with patch.object(self.service, '_identify_success_indicators', return_value=[]):
                                result = await self.service.analyze_task_workflow(
                                    self.task_id,
                                    include_related=False
                                )
        
        assert isinstance(result, WorkflowAnalysis)


class TestTaskContextAndRelatedTasks:
    """Test suite for task context and related tasks functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        self.service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        self.task_id = uuid.uuid4()
    
    @pytest.mark.asyncio
    async def test_get_task_context_success(self):
        """Test successful task context retrieval"""
        mock_context = Mock()
        self.context_repository.get_by_task_id.return_value = mock_context
        
        result = await self.service._get_task_context(self.task_id)
        
        assert result == mock_context
        self.context_repository.get_by_task_id.assert_called_once_with(self.task_id)
    
    @pytest.mark.asyncio
    async def test_get_task_context_exception(self):
        """Test task context retrieval with exception"""
        self.context_repository.get_by_task_id.side_effect = Exception("Context not found")
        
        result = await self.service._get_task_context(self.task_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_related_tasks_by_labels(self):
        """Test getting related tasks by labels"""
        task = Mock()
        task.id = self.task_id
        task.labels = ["frontend", "bug"]
        task.subtasks = []  # No subtasks for this test
        task.parent_id = None  # No parent for this test
        
        # Mock tasks returned by label queries
        label_tasks = [Mock(id=uuid.uuid4()) for _ in range(3)]
        self.task_repository.list.return_value = label_tasks
        
        result = await self.service._get_related_tasks(task)
        
        assert len(result) == 3
        assert all(t.id != self.task_id for t in result)
        # Should have called list for each label
        assert self.task_repository.list.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_related_tasks_with_parent_and_subtasks(self):
        """Test getting related tasks with parent and subtasks"""
        parent_id = uuid.uuid4()
        subtask_id1 = uuid.uuid4()
        subtask_id2 = uuid.uuid4()
        
        task = Mock()
        task.id = self.task_id
        task.labels = []
        task.parent_id = parent_id
        task.subtasks = [subtask_id1, subtask_id2]
        
        parent_task = Mock(id=parent_id)
        subtask1 = Mock(id=subtask_id1)
        subtask2 = Mock(id=subtask_id2)
        
        self.task_repository.list.return_value = []  # No label matches
        self.task_repository.get.side_effect = [parent_task, subtask1, subtask2]
        
        result = await self.service._get_related_tasks(task)
        
        assert len(result) == 3
        assert parent_task in result
        assert subtask1 in result
        assert subtask2 in result
    
    @pytest.mark.asyncio
    async def test_get_related_tasks_removes_duplicates(self):
        """Test that get_related_tasks removes duplicates"""
        task = Mock()
        task.id = self.task_id
        task.labels = ["test"]
        task.subtasks = []  # No subtasks for this test
        task.parent_id = None  # No parent for this test
        
        duplicate_task = Mock(id=uuid.uuid4())
        self.task_repository.list.return_value = [duplicate_task, duplicate_task]
        
        result = await self.service._get_related_tasks(task)
        
        # Should only have one instance of the duplicate task
        assert len(result) == 1
        assert result[0].id == duplicate_task.id
    
    @pytest.mark.asyncio
    async def test_get_related_tasks_excludes_self(self):
        """Test that get_related_tasks excludes the task itself"""
        task = Mock()
        task.id = self.task_id
        task.labels = ["test"]
        task.subtasks = []  # No subtasks for this test
        task.parent_id = None  # No parent for this test
        
        self.task_repository.list.return_value = [task]  # Returns self
        
        result = await self.service._get_related_tasks(task)
        
        # Should exclude the task itself
        assert len(result) == 0


class TestPatternDetection:
    """Test suite for pattern detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkflowAnalysisService(Mock(), Mock())
        self.task_id = uuid.uuid4()
    
    def test_detect_completion_patterns_extended_duration(self):
        """Test detection of extended duration pattern"""
        # Create task that's taking longer than average
        task = Mock()
        task.id = self.task_id
        task.created_at = datetime.now(timezone.utc) - timedelta(hours=20)  # Current duration: 20h
        
        # Create related completed tasks with shorter duration
        related_tasks = []
        for i in range(5):
            related_task = Mock()
            related_task.status = "done"
            related_task.created_at = datetime.now(timezone.utc) - timedelta(days=1)
            related_task.updated_at = datetime.now(timezone.utc) - timedelta(hours=16)  # 8h duration
            related_tasks.append(related_task)
        
        patterns = self.service._detect_completion_patterns(task, related_tasks)
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.pattern_name == "extended_duration"
        assert pattern.pattern_type == "bottleneck"
        assert pattern.confidence == 0.8
        assert "20.0h vs avg 8.0h" in pattern.description
        assert len(pattern.recommendations) == 3
    
    def test_detect_completion_patterns_insufficient_data(self):
        """Test completion pattern detection with insufficient data"""
        task = Mock()
        task.id = self.task_id
        
        # Only 2 completed tasks (need 3+ for pattern detection)
        related_tasks = [Mock(status="done") for _ in range(2)]
        
        patterns = self.service._detect_completion_patterns(task, related_tasks)
        
        assert len(patterns) == 0
    
    def test_detect_blocker_patterns_high_rate(self):
        """Test detection of high blocker rate pattern"""
        task = Mock()
        task.id = self.task_id
        
        # Create related tasks with high blocker rate
        related_tasks = []
        for i in range(10):
            related_task = Mock()
            related_task.id = uuid.uuid4()
            related_task.status = "blocked" if i < 4 else "in_progress"  # 40% blocked
            related_tasks.append(related_task)
        
        patterns = self.service._detect_blocker_patterns(task, related_tasks)
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.pattern_name == "high_blocker_rate"
        assert pattern.pattern_type == "bottleneck"
        assert pattern.confidence == 0.85
        assert "4/10 related tasks are blocked" in pattern.description
        assert pattern.metrics["blocker_rate"] == 0.4
    
    def test_detect_blocker_patterns_insufficient_data(self):
        """Test blocker pattern detection with insufficient data"""
        task = Mock()
        
        # Only 3 related tasks (need more for meaningful pattern)
        related_tasks = [Mock(status="blocked") for _ in range(3)]
        
        patterns = self.service._detect_blocker_patterns(task, related_tasks)
        
        assert len(patterns) == 0  # Not enough data for pattern
    
    def test_detect_collaboration_patterns_multiple_indicators(self):
        """Test detection of collaboration patterns with multiple indicators"""
        task = Mock()
        task.id = self.task_id
        task.created_at = datetime.now(timezone.utc) - timedelta(days=20)  # Long running
        task.status = "in_progress"
        task.assignees = ["user1", "user2", "user3"]  # Multiple assignees
        
        context = Mock()
        context.notes = "Need help with this implementation, stuck on review"  # Contains keywords
        
        patterns = self.service._detect_collaboration_patterns(task, context)
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.pattern_name == "collaboration_opportunity"
        assert pattern.pattern_type == "optimization"
        assert pattern.confidence == 0.75
        assert len(pattern.recommendations) == 3
        assert pattern.metrics["indicator_count"] == 3
    
    def test_detect_collaboration_patterns_single_indicator(self):
        """Test collaboration pattern detection with single indicator"""
        task = Mock()
        task.id = self.task_id
        task.created_at = datetime.now(timezone.utc) - timedelta(days=2)  # Not long running
        task.assignees = ["user1"]  # Single assignee
        
        context = Mock()
        context.notes = "Regular task notes"  # No keywords
        
        patterns = self.service._detect_collaboration_patterns(task, context)
        
        assert len(patterns) == 0  # Need at least 2 indicators
    
    def test_detect_progress_patterns_unbalanced(self):
        """Test detection of unbalanced progress pattern"""
        task = Mock()
        task.id = self.task_id
        task.progress_breakdown = {
            "implementation": 0.9,  # High progress
            "testing": 0.2,         # Low progress
            "documentation": 0.1    # Low progress
        }
        
        patterns = self.service._detect_progress_patterns(task)
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.pattern_name == "unbalanced_progress"
        assert pattern.pattern_type == "optimization"
        assert pattern.confidence == 0.8
        assert "testing" in pattern.recommendations[0]
        assert "documentation" in pattern.recommendations[0]
    
    def test_detect_progress_patterns_balanced(self):
        """Test progress pattern detection with balanced progress"""
        task = Mock()
        task.progress_breakdown = {
            "implementation": 0.6,
            "testing": 0.5,
            "documentation": 0.7
        }
        
        patterns = self.service._detect_progress_patterns(task)
        
        assert len(patterns) == 0  # Progress is balanced
    
    def test_detect_progress_patterns_no_breakdown(self):
        """Test progress pattern detection without progress breakdown"""
        task = Mock()
        task.progress_breakdown = None  # Explicitly set to None
        
        patterns = self.service._detect_progress_patterns(task)
        
        assert len(patterns) == 0


class TestBottleneckIdentification:
    """Test suite for bottleneck identification functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.service = WorkflowAnalysisService(self.task_repository, Mock())
        self.task_id = uuid.uuid4()
    
    @pytest.mark.asyncio
    async def test_identify_bottlenecks_progress_stall(self):
        """Test identification of progress stall bottleneck"""
        task = Mock()
        task.progress_timeline = [
            {"timestamp": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()}
        ]
        task.dependencies = []  # No dependencies for this test
        task.subtasks = []  # No subtasks for this test
        
        context = Mock()
        
        bottlenecks = await self.service._identify_bottlenecks(task, context)
        
        assert len(bottlenecks) == 1
        bottleneck = bottlenecks[0]
        assert bottleneck["type"] == "progress_stall"
        assert bottleneck["severity"] == "high"
        assert "5 days" in bottleneck["description"]
        assert len(bottleneck["suggestions"]) == 3
    
    @pytest.mark.asyncio
    async def test_identify_bottlenecks_dependency_blocked(self):
        """Test identification of dependency blocked bottleneck"""
        dep_id1 = uuid.uuid4()
        dep_id2 = uuid.uuid4()
        
        task = Mock()
        task.dependencies = [dep_id1, dep_id2, uuid.uuid4(), uuid.uuid4()]  # 4 dependencies
        task.progress_timeline = []  # No timeline to avoid the stalled progress check
        
        # Mock dependency tasks - some blocked
        blocked_task = Mock(status="blocked")
        normal_task = Mock(status="in_progress")
        
        self.task_repository.get.side_effect = [blocked_task, normal_task, blocked_task, None]
        
        bottlenecks = await self.service._identify_bottlenecks(task, None)
        
        assert len(bottlenecks) == 1
        bottleneck = bottlenecks[0]
        assert bottleneck["type"] == "dependency_blocked"
        assert bottleneck["severity"] == "critical"
        assert "2 dependencies are blocked" in bottleneck["description"]
        assert "Cannot proceed until resolved" in bottleneck["impact"]
    
    @pytest.mark.asyncio
    async def test_identify_bottlenecks_no_issues(self):
        """Test bottleneck identification with no issues"""
        task = Mock()
        task.progress_timeline = []  # Empty timeline
        task.dependencies = []  # No dependencies
        task.subtasks = []  # No subtasks
        
        bottlenecks = await self.service._identify_bottlenecks(task, None)
        
        assert len(bottlenecks) == 0


class TestOptimizationOpportunities:
    """Test suite for optimization opportunities functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkflowAnalysisService(Mock(), Mock())
    
    @pytest.mark.asyncio
    async def test_find_optimization_opportunities_task_decomposition(self):
        """Test finding task decomposition opportunity"""
        task = Mock()
        task.subtasks = []  # No subtasks
        task.estimated_effort = "5d"  # Large effort
        
        opportunities = await self.service._find_optimization_opportunities(task, None, [])
        
        assert len(opportunities) == 1
        opportunity = opportunities[0]
        assert opportunity["type"] == "task_decomposition"
        assert opportunity["potential_impact"] == "high"
        assert "Large task could benefit from breakdown" in opportunity["description"]
        assert len(opportunity["benefits"]) == 3
        assert len(opportunity["implementation"]) == 3
    
    @pytest.mark.asyncio
    async def test_find_optimization_opportunities_task_decomposition_hours(self):
        """Test task decomposition opportunity with hours"""
        task = Mock()
        task.subtasks = []
        task.estimated_effort = "30h"  # Large effort in hours
        
        opportunities = await self.service._find_optimization_opportunities(task, None, [])
        
        assert len(opportunities) == 1
        assert opportunities[0]["type"] == "task_decomposition"
    
    @pytest.mark.asyncio
    async def test_find_optimization_opportunities_automation(self):
        """Test finding automation opportunity"""
        task = Mock()
        task.subtasks = ["sub1"]  # Has subtasks (no decomposition needed)
        task.estimated_effort = "1d"  # Small effort (no decomposition needed)
        
        context = Mock()
        context.notes = "This task involves manual copying and repetitive work every time"
        
        opportunities = await self.service._find_optimization_opportunities(task, context, [])
        
        assert len(opportunities) == 1
        opportunity = opportunities[0]
        assert opportunity["type"] == "automation"
        assert opportunity["potential_impact"] == "medium"
        assert "repetitive manual work" in opportunity["description"]
    
    @pytest.mark.asyncio
    async def test_find_optimization_opportunities_multiple(self):
        """Test finding multiple optimization opportunities"""
        task = Mock()
        task.subtasks = []  # No subtasks
        task.estimated_effort = "10d"  # Large effort
        
        context = Mock()
        context.notes = "Manual process that needs to be done every time"
        
        opportunities = await self.service._find_optimization_opportunities(task, context, [])
        
        assert len(opportunities) == 2
        types = [opp["type"] for opp in opportunities]
        assert "task_decomposition" in types
        assert "automation" in types
    
    @pytest.mark.asyncio
    async def test_find_optimization_opportunities_none(self):
        """Test finding no optimization opportunities"""
        task = Mock()
        task.subtasks = ["sub1"]  # Has subtasks
        task.estimated_effort = "2h"  # Small effort
        
        context = Mock()
        context.notes = "Regular task notes"
        
        opportunities = await self.service._find_optimization_opportunities(task, context, [])
        
        assert len(opportunities) == 0


class TestCompletionTimePrediction:
    """Test suite for completion time prediction functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkflowAnalysisService(Mock(), Mock())
        self.task_id = uuid.uuid4()
    
    @pytest.mark.asyncio
    async def test_predict_completion_time_with_similar_tasks(self):
        """Test completion time prediction with similar completed tasks"""
        task = Mock()
        task.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
        task.progress = 0.5
        task.estimated_effort = "2d"
        
        # Create similar completed tasks
        related_tasks = []
        for i in range(3):
            related_task = Mock()
            related_task.status = "done"
            related_task.created_at = datetime.now(timezone.utc) - timedelta(days=2)
            related_task.updated_at = datetime.now(timezone.utc) - timedelta(days=1)  # 24h completion
            related_task.estimated_effort = "2d"
            related_tasks.append(related_task)
        
        result = await self.service._predict_completion_time(task, related_tasks)
        
        assert result is not None
        assert isinstance(result, timedelta)
        # Should be positive (remaining time)
        assert result.total_seconds() >= 0
    
    @pytest.mark.asyncio
    async def test_predict_completion_time_fallback_to_any_similar(self):
        """Test completion time prediction falling back to any similar tasks"""
        task = Mock()
        task.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
        task.progress = 0.5
        task.estimated_effort = "2d"
        
        # No tasks with matching estimated_effort, but some completed tasks
        related_tasks = []
        for i in range(3):
            related_task = Mock()
            related_task.status = "done"
            related_task.created_at = datetime.now(timezone.utc) - timedelta(days=2)
            related_task.updated_at = datetime.now(timezone.utc) - timedelta(days=1)
            related_task.estimated_effort = "1d"  # Different effort
            related_tasks.append(related_task)
        
        result = await self.service._predict_completion_time(task, related_tasks)
        
        assert result is not None
        assert isinstance(result, timedelta)
    
    @pytest.mark.asyncio
    async def test_predict_completion_time_no_similar_tasks(self):
        """Test completion time prediction with no similar tasks"""
        task = Mock()
        task.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
        
        related_tasks = [Mock(status="in_progress")]  # No completed tasks
        
        result = await self.service._predict_completion_time(task, related_tasks)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_predict_completion_time_no_created_at(self):
        """Test completion time prediction without created_at"""
        task = Mock()
        # No created_at attribute
        
        result = await self.service._predict_completion_time(task, [])
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_predict_completion_time_overdue(self):
        """Test completion time prediction for overdue task"""
        task = Mock()
        task.created_at = datetime.now(timezone.utc) - timedelta(days=10)  # Very old
        task.progress = 0.95  # Almost complete (95%) but stuck
        
        # Short completion time for similar tasks
        related_task = Mock()
        related_task.status = "done"
        related_task.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        related_task.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)  # 1h completion
        
        result = await self.service._predict_completion_time(task, [related_task])
        
        # Task at 95% after 10 days should be overdue based on similar 1h tasks
        assert result == timedelta(seconds=0)  # Overdue, so 0 remaining time


class TestRiskAssessment:
    """Test suite for risk assessment functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkflowAnalysisService(Mock(), Mock())
    
    def test_assess_risk_factors_high_priority_low_progress(self):
        """Test risk assessment for high priority task with low progress"""
        task = Mock()
        task.priority = "urgent"
        task.progress = 0.2
        task.assignees = ["user1"]
        task.dependencies = []
        
        context = Mock()
        context.data = {"some": "data"}
        
        patterns = []
        
        risks = self.service._assess_risk_factors(task, context, patterns)
        
        assert "High priority task with low progress" in risks
    
    def test_assess_risk_factors_bottleneck_patterns(self):
        """Test risk assessment with bottleneck patterns"""
        task = Mock()
        task.priority = "medium"
        task.progress = 0.5
        task.assignees = ["user1"]
        task.dependencies = []
        
        # Create bottleneck patterns
        bottleneck_pattern = Mock()
        bottleneck_pattern.pattern_type = "bottleneck"
        patterns = [bottleneck_pattern, bottleneck_pattern]
        
        risks = self.service._assess_risk_factors(task, None, patterns)
        
        assert "2 bottleneck patterns detected" in risks
    
    def test_assess_risk_factors_missing_context(self):
        """Test risk assessment with missing context"""
        task = Mock()
        task.priority = "medium"
        task.progress = 0.5
        task.assignees = ["user1"]
        task.dependencies = []
        
        risks = self.service._assess_risk_factors(task, None, [])
        
        assert "Limited context information available" in risks
    
    def test_assess_risk_factors_no_assignees(self):
        """Test risk assessment with no assignees"""
        task = Mock()
        task.priority = "medium"
        task.progress = 0.5
        task.assignees = []
        task.dependencies = []
        
        risks = self.service._assess_risk_factors(task, Mock(), [])
        
        assert "No assignees on task" in risks
    
    def test_assess_risk_factors_high_dependencies(self):
        """Test risk assessment with high number of dependencies"""
        task = Mock()
        task.dependencies = [uuid.uuid4() for _ in range(6)]  # 6 dependencies
        
        risks = self.service._assess_risk_factors(task, Mock(), [])
        
        assert "High number of dependencies" in risks
    
    def test_assess_risk_factors_multiple_risks(self):
        """Test risk assessment with multiple risk factors"""
        task = Mock()
        task.priority = "critical"
        task.progress = 0.1
        task.assignees = []
        task.dependencies = [uuid.uuid4() for _ in range(8)]
        
        risks = self.service._assess_risk_factors(task, None, [])
        
        assert len(risks) >= 3
        assert any("High priority" in risk for risk in risks)
        assert any("No assignees" in risk for risk in risks)
        assert any("High number of dependencies" in risk for risk in risks)


class TestSuccessIndicators:
    """Test suite for success indicators functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkflowAnalysisService(Mock(), Mock())
    
    def test_identify_success_indicators_progress_momentum(self):
        """Test success indicator for progress momentum"""
        task = Mock()
        task.progress_timeline = [
            {"status": "in_progress"},
            {"status": "in_progress"},
            {"status": "in_progress"},
            {"status": "in_progress"}
        ]
        task.progress_breakdown = None
        
        context = Mock()
        context.notes = ["note1", "note2", "note3", "note4"]  # Well documented
        context.data = {"requirements": ["req1"]}
        
        indicators = self.service._identify_success_indicators(task, context)
        
        # Now that we fixed the ProgressStatus.ADVANCING bug to use IN_PROGRESS, the momentum indicator should be detected
        assert "Consistent progress momentum" in indicators
        assert "Well-documented context" in indicators
        assert "Clear requirements defined" in indicators
    
    def test_identify_success_indicators_balanced_progress(self):
        """Test success indicator for balanced progress"""
        task = Mock()
        task.progress_breakdown = {
            "implementation": 0.6,
            "testing": 0.5,
            "documentation": 0.7
        }  # Balanced progress (max-min < 0.3)
        task.progress_timeline = []
        
        indicators = self.service._identify_success_indicators(task, None)
        
        assert "Balanced progress across all areas" in indicators
    
    def test_identify_success_indicators_unbalanced_progress(self):
        """Test success indicators without balanced progress"""
        task = Mock()
        task.progress_breakdown = {
            "implementation": 0.9,
            "testing": 0.2,
            "documentation": 0.1
        }  # Unbalanced progress (max-min > 0.3)
        task.progress_timeline = []
        
        indicators = self.service._identify_success_indicators(task, None)
        
        assert "Balanced progress across all areas" not in indicators
    
    def test_identify_success_indicators_minimal_context(self):
        """Test success indicators with minimal context"""
        task = Mock()
        # No progress_timeline or progress_breakdown
        task.progress_timeline = []
        task.progress_breakdown = None
        
        context = Mock()
        context.notes = ["single note"]  # Not well documented (< 4 notes)
        context.data = {}  # No requirements
        
        indicators = self.service._identify_success_indicators(task, context)
        
        assert len(indicators) == 0  # No success indicators


class TestWorkflowRecommendations:
    """Test suite for workflow recommendations functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        self.service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        self.task_id = uuid.uuid4()
    
    @pytest.mark.asyncio
    async def test_get_workflow_recommendations(self):
        """Test getting workflow recommendations"""
        # Mock analysis result
        pattern = WorkflowPattern(
            pattern_name="test_pattern",
            pattern_type="optimization",
            confidence=0.9,
            description="Test pattern",
            affected_tasks=[],
            recommendations=["Pattern recommendation"],
            metrics={}
        )
        
        analysis = WorkflowAnalysis(
            task_id=self.task_id,
            analysis_timestamp=datetime.now(timezone.utc),
            patterns=[pattern],
            bottlenecks=[{
                "type": "progress_stall",
                "severity": "high",
                "suggestions": ["Bottleneck suggestion"]
            }],
            optimization_opportunities=[{
                "type": "automation",
                "potential_impact": "high",
                "description": "Automation opportunity",
                "implementation": ["Step 1", "Step 2"]
            }],
            predicted_completion_time=None,
            risk_factors=[],
            success_indicators=[]
        )
        
        with patch.object(self.service, 'analyze_task_workflow', return_value=analysis):
            recommendations = await self.service.get_workflow_recommendations(self.task_id)
        
        assert len(recommendations) == 3
        
        # Check pattern recommendation
        pattern_rec = next(r for r in recommendations if r["source"] == "test_pattern")
        assert pattern_rec["priority"] == "high"
        assert pattern_rec["confidence"] == 0.9
        
        # Check bottleneck recommendation
        bottleneck_rec = next(r for r in recommendations if r["source"] == "bottleneck_progress_stall")
        assert bottleneck_rec["priority"] == "high"
        assert bottleneck_rec["confidence"] == 0.9
        
        # Check optimization recommendation
        opt_rec = next(r for r in recommendations if r["source"] == "optimization_automation")
        assert opt_rec["priority"] == "high"
        assert opt_rec["implementation_steps"] == ["Step 1", "Step 2"]
    
    @pytest.mark.asyncio
    async def test_get_workflow_recommendations_priority_sorting(self):
        """Test that recommendations are sorted by priority and confidence"""
        # Mock analysis with different priority recommendations
        analysis = WorkflowAnalysis(
            task_id=self.task_id,
            analysis_timestamp=datetime.now(timezone.utc),
            patterns=[
                WorkflowPattern(
                    pattern_name="low_confidence",
                    pattern_type="optimization",
                    confidence=0.5,  # Low confidence
                    description="Low confidence pattern",
                    affected_tasks=[],
                    recommendations=["Low confidence rec"],
                    metrics={}
                ),
                WorkflowPattern(
                    pattern_name="high_confidence",
                    pattern_type="bottleneck",
                    confidence=0.95,  # High confidence
                    description="High confidence pattern",
                    affected_tasks=[],
                    recommendations=["High confidence rec"],
                    metrics={}
                )
            ],
            bottlenecks=[{
                "type": "critical_issue",
                "severity": "critical",  # Highest priority
                "suggestions": ["Critical suggestion"]
            }],
            optimization_opportunities=[{
                "type": "minor_improvement",
                "potential_impact": "low",  # Low priority
                "description": "Minor improvement"
            }],
            predicted_completion_time=None,
            risk_factors=[],
            success_indicators=[]
        )
        
        with patch.object(self.service, 'analyze_task_workflow', return_value=analysis):
            recommendations = await self.service.get_workflow_recommendations(self.task_id)
        
        # Should be sorted: critical first, then high confidence, then others
        assert recommendations[0]["source"] == "bottleneck_critical_issue"
        assert recommendations[1]["source"] == "high_confidence"
        # Low confidence and low impact should come later
    
    @pytest.mark.asyncio
    async def test_get_workflow_recommendations_limit(self):
        """Test that recommendations are limited to top 10"""
        # Create many recommendations
        patterns = [
            WorkflowPattern(
                pattern_name=f"pattern_{i}",
                pattern_type="optimization",
                confidence=0.8,
                description=f"Pattern {i}",
                affected_tasks=[],
                recommendations=[f"Recommendation {i}"],
                metrics={}
            )
            for i in range(15)  # 15 patterns
        ]
        
        analysis = WorkflowAnalysis(
            task_id=self.task_id,
            analysis_timestamp=datetime.now(timezone.utc),
            patterns=patterns,
            bottlenecks=[],
            optimization_opportunities=[],
            predicted_completion_time=None,
            risk_factors=[],
            success_indicators=[]
        )
        
        with patch.object(self.service, 'analyze_task_workflow', return_value=analysis):
            recommendations = await self.service.get_workflow_recommendations(self.task_id)
        
        # Should be limited to 10 recommendations
        assert len(recommendations) <= 10


class TestIntegration:
    """Integration tests for WorkflowAnalysisService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        
        self.service = WorkflowAnalysisService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        self.task_id = uuid.uuid4()
    
    @pytest.mark.asyncio
    async def test_full_workflow_analysis(self):
        """Test complete workflow analysis workflow"""
        # Create a complex task scenario
        task = Mock()
        task.id = self.task_id
        task.status = "in_progress"
        task.priority = "urgent"  # Changed to urgent to trigger risk factor for high priority with low progress
        task.created_at = datetime.now(timezone.utc) - timedelta(days=15)  # Long running (>14 days for collaboration indicator)
        task.labels = ["frontend", "critical"]
        task.subtasks = []
        task.assignees = ["user1"]
        task.dependencies = []
        task.progress = 0.2  # Low progress for high priority (< 0.3 to trigger risk)
        task.estimated_effort = "5d"  # Large task
        task.progress_breakdown = {
            "implementation": 0.8,  # Unbalanced
            "testing": 0.1
        }
        task.progress_timeline = [
            {"timestamp": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
             "status": "in_progress"}
        ]
        
        context = Mock()
        context.notes = "Need help with testing, manual repetitive work every time"
        context.data = {"requirements": ["req1", "req2"]}
        
        # Mock related completed tasks
        related_task = Mock()
        related_task.id = uuid.uuid4()
        related_task.status = "done"
        related_task.created_at = datetime.now(timezone.utc) - timedelta(days=5)
        related_task.updated_at = datetime.now(timezone.utc) - timedelta(days=2)  # 3 days to complete
        related_task.estimated_effort = "2d"
        
        # Configure mocks
        self.task_repository.get.return_value = task
        self.context_repository.get_by_task_id.return_value = context
        self.task_repository.list.return_value = [related_task]
        
        # Perform analysis
        result = await self.service.analyze_task_workflow(self.task_id)
        
        # Verify comprehensive analysis
        assert isinstance(result, WorkflowAnalysis)
        assert result.task_id == self.task_id
        
        # Should detect patterns
        assert len(result.patterns) > 0
        pattern_names = [p.pattern_name for p in result.patterns]
        assert "collaboration_opportunity" in pattern_names  # Multiple indicators
        assert "unbalanced_progress" in pattern_names  # Unbalanced progress breakdown
        
        # Should identify risks
        assert len(result.risk_factors) > 0
        assert any("High priority task with low progress" in risk for risk in result.risk_factors)
        
        # Should find optimization opportunities
        assert len(result.optimization_opportunities) > 0
        opportunity_types = [opp["type"] for opp in result.optimization_opportunities]
        assert "task_decomposition" in opportunity_types  # Large task
        assert "automation" in opportunity_types  # Manual work mentioned
        
        # Should have success indicators
        assert len(result.success_indicators) > 0
        assert "Clear requirements defined" in result.success_indicators
        
        # Get recommendations
        recommendations = await self.service.get_workflow_recommendations(self.task_id)
        assert len(recommendations) > 0
        
        # Verify prioritization
        high_priority_recs = [r for r in recommendations if r["priority"] in ["critical", "high"]]
        assert len(high_priority_recs) > 0
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self):
        """Test that analysis results are properly cached"""
        task = Mock(spec=['id', 'status', 'created_at', 'updated_at', 'labels', 'subtasks', 'assignees', 'dependencies', 'progress', 'estimated_effort', 'progress_breakdown', 'progress_timeline', 'priority'])
        task.id = self.task_id
        task.status = "done"
        task.created_at = datetime.now(timezone.utc) - timedelta(days=5)  # Add created_at for datetime operations
        task.updated_at = datetime.now(timezone.utc) - timedelta(days=1)  # Add updated_at
        task.priority = "medium"  # Add priority
        task.labels = []
        task.subtasks = []
        task.assignees = ["user1"]
        task.dependencies = []
        task.progress = 0.5
        task.estimated_effort = "2d"  # Add estimated_effort to avoid subscript error
        task.progress_breakdown = None
        task.progress_timeline = []
        
        self.task_repository.get.return_value = task
        self.context_repository.get_by_task_id.return_value = None
        
        # First analysis
        result1 = await self.service.analyze_task_workflow(self.task_id)
        
        # Second analysis (should use cache)
        result2 = await self.service.analyze_task_workflow(self.task_id)
        
        # Should be the same object from cache
        assert result1 == result2
        
        # Repository should only be called once
        self.task_repository.get.assert_called_once()
        
        # Verify cache contains the result
        assert self.task_id in self.service._analysis_cache
        assert self.service._analysis_cache[self.task_id] == result1