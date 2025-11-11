"""Unit tests for workflow hint value objects."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from fastmcp.task_management.domain.value_objects.hints import (
    HintCollection,
    HintMetadata,
    HintPriority,
    HintType,
    WorkflowHint,
)


class TestHintType:
    """Test cases for HintType enum."""

    def test_hint_type_values(self):
        """Test that HintType has correct values."""
        assert HintType.NEXT_ACTION.value == "next_action"
        assert HintType.BLOCKER_RESOLUTION.value == "blocker_resolution"
        assert HintType.OPTIMIZATION.value == "optimization"
        assert HintType.COMPLETION.value == "completion"
        assert HintType.COLLABORATION.value == "collaboration"


class TestHintPriority:
    """Test cases for HintPriority enum."""

    def test_hint_priority_values(self):
        """Test that HintPriority has correct values."""
        assert HintPriority.LOW.value == "low"
        assert HintPriority.MEDIUM.value == "medium"
        assert HintPriority.HIGH.value == "high"
        assert HintPriority.CRITICAL.value == "critical"


class TestHintMetadata:
    """Test cases for HintMetadata value object."""

    def test_create_hint_metadata_valid(self):
        """Test creating HintMetadata with valid data."""
        task_ids = [uuid4(), uuid4()]
        patterns = ["pattern1", "pattern2"]

        metadata = HintMetadata(
            source="rule_engine",
            confidence=0.85,
            reasoning="Based on similar tasks",
            related_tasks=task_ids,
            patterns_detected=patterns,
            effectiveness_score=0.75,
        )

        assert metadata.source == "rule_engine"
        assert metadata.confidence == 0.85
        assert metadata.reasoning == "Based on similar tasks"
        assert metadata.related_tasks == task_ids
        assert metadata.patterns_detected == patterns
        assert metadata.effectiveness_score == 0.75

    def test_create_hint_metadata_minimal(self):
        """Test creating HintMetadata with minimal required fields."""
        metadata = HintMetadata(
            source="manual", confidence=0.5, reasoning="User feedback"
        )

        assert metadata.source == "manual"
        assert metadata.confidence == 0.5
        assert metadata.reasoning == "User feedback"
        assert metadata.related_tasks == []
        assert metadata.patterns_detected == []
        assert metadata.effectiveness_score is None

    def test_confidence_validation(self):
        """Test confidence score validation."""
        # Valid confidence scores
        HintMetadata(source="test", confidence=0.0, reasoning="test")
        HintMetadata(source="test", confidence=1.0, reasoning="test")
        HintMetadata(source="test", confidence=0.5, reasoning="test")

        # Invalid confidence scores
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            HintMetadata(source="test", confidence=-0.1, reasoning="test")

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            HintMetadata(source="test", confidence=1.1, reasoning="test")

    def test_effectiveness_score_validation(self):
        """Test effectiveness score validation."""
        # Valid effectiveness scores
        HintMetadata(
            source="test", confidence=0.5, reasoning="test", effectiveness_score=0.0
        )
        HintMetadata(
            source="test", confidence=0.5, reasoning="test", effectiveness_score=1.0
        )
        HintMetadata(
            source="test", confidence=0.5, reasoning="test", effectiveness_score=0.7
        )

        # Invalid effectiveness scores
        with pytest.raises(
            ValueError, match="Effectiveness score must be between 0.0 and 1.0"
        ):
            HintMetadata(
                source="test",
                confidence=0.5,
                reasoning="test",
                effectiveness_score=-0.1,
            )

        with pytest.raises(
            ValueError, match="Effectiveness score must be between 0.0 and 1.0"
        ):
            HintMetadata(
                source="test", confidence=0.5, reasoning="test", effectiveness_score=1.5
            )

    def test_hint_metadata_immutable(self):
        """Test that HintMetadata is immutable (frozen)."""
        metadata = HintMetadata(
            source="test", confidence=0.5, reasoning="test reasoning"
        )

        with pytest.raises(AttributeError):
            metadata.source = "new_source"

        with pytest.raises(AttributeError):
            metadata.confidence = 0.8


class TestWorkflowHint:
    """Test cases for WorkflowHint value object."""

    def test_create_workflow_hint(self):
        """Test creating WorkflowHint with valid data."""
        task_id = uuid4()
        hint_id = uuid4()
        now = datetime.now(UTC)
        metadata = HintMetadata(source="test", confidence=0.8, reasoning="test")
        context = {"key": "value"}
        expires = now + timedelta(hours=1)

        hint = WorkflowHint(
            id=hint_id,
            type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Complete the documentation",
            suggested_action="Write API documentation",
            metadata=metadata,
            created_at=now,
            task_id=task_id,
            context_data=context,
            expires_at=expires,
        )

        assert hint.id == hint_id
        assert hint.type == HintType.NEXT_ACTION
        assert hint.priority == HintPriority.HIGH
        assert hint.message == "Complete the documentation"
        assert hint.suggested_action == "Write API documentation"
        assert hint.metadata == metadata
        assert hint.created_at == now
        assert hint.task_id == task_id
        assert hint.context_data == context
        assert hint.expires_at == expires

    def test_create_hint_factory_method(self):
        """Test creating hint using factory method."""
        task_id = uuid4()
        metadata = HintMetadata(source="factory", confidence=0.9, reasoning="test")

        hint = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.BLOCKER_RESOLUTION,
            priority=HintPriority.CRITICAL,
            message="Resolve dependency conflict",
            suggested_action="Update package version",
            metadata=metadata,
        )

        assert isinstance(hint.id, UUID)
        assert hint.task_id == task_id
        assert hint.type == HintType.BLOCKER_RESOLUTION
        assert hint.priority == HintPriority.CRITICAL
        assert hint.message == "Resolve dependency conflict"
        assert hint.suggested_action == "Update package version"
        assert hint.metadata == metadata
        assert hint.context_data == {}
        assert hint.expires_at is None

    def test_is_expired_no_expiration(self):
        """Test is_expired when no expiration is set."""
        hint = WorkflowHint.create(
            task_id=uuid4(),
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.LOW,
            message="Consider refactoring",
            suggested_action="Extract method",
            metadata=HintMetadata(source="test", confidence=0.5, reasoning="test"),
            expires_at=None,
        )

        assert hint.is_expired() is False

    def test_is_expired_future_expiration(self):
        """Test is_expired when expiration is in the future."""
        future_time = datetime.now(UTC) + timedelta(hours=1)

        hint = WorkflowHint.create(
            task_id=uuid4(),
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.LOW,
            message="Consider refactoring",
            suggested_action="Extract method",
            metadata=HintMetadata(source="test", confidence=0.5, reasoning="test"),
            expires_at=future_time,
        )

        assert hint.is_expired() is False

    def test_is_expired_past_expiration(self):
        """Test is_expired when expiration is in the past."""
        past_time = datetime.now(UTC) - timedelta(hours=1)

        hint = WorkflowHint.create(
            task_id=uuid4(),
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.LOW,
            message="Consider refactoring",
            suggested_action="Extract method",
            metadata=HintMetadata(source="test", confidence=0.5, reasoning="test"),
            expires_at=past_time,
        )

        assert hint.is_expired() is True

    def test_to_dict(self):
        """Test converting hint to dictionary."""
        task_id = uuid4()
        hint_id = uuid4()
        now = datetime.now(UTC)
        expires = now + timedelta(hours=2)
        metadata = HintMetadata(
            source="test",
            confidence=0.7,
            reasoning="Test reasoning",
            related_tasks=[uuid4()],
            patterns_detected=["pattern1"],
        )

        hint = WorkflowHint(
            id=hint_id,
            type=HintType.COMPLETION,
            priority=HintPriority.MEDIUM,
            message="Ready for review",
            suggested_action="Request code review",
            metadata=metadata,
            created_at=now,
            task_id=task_id,
            context_data={"reviewer": "user123"},
            expires_at=expires,
        )

        result = hint.to_dict()

        assert result["id"] == str(hint_id)
        assert result["type"] == "completion"
        assert result["priority"] == "medium"
        assert result["message"] == "Ready for review"
        assert result["suggested_action"] == "Request code review"
        assert result["reasoning"] == "Test reasoning"
        assert result["confidence"] == 0.7
        assert result["created_at"] == now.isoformat()
        assert result["task_id"] == str(task_id)
        assert result["context_data"] == {"reviewer": "user123"}
        assert result["expires_at"] == expires.isoformat()

    def test_to_dict_no_expiration(self):
        """Test to_dict when no expiration is set."""
        hint = WorkflowHint.create(
            task_id=uuid4(),
            hint_type=HintType.COLLABORATION,
            priority=HintPriority.HIGH,
            message="Team input needed",
            suggested_action="Schedule team meeting",
            metadata=HintMetadata(source="test", confidence=0.6, reasoning="test"),
        )

        result = hint.to_dict()
        assert result["expires_at"] is None

    def test_workflow_hint_immutable(self):
        """Test that WorkflowHint is immutable (frozen)."""
        hint = WorkflowHint.create(
            task_id=uuid4(),
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.LOW,
            message="Test",
            suggested_action="Test action",
            metadata=HintMetadata(source="test", confidence=0.5, reasoning="test"),
        )

        with pytest.raises(AttributeError):
            hint.message = "New message"

        with pytest.raises(AttributeError):
            hint.priority = HintPriority.HIGH


class TestHintCollection:
    """Test cases for HintCollection."""

    def test_create_hint_collection(self):
        """Test creating a HintCollection."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)

        assert collection.task_id == task_id
        assert collection.hints == []

    def test_add_hint(self):
        """Test adding hints to collection."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)

        hint = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Start implementation",
            suggested_action="Create base class",
            metadata=HintMetadata(source="test", confidence=0.8, reasoning="test"),
        )

        collection.add_hint(hint)
        assert len(collection.hints) == 1
        assert collection.hints[0] == hint

    def test_add_hint_wrong_task_id(self):
        """Test adding hint with wrong task_id raises error."""
        collection = HintCollection(task_id=uuid4())

        wrong_hint = WorkflowHint.create(
            task_id=uuid4(),  # Different task_id
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Test",
            suggested_action="Test",
            metadata=HintMetadata(source="test", confidence=0.5, reasoning="test"),
        )

        with pytest.raises(
            ValueError, match="Hint task_id must match collection task_id"
        ):
            collection.add_hint(wrong_hint)

    def test_get_active_hints(self):
        """Test getting active (non-expired) hints."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        metadata = HintMetadata(source="test", confidence=0.5, reasoning="test")

        # Add active hint
        active_hint = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Active",
            suggested_action="Do this",
            metadata=metadata,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        # Add expired hint
        expired_hint = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.LOW,
            message="Expired",
            suggested_action="Do that",
            metadata=metadata,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        collection.add_hint(active_hint)
        collection.add_hint(expired_hint)

        active = collection.get_active_hints()
        assert len(active) == 1
        assert active[0] == active_hint

    def test_get_hints_by_type(self):
        """Test filtering hints by type."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        metadata = HintMetadata(source="test", confidence=0.5, reasoning="test")

        # Add hints of different types
        next_action = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Next",
            suggested_action="Do next",
            metadata=metadata,
        )

        optimization = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.MEDIUM,
            message="Optimize",
            suggested_action="Refactor",
            metadata=metadata,
        )

        collection.add_hint(next_action)
        collection.add_hint(optimization)

        next_hints = collection.get_hints_by_type(HintType.NEXT_ACTION)
        assert len(next_hints) == 1
        assert next_hints[0] == next_action

        opt_hints = collection.get_hints_by_type(HintType.OPTIMIZATION)
        assert len(opt_hints) == 1
        assert opt_hints[0] == optimization

    def test_get_hints_by_priority(self):
        """Test filtering hints by priority."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        metadata = HintMetadata(source="test", confidence=0.5, reasoning="test")

        # Add hints of different priorities
        high = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="High priority",
            suggested_action="Do now",
            metadata=metadata,
        )

        low = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.LOW,
            message="Low priority",
            suggested_action="Do later",
            metadata=metadata,
        )

        collection.add_hint(high)
        collection.add_hint(low)

        high_hints = collection.get_hints_by_priority(HintPriority.HIGH)
        assert len(high_hints) == 1
        assert high_hints[0] == high

        low_hints = collection.get_hints_by_priority(HintPriority.LOW)
        assert len(low_hints) == 1
        assert low_hints[0] == low

    def test_get_top_hints(self):
        """Test getting top hints by priority and confidence."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)

        # Add hints with various priorities and confidences
        hints_data = [
            (HintPriority.CRITICAL, 0.9, "Critical high confidence"),
            (HintPriority.CRITICAL, 0.5, "Critical low confidence"),
            (HintPriority.HIGH, 0.8, "High confidence"),
            (HintPriority.MEDIUM, 0.9, "Medium high confidence"),
            (HintPriority.LOW, 1.0, "Low perfect confidence"),
        ]

        for priority, confidence, message in hints_data:
            hint = WorkflowHint.create(
                task_id=task_id,
                hint_type=HintType.NEXT_ACTION,
                priority=priority,
                message=message,
                suggested_action="Action",
                metadata=HintMetadata(
                    source="test", confidence=confidence, reasoning="test"
                ),
            )
            collection.add_hint(hint)

        top_3 = collection.get_top_hints(limit=3)
        assert len(top_3) == 3

        # Check order: Critical hints first (sorted by confidence), then High
        assert top_3[0].priority == HintPriority.CRITICAL
        assert top_3[0].metadata.confidence == 0.9
        assert top_3[1].priority == HintPriority.CRITICAL
        assert top_3[1].metadata.confidence == 0.5
        assert top_3[2].priority == HintPriority.HIGH
        assert top_3[2].metadata.confidence == 0.8

    def test_get_top_hints_with_expired(self):
        """Test that get_top_hints excludes expired hints."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        metadata = HintMetadata(source="test", confidence=0.8, reasoning="test")

        # Add active hint
        active = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Active",
            suggested_action="Do",
            metadata=metadata,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        # Add expired hint with higher priority
        expired = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.BLOCKER_RESOLUTION,
            priority=HintPriority.CRITICAL,
            message="Expired",
            suggested_action="Don't",
            metadata=metadata,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        collection.add_hint(active)
        collection.add_hint(expired)

        top = collection.get_top_hints(limit=2)
        assert len(top) == 1
        assert top[0] == active

    def test_remove_expired_hints(self):
        """Test removing expired hints from collection."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        metadata = HintMetadata(source="test", confidence=0.5, reasoning="test")

        # Add mix of active and expired hints
        for i in range(5):
            expires = (
                datetime.now(UTC) + timedelta(hours=1)
                if i < 3
                else datetime.now(UTC) - timedelta(hours=1)
            )

            hint = WorkflowHint.create(
                task_id=task_id,
                hint_type=HintType.NEXT_ACTION,
                priority=HintPriority.MEDIUM,
                message=f"Hint {i}",
                suggested_action="Action",
                metadata=metadata,
                expires_at=expires,
            )
            collection.add_hint(hint)

        assert len(collection.hints) == 5
        removed = collection.remove_expired_hints()

        assert removed == 2
        assert len(collection.hints) == 3

        # Verify all remaining are active
        for hint in collection.hints:
            assert not hint.is_expired()

    def test_clear_hints_by_type(self):
        """Test clearing hints by specific type."""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        metadata = HintMetadata(source="test", confidence=0.5, reasoning="test")

        # Add hints of different types
        types = [
            HintType.NEXT_ACTION,
            HintType.NEXT_ACTION,
            HintType.OPTIMIZATION,
            HintType.COMPLETION,
            HintType.OPTIMIZATION,
        ]

        for hint_type in types:
            hint = WorkflowHint.create(
                task_id=task_id,
                hint_type=hint_type,
                priority=HintPriority.MEDIUM,
                message="Test",
                suggested_action="Test",
                metadata=metadata,
            )
            collection.add_hint(hint)

        assert len(collection.hints) == 5

        # Clear optimization hints
        removed = collection.clear_hints_by_type(HintType.OPTIMIZATION)
        assert removed == 2
        assert len(collection.hints) == 3

        # Verify no optimization hints remain
        remaining_types = [hint.type for hint in collection.hints]
        assert HintType.OPTIMIZATION not in remaining_types

    def test_empty_collection_operations(self):
        """Test operations on empty collection."""
        collection = HintCollection(task_id=uuid4())

        assert collection.get_active_hints() == []
        assert collection.get_hints_by_type(HintType.NEXT_ACTION) == []
        assert collection.get_hints_by_priority(HintPriority.HIGH) == []
        assert collection.get_top_hints(limit=5) == []
        assert collection.remove_expired_hints() == 0
        assert collection.clear_hints_by_type(HintType.OPTIMIZATION) == 0
