# MCP Controller Refactoring Plan

## Overview
Large MCP controller files need to be refactored into modular structures following a factory-based pattern to improve maintainability, testability, and separation of concerns.

## Target Files for Refactoring
1. **task_mcp_controller.py** - 2377 lines 🔴 CRITICAL
2. **subtask_mcp_controller.py** - 1407 lines 🔴 CRITICAL  
3. **workflow_hint_enhancer.py** - 1068 lines 🔴 CRITICAL

## Modular Architecture Pattern

### For each large controller file, create the following structure:

```
{controller_name}/
├── __init__.py                    # Entry point, exports main controller
├── {controller_name}_controller.py # Main controller (entry point)
├── factories/
│   ├── __init__.py
│   ├── operation_factory.py      # Factory for operation handlers
│   ├── validation_factory.py     # Factory for validation components
│   └── response_factory.py       # Factory for response formatting
├── handlers/
│   ├── __init__.py
│   ├── crud_handler.py           # CRUD operations
│   ├── search_handler.py         # Search and list operations
│   ├── dependency_handler.py     # Dependency management
│   └── workflow_handler.py       # Workflow and context operations
├── validators/
│   ├── __init__.py
│   ├── parameter_validator.py    # Parameter validation
│   ├── context_validator.py      # Context validation
│   └── business_validator.py     # Business rule validation
├── services/
│   ├── __init__.py
│   ├── enrichment_service.py     # Response enrichment
│   ├── hint_service.py           # Workflow hints
│   └── progress_service.py       # Progress tracking
└── utils/
    ├── __init__.py
    ├── response_formatter.py     # Response formatting utilities
    └── context_helper.py         # Context manipulation utilities
```

## Implementation Strategy

### Phase 1: Create Folder Structure
- Create directory for each large controller
- Set up the modular file structure

### Phase 2: Extract Components
- Extract handlers for different operation types
- Extract validators for parameter/context validation
- Extract services for enrichment and workflow

### Phase 3: Create Factories
- Implement operation factory to coordinate handlers
- Implement validation factory for all validation logic
- Implement response factory for consistent formatting

### Phase 4: Refactor Main Controller
- Keep main controller as thin entry point
- Delegate all operations to appropriate factories
- Maintain same public interface

### Phase 5: Verify Functionality
- Ensure all public methods work identically
- Run tests to verify no functionality is lost
- Update imports if needed

## Benefits
- **Maintainability**: Smaller, focused files
- **Testability**: Each component can be tested independently  
- **Reusability**: Common patterns can be shared
- **Readability**: Clear separation of concerns
- **Scalability**: Easy to add new operations

## Implementation Order
1. Start with task_mcp_controller.py (largest, most complex)
2. Apply same pattern to subtask_mcp_controller.py
3. Apply same pattern to workflow_hint_enhancer.py
4. Verify all functionality works correctly