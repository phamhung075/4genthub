# Design Pattern Implementation Examples

## 1. Strategy Pattern for Validation

### Current Problem: If-Elif Chains
```python
# BEFORE: Current validation with if-elif chains
def validate_entity(entity_type, entity_data):
    if entity_type == "task":
        if not entity_data.get("title"):
            return "Task title is required"
        if not entity_data.get("assignees"):
            return "Task must have assignees"
    elif entity_type == "project":
        if not entity_data.get("name"):
            return "Project name is required"
    elif entity_type == "agent":
        if not entity_data.get("name"):
            return "Agent name is required"
    # More conditions...
```

### Solution: Strategy Pattern Implementation
```python
# validation/strategies.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validation with errors and warnings."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ValidationStrategy(ABC):
    """Abstract base for validation strategies."""
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate the data according to strategy rules."""
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Get list of required fields for this entity."""
        pass

class TaskValidationStrategy(ValidationStrategy):
    """Validation strategy for tasks."""
    
    def get_required_fields(self) -> List[str]:
        return ["title", "assignees", "git_branch_id"]
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.get_required_fields():
            if not data.get(field):
                errors.append(f"Required field '{field}' is missing")
        
        # Business rules
        if data.get("priority") not in ["low", "medium", "high", "urgent", None]:
            errors.append("Invalid priority value")
        
        if data.get("estimated_effort"):
            # Validate effort format
            if not self._validate_effort_format(data["estimated_effort"]):
                warnings.append("Estimated effort should be in format: '2 hours', '3 days'")
        
        # Check dependencies
        if deps := data.get("dependencies"):
            if not isinstance(deps, list):
                errors.append("Dependencies must be a list")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_effort_format(self, effort: str) -> bool:
        """Validate effort string format."""
        import re
        pattern = r'^\d+\s+(hour|hours|day|days|week|weeks)$'
        return bool(re.match(pattern, effort))

class ProjectValidationStrategy(ValidationStrategy):
    """Validation strategy for projects."""
    
    def get_required_fields(self) -> List[str]:
        return ["name", "user_id"]
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.get_required_fields():
            if not data.get(field):
                errors.append(f"Required field '{field}' is missing")
        
        # Name validation
        if name := data.get("name"):
            if len(name) < 3:
                errors.append("Project name must be at least 3 characters")
            if len(name) > 100:
                errors.append("Project name must be less than 100 characters")
            if not name.replace(" ", "").replace("-", "").replace("_", "").isalnum():
                warnings.append("Project name should contain only alphanumeric characters, spaces, hyphens, and underscores")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class ValidationContext:
    """Context for executing validation strategies."""
    
    def __init__(self):
        self._strategies: Dict[str, ValidationStrategy] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default validation strategies."""
        self.register("task", TaskValidationStrategy())
        self.register("project", ProjectValidationStrategy())
        self.register("agent", AgentValidationStrategy())
        self.register("subtask", SubtaskValidationStrategy())
    
    def register(self, entity_type: str, strategy: ValidationStrategy):
        """Register a validation strategy for an entity type."""
        self._strategies[entity_type] = strategy
    
    def validate(self, entity_type: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate data using appropriate strategy."""
        strategy = self._strategies.get(entity_type)
        if not strategy:
            return ValidationResult(
                is_valid=False,
                errors=[f"No validation strategy for entity type: {entity_type}"],
                warnings=[]
            )
        
        return strategy.validate(data)

# Usage example
validator = ValidationContext()

# Validate a task
task_data = {
    "title": "Implement feature",
    "assignees": ["user1"],
    "git_branch_id": "branch-123",
    "priority": "high",
    "estimated_effort": "2 days"
}

result = validator.validate("task", task_data)
if not result.is_valid:
    print("Validation errors:", result.errors)
if result.warnings:
    print("Warnings:", result.warnings)
```

## 2. Builder Pattern for Task Creation

### Current Problem: Complex Constructor
```python
# BEFORE: Complex task creation with many parameters
task = Task(
    id="task-123",
    title="Implement feature",
    description="Long description...",
    status="todo",
    priority="high",
    details="Technical details...",
    estimated_effort="2 days",
    assignees=["user1", "user2"],
    labels=["frontend", "feature"],
    due_date="2024-12-31",
    dependencies=["task-100", "task-101"],
    git_branch_id="branch-123",
    project_id="project-456",
    created_at=datetime.now(),
    updated_at=datetime.now(),
    created_by="user1"
)
```

