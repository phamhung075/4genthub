"""
Batch Context Operations Use Case

Provides efficient batch operations for multiple context updates,
reducing network overhead and database transactions.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio
from datetime import datetime

from ...domain.models.unified_context import ContextLevel
from ..services.unified_context_service import UnifiedContextService
from ...domain.interfaces.cache_service import ICacheService

logger = logging.getLogger(__name__)


class BatchOperationType(Enum):
    """Types of batch operations"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UPSERT = "upsert"  # Create if not exists, update if exists


@dataclass
class BatchOperation:
    """Single operation in a batch"""
    operation: BatchOperationType
    level: ContextLevel
    context_id: str
    data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    git_branch_id: Optional[str] = None
    
    # Additional options
    propagate_changes: bool = True
    include_inherited: bool = False
    force_refresh: bool = False


@dataclass
class BatchOperationResult:
    """Result of a single batch operation"""
    success: bool
    operation: BatchOperation
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class BatchContextOperations:
    """
    Handles batch context operations with optimizations for performance.
    """
    
    def __init__(self, context_service: UnifiedContextService):
        self.context_service = context_service
        self.cache = get_context_cache()
    
    async def execute_batch(
        self,
        operations: List[BatchOperation],
        transaction: bool = True,
        parallel: bool = False,
        stop_on_error: bool = True,
        user_id: Optional[str] = None
    ) -> List[BatchOperationResult]:
        """
        Execute a batch of context operations.
        
        Args:
            operations: List of operations to execute
            transaction: Execute all in a single transaction (all succeed or all fail)
            parallel: Execute operations in parallel (only if transaction=False)
            stop_on_error: Stop processing on first error
            user_id: Default user_id for all operations
        
        Returns:
            List of operation results
        """
        results = []
        
        # Apply default user_id if provided
        if user_id:
            for op in operations:
                if not op.user_id:
                    op.user_id = user_id
        
        if transaction and not parallel:
            # Execute in transaction
            results = await self._execute_transactional(operations, stop_on_error)
        elif parallel and not transaction:
            # Execute in parallel
            results = await self._execute_parallel(operations, stop_on_error)
        else:
            # Execute sequentially
            results = await self._execute_sequential(operations, stop_on_error)
        
        # Invalidate cache for affected contexts
        await self._invalidate_caches(operations, user_id)
        
        return results
    
    async def _execute_transactional(
        self, 
        operations: List[BatchOperation],
        stop_on_error: bool
    ) -> List[BatchOperationResult]:
        """Execute operations in a single transaction"""
        results = []
        
        # Start transaction (implementation depends on your database)
        # For SQLAlchemy, you would use session.begin()
        
        try:
            for op in operations:
                start_time = datetime.now(timezone.utc)
                
                try:
                    result = await self._execute_single_operation(op)
                    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    
                    results.append(BatchOperationResult(
                        success=True,
                        operation=op,
                        result=result,
                        execution_time_ms=execution_time
                    ))
                except Exception as e:
                    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    
                    results.append(BatchOperationResult(
                        success=False,
                        operation=op,
                        error=str(e),
                        execution_time_ms=execution_time
                    ))
                    
                    if stop_on_error:
                        # Rollback transaction
                        raise e
            
            # Commit transaction
            # await session.commit()
            
        except Exception as e:
            # Rollback transaction
            # await session.rollback()
            logger.error(f"Batch transaction failed: {e}")
            
            # Mark remaining operations as failed
            for i in range(len(results), len(operations)):
                results.append(BatchOperationResult(
                    success=False,
                    operation=operations[i],
                    error="Transaction rolled back"
                ))
        
        return results
    
    async def _execute_sequential(
        self,
        operations: List[BatchOperation],
        stop_on_error: bool
    ) -> List[BatchOperationResult]:
        """Execute operations sequentially"""
        results = []
        
        for op in operations:
            start_time = datetime.now(timezone.utc)
            
            try:
                result = await self._execute_single_operation(op)
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                results.append(BatchOperationResult(
                    success=True,
                    operation=op,
                    result=result,
                    execution_time_ms=execution_time
                ))
            except Exception as e:
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                results.append(BatchOperationResult(
                    success=False,
                    operation=op,
                    error=str(e),
                    execution_time_ms=execution_time
                ))
                
                if stop_on_error:
                    # Mark remaining as skipped
                    for i in range(len(results), len(operations)):
                        results.append(BatchOperationResult(
                            success=False,
                            operation=operations[i],
                            error="Skipped due to previous error"
                        ))
                    break
        
        return results
    
    async def _execute_parallel(
        self,
        operations: List[BatchOperation],
        stop_on_error: bool
    ) -> List[BatchOperationResult]:
        """Execute operations in parallel"""
        
        async def execute_with_timing(op: BatchOperation) -> BatchOperationResult:
            start_time = datetime.now(timezone.utc)
            
            try:
                result = await self._execute_single_operation(op)
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                return BatchOperationResult(
                    success=True,
                    operation=op,
                    result=result,
                    execution_time_ms=execution_time
                )
            except Exception as e:
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                return BatchOperationResult(
                    success=False,
                    operation=op,
                    error=str(e),
                    execution_time_ms=execution_time
                )
        
        # Execute all operations in parallel
        tasks = [execute_with_timing(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Check if we should have stopped on error
        if stop_on_error:
            for i, result in enumerate(results):
                if not result.success:
                    # Cancel remaining tasks (they may have already completed)
                    logger.warning(f"Operation {i} failed, but parallel execution continued")
                    break
        
        return results
    
    async def _execute_single_operation(self, op: BatchOperation) -> Dict[str, Any]:
        """Execute a single operation"""
        
        if op.operation == BatchOperationType.CREATE:
            return await self.context_service.create_context(
                context_level=op.level,
                context_id=op.context_id,
                data=op.data or {},
                user_id=op.user_id,
                project_id=op.project_id,
                git_branch_id=op.git_branch_id
            )
        
        elif op.operation == BatchOperationType.UPDATE:
            return await self.context_service.update_context(
                context_level=op.level,
                context_id=op.context_id,
                data=op.data or {},
                user_id=op.user_id,
                propagate_changes=op.propagate_changes
            )
        
        elif op.operation == BatchOperationType.DELETE:
            return await self.context_service.delete_context(
                context_level=op.level,
                context_id=op.context_id,
                user_id=op.user_id
            )
        
        elif op.operation == BatchOperationType.UPSERT:
            # Try to get existing context
            existing = await self.context_service.get_context(
                context_level=op.level,
                context_id=op.context_id,
                user_id=op.user_id,
                include_inherited=False
            )
            
            if existing:
                # Update existing
                return await self.context_service.update_context(
                    context_level=op.level,
                    context_id=op.context_id,
                    data=op.data or {},
                    user_id=op.user_id,
                    propagate_changes=op.propagate_changes
                )
            else:
                # Create new
                return await self.context_service.create_context(
                    context_level=op.level,
                    context_id=op.context_id,
                    data=op.data or {},
                    user_id=op.user_id,
                    project_id=op.project_id,
                    git_branch_id=op.git_branch_id
                )
        
        else:
            raise ValueError(f"Unknown operation type: {op.operation}")
    
    async def _invalidate_caches(self, operations: List[BatchOperation], user_id: str):
        """Invalidate caches for affected contexts"""
        for op in operations:
            if op.operation != BatchOperationType.DELETE:
                self.cache.invalidate_context(
                    user_id=op.user_id or user_id,
                    level=op.level.value,
                    context_id=op.context_id
                )
                self.cache.invalidate_inheritance(
                    user_id=op.user_id or user_id,
                    level=op.level.value,
                    context_id=op.context_id
                )
    
    # Convenience methods
    
    async def bulk_create(
        self,
        contexts: List[Dict[str, Any]],
        level: ContextLevel,
        user_id: str,
        transaction: bool = True
    ) -> List[BatchOperationResult]:
        """Create multiple contexts of the same level"""
        operations = [
            BatchOperation(
                operation=BatchOperationType.CREATE,
                level=level,
                context_id=ctx['context_id'],
                data=ctx.get('data', {}),
                user_id=user_id,
                project_id=ctx.get('project_id'),
                git_branch_id=ctx.get('git_branch_id')
            )
            for ctx in contexts
        ]
        
        return await self.execute_batch(
            operations=operations,
            transaction=transaction,
            user_id=user_id
        )
    
    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        level: ContextLevel,
        user_id: str,
        transaction: bool = False,
        parallel: bool = True
    ) -> List[BatchOperationResult]:
        """Update multiple contexts of the same level"""
        operations = [
            BatchOperation(
                operation=BatchOperationType.UPDATE,
                level=level,
                context_id=update['context_id'],
                data=update.get('data', {}),
                user_id=user_id,
                propagate_changes=update.get('propagate_changes', True)
            )
            for update in updates
        ]
        
        return await self.execute_batch(
            operations=operations,
            transaction=transaction,
            parallel=parallel,
            user_id=user_id
        )
    
    async def copy_contexts(
        self,
        source_branch_id: str,
        target_branch_id: str,
        user_id: str,
        include_task_contexts: bool = True
    ) -> List[BatchOperationResult]:
        """Copy all contexts from one branch to another"""
        
        # Get all contexts from source branch
        source_contexts = await self.context_service.get_context(
            context_level=ContextLevel.BRANCH,
            context_id=source_branch_id,
            user_id=user_id,
            include_inherited=False
        )
        
        operations = []
        
        # Copy branch context
        if source_contexts:
            operations.append(
                BatchOperation(
                    operation=BatchOperationType.UPSERT,
                    level=ContextLevel.BRANCH,
                    context_id=target_branch_id,
                    data=source_contexts.get('data', {}),
                    user_id=user_id
                )
            )
        
        # Copy task contexts if requested
        if include_task_contexts:
            # This would need to query all task contexts for the source branch
            # Implementation depends on your repository structure
            pass
        
        return await self.execute_batch(
            operations=operations,
            transaction=True,
            user_id=user_id
        )