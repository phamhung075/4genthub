"""Unit tests for progress tracking value objects."""

from datetime import UTC, datetime, timedelta

import pytest

from fastmcp.task_management.domain.value_objects.progress import (
    ProgressCalculationStrategy,
    ProgressMetadata,
    ProgressSnapshot,
    ProgressStatus,
    ProgressTimeline,
    ProgressType,
)


class TestProgressType:
    """Test cases for ProgressType enum."""

    def test_progress_type_values(self):
        """Test that ProgressType has correct values."""
        assert ProgressType.ANALYSIS.value == "analysis"
        assert ProgressType.DESIGN.value == "design"
        assert ProgressType.IMPLEMENTATION.value == "implementation"
        assert ProgressType.TESTING.value == "testing"
        assert ProgressType.DOCUMENTATION.value == "documentation"
        assert ProgressType.REVIEW.value == "review"
        assert ProgressType.DEPLOYMENT.value == "deployment"
        assert ProgressType.GENERAL.value == "general"


class TestProgressStatus:
    """Test cases for ProgressStatus enum."""

    def test_progress_status_values(self):
        """Test that ProgressStatus has correct values."""
        assert ProgressStatus.NOT_STARTED.value == "not_started"
        assert ProgressStatus.IN_PROGRESS.value == "in_progress"
        assert ProgressStatus.BLOCKED.value == "blocked"
        assert ProgressStatus.COMPLETED.value == "completed"
        assert ProgressStatus.PAUSED.value == "paused"


class TestProgressMetadata:
    """Test cases for ProgressMetadata value object."""

    def test_create_progress_metadata(self):
        """Test creating ProgressMetadata with all fields."""
        estimated = datetime.now(UTC) + timedelta(days=3)

        metadata = ProgressMetadata(
            blockers=["Missing API specs", "Dependency not ready"],
            dependencies=["task-123", "task-456"],
            confidence_level=0.8,
            notes="Waiting for design approval",
            estimated_completion=estimated,
        )

        assert metadata.blockers == ["Missing API specs", "Dependency not ready"]
        assert metadata.dependencies == ["task-123", "task-456"]
        assert metadata.confidence_level == 0.8
        assert metadata.notes == "Waiting for design approval"
        assert metadata.estimated_completion == estimated

    def test_create_progress_metadata_defaults(self):
        """Test creating ProgressMetadata with default values."""
        metadata = ProgressMetadata()

        assert metadata.blockers == []
        assert metadata.dependencies == []
        assert metadata.confidence_level == 1.0
        assert metadata.notes is None
        assert metadata.estimated_completion is None

    def test_to_dict(self):
        """Test converting metadata to dictionary."""
        estimated = datetime.now(UTC)

        metadata = ProgressMetadata(
            blockers=["Blocker 1"],
            dependencies=["dep-1", "dep-2"],
            confidence_level=0.75,
            notes="Test notes",
            estimated_completion=estimated,
        )

        result = metadata.to_dict()

        assert result["blockers"] == ["Blocker 1"]
        assert result["dependencies"] == ["dep-1", "dep-2"]
        assert result["confidence_level"] == 0.75
        assert result["notes"] == "Test notes"
        assert result["estimated_completion"] == estimated.isoformat()

    def test_to_dict_no_estimated_completion(self):
        """Test to_dict when no estimated completion."""
        metadata = ProgressMetadata(blockers=[], dependencies=[], confidence_level=1.0)

        result = metadata.to_dict()
        assert result["estimated_completion"] is None

    def test_from_dict(self):
        """Test creating metadata from dictionary."""
        estimated = datetime.now(UTC)
        data = {
            "blockers": ["Test blocker"],
            "dependencies": ["dep-123"],
            "confidence_level": 0.9,
            "notes": "From dict",
            "estimated_completion": estimated.isoformat(),
        }

        metadata = ProgressMetadata.from_dict(data)

        assert metadata.blockers == ["Test blocker"]
        assert metadata.dependencies == ["dep-123"]
        assert metadata.confidence_level == 0.9
        assert metadata.notes == "From dict"
        assert (
            abs(metadata.estimated_completion.timestamp() - estimated.timestamp()) < 1
        )

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        metadata = ProgressMetadata.from_dict({})

        assert metadata.blockers == []
        assert metadata.dependencies == []
        assert metadata.confidence_level == 1.0
        assert metadata.notes is None
        assert metadata.estimated_completion is None

    def test_progress_metadata_immutable(self):
        """Test that ProgressMetadata is immutable (frozen)."""
        metadata = ProgressMetadata(confidence_level=0.8)

        with pytest.raises(AttributeError):
            metadata.confidence_level = 0.9

        with pytest.raises(AttributeError):
            metadata.blockers = ["new blocker"]


