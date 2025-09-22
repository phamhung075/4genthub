"""
Comprehensive Test Suite for WebSocket Protocol v2.0

Tests all aspects of the WebSocket protocol including:
- Message validation (v2.0 only, reject other versions)
- Payload structure validation
- Cascade data integration
- Message size validation (< 64KB)
- Dual-track message types (user vs AI)
- JSON serialization/deserialization
- Error handling for malformed messages
"""

import json
import pytest
import uuid
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from fastmcp.websocket import (
    WSMessage,
    WSPayload,
    WSData,
    WSMetadata,
    CascadeData,
    UserUpdateMessage,
    AIBatchMessage,
    HeartbeatMessage,
    ErrorMessage,
    SyncMessage,
    validate_message,
    create_user_update,
    create_ai_batch,
    create_heartbeat,
    create_error,
    create_sync,
    get_message_size,
    is_message_size_valid,
    MessageSizeError,
    ProtocolError,
    InvalidVersionError,
)
from fastmcp.task_management.domain.services.cascade_calculator import (
    CascadeCalculator,
    CascadeResult,
    EntityType as CascadeEntityType
)


class TestMessageValidation:
    """Test message validation and protocol enforcement"""

    def test_validate_message_v2_success(self):
        """Test successful validation of v2.0 message"""
        message = {
            "version": "2.0",
            "type": "update",
            "sequence": 1,
            "payload": {
                "entity": "task",
                "action": "create",
                "data": {
                    "primary": {"id": "123", "title": "Test Task"}
                }
            },
            "metadata": {
                "source": "user",
                "immediate": True
            }
        }

        result = validate_message(message)
        assert isinstance(result, WSMessage)
        assert result.version == "2.0"
        assert result.type == "update"

    def test_validate_message_rejects_v1(self):
        """Test that v1.0 messages are rejected"""
        message = {
            "version": "1.0",
            "type": "update",
            "data": {"test": "data"}
        }

        with pytest.raises(InvalidVersionError) as exc_info:
            validate_message(message)

        assert "Only protocol v2.0 is supported" in str(exc_info.value)

    def test_validate_message_rejects_no_version(self):
        """Test that messages without version are rejected"""
        message = {
            "type": "update",
            "data": {"test": "data"}
        }

        with pytest.raises(InvalidVersionError):
            validate_message(message)

    def test_validate_message_rejects_invalid_structure(self):
        """Test that malformed messages are rejected"""
        message = {
            "version": "2.0",
            "type": "invalid_type",  # Invalid message type
            "sequence": "not_a_number"  # Invalid sequence type
        }

        with pytest.raises(ProtocolError):
            validate_message(message)

    def test_validate_message_size_limit(self):
        """Test that oversized messages are rejected"""
        # Create a message that exceeds 64KB
        large_data = {"data": "x" * 70000}  # Over 64KB
        message = {
            "version": "2.0",
            "type": "update",
            "sequence": 1,
            "payload": {
                "entity": "task",
                "action": "create",
                "data": {
                    "primary": large_data
                }
            },
            "metadata": {
                "source": "user",
                "immediate": True
            }
        }

        with pytest.raises(MessageSizeError) as exc_info:
            validate_message(message)

        assert "exceeds limit" in str(exc_info.value)


