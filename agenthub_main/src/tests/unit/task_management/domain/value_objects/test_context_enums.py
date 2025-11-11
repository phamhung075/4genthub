"""Unit tests for context enums value objects."""

import pytest

from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel


class TestContextLevel:
    """Test cases for ContextLevel enum."""

    def test_context_level_values(self):
        """Test that ContextLevel has correct values."""
        assert ContextLevel.GLOBAL.value == "global"
        assert ContextLevel.PROJECT.value == "project"
        assert ContextLevel.BRANCH.value == "branch"
        assert ContextLevel.TASK.value == "task"

    def test_context_level_str_representation(self):
        """Test string representation of ContextLevel."""
        assert str(ContextLevel.GLOBAL) == "global"
        assert str(ContextLevel.PROJECT) == "project"
        assert str(ContextLevel.BRANCH) == "branch"
        assert str(ContextLevel.TASK) == "task"

    def test_from_string_valid_values(self):
        """Test creating ContextLevel from valid string values."""
        assert ContextLevel.from_string("global") == ContextLevel.GLOBAL
        assert ContextLevel.from_string("project") == ContextLevel.PROJECT
        assert ContextLevel.from_string("branch") == ContextLevel.BRANCH
        assert ContextLevel.from_string("task") == ContextLevel.TASK

    def test_from_string_case_insensitive(self):
        """Test that from_string is case insensitive."""
        assert ContextLevel.from_string("GLOBAL") == ContextLevel.GLOBAL
        assert ContextLevel.from_string("Project") == ContextLevel.PROJECT
        assert ContextLevel.from_string("BrAnCh") == ContextLevel.BRANCH
        assert ContextLevel.from_string("tAsK") == ContextLevel.TASK

    def test_from_string_invalid_value(self):
        """Test that from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="Invalid context level: invalid"):
            ContextLevel.from_string("invalid")

        with pytest.raises(
            ValueError, match="Valid levels are: global, project, branch, task"
        ):
            ContextLevel.from_string("unknown")

    def test_get_parent_level_hierarchy(self):
        """Test getting parent levels in the hierarchy."""
        # Task -> Branch -> Project -> Global -> None
        assert ContextLevel.TASK.get_parent_level() == ContextLevel.BRANCH
        assert ContextLevel.BRANCH.get_parent_level() == ContextLevel.PROJECT
        assert ContextLevel.PROJECT.get_parent_level() == ContextLevel.GLOBAL
        assert ContextLevel.GLOBAL.get_parent_level() is None

    def test_hierarchy_traversal(self):
        """Test traversing the full hierarchy from task to global."""
        levels = []
        current = ContextLevel.TASK

        while current is not None:
            levels.append(current)
            current = current.get_parent_level()

        expected = [
            ContextLevel.TASK,
            ContextLevel.BRANCH,
            ContextLevel.PROJECT,
            ContextLevel.GLOBAL,
        ]
        assert levels == expected

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        # Enums support identity comparison
        assert ContextLevel.GLOBAL == ContextLevel.GLOBAL
        assert ContextLevel.PROJECT != ContextLevel.BRANCH

        # Test with from_string
        assert ContextLevel.from_string("task") == ContextLevel.TASK
        assert ContextLevel.from_string("global") != ContextLevel.PROJECT

    def test_enum_iteration(self):
        """Test iterating over all context levels."""
        all_levels = list(ContextLevel)
        assert len(all_levels) == 4
        assert ContextLevel.GLOBAL in all_levels
        assert ContextLevel.PROJECT in all_levels
        assert ContextLevel.BRANCH in all_levels
        assert ContextLevel.TASK in all_levels

    def test_enum_membership(self):
        """Test membership testing for ContextLevel."""
        # Valid values
        assert "global" in [level.value for level in ContextLevel]
        assert "project" in [level.value for level in ContextLevel]
        assert "branch" in [level.value for level in ContextLevel]
        assert "task" in [level.value for level in ContextLevel]

        # Invalid values
        assert "invalid" not in [level.value for level in ContextLevel]
        assert "unknown" not in [level.value for level in ContextLevel]

    def test_context_level_ordering_consistency(self):
        """Test that context level ordering is consistent with hierarchy."""

        # Create a mapping of levels to their hierarchy depth
        def get_depth(level: ContextLevel) -> int:
            depth = 0
            current = level
            while current.get_parent_level() is not None:
                depth += 1
                current = current.get_parent_level()
            return depth

        depths = {level: get_depth(level) for level in ContextLevel}

        # Verify depths match expected hierarchy
        assert depths[ContextLevel.TASK] == 3
        assert depths[ContextLevel.BRANCH] == 2
        assert depths[ContextLevel.PROJECT] == 1
        assert depths[ContextLevel.GLOBAL] == 0

    def test_from_string_empty_string(self):
        """Test that from_string handles empty string."""
        with pytest.raises(ValueError, match="Invalid context level: "):
            ContextLevel.from_string("")

    def test_from_string_whitespace(self):
        """Test that from_string handles whitespace."""
        # Test with spaces - from_string calls lower() which doesn't strip
        with pytest.raises(ValueError, match="Invalid context level"):
            ContextLevel.from_string("  global  ")

        with pytest.raises(ValueError, match="Invalid context level"):
            ContextLevel.from_string("\ttask\n")

        # Test whitespace-only string
        with pytest.raises(ValueError):
            ContextLevel.from_string("   ")

    def test_enum_hashability(self):
        """Test that ContextLevel enums are hashable and can be used in sets/dicts."""
        # Test in set
        level_set = {ContextLevel.GLOBAL, ContextLevel.PROJECT, ContextLevel.GLOBAL}
        assert len(level_set) == 2  # Duplicate GLOBAL should be removed

        # Test as dict keys
        level_dict = {
            ContextLevel.GLOBAL: "Global level",
            ContextLevel.PROJECT: "Project level",
            ContextLevel.BRANCH: "Branch level",
            ContextLevel.TASK: "Task level",
        }
        assert level_dict[ContextLevel.TASK] == "Task level"

    def test_special_characters_in_from_string(self):
        """Test that from_string handles special characters properly."""
        special_cases = [
            "global!",
            "project@",
            "#branch",
            "task$",
            "glo bal",
            "pro-ject",
        ]

        for case in special_cases:
            with pytest.raises(ValueError, match="Invalid context level"):
                ContextLevel.from_string(case)

    def test_parent_level_immutability(self):
        """Test that get_parent_level doesn't modify the enum."""
        original_task = ContextLevel.TASK
        parent = original_task.get_parent_level()

        # Ensure original is unchanged
        assert original_task == ContextLevel.TASK
        assert parent == ContextLevel.BRANCH
        assert original_task != parent
