# Progress Calculation Formulas and Expected Outcomes

## Overview
This document provides the exact mathematical formulas used for calculating parent task progress based on subtask completion, along with comprehensive test scenarios and expected outcomes.

## Core Formula

### Basic Progress Calculation
```python
def calculate_parent_progress(subtasks: List[Subtask]) -> Dict[str, Any]:
    """
    Calculate parent task progress based on subtask completion.
    
    Formula:
    Progress Percentage = (Completed Subtasks / Total Subtasks) × 100
    
    Where:
    - Completed Subtasks = Count of subtasks with status == "done"
    - Total Subtasks = Total count of all subtasks
    - Result is rounded down to nearest integer (floor division)
    """
    total_subtasks = len(subtasks)
    
    if total_subtasks == 0:
        return {
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "in_progress_subtasks": 0,
            "todo_subtasks": 0,
            "progress_percentage": 0,
            "status": "todo",
            "completion_rate": "0/0"
        }
    
    # Count subtasks by status
    completed = sum(1 for subtask in subtasks if subtask.status == "done")
    in_progress = sum(1 for subtask in subtasks if subtask.status == "in_progress")
    todo = sum(1 for subtask in subtasks if subtask.status == "todo")
    
    # Calculate progress percentage (floor division for integer result)
    progress_percentage = int((completed / total_subtasks) * 100)
    
    # Determine parent status based on subtask statuses
    if completed == total_subtasks:
        parent_status = "done"
    elif completed > 0 or in_progress > 0:
        parent_status = "in_progress"
    else:
        parent_status = "todo"
    
    return {
        "total_subtasks": total_subtasks,
        "completed_subtasks": completed,
        "in_progress_subtasks": in_progress,
        "todo_subtasks": todo,
        "progress_percentage": progress_percentage,
        "status": parent_status,
        "completion_rate": f"{completed}/{total_subtasks}"
    }
```

## Formula Variations and Edge Cases

### 1. Standard Integer Division (Recommended)
```python
progress_percentage = int((completed / total) * 100)
```
- **Behavior**: Always rounds down (floor)
- **Example**: 3/7 = 0.4286 → 42.86% → 42%
- **Advantage**: Consistent, conservative estimates

### 2. Rounded Division (Alternative)
```python
progress_percentage = round((completed / total) * 100)
```
- **Behavior**: Rounds to nearest integer
- **Example**: 3/7 = 0.4286 → 42.86% → 43%
- **Advantage**: More accurate representation

### 3. Ceiling Division (Optimistic)
```python
import math
progress_percentage = math.ceil((completed / total) * 100)
```
- **Behavior**: Always rounds up
- **Example**: 3/7 = 0.4286 → 42.86% → 43%
- **Advantage**: Optimistic progress reporting

## Comprehensive Test Scenarios

### Scenario Group 1: Basic Cases

#### Test Case 1.1: Empty Task (0 Subtasks)
```python
subtasks = []
expected_result = {
    "total_subtasks": 0,
    "completed_subtasks": 0,
    "in_progress_subtasks": 0,
    "todo_subtasks": 0,
    "progress_percentage": 0,
    "status": "todo",
    "completion_rate": "0/0"
}
```

#### Test Case 1.2: Single Subtask - Not Started
```python
subtasks = [Subtask(status="todo")]
expected_result = {
    "total_subtasks": 1,
    "completed_subtasks": 0,
    "in_progress_subtasks": 0,
    "todo_subtasks": 1,
    "progress_percentage": 0,
    "status": "todo",
    "completion_rate": "0/1"
}
```

#### Test Case 1.3: Single Subtask - Completed
```python
subtasks = [Subtask(status="done")]
expected_result = {
    "total_subtasks": 1,
    "completed_subtasks": 1,
    "in_progress_subtasks": 0,
    "todo_subtasks": 0,
    "progress_percentage": 100,
    "status": "done",
    "completion_rate": "1/1"
}
```

### Scenario Group 2: Even Division Cases

#### Test Case 2.1: 4 Subtasks - Progressive Completion
| Stage | Completed | Progress | Status | Formula |
|-------|-----------|----------|---------|---------|
| Initial | 0/4 | 0% | todo | (0/4) × 100 = 0% |
| Step 1 | 1/4 | 25% | in_progress | (1/4) × 100 = 25% |
| Step 2 | 2/4 | 50% | in_progress | (2/4) × 100 = 50% |
| Step 3 | 3/4 | 75% | in_progress | (3/4) × 100 = 75% |
| Final | 4/4 | 100% | done | (4/4) × 100 = 100% |

#### Test Case 2.2: 10 Subtasks - Batch Completion
| Stage | Completed | Progress | Status | Formula |
|-------|-----------|----------|---------|---------|
| Initial | 0/10 | 0% | todo | (0/10) × 100 = 0% |
| Batch 1 | 3/10 | 30% | in_progress | (3/10) × 100 = 30% |
| Batch 2 | 5/10 | 50% | in_progress | (5/10) × 100 = 50% |
| Batch 3 | 8/10 | 80% | in_progress | (8/10) × 100 = 80% |
| Final | 10/10 | 100% | done | (10/10) × 100 = 100% |