### Solution: Builder Pattern Implementation
```python
# builders/task_builder.py
from typing import List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import uuid

@dataclass
class Task:
    """Task entity."""
    id: str
    title: str
    git_branch_id: str
    assignees: List[str]
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    details: Optional[str] = None
    estimated_effort: Optional[str] = None
    labels: List[str] = None
    due_date: Optional[str] = None
    dependencies: List[str] = None
    project_id: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    created_by: Optional[str] = None

class TaskBuilder:
    """Builder for creating Task instances with fluent interface."""
    
    def __init__(self):
        """Initialize builder with defaults."""
        self._reset()
    
    def _reset(self):
        """Reset builder to initial state."""
        self._id = str(uuid.uuid4())
        self._title = None
        self._description = None
        self._status = "todo"
        self._priority = "medium"
        self._details = None
        self._estimated_effort = None
        self._assignees = []
        self._labels = []
        self._due_date = None
        self._dependencies = []
        self._git_branch_id = None
        self._project_id = None
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._created_by = None
    
    def with_title(self, title: str) -> 'TaskBuilder':
        """Set task title."""
        self._title = title
        return self
    
    def with_description(self, description: str) -> 'TaskBuilder':
        """Set task description."""
        self._description = description
        return self
    
    def with_status(self, status: str) -> 'TaskBuilder':
        """Set task status."""
        if status not in ["todo", "in_progress", "blocked", "review", "done"]:
            raise ValueError(f"Invalid status: {status}")
        self._status = status
        return self
    
    def with_priority(self, priority: str) -> 'TaskBuilder':
        """Set task priority."""
        if priority not in ["low", "medium", "high", "urgent", "critical"]:
            raise ValueError(f"Invalid priority: {priority}")
        self._priority = priority
        return self
    
    def with_assignees(self, *assignees: str) -> 'TaskBuilder':
        """Add assignees to task."""
        self._assignees.extend(assignees)
        return self
    
    def with_labels(self, *labels: str) -> 'TaskBuilder':
        """Add labels to task."""
        self._labels.extend(labels)
        return self
    
    def with_dependencies(self, *task_ids: str) -> 'TaskBuilder':
        """Add task dependencies."""
        self._dependencies.extend(task_ids)
        return self
    
    def with_effort(self, effort: str) -> 'TaskBuilder':
        """Set estimated effort."""
        self._estimated_effort = effort
        return self
    
    def with_due_date(self, due_date: str) -> 'TaskBuilder':
        """Set due date."""
        self._due_date = due_date
        return self
    
    def in_project(self, project_id: str) -> 'TaskBuilder':
        """Set project context."""
        self._project_id = project_id
        return self
    
    def in_branch(self, git_branch_id: str) -> 'TaskBuilder':
        """Set git branch context."""
        self._git_branch_id = git_branch_id
        return self
    
    def created_by(self, user_id: str) -> 'TaskBuilder':
        """Set creator."""
        self._created_by = user_id
        return self
    
    def build(self) -> Task:
        """Build the task with validation."""
        # Validate required fields
        if not self._title:
            raise ValueError("Task title is required")
        if not self._git_branch_id:
            raise ValueError("Git branch ID is required")
        if not self._assignees:
            raise ValueError("At least one assignee is required")
        
        # Create task
        task = Task(
            id=self._id,
            title=self._title,
            description=self._description,
            status=self._status,
            priority=self._priority,
            details=self._details,
            estimated_effort=self._estimated_effort,
            assignees=self._assignees,
            labels=self._labels or [],
            due_date=self._due_date,
            dependencies=self._dependencies or [],
            git_branch_id=self._git_branch_id,
            project_id=self._project_id,
            created_at=self._created_at,
            updated_at=self._updated_at,
            created_by=self._created_by
        )
        
        # Reset builder for next use
        self._reset()
        
        return task

# Director class for common task configurations
class TaskDirector:
    """Director for creating common task configurations."""
    
    @staticmethod
    def create_bug_task(builder: TaskBuilder, title: str, 
                       description: str, assignee: str) -> Task:
        """Create a bug fix task."""
        return (builder
                .with_title(f"[BUG] {title}")
                .with_description(description)
                .with_priority("high")
                .with_labels("bug", "fix")
                .with_assignees(assignee)
                .build())
    
    @staticmethod
    def create_feature_task(builder: TaskBuilder, title: str,
                           description: str, team: List[str]) -> Task:
        """Create a feature task."""
        return (builder
                .with_title(f"[FEATURE] {title}")
                .with_description(description)
                .with_priority("medium")
                .with_labels("feature", "enhancement")
                .with_assignees(*team)
                .build())

# Usage examples
builder = TaskBuilder()

# Simple task
task1 = (builder
         .with_title("Fix login bug")
         .with_priority("high")
         .with_assignees("dev1")
         .in_branch("branch-123")
         .build())

# Complex task with all options
task2 = (builder
         .with_title("Implement OAuth2")
         .with_description("Add OAuth2 authentication support")
         .with_priority("high")
         .with_status("in_progress")
         .with_assignees("dev1", "dev2")
         .with_labels("security", "authentication")
         .with_dependencies("task-100", "task-101")
         .with_effort("5 days")
         .with_due_date("2024-12-31")
         .in_project("project-456")
         .in_branch("feature/oauth")
         .created_by("manager1")
         .build())

# Using director for common patterns
director = TaskDirector()
bug_task = director.create_bug_task(
    builder,
    "Login fails with special characters",
    "Users cannot login when password contains @#$",
    "security-team"
)
```

