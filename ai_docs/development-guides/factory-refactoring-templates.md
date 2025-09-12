# Factory Pattern Refactoring Templates

## 1. Abstract Factory Base Classes

### AbstractFacadeFactory Implementation
```python
"""Abstract base factory for all facade factories following DDD principles."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Generic
import logging

T = TypeVar('T')  # Generic type for facades

class AbstractFacadeFactory(ABC, Generic[T]):
    """
    Abstract base factory implementing singleton pattern and cache management.
    
    This base class provides:
    - Singleton pattern implementation
    - Cache management
    - User validation hooks
    - Consistent error handling
    """
    
    _instances: Dict[type, 'AbstractFacadeFactory'] = {}
    _initialized: Dict[type, bool] = {}
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern at the class level."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._initialized[cls] = False
        return cls._instances[cls]
    
    def __init__(self):
        """Initialize the factory with cache if not already initialized."""
        cls_type = type(self)
        if not self._initialized.get(cls_type, False):
            self._facades_cache: Dict[str, T] = {}
            self._logger = logging.getLogger(self.__class__.__name__)
            self._initialized[cls_type] = True
            self._post_init()
    
    def _post_init(self):
        """Hook for subclasses to perform additional initialization."""
        pass
    
    @abstractmethod
    def _create_facade_impl(self, user_id: str, **kwargs) -> T:
        """
        Actual facade creation logic to be implemented by subclasses.
        
        Args:
            user_id: Validated user identifier
            **kwargs: Additional parameters specific to facade type
            
        Returns:
            Created facade instance
        """
        pass
    
    @abstractmethod
    def _get_cache_key(self, user_id: str, **kwargs) -> str:
        """
        Generate cache key for the facade.
        
        Args:
            user_id: User identifier
            **kwargs: Additional parameters affecting cache key
            
        Returns:
            Cache key string
        """
        pass
    
    def create_facade(self, user_id: str, **kwargs) -> T:
        """
        Create or retrieve cached facade with validation and error handling.
        
        Args:
            user_id: User identifier (required)
            **kwargs: Additional facade-specific parameters
            
        Returns:
            Facade instance
            
        Raises:
            ValueError: If user_id is invalid
        """
        # Validate user
        validated_user_id = self._validate_user(user_id)
        
        # Generate cache key
        cache_key = self._get_cache_key(validated_user_id, **kwargs)
        
        # Check cache
        if cache_key in self._facades_cache:
            self._logger.debug(f"Returning cached facade for {cache_key}")
            return self._facades_cache[cache_key]
        
        try:
            # Create new facade
            facade = self._create_facade_impl(validated_user_id, **kwargs)
            
            # Cache it
            self._facades_cache[cache_key] = facade
            self._logger.info(f"Created new facade for {cache_key}")
            
            return facade
            
        except Exception as e:
            self._logger.error(f"Failed to create facade: {e}")
            return self._handle_creation_error(e, validated_user_id, **kwargs)
    
    def _validate_user(self, user_id: str) -> str:
        """
        Validate user identifier.
        
        Args:
            user_id: User identifier to validate
            
        Returns:
            Validated user identifier
            
        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id:
            raise ValueError("user_id is required for facade creation")
        return user_id
    
    def _handle_creation_error(self, error: Exception, user_id: str, **kwargs) -> T:
        """
        Handle facade creation errors.
        
        Can be overridden by subclasses for custom error handling.
        
        Args:
            error: The exception that occurred
            user_id: User identifier
            **kwargs: Additional parameters
            
        Raises:
            Exception: Re-raises the error by default
        """
        raise error
    
    def clear_cache(self):
        """Clear all cached facades."""
        self._facades_cache.clear()
        self._logger.info("Facade cache cleared")
    
    def get_cached_facade(self, user_id: str, **kwargs) -> Optional[T]:
        """
        Retrieve cached facade if available.
        
        Args:
            user_id: User identifier
            **kwargs: Additional parameters affecting cache key
            
        Returns:
            Cached facade or None
        """
        cache_key = self._get_cache_key(user_id, **kwargs)
        return self._facades_cache.get(cache_key)
    
    @classmethod
    def get_instance(cls) -> 'AbstractFacadeFactory':
        """
        Get singleton instance of the factory.
        
        Returns:
            Factory instance
        """
        return cls()
```