class TestWSMessageModels:
    """Test WebSocket message models and their validation"""

    def test_ws_message_creation(self):
        """Test basic WSMessage creation with all required fields"""
        payload = WSPayload(
            entity="task",
            action="create",
            data=WSData(primary={"id": "123"})
        )

        metadata = WSMetadata(source="user")

        message = WSMessage(
            type="update",
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        assert message.version == "2.0"
        assert message.type == "update"
        assert message.sequence == 1
        assert isinstance(message.id, str)
        assert isinstance(message.timestamp, datetime)

    def test_cascade_data_model(self):
        """Test CascadeData model functionality"""
        cascade = CascadeData(
            tasks=[{"id": "task1"}, {"id": "task2"}],
            branches=[{"id": "branch1"}],
            projects=[{"id": "project1"}]
        )

        assert cascade.get_total_entities() == 4
        assert not cascade.is_empty()

        empty_cascade = CascadeData()
        assert empty_cascade.get_total_entities() == 0
        assert empty_cascade.is_empty()

    def test_user_update_message_defaults(self):
        """Test UserUpdateMessage enforces correct defaults"""
        payload = WSPayload(
            entity="task",
            action="create",
            data=WSData(primary={"id": "123"})
        )

        metadata = WSMetadata(source="system")  # Will be overridden

        message = UserUpdateMessage(
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        assert message.type == "update"
        assert message.metadata.source == "user"
        assert message.metadata.immediate is True

    def test_ai_batch_message_defaults(self):
        """Test AIBatchMessage enforces correct defaults"""
        payload = WSPayload(
            entity="multiple",
            action="batch",
            data=WSData(primary=[{"id": "123"}, {"id": "456"}])
        )

        metadata = WSMetadata(source="system")  # Will be overridden

        message = AIBatchMessage(
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        assert message.type == "bulk"
        assert message.metadata.source == "mcp-ai"
        assert message.metadata.immediate is False

    def test_system_message_types(self):
        """Test system message types (heartbeat, error, sync)"""
        payload = WSPayload(
            entity="multiple",
            action="update",
            data=WSData(primary={"status": "test"})
        )

        metadata = WSMetadata(source="user")  # Will be overridden

        # Test HeartbeatMessage
        heartbeat = HeartbeatMessage(
            sequence=1,
            payload=payload,
            metadata=metadata
        )
        assert heartbeat.type == "heartbeat"
        assert heartbeat.metadata.source == "system"

        # Test ErrorMessage
        error = ErrorMessage(
            sequence=2,
            payload=payload,
            metadata=metadata
        )
        assert error.type == "error"
        assert error.metadata.source == "system"

        # Test SyncMessage
        sync = SyncMessage(
            sequence=3,
            payload=payload,
            metadata=metadata
        )
        assert sync.type == "sync"
        assert sync.metadata.source == "system"


class TestProtocolHelpers:
    """Test protocol helper functions"""

    @pytest.mark.asyncio
    async def test_create_user_update_without_cascade(self):
        """Test creating user update without cascade calculator"""
        message = create_user_update(
            entity_type="task",
            action="create",
            primary_data={"id": "123", "title": "Test Task"},
            user_id="user123",
            session_id="session123",
            sequence=1
        )

        assert isinstance(message, UserUpdateMessage)
        assert message.type == "update"
        assert message.metadata.source == "user"
        assert message.metadata.user_id == "user123"
        assert message.metadata.session_id == "session123"
        assert message.metadata.immediate is True
        assert message.payload.entity == "task"
        assert message.payload.action == "create"
        assert message.payload.data.cascade is None

    @pytest.mark.asyncio
    async def test_create_user_update_with_cascade(self):
        """Test creating user update with cascade calculator"""
        # Mock cascade calculator
        mock_calculator = AsyncMock(spec=CascadeCalculator)
        mock_result = CascadeResult(
            entity_id="task123",
            entity_type=CascadeEntityType.TASK,
            affected_tasks={"task123", "task456"},
            affected_subtasks={"sub123"},
            affected_branches={"branch123"},
            affected_projects={"project123"},
            affected_contexts=set(),
            calculation_time_ms=25.0
        )
        mock_calculator.calculate_cascade.return_value = mock_result

        message = await create_user_update(
            entity_type="task",
            action="update",
            primary_data={"id": "task123", "title": "Updated Task"},
            cascade_calculator=mock_calculator,
            entity_id="task123",
            sequence=1
        )

        assert isinstance(message, UserUpdateMessage)
        assert message.payload.data.cascade is not None
        assert len(message.payload.data.cascade.tasks) == 2
        assert len(message.payload.data.cascade.subtasks) == 1
        assert len(message.payload.data.cascade.branches) == 1
        assert len(message.payload.data.cascade.projects) == 1

        # Verify cascade calculator was called correctly
        mock_calculator.calculate_cascade.assert_called_once_with(
            entity_id="task123",
            entity_type=CascadeEntityType.TASK
        )

    @pytest.mark.asyncio
    async def test_create_ai_batch(self):
        """Test creating AI batch message"""
        updates = [
            {"entity_id": "task1", "entity_type": "task", "action": "update"},
            {"entity_id": "task2", "entity_type": "task", "action": "create"}
        ]

        message = create_ai_batch(
            updates=updates,
            batch_id="batch_456",
            user_id="user123",
            sequence=5
        )

        assert isinstance(message, AIBatchMessage)
        assert message.type == "bulk"
        assert message.metadata.source == "mcp-ai"
        assert message.metadata.batch_id == "batch_456"
        assert message.metadata.immediate is False
        assert message.payload.entity == "multiple"
        assert message.payload.action == "batch"
        assert message.payload.data.primary == updates

    def test_create_heartbeat(self):
        """Test creating heartbeat message"""
        message = create_heartbeat(
            session_id="session123",
            sequence=10
        )

        assert isinstance(message, HeartbeatMessage)
        assert message.type == "heartbeat"
        assert message.metadata.source == "system"
        assert message.metadata.session_id == "session123"
        assert message.metadata.immediate is True
        assert message.payload.data.primary == {"status": "alive"}

    def test_create_error(self):
        """Test creating error message"""
        message = create_error(
            error_message="Something went wrong",
            error_code="ERR_001",
            error_details={"field": "invalid_value"},
            session_id="session123",
            correlation_id="corr_456",
            sequence=15
        )

        assert isinstance(message, ErrorMessage)
        assert message.type == "error"
        assert message.metadata.source == "system"
        assert message.metadata.session_id == "session123"
        assert message.metadata.correlation_id == "corr_456"

        error_data = message.payload.data.primary
        assert error_data["message"] == "Something went wrong"
        assert error_data["code"] == "ERR_001"
        assert error_data["details"] == {"field": "invalid_value"}
        assert "timestamp" in error_data

    def test_create_sync(self):
        """Test creating sync message"""
        sync_data = {
            "user_state": {"tasks": [], "branches": []},
            "server_time": "2023-01-01T00:00:00Z"
        }

        message = create_sync(
            sync_data=sync_data,
            session_id="session123",
            user_id="user456",
            sequence=20
        )

        assert isinstance(message, SyncMessage)
        assert message.type == "sync"
        assert message.metadata.source == "system"
        assert message.metadata.session_id == "session123"
        assert message.metadata.user_id == "user456"
        assert message.payload.data.primary == sync_data


class TestMessageSizing:
    """Test message size validation and helpers"""

    def test_get_message_size(self):
        """Test message size calculation"""
        payload = WSPayload(
            entity="task",
            action="create",
            data=WSData(primary={"id": "123", "title": "Test"})
        )

        metadata = WSMetadata(source="user")

        message = WSMessage(
            type="update",
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        size = get_message_size(message)
        assert isinstance(size, int)
        assert size > 0

    def test_is_message_size_valid_small_message(self):
        """Test size validation for small message"""
        payload = WSPayload(
            entity="task",
            action="create",
            data=WSData(primary={"id": "123"})
        )

        metadata = WSMetadata(source="user")

        message = WSMessage(
            type="update",
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        assert is_message_size_valid(message) is True

    def test_is_message_size_valid_large_message(self):
        """Test size validation for large message"""
        # Create a message that's close to or over the limit
        large_data = {"data": "x" * 70000}  # Over 64KB

        payload = WSPayload(
            entity="task",
            action="create",
            data=WSData(primary=large_data)
        )

        metadata = WSMetadata(source="user")

        message = WSMessage(
            type="update",
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        assert is_message_size_valid(message) is False


class TestJSONSerialization:
    """Test JSON serialization and deserialization"""

    def test_message_json_serialization(self):
        """Test that messages can be serialized to JSON"""
        payload = WSPayload(
            entity="task",
            action="create",
            data=WSData(
                primary={"id": "123", "title": "Test Task"},
                cascade=CascadeData(
                    tasks=[{"id": "task1"}],
                    branches=[{"id": "branch1"}]
                )
            )
        )

        metadata = WSMetadata(
            source="user",
            user_id="user123",
            session_id="session456"
        )

        message = WSMessage(
            type="update",
            sequence=1,
            payload=payload,
            metadata=metadata
        )

        # Test serialization
        json_str = message.model_dump_json()
        assert isinstance(json_str, str)

        # Test deserialization
        json_data = json.loads(json_str)
        reconstructed = WSMessage(**json_data)

        assert reconstructed.version == "2.0"
        assert reconstructed.type == "update"
        assert reconstructed.sequence == 1
        assert reconstructed.metadata.source == "user"
        assert reconstructed.payload.entity == "task"

    def test_datetime_serialization(self):
        """Test that datetime fields are properly serialized"""
        message = WSMessage(
            type="update",
            sequence=1,
            payload=WSPayload(
                entity="task",
                action="create",
                data=WSData(primary={"id": "123"})
            ),
            metadata=WSMetadata(source="user")
        )

        json_data = json.loads(message.model_dump_json())

        # Check that timestamp is serialized as ISO format string
        assert "timestamp" in json_data
        assert isinstance(json_data["timestamp"], str)
        assert "T" in json_data["timestamp"]  # ISO format indicator


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_entity_type_mapping(self):
        """Test handling of invalid entity types in cascade mapping"""
        # This would be tested in the actual protocol implementation
        # when an unsupported entity type is passed to cascade calculation
        pass

    @pytest.mark.asyncio
    async def test_cascade_calculation_failure(self):
        """Test handling when cascade calculation fails"""
        # Mock a failing cascade calculator
        mock_calculator = AsyncMock(spec=CascadeCalculator)
        mock_calculator.calculate_cascade.side_effect = Exception("Database error")

        # Should not raise exception, should log warning and continue
        message = await create_user_update(
            entity_type="task",
            action="update",
            primary_data={"id": "task123"},
            cascade_calculator=mock_calculator,
            entity_id="task123",
            sequence=1
        )

        assert isinstance(message, UserUpdateMessage)
        assert message.payload.data.cascade is None  # No cascade due to error

    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        # Test missing payload
        with pytest.raises(Exception):
            WSMessage(
                type="update",
                sequence=1,
                metadata=WSMetadata(source="user")
                # Missing payload
            )

        # Test missing metadata
        with pytest.raises(Exception):
            WSMessage(
                type="update",
                sequence=1,
                payload=WSPayload(
                    entity="task",
                    action="create",
                    data=WSData(primary={"id": "123"})
                )
                # Missing metadata
            )


class TestDualTrackMessaging:
    """Test dual-track messaging (user vs AI) functionality"""

    def test_user_message_characteristics(self):
        """Test that user messages have correct characteristics"""
        message = UserUpdateMessage(
            sequence=1,
            payload=WSPayload(
                entity="task",
                action="update",
                data=WSData(primary={"id": "123"})
            ),
            metadata=WSMetadata(source="placeholder")  # Will be overridden
        )

        assert message.type == "update"
        assert message.metadata.source == "user"
        assert message.metadata.immediate is True
        assert message.metadata.batch_id is None

    def test_ai_batch_characteristics(self):
        """Test that AI batch messages have correct characteristics"""
        message = AIBatchMessage(
            sequence=1,
            payload=WSPayload(
                entity="multiple",
                action="batch",
                data=WSData(primary=[{"id": "123"}, {"id": "456"}])
            ),
            metadata=WSMetadata(
                source="placeholder",  # Will be overridden
                batch_id="batch_123"
            )
        )

        assert message.type == "bulk"
        assert message.metadata.source == "mcp-ai"
        assert message.metadata.immediate is False
        assert message.metadata.batch_id == "batch_123"

    def test_system_message_characteristics(self):
        """Test that system messages have correct characteristics"""
        message = HeartbeatMessage(
            sequence=1,
            payload=WSPayload(
                entity="multiple",
                action="update",
                data=WSData(primary={"status": "alive"})
            ),
            metadata=WSMetadata(source="placeholder")  # Will be overridden
        )

        assert message.type == "heartbeat"
        assert message.metadata.source == "system"
        assert message.metadata.immediate is True


# Integration test
class TestProtocolIntegration:
    """Integration tests for the complete protocol"""

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self):
        """Test complete user update workflow with cascade"""
        # Mock cascade calculator
        mock_calculator = AsyncMock(spec=CascadeCalculator)
        mock_result = CascadeResult(
            entity_id="task123",
            entity_type=CascadeEntityType.TASK,
            affected_tasks={"task123"},
            affected_subtasks=set(),
            affected_branches={"branch123"},
            affected_projects={"project123"},
            affected_contexts=set(),
            calculation_time_ms=15.0
        )
        mock_calculator.calculate_cascade.return_value = mock_result

        # Create user update
        message = await create_user_update(
            entity_type="task",
            action="update",
            primary_data={"id": "task123", "title": "Updated Task", "status": "in_progress"},
            cascade_calculator=mock_calculator,
            entity_id="task123",
            user_id="user456",
            session_id="session789",
            correlation_id="corr_123",
            sequence=42
        )

        # Validate message structure
        assert isinstance(message, UserUpdateMessage)
        assert message.version == "2.0"
        assert message.type == "update"
        assert message.sequence == 42

        # Validate metadata
        assert message.metadata.source == "user"
        assert message.metadata.user_id == "user456"
        assert message.metadata.session_id == "session789"
        assert message.metadata.correlation_id == "corr_123"
        assert message.metadata.immediate is True

        # Validate payload
        assert message.payload.entity == "task"
        assert message.payload.action == "update"
        assert message.payload.data.primary["id"] == "task123"

        # Validate cascade
        assert message.payload.data.cascade is not None
        assert len(message.payload.data.cascade.tasks) == 1
        assert len(message.payload.data.cascade.branches) == 1
        assert len(message.payload.data.cascade.projects) == 1

        # Test serialization roundtrip
        json_str = message.model_dump_json()
        json_data = json.loads(json_str)

        # Validate with protocol
        validated = validate_message(json_data)
        assert isinstance(validated, WSMessage)
        assert validated.version == "2.0"

        # Test size validation
        assert is_message_size_valid(message) is True