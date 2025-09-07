"""Application Facades Module

This module contains facade classes that orchestrate multiple use cases
and provide simplified interfaces for the presentation layer.

Facades help reduce complexity by providing a unified interface to
a set of interfaces in the application layer.
"""
from .agent_application_facade import AgentApplicationFacade
from .unified_context_facade import UnifiedContextFacade as ContextApplicationFacade
from .task_application_facade import TaskApplicationFacade
from .subtask_application_facade import SubtaskApplicationFacade
from .dependency_application_facade import DependencyApplicationFacade
from .rule_application_facade import RuleApplicationFacade
from .file_resource_application_facade import FileResourceApplicationFacade
from .git_branch_application_facade import GitBranchApplicationFacade
from .project_application_facade import ProjectApplicationFacade
from .rule_orchestration_facade import RuleOrchestrationFacade
__all__ = [
    'AgentApplicationFacade',
    'ContextApplicationFacade',
    'TaskApplicationFacade',
    'SubtaskApplicationFacade',
    'DependencyApplicationFacade',
    'RuleApplicationFacade',
    'FileResourceApplicationFacade',
    'GitBranchApplicationFacade',
    'ProjectApplicationFacade',
    'RuleOrchestrationFacade',
    ] 