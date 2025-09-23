"""
WebSocket Batch Processor v2.0

Processes AI messages in 500ms batches with deduplication and merging.
Supports efficient batching of multiple entity updates with cascade data.

NO backward compatibility - clean v2.0 implementation only.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ..task_management.domain.services.cascade_calculator import CascadeCalculator
from .protocol import create_ai_batch
from .models import WSMessage, AIBatchMessage, CascadeData
from .types import EntityType, ActionType

if TYPE_CHECKING:
    from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes AI messages in 500ms batches with intelligent merging.

    Features:
    - 500ms±10ms batch intervals
    - Deduplication of entity updates
    - Cascade data merging
    - Maximum batch size limits
    - Efficient memory usage
    """

    def __init__(self, manager: "ConnectionManager", session_factory):
        """
        Initialize batch processor.

        Args:
            manager: ConnectionManager instance for broadcasting
            session_factory: Factory function for creating database sessions
        """
        self.manager = manager
        self.session_factory = session_factory

        # Batch configuration
        self.batch_interval = 0.5  # 500ms
        self.max_batch_size = 50
        self.max_batch_timeout = 2.0  # Maximum wait time

        # Processing state
        self.is_running = False
        self.batch_task: Optional[asyncio.Task] = None
        self.current_batch: List[WSMessage] = []
        self.batch_lock = asyncio.Lock()

        # Statistics
        self.batches_processed = 0
        self.messages_processed = 0
        self.average_batch_size = 0.0
        self.last_batch_time: Optional[datetime] = None

        logger.info(f"BatchProcessor initialized with {self.batch_interval}s interval")

    async def start(self) -> None:
        """
        Start the batch processing background task.
        """
        if self.is_running:
            logger.warning("BatchProcessor already running")
            return

        self.is_running = True
        self.batch_task = asyncio.create_task(self._batch_loop())
        logger.info("BatchProcessor started")

    async def stop(self) -> None:
        """
        Stop the batch processing background task.
        """
        if not self.is_running:
            return

        self.is_running = False

        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass

        # Process any remaining messages
        await self._process_final_batch()

        logger.info("BatchProcessor stopped")

    async def _batch_loop(self) -> None:
        """
        Main batch processing loop that runs every 500ms.
        """
        while self.is_running:
            try:
                # Wait for batch interval
                await asyncio.sleep(self.batch_interval)

                # Process current batch
                await self._process_batch()

            except asyncio.CancelledError:
                logger.info("Batch processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                # Continue processing despite errors

    async def _process_batch(self) -> None:
        """
        Process the current batch of AI messages.
        """
        async with self.batch_lock:
            if not self.current_batch:
                return

            batch_start = datetime.now(timezone.utc)
            batch_size = len(self.current_batch)

            logger.debug(f"Processing batch of {batch_size} AI messages")

            try:
                # Collect messages from queue
                batch_messages = await self._collect_batch_messages()

                if not batch_messages:
                    return

                # Process and merge batch
                merged_batch = await self._merge_batch(batch_messages)

                # Broadcast merged batch
                await self.manager.broadcast_batch(merged_batch)

                # Update statistics
                self._update_stats(batch_size, batch_start)

                logger.debug(f"Batch processed successfully: {batch_size} messages merged")

            except Exception as e:
                logger.error(f"Error processing batch: {e}")

    async def _collect_batch_messages(self) -> List[WSMessage]:
        """
        Collect messages from the AI batch queue.

        Returns:
            List of messages to process in this batch
        """
        messages = []
        start_time = datetime.now(timezone.utc)

        # Collect messages until batch size or timeout
        while (
            len(messages) < self.max_batch_size and
            (datetime.now(timezone.utc) - start_time).total_seconds() < self.max_batch_timeout
        ):
            try:
                # Non-blocking queue get with timeout
                message = await asyncio.wait_for(
                    self.manager.ai_batch_queue.get(),
                    timeout=0.1
                )
                messages.append(message)
            except asyncio.TimeoutError:
                # No more messages in queue
                break

        return messages

    async def _merge_batch(self, messages: List[WSMessage]) -> AIBatchMessage:
        """
        Merge multiple AI messages into a single batch message.

        Args:
            messages: List of WSMessage to merge

        Returns:
            AIBatchMessage with combined data and cascade information
        """
        if not messages:
            raise ValueError("Cannot merge empty batch")

        # Deduplicate and organize updates by entity
        entity_updates = self._deduplicate_updates(messages)

        # Create batch ID
        batch_id = str(uuid.uuid4())

        # Convert to update format for create_ai_batch
        updates = []
        for entity_id, update_data in entity_updates.items():
            updates.append({
                "entity_id": entity_id,
                "entity_type": update_data["entity_type"],
                "action": update_data["action"],
                "data": update_data["data"]
            })

        # Get user_id from first message (all should be from same context)
        user_id = messages[0].metadata.user_id if messages else None

        # Create merged batch message with cascade calculation
        async with self.session_factory() as db_session:
            cascade_calculator = CascadeCalculator(db_session)

            batch_message = await create_ai_batch(
                updates=updates,
                batch_id=batch_id,
                cascade_calculator=cascade_calculator,
                user_id=user_id,
                sequence=self.manager._next_sequence()
            )

        return batch_message

    def _deduplicate_updates(self, messages: List[WSMessage]) -> Dict[str, Dict[str, Any]]:
        """
        Deduplicate entity updates, keeping the latest update for each entity.

        Args:
            messages: List of messages to deduplicate

        Returns:
            Dictionary mapping entity_id to latest update data
        """
        entity_updates = {}

        for message in messages:
            payload = message.payload
            primary_data = payload.data.primary

            # Extract entity ID
            entity_id = None
            if isinstance(primary_data, dict):
                entity_id = primary_data.get("id")
            elif isinstance(primary_data, list) and primary_data:
                entity_id = primary_data[0].get("id") if isinstance(primary_data[0], dict) else None

            if not entity_id:
                logger.warning("Message without entity ID, skipping deduplication")
                continue

            # Store latest update for this entity
            entity_updates[entity_id] = {
                "entity_type": payload.entity,
                "action": payload.action,
                "data": primary_data,
                "timestamp": message.timestamp
            }

        logger.debug(f"Deduplicated {len(messages)} messages to {len(entity_updates)} unique entities")
        return entity_updates

    async def _process_final_batch(self) -> None:
        """
        Process any remaining messages when stopping.
        """
        try:
            final_messages = await self._collect_batch_messages()
            if final_messages:
                merged_batch = await self._merge_batch(final_messages)
                await self.manager.broadcast_batch(merged_batch)
                logger.info(f"Processed final batch of {len(final_messages)} messages")
        except Exception as e:
            logger.error(f"Error processing final batch: {e}")

    def _update_stats(self, batch_size: int, batch_start: datetime) -> None:
        """
        Update batch processing statistics.

        Args:
            batch_size: Number of messages in processed batch
            batch_start: Batch start timestamp
        """
        self.batches_processed += 1
        self.messages_processed += batch_size
        self.last_batch_time = batch_start

        # Calculate running average batch size
        self.average_batch_size = (
            (self.average_batch_size * (self.batches_processed - 1) + batch_size) /
            self.batches_processed
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get batch processor statistics.

        Returns:
            Dictionary with processing statistics
        """
        return {
            "is_running": self.is_running,
            "batch_interval_ms": self.batch_interval * 1000,
            "max_batch_size": self.max_batch_size,
            "batches_processed": self.batches_processed,
            "messages_processed": self.messages_processed,
            "average_batch_size": round(self.average_batch_size, 2),
            "last_batch_time": self.last_batch_time.isoformat() if self.last_batch_time else None,
            "queue_size": self.manager.ai_batch_queue.qsize() if self.manager else 0
        }

    async def force_process_batch(self) -> bool:
        """
        Force immediate processing of current batch (for testing/emergency).

        Returns:
            True if batch was processed, False if no messages
        """
        async with self.batch_lock:
            messages = await self._collect_batch_messages()
            if not messages:
                return False

            merged_batch = await self._merge_batch(messages)
            await self.manager.broadcast_batch(merged_batch)

            logger.info(f"Force processed batch of {len(messages)} messages")
            return True

    def configure_batch_params(
        self,
        interval: Optional[float] = None,
        max_size: Optional[int] = None,
        max_timeout: Optional[float] = None
    ) -> None:
        """
        Update batch processing parameters (for testing/tuning).

        Args:
            interval: Batch interval in seconds
            max_size: Maximum messages per batch
            max_timeout: Maximum wait time for batch collection
        """
        if interval is not None:
            self.batch_interval = max(0.1, min(5.0, interval))  # 100ms to 5s limit

        if max_size is not None:
            self.max_batch_size = max(1, min(200, max_size))  # 1 to 200 limit

        if max_timeout is not None:
            self.max_batch_timeout = max(0.5, min(10.0, max_timeout))  # 0.5s to 10s limit

        logger.info(
            f"Batch parameters updated: interval={self.batch_interval}s, "
            f"max_size={self.max_batch_size}, max_timeout={self.max_batch_timeout}s"
        )