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
from fastmcp.task_management.domain.services.protocols.cascade_data_provider import (
    TaskCascadeData,
    SubtaskCascadeData,
    BranchCascadeData,
    ProjectCascadeData,
    ContextCascadeData
)


@pytest.fixture
def mock_data_provider():
    """Create a mock CascadeDataProvider"""
    provider = AsyncMock()

    # Configure default return values
    provider.get_task_subtask_ids.return_value = set()
    provider.get_task_parent_task_ids.return_value = set()
    provider.get_related_context_ids.return_value = set()

    return provider


@pytest.fixture
def cascade_calculator(mock_data_provider):
    """Create CascadeCalculator instance with mock data provider"""
    return CascadeCalculator(mock_data_provider)


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


@pytest.fixture
def sample_context_id():
    """Generate sample context UUID"""
    return str(uuid.uuid4())


class TestCascadeCalculator:
    """Test suite for CascadeCalculator"""

    @pytest.mark.asyncio
    async def test_task_cascade_calculation(
        self, cascade_calculator, mock_data_provider, sample_task_id, sample_branch_id, sample_project_id
    ):
        """Test task cascade returns correct affected entities"""

        # Mock task data from provider
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

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
        self, cascade_calculator, mock_data_provider, sample_subtask_id,
        sample_task_id, sample_branch_id, sample_project_id
    ):
        """Test subtask cascade propagates to parent task"""

        # Mock subtask data from provider
        subtask_data = SubtaskCascadeData(
            id=sample_subtask_id,
            task_id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_subtask_cascade_data.return_value = subtask_data

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
        self, cascade_calculator, mock_data_provider, sample_branch_id,
        sample_project_id, sample_task_id, sample_subtask_id
    ):
        """Test branch cascade affects project and all related entities"""

        # Mock branch data from provider
        branch_data = BranchCascadeData(
            id=sample_branch_id,
            project_id=sample_project_id,
            task_ids={sample_task_id},
            subtask_ids={sample_subtask_id}
        )
        mock_data_provider.get_branch_cascade_data.return_value = branch_data

        # Execute cascade calculation
        result = await cascade_calculator.calculate_branch_cascade(sample_branch_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_branch_id
        assert result.entity_type == EntityType.BRANCH

        # Verify cascade to project and all tasks/subtasks
        assert sample_branch_id in result.affected_branches
        assert sample_project_id in result.affected_projects
        assert sample_task_id in result.affected_tasks
        assert sample_subtask_id in result.affected_subtasks

    @pytest.mark.asyncio
    async def test_project_cascade_all_branches(
        self, cascade_calculator, mock_data_provider, sample_project_id,
        sample_branch_id, sample_task_id, sample_subtask_id
    ):
        """Test project cascade affects all branches and tasks"""

        # Create additional IDs for multiple branches
        branch_id_2 = str(uuid.uuid4())
        task_id_2 = str(uuid.uuid4())
        subtask_id_2 = str(uuid.uuid4())

        # Mock project data from provider
        project_data = ProjectCascadeData(
            id=sample_project_id,
            branch_ids={sample_branch_id, branch_id_2},
            task_ids={sample_task_id, task_id_2},
            subtask_ids={sample_subtask_id, subtask_id_2}
        )
        mock_data_provider.get_project_cascade_data.return_value = project_data

        # Execute cascade calculation
        result = await cascade_calculator.calculate_project_cascade(sample_project_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_project_id
        assert result.entity_type == EntityType.PROJECT

        # Verify all branches are affected
        assert sample_branch_id in result.affected_branches
        assert branch_id_2 in result.affected_branches

        # Verify all tasks are affected
        assert sample_task_id in result.affected_tasks
        assert task_id_2 in result.affected_tasks

        # Verify all subtasks are affected
        assert sample_subtask_id in result.affected_subtasks
        assert subtask_id_2 in result.affected_subtasks

        # Verify project itself is affected
        assert sample_project_id in result.affected_projects

    @pytest.mark.asyncio
    async def test_entity_type_detection(
        self, cascade_calculator, mock_data_provider, sample_task_id
    ):
        """Test automatic entity type detection"""

        # Mock entity type detection
        mock_data_provider.detect_entity_type.return_value = EntityType.TASK

        # Mock task data for when type is detected
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # Execute cascade with auto-detection
        result = await cascade_calculator.calculate_cascade(sample_task_id)

        # Verify type was detected and used
        assert result.entity_type == EntityType.TASK
        assert result.entity_id == sample_task_id
        mock_data_provider.detect_entity_type.assert_called_once_with(sample_task_id)

    @pytest.mark.asyncio
    async def test_deduplication_works_correctly(
        self, cascade_calculator, mock_data_provider, sample_task_id,
        sample_subtask_id, sample_branch_id, sample_project_id
    ):
        """Test that duplicate IDs are properly deduplicated"""

        # Setup task with subtasks
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # Return the same subtask multiple times (should be deduplicated)
        mock_data_provider.get_task_subtask_ids.return_value = {sample_subtask_id}

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(sample_task_id)

        # Verify deduplication - each ID should appear exactly once
        assert len(result.affected_tasks) == 1
        assert len(result.affected_subtasks) == 1
        assert sample_task_id in result.affected_tasks
        assert sample_subtask_id in result.affected_subtasks

    @pytest.mark.asyncio
    async def test_cache_functionality(
        self, cascade_calculator, mock_data_provider, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test cascade calculation caching works correctly"""

        # Mock task data
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # First call - should miss cache
        result1 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result1.cache_hit is False
        assert result1.entity_id == sample_task_id

        # Second call - should hit cache
        result2 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result2.cache_hit is True
        assert result2.entity_id == sample_task_id

        # Results should be identical
        assert result1.affected_tasks == result2.affected_tasks
        assert result1.affected_branches == result2.affected_branches
        assert result1.affected_projects == result2.affected_projects

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cascade_calculator, mock_data_provider):
        """Test cache expires after TTL"""
        sample_task_id = str(uuid.uuid4())
        sample_branch_id = str(uuid.uuid4())
        sample_project_id = str(uuid.uuid4())

        # Mock task data
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # Set very short TTL for testing
        cascade_calculator._cache_ttl_seconds = 0.1

        # First call - cache miss
        result1 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result1.cache_hit is False

        # Immediate second call - cache hit
        result2 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result2.cache_hit is True

        # Wait for cache to expire
        time.sleep(0.2)

        # Third call after expiration - cache miss
        result3 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result3.cache_hit is False

    @pytest.mark.asyncio
    async def test_cache_clear(self, cascade_calculator, mock_data_provider):
        """Test cache can be cleared manually"""
        sample_task_id = str(uuid.uuid4())
        sample_branch_id = str(uuid.uuid4())
        sample_project_id = str(uuid.uuid4())

        # Mock task data
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # First call - cache miss
        result1 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result1.cache_hit is False

        # Second call - cache hit
        result2 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result2.cache_hit is True

        # Clear cache
        cascade_calculator.clear_cache()

        # Third call after clear - cache miss
        result3 = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=True
        )
        assert result3.cache_hit is False

    @pytest.mark.asyncio
    async def test_performance_under_50ms(
        self, cascade_calculator, mock_data_provider, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test cascade calculation completes in under 50ms"""

        # Mock task data
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=None
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # Add some subtasks and parent tasks
        subtask_ids = {str(uuid.uuid4()) for _ in range(10)}
        parent_task_ids = {str(uuid.uuid4()) for _ in range(5)}
        mock_data_provider.get_task_subtask_ids.return_value = subtask_ids
        mock_data_provider.get_task_parent_task_ids.return_value = parent_task_ids

        # Execute cascade calculation with timing
        start_time = time.time()
        result = await cascade_calculator.calculate_cascade(
            sample_task_id,
            entity_type=EntityType.TASK,
            use_cache=False
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify performance requirement
        assert elapsed_ms < 50, f"Cascade calculation took {elapsed_ms:.2f}ms (should be < 50ms)"
        assert result.calculation_time_ms < 50

    @pytest.mark.asyncio
    async def test_missing_entity_handling(
        self, cascade_calculator, mock_data_provider, sample_task_id
    ):
        """Test handling of missing entities"""

        # Mock missing task
        mock_data_provider.get_task_cascade_data.return_value = None

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(sample_task_id)

        # Verify graceful handling
        assert result.entity_id == sample_task_id
        assert result.entity_type == EntityType.TASK
        assert len(result.affected_tasks) == 1  # Only the task itself
        assert sample_task_id in result.affected_tasks
        assert len(result.affected_branches) == 0
        assert len(result.affected_projects) == 0

    @pytest.mark.asyncio
    async def test_get_all_affected_ids(
        self, cascade_calculator, mock_data_provider, sample_task_id,
        sample_branch_id, sample_project_id
    ):
        """Test get_all_affected_ids returns union of all entity IDs"""

        # Mock task data with context
        context_id = str(uuid.uuid4())
        task_data = TaskCascadeData(
            id=sample_task_id,
            git_branch_id=sample_branch_id,
            project_id=sample_project_id,
            context_id=context_id
        )
        mock_data_provider.get_task_cascade_data.return_value = task_data

        # Execute cascade calculation
        result = await cascade_calculator.calculate_task_cascade(sample_task_id)

        # Get all affected IDs
        all_ids = result.get_all_affected_ids()

        # Verify all IDs are included
        assert sample_task_id in all_ids
        assert sample_branch_id in all_ids
        assert sample_project_id in all_ids
        assert context_id in all_ids

        # Verify count matches
        expected_count = 4  # task + branch + project + context
        assert len(all_ids) == expected_count
        assert result.get_affected_count() == expected_count

    @pytest.mark.asyncio
    async def test_context_cascade_calculation(
        self, cascade_calculator, mock_data_provider, sample_context_id,
        sample_task_id, sample_branch_id, sample_project_id
    ):
        """Test context cascade calculation"""

        # Mock context data
        context_data = ContextCascadeData(
            id=sample_context_id,
            task_ids={sample_task_id},
            branch_ids={sample_branch_id},
            project_ids={sample_project_id},
            subtask_ids=set()
        )
        mock_data_provider.get_context_cascade_data.return_value = context_data

        # Execute cascade calculation
        result = await cascade_calculator.calculate_context_cascade(sample_context_id)

        # Verify result structure
        assert isinstance(result, CascadeResult)
        assert result.entity_id == sample_context_id
        assert result.entity_type == EntityType.CONTEXT

        # Verify affected entities
        assert sample_context_id in result.affected_contexts
        assert sample_task_id in result.affected_tasks
        assert sample_branch_id in result.affected_branches
        assert sample_project_id in result.affected_projects


class TestCascadeResultDataClass:
    """Test suite for CascadeResult data class"""

    def test_cascade_result_creation(self):
        """Test CascadeResult can be created with all fields"""
        task_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())

        result = CascadeResult(
            entity_id=task_id,
            entity_type=EntityType.TASK,
            affected_tasks={task_id},
            affected_subtasks=set(),
            affected_branches={branch_id},
            affected_projects=set(),
            affected_contexts=set(),
            calculation_time_ms=10.5,
            cache_hit=False
        )

        assert result.entity_id == task_id
        assert result.entity_type == EntityType.TASK
        assert result.calculation_time_ms == 10.5
        assert result.cache_hit is False

    def test_get_all_affected_ids(self):
        """Test get_all_affected_ids combines all entity types"""
        task_id = str(uuid.uuid4())
        subtask_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())

        result = CascadeResult(
            entity_id=task_id,
            entity_type=EntityType.TASK,
            affected_tasks={task_id},
            affected_subtasks={subtask_id},
            affected_branches={branch_id},
            affected_projects={project_id},
            affected_contexts={context_id},
            calculation_time_ms=0.0
        )

        all_ids = result.get_all_affected_ids()

        assert len(all_ids) == 5
        assert task_id in all_ids
        assert subtask_id in all_ids
        assert branch_id in all_ids
        assert project_id in all_ids
        assert context_id in all_ids

    def test_get_affected_count(self):
        """Test get_affected_count returns correct total"""
        result = CascadeResult(
            entity_id=str(uuid.uuid4()),
            entity_type=EntityType.TASK,
            affected_tasks={str(uuid.uuid4()), str(uuid.uuid4())},
            affected_subtasks={str(uuid.uuid4())},
            affected_branches={str(uuid.uuid4())},
            affected_projects={str(uuid.uuid4())},
            affected_contexts=set(),
            calculation_time_ms=0.0
        )

        assert result.get_affected_count() == 5  # 2 tasks + 1 subtask + 1 branch + 1 project
