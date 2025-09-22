"""
Basic WebSocket Protocol v2.0 Tests

Simple tests to verify core functionality without complex dependencies.
"""

import json
import pytest
from datetime import datetime

from fastmcp.websocket import (
    WSMessage,
    WSPayload,
    WSData,
    WSMetadata,
    CascadeData,
    validate_message,
    MessageSizeError,
    ProtocolError,
    InvalidVersionError,
)


class TestBasicValidation:
    """Test basic message validation"""

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


class TestModels:
    """Test basic model functionality"""

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

    def test_ws_message_creation(self):
        """Test basic WSMessage creation"""
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

    def test_json_serialization(self):
        """Test basic JSON serialization"""
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

        # Test serialization
        json_str = message.model_dump_json()
        assert isinstance(json_str, str)

        # Test deserialization
        json_data = json.loads(json_str)
        reconstructed = WSMessage(**json_data)

        assert reconstructed.version == "2.0"
        assert reconstructed.type == "update"