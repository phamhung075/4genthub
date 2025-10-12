"""Unit tests for Priority value object."""

import pytest
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel


class TestPriorityCreation:
    """Test Priority creation with valid and invalid inputs."""
    
    def test_create_valid_priority_low(self):
        """Test creating Priority with LOW value."""
        priority = Priority("low")
        assert priority.value == "low"
        assert str(priority) == "low"
    
    def test_create_valid_priority_medium(self):
        """Test creating Priority with MEDIUM value."""
        priority = Priority("medium")
        assert priority.value == "medium"
        assert str(priority) == "medium"
    
    def test_create_valid_priority_high(self):
        """Test creating Priority with HIGH value."""
        priority = Priority("high")
        assert priority.value == "high"
        assert str(priority) == "high"
    
    def test_create_valid_priority_urgent(self):
        """Test creating Priority with URGENT value."""
        priority = Priority("urgent")
        assert priority.value == "urgent"
        assert str(priority) == "urgent"
    
    def test_create_valid_priority_critical(self):
        """Test creating Priority with CRITICAL value."""
        priority = Priority("critical")
        assert priority.value == "critical"
        assert str(priority) == "critical"
    
    def test_all_enum_values_are_valid(self):
        """Test that all PriorityLevel enum values can create valid Priority objects."""
        for priority_enum in PriorityLevel:
            priority = Priority(priority_enum.label)
            assert priority.value == priority_enum.label


class TestPriorityValidation:
    """Test Priority validation and error handling."""
    
    def test_invalid_priority_raises_error(self):
        """Test that invalid priority values raise ValueError."""
        invalid_priorities = ["invalid", "highest", "lowest", "normal", "asap"]
        
        for invalid_priority in invalid_priorities:
            with pytest.raises(ValueError, match="Invalid priority"):
                Priority(invalid_priority)
    
    def test_empty_priority_raises_error(self):
        """Test that empty priority raises ValueError."""
        with pytest.raises(ValueError, match="Priority cannot be empty"):
            Priority("")
    
    def test_none_priority_raises_error(self):
        """Test that None priority raises appropriate error."""
        with pytest.raises(ValueError, match="Priority cannot be empty"):
            Priority(None)
    
    def test_case_sensitivity(self):
        """Test that priority values are case-sensitive."""
        # Priority should be case-sensitive
        with pytest.raises(ValueError, match="Invalid priority"):
            Priority("LOW")  # Uppercase should be invalid
        
        with pytest.raises(ValueError, match="Invalid priority"):
            Priority("Medium")  # Mixed case should be invalid


class TestPriorityFactoryMethods:
    """Test Priority factory methods."""
    
    def test_low_factory(self):
        """Test low() factory method."""
        priority = Priority.low()
        assert priority.value == "low"
        assert priority.order == 1
    
    def test_medium_factory(self):
        """Test medium() factory method."""
        priority = Priority.medium()
        assert priority.value == "medium"
        assert priority.order == 2
    
    def test_high_factory(self):
        """Test high() factory method."""
        priority = Priority.high()
        assert priority.value == "high"
        assert priority.order == 3
    
    def test_urgent_factory(self):
        """Test urgent() factory method."""
        priority = Priority.urgent()
        assert priority.value == "urgent"
        assert priority.order == 4
    
    def test_critical_factory(self):
        """Test critical() factory method."""
        priority = Priority.critical()
        assert priority.value == "critical"
        assert priority.order == 5
    
    def test_from_string_valid(self):
        """Test from_string() with valid values."""
        priority = Priority.from_string("high")
        assert priority.value == "high"
        
        # Test with whitespace
        priority_with_space = Priority.from_string("  critical  ")
        assert priority_with_space.value == "critical"
    
    def test_from_string_empty_defaults_to_medium(self):
        """Test from_string() with empty value defaults to medium."""
        priority = Priority.from_string("")
        assert priority.value == "medium"
        
        priority_none = Priority.from_string(None)
        assert priority_none.value == "medium"


class TestPriorityLevelDetermination:
    
    """Test Priority level and order determination."""
    
    def test_get_level_for_all_priorities(self):
        """Test _get_level() returns correct numeric level."""
        assert Priority.low()._get_level() == 1
        assert Priority.medium()._get_level() == 2
        assert Priority.high()._get_level() == 3
        assert Priority.urgent()._get_level() == 4
        assert Priority.critical()._get_level() == 5
    
    def test_order_property(self):
        """Test order property returns correct numeric level."""
        assert Priority.low().order == 1
        assert Priority.medium().order == 2
        assert Priority.high().order == 3
        assert Priority.urgent().order == 4
        assert Priority.critical().order == 5
    
    def test_is_critical(self):
        """Test is_critical() method."""
        assert Priority.critical().is_critical() is True
        assert Priority.urgent().is_critical() is False
        assert Priority.high().is_critical() is False
        assert Priority.medium().is_critical() is False
        assert Priority.low().is_critical() is False
    
    def test_is_high_or_critical(self):
        """Test is_high_or_critical() method."""
        assert Priority.critical().is_high_or_critical() is True
        assert Priority.high().is_high_or_critical() is True
        assert Priority.urgent().is_high_or_critical() is False
        assert Priority.medium().is_high_or_critical() is False
        assert Priority.low().is_high_or_critical() is False