### AbstractOperationFactory Implementation
```python
"""Abstract base factory for operation factories."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

class AbstractOperationFactory(ABC):
    """
    Abstract base for operation factories with handler management.
    
    Provides:
    - Handler registration and management
    - Operation routing
    - Parameter filtering
    - Error handling
    """
    
    def __init__(self, response_formatter):
        """
        Initialize with response formatter.
        
        Args:
            response_formatter: Formatter for standardizing responses
        """
        self._response_formatter = response_formatter
        self._handlers: Dict[str, Any] = {}
        self._operation_map: Dict[str, str] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize handlers
        self._create_handlers()
        self._register_operations()
    
    @abstractmethod
    def _create_handlers(self):
        """Create and register all handlers."""
        pass
    
    @abstractmethod
    def _register_operations(self):
        """Register operation to handler mappings."""
        pass
    
    def register_handler(self, name: str, handler: Any):
        """
        Register a handler.
        
        Args:
            name: Handler identifier
            handler: Handler instance
        """
        self._handlers[name] = handler
        self._logger.debug(f"Registered handler: {name}")
    
    def register_operation(self, operation: str, handler_name: str):
        """
        Map an operation to a handler.
        
        Args:
            operation: Operation identifier
            handler_name: Name of the handler to use
        """
        self._operation_map[operation] = handler_name
    
    def handle_operation(self, operation: str, facade: Any, **kwargs) -> Dict[str, Any]:
        """
        Route operation to appropriate handler.
        
        Args:
            operation: Operation to perform
            facade: Facade to operate on
            **kwargs: Operation parameters
            
        Returns:
            Operation result
        """
        try:
            # Find handler for operation
            handler_name = self._operation_map.get(operation)
            if not handler_name:
                return self._handle_unknown_operation(operation)
            
            handler = self._handlers.get(handler_name)
            if not handler:
                return self._handle_missing_handler(handler_name, operation)
            
            # Filter parameters for the operation
            filtered_params = self._filter_parameters(operation, kwargs)
            
            # Execute operation
            return self._execute_operation(handler, operation, facade, filtered_params)
            
        except Exception as e:
            return self._handle_operation_error(operation, e)
    
    @abstractmethod
    def _filter_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter parameters for the operation.
        
        Args:
            operation: Operation identifier
            params: Raw parameters
            
        Returns:
            Filtered parameters
        """
        pass
    
    def _execute_operation(self, handler: Any, operation: str, 
                          facade: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the operation using the handler.
        
        Args:
            handler: Handler instance
            operation: Operation identifier
            facade: Facade instance
            params: Filtered parameters
            
        Returns:
            Operation result
        """
        # Default implementation - can be overridden
        method_name = f"handle_{operation}"
        if hasattr(handler, method_name):
            method = getattr(handler, method_name)
            return method(facade, **params)
        else:
            # Fallback to generic handle method
            return handler.handle(operation, facade, **params)
    
    def _handle_unknown_operation(self, operation: str) -> Dict[str, Any]:
        """Handle unknown operation."""
        self._logger.error(f"Unknown operation: {operation}")
        return self._response_formatter.create_error_response(
            operation=operation,
            error=f"Unknown operation: {operation}",
            error_code="UNKNOWN_OPERATION"
        )
    
    def _handle_missing_handler(self, handler_name: str, operation: str) -> Dict[str, Any]:
        """Handle missing handler."""
        self._logger.error(f"Handler not found: {handler_name} for operation {operation}")
        return self._response_formatter.create_error_response(
            operation=operation,
            error=f"Handler not configured: {handler_name}",
            error_code="HANDLER_NOT_FOUND"
        )
    
    def _handle_operation_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Handle operation execution error."""
        self._logger.error(f"Operation {operation} failed: {str(error)}")
        return self._response_formatter.create_error_response(
            operation=operation,
            error=f"Operation failed: {str(error)}",
            error_code="OPERATION_FAILED"
        )
```

## 2. Parameter Filter Service