class TestProgressSnapshot:
    """Test cases for ProgressSnapshot value object."""

    def test_create_progress_snapshot(self):
        """Test creating ProgressSnapshot with all fields."""
        now = datetime.now(UTC)
        metadata = ProgressMetadata(confidence_level=0.85)

        snapshot = ProgressSnapshot(
            id="snap-123",
            task_id="task-456",
            timestamp=now,
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=75.5,
            status=ProgressStatus.IN_PROGRESS,
            description="Completed core functionality",
            metadata=metadata,
            agent_id="agent-789",
        )

        assert snapshot.id == "snap-123"
        assert snapshot.task_id == "task-456"
        assert snapshot.timestamp == now
        assert snapshot.progress_type == ProgressType.IMPLEMENTATION
        assert snapshot.percentage == 75.5
        assert snapshot.status == ProgressStatus.IN_PROGRESS
        assert snapshot.description == "Completed core functionality"
        assert snapshot.metadata == metadata
        assert snapshot.agent_id == "agent-789"

    def test_create_progress_snapshot_defaults(self):
        """Test creating ProgressSnapshot with default values."""
        snapshot = ProgressSnapshot()

        assert len(snapshot.id) > 0  # Auto-generated UUID
        assert snapshot.task_id == ""
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.progress_type == ProgressType.GENERAL
        assert snapshot.percentage == 0.0
        assert snapshot.status == ProgressStatus.NOT_STARTED
        assert snapshot.description is None
        assert isinstance(snapshot.metadata, ProgressMetadata)
        assert snapshot.agent_id is None

    def test_percentage_validation(self):
        """Test percentage validation in post_init."""
        # Valid percentages
        ProgressSnapshot(percentage=0.0)
        ProgressSnapshot(percentage=50.0)
        ProgressSnapshot(percentage=100.0)

        # Invalid percentages
        with pytest.raises(
            ValueError, match="Progress percentage must be between 0 and 100"
        ):
            ProgressSnapshot(percentage=-1.0)

        with pytest.raises(
            ValueError, match="Progress percentage must be between 0 and 100"
        ):
            ProgressSnapshot(percentage=101.0)

    def test_to_dict(self):
        """Test converting snapshot to dictionary."""
        now = datetime.now(UTC)
        metadata = ProgressMetadata(blockers=["Test blocker"], confidence_level=0.9)

        snapshot = ProgressSnapshot(
            id="test-id",
            task_id="task-123",
            timestamp=now,
            progress_type=ProgressType.TESTING,
            percentage=60.0,
            status=ProgressStatus.IN_PROGRESS,
            description="Running unit tests",
            metadata=metadata,
            agent_id="agent-456",
        )

        result = snapshot.to_dict()

        assert result["id"] == "test-id"
        assert result["task_id"] == "task-123"
        assert result["timestamp"] == now.isoformat()
        assert result["progress_type"] == "testing"
        assert result["percentage"] == 60.0
        assert result["status"] == "in_progress"
        assert result["description"] == "Running unit tests"
        assert result["metadata"]["blockers"] == ["Test blocker"]
        assert result["metadata"]["confidence_level"] == 0.9
        assert result["agent_id"] == "agent-456"

    def test_from_dict(self):
        """Test creating snapshot from dictionary."""
        now = datetime.now(UTC)
        data = {
            "id": "from-dict-id",
            "task_id": "task-789",
            "timestamp": now.isoformat(),
            "progress_type": "documentation",
            "percentage": 85.0,
            "status": "completed",
            "description": "Docs complete",
            "metadata": {"confidence_level": 0.95, "notes": "Well documented"},
            "agent_id": "doc-agent",
        }

        snapshot = ProgressSnapshot.from_dict(data)

        assert snapshot.id == "from-dict-id"
        assert snapshot.task_id == "task-789"
        assert abs(snapshot.timestamp.timestamp() - now.timestamp()) < 1
        assert snapshot.progress_type == ProgressType.DOCUMENTATION
        assert snapshot.percentage == 85.0
        assert snapshot.status == ProgressStatus.COMPLETED
        assert snapshot.description == "Docs complete"
        assert snapshot.metadata.confidence_level == 0.95
        assert snapshot.metadata.notes == "Well documented"
        assert snapshot.agent_id == "doc-agent"

    def test_from_dict_with_defaults(self):
        """Test from_dict with minimal data."""
        snapshot = ProgressSnapshot.from_dict({})

        assert len(snapshot.id) > 0  # Auto-generated
        assert snapshot.task_id == ""
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.progress_type == ProgressType.GENERAL
        assert snapshot.percentage == 0.0
        assert snapshot.status == ProgressStatus.NOT_STARTED

    def test_progress_snapshot_immutable(self):
        """Test that ProgressSnapshot is immutable (frozen)."""
        snapshot = ProgressSnapshot(percentage=50.0)

        with pytest.raises(AttributeError):
            snapshot.percentage = 75.0

        with pytest.raises(AttributeError):
            snapshot.status = ProgressStatus.COMPLETED