class TestPriorityComparison:
    
    """Test Priority comparison methods."""
    
    def test_less_than_comparison(self):
        """Test < comparison between priorities."""
        low = Priority.low()
        medium = Priority.medium()
        high = Priority.high()
        urgent = Priority.urgent()
        critical = Priority.critical()
        
        assert low < medium
        assert medium < high
        assert high < urgent
        assert urgent < critical
        assert low < critical
        
        # Not less than itself
        assert not (low < low)
        assert not (critical < critical)
    
    def test_less_than_or_equal_comparison(self):
        """Test <= comparison between priorities."""
        low = Priority.low()
        medium = Priority.medium()
        critical = Priority.critical()
        
        assert low <= medium
        assert low <= low
        assert medium <= critical
        assert critical <= critical
        
        assert not (critical <= low)
    
    def test_greater_than_comparison(self):
        """Test > comparison between priorities."""
        low = Priority.low()
        medium = Priority.medium()
        high = Priority.high()
        urgent = Priority.urgent()
        critical = Priority.critical()
        
        assert medium > low
        assert high > medium
        assert urgent > high
        assert critical > urgent
        assert critical > low
        
        # Not greater than itself
        assert not (low > low)
        assert not (critical > critical)
    
    def test_greater_than_or_equal_comparison(self):
        """Test >= comparison between priorities."""
        low = Priority.low()
        medium = Priority.medium()
        critical = Priority.critical()
        
        assert medium >= low
        assert low >= low
        assert critical >= medium
        assert critical >= critical
        
        assert not (low >= critical)
    
    def test_comparison_chain(self):
        """Test chained comparisons work correctly."""
        low = Priority.low()
        medium = Priority.medium()
        high = Priority.high()
        
        assert low < medium < high
        assert not (high < medium < low)


class TestPriorityEquality:
    
    """Test Priority equality comparison."""
    
    def test_equal_priorities(self):
        """Test that Priority objects with same value are equal."""
        priority1 = Priority("high")
        priority2 = Priority("high")
        assert priority1 == priority2
        
        # Test with factory methods
        priority3 = Priority.high()
        priority4 = Priority.high()
        assert priority3 == priority4
        assert priority1 == priority3
    
    def test_not_equal_priorities(self):
        """Test that Priority objects with different values are not equal."""
        priority1 = Priority("low")
        priority2 = Priority("high")
        assert priority1 != priority2


class TestPriorityOrdering:
    
    """Test Priority ordering and sorting behavior."""
    
    def test_sort_priorities_ascending(self):
        """Test sorting priorities in ascending order."""
        priorities = [
            Priority.critical(),
            Priority.low(),
            Priority.urgent(),
            Priority.medium(),
            Priority.high()
        ]
        
        sorted_priorities = sorted(priorities)
        
        expected_order = [
            Priority.low(),
            Priority.medium(),
            Priority.high(),
            Priority.urgent(),
            Priority.critical()
        ]
        
        assert sorted_priorities == expected_order
    
    def test_sort_priorities_descending(self):
        """Test sorting priorities in descending order."""
        priorities = [
            Priority.low(),
            Priority.critical(),
            Priority.medium(),
            Priority.urgent(),
            Priority.high()
        ]
        
        sorted_priorities = sorted(priorities, reverse=True)
        
        expected_order = [
            Priority.critical(),
            Priority.urgent(),
            Priority.high(),
            Priority.medium(),
            Priority.low()
        ]
        
        assert sorted_priorities == expected_order
    
    def test_max_priority(self):
        """Test finding maximum priority."""
        priorities = [Priority.low(), Priority.high(), Priority.medium()]
        assert max(priorities) == Priority.high()
        
        all_priorities = [
            Priority.low(),
            Priority.medium(),
            Priority.high(),
            Priority.urgent(),
            Priority.critical()
        ]
        assert max(all_priorities) == Priority.critical()
    
    def test_min_priority(self):
        """Test finding minimum priority."""
        priorities = [Priority.low(), Priority.high(), Priority.medium()]
        assert min(priorities) == Priority.low()
        
        all_priorities = [
            Priority.low(),
            Priority.medium(),
            Priority.high(),
            Priority.urgent(),
            Priority.critical()
        ]
        assert min(all_priorities) == Priority.low()


