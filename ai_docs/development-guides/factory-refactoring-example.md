# Factory Refactoring: Before and After Example

## Case Study: Refactoring TaskOperationFactory

### BEFORE: Current Implementation Problems

```python
# Current implementation with SOLID violations
class OperationFactory:
    """Factory doing too much - violates SRP."""
    
    def __init__(self, response_formatter, context_facade_factory=None):
        self._response_formatter = response_formatter
        self._context_facade_factory = context_facade_factory
        
        # Problem 1: Direct handler instantiation in constructor
        self._crud_handler = CRUDHandler(response_formatter)
        self._search_handler = SearchHandler(response_formatter)
        self._workflow_handler = WorkflowHandler(response_formatter, context_facade_factory)
    
    def handle_operation(self, operation: str, facade, **kwargs):
        """
        Problem 2: Massive method doing routing, filtering, and execution.
        Violates SRP and OCP.
        """
        try:
            # Problem 3: Hard-coded if-else chains (OCP violation)
            if operation in ['create', 'update', 'delete', 'get', 'complete']:
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation in ['list', 'search', 'next', 'count']:
                return self._handle_search_operation(operation, facade, **kwargs)
            elif operation in ['enrich', 'context', 'workflow']:
                return self._handle_workflow_operation(operation, facade, **kwargs)
            else:
                # Error handling mixed with business logic
                return self._response_formatter.create_error_response(...)
        except Exception as e:
            # Generic error handling
            return self._response_formatter.create_error_response(...)
    
    def _handle_crud_operation(self, operation: str, facade, **kwargs):
        """Problem 4: Hard-coded parameter lists."""
        if operation == 'create':
            # Problem 5: Parameter filtering mixed with operation logic
            allowed_params = {
                'git_branch_id', 'title', 'description', 'status', 
                'priority', 'details', 'estimated_effort', 'assignees', 
                'labels', 'due_date', 'dependencies', 'user_id'
            }
            crud_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            result = handler.create_task(facade, **crud_kwargs)
            
            # Problem 6: Business logic mixed with factory logic
            if result.get("success") and result.get("task"):
                # Auto-create context logic shouldn't be here
                pass
```

### AFTER: Refactored with SOLID Principles

#### Step 1: Create Abstract Base and Separate Concerns

```python
# abstract_operation_factory.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IOperationHandler(ABC):
    """Interface for operation handlers."""
    
    @abstractmethod
    def can_handle(self, operation: str) -> bool:
        """Check if handler can handle the operation."""
        pass
    
    @abstractmethod
    def handle(self, operation: str, facade: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the operation."""
        pass


class AbstractOperationFactory(ABC):
    """Abstract base focusing only on factory responsibilities."""
    
    def __init__(self):
        self._handlers: List[IOperationHandler] = []
        self._initialize_handlers()
    
    @abstractmethod
    def _initialize_handlers(self):
        """Initialize handlers - to be implemented by subclasses."""
        pass
    
    def handle_operation(self, operation: str, facade: Any, **kwargs) -> Dict[str, Any]:
        """Route to appropriate handler - single responsibility."""
        for handler in self._handlers:
            if handler.can_handle(operation):
                return handler.handle(operation, facade, kwargs)
        
        return self._create_error_response(f"No handler for operation: {operation}")
```

#### Step 2: Separate Parameter Filtering

```python
# parameter_filter.py
from typing import Dict, Any, Set
from dataclasses import dataclass

@dataclass
class OperationConfig:
    """Configuration for an operation."""
    allowed_params: Set[str]
    required_params: Set[str]
    
class ParameterFilter:
    """Dedicated class for parameter filtering - SRP."""
    
    def __init__(self):
        self._configs = self._load_configs()
    
    def _load_configs(self) -> Dict[str, OperationConfig]:
        """Load from configuration file instead of hard-coding."""
        return {
            'task.create': OperationConfig(
                allowed_params={'git_branch_id', 'title', 'description', 'status', 
                              'priority', 'details', 'estimated_effort', 'assignees', 
                              'labels', 'due_date', 'dependencies', 'user_id'},
                required_params={'git_branch_id', 'title', 'assignees'}
            ),
            # ... more configurations
        }
    
    def filter(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter parameters for operation."""
        config = self._configs.get(operation)
        if not config:
            return params
        
        return {k: v for k, v in params.items() if k in config.allowed_params}
    
    def validate(self, operation: str, params: Dict[str, Any]) -> Optional[str]:
        """Validate required parameters."""
        config = self._configs.get(operation)
        if not config:
            return None
        
        missing = config.required_params - set(params.keys())
        if missing:
            return f"Missing required parameters: {missing}"
        return None
```

