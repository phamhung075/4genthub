"""Unit tests for TaskContextUnified Rich Domain Model (Phase 1).

Tests the business logic methods added to TaskContextUnified entity:
- validate_context_data()
- merge_context_updates()
- add_insight()
- update_progress()

Feature flag: FEATURE_RICH_DOMAIN_MODEL controls behavior (Strangler Fig Pattern).
"""

import pytest
from datetime import datetime, timezone
from fastmcp.task_management.domain.entities.context import TaskContextUnified


class TestTaskContextUnifiedFeatureFlag:
    """Test feature flag behavior for Rich Domain Model."""

    def test_feature_flag_default_value(self):
        """Test that feature flag defaults to False for backward compatibility."""
        context = TaskContextUnified(
            id="test-ctx-1",
            branch_id="branch-1"
        )

        assert context.FEATURE_RICH_DOMAIN_MODEL is False

    def test_feature_flag_can_be_enabled(self):
        """Test that feature flag can be enabled."""
        context = TaskContextUnified(
            id="test-ctx-2",
            branch_id="branch-2"
        )

        # Enable rich domain model
        context.FEATURE_RICH_DOMAIN_MODEL = True
        assert context.FEATURE_RICH_DOMAIN_MODEL is True


class TestValidateContextData:
    """Test validate_context_data() method."""

    def test_validate_with_flag_disabled_always_valid(self):
        """When flag is disabled, validation always passes (legacy behavior)."""
        context = TaskContextUnified(
            id="ctx-1",
            branch_id="br-1",
            progress=150,  # Invalid progress
            task_data={}  # Missing title
        )
        context.FEATURE_RICH_DOMAIN_MODEL = False

        is_valid, errors = context.validate_context_data()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_valid_context(self):
        """Validate a properly structured context."""
        context = TaskContextUnified(
            id="ctx-2",
            branch_id="br-2",
            progress=50,
            task_data={"title": "Test Task"},
            insights=[
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "category": "insight",
                    "content": "Found optimization"
                }
            ],
            blockers={
                "blocker1": {"description": "Waiting for API"}
            }
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_progress_out_of_range(self):
        """Progress must be 0-100."""
        context = TaskContextUnified(
            id="ctx-3",
            branch_id="br-3",
            progress=150,
            task_data={"title": "Test"}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("Progress must be between 0-100" in e for e in errors)

    def test_validate_negative_progress(self):
        """Negative progress is invalid."""
        context = TaskContextUnified(
            id="ctx-4",
            branch_id="br-4",
            progress=-10,
            task_data={"title": "Test"}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("Progress must be between 0-100" in e for e in errors)

    def test_validate_missing_title(self):
        """Task data must contain title."""
        context = TaskContextUnified(
            id="ctx-5",
            branch_id="br-5",
            progress=50,
            task_data={}  # Missing title
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("task_data must contain a title" in e for e in errors)

    def test_validate_insight_not_dict(self):
        """Insights must be dictionaries."""
        context = TaskContextUnified(
            id="ctx-6",
            branch_id="br-6",
            progress=50,
            task_data={"title": "Test"},
            insights=["not a dict"]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("Insight 0 must be a dictionary" in e for e in errors)

    def test_validate_insight_missing_required_fields(self):
        """Insights must have timestamp, category, content."""
        context = TaskContextUnified(
            id="ctx-7",
            branch_id="br-7",
            progress=50,
            task_data={"title": "Test"},
            insights=[
                {"timestamp": "2024-01-01T10:00:00Z"}  # Missing category, content
            ]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("missing required field: category" in e for e in errors)
        assert any("missing required field: content" in e for e in errors)

    def test_validate_insight_invalid_category(self):
        """Insight category must be valid."""
        context = TaskContextUnified(
            id="ctx-8",
            branch_id="br-8",
            progress=50,
            task_data={"title": "Test"},
            insights=[
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "category": "invalid_category",
                    "content": "Test"
                }
            ]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("invalid category: invalid_category" in e for e in errors)

    def test_validate_blocker_missing_description(self):
        """Blockers must have description."""
        context = TaskContextUnified(
            id="ctx-9",
            branch_id="br-9",
            progress=50,
            task_data={"title": "Test"},
            blockers={
                "blocker1": {}  # Missing description
            }
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert any("must have a description" in e for e in errors)

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        context = TaskContextUnified(
            id="ctx-10",
            branch_id="br-10",
            progress=150,  # Invalid
            task_data={},  # Missing title
            insights=[
                {"timestamp": "2024-01-01T10:00:00Z"}  # Missing fields
            ]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        is_valid, errors = context.validate_context_data()

        assert is_valid is False
        assert len(errors) >= 3  # Multiple validation errors


class TestMergeContextUpdates:
    """Test merge_context_updates() method."""

    def test_merge_with_flag_disabled_direct_update(self):
        """When flag is disabled, updates are applied directly (legacy)."""
        context = TaskContextUnified(
            id="ctx-1",
            branch_id="br-1",
            progress=50,
            task_data={"title": "Original"}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = False

        context.merge_context_updates({
            "progress": 75,
            "task_data": {"title": "Updated"}
        })

        assert context.progress == 75
        assert context.task_data["title"] == "Updated"

    def test_merge_progress_increase_allowed(self):
        """Progress can increase without restriction."""
        context = TaskContextUnified(
            id="ctx-2",
            branch_id="br-2",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({"progress": 75})

        assert context.progress == 75

    def test_merge_progress_decrease_ignored_by_default(self):
        """Progress decrease is ignored unless explicitly allowed."""
        context = TaskContextUnified(
            id="ctx-3",
            branch_id="br-3",
            progress=75
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({"progress": 50})

        assert context.progress == 75  # Unchanged

    def test_merge_progress_decrease_with_flag(self):
        """Progress decrease allowed with _allow_progress_decrease flag."""
        context = TaskContextUnified(
            id="ctx-4",
            branch_id="br-4",
            progress=75
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "progress": 50,
            "_allow_progress_decrease": True
        })

        assert context.progress == 50

    def test_merge_progress_clamped_to_range(self):
        """Progress is clamped to 0-100 range."""
        context = TaskContextUnified(
            id="ctx-5",
            branch_id="br-5",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        # Test upper bound
        context.merge_context_updates({"progress": 150})
        assert context.progress == 100

        # Test lower bound with explicit allow
        context.merge_context_updates({
            "progress": -10,
            "_allow_progress_decrease": True
        })
        assert context.progress == 0

    def test_merge_insights_append_only_list(self):
        """Insights are append-only when list provided."""
        context = TaskContextUnified(
            id="ctx-6",
            branch_id="br-6",
            insights=[{"content": "Original"}]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "insights": [{"content": "New 1"}, {"content": "New 2"}]
        })

        assert len(context.insights) == 3
        assert context.insights[0]["content"] == "Original"
        assert context.insights[1]["content"] == "New 1"
        assert context.insights[2]["content"] == "New 2"

    def test_merge_insights_append_only_dict(self):
        """Single insight dict is appended to list."""
        context = TaskContextUnified(
            id="ctx-7",
            branch_id="br-7",
            insights=[{"content": "Original"}]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "insights": {"content": "New"}
        })

        assert len(context.insights) == 2
        assert context.insights[1]["content"] == "New"

    def test_merge_blockers_update(self):
        """Blockers can be added or updated."""
        context = TaskContextUnified(
            id="ctx-8",
            branch_id="br-8",
            blockers={"blocker1": {"description": "Original"}}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "blockers": {
                "blocker1": {"description": "Updated"},
                "blocker2": {"description": "New"}
            }
        })

        assert context.blockers["blocker1"]["description"] == "Updated"
        assert context.blockers["blocker2"]["description"] == "New"

    def test_merge_metadata_deep_merge(self):
        """Metadata is deep merged, not replaced."""
        context = TaskContextUnified(
            id="ctx-9",
            branch_id="br-9",
            metadata={"key1": "value1", "key2": "value2"}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "metadata": {"key2": "updated", "key3": "new"}
        })

        assert context.metadata["key1"] == "value1"  # Preserved
        assert context.metadata["key2"] == "updated"  # Updated
        assert context.metadata["key3"] == "new"  # Added

    def test_merge_nested_dicts_deep_merge(self):
        """Nested dictionaries are deep merged."""
        context = TaskContextUnified(
            id="ctx-10",
            branch_id="br-10",
            task_data={"title": "Test", "status": "todo"},
            execution_context={"files": ["file1.py"]}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "task_data": {"status": "in_progress", "progress": 50},
            "execution_context": {"tests": ["test1.py"]}
        })

        # task_data merged
        assert context.task_data["title"] == "Test"
        assert context.task_data["status"] == "in_progress"
        assert context.task_data["progress"] == 50

        # execution_context merged
        assert context.execution_context["files"] == ["file1.py"]
        assert context.execution_context["tests"] == ["test1.py"]

    def test_merge_next_steps_replaced(self):
        """Next steps are replaced, not appended."""
        context = TaskContextUnified(
            id="ctx-11",
            branch_id="br-11",
            next_steps=["Old step 1", "Old step 2"]
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "next_steps": ["New step 1", "New step 2"]
        })

        assert context.next_steps == ["New step 1", "New step 2"]

    def test_merge_internal_flags_ignored(self):
        """Internal flags (starting with _) are ignored."""
        context = TaskContextUnified(
            id="ctx-12",
            branch_id="br-12",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.merge_context_updates({
            "_internal_flag": "should be ignored",
            "progress": 75
        })

        assert not hasattr(context, "_internal_flag")
        assert context.progress == 75


class TestAddInsight:
    """Test add_insight() method."""

    def test_add_insight_with_flag_disabled_simple(self):
        """When flag is disabled, simple insight is added (legacy)."""
        context = TaskContextUnified(
            id="ctx-1",
            branch_id="br-1"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = False

        context.add_insight(
            category="insight",
            content="Test insight",
            agent="test-agent"
        )

        assert len(context.insights) == 1
        assert context.insights[0]["category"] == "insight"
        assert context.insights[0]["content"] == "Test insight"
        assert context.insights[0]["agent"] == "test-agent"
        assert "timestamp" not in context.insights[0]  # Legacy doesn't add timestamp

    def test_add_insight_valid_categories(self):
        """Test adding insights with all valid categories."""
        context = TaskContextUnified(
            id="ctx-2",
            branch_id="br-2"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        valid_categories = ['insight', 'challenge', 'solution', 'decision', 'technical', 'business']

        for category in valid_categories:
            context.add_insight(
                category=category,
                content=f"Test {category}",
                agent="test-agent"
            )

        assert len(context.insights) == 6
        for i, category in enumerate(valid_categories):
            assert context.insights[i]["category"] == category

    def test_add_insight_invalid_category(self):
        """Invalid category raises ValueError."""
        context = TaskContextUnified(
            id="ctx-3",
            branch_id="br-3"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="Invalid category"):
            context.add_insight(
                category="invalid_category",
                content="Test",
                agent="test-agent"
            )

    def test_add_insight_empty_content(self):
        """Empty content raises ValueError."""
        context = TaskContextUnified(
            id="ctx-4",
            branch_id="br-4"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="content cannot be empty"):
            context.add_insight(
                category="insight",
                content="",
                agent="test-agent"
            )

    def test_add_insight_whitespace_content(self):
        """Whitespace-only content raises ValueError."""
        context = TaskContextUnified(
            id="ctx-5",
            branch_id="br-5"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="content cannot be empty"):
            context.add_insight(
                category="insight",
                content="   ",
                agent="test-agent"
            )

    def test_add_insight_valid_importance_levels(self):
        """Test all valid importance levels."""
        context = TaskContextUnified(
            id="ctx-6",
            branch_id="br-6"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        valid_importance = ['low', 'medium', 'high', 'critical']

        for importance in valid_importance:
            context.add_insight(
                category="insight",
                content=f"Test {importance}",
                agent="test-agent",
                importance=importance
            )

        assert len(context.insights) == 4
        for i, importance in enumerate(valid_importance):
            assert context.insights[i]["importance"] == importance

    def test_add_insight_invalid_importance(self):
        """Invalid importance raises ValueError."""
        context = TaskContextUnified(
            id="ctx-7",
            branch_id="br-7"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="Invalid importance"):
            context.add_insight(
                category="insight",
                content="Test",
                agent="test-agent",
                importance="invalid"
            )

    def test_add_insight_default_values(self):
        """Test default values for agent and importance."""
        context = TaskContextUnified(
            id="ctx-8",
            branch_id="br-8"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.add_insight(
            category="insight",
            content="Test insight"
        )

        assert context.insights[0]["agent"] == "system"
        assert context.insights[0]["importance"] == "medium"

    def test_add_insight_timestamp_added(self):
        """Timestamp is automatically added."""
        context = TaskContextUnified(
            id="ctx-9",
            branch_id="br-9"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        before = datetime.now(timezone.utc)
        context.add_insight(
            category="insight",
            content="Test insight",
            agent="test-agent"
        )
        after = datetime.now(timezone.utc)

        assert "timestamp" in context.insights[0]
        timestamp = datetime.fromisoformat(context.insights[0]["timestamp"])
        assert before <= timestamp <= after

    def test_add_insight_content_stripped(self):
        """Content is stripped of whitespace."""
        context = TaskContextUnified(
            id="ctx-10",
            branch_id="br-10"
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.add_insight(
            category="insight",
            content="  Test with spaces  ",
            agent="test-agent"
        )

        assert context.insights[0]["content"] == "Test with spaces"


class TestUpdateProgress:
    """Test update_progress() method."""

    def test_update_progress_with_flag_disabled_direct(self):
        """When flag is disabled, progress updated directly (legacy)."""
        context = TaskContextUnified(
            id="ctx-1",
            branch_id="br-1",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = False

        context.update_progress(75, notes="Progress update")

        assert context.progress == 75
        assert context.implementation_notes["progress_notes"] == "Progress update"

    def test_update_progress_valid_increase(self):
        """Valid progress increase is applied."""
        context = TaskContextUnified(
            id="ctx-2",
            branch_id="br-2",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.update_progress(75)

        assert context.progress == 75

    def test_update_progress_invalid_too_high(self):
        """Progress > 100 raises ValueError."""
        context = TaskContextUnified(
            id="ctx-3",
            branch_id="br-3",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="Progress must be between 0-100"):
            context.update_progress(150)

    def test_update_progress_invalid_negative(self):
        """Negative progress raises ValueError."""
        context = TaskContextUnified(
            id="ctx-4",
            branch_id="br-4",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="Progress must be between 0-100"):
            context.update_progress(-10)

    def test_update_progress_decrease_not_allowed_by_default(self):
        """Progress decrease raises ValueError by default."""
        context = TaskContextUnified(
            id="ctx-5",
            branch_id="br-5",
            progress=75
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        with pytest.raises(ValueError, match="Progress cannot decrease"):
            context.update_progress(50)

    def test_update_progress_decrease_with_flag(self):
        """Progress decrease allowed with allow_decrease=True."""
        context = TaskContextUnified(
            id="ctx-6",
            branch_id="br-6",
            progress=75
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.update_progress(50, allow_decrease=True)

        assert context.progress == 50

    def test_update_progress_history_tracked(self):
        """Progress changes are tracked in metadata history."""
        context = TaskContextUnified(
            id="ctx-7",
            branch_id="br-7",
            progress=25
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.update_progress(50)
        context.update_progress(75)

        assert "progress_history" in context.metadata
        assert len(context.metadata["progress_history"]) == 2
        assert context.metadata["progress_history"][0]["old_progress"] == 25
        assert context.metadata["progress_history"][0]["new_progress"] == 50
        assert context.metadata["progress_history"][1]["old_progress"] == 50
        assert context.metadata["progress_history"][1]["new_progress"] == 75

    def test_update_progress_with_notes(self):
        """Notes are added to implementation_notes."""
        context = TaskContextUnified(
            id="ctx-8",
            branch_id="br-8",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.update_progress(75, notes="Completed authentication module")

        assert "progress_updates" in context.implementation_notes
        assert len(context.implementation_notes["progress_updates"]) == 1
        assert context.implementation_notes["progress_updates"][0]["progress"] == 75
        assert context.implementation_notes["progress_updates"][0]["notes"] == "Completed authentication module"

    def test_update_progress_multiple_notes(self):
        """Multiple progress updates accumulate notes."""
        context = TaskContextUnified(
            id="ctx-9",
            branch_id="br-9",
            progress=25
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.update_progress(50, notes="First update")
        context.update_progress(75, notes="Second update")

        assert len(context.implementation_notes["progress_updates"]) == 2
        assert context.implementation_notes["progress_updates"][0]["notes"] == "First update"
        assert context.implementation_notes["progress_updates"][1]["notes"] == "Second update"

    def test_update_progress_notes_in_history(self):
        """Notes are included in progress history."""
        context = TaskContextUnified(
            id="ctx-10",
            branch_id="br-10",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        context.update_progress(75, notes="Test notes")

        assert context.metadata["progress_history"][0]["notes"] == "Test notes"

    def test_update_progress_timestamps(self):
        """Progress updates include timestamps."""
        context = TaskContextUnified(
            id="ctx-11",
            branch_id="br-11",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        before = datetime.now(timezone.utc)
        context.update_progress(75, notes="Test")
        after = datetime.now(timezone.utc)

        history_timestamp = datetime.fromisoformat(
            context.metadata["progress_history"][0]["timestamp"]
        )
        notes_timestamp = datetime.fromisoformat(
            context.implementation_notes["progress_updates"][0]["timestamp"]
        )

        assert before <= history_timestamp <= after
        assert before <= notes_timestamp <= after


class TestTaskContextUnifiedIntegration:
    """Integration tests for TaskContextUnified Rich Domain Model."""

    def test_full_rich_domain_workflow(self):
        """Test complete workflow with all rich domain features enabled."""
        # Create context
        context = TaskContextUnified(
            id="workflow-ctx",
            branch_id="workflow-branch",
            progress=0,
            task_data={"title": "Implement authentication"}
        )
        context.FEATURE_RICH_DOMAIN_MODEL = True

        # Validate initial state
        is_valid, errors = context.validate_context_data()
        assert is_valid is True

        # Add initial insight
        context.add_insight(
            category="technical",
            content="Using JWT for authentication",
            agent="architect-agent",
            importance="high"
        )

        # Update progress with notes
        context.update_progress(25, notes="Completed initial setup")

        # Add challenge
        context.add_insight(
            category="challenge",
            content="Database connection timeout issues",
            agent="dev-agent",
            importance="high"
        )

        # Update progress
        context.update_progress(50, notes="Fixed connection pooling")

        # Add solution
        context.add_insight(
            category="solution",
            content="Implemented connection pooling with retry logic",
            agent="dev-agent",
            importance="medium"
        )

        # Merge additional context
        context.merge_context_updates({
            "execution_context": {
                "files_modified": ["auth.py", "database.py"],
                "tests_added": ["test_auth.py"]
            },
            "test_results": {
                "passed": 15,
                "failed": 0,
                "coverage": 95.5
            }
        })

        # Final progress update
        context.update_progress(100, notes="All tests passing, ready for review")

        # Final validation
        is_valid, errors = context.validate_context_data()
        assert is_valid is True

        # Verify state
        assert context.progress == 100
        assert len(context.insights) == 3
        assert len(context.metadata["progress_history"]) == 3
        assert len(context.implementation_notes["progress_updates"]) == 3
        assert "files_modified" in context.execution_context
        assert context.test_results["coverage"] == 95.5

    def test_legacy_behavior_preserved_when_flag_disabled(self):
        """Ensure legacy behavior works when feature flag is disabled."""
        context = TaskContextUnified(
            id="legacy-ctx",
            branch_id="legacy-branch",
            progress=50
        )
        context.FEATURE_RICH_DOMAIN_MODEL = False

        # Validation always passes
        is_valid, errors = context.validate_context_data()
        assert is_valid is True

        # Progress can decrease without restriction
        context.update_progress(25)
        assert context.progress == 25

        # Insights added without validation
        context.add_insight(
            category="invalid_category",  # Would fail with flag enabled
            content="",  # Would fail with flag enabled
            agent="test"
        )
        assert len(context.insights) == 1

        # Merge applies directly
        context.merge_context_updates({
            "progress": 100,
            "custom_field": "custom_value"
        })
        assert context.progress == 100

    def test_feature_flag_can_be_toggled(self):
        """Feature flag can be toggled during runtime."""
        context = TaskContextUnified(
            id="toggle-ctx",
            branch_id="toggle-branch",
            progress=50,
            task_data={"title": "Test"}
        )

        # Start with flag disabled
        context.FEATURE_RICH_DOMAIN_MODEL = False
        is_valid, _ = context.validate_context_data()
        assert is_valid is True  # Always valid

        # Enable flag
        context.FEATURE_RICH_DOMAIN_MODEL = True
        is_valid, _ = context.validate_context_data()
        assert is_valid is True  # Still valid with proper data

        # Make data invalid
        context.progress = 150
        is_valid, errors = context.validate_context_data()
        assert is_valid is False  # Now validation catches errors

        # Disable flag again
        context.FEATURE_RICH_DOMAIN_MODEL = False
        is_valid, _ = context.validate_context_data()
        assert is_valid is True  # Back to always valid