## 3. Command Pattern for Operations

### Implementation: Command Pattern for Task Operations
```python
# commands/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class Command(ABC):
    """Abstract base for commands."""
    
    @abstractmethod
    def execute(self) -> CommandResult:
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self) -> CommandResult:
        """Undo the command."""
        pass
    
    @abstractmethod
    def can_execute(self) -> bool:
        """Check if command can be executed."""
        pass
    
    def __str__(self) -> str:
        """String representation of command."""
        return self.__class__.__name__

# commands/task_commands.py
class CreateTaskCommand(Command):
    """Command to create a task."""
    
    def __init__(self, facade, task_data: Dict[str, Any]):
        self._facade = facade
        self._task_data = task_data
        self._created_task_id = None
    
    def can_execute(self) -> bool:
        """Check if task can be created."""
        # Validate required fields
        required = ["title", "assignees", "git_branch_id"]
        return all(self._task_data.get(field) for field in required)
    
    def execute(self) -> CommandResult:
        """Create the task."""
        if not self.can_execute():
            return CommandResult(
                success=False,
                error="Cannot execute: missing required fields"
            )
        
        try:
            result = self._facade.create_task(**self._task_data)
            if result.get("success"):
                self._created_task_id = result["task"]["id"]
                logger.info(f"Created task: {self._created_task_id}")
                return CommandResult(
                    success=True,
                    data=result["task"],
                    metadata={"task_id": self._created_task_id}
                )
            else:
                return CommandResult(
                    success=False,
                    error=result.get("error", "Unknown error")
                )
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return CommandResult(
                success=False,
                error=str(e)
            )
    
    def undo(self) -> CommandResult:
        """Delete the created task."""
        if not self._created_task_id:
            return CommandResult(
                success=False,
                error="No task to undo"
            )
        
        try:
            result = self._facade.delete_task(self._created_task_id)
            if result.get("success"):
                logger.info(f"Undone: deleted task {self._created_task_id}")
                self._created_task_id = None
                return CommandResult(success=True)
            else:
                return CommandResult(
                    success=False,
                    error=result.get("error", "Failed to undo")
                )
        except Exception as e:
            logger.error(f"Failed to undo task creation: {e}")
            return CommandResult(
                success=False,
                error=str(e)
            )

class UpdateTaskCommand(Command):
    """Command to update a task."""
    
    def __init__(self, facade, task_id: str, updates: Dict[str, Any]):
        self._facade = facade
        self._task_id = task_id
        self._updates = updates
        self._original_data = None
    
    def can_execute(self) -> bool:
        """Check if task can be updated."""
        return bool(self._task_id and self._updates)
    
    def execute(self) -> CommandResult:
        """Update the task."""
        if not self.can_execute():
            return CommandResult(
                success=False,
                error="Cannot execute: invalid parameters"
            )
        
        try:
            # Store original data for undo
            original = self._facade.get_task(self._task_id)
            if original.get("success"):
                self._original_data = original["task"]
            
            # Execute update
            result = self._facade.update_task(
                task_id=self._task_id,
                **self._updates
            )
            
            if result.get("success"):
                logger.info(f"Updated task: {self._task_id}")
                return CommandResult(
                    success=True,
                    data=result["task"]
                )
            else:
                return CommandResult(
                    success=False,
                    error=result.get("error", "Update failed")
                )
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return CommandResult(
                success=False,
                error=str(e)
            )
    
    def undo(self) -> CommandResult:
        """Restore original task data."""
        if not self._original_data:
            return CommandResult(
                success=False,
                error="No original data to restore"
            )
        
        try:
            # Restore original values
            restore_data = {
                k: self._original_data.get(k)
                for k in self._updates.keys()
                if k in self._original_data
            }
            
            result = self._facade.update_task(
                task_id=self._task_id,
                **restore_data
            )
            
            if result.get("success"):
                logger.info(f"Restored task: {self._task_id}")
                return CommandResult(success=True)
            else:
                return CommandResult(
                    success=False,
                    error="Failed to restore"
                )
        except Exception as e:
            logger.error(f"Failed to undo task update: {e}")
            return CommandResult(
                success=False,
                error=str(e)
            )

# commands/macro_command.py
class MacroCommand(Command):
    """Composite command that executes multiple commands."""
    
    def __init__(self, commands: List[Command]):
        self._commands = commands
        self._executed_commands = []
    
    def can_execute(self) -> bool:
        """Check if all commands can execute."""
        return all(cmd.can_execute() for cmd in self._commands)
    
    def execute(self) -> CommandResult:
        """Execute all commands in sequence."""
        if not self.can_execute():
            return CommandResult(
                success=False,
                error="Not all commands can execute"
            )
        
        results = []
        for command in self._commands:
            result = command.execute()
            if result.success:
                self._executed_commands.append(command)
                results.append(result)
            else:
                # Rollback on failure
                self._rollback()
                return CommandResult(
                    success=False,
                    error=f"Failed at {command}: {result.error}"
                )
        
        return CommandResult(
            success=True,
            data=results,
            metadata={"executed_count": len(results)}
        )
    
    def undo(self) -> CommandResult:
        """Undo all executed commands in reverse order."""
        return self._rollback()
    
    def _rollback(self) -> CommandResult:
        """Rollback executed commands."""
        errors = []
        for command in reversed(self._executed_commands):
            result = command.undo()
            if not result.success:
                errors.append(f"{command}: {result.error}")
        
        self._executed_commands.clear()
        
        if errors:
            return CommandResult(
                success=False,
                error="; ".join(errors)
            )
        return CommandResult(success=True)

# commands/invoker.py
class CommandInvoker:
    """Invoker that executes commands with history tracking."""
    
    def __init__(self, max_history: int = 100):
        self._history: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history
    
    def execute(self, command: Command) -> CommandResult:
        """Execute a command and add to history."""
        result = command.execute()
        
        if result.success:
            self._history.append(command)
            self._redo_stack.clear()  # Clear redo stack on new command
            
            # Limit history size
            if len(self._history) > self._max_history:
                self._history.pop(0)
        
        return result
    
    def undo(self) -> CommandResult:
        """Undo the last command."""
        if not self._history:
            return CommandResult(
                success=False,
                error="Nothing to undo"
            )
        
        command = self._history.pop()
        result = command.undo()
        
        if result.success:
            self._redo_stack.append(command)
        
        return result
    
    def redo(self) -> CommandResult:
        """Redo the last undone command."""
        if not self._redo_stack:
            return CommandResult(
                success=False,
                error="Nothing to redo"
            )
        
        command = self._redo_stack.pop()
        return self.execute(command)
    
    def get_history(self) -> List[str]:
        """Get command history."""
        return [str(cmd) for cmd in self._history]

# Usage example
invoker = CommandInvoker()
facade = TaskApplicationFacade()

# Create a task
create_cmd = CreateTaskCommand(facade, {
    "title": "Implement feature",
    "assignees": ["dev1"],
    "git_branch_id": "branch-123"
})
result = invoker.execute(create_cmd)

# Update the task
if result.success:
    task_id = result.metadata["task_id"]
    update_cmd = UpdateTaskCommand(facade, task_id, {
        "priority": "high",
        "status": "in_progress"
    })
    invoker.execute(update_cmd)

# Undo last operation
invoker.undo()  # Reverts the update

# Redo
invoker.redo()  # Re-applies the update

# Batch operations with macro command
macro = MacroCommand([
    CreateTaskCommand(facade, {...}),
    CreateTaskCommand(facade, {...}),
    UpdateTaskCommand(facade, task_id, {...})
])
invoker.execute(macro)
```