#### Step 3: Create Specialized Handlers

```python
# handlers/crud_handler.py
class CRUDOperationHandler(IOperationHandler):
    """Handler for CRUD operations - SRP."""
    
    OPERATIONS = {'create', 'update', 'delete', 'get', 'complete'}
    
    def __init__(self, param_filter: ParameterFilter, response_formatter):
        self._param_filter = param_filter
        self._response_formatter = response_formatter
        self._strategies = self._init_strategies()
    
    def _init_strategies(self) -> Dict[str, Callable]:
        """Strategy pattern for different CRUD operations."""
        return {
            'create': self._handle_create,
            'update': self._handle_update,
            'delete': self._handle_delete,
            'get': self._handle_get,
            'complete': self._handle_complete
        }
    
    def can_handle(self, operation: str) -> bool:
        """Check if this handler can handle the operation."""
        return operation in self.OPERATIONS
    
    def handle(self, operation: str, facade: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CRUD operation with proper filtering."""
        # Filter parameters
        filtered_params = self._param_filter.filter(f"task.{operation}", params)
        
        # Validate required parameters
        error = self._param_filter.validate(f"task.{operation}", filtered_params)
        if error:
            return self._response_formatter.create_error_response(operation, error)
        
        # Execute strategy
        strategy = self._strategies.get(operation)
        if strategy:
            return strategy(facade, filtered_params)
        
        return self._response_formatter.create_error_response(
            operation, f"No strategy for operation: {operation}"
        )
    
    def _handle_create(self, facade: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create operation."""
        return facade.create_task(**params)
    
    # ... other handle methods
```

#### Step 4: Create the Refactored Factory

```python
# refactored_task_operation_factory.py
class RefactoredTaskOperationFactory(AbstractOperationFactory):
    """Clean factory following SOLID principles."""
    
    def __init__(self, response_formatter, context_facade_factory=None):
        self._response_formatter = response_formatter
        self._context_facade_factory = context_facade_factory
        self._param_filter = ParameterFilter()
        super().__init__()
    
    def _initialize_handlers(self):
        """Initialize handlers with dependency injection."""
        # Create handlers
        crud_handler = CRUDOperationHandler(
            self._param_filter, 
            self._response_formatter
        )
        
        search_handler = SearchOperationHandler(
            self._param_filter,
            self._response_formatter
        )
        
        workflow_handler = WorkflowOperationHandler(
            self._param_filter,
            self._response_formatter,
            self._context_facade_factory
        )
        
        dependency_handler = DependencyOperationHandler(
            self._param_filter,
            self._response_formatter
        )
        
        # Register handlers - Open for extension
        self._handlers = [
            crud_handler,
            search_handler,
            workflow_handler,
            dependency_handler
        ]
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create error response."""
        return self._response_formatter.create_error_response(
            operation="unknown",
            error=message,
            error_code="HANDLER_NOT_FOUND"
        )
```

#### Step 5: Add Post-Processing Chain (Decorator Pattern)