### Scenario Group 3: Uneven Division Cases (Prime Numbers)

#### Test Case 3.1: 7 Subtasks - Fractional Percentages
| Completed | Exact Calculation | Floor Result | Status |
|-----------|------------------|--------------|---------|
| 0/7 | (0/7) × 100 = 0.000% | 0% | todo |
| 1/7 | (1/7) × 100 = 14.286% | 14% | in_progress |
| 2/7 | (2/7) × 100 = 28.571% | 28% | in_progress |
| 3/7 | (3/7) × 100 = 42.857% | 42% | in_progress |
| 4/7 | (4/7) × 100 = 57.143% | 57% | in_progress |
| 5/7 | (5/7) × 100 = 71.429% | 71% | in_progress |
| 6/7 | (6/7) × 100 = 85.714% | 85% | in_progress |
| 7/7 | (7/7) × 100 = 100.000% | 100% | done |

#### Test Case 3.2: 13 Subtasks - Prime Number Edge Case
| Completed | Exact Calculation | Floor Result | Completion Rate |
|-----------|------------------|--------------|-----------------|
| 1/13 | (1/13) × 100 = 7.692% | 7% | 1/13 |
| 4/13 | (4/13) × 100 = 30.769% | 30% | 4/13 |
| 7/13 | (7/13) × 100 = 53.846% | 53% | 7/13 |
| 10/13 | (10/13) × 100 = 76.923% | 76% | 10/13 |
| 12/13 | (12/13) × 100 = 92.308% | 92% | 12/13 |
| 13/13 | (13/13) × 100 = 100.000% | 100% | 13/13 |

### Scenario Group 4: Large Scale Cases

#### Test Case 4.1: 100 Subtasks - Percentage Points
| Completed | Progress | Status | Significance |
|-----------|----------|---------|--------------|
| 0/100 | 0% | todo | Starting point |
| 25/100 | 25% | in_progress | Quarter complete |
| 50/100 | 50% | in_progress | Half complete |
| 75/100 | 75% | in_progress | Three-quarters |
| 99/100 | 99% | in_progress | Nearly done |
| 100/100 | 100% | done | Complete |

#### Test Case 4.2: 1000 Subtasks - High Precision
| Completed | Progress | Status | Granularity |
|-----------|----------|---------|-------------|
| 1/1000 | 0% | in_progress | (0.1% → 0%) |
| 10/1000 | 1% | in_progress | (1.0% → 1%) |
| 100/1000 | 10% | in_progress | (10.0% → 10%) |
| 999/1000 | 99% | in_progress | (99.9% → 99%) |
| 1000/1000 | 100% | done | (100.0% → 100%) |

### Scenario Group 5: Mixed Status Cases

#### Test Case 5.1: Mixed Progress States
```python
subtasks = [
    Subtask(status="done"),      # 1 completed
    Subtask(status="done"),      # 2 completed  
    Subtask(status="in_progress"), # 1 in progress
    Subtask(status="todo"),      # 1 todo
    Subtask(status="todo")       # 1 todo
]
# Total: 5 subtasks, 2 completed
# Progress: (2/5) × 100 = 40%
# Status: in_progress (has completed + in_progress)
```

Expected Result:
```python
{
    "total_subtasks": 5,
    "completed_subtasks": 2,
    "in_progress_subtasks": 1,
    "todo_subtasks": 2,
    "progress_percentage": 40,
    "status": "in_progress",
    "completion_rate": "2/5"
}
```

## Status Determination Logic

### Status Rules
```python
def determine_parent_status(completed_count, in_progress_count, total_count):
    """
    Determine parent task status based on subtask distribution.
    
    Rules:
    1. If all subtasks are completed → "done"
    2. If any subtask is completed or in_progress → "in_progress"
    3. If all subtasks are todo → "todo"
    """
    if completed_count == total_count and total_count > 0:
        return "done"
    elif completed_count > 0 or in_progress_count > 0:
        return "in_progress"
    else:
        return "todo"
```

### Status Test Cases
| Completed | In Progress | Todo | Total | Expected Status | Reasoning |
|-----------|-------------|------|-------|----------------|-----------|
| 0 | 0 | 0 | 0 | todo | No subtasks |
| 0 | 0 | 5 | 5 | todo | All todo |
| 1 | 0 | 4 | 5 | in_progress | Has completed |
| 0 | 1 | 4 | 5 | in_progress | Has in_progress |
| 2 | 1 | 2 | 5 | in_progress | Mixed states |
| 5 | 0 | 0 | 5 | done | All completed |

## Advanced Calculations