## 4. Service Registry Pattern

### Implementation: Centralized Service Management
```python
# services/registry.py
from typing import Dict, Any, Type, Optional, Callable
from abc import ABC, abstractmethod
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceScope(Enum):
    """Service lifetime scope."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

class ServiceDescriptor:
    """Describes a service registration."""
    
    def __init__(self, 
                 service_type: Type,
                 implementation: Optional[Type] = None,
                 factory: Optional[Callable] = None,
                 instance: Optional[Any] = None,
                 scope: ServiceScope = ServiceScope.SINGLETON):
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.instance = instance
        self.scope = scope

class ServiceRegistry:
    """Central registry for all services."""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        
    def register_singleton(self, service_type: Type, 
                          implementation: Optional[Type] = None,
                          factory: Optional[Callable] = None):
        """Register a singleton service."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            scope=ServiceScope.SINGLETON
        )
        self._services[service_type] = descriptor
        logger.info(f"Registered singleton: {service_type.__name__}")
    
    def register_transient(self, service_type: Type,
                          implementation: Optional[Type] = None,
                          factory: Optional[Callable] = None):
        """Register a transient service."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            scope=ServiceScope.TRANSIENT
        )
        self._services[service_type] = descriptor
        logger.info(f"Registered transient: {service_type.__name__}")
    
    def register_instance(self, service_type: Type, instance: Any):
        """Register an existing instance."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            scope=ServiceScope.SINGLETON
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        logger.info(f"Registered instance: {service_type.__name__}")
    
    def resolve(self, service_type: Type) -> Any:
        """Resolve a service instance."""
        if service_type not in self._services:
            raise ValueError(f"Service not registered: {service_type.__name__}")
        
        descriptor = self._services[service_type]
        
        # Return existing singleton
        if descriptor.scope == ServiceScope.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
        
        # Create instance
        instance = self._create_instance(descriptor)
        
        # Cache singleton
        if descriptor.scope == ServiceScope.SINGLETON:
            self._singletons[service_type] = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance."""
        # Use existing instance if available
        if descriptor.instance is not None:
            return descriptor.instance
        
        # Use factory if provided
        if descriptor.factory:
            return descriptor.factory()
        
        # Create from implementation class
        return self._instantiate(descriptor.implementation)
    
    def _instantiate(self, implementation: Type) -> Any:
        """Instantiate a class with dependency injection."""
        # Simple instantiation - could be enhanced with DI
        return implementation()

# Global registry instance
_registry = ServiceRegistry()

def get_service(service_type: Type) -> Any:
    """Get a service from the global registry."""
    return _registry.resolve(service_type)

def register_services():
    """Register all application services."""
    from application.services import (
        TaskApplicationService,
        ProjectManagementService,
        ValidationService,
        CacheService
    )
    from infrastructure.services import (
        EmailService,
        LoggingService
    )
    
    # Register singletons
    _registry.register_singleton(CacheService)
    _registry.register_singleton(LoggingService)
    
    # Register transient services
    _registry.register_transient(ValidationService)
    
    # Register with factory
    _registry.register_singleton(
        TaskApplicationService,
        factory=lambda: TaskApplicationService(
            get_service(TaskRepository),
            get_service(CacheService)
        )
    )
    
    # Register instance
    config = load_config()
    _registry.register_instance(Config, config)

# Usage
register_services()

# Resolve services anywhere in the application
cache_service = get_service(CacheService)
task_service = get_service(TaskApplicationService)
```

## Summary

These implementation examples demonstrate:

1. **Strategy Pattern**: Eliminates if-elif chains for validation
2. **Builder Pattern**: Simplifies complex object creation
3. **Command Pattern**: Enables undo/redo and operation tracking
4. **Service Registry**: Centralizes service management

Each pattern addresses specific problems found in the codebase and provides clear benefits for maintainability, testability, and extensibility.