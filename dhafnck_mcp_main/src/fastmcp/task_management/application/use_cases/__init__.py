"""Use Cases Module - Lazy Loading to Prevent Circular Imports"""

# Define what should be available when importing from this module
__all__ = [
    'CreateTaskUseCase',
    'GetTaskUseCase',
    'UpdateTaskUseCase',
    'ListTasksUseCase',
    'SearchTasksUseCase',
    'DeleteTaskUseCase',
    'CompleteTaskUseCase',
    'NextTaskUseCase',
    'CallAgentUseCase',
    'AddSubtaskUseCase',
    'UpdateSubtaskUseCase',
    'RemoveSubtaskUseCase',
    'CompleteSubtaskUseCase',
    'GetSubtasksUseCase',
    'GetSubtaskUseCase',
    'AddDependencyUseCase',
    'RemoveDependencyUseCase',
    'GetDependenciesUseCase',
    'ClearDependenciesUseCase',
    'GetBlockingTasksUseCase',
    'CreateContextUseCase',
    'GetContextUseCase',
    'UpdateContextUseCase',
    'ListContextsUseCase',
    'AddContextInsightUseCase',
    'AddContextProgressUseCase'
]

# Mapping of use case names to their module paths
_USE_CASE_MODULES = {
    'CreateTaskUseCase': '.create_task',
    'GetTaskUseCase': '.get_task',
    'UpdateTaskUseCase': '.update_task',
    'ListTasksUseCase': '.list_tasks',
    'SearchTasksUseCase': '.search_tasks',
    'DeleteTaskUseCase': '.delete_task',
    'CompleteTaskUseCase': '.complete_task',
    'NextTaskUseCase': '.next_task',
    'CallAgentUseCase': '.call_agent',
    'AddSubtaskUseCase': '.add_subtask',
    'UpdateSubtaskUseCase': '.update_subtask',
    'RemoveSubtaskUseCase': '.remove_subtask',
    'CompleteSubtaskUseCase': '.complete_subtask',
    'GetSubtasksUseCase': '.get_subtasks',
    'GetSubtaskUseCase': '.get_subtask',
    'AddDependencyUseCase': '.add_dependency',
    'RemoveDependencyUseCase': '.remove_dependency',
    'GetDependenciesUseCase': '.get_dependencies',
    'ClearDependenciesUseCase': '.clear_dependencies',
    'GetBlockingTasksUseCase': '.get_blocking_tasks',
    'CreateContextUseCase': '.create_context',
    'GetContextUseCase': '.get_context',
    'UpdateContextUseCase': '.update_context',
    'ListContextsUseCase': '.list_contexts',
    'AddContextInsightUseCase': '.add_context_insight',
    'AddContextProgressUseCase': '.add_context_progress'
}


def __getattr__(name: str):
    """Lazy loading of use cases to prevent circular imports"""
    if name in _USE_CASE_MODULES:
        # Import the module dynamically
        from importlib import import_module
        module_path = _USE_CASE_MODULES[name]
        try:
            module = import_module(module_path, package=__name__)
            # Get the class from the module
            use_case_class = getattr(module, name)
            # Cache the class in the current module to avoid repeated imports
            globals()[name] = use_case_class
            return use_case_class
        except ImportError as e:
            raise ImportError(f"Cannot import {name} from {module_path}: {e}")
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 