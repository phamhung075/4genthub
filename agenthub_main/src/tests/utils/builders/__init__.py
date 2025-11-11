"""Test Data Builders - Builder Pattern for Test Data Creation

This package provides builder classes for creating test data with flexible
configuration using the builder pattern.

Usage:
    from tests.utils.builders import UserBuilder, ProjectBuilder, TaskBuilder

    # Chain methods to configure test data
    user = (UserBuilder()
        .with_email("admin@test.com")
        .with_admin_role()
        .build())

    project = (ProjectBuilder()
        .with_name("Test Project")
        .with_users([user])
        .build())

    task = (TaskBuilder()
        .with_title("Implement feature")
        .with_assignee("coding-agent")
        .with_priority("high")
        .build())
"""

from .user_builder import UserBuilder
from .project_builder import ProjectBuilder
from .task_builder import TaskBuilder
from .context_builder import ContextBuilder

__all__ = ["UserBuilder", "ProjectBuilder", "TaskBuilder", "ContextBuilder"]
