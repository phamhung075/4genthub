"""
Unit tests for CascadeCalculator Service

Tests for the cascade calculation service that tracks relationships
between tasks, subtasks, branches, projects, and contexts.

Test Requirements:
- Test task cascade returns correct affected entities
- Test subtask cascade propagates to parent
- Test branch cascade affects project
- Test performance is under 50ms
- Test deduplication works correctly
- Test cache functionality
"""

import pytest
import time
import uuid
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from fastmcp.task_management.domain.services.cascade_calculator import (
    CascadeCalculator,
    EntityType,
    CascadeResult
)


@pytest.fixture
def mock_session():
    """Create a mock database session"""
    session = AsyncMock()

    # Mock the dialect
    mock_bind = Mock()
    mock_bind.dialect.name = 'sqlite'  # Default to SQLite for tests
    session.get_bind.return_value = mock_bind

    return session


@pytest.fixture
def cascade_calculator(mock_session):
    """Create CascadeCalculator instance with mock session"""
    return CascadeCalculator(mock_session)


@pytest.fixture
def sample_task_id():
    """Generate sample task UUID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_subtask_id():
    """Generate sample subtask UUID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_branch_id():
    """Generate sample branch UUID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_project_id():
    """Generate sample project UUID"""
    return str(uuid.uuid4())


class TestCascadeCalculator:
    """Test suite for CascadeCalculator"""

    @pytest.mark.asyncio
    async def test_task_cascade_calculation(
        self, cascade_calculator, mock_session, sample_task_id, sample_branch_id, sample_project_id
    ):
        """Test task cascade returns correct affected entities"""

        # Mock task query result
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            sample_task_id, sample_branch_id, sample_project_id, None
        )
        mock_session.execute.return_value = mock_result

        # Mock subtasks query (empty result)
        mock_subtasks_result = Mock()
        mock_subtasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock parent tasks query (empty result)
        mock_parent_tasks_result = Mock()
        mock_parent_tasks_result.__iter__ = Mock(return_value=iter([]))

        # Configure side effects for multiple execute calls
        mock_session.execute.side_effect = [
            mock_result,  # Task details query
            mock_subtasks_result,  # Subtasks query
            mock_parent_tasks_result,  # Parent tasks query
            Mock()  # Related contexts query
        ]

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(sample_task_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_task_id
        assert result.entity_type == EntityType.TASK

        # Verify affected entities
        assert sample_task_id in result.affected_tasks
        assert sample_branch_id in result.affected_branches
        assert sample_project_id in result.affected_projects

        # Verify calculation time is set
        assert result.calculation_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_subtask_cascade_propagation(
        self, cascade_calculator, mock_session, sample_subtask_id,
        sample_task_id, sample_branch_id, sample_project_id
    ):
        """Test subtask cascade propagates to parent task"""

        # Mock subtask query result
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            sample_task_id, sample_branch_id, sample_project_id, None
        )
        mock_session.execute.return_value = mock_result

        # Execute cascade calculation
        result = await cascade_calculator.calculate_subtask_cascade(sample_subtask_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_subtask_id
        assert result.entity_type == EntityType.SUBTASK

        # Verify cascade to parent
        assert sample_subtask_id in result.affected_subtasks
        assert sample_task_id in result.affected_tasks
        assert sample_branch_id in result.affected_branches
        assert sample_project_id in result.affected_projects

    @pytest.mark.asyncio
    async def test_branch_cascade_affects_project(
        self, cascade_calculator, mock_session, sample_branch_id,
        sample_project_id, sample_task_id, sample_subtask_id
    ):
        """Test branch cascade affects project and all related entities"""

        # Mock branch query result with tasks and subtasks
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            (sample_project_id, sample_task_id, sample_subtask_id),
            (sample_project_id, None, None)  # Branch row without task/subtask
        ]))
        mock_session.execute.return_value = mock_result

        # Execute cascade calculation
        result = await cascade_calculator.calculate_branch_cascade(sample_branch_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_branch_id
        assert result.entity_type == EntityType.BRANCH

        # Verify cascade affects all levels
        assert sample_branch_id in result.affected_branches
        assert sample_project_id in result.affected_projects
        assert sample_task_id in result.affected_tasks
        assert sample_subtask_id in result.affected_subtasks

    @pytest.mark.asyncio
    async def test_project_cascade_all_branches(
        self, cascade_calculator, mock_session, sample_project_id,
        sample_branch_id, sample_task_id, sample_subtask_id
    ):
        """Test project cascade affects all branches and their contents"""

        # Create additional IDs for multiple branches
        branch_id_2 = str(uuid.uuid4())
        task_id_2 = str(uuid.uuid4())

        # Mock project query result with multiple branches
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            (sample_branch_id, sample_task_id, sample_subtask_id),
            (branch_id_2, task_id_2, None),
            (sample_branch_id, None, None)  # Branch row without task
        ]))
        mock_session.execute.return_value = mock_result

        # Execute cascade calculation
        result = await cascade_calculator.calculate_project_cascade(sample_project_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_project_id
        assert result.entity_type == EntityType.PROJECT

        # Verify all branches are affected
        assert sample_project_id in result.affected_projects
        assert sample_branch_id in result.affected_branches
        assert branch_id_2 in result.affected_branches

        # Verify all tasks are affected
        assert sample_task_id in result.affected_tasks
        assert task_id_2 in result.affected_tasks

        # Verify subtasks are affected
        assert sample_subtask_id in result.affected_subtasks

    @pytest.mark.asyncio
    async def test_entity_type_detection(
        self, cascade_calculator, mock_session, sample_task_id
    ):
        """Test automatic entity type detection"""

        # Mock queries for type detection - task found
        mock_result_task = Mock()
        mock_result_task.scalar.return_value = 1  # Task found

        mock_result_others = Mock()
        mock_result_others.scalar.return_value = 0  # Others not found

        mock_session.execute.side_effect = [mock_result_task]

        # Test detection
        entity_type = await cascade_calculator._detect_entity_type(sample_task_id)
        assert entity_type == EntityType.TASK

    @pytest.mark.asyncio
    async def test_deduplication_works_correctly(
        self, cascade_calculator, mock_session, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test deduplication works correctly for affected entities"""

        # Mock task query with duplicate entities in result
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            sample_task_id, sample_branch_id, sample_project_id, None
        )

        # Mock subtasks query with duplicates
        mock_subtasks_result = Mock()
        subtask_id = str(uuid.uuid4())
        mock_subtasks_result.__iter__ = Mock(return_value=iter([
            (subtask_id,), (subtask_id,)  # Duplicate subtask
        ]))

        # Mock parent tasks query
        mock_parent_tasks_result = Mock()
        mock_parent_tasks_result.__iter__ = Mock(return_value=iter([]))

        mock_session.execute.side_effect = [
            mock_result,
            mock_subtasks_result,
            mock_parent_tasks_result,
            Mock()  # Related contexts
        ]

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(sample_task_id)

        # Verify deduplication - each ID should appear only once
        assert len(result.affected_subtasks) == 1
        assert subtask_id in result.affected_subtasks

    @pytest.mark.asyncio
    async def test_cache_functionality(
        self, cascade_calculator, mock_session, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test cache functionality works correctly"""

        # Mock task query result
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            sample_task_id, sample_branch_id, sample_project_id, None
        )

        # Mock subtasks query (empty result)
        mock_subtasks_result = Mock()
        mock_subtasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock parent tasks query (empty result)
        mock_parent_tasks_result = Mock()
        mock_parent_tasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock related contexts query (empty result)
        mock_contexts_result = Mock()
        mock_contexts_result.__iter__ = Mock(return_value=iter([]))

        # Mock other queries
        mock_session.execute.side_effect = [
            mock_result,  # Task details
            mock_subtasks_result,  # Subtasks
            mock_parent_tasks_result,  # Parent tasks
            mock_contexts_result   # Related contexts
        ]

        # First calculation - should execute queries
        result1 = await cascade_calculator.calculate_cascade(
            sample_task_id, EntityType.TASK, use_cache=True
        )

        # Verify result
        assert not result1.cache_hit
        assert result1.entity_id == sample_task_id

        # Second calculation - should hit cache
        result2 = await cascade_calculator.calculate_cascade(
            sample_task_id, EntityType.TASK, use_cache=True
        )

        # Verify cache hit
        assert result2.cache_hit
        assert result2.entity_id == sample_task_id

        # Verify cache statistics
        stats = cascade_calculator.get_cache_stats()
        assert stats["cache_size"] == 1
        assert len(stats["cache_entries"]) == 1

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cascade_calculator, mock_session):
        """Test cache expiration works correctly"""

        # Set short TTL for testing
        cascade_calculator._cache_ttl_seconds = 0.1

        sample_id = str(uuid.uuid4())

        # Mock queries
        mock_result = Mock()
        mock_result.fetchone.return_value = (sample_id, sample_id, sample_id, None)

        # Mock subtasks query (empty result)
        mock_subtasks_result = Mock()
        mock_subtasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock parent tasks query (empty result)
        mock_parent_tasks_result = Mock()
        mock_parent_tasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock related contexts query (empty result)
        mock_contexts_result = Mock()
        mock_contexts_result.__iter__ = Mock(return_value=iter([]))

        mock_session.execute.side_effect = [
            mock_result, mock_subtasks_result, mock_parent_tasks_result, mock_contexts_result,  # First call
            mock_result, mock_subtasks_result, mock_parent_tasks_result, mock_contexts_result   # Second call after expiration
        ]

        # First calculation
        result1 = await cascade_calculator.calculate_cascade(
            sample_id, EntityType.TASK, use_cache=True
        )
        assert not result1.cache_hit

        # Wait for cache to expire
        time.sleep(0.2)

        # Second calculation - cache should be expired
        result2 = await cascade_calculator.calculate_cascade(
            sample_id, EntityType.TASK, use_cache=True
        )
        assert not result2.cache_hit

    @pytest.mark.asyncio
    async def test_cache_clear(self, cascade_calculator, mock_session):
        """Test cache clearing functionality"""

        sample_id = str(uuid.uuid4())

        # Mock queries
        mock_result = Mock()
        mock_result.fetchone.return_value = (sample_id, sample_id, sample_id, None)

        # Mock subtasks query (empty result)
        mock_subtasks_result = Mock()
        mock_subtasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock parent tasks query (empty result)
        mock_parent_tasks_result = Mock()
        mock_parent_tasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock related contexts query (empty result)
        mock_contexts_result = Mock()
        mock_contexts_result.__iter__ = Mock(return_value=iter([]))

        mock_session.execute.side_effect = [
            mock_result,
            mock_subtasks_result,
            mock_parent_tasks_result,
            mock_contexts_result
        ]

        # Add entry to cache
        await cascade_calculator.calculate_cascade(
            sample_id, EntityType.TASK, use_cache=True
        )

        # Verify cache has content
        stats = cascade_calculator.get_cache_stats()
        assert stats["cache_size"] == 1

        # Clear cache
        cascade_calculator.clear_cache()

        # Verify cache is empty
        stats = cascade_calculator.get_cache_stats()
        assert stats["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_performance_under_50ms(
        self, cascade_calculator, mock_session, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test performance is under 50ms for cascade calculation"""

        # Mock fast queries
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            sample_task_id, sample_branch_id, sample_project_id, None
        )

        # Mock empty subtasks and parent tasks
        mock_empty_result = Mock()
        mock_empty_result.__iter__ = Mock(return_value=iter([]))

        mock_session.execute.side_effect = [
            mock_result,        # Task details
            mock_empty_result,  # Subtasks
            mock_empty_result,  # Parent tasks
            mock_empty_result   # Related contexts
        ]

        # Execute cascade calculation and measure time
        start_time = time.time()
        result = await cascade_calculator.calculate_cascade(
            sample_task_id, EntityType.TASK, use_cache=False
        )
        end_time = time.time()

        # Verify performance requirement
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms < 50, f"Cascade calculation took {actual_time_ms:.2f}ms (should be < 50ms)"

        # Verify result is valid
        assert isinstance(result, CascadeResult)
        assert result.calculation_time_ms >= 0

    @pytest.mark.asyncio
    async def test_missing_entity_handling(
        self, cascade_calculator, mock_session
    ):
        """Test handling of missing entities gracefully"""

        missing_id = str(uuid.uuid4())

        # Mock query result for missing entity
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(missing_id)

        # Verify graceful handling
        assert isinstance(result, CascadeResult)
        assert result.entity_id == missing_id
        assert result.entity_type == EntityType.TASK

        # Verify only the missing entity is in affected entities
        assert len(result.affected_tasks) == 1
        assert missing_id in result.affected_tasks

    @pytest.mark.asyncio
    async def test_get_all_affected_ids(
        self, cascade_calculator, mock_session, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test get_all_affected_ids method returns deduplicated set"""

        # Mock query result
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            sample_task_id, sample_branch_id, sample_project_id, None
        )

        # Mock subtasks query (empty result)
        mock_subtasks_result = Mock()
        mock_subtasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock parent tasks query (empty result)
        mock_parent_tasks_result = Mock()
        mock_parent_tasks_result.__iter__ = Mock(return_value=iter([]))

        # Mock related contexts query (empty result)
        mock_contexts_result = Mock()
        mock_contexts_result.__iter__ = Mock(return_value=iter([]))

        mock_session.execute.side_effect = [
            mock_result,
            mock_subtasks_result,
            mock_parent_tasks_result,
            mock_contexts_result
        ]

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(sample_task_id)

        # Test get_all_affected_ids
        all_ids = result.get_all_affected_ids()
        assert isinstance(all_ids, set)
        assert sample_task_id in all_ids
        assert sample_branch_id in all_ids
        assert sample_project_id in all_ids

        # Test get_affected_count
        count = result.get_affected_count()
        assert count == len(all_ids)
        assert count >= 3  # At least task, branch, and project

    @pytest.mark.asyncio
    async def test_materialized_view_queries(
        self, cascade_calculator, mock_session, sample_branch_id, sample_project_id
    ):
        """Test materialized view query methods"""

        # Test branch summary query
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock()
        mock_result.fetchone.return_value._mapping = {
            "branch_id": sample_branch_id,
            "total_tasks": 5,
            "completed_tasks": 2
        }
        mock_session.execute.return_value = mock_result

        branch_summary = await cascade_calculator._get_branch_summary(sample_branch_id)
        assert branch_summary is not None
        assert branch_summary["branch_id"] == sample_branch_id
        assert branch_summary["total_tasks"] == 5

        # Test project metrics query
        mock_result.fetchone.return_value._mapping = {
            "project_id": sample_project_id,
            "total_branches": 3,
            "overall_progress_percentage": 40
        }

        project_metrics = await cascade_calculator._get_project_metrics(sample_project_id)
        assert project_metrics is not None
        assert project_metrics["project_id"] == sample_project_id
        assert project_metrics["total_branches"] == 3

    @pytest.mark.asyncio
    async def test_parent_progress_calculation(
        self, cascade_calculator, mock_session, sample_task_id
    ):
        """Test parent progress calculation from subtasks"""

        # Mock query result with average progress
        mock_result = Mock()
        mock_result.fetchone.return_value = (75.0,)  # 75% average progress
        mock_session.execute.return_value = mock_result

        progress = await cascade_calculator._calculate_parent_progress(sample_task_id)
        assert progress == 75.0

        # Test with no subtasks
        mock_result.fetchone.return_value = (None,)
        progress = await cascade_calculator._calculate_parent_progress(sample_task_id)
        assert progress == 0.0

    @pytest.mark.asyncio
    async def test_context_cascade_calculation(
        self, cascade_calculator, mock_session, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test context cascade calculation"""

        context_id = str(uuid.uuid4())
        subtask_id = str(uuid.uuid4())

        # Mock context query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            (sample_task_id, sample_branch_id, sample_project_id, subtask_id)
        ]))
        mock_session.execute.return_value = mock_result

        # Execute cascade calculation
        result = await cascade_calculator.calculate_context_cascade(context_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == context_id
        assert result.entity_type == EntityType.CONTEXT

        # Verify affected entities
        assert context_id in result.affected_contexts
        assert sample_task_id in result.affected_tasks
        assert sample_branch_id in result.affected_branches
        assert sample_project_id in result.affected_projects
        assert subtask_id in result.affected_subtasks


class TestEntityTypeDetection:
    """Test suite for entity type auto-detection"""

    @pytest.mark.asyncio
    async def test_detect_task_type(self, cascade_calculator, mock_session):
        """Test detection of task entity type"""
        entity_id = str(uuid.uuid4())

        # Mock task found
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        entity_type = await cascade_calculator._detect_entity_type(entity_id)
        assert entity_type == EntityType.TASK

    @pytest.mark.asyncio
    async def test_detect_subtask_type(self, cascade_calculator, mock_session):
        """Test detection of subtask entity type"""
        entity_id = str(uuid.uuid4())

        # Mock task not found, subtask found
        mock_result_task = Mock()
        mock_result_task.scalar.return_value = 0
        mock_result_subtask = Mock()
        mock_result_subtask.scalar.return_value = 1

        mock_session.execute.side_effect = [mock_result_task, mock_result_subtask]

        entity_type = await cascade_calculator._detect_entity_type(entity_id)
        assert entity_type == EntityType.SUBTASK

    @pytest.mark.asyncio
    async def test_detect_branch_type(self, cascade_calculator, mock_session):
        """Test detection of branch entity type"""
        entity_id = str(uuid.uuid4())

        # Mock task and subtask not found, branch found
        mock_result_none = Mock()
        mock_result_none.scalar.return_value = 0
        mock_result_branch = Mock()
        mock_result_branch.scalar.return_value = 1

        mock_session.execute.side_effect = [
            mock_result_none, mock_result_none, mock_result_branch
        ]

        entity_type = await cascade_calculator._detect_entity_type(entity_id)
        assert entity_type == EntityType.BRANCH

    @pytest.mark.asyncio
    async def test_detect_project_type(self, cascade_calculator, mock_session):
        """Test detection of project entity type"""
        entity_id = str(uuid.uuid4())

        # Mock others not found, project found
        mock_result_none = Mock()
        mock_result_none.scalar.return_value = 0
        mock_result_project = Mock()
        mock_result_project.scalar.return_value = 1

        mock_session.execute.side_effect = [
            mock_result_none, mock_result_none, mock_result_none, mock_result_project
        ]

        entity_type = await cascade_calculator._detect_entity_type(entity_id)
        assert entity_type == EntityType.PROJECT

    @pytest.mark.asyncio
    async def test_detect_context_type_default(self, cascade_calculator, mock_session):
        """Test default to context type when entity not found"""
        entity_id = str(uuid.uuid4())

        # Mock all entities not found
        mock_result_none = Mock()
        mock_result_none.scalar.return_value = 0
        mock_session.execute.side_effect = [
            mock_result_none, mock_result_none, mock_result_none, mock_result_none
        ]

        entity_type = await cascade_calculator._detect_entity_type(entity_id)
        assert entity_type == EntityType.CONTEXT


class TestCascadeResultDataClass:
    """Test suite for CascadeResult dataclass"""

    def test_cascade_result_creation(self):
        """Test CascadeResult creation with all fields"""
        task_id = str(uuid.uuid4())

        result = CascadeResult(
            entity_id=task_id,
            entity_type=EntityType.TASK,
            affected_tasks={task_id},
            affected_subtasks=set(),
            affected_branches=set(),
            affected_projects=set(),
            affected_contexts=set(),
            calculation_time_ms=25.5,
            cache_hit=False
        )

        assert result.entity_id == task_id
        assert result.entity_type == EntityType.TASK
        assert result.calculation_time_ms == 25.5
        assert not result.cache_hit

    def test_get_all_affected_ids(self):
        """Test get_all_affected_ids method"""
        task_id = str(uuid.uuid4())
        subtask_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())

        result = CascadeResult(
            entity_id=task_id,
            entity_type=EntityType.TASK,
            affected_tasks={task_id},
            affected_subtasks={subtask_id},
            affected_branches={branch_id},
            affected_projects=set(),
            affected_contexts=set(),
            calculation_time_ms=0.0
        )

        all_ids = result.get_all_affected_ids()
        assert len(all_ids) == 3
        assert task_id in all_ids
        assert subtask_id in all_ids
        assert branch_id in all_ids

    def test_get_affected_count(self):
        """Test get_affected_count method"""
        result = CascadeResult(
            entity_id="test",
            entity_type=EntityType.TASK,
            affected_tasks={"task1", "task2"},
            affected_subtasks={"sub1"},
            affected_branches={"branch1"},
            affected_projects=set(),
            affected_contexts=set(),
            calculation_time_ms=0.0
        )

        count = result.get_affected_count()
        assert count == 4  # 2 tasks + 1 subtask + 1 branch


# Performance test configuration
pytest_plugins = ["pytest_asyncio"]