```python
"""Service for filtering and validating operation parameters."""

from typing import Dict, Any, Set, Optional
import logging

class ParameterFilterService:
    """
    Centralized service for parameter filtering and validation.
    
    Replaces hard-coded parameter lists scattered across factories.
    """
    
    def __init__(self):
        """Initialize with parameter configuration."""
        self._operation_params: Dict[str, Set[str]] = {}
        self._logger = logging.getLogger(__name__)
        self._load_configuration()
    
    def _load_configuration(self):
        """Load parameter configuration from config file or database."""
        # This would typically load from a configuration file
        self._operation_params = {
            'task.create': {
                'git_branch_id', 'title', 'description', 'status', 
                'priority', 'details', 'estimated_effort', 'assignees', 
                'labels', 'due_date', 'dependencies', 'user_id'
            },
            'task.update': {
                'task_id', 'title', 'description', 'status', 'priority', 
                'details', 'estimated_effort', 'assignees', 'labels', 
                'due_date', 'context_id', 'completion_summary', 'testing_notes'
            },
            'task.delete': {'task_id'},
            'task.get': {'task_id', 'include_context'},
            'task.complete': {'task_id', 'completion_summary', 'testing_notes'},
            'task.list': {
                'status', 'priority', 'assignee', 'tag', 'git_branch_id', 
                'limit', 'offset', 'sort_by', 'sort_order'
            },
            'task.search': {
                'query', 'status', 'priority', 'assignee', 'tag', 
                'git_branch_id', 'limit', 'offset'
            },
            'task.next': {'git_branch_id', 'include_context'},
            # Add more operations as needed
        }
    
    def filter_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter parameters for an operation.
        
        Args:
            operation: Operation identifier (e.g., 'task.create')
            params: Raw parameters
            
        Returns:
            Filtered parameters containing only allowed keys
        """
        allowed = self._operation_params.get(operation, set())
        
        if not allowed:
            self._logger.warning(f"No parameter configuration for operation: {operation}")
            return params
        
        filtered = {k: v for k, v in params.items() if k in allowed}
        
        # Log filtered out parameters for debugging
        removed = set(params.keys()) - set(filtered.keys())
        if removed:
            self._logger.debug(f"Filtered out parameters for {operation}: {removed}")
        
        return filtered
    
    def validate_required(self, operation: str, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate required parameters are present.
        
        Args:
            operation: Operation identifier
            params: Parameters to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        required = self._get_required_params(operation)
        missing = required - set(params.keys())
        
        if missing:
            return f"Missing required parameters for {operation}: {', '.join(missing)}"
        
        return None
    
    def _get_required_params(self, operation: str) -> Set[str]:
        """
        Get required parameters for an operation.
        
        Args:
            operation: Operation identifier
            
        Returns:
            Set of required parameter names
        """
        # This would typically come from configuration
        required_map = {
            'task.create': {'git_branch_id', 'title', 'assignees'},
            'task.update': {'task_id'},
            'task.delete': {'task_id'},
            'task.get': {'task_id'},
            'task.complete': {'task_id'},
            'task.search': {'query'},
            'task.next': {'git_branch_id'},
        }
        
        return required_map.get(operation, set())
    
    def register_operation(self, operation: str, 
                          allowed_params: Set[str], 
                          required_params: Optional[Set[str]] = None):
        """
        Register parameter configuration for an operation.
        
        Args:
            operation: Operation identifier
            allowed_params: Set of allowed parameter names
            required_params: Set of required parameter names
        """
        self._operation_params[operation] = allowed_params
        if required_params:
            # Store required params separately if needed
            pass
        
        self._logger.info(f"Registered parameters for operation: {operation}")
    
    @classmethod
    def get_instance(cls) -> 'ParameterFilterService':
        """Get singleton instance."""
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance
```

## 3. Factory Registry Pattern