### Weighted Progress (Future Enhancement)
```python
def calculate_weighted_progress(subtasks):
    """
    Calculate progress with weighted subtasks based on complexity/effort.
    
    Formula:
    Weighted Progress = Σ(completed_subtask.weight) / Σ(all_subtasks.weight) × 100
    """
    total_weight = sum(subtask.weight for subtask in subtasks)
    completed_weight = sum(
        subtask.weight for subtask in subtasks 
        if subtask.status == "done"
    )
    
    if total_weight == 0:
        return 0
    
    return int((completed_weight / total_weight) * 100)
```

### Partial Progress Tracking
```python
def calculate_granular_progress(subtasks):
    """
    Calculate progress including partial completion of individual subtasks.
    
    Formula:
    Granular Progress = Σ(subtask.progress_percentage) / (total_subtasks × 100) × 100
    """
    if not subtasks:
        return 0
    
    total_progress = sum(subtask.progress_percentage for subtask in subtasks)
    max_possible_progress = len(subtasks) * 100
    
    return int((total_progress / max_possible_progress) * 100)
```

## Performance Considerations

### Optimization Strategies

#### 1. Caching Results
```python
@lru_cache(maxsize=128)
def calculate_cached_progress(subtask_hash):
    """Cache progress calculations for identical subtask sets."""
    return calculate_parent_progress(subtasks)
```

#### 2. Incremental Updates
```python
def update_progress_incrementally(current_progress, subtask_change):
    """Update progress without recalculating from scratch."""
    if subtask_change.old_status != "done" and subtask_change.new_status == "done":
        # Subtask completed
        new_completed = current_progress["completed_subtasks"] + 1
        new_percentage = int((new_completed / current_progress["total_subtasks"]) * 100)
        return new_percentage
```

#### 3. Batch Processing
```python
def batch_update_progress(parent_tasks):
    """Process multiple parent task progress updates in batch."""
    for task in parent_tasks:
        task.progress = calculate_parent_progress(task.subtasks)
```

## Validation Rules

### Data Integrity Checks
```python
def validate_progress_calculation(result):
    """Validate progress calculation result for consistency."""
    assert 0 <= result["progress_percentage"] <= 100
    assert result["completed_subtasks"] <= result["total_subtasks"]
    assert result["completed_subtasks"] >= 0
    assert result["total_subtasks"] >= 0
    
    # Status validation
    if result["progress_percentage"] == 100:
        assert result["status"] == "done"
    elif result["progress_percentage"] == 0 and result["in_progress_subtasks"] == 0:
        assert result["status"] == "todo"
    else:
        assert result["status"] == "in_progress"
```

## Testing Framework

### Unit Test Structure
```python
class TestProgressCalculation:
    
    @pytest.mark.parametrize("completed,total,expected", [
        (0, 0, 0),      # No subtasks
        (0, 1, 0),      # No progress
        (1, 1, 100),    # Complete
        (1, 4, 25),     # Quarter
        (2, 4, 50),     # Half  
        (3, 4, 75),     # Three quarters
        (3, 7, 42),     # Fractional (42.857% → 42%)
    ])
    def test_progress_calculation(self, completed, total, expected):
        """Test progress calculation with various inputs."""
        result = calculate_parent_progress(create_subtasks(completed, total))
        assert result["progress_percentage"] == expected
    
    def test_status_determination(self):
        """Test status determination logic."""
        # Test all combinations
        test_cases = [
            (0, 0, 5, "todo"),
            (1, 0, 4, "in_progress"),
            (0, 1, 4, "in_progress"),
            (5, 0, 0, "done"),
        ]
        
        for completed, in_progress, todo, expected_status in test_cases:
            result = calculate_parent_progress(
                create_mixed_subtasks(completed, in_progress, todo)
            )
            assert result["status"] == expected_status
```

## Expected Implementation Behavior

### Success Criteria
1. ✅ **Accuracy**: Progress percentages match mathematical formula exactly
2. ✅ **Consistency**: Same inputs always produce same outputs
3. ✅ **Performance**: Calculations complete in <10ms for 1000 subtasks
4. ✅ **Validation**: All edge cases handled gracefully
5. ✅ **Status Logic**: Parent status correctly reflects subtask states
6. ✅ **Completeness**: All subtask states properly counted

### Error Handling
```python
def safe_calculate_progress(subtasks):
    """Safely calculate progress with error handling."""
    try:
        if subtasks is None:
            return create_empty_progress_result()
        
        if not isinstance(subtasks, (list, tuple)):
            raise TypeError("Subtasks must be a list or tuple")
        
        return calculate_parent_progress(subtasks)
        
    except ZeroDivisionError:
        return create_empty_progress_result()
    except Exception as e:
        logger.error(f"Progress calculation error: {e}")
        return create_error_progress_result(str(e))
```

This comprehensive formula documentation ensures accurate, predictable, and efficient progress calculations across all scenarios.