class TestProgressTimeline:
    """Test cases for ProgressTimeline aggregate."""

    def test_create_progress_timeline(self):
        """Test creating ProgressTimeline."""
        timeline = ProgressTimeline(task_id="task-123")

        assert timeline.task_id == "task-123"
        assert timeline.snapshots == []
        assert timeline.milestones == {}

    def test_add_snapshot(self):
        """Test adding snapshots to timeline."""
        timeline = ProgressTimeline(task_id="task-123")

        snapshot = ProgressSnapshot(
            task_id="task-123", percentage=25.0, progress_type=ProgressType.DESIGN
        )

        timeline.add_snapshot(snapshot)
        assert len(timeline.snapshots) == 1
        assert timeline.snapshots[0] == snapshot

    def test_add_snapshot_wrong_task_id(self):
        """Test adding snapshot with wrong task_id raises error."""
        timeline = ProgressTimeline(task_id="task-123")

        wrong_snapshot = ProgressSnapshot(
            task_id="task-456",  # Different task_id
            percentage=50.0,
        )

        with pytest.raises(
            ValueError, match="Snapshot task_id .+ doesn't match timeline task_id"
        ):
            timeline.add_snapshot(wrong_snapshot)

    def test_snapshots_sorted_by_timestamp(self):
        """Test that snapshots are automatically sorted by timestamp."""
        timeline = ProgressTimeline(task_id="task-123")

        # Add snapshots in reverse chronological order
        now = datetime.now(UTC)
        for i in range(3):
            snapshot = ProgressSnapshot(
                task_id="task-123",
                timestamp=now - timedelta(hours=i),
                percentage=float((3 - i) * 25),
            )
            timeline.add_snapshot(snapshot)

        # Verify they're sorted chronologically
        for i in range(len(timeline.snapshots) - 1):
            assert timeline.snapshots[i].timestamp < timeline.snapshots[i + 1].timestamp

    def test_get_latest_snapshot(self):
        """Test getting the latest snapshot."""
        timeline = ProgressTimeline(task_id="task-123")

        # Empty timeline
        assert timeline.get_latest_snapshot() is None

        # Add snapshots
        now = datetime.now(UTC)
        old_snapshot = ProgressSnapshot(
            task_id="task-123", timestamp=now - timedelta(hours=2), percentage=25.0
        )
        new_snapshot = ProgressSnapshot(
            task_id="task-123", timestamp=now, percentage=75.0
        )

        timeline.add_snapshot(old_snapshot)
        timeline.add_snapshot(new_snapshot)

        latest = timeline.get_latest_snapshot()
        assert latest == new_snapshot

    def test_get_snapshots_by_type(self):
        """Test filtering snapshots by progress type."""
        timeline = ProgressTimeline(task_id="task-123")

        # Add different types
        design_snap = ProgressSnapshot(
            task_id="task-123", progress_type=ProgressType.DESIGN, percentage=100.0
        )
        impl_snap1 = ProgressSnapshot(
            task_id="task-123",
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=50.0,
        )
        impl_snap2 = ProgressSnapshot(
            task_id="task-123",
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=75.0,
        )

        timeline.add_snapshot(design_snap)
        timeline.add_snapshot(impl_snap1)
        timeline.add_snapshot(impl_snap2)

        design_snaps = timeline.get_snapshots_by_type(ProgressType.DESIGN)
        assert len(design_snaps) == 1
        assert design_snaps[0] == design_snap

        impl_snaps = timeline.get_snapshots_by_type(ProgressType.IMPLEMENTATION)
        assert len(impl_snaps) == 2

    def test_get_overall_progress_empty(self):
        """Test overall progress with no snapshots."""
        timeline = ProgressTimeline(task_id="task-123")
        assert timeline.get_overall_progress() == 0.0

    def test_get_overall_progress_single_type(self):
        """Test overall progress with single progress type."""
        timeline = ProgressTimeline(task_id="task-123")

        snapshot = ProgressSnapshot(
            task_id="task-123",
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=60.0,
        )
        timeline.add_snapshot(snapshot)

        assert timeline.get_overall_progress() == 60.0

    def test_get_overall_progress_multiple_types(self):
        """Test overall progress with multiple progress types."""
        timeline = ProgressTimeline(task_id="task-123")

        # Add snapshots for different types
        types_progress = [
            (ProgressType.DESIGN, 100.0),
            (ProgressType.IMPLEMENTATION, 75.0),
            (ProgressType.TESTING, 50.0),
            (ProgressType.DOCUMENTATION, 25.0),
        ]

        for progress_type, percentage in types_progress:
            snapshot = ProgressSnapshot(
                task_id="task-123", progress_type=progress_type, percentage=percentage
            )
            timeline.add_snapshot(snapshot)

        # Average: (100 + 75 + 50 + 25) / 4 = 62.5
        assert timeline.get_overall_progress() == 62.5

    def test_get_overall_progress_uses_latest_per_type(self):
        """Test that overall progress uses only the latest snapshot per type."""
        timeline = ProgressTimeline(task_id="task-123")

        now = datetime.now(UTC)

        # Add multiple snapshots for same type
        old_impl = ProgressSnapshot(
            task_id="task-123",
            timestamp=now - timedelta(hours=2),
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=25.0,
        )
        new_impl = ProgressSnapshot(
            task_id="task-123",
            timestamp=now,
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=75.0,
        )

        timeline.add_snapshot(old_impl)
        timeline.add_snapshot(new_impl)

        assert timeline.get_overall_progress() == 75.0  # Uses latest

    def test_add_milestone(self):
        """Test adding milestones."""
        timeline = ProgressTimeline(task_id="task-123")

        timeline.add_milestone("Design Complete", 25.0)
        timeline.add_milestone("MVP Ready", 60.0)
        timeline.add_milestone("Release", 100.0)

        assert timeline.milestones["Design Complete"] == 25.0
        assert timeline.milestones["MVP Ready"] == 60.0
        assert timeline.milestones["Release"] == 100.0

    def test_add_milestone_validation(self):
        """Test milestone percentage validation."""
        timeline = ProgressTimeline(task_id="task-123")

        with pytest.raises(
            ValueError, match="Milestone percentage must be between 0 and 100"
        ):
            timeline.add_milestone("Invalid", -5.0)

        with pytest.raises(
            ValueError, match="Milestone percentage must be between 0 and 100"
        ):
            timeline.add_milestone("Too High", 105.0)

    def test_is_milestone_reached(self):
        """Test checking if milestone is reached."""
        timeline = ProgressTimeline(task_id="task-123")

        # Add milestones
        timeline.add_milestone("25% Complete", 25.0)
        timeline.add_milestone("50% Complete", 50.0)
        timeline.add_milestone("75% Complete", 75.0)

        # No progress yet
        assert not timeline.is_milestone_reached("25% Complete")

        # Add progress
        timeline.add_snapshot(ProgressSnapshot(task_id="task-123", percentage=30.0))

        assert timeline.is_milestone_reached("25% Complete")
        assert not timeline.is_milestone_reached("50% Complete")
        assert not timeline.is_milestone_reached("75% Complete")

    def test_is_milestone_reached_unknown_milestone(self):
        """Test checking unknown milestone returns False."""
        timeline = ProgressTimeline(task_id="task-123")
        assert not timeline.is_milestone_reached("Unknown Milestone")

    def test_get_progress_trend(self):
        """Test getting progress trend for last N hours."""
        timeline = ProgressTimeline(task_id="task-123")
        now = datetime.now(UTC)

        # Add snapshots at different times
        for i in range(48, -1, -6):  # 48, 42, 36, ..., 6, 0 hours ago
            snapshot = ProgressSnapshot(
                task_id="task-123",
                timestamp=now - timedelta(hours=i),
                percentage=float(100 - i * 2),  # Progress increases over time
            )
            timeline.add_snapshot(snapshot)

        # Get last 24 hours
        trend_24h = timeline.get_progress_trend(hours=24)

        # Should include snapshots from 0, 6, 12, 18 hours ago
        assert len(trend_24h) == 4

        # Verify all are within 24 hours
        cutoff = now - timedelta(hours=24)
        for snapshot in trend_24h:
            assert snapshot.timestamp > cutoff

    def test_to_dict(self):
        """Test converting timeline to dictionary."""
        timeline = ProgressTimeline(task_id="task-123")

        # Add data
        snapshot = ProgressSnapshot(
            task_id="task-123",
            percentage=55.0,
            progress_type=ProgressType.IMPLEMENTATION,
        )
        timeline.add_snapshot(snapshot)
        timeline.add_milestone("Halfway", 50.0)

        result = timeline.to_dict()

        assert result["task_id"] == "task-123"
        assert len(result["snapshots"]) == 1
        assert result["snapshots"][0]["percentage"] == 55.0
        assert result["milestones"]["Halfway"] == 50.0
        assert result["overall_progress"] == 55.0


