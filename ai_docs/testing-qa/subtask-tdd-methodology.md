# Subtask TDD Methodology and Testing Guide

## Overview

This document provides comprehensive Test-Driven Development (TDD) methodology for subtask management in the DhafnckMCP platform. Based on testing conducted on 2025-09-09, this guide covers TDD patterns, validation requirements, and practical implementation approaches.

## System Validation Findings

### Current Subtask System State

**✅ Working Components:**
- UUID format validation (requires canonical format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- Parent task existence validation
- Clear error messaging with operation IDs and timestamps
- Proper request/response structure with success/failure status

**❌ Blocking Issues:**
- Cannot create parent tasks due to import error in `task_mcp_controller.py`
- Requires existing parent task UUID for all subtask operations
- Cannot test full subtask lifecycle without parent task creation capability

### Validation Requirements Discovered

1. **UUID Format Validation:**
   ```
   ✅ Valid: 550e8400-e29b-41d4-a716-446655440000
   ❌ Invalid: test-task-id
   
   Error: "Invalid Task ID format: 'test-task-id'. Expected canonical UUID format"
   ```

2. **Parent Task Existence:**
   ```
   Error: "Task 550e8400-e29b-41d4-a716-446655440000 not found"
   ```

3. **Operation Tracking:**
   - Each operation gets unique operation_id for tracking
   - Timestamps in ISO format
   - Success/failure status with detailed confirmation objects

## TDD Methodology for Subtasks

### Red-Green-Refactor Cycle

#### Phase 1: Red (Write Failing Tests)

**1.1 Validation Tests**
```python
def test_subtask_list_requires_valid_uuid():
    """Test that list operation fails with invalid UUID format"""
    # RED: This should fail validation
    result = manage_subtask(action="list", task_id="invalid-id")
    assert result.status == "failure"
    assert "Invalid Task ID format" in result.error.message

def test_subtask_list_requires_existing_parent():
    """Test that list operation fails with non-existent parent task"""
    # RED: This should fail parent existence check
    result = manage_subtask(action="list", task_id="550e8400-e29b-41d4-a716-446655440000")
    assert result.status == "failure"
    assert "not found" in result.error.message
```

**1.2 Subtask CRUD Tests**
```python
def test_create_subtask_with_valid_parent():
    """Test creating subtask with valid parent task"""
    # RED: Should fail until parent task exists
    parent_id = create_parent_task()  # This currently fails due to import error
    result = manage_subtask(
        action="create",
        task_id=parent_id,
        title="Test Subtask",
        description="Testing subtask creation"
    )
    assert result.status == "success"
    assert result.metadata.get("task_id") == parent_id

def test_list_subtasks_returns_empty_for_new_parent():
    """Test listing subtasks for parent with no subtasks"""
    parent_id = create_parent_task()
    result = manage_subtask(action="list", task_id=parent_id)
    assert result.status == "success"
    assert len(result.data.get("subtasks", [])) == 0
```

**1.3 Progress Tracking Tests**
```python
def test_subtask_progress_percentage_updates_status():
    """Test that progress percentage automatically updates status"""
    # RED: Should fail until implemented
    subtask_id = create_subtask_with_parent()
    result = manage_subtask(
        action="update",
        task_id=parent_id,
        subtask_id=subtask_id,
        progress_percentage=50
    )
    assert result.status == "success"
    assert result.data.get("status") == "in_progress"
```

#### Phase 2: Green (Make Tests Pass)

**2.1 Fix Import Issues**
```python
# Fix in task_mcp_controller.py
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
# Ensure all required imports are available
```

**2.2 Implement Parent Task Creation**
```python
def create_parent_task_for_testing():
    """Helper function to create parent tasks for subtask testing"""
    return manage_task(
        action="create",
        git_branch_id="550e8400-e29b-41d4-a716-446655440001",
        title="Parent Task for Subtask Testing",
        assignees="@test-orchestrator-agent"
    )
```

**2.3 Implement Subtask Operations**
```python
def implement_subtask_creation():
    """Ensure subtask creation works with all required fields"""
    # Implement agent inheritance from parent task
    # Implement automatic progress calculation
    # Implement context updates
```

#### Phase 3: Refactor (Clean Up Code)

**3.1 Extract Common Patterns**
```python
class SubtaskTestHelper:
    """Helper class for subtask testing patterns"""
    
    @staticmethod
    def create_test_parent() -> str:
        """Create a parent task for testing"""
        pass
    
    @staticmethod
    def assert_valid_subtask_response(response):
        """Assert response has valid subtask structure"""
        pass
    
    @staticmethod
    def cleanup_test_data(parent_id: str):
        """Clean up test data after tests"""
        pass
```

**3.2 Parameterized Tests**
```python
@pytest.mark.parametrize("progress,expected_status", [
    (0, "todo"),
    (25, "in_progress"),
    (50, "in_progress"),
    (75, "in_progress"),
    (100, "done")
])
def test_progress_percentage_to_status_mapping(progress, expected_status):
    """Test automatic status mapping from progress percentage"""
    pass
```

## TDD Templates

### Test File Template

```python
"""
TDD Tests for Subtask Management
Created: 2025-09-09
Purpose: Test subtask CRUD operations with TDD methodology
"""

import pytest
import uuid
from typing import Dict, Any

class TestSubtaskTDD:
    """Test-Driven Development tests for subtask management"""
    
    @pytest.fixture
    def parent_task_id(self) -> str:
        """Fixture to provide valid parent task ID"""
        # GREEN: Implement after fixing import issues
        task_id = str(uuid.uuid4())
        # Create parent task here
        yield task_id
        # Cleanup after test
        
    def test_red_subtask_validation_failures(self):
        """RED: Test validation failures before implementation"""
        # Test invalid UUID format
        result = self.manage_subtask_invalid_uuid()
        assert result["status"] == "failure"
        
        # Test non-existent parent
        result = self.manage_subtask_nonexistent_parent()
        assert result["status"] == "failure"
    
    def test_green_subtask_basic_operations(self, parent_task_id):
        """GREEN: Test basic operations after implementation"""
        # Create subtask
        subtask = self.create_test_subtask(parent_task_id)
        assert subtask["status"] == "success"
        
        # List subtasks
        subtasks = self.list_subtasks(parent_task_id)
        assert len(subtasks["data"]["subtasks"]) > 0
        
        # Get specific subtask
        subtask_detail = self.get_subtask(parent_task_id, subtask["subtask_id"])
        assert subtask_detail["status"] == "success"
    
    def test_refactor_subtask_progress_tracking(self, parent_task_id):
        """REFACTOR: Test refined progress tracking features"""
        # Test progress percentage to status mapping
        # Test parent progress recalculation
        # Test workflow guidance
        pass
```

### Integration Test Template

```python
"""
Integration Tests for Subtask TDD Workflow
Tests the complete subtask lifecycle using TDD patterns
"""

class TestSubtaskIntegrationTDD:
    """Integration tests following TDD methodology"""
    
    def test_complete_subtask_lifecycle_tdd(self):
        """Test complete subtask lifecycle using TDD approach"""
        
        # RED: Test failures before implementation
        self.test_prerequisites_fail()
        
        # GREEN: Implement minimal viable solution
        parent_id = self.implement_parent_task_creation()
        subtask_id = self.implement_subtask_creation(parent_id)
        
        # REFACTOR: Enhance with advanced features
        self.enhance_with_progress_tracking(parent_id, subtask_id)
        self.enhance_with_workflow_guidance(parent_id, subtask_id)
        self.enhance_with_context_updates(parent_id, subtask_id)
    
    def test_agent_inheritance_tdd(self):
        """Test agent inheritance using TDD methodology"""
        # RED: Test agent inheritance failures
        # GREEN: Implement basic agent inheritance
        # REFACTOR: Enhance with conditional assignment
        pass
```

## Practical Implementation Steps

### Step 1: Fix System Prerequisites

```bash
# 1. Fix import issues in task_mcp_controller.py
# 2. Ensure parent task creation works
# 3. Verify database schema supports subtasks
```

### Step 2: Implement Basic TDD Cycle

```python
# RED Phase
def test_subtask_creation_fails_without_parent():
    """Write test that should fail"""
    pass

# GREEN Phase  
def implement_minimal_subtask_creation():
    """Implement just enough to pass the test"""
    pass

# REFACTOR Phase
def enhance_subtask_with_advanced_features():
    """Clean up and add advanced features"""
    pass
```

### Step 3: Build Test Suite

```
tests/
├── unit/
│   ├── test_subtask_validation.py
│   ├── test_subtask_operations.py
│   └── test_subtask_progress.py
├── integration/
│   ├── test_subtask_lifecycle.py
│   └── test_subtask_inheritance.py
└── e2e/
    └── test_complete_subtask_workflow.py
```

## Expected Workflow with TDD

### 1. Feature: Subtask Creation
```
RED → Write failing test for subtask creation
GREEN → Implement minimal subtask creation
REFACTOR → Add agent inheritance, validation, context updates
```

### 2. Feature: Progress Tracking
```
RED → Write failing test for progress percentage mapping
GREEN → Implement basic progress to status mapping
REFACTOR → Add parent progress recalculation and workflow hints
```

### 3. Feature: Context Updates
```
RED → Write failing test for context synchronization
GREEN → Implement basic context updates
REFACTOR → Add insight propagation and blocker management
```

## Test Data Management

### Test Fixtures
```python
@pytest.fixture
def test_parent_task():
    """Provide consistent parent task for testing"""
    return {
        "git_branch_id": "550e8400-e29b-41d4-a716-446655440001",
        "title": "Test Parent Task",
        "assignees": "@test-orchestrator-agent"
    }

@pytest.fixture  
def test_subtask_data():
    """Provide consistent subtask data for testing"""
    return {
        "title": "Test Subtask",
        "description": "Testing subtask functionality",
        "progress_percentage": 0
    }
```

### Cleanup Strategies
```python
def cleanup_test_data(parent_task_id: str):
    """Clean up test data after each test"""
    # Delete all subtasks
    # Delete parent task
    # Clear context data
    pass
```

## Conclusion

This TDD methodology provides a structured approach to subtask development and testing. The key findings show that the subtask system has solid validation and error handling, but requires fixing the parent task creation import issue before full testing can proceed.

Once the import issues are resolved, this TDD approach will enable:
- Robust subtask functionality with comprehensive test coverage
- Clear validation and error handling
- Progressive enhancement through Red-Green-Refactor cycles
- Maintainable test suite with proper fixtures and cleanup

The methodology emphasizes testing failures first (RED), implementing minimal solutions (GREEN), and enhancing with advanced features (REFACTOR), ensuring reliable and maintainable subtask management.

---
*Last Updated: 2025-09-09*
*Status: System validation complete, awaiting import fix for full implementation*