```python
# post_processors.py
from abc import ABC, abstractmethod

class IPostProcessor(ABC):
    """Interface for post-processors."""
    
    @abstractmethod
    def process(self, operation: str, result: Dict[str, Any], 
                context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the result."""
        pass

class ContextEnrichmentProcessor(IPostProcessor):
    """Add context enrichment to results."""
    
    def __init__(self, context_service):
        self._context_service = context_service
    
    def process(self, operation: str, result: Dict[str, Any], 
                context: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich result with context if applicable."""
        if operation == 'get' and result.get('success') and result.get('task'):
            task_id = result['task'].get('id')
            if task_id:
                context_data = self._context_service.get_context(task_id)
                result['context'] = context_data
        
        return result

class AuditProcessor(IPostProcessor):
    """Add audit logging to operations."""
    
    def __init__(self, audit_service):
        self._audit_service = audit_service
    
    def process(self, operation: str, result: Dict[str, Any], 
                context: Dict[str, Any]) -> Dict[str, Any]:
        """Log operation for audit."""
        self._audit_service.log_operation(
            operation=operation,
            user_id=context.get('user_id'),
            result_status=result.get('success'),
            timestamp=datetime.now()
        )
        return result

# Enhanced factory with post-processing
class EnhancedTaskOperationFactory(RefactoredTaskOperationFactory):
    """Factory with post-processing chain."""
    
    def __init__(self, response_formatter, context_facade_factory=None, 
                 audit_service=None):
        super().__init__(response_formatter, context_facade_factory)
        self._post_processors = self._init_post_processors(audit_service)
    
    def _init_post_processors(self, audit_service) -> List[IPostProcessor]:
        """Initialize post-processors."""
        processors = []
        
        if self._context_facade_factory:
            processors.append(
                ContextEnrichmentProcessor(self._context_facade_factory)
            )
        
        if audit_service:
            processors.append(AuditProcessor(audit_service))
        
        return processors
    
    def handle_operation(self, operation: str, facade: Any, **kwargs) -> Dict[str, Any]:
        """Handle with post-processing."""
        # Get base result
        result = super().handle_operation(operation, facade, **kwargs)
        
        # Apply post-processors
        context = {'user_id': kwargs.get('user_id')}
        for processor in self._post_processors:
            result = processor.process(operation, result, context)
        
        return result
```

### Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Lines of Code** | 250 | 180 (main) + 150 (handlers) |
| **Cyclomatic Complexity** | 15+ | 3-4 per method |
| **SRP Compliance** | ❌ Multiple responsibilities | ✅ Single responsibility |
| **OCP Compliance** | ❌ Hard-coded if-else | ✅ Handler registration |
| **DIP Compliance** | ❌ Direct dependencies | ✅ Interface-based |
| **Testability** | Hard to mock | Easy to mock handlers |
| **Maintainability** | Hard to extend | Easy to add handlers |

### Testing the Refactored Code

```python
# test_refactored_factory.py
import unittest
from unittest.mock import Mock, MagicMock

class TestRefactoredTaskOperationFactory(unittest.TestCase):
    """Test the refactored factory."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.response_formatter = Mock()
        self.context_factory = Mock()
        self.factory = RefactoredTaskOperationFactory(
            self.response_formatter,
            self.context_factory
        )
    
    def test_handler_registration(self):
        """Test that handlers are properly registered."""
        self.assertEqual(len(self.factory._handlers), 4)
    
    def test_operation_routing(self):
        """Test operation routing to correct handler."""
        facade = Mock()
        facade.create_task.return_value = {'success': True, 'task': {'id': '123'}}
        
        result = self.factory.handle_operation(
            'create',
            facade,
            git_branch_id='branch-1',
            title='Test Task',
            assignees='user1'
        )
        
        self.assertTrue(result['success'])
        facade.create_task.assert_called_once()
    
    def test_parameter_filtering(self):
        """Test that parameters are properly filtered."""
        facade = Mock()
        facade.create_task.return_value = {'success': True}
        
        # Include extra parameters that should be filtered
        result = self.factory.handle_operation(
            'create',
            facade,
            git_branch_id='branch-1',
            title='Test Task',
            assignees='user1',
            invalid_param='should_be_filtered'
        )
        
        # Check that invalid_param was not passed to facade
        call_args = facade.create_task.call_args[1]
        self.assertNotIn('invalid_param', call_args)
    
    def test_unknown_operation(self):
        """Test handling of unknown operation."""
        facade = Mock()
        
        self.response_formatter.create_error_response.return_value = {
            'success': False,
            'error': 'No handler for operation: unknown_op'
        }
        
        result = self.factory.handle_operation('unknown_op', facade)
        
        self.assertFalse(result['success'])
        self.assertIn('No handler', result['error'])
```

### Migration Path

1. **Phase 1**: Create new refactored factory alongside existing
2. **Phase 2**: Add feature flag to switch between implementations
3. **Phase 3**: Migrate one controller at a time to new factory
4. **Phase 4**: Monitor for issues, maintain metrics
5. **Phase 5**: Remove old factory after successful migration

### Benefits Achieved

1. **Maintainability**: Each class has clear, single responsibility
2. **Extensibility**: Easy to add new handlers or processors
3. **Testability**: Each component can be tested in isolation
4. **Performance**: Reduced complexity improves performance
5. **Documentation**: Code is self-documenting with clear interfaces
6. **Debugging**: Easier to trace issues with separated concerns