class TestProgressCalculationStrategy:
    """Test cases for ProgressCalculationStrategy."""

    def test_calculate_weighted_average_empty(self):
        """Test weighted average with empty values."""
        result = ProgressCalculationStrategy.calculate_weighted_average({})
        assert result == 0.0

    def test_calculate_weighted_average_equal_weights(self):
        """Test weighted average with equal weights (default)."""
        values = {"task1": 80.0, "task2": 60.0, "task3": 100.0}

        result = ProgressCalculationStrategy.calculate_weighted_average(values)
        assert result == 80.0  # (80 + 60 + 100) / 3

    def test_calculate_weighted_average_custom_weights(self):
        """Test weighted average with custom weights."""
        values = {"critical": 50.0, "normal": 100.0, "minor": 0.0}
        weights = {"critical": 3.0, "normal": 2.0, "minor": 1.0}

        result = ProgressCalculationStrategy.calculate_weighted_average(values, weights)
        # (50*3 + 100*2 + 0*1) / (3+2+1) = 350/6 ≈ 58.33
        assert abs(result - 58.333) < 0.01

    def test_calculate_weighted_average_missing_weights(self):
        """Test weighted average when some weights are missing."""
        values = {"task1": 75.0, "task2": 90.0, "task3": 60.0}
        weights = {
            "task1": 2.0,
            "task2": 3.0,
            # task3 missing, should default to 1.0
        }

        result = ProgressCalculationStrategy.calculate_weighted_average(values, weights)
        # (75*2 + 90*3 + 60*1) / (2+3+1) = 480/6 = 80.0
        assert result == 80.0

    def test_calculate_weighted_average_zero_total_weight(self):
        """Test weighted average when total weight is zero."""
        values = {"task1": 50.0}
        weights = {"task1": 0.0}

        result = ProgressCalculationStrategy.calculate_weighted_average(values, weights)
        assert result == 0.0

    def test_calculate_from_subtasks_empty(self):
        """Test calculating from empty subtasks."""
        result = ProgressCalculationStrategy.calculate_from_subtasks([])
        assert result == 0.0

    def test_calculate_from_subtasks_simple(self):
        """Test calculating from subtasks without blocked."""
        subtasks = [
            {"status": "completed", "progress": 100.0},
            {"status": "in_progress", "progress": 50.0},
            {"status": "not_started", "progress": 0.0},
        ]

        result = ProgressCalculationStrategy.calculate_from_subtasks(subtasks)
        assert result == 50.0  # (100 + 50 + 0) / 3

    def test_calculate_from_subtasks_exclude_blocked(self):
        """Test calculating from subtasks excluding blocked ones."""
        subtasks = [
            {"status": "completed", "progress": 100.0},
            {"status": "blocked", "progress": 25.0},  # Should be excluded
            {"status": "in_progress", "progress": 60.0},
        ]

        result = ProgressCalculationStrategy.calculate_from_subtasks(
            subtasks, include_blocked=False
        )
        assert result == 80.0  # (100 + 60) / 2

    def test_calculate_from_subtasks_include_blocked(self):
        """Test calculating from subtasks including blocked ones."""
        subtasks = [
            {"status": "completed", "progress": 100.0},
            {"status": "blocked", "progress": 25.0},
            {"status": "in_progress", "progress": 60.0},
        ]

        result = ProgressCalculationStrategy.calculate_from_subtasks(
            subtasks, include_blocked=True
        )
        assert abs(result - 61.67) < 0.01  # (100 + 25 + 60) / 3

    def test_calculate_from_subtasks_all_blocked(self):
        """Test calculating when all subtasks are blocked."""
        subtasks = [
            {"status": "blocked", "progress": 10.0},
            {"status": "blocked", "progress": 20.0},
        ]

        result = ProgressCalculationStrategy.calculate_from_subtasks(
            subtasks, include_blocked=False
        )
        assert result == 0.0  # No valid subtasks

    def test_calculate_from_subtasks_missing_progress(self):
        """Test calculating when subtasks missing progress field."""
        subtasks = [
            {"status": "completed"},  # Missing progress, defaults to 0
            {"status": "in_progress", "progress": 75.0},
        ]

        result = ProgressCalculationStrategy.calculate_from_subtasks(subtasks)
        assert result == 37.5  # (0 + 75) / 2

    def test_calculate_by_milestones_empty(self):
        """Test milestone calculation with no milestones."""
        result = ProgressCalculationStrategy.calculate_by_milestones([], {})
        assert result == 0.0

    def test_calculate_by_milestones_simple(self):
        """Test milestone calculation with completed milestones."""
        completed = ["Design", "Implementation"]
        all_milestones = {
            "Design": 25.0,
            "Implementation": 75.0,
            "Testing": 90.0,
            "Release": 100.0,
        }

        result = ProgressCalculationStrategy.calculate_by_milestones(
            completed, all_milestones
        )
        assert result == 75.0  # Max of completed (25, 75)

    def test_calculate_by_milestones_unknown_completed(self):
        """Test milestone calculation when completed contains unknown milestones."""
        completed = ["Design", "Unknown Milestone"]
        all_milestones = {"Design": 30.0, "Testing": 80.0}

        result = ProgressCalculationStrategy.calculate_by_milestones(
            completed, all_milestones
        )
        assert result == 30.0  # Only counts known milestone

    def test_calculate_by_milestones_no_valid_completed(self):
        """Test milestone calculation with no valid completed milestones."""
        completed = ["Unknown1", "Unknown2"]
        all_milestones = {"Real Milestone": 50.0}

        result = ProgressCalculationStrategy.calculate_by_milestones(
            completed, all_milestones
        )
        assert result == 0.0

    def test_progress_timeline_mutable(self):
        """Test that ProgressTimeline is mutable (not frozen)."""
        timeline = ProgressTimeline(task_id="task-123")

        # Should be able to modify attributes
        timeline.task_id = "task-456"
        assert timeline.task_id == "task-456"

        timeline.milestones["New"] = 50.0
        assert timeline.milestones["New"] == 50.0