```python
"""Registry pattern for dynamic factory management."""

from typing import Dict, Any, Type, Optional
import logging

class FactoryRegistry:
    """
    Central registry for all factories in the system.
    
    Enables:
    - Dynamic factory registration
    - Factory discovery
    - Dependency injection
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._factories: Dict[str, Any] = {}
        self._factory_types: Dict[str, Type] = {}
        self._logger = logging.getLogger(__name__)
    
    def register_factory(self, name: str, factory_class: Type, 
                        auto_instantiate: bool = True):
        """
        Register a factory class.
        
        Args:
            name: Factory identifier
            factory_class: Factory class type
            auto_instantiate: Whether to create instance immediately
        """
        self._factory_types[name] = factory_class
        
        if auto_instantiate:
            try:
                instance = factory_class.get_instance() if hasattr(factory_class, 'get_instance') else factory_class()
                self._factories[name] = instance
                self._logger.info(f"Registered and instantiated factory: {name}")
            except Exception as e:
                self._logger.error(f"Failed to instantiate factory {name}: {e}")
        else:
            self._logger.info(f"Registered factory type: {name}")
    
    def get_factory(self, name: str) -> Optional[Any]:
        """
        Get a factory instance by name.
        
        Args:
            name: Factory identifier
            
        Returns:
            Factory instance or None
        """
        # Check if already instantiated
        if name in self._factories:
            return self._factories[name]
        
        # Try to instantiate if we have the type
        if name in self._factory_types:
            factory_class = self._factory_types[name]
            try:
                instance = factory_class.get_instance() if hasattr(factory_class, 'get_instance') else factory_class()
                self._factories[name] = instance
                return instance
            except Exception as e:
                self._logger.error(f"Failed to create factory {name}: {e}")
        
        return None
    
    def create_facade(self, facade_type: str, **kwargs) -> Any:
        """
        Create a facade using the appropriate factory.
        
        Args:
            facade_type: Type of facade to create (e.g., 'task', 'project')
            **kwargs: Parameters for facade creation
            
        Returns:
            Created facade instance
            
        Raises:
            ValueError: If factory not found
        """
        factory_name = f"{facade_type}_facade_factory"
        factory = self.get_factory(factory_name)
        
        if not factory:
            raise ValueError(f"Factory not found: {factory_name}")
        
        return factory.create_facade(**kwargs)
    
    def list_factories(self) -> Dict[str, str]:
        """
        List all registered factories.
        
        Returns:
            Dictionary of factory names to their status
        """
        result = {}
        for name in self._factory_types:
            if name in self._factories:
                result[name] = "instantiated"
            else:
                result[name] = "registered"
        return result
    
    @classmethod
    def get_instance(cls) -> 'FactoryRegistry':
        """Get singleton instance."""
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
            cls._instance._auto_register()
        return cls._instance
    
    def _auto_register(self):
        """Auto-register known factories."""
        # Import and register all known factories
        try:
            from application.factories.task_facade_factory import TaskFacadeFactory
            from application.factories.project_facade_factory import ProjectFacadeFactory
            from application.factories.agent_facade_factory import AgentFacadeFactory
            
            self.register_factory('task_facade_factory', TaskFacadeFactory)
            self.register_factory('project_facade_factory', ProjectFacadeFactory)
            self.register_factory('agent_facade_factory', AgentFacadeFactory)
            
        except ImportError as e:
            self._logger.warning(f"Could not auto-register some factories: {e}")
```

## 4. Refactored Operation Factory Example

```python
"""Example of refactored task operation factory using new patterns."""

from typing import Dict, Any
from .abstract_operation_factory import AbstractOperationFactory
from .parameter_filter_service import ParameterFilterService

class RefactoredTaskOperationFactory(AbstractOperationFactory):
    """
    Refactored task operation factory following SOLID principles.
    
    Changes:
    - Extends AbstractOperationFactory
    - Uses ParameterFilterService
    - Cleaner handler registration
    - No hard-coded parameter lists
    """
    
    def __init__(self, response_formatter, context_facade_factory=None):
        """Initialize with dependencies."""
        self._context_facade_factory = context_facade_factory
        self._param_filter = ParameterFilterService.get_instance()
        super().__init__(response_formatter)
    
    def _create_handlers(self):
        """Create and register handlers."""
        from ..handlers.crud_handler import CRUDHandler
        from ..handlers.search_handler import SearchHandler
        from ..handlers.workflow_handler import WorkflowHandler
        
        # Create handlers
        crud_handler = CRUDHandler(self._response_formatter)
        search_handler = SearchHandler(self._response_formatter)
        workflow_handler = WorkflowHandler(
            self._response_formatter, 
            self._context_facade_factory
        )
        
        # Register handlers
        self.register_handler('crud', crud_handler)
        self.register_handler('search', search_handler)
        self.register_handler('workflow', workflow_handler)
    
    def _register_operations(self):
        """Register operation to handler mappings."""
        # CRUD operations
        for op in ['create', 'update', 'delete', 'get', 'complete']:
            self.register_operation(op, 'crud')
        
        # Search operations
        for op in ['list', 'search', 'next', 'count']:
            self.register_operation(op, 'search')
        
        # Workflow operations
        for op in ['enrich', 'context', 'workflow']:
            self.register_operation(op, 'workflow')
        
        # Dependency operations
        for op in ['add_dependency', 'remove_dependency']:
            self.register_operation(op, 'crud')
    
    def _filter_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Use ParameterFilterService for filtering."""
        # Prefix with domain for namespacing
        namespaced_op = f"task.{operation}"
        return self._param_filter.filter_parameters(namespaced_op, params)
    
    def _execute_operation(self, handler: Any, operation: str, 
                          facade: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with enrichment for specific operations."""
        result = super()._execute_operation(handler, operation, facade, params)
        
        # Add enrichment for get operations
        if operation == 'get' and result.get('success'):
            workflow_handler = self._handlers.get('workflow')
            if workflow_handler and result.get('task'):
                result = workflow_handler.enrich_task_response(
                    result, operation, result['task']
                )
        
        return result
```