class TestPriorityImmutability:
    
    """Test Priority immutability."""
    
    def test_priority_is_immutable(self):
        """Test that Priority value cannot be changed after creation."""
        priority = Priority("low")
        
        with pytest.raises(AttributeError):
            priority.value = "high"


class TestPriorityHashing:
    
    """Test Priority hashing behavior."""
    
    def test_priority_is_hashable(self):
        """Test that Priority can be used as dict key or in sets."""
        priority1 = Priority("low")
        priority2 = Priority("high")
        priority3 = Priority("low")  # Duplicate
        
        # Test as dict keys
        priority_dict = {priority1: "First", priority2: "Second"}
        assert priority_dict[priority1] == "First"
        assert priority_dict[priority2] == "Second"
        
        # Test in sets
        priority_set = {priority1, priority2, priority3}
        assert len(priority_set) == 2  # Duplicate should be ignored
        assert priority1 in priority_set
        assert priority2 in priority_set
    
    def test_equal_priorities_have_same_hash(self):
        """Test that equal Priority objects have the same hash."""
        priority1 = Priority("medium")
        priority2 = Priority("medium")
        priority3 = Priority.medium()
        
        assert hash(priority1) == hash(priority2)
        assert hash(priority1) == hash(priority3)


class TestPriorityEdgeCases:
    
    """Test edge cases and error handling."""
    
    def test_priority_with_whitespace_in_value(self):
        """Test that priority values with internal whitespace are invalid."""
        with pytest.raises(ValueError, match="Invalid priority"):
            Priority("high priority")  # Space in value
        
        with pytest.raises(ValueError, match="Invalid priority"):
            Priority("very urgent")  # Space in value
    
    def test_priority_string_representation(self):
        """Test string representation of Priority."""
        for priority_enum in PriorityLevel:
            priority = Priority(priority_enum.label)
            assert str(priority) == priority_enum.label
    
    def test_priority_level_enum_properties(self):
        """Test PriorityLevel enum properties."""
        assert PriorityLevel.LOW.label == "low"
        assert PriorityLevel.LOW.level == 1
        
        assert PriorityLevel.CRITICAL.label == "critical"
        assert PriorityLevel.CRITICAL.level == 5
    
    def test_get_level_fallback(self):
        """Test _get_level fallback for edge case (should never happen due to validation)."""
        # This is a defensive test - in practice, validation prevents invalid values
        # We need to bypass validation to test the fallback
        priority = Priority.__new__(Priority)
        object.__setattr__(priority, 'value', 'invalid_priority')
        
        # The fallback should return 0
        assert priority._get_level() == 0


class TestPriorityIntegration:
    
    """Integration tests with real use cases."""
    
    def test_priority_based_task_sorting(self):
        """Test sorting tasks based on priority."""
        # Simulate tasks with priorities
        tasks = [
            {"id": 1, "priority": Priority.low()},
            {"id": 2, "priority": Priority.critical()},
            {"id": 3, "priority": Priority.medium()},
            {"id": 4, "priority": Priority.urgent()},
            {"id": 5, "priority": Priority.high()}
        ]
        
        # Sort by priority (highest first)
        sorted_tasks = sorted(tasks, key=lambda t: t["priority"], reverse=True)
        
        expected_order = [2, 4, 5, 3, 1]  # critical, urgent, high, medium, low
        actual_order = [t["id"] for t in sorted_tasks]
        
        assert actual_order == expected_order
    
    def test_filter_high_priority_tasks(self):
        """Test filtering tasks by high priority."""
        priorities = [
            Priority.low(),
            Priority.medium(),
            Priority.high(),
            Priority.urgent(),
            Priority.critical()
        ]
        
        # Filter high or critical priorities
        high_priority_tasks = [p for p in priorities if p.is_high_or_critical()]
        assert len(high_priority_tasks) == 2
        assert Priority.high() in high_priority_tasks
        assert Priority.critical() in high_priority_tasks
        
        # Filter only critical
        critical_tasks = [p for p in priorities if p.is_critical()]
        assert len(critical_tasks) == 1
        assert critical_tasks[0] == Priority.critical()
    
    def test_priority_in_collections(self):
        """Test using Priority in various collections."""
        # Create priorities
        priorities = [Priority(p.label) for p in PriorityLevel]
        
        # Group by level
        priority_groups = {}
        for priority in priorities:
            level = priority.order
            priority_groups.setdefault(level, []).append(priority)
        
        assert len(priority_groups) == 5
        assert all(len(group) == 1 for group in priority_groups.values())
        
        # Create priority count map
        priority_counts = {
            Priority.low(): 5,
            Priority.medium(): 3,
            Priority.high(): 2,
            Priority.urgent(): 1,
            Priority.critical(): 1
        }
        
        # Find most common priority
        most_common = max(priority_counts.items(), key=lambda x: x[1])
        assert most_common[0] == Priority.low()
        assert most_common[1] == 5