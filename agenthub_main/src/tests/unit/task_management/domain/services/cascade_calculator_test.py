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
    def mock_session(self):
        """Mock database session"""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def calculator(self, mock_session):
        """Create CascadeCalculator instance"""
        return CascadeCalculator(mock_session)
    
    @pytest.mark.asyncio
    async def test_init(self, mock_session):
        """Test initialization"""
        calculator = CascadeCalculator(mock_session)
        
        assert calculator.session == mock_session
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
    async def test_calculate_cascade_auto_detect_type(self, calculator, mock_session):
        """Test cascade calculation with auto-detected entity type"""
        # Mock entity type detection to return TASK
        calculator._detect_entity_type = AsyncMock(return_value=EntityType.TASK)
        
        # Mock task cascade calculation
        expected_result = CascadeResult(
            entity_id="test-id",
            entity_type=EntityType.TASK,
            affected_tasks={"test-id"},
            affected_subtasks=set(),
            affected_branches={"branch-id"},
            affected_projects={"proj-id"},
            affected_contexts=set(),
            calculation_time_ms=0.0
        )
        calculator.calculate_task_cascade = AsyncMock(return_value=expected_result)
        
        # Call without specifying entity type
        result = await calculator.calculate_cascade("test-id", entity_type=None)
        
        calculator._detect_entity_type.assert_called_once_with("test-id")
        calculator.calculate_task_cascade.assert_called_once_with("test-id")
    
    @pytest.mark.asyncio
    async def test_calculate_cascade_unsupported_type(self, calculator):
        """Test cascade calculation with unsupported entity type"""
        # Create a mock unsupported type
        mock_type = Mock()
        mock_type.value = "unsupported"
        
        with pytest.raises(ValueError, match="Unsupported entity type"):
            await calculator.calculate_cascade("test-id", entity_type=mock_type)
    
    @pytest.mark.asyncio
    async def test_calculate_cascade_performance_warning(self, calculator, mock_session, caplog):
        """Test performance warning when calculation exceeds 50ms"""
        # Mock slow cascade calculation
        expected_result = CascadeResult(
            entity_id="test-id",
            entity_type=EntityType.TASK,
            affected_tasks={"test-id"},
            affected_subtasks=set(),
            affected_branches=set(),
            affected_projects=set(),
            affected_contexts=set(),
            calculation_time_ms=0.0
        )
        
        # Mock slow execution
        async def slow_cascade(task_id):
            await asyncio.sleep(0.06)  # 60ms
            return expected_result
        
        import asyncio
        calculator.calculate_task_cascade = slow_cascade
        
        # Execute
        result = await calculator.calculate_cascade("test-id", EntityType.TASK, use_cache=False)
        
        # Check warning was logged
        assert "Cascade calculation exceeded 50ms" in caplog.text
        assert result.calculation_time_ms > 50
    
    @pytest.mark.asyncio
    async def test_calculate_task_cascade_success(self, calculator, mock_session):
        """Test successful task cascade calculation"""
        # Mock query results
        task_row = MagicMock()
        task_row.__getitem__.side_effect = lambda x: ["test-id", "branch-id", "proj-id", "ctx-id"][x]
        
        subtask_row = MagicMock()
        subtask_row.__getitem__.side_effect = lambda x: "sub-id"
        
        parent_row = MagicMock()
        parent_row.__getitem__.side_effect = lambda x: "parent-task-id"
        
        # Mock session executions
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = [
            Mock(fetchone=Mock(return_value=task_row)),       # task query
            Mock(__iter__=lambda x: iter([subtask_row])),     # subtasks query
            Mock(__iter__=lambda x: iter([parent_row])),      # parent tasks query
        ]
        
        # Mock related contexts
        calculator._get_related_contexts = AsyncMock(return_value={"ctx2", "ctx3"})
        
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
    async def test_calculate_task_cascade_not_found(self, calculator, mock_session):
        """Test task cascade when task not found"""
        # Mock empty result
        mock_session.execute = AsyncMock(return_value=Mock(fetchone=Mock(return_value=None)))
        
        # Execute
        result = await calculator.calculate_task_cascade("missing-id")
        
        # Verify result
        assert result.entity_id == "missing-id"
        assert result.entity_type == EntityType.TASK
        assert result.affected_tasks == {"missing-id"}
        assert len(result.affected_subtasks) == 0
        assert len(result.affected_branches) == 0
        assert len(result.affected_projects) == 0
        assert len(result.affected_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_subtask_cascade_success(self, calculator, mock_session):
        """Test successful subtask cascade calculation"""
        # Mock query result
        subtask_row = MagicMock()
        subtask_row.__getitem__.side_effect = lambda x: ["task-id", "branch-id", "proj-id", "ctx-id"][x]
        
        # Mock session execution
        mock_session.execute = AsyncMock(return_value=Mock(fetchone=Mock(return_value=subtask_row)))
        
        # Mock related contexts
        calculator._get_related_contexts = AsyncMock(return_value={"ctx2"})
        
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
    async def test_calculate_branch_cascade_success(self, calculator, mock_session):
        """Test successful branch cascade calculation"""
        # Mock query results
        rows = [
            MagicMock(__getitem__=lambda _, x: ["proj-id", "task1", "sub1"][x]),
            MagicMock(__getitem__=lambda _, x: ["proj-id", "task2", None][x]),
            MagicMock(__getitem__=lambda _, x: ["proj-id", "task3", "sub2"][x]),
        ]
        
        # Mock session execution
        mock_session.execute = AsyncMock(return_value=Mock(__iter__=lambda x: iter(rows)))
        
        # Mock related contexts
        calculator._get_related_contexts = AsyncMock(return_value={"ctx1", "ctx2"})
        
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
    async def test_calculate_project_cascade_success(self, calculator, mock_session):
        """Test successful project cascade calculation"""
        # Mock query results
        rows = [
            MagicMock(__getitem__=lambda _, x: ["branch1", "task1", "sub1"][x]),
            MagicMock(__getitem__=lambda _, x: ["branch2", "task2", None][x]),
            MagicMock(__getitem__=lambda _, x: ["branch2", "task3", "sub2"][x]),
        ]
        
        # Mock session execution
        mock_session.execute = AsyncMock(return_value=Mock(__iter__=lambda x: iter(rows)))
        
        # Mock related contexts for each branch
        calculator._get_related_contexts = AsyncMock(side_effect=[{"ctx1"}, {"ctx2"}])
        
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
    async def test_calculate_context_cascade_success(self, calculator, mock_session):
        """Test successful context cascade calculation"""
        # Mock query results
        rows = [
            MagicMock(__getitem__=lambda _, x: ["task1", "branch1", "proj1", "sub1"][x]),
            MagicMock(__getitem__=lambda _, x: ["task2", "branch2", "proj2", None][x]),
        ]
        
        # Mock session execution
        mock_session.execute = AsyncMock(return_value=Mock(__iter__=lambda x: iter(rows)))
        
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
    
    @pytest.mark.asyncio
    async def test_get_branch_summary(self, calculator, mock_session):
        """Test branch summary calculation"""
        # Mock query result
        result_row = MagicMock()
        result_row._mapping = {
            "branch_id": "branch-id",
            "project_id": "proj-id",
            "branch_name": "main",
            "total_tasks": 10,
            "completed_tasks": 3,
            "progress_percentage": 30.0
        }
        
        mock_session.execute = AsyncMock(return_value=Mock(fetchone=Mock(return_value=result_row)))
        
        # Execute
        summary = await calculator._get_branch_summary("branch-id")
        
        # Verify result
        assert summary["branch_id"] == "branch-id"
        assert summary["total_tasks"] == 10
        assert summary["completed_tasks"] == 3
        assert summary["progress_percentage"] == 30.0
    
    @pytest.mark.asyncio
    async def test_get_project_metrics(self, calculator, mock_session):
        """Test project metrics calculation"""
        # Mock query result
        result_row = MagicMock()
        result_row._mapping = {
            "project_id": "proj-id",
            "project_name": "Test Project",
            "total_branches": 5,
            "active_branches": 3,
            "total_tasks": 50,
            "completed_tasks": 20,
            "overall_progress_percentage": 40.0
        }
        
        mock_session.execute = AsyncMock(return_value=Mock(fetchone=Mock(return_value=result_row)))
        
        # Execute
        metrics = await calculator._get_project_metrics("proj-id")
        
        # Verify result
        assert metrics["project_id"] == "proj-id"
        assert metrics["total_branches"] == 5
        assert metrics["active_branches"] == 3
        assert metrics["total_tasks"] == 50
        assert metrics["overall_progress_percentage"] == 40.0
    
    @pytest.mark.asyncio
    async def test_calculate_parent_progress(self, calculator, mock_session):
        """Test parent task progress calculation"""
        # Mock query result
        result_row = MagicMock()
        result_row.__getitem__.side_effect = lambda x: 75.5
        
        mock_session.execute = AsyncMock(return_value=Mock(fetchone=Mock(return_value=result_row)))
        
        # Execute
        progress = await calculator._calculate_parent_progress("task-id")
        
        # Verify result
        assert progress == 75.5
    
    @pytest.mark.asyncio
    async def test_get_related_contexts_success(self, calculator, mock_session):
        """Test getting related contexts"""
        # Mock query results
        rows = [
            MagicMock(__getitem__=lambda _, x: "ctx1"),
            MagicMock(__getitem__=lambda _, x: "ctx2"),
        ]
        
        mock_session.execute = AsyncMock(return_value=Mock(__iter__=lambda x: iter(rows)))
        
        # Execute
        contexts = await calculator._get_related_contexts("branch-id", "proj-id")
        
        # Verify result
        assert "ctx1" in contexts
        assert "ctx2" in contexts
        assert len(contexts) == 2
    
    @pytest.mark.asyncio
    async def test_get_related_contexts_with_error(self, calculator, mock_session):
        """Test getting related contexts with error (graceful failure)"""
        # Mock execution error
        mock_session.execute = AsyncMock(side_effect=Exception("Column not found"))
        
        # Execute
        contexts = await calculator._get_related_contexts("branch-id", "proj-id")
        
        # Should return empty set (error is logged but not raised)
        assert len(contexts) == 0
    
    @pytest.mark.asyncio
    async def test_detect_entity_type_task(self, calculator, mock_session):
        """Test entity type detection for task"""
        # Mock query results
        mock_session.execute = AsyncMock(side_effect=[
            Mock(scalar=Mock(return_value=1)),  # task query returns 1
        ])
        
        # Execute
        entity_type = await calculator._detect_entity_type("entity-id")
        
        # Verify
        assert entity_type == EntityType.TASK
    
    @pytest.mark.asyncio
    async def test_detect_entity_type_subtask(self, calculator, mock_session):
        """Test entity type detection for subtask"""
        # Mock query results
        mock_session.execute = AsyncMock(side_effect=[
            Mock(scalar=Mock(return_value=0)),  # task query returns 0
            Mock(scalar=Mock(return_value=1)),  # subtask query returns 1
        ])
        
        # Execute
        entity_type = await calculator._detect_entity_type("entity-id")
        
        # Verify
        assert entity_type == EntityType.SUBTASK
    
    @pytest.mark.asyncio
    async def test_detect_entity_type_branch(self, calculator, mock_session):
        """Test entity type detection for branch"""
        # Mock query results
        mock_session.execute = AsyncMock(side_effect=[
            Mock(scalar=Mock(return_value=0)),  # task query
            Mock(scalar=Mock(return_value=0)),  # subtask query
            Mock(scalar=Mock(return_value=1)),  # branch query returns 1
        ])
        
        # Execute
        entity_type = await calculator._detect_entity_type("entity-id")
        
        # Verify
        assert entity_type == EntityType.BRANCH
    
    @pytest.mark.asyncio
    async def test_detect_entity_type_project(self, calculator, mock_session):
        """Test entity type detection for project"""
        # Mock query results
        mock_session.execute = AsyncMock(side_effect=[
            Mock(scalar=Mock(return_value=0)),  # task query
            Mock(scalar=Mock(return_value=0)),  # subtask query
            Mock(scalar=Mock(return_value=0)),  # branch query
            Mock(scalar=Mock(return_value=1)),  # project query returns 1
        ])
        
        # Execute
        entity_type = await calculator._detect_entity_type("entity-id")
        
        # Verify
        assert entity_type == EntityType.PROJECT
    
    @pytest.mark.asyncio
    async def test_detect_entity_type_default_context(self, calculator, mock_session):
        """Test entity type detection defaults to context"""
        # Mock all queries returning 0
        mock_session.execute = AsyncMock(side_effect=[
            Mock(scalar=Mock(return_value=0)),  # task query
            Mock(scalar=Mock(return_value=0)),  # subtask query
            Mock(scalar=Mock(return_value=0)),  # branch query
            Mock(scalar=Mock(return_value=0)),  # project query
        ])
        
        # Execute
        entity_type = await calculator._detect_entity_type("entity-id")
        
        # Verify defaults to context
        assert entity_type == EntityType.CONTEXT
    
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