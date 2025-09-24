"""
Test Suite for Batch Context Operations

Tests batch operations for context management including create, update, delete,
and upsert operations with various execution modes (transactional, sequential, parallel).
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastmcp.task_management.application.use_cases.batch_context_operations import (
    BatchContextOperations,
    BatchOperation,
    BatchOperationType,
    BatchOperationResult
)
from fastmcp.task_management.domain.models.unified_context import ContextLevel


class TestBatchContextOperations:
    """Test suite for BatchContextOperations"""
    
    @pytest.fixture
    def mock_context_service(self):
        """Create mock context service"""
        service = Mock()
        service.create_context = AsyncMock()
        service.update_context = AsyncMock()
        service.delete_context = AsyncMock()
        service.get_context = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock cache"""
        cache = Mock()
        cache.invalidate_context = Mock()
        cache.invalidate_inheritance = Mock()
        return cache
    
    @pytest.fixture
    @patch('fastmcp.task_management.application.use_cases.batch_context_operations.get_context_cache')
    def batch_operations(self, mock_get_cache, mock_context_service, mock_cache):
        """Create BatchContextOperations instance"""
        mock_get_cache.return_value = mock_cache
        return BatchContextOperations(mock_context_service)
    
    def create_test_operations(self, count: int = 3) -> List[BatchOperation]:
        """Create test batch operations"""
        operations = []
        for i in range(count):
            op = BatchOperation(
                operation=BatchOperationType.CREATE,
                level=ContextLevel.PROJECT,
                context_id=f"proj_{i}",
                data={"name": f"Project {i}", "index": i},
                user_id=f"user_{i}",
                project_id=f"proj_{i}"
            )
            operations.append(op)
        return operations
    
    @pytest.mark.asyncio
    async def test_execute_batch_sequential_success(self, batch_operations, mock_context_service):
        """Test successful sequential batch execution"""
        # Setup
        operations = self.create_test_operations(3)
        mock_context_service.create_context.return_value = {"success": True}
        
        # Execute
        results = await batch_operations.execute_batch(
            operations=operations,
            transaction=False,
            parallel=False,
            stop_on_error=True,
            user_id="default_user"
        )
        
        # Verify
        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_context_service.create_context.call_count == 3
        
        # Verify sequential execution
        for i, op in enumerate(operations):
            assert results[i].operation == op
            assert results[i].execution_time_ms is not None
            assert results[i].execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_batch_with_default_user_id(self, batch_operations, mock_context_service):
        """Test batch execution applies default user_id"""
        # Create operations without user_id
        operations = [
            BatchOperation(
                operation=BatchOperationType.CREATE,
                level=ContextLevel.PROJECT,
                context_id="proj_1",
                data={"name": "Project 1"}
            )
        ]
        
        mock_context_service.create_context.return_value = {"success": True}
        
        # Execute with default user_id
        results = await batch_operations.execute_batch(
            operations=operations,
            user_id="default_user"
        )
        
        # Verify user_id was applied
        assert operations[0].user_id == "default_user"
        mock_context_service.create_context.assert_called_once()
        call_args = mock_context_service.create_context.call_args
        assert call_args.kwargs['user_id'] == "default_user"
    
    @pytest.mark.asyncio
    async def test_execute_batch_stop_on_error(self, batch_operations, mock_context_service):
        """Test batch execution stops on error when configured"""
        operations = self.create_test_operations(5)
        
        # Make third operation fail
        mock_context_service.create_context.side_effect = [
            {"success": True},
            {"success": True},
            Exception("Operation failed"),
            {"success": True},
            {"success": True}
        ]
        
        # Execute
        results = await batch_operations.execute_batch(
            operations=operations,
            stop_on_error=True
        )
        
        # Verify
        assert len(results) == 5
        assert results[0].success is True
        assert results[1].success is True
        assert results[2].success is False
        assert "Operation failed" in results[2].error
        
        # Remaining operations should be marked as rolled back (since transaction=True)
        assert results[3].success is False
        assert "Transaction rolled back" in results[3].error
        assert results[4].success is False
        assert "Transaction rolled back" in results[4].error
        
        # Only first 3 operations should have been attempted
        assert mock_context_service.create_context.call_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_batch_continue_on_error(self, batch_operations, mock_context_service):
        """Test batch execution continues on error when configured"""
        operations = self.create_test_operations(5)
        
        # Make third operation fail
        mock_context_service.create_context.side_effect = [
            {"success": True},
            {"success": True},
            Exception("Operation failed"),
            {"success": True},
            {"success": True}
        ]
        
        # Execute
        results = await batch_operations.execute_batch(
            operations=operations,
            stop_on_error=False
        )
        
        # Verify
        assert len(results) == 5
        assert results[0].success is True
        assert results[1].success is True
        assert results[2].success is False
        assert results[3].success is True
        assert results[4].success is True
        
        # All operations should have been attempted
        assert mock_context_service.create_context.call_count == 5
    
    @pytest.mark.asyncio
    async def test_execute_batch_transactional(self, batch_operations, mock_context_service):
        """Test transactional batch execution"""
        operations = self.create_test_operations(3)
        mock_context_service.create_context.return_value = {"success": True}
        
        # Execute
        results = await batch_operations.execute_batch(
            operations=operations,
            transaction=True,
            parallel=False
        )
        
        # Verify all succeeded
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_execute_batch_transactional_rollback(self, batch_operations, mock_context_service):
        """Test transactional rollback on error"""
        operations = self.create_test_operations(5)
        
        # Make third operation fail
        mock_context_service.create_context.side_effect = [
            {"success": True},
            {"success": True},
            Exception("Transaction failed"),
            {"success": True},
            {"success": True}
        ]
        
        # Execute
        results = await batch_operations.execute_batch(
            operations=operations,
            transaction=True,
            stop_on_error=True
        )
        
        # Verify
        assert len(results) == 5
        
        # First two should show success (before rollback)
        assert results[0].success is True
        assert results[1].success is True
        
        # Failed operation
        assert results[2].success is False
        assert "Transaction failed" in results[2].error
        
        # Remaining marked as rolled back
        assert results[3].success is False
        assert "Transaction rolled back" in results[3].error
        assert results[4].success is False
        assert "Transaction rolled back" in results[4].error
    
    @pytest.mark.asyncio
    async def test_execute_batch_parallel(self, batch_operations, mock_context_service):
        """Test parallel batch execution"""
        operations = self.create_test_operations(5)
        
        # Track execution order
        execution_order = []
        
        async def mock_create(**kwargs):
            execution_order.append(kwargs['context_id'])
            await asyncio.sleep(0.01)  # Small delay to test parallelism
            return {"success": True}
        
        mock_context_service.create_context = mock_create
        
        # Execute
        start_time = datetime.now(timezone.utc)
        results = await batch_operations.execute_batch(
            operations=operations,
            transaction=False,
            parallel=True
        )
        end_time = datetime.now(timezone.utc)
        
        # Verify
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # Execution should be faster than sequential (rough check)
        total_time = (end_time - start_time).total_seconds()
        assert total_time < 0.05 * 5  # Should be faster than 5 sequential operations
    
    @pytest.mark.asyncio
    async def test_execute_batch_parallel_with_errors(self, batch_operations, mock_context_service):
        """Test parallel execution with some failures"""
        operations = self.create_test_operations(5)
        
        # Make some operations fail
        async def mock_create(**kwargs):
            if kwargs['context_id'] in ['proj_1', 'proj_3']:
                raise Exception(f"Failed {kwargs['context_id']}")
            return {"success": True}
        
        mock_context_service.create_context = mock_create
        
        # Execute
        results = await batch_operations.execute_batch(
            operations=operations,
            parallel=True,
            stop_on_error=False
        )
        
        # Verify
        assert len(results) == 5
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert results[3].success is False
        assert results[4].success is True
    
    @pytest.mark.asyncio
    async def test_execute_single_operation_create(self, batch_operations, mock_context_service):
        """Test executing single CREATE operation"""
        op = BatchOperation(
            operation=BatchOperationType.CREATE,
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "Project 1"},
            user_id="user1",
            project_id="proj_1"
        )
        
        mock_context_service.create_context.return_value = {"id": "proj_1", "success": True}
        
        result = await batch_operations._execute_single_operation(op)
        
        assert result == {"id": "proj_1", "success": True}
        mock_context_service.create_context.assert_called_once_with(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "Project 1"},
            user_id="user1",
            project_id="proj_1",
            git_branch_id=None
        )
    
    @pytest.mark.asyncio
    async def test_execute_single_operation_update(self, batch_operations, mock_context_service):
        """Test executing single UPDATE operation"""
        op = BatchOperation(
            operation=BatchOperationType.UPDATE,
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "Updated Project"},
            user_id="user1",
            propagate_changes=False
        )
        
        mock_context_service.update_context.return_value = {"success": True}
        
        result = await batch_operations._execute_single_operation(op)
        
        mock_context_service.update_context.assert_called_once_with(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "Updated Project"},
            user_id="user1",
            propagate_changes=False
        )
    
    @pytest.mark.asyncio
    async def test_execute_single_operation_delete(self, batch_operations, mock_context_service):
        """Test executing single DELETE operation"""
        op = BatchOperation(
            operation=BatchOperationType.DELETE,
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            user_id="user1"
        )
        
        mock_context_service.delete_context.return_value = {"success": True}
        
        result = await batch_operations._execute_single_operation(op)
        
        mock_context_service.delete_context.assert_called_once_with(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            user_id="user1"
        )
    
    @pytest.mark.asyncio
    async def test_execute_single_operation_upsert_existing(self, batch_operations, mock_context_service):
        """Test UPSERT operation on existing context"""
        op = BatchOperation(
            operation=BatchOperationType.UPSERT,
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "Upserted Project"},
            user_id="user1"
        )
        
        # Context exists
        mock_context_service.get_context.return_value = {"id": "proj_1", "existing": True}
        mock_context_service.update_context.return_value = {"success": True}
        
        result = await batch_operations._execute_single_operation(op)
        
        # Should update existing
        mock_context_service.get_context.assert_called_once()
        mock_context_service.update_context.assert_called_once()
        mock_context_service.create_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_single_operation_upsert_new(self, batch_operations, mock_context_service):
        """Test UPSERT operation on non-existing context"""
        op = BatchOperation(
            operation=BatchOperationType.UPSERT,
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "New Project"},
            user_id="user1",
            project_id="proj_1"
        )
        
        # Context doesn't exist
        mock_context_service.get_context.return_value = None
        mock_context_service.create_context.return_value = {"success": True}
        
        result = await batch_operations._execute_single_operation(op)
        
        # Should create new
        mock_context_service.get_context.assert_called_once()
        mock_context_service.create_context.assert_called_once()
        mock_context_service.update_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_single_operation_unknown_type(self, batch_operations):
        """Test executing operation with unknown type"""
        op = BatchOperation(
            operation="unknown",  # Invalid type
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            user_id="user1"
        )
        
        with pytest.raises(ValueError, match="Unknown operation type"):
            await batch_operations._execute_single_operation(op)
    
    @pytest.mark.asyncio
    async def test_invalidate_caches(self, batch_operations, mock_cache):
        """Test cache invalidation after operations"""
        operations = [
            BatchOperation(
                operation=BatchOperationType.CREATE,
                level=ContextLevel.PROJECT,
                context_id="proj_1",
                user_id="user1"
            ),
            BatchOperation(
                operation=BatchOperationType.UPDATE,
                level=ContextLevel.BRANCH,
                context_id="branch_1",
                user_id="user2"
            ),
            BatchOperation(
                operation=BatchOperationType.DELETE,
                level=ContextLevel.TASK,
                context_id="task_1",
                user_id="user3"
            )
        ]
        
        await batch_operations._invalidate_caches(operations, "default_user")
        
        # Verify cache invalidation (skip DELETE operations)
        assert mock_cache.invalidate_context.call_count == 2
        assert mock_cache.invalidate_inheritance.call_count == 2
        
        # Check specific calls
        mock_cache.invalidate_context.assert_any_call(
            user_id="user1",
            level="project",
            context_id="proj_1"
        )
        mock_cache.invalidate_context.assert_any_call(
            user_id="user2",
            level="branch",
            context_id="branch_1"
        )
    
    @pytest.mark.asyncio
    async def test_bulk_create(self, batch_operations, mock_context_service):
        """Test bulk create convenience method"""
        contexts = [
            {
                'context_id': 'proj_1',
                'data': {'name': 'Project 1'},
                'project_id': 'proj_1'
            },
            {
                'context_id': 'proj_2',
                'data': {'name': 'Project 2'},
                'project_id': 'proj_2',
                'git_branch_id': 'branch_1'
            }
        ]
        
        mock_context_service.create_context.return_value = {"success": True}
        
        results = await batch_operations.bulk_create(
            contexts=contexts,
            level=ContextLevel.PROJECT,
            user_id="user1",
            transaction=True
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_context_service.create_context.call_count == 2
    
    @pytest.mark.asyncio
    async def test_bulk_update(self, batch_operations, mock_context_service):
        """Test bulk update convenience method"""
        updates = [
            {
                'context_id': 'proj_1',
                'data': {'status': 'active'},
                'propagate_changes': True
            },
            {
                'context_id': 'proj_2',
                'data': {'status': 'inactive'},
                'propagate_changes': False
            }
        ]
        
        mock_context_service.update_context.return_value = {"success": True}
        
        results = await batch_operations.bulk_update(
            updates=updates,
            level=ContextLevel.PROJECT,
            user_id="user1",
            transaction=False,
            parallel=True
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_copy_contexts(self, batch_operations, mock_context_service):
        """Test copying contexts between branches"""
        # Mock source branch context
        source_context = {
            'level': 'branch',
            'context_id': 'source_branch',
            'data': {
                'name': 'Source Branch',
                'config': {'key': 'value'}
            }
        }
        
        mock_context_service.get_context.return_value = source_context
        mock_context_service.create_context.return_value = {"success": True}
        
        results = await batch_operations.copy_contexts(
            source_branch_id="source_branch",
            target_branch_id="target_branch",
            user_id="user1",
            include_task_contexts=False
        )
        
        assert len(results) == 1
        assert results[0].operation.operation == BatchOperationType.UPSERT
        assert results[0].operation.context_id == "target_branch"
        assert results[0].operation.data == source_context['data']
    
    @pytest.mark.asyncio
    async def test_copy_contexts_no_source(self, batch_operations, mock_context_service):
        """Test copying when source has no contexts"""
        mock_context_service.get_context.return_value = None
        
        results = await batch_operations.copy_contexts(
            source_branch_id="source_branch",
            target_branch_id="target_branch",
            user_id="user1"
        )
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_batch_operation_result_timing(self, batch_operations, mock_context_service):
        """Test that execution time is properly recorded"""
        op = BatchOperation(
            operation=BatchOperationType.CREATE,
            level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"name": "Project 1"},
            user_id="user1"
        )
        
        # Add delay to mock operation
        async def slow_create(**kwargs):
            await asyncio.sleep(0.01)
            return {"success": True}
        
        mock_context_service.create_context = slow_create
        
        results = await batch_operations.execute_batch([op])
        
        assert results[0].execution_time_ms >= 10  # At least 10ms
        assert results[0].execution_time_ms < 100  # But reasonable
    
    @pytest.mark.asyncio
    async def test_mixed_operation_types(self, batch_operations, mock_context_service):
        """Test batch with mixed operation types"""
        operations = [
            BatchOperation(
                operation=BatchOperationType.CREATE,
                level=ContextLevel.PROJECT,
                context_id="proj_1",
                data={"name": "New Project"},
                user_id="user1"
            ),
            BatchOperation(
                operation=BatchOperationType.UPDATE,
                level=ContextLevel.PROJECT,
                context_id="proj_2",
                data={"status": "active"},
                user_id="user1"
            ),
            BatchOperation(
                operation=BatchOperationType.DELETE,
                level=ContextLevel.PROJECT,
                context_id="proj_3",
                user_id="user1"
            ),
            BatchOperation(
                operation=BatchOperationType.UPSERT,
                level=ContextLevel.PROJECT,
                context_id="proj_4",
                data={"name": "Upserted Project"},
                user_id="user1"
            )
        ]
        
        mock_context_service.create_context.return_value = {"success": True}
        mock_context_service.update_context.return_value = {"success": True}
        mock_context_service.delete_context.return_value = {"success": True}
        mock_context_service.get_context.return_value = None  # For upsert
        
        results = await batch_operations.execute_batch(operations)
        
        assert len(results) == 4
        assert all(r.success for r in results)
        
        # Verify each operation was called
        assert mock_context_service.create_context.call_count == 2  # CREATE + UPSERT
        assert mock_context_service.update_context.call_count == 1
        assert mock_context_service.delete_context.call_count == 1
        assert mock_context_service.get_context.call_count == 1  # For UPSERT check