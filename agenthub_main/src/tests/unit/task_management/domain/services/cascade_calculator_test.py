"""Unit tests for CascadeCalculator domain service"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import time
import uuid

from fastmcp.task_management.domain.services.cascade_calculator import (
    CascadeCalculator,
    CascadeResult,
    EntityType
)


class TestCascadeResult:
    """Test CascadeResult dataclass methods"""
    
    def test_get_all_affected_ids(self):
        """Test getting all affected entity IDs"""
        result = CascadeResult(
            entity_id="test-id",
            entity_type=EntityType.TASK,
            affected_tasks={"task1", "task2"},
            affected_subtasks={"sub1", "sub2"},
            affected_branches={"branch1"},
            affected_projects={"proj1"},
            affected_contexts={"ctx1", "ctx2"},
            calculation_time_ms=10.5
        )
        
        all_ids = result.get_all_affected_ids()
        
        assert len(all_ids) == 8
        assert "task1" in all_ids
        assert "task2" in all_ids
        assert "sub1" in all_ids
        assert "sub2" in all_ids
        assert "branch1" in all_ids
        assert "proj1" in all_ids
        assert "ctx1" in all_ids
        assert "ctx2" in all_ids
    
    def test_get_affected_count(self):
        """Test getting total count of affected entities"""
        result = CascadeResult(
            entity_id="test-id",
            entity_type=EntityType.TASK,
            affected_tasks={"task1", "task2"},
            affected_subtasks={"sub1"},
            affected_branches={"branch1"},
            affected_projects={"proj1"},
            affected_contexts=set(),
            calculation_time_ms=10.5
        )
        
        assert result.get_affected_count() == 5


class TestEntityType:
    """Test EntityType enum"""
    
    def test_entity_type_values(self):
        """Test that entity types have correct values"""
        assert EntityType.TASK.value == "task"
        assert EntityType.SUBTASK.value == "subtask"
        assert EntityType.BRANCH.value == "branch"
        assert EntityType.PROJECT.value == "project"
        assert EntityType.CONTEXT.value == "context"


class TestCascadeCalculator:
    """Test CascadeCalculator service"""

    @pytest.fixture
    def mock_data_provider(self):
        """Mock data provider for cascade calculator"""
        data_provider = AsyncMock()
        return data_provider

    @pytest.fixture
    def calculator(self, mock_data_provider):
        """Create CascadeCalculator instance"""
        return CascadeCalculator(mock_data_provider)

    @pytest.mark.asyncio
    async def test_init(self, mock_data_provider):
        """Test initialization"""
        calculator = CascadeCalculator(mock_data_provider)

        assert calculator._data_provider == mock_data_provider
        assert calculator._cache == {}
        assert calculator._cache_ttl_seconds == 300
        assert calculator._cache_timestamps == {}
    
    @pytest.mark.asyncio
    async def test_calculate_cascade_with_cache_hit(self, calculator):
        """Test cascade calculation with cache hit"""
        # Prepare cached result
        cached_result = CascadeResult(
            entity_id="test-id",
            entity_type=EntityType.TASK,
            affected_tasks={"test-id"},
            affected_subtasks=set(),
            affected_branches=set(),
            affected_projects=set(),
            affected_contexts=set(),
            calculation_time_ms=5.0,
            cache_hit=False
        )
        
        calculator._cache["test-id:task"] = cached_result
        calculator._cache_timestamps["test-id:task"] = time.time()
        
        # Call with cache enabled
        result = await calculator.calculate_cascade("test-id", EntityType.TASK, use_cache=True)
        
        assert result.cache_hit == True
        assert result.entity_id == "test-id"
    
    @pytest.mark.asyncio
    async def test_calculate_cascade_with_entity_type(self, calculator, mock_data_provider):
        """Test cascade calculation with explicitly specified entity type"""
        # Setup mock data provider to return task data
        mock_task_data = Mock()
        mock_task_data.git_branch_id = "branch-id"
        mock_task_data.project_id = "proj-id"
        mock_task_data.context_id = "ctx-id"

        mock_data_provider.get_task_cascade_data.return_value = mock_task_data
        mock_data_provider.get_task_subtask_ids.return_value = set()
        mock_data_provider.get_task_parent_task_ids.return_value = set()
        mock_data_provider.get_related_context_ids.return_value = set()

        # Call with explicit entity type
        result = await calculator.calculate_cascade("test-id", entity_type=EntityType.TASK)

        # Verify data provider was called
        mock_data_provider.get_task_cascade_data.assert_called_once_with("test-id")

        # Verify result structure
        assert result.entity_id == "test-id"
        assert result.entity_type == EntityType.TASK
    
    @pytest.mark.asyncio
    async def test_calculate_cascade_with_explicit_type(self, calculator, mock_data_provider):
        """Test cascade calculation with explicitly specified entity type"""
        # Setup mock for branch cascade
        mock_branch_data = Mock()
        mock_branch_data.project_id = "proj-id"
        mock_branch_data.task_ids = set()
        mock_branch_data.subtask_ids = set()

        mock_data_provider.get_branch_cascade_data.return_value = mock_branch_data
        mock_data_provider.get_related_context_ids.return_value = set()

        # Call with explicit BRANCH entity type
        result = await calculator.calculate_cascade("test-id", entity_type=EntityType.BRANCH)

        # Verify it called branch cascade
        mock_data_provider.get_branch_cascade_data.assert_called_once_with("test-id")
        assert result.entity_type == EntityType.BRANCH
    
    @pytest.mark.asyncio
    async def test_calculate_cascade_performance_warning(self, calculator, mock_data_provider, caplog):
        """Test performance warning when calculation exceeds 50ms"""
        import asyncio

        # Setup mock data provider with slow response
        mock_task_data = Mock()
        mock_task_data.git_branch_id = "branch-id"
        mock_task_data.project_id = "proj-id"
        mock_task_data.context_id = None

        async def slow_get_task_data(task_id):
            await asyncio.sleep(0.06)  # 60ms delay
            return mock_task_data

        mock_data_provider.get_task_cascade_data = slow_get_task_data
        mock_data_provider.get_task_subtask_ids.return_value = set()
        mock_data_provider.get_task_parent_task_ids.return_value = set()
        mock_data_provider.get_related_context_ids.return_value = set()

        # Execute
        result = await calculator.calculate_cascade("test-id", EntityType.TASK, use_cache=False)

        # Check warning was logged
        assert "Cascade calculation exceeded 50ms" in caplog.text
        assert result.calculation_time_ms > 50
    
    @pytest.mark.asyncio
    async def test_calculate_task_cascade_success(self, calculator, mock_data_provider):
        """Test successful task cascade calculation"""
        # Setup mock data provider
        mock_task_data = Mock()
        mock_task_data.git_branch_id = "branch-id"
        mock_task_data.project_id = "proj-id"
        mock_task_data.context_id = "ctx-id"

        mock_data_provider.get_task_cascade_data.return_value = mock_task_data
        mock_data_provider.get_task_subtask_ids.return_value = {"sub-id"}
        mock_data_provider.get_task_parent_task_ids.return_value = {"parent-task-id"}
        mock_data_provider.get_related_context_ids.return_value = {"ctx2", "ctx3"}

        # Execute
        result = await calculator.calculate_task_cascade("test-id")

        # Verify result
        assert result.entity_id == "test-id"
        assert result.entity_type == EntityType.TASK
        assert "test-id" in result.affected_tasks
        assert "parent-task-id" in result.affected_tasks
        assert "sub-id" in result.affected_subtasks
        assert "branch-id" in result.affected_branches
        assert "proj-id" in result.affected_projects
        assert "ctx-id" in result.affected_contexts
        assert "ctx2" in result.affected_contexts
        assert "ctx3" in result.affected_contexts
    
    @pytest.mark.asyncio
    async def test_calculate_task_cascade_not_found(self, calculator, mock_data_provider):
        """Test task cascade when task not found"""
        # Mock data provider to return None (task not found)
        mock_data_provider.get_task_cascade_data.return_value = None

        # Execute
        result = await calculator.calculate_task_cascade("missing-id")

        # Verify result - only the task ID itself is in affected_tasks
        assert result.entity_id == "missing-id"
        assert result.entity_type == EntityType.TASK
        assert result.affected_tasks == {"missing-id"}
        assert len(result.affected_subtasks) == 0
        assert len(result.affected_branches) == 0
        assert len(result.affected_projects) == 0
        assert len(result.affected_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_subtask_cascade_success(self, calculator, mock_data_provider):
        """Test successful subtask cascade calculation"""
        # Setup mock data provider
        mock_subtask_data = Mock()
        mock_subtask_data.task_id = "task-id"
        mock_subtask_data.git_branch_id = "branch-id"
        mock_subtask_data.project_id = "proj-id"
        mock_subtask_data.context_id = "ctx-id"

        mock_data_provider.get_subtask_cascade_data.return_value = mock_subtask_data
        mock_data_provider.get_related_context_ids.return_value = {"ctx2"}

        # Execute
        result = await calculator.calculate_subtask_cascade("sub-id")

        # Verify result
        assert result.entity_id == "sub-id"
        assert result.entity_type == EntityType.SUBTASK
        assert "task-id" in result.affected_tasks
        assert "sub-id" in result.affected_subtasks
        assert "branch-id" in result.affected_branches
        assert "proj-id" in result.affected_projects
        assert "ctx-id" in result.affected_contexts
        assert "ctx2" in result.affected_contexts
    
    @pytest.mark.asyncio
    async def test_calculate_branch_cascade_success(self, calculator, mock_data_provider):
        """Test successful branch cascade calculation"""
        # Setup mock data provider
        mock_branch_data = Mock()
        mock_branch_data.project_id = "proj-id"
        mock_branch_data.task_ids = {"task1", "task2", "task3"}
        mock_branch_data.subtask_ids = {"sub1", "sub2"}

        mock_data_provider.get_branch_cascade_data.return_value = mock_branch_data
        mock_data_provider.get_related_context_ids.return_value = {"ctx1", "ctx2"}

        # Execute
        result = await calculator.calculate_branch_cascade("branch-id")

        # Verify result
        assert result.entity_id == "branch-id"
        assert result.entity_type == EntityType.BRANCH
        assert "branch-id" in result.affected_branches
        assert "proj-id" in result.affected_projects
        assert "task1" in result.affected_tasks
        assert "task2" in result.affected_tasks
        assert "task3" in result.affected_tasks
        assert "sub1" in result.affected_subtasks
        assert "sub2" in result.affected_subtasks
        assert "ctx1" in result.affected_contexts
        assert "ctx2" in result.affected_contexts
    
    @pytest.mark.asyncio
    async def test_calculate_project_cascade_success(self, calculator, mock_data_provider):
        """Test successful project cascade calculation"""
        # Setup mock data provider
        mock_project_data = Mock()
        mock_project_data.branch_ids = {"branch1", "branch2"}
        mock_project_data.task_ids = {"task1", "task2", "task3"}
        mock_project_data.subtask_ids = {"sub1", "sub2"}

        mock_data_provider.get_project_cascade_data.return_value = mock_project_data
        # Return different contexts for each branch
        mock_data_provider.get_related_context_ids.side_effect = [{"ctx1"}, {"ctx2"}]

        # Execute
        result = await calculator.calculate_project_cascade("proj-id")

        # Verify result
        assert result.entity_id == "proj-id"
        assert result.entity_type == EntityType.PROJECT
        assert "proj-id" in result.affected_projects
        assert "branch1" in result.affected_branches
        assert "branch2" in result.affected_branches
        assert "task1" in result.affected_tasks
        assert "task2" in result.affected_tasks
        assert "task3" in result.affected_tasks
        assert "sub1" in result.affected_subtasks
        assert "sub2" in result.affected_subtasks
        assert "ctx1" in result.affected_contexts
        assert "ctx2" in result.affected_contexts
    
    @pytest.mark.asyncio
    async def test_calculate_context_cascade_success(self, calculator, mock_data_provider):
        """Test successful context cascade calculation"""
        # Setup mock data provider
        mock_context_data = Mock()
        mock_context_data.task_ids = {"task1", "task2"}
        mock_context_data.branch_ids = {"branch1", "branch2"}
        mock_context_data.project_ids = {"proj1", "proj2"}
        mock_context_data.subtask_ids = {"sub1"}

        mock_data_provider.get_context_cascade_data.return_value = mock_context_data

        # Execute
        result = await calculator.calculate_context_cascade("ctx-id")

        # Verify result
        assert result.entity_id == "ctx-id"
        assert result.entity_type == EntityType.CONTEXT
        assert "ctx-id" in result.affected_contexts
        assert "task1" in result.affected_tasks
        assert "task2" in result.affected_tasks
        assert "branch1" in result.affected_branches
        assert "branch2" in result.affected_branches
        assert "proj1" in result.affected_projects
        assert "proj2" in result.affected_projects
        assert "sub1" in result.affected_subtasks

    # NOTE: Tests for private methods (_get_branch_summary, _get_project_metrics,
    # _calculate_parent_progress, _get_related_contexts, _detect_entity_type) have been
    # removed as these methods no longer exist in the refactored implementation.
    # The new implementation uses a CascadeDataProvider protocol which encapsulates
    # these concerns at the infrastructure layer.

    def test_is_cache_valid_no_entry(self, calculator):
        """Test cache validity check with no entry"""
        assert calculator._is_cache_valid("missing-key") == False
    
    def test_is_cache_valid_expired(self, calculator):
        """Test cache validity check with expired entry"""
        # Add entry with old timestamp
        calculator._cache["test-key"] = Mock()
        calculator._cache_timestamps["test-key"] = time.time() - 400  # 400 seconds ago
        
        assert calculator._is_cache_valid("test-key") == False
    
    def test_is_cache_valid_fresh(self, calculator):
        """Test cache validity check with fresh entry"""
        # Add entry with recent timestamp
        calculator._cache["test-key"] = Mock()
        calculator._cache_timestamps["test-key"] = time.time() - 100  # 100 seconds ago
        
        assert calculator._is_cache_valid("test-key") == True
    
    def test_clear_cache(self, calculator):
        """Test cache clearing"""
        # Add some cache entries
        calculator._cache["key1"] = Mock()
        calculator._cache["key2"] = Mock()
        calculator._cache_timestamps["key1"] = time.time()
        calculator._cache_timestamps["key2"] = time.time()
        
        # Clear cache
        calculator.clear_cache()
        
        # Verify cache is empty
        assert len(calculator._cache) == 0
        assert len(calculator._cache_timestamps) == 0
    
    def test_get_cache_stats(self, calculator):
        """Test getting cache statistics"""
        # Add some cache entries
        calculator._cache["key1"] = Mock()
        calculator._cache["key2"] = Mock()
        calculator._cache_ttl_seconds = 600
        
        # Get stats
        stats = calculator.get_cache_stats()
        
        # Verify stats
        assert stats["cache_size"] == 2
        assert "key1" in stats["cache_entries"]
        assert "key2" in stats["cache_entries"]
        assert stats["cache_ttl_seconds"] == 600