## 5. Migration Strategy

### Phase 1: Non-Breaking Introduction
```python
# Keep existing factory working while introducing new base
class TaskFacadeFactory(AbstractFacadeFactory):
    """Migrated to use abstract base while maintaining compatibility."""
    
    def _create_facade_impl(self, user_id: str, **kwargs) -> TaskApplicationFacade:
        # Existing creation logic moved here
        pass
    
    def _get_cache_key(self, user_id: str, **kwargs) -> str:
        project_id = kwargs.get('project_id', '')
        return f"{user_id}:{project_id}"
    
    # Keep old methods for backward compatibility
    def create_task_facade(self, project_id: str = None, user_id: str = None):
        """Backward compatible method."""
        return self.create_facade(user_id, project_id=project_id)
```

### Phase 2: Gradual Adoption
```python
# Update callers one at a time
# Old way:
factory = TaskFacadeFactory()
facade = factory.create_task_facade(project_id, user_id)

# New way:
registry = FactoryRegistry.get_instance()
facade = registry.create_facade('task', user_id=user_id, project_id=project_id)
```

### Phase 3: Deprecation
```python
class TaskFacadeFactory(AbstractFacadeFactory):
    def create_task_facade(self, project_id: str = None, user_id: str = None):
        """
        DEPRECATED: Use create_facade() instead.
        This method will be removed in version 2.0.
        """
        import warnings
        warnings.warn(
            "create_task_facade is deprecated, use create_facade instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.create_facade(user_id, project_id=project_id)
```

## Testing Strategy

### Unit Test Template
```python
import unittest
from unittest.mock import Mock, patch

class TestAbstractFacadeFactory(unittest.TestCase):
    """Test abstract facade factory base class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create concrete implementation for testing
        class TestFacadeFactory(AbstractFacadeFactory):
            def _create_facade_impl(self, user_id, **kwargs):
                return Mock(user_id=user_id)
            
            def _get_cache_key(self, user_id, **kwargs):
                return user_id
        
        self.factory = TestFacadeFactory()
    
    def test_singleton_pattern(self):
        """Test singleton implementation."""
        factory1 = TestFacadeFactory.get_instance()
        factory2 = TestFacadeFactory.get_instance()
        self.assertIs(factory1, factory2)
    
    def test_cache_management(self):
        """Test facade caching."""
        facade1 = self.factory.create_facade('user1')
        facade2 = self.factory.create_facade('user1')
        self.assertIs(facade1, facade2)
        
        # Different user should get different facade
        facade3 = self.factory.create_facade('user2')
        self.assertIsNot(facade1, facade3)
    
    def test_cache_clearing(self):
        """Test cache clearing."""
        facade1 = self.factory.create_facade('user1')
        self.factory.clear_cache()
        facade2 = self.factory.create_facade('user1')
        self.assertIsNot(facade1, facade2)
```

## Benefits of Refactoring

1. **Code Reduction**: ~70% less duplicated code
2. **Maintainability**: Single place to update common logic
3. **Testability**: Easier to mock and test
4. **Flexibility**: Easy to add new factories
5. **SOLID Compliance**: Each class has single responsibility
6. **Configuration-Driven**: Parameters defined in config, not code