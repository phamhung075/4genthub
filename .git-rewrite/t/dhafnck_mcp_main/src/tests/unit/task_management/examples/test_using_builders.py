"""Example tests demonstrating the use of test data builders."""

import pytest
from datetime import datetime, timezone

from tests.unit.task_management.fixtures.builders import (
    a_task, an_agent, a_project, a_subtask, a_work_session
)
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestBuilderExamples:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Examples of using test data builders for cleaner tests."""
    
    def test_simple_task_creation(self):
        """Example: Create a simple task with builder."""
        # Using builder - clean and readable
        task = a_task().with_title("Implement login").build()
        
        assert task.title == "Implement login"
        assert task.status.is_todo()
        assert task.priority.value == "medium"
    
    def test_complex_task_setup(self):
        """Example: Create a complex task with multiple attributes."""
        # Fluent interface makes complex setup readable
        task = (a_task()
                .with_title("Implement OAuth2")
                .with_description("Add OAuth2 authentication support")
                .high_priority()
                .in_progress()
                .with_assignees(["alice", "bob"])
                .with_labels(["security", "feature"])
                .build())
        
        assert task.title == "Implement OAuth2"
        assert task.priority.value == "high"
        assert task.status.is_in_progress()
        assert "alice" in task.assignees
        assert "security" in task.labels
    
    def test_completed_task_with_context(self):
        """Example: Create a completed task ready for testing."""
        # The completed() method sets up all required fields
        task = (a_task()
                .with_title("Fix bug #123")
                .completed()  # Sets status, context_id, progress
                .build())
        
        assert task.is_completed
        assert task.context_id is not None  # Required for completion
        assert task.overall_progress == 100
    
    def test_agent_with_capabilities(self):
        """Example: Create an agent with specific capabilities."""
        agent = (an_agent()
                .with_name("Python Expert")
                .with_capabilities(["backend", "api", "testing"])
                .with_languages(["python", "sql"])
                .with_frameworks(["django", "fastapi", "pytest"])
                .build())
        
        assert agent.name == "Python Expert"
        assert agent.can_handle_task({"languages": ["python"], "frameworks": ["pytest"]})
        assert "pytest" in agent.preferred_frameworks
    
    def test_project_with_agents_and_branches(self):
        """Example: Create a project with full setup."""
        # Create agents
        backend_agent = (an_agent()
                        .with_name("Backend Dev")
                        .with_capabilities(["backend"])
                        .build())
        
        frontend_agent = (an_agent()
                         .with_name("Frontend Dev")
                         .with_capabilities(["frontend"])
                         .build())
        
        # Create project with agents and branches
        project = (a_project()
                  .with_name("E-commerce Platform")
                  .with_agent(backend_agent)
                  .with_agent(frontend_agent)
                  .with_git_branch("feature/auth")
                  .with_git_branch("feature/cart")
                  .build())
        
        assert project.name == "E-commerce Platform"
        assert len(project.agents) == 2
        assert "feature/auth" in project.git_branchs
        assert "feature/cart" in project.git_branchs
    
    def test_subtask_hierarchy(self):
        """Example: Create subtasks for a parent task."""
        parent_task = a_task().with_title("Epic: User Authentication").build()
        
        subtask1 = (a_subtask()
                   .with_parent_task_id(parent_task.id.value)
                   .with_title("Implement login endpoint")
                   .build())
        
        subtask2 = (a_subtask()
                   .with_parent_task_id(parent_task.id.value)
                   .with_title("Add password reset")
                   .completed()
                   .build())
        
        assert subtask1.parent_task_id == parent_task.id.value
        assert subtask1.status.is_todo()
        assert subtask2.is_completed
    
    def test_work_session_scenario(self):
        """Example: Create a work session for testing."""
        agent = an_agent().with_name("Developer").build()
        task = a_task().with_title("Implement feature").build()
        
        session = (a_work_session()
                  .for_agent(agent.id)
                  .for_task(task.id.value)
                  .on_branch("feature/new-feature")
                  .build())
        
        assert session.agent_id == agent.id
        assert session.task_id == task.id.value
        assert session.git_branch_name == "feature/new-feature"
        assert session.status.value == "active"
    
    def test_multiple_builders_in_test(self):
        """Example: Using multiple builders together."""
        # Setup: Create a complete scenario
        project = a_project().with_name("AI Project").build()
        
        agent = (an_agent()
                .with_name("AI Developer")
                .assigned_to_project(project.id, "main")
                .build())
        
        task = (a_task()
               .with_title("Train ML model")
               .with_assignees([agent.name])
               .high_priority()
               .build())
        
        session = (a_work_session()
                  .for_agent(agent.id)
                  .for_task(task.id.value)
                  .build())
        
        # Test the scenario
        assert project.id in agent.assigned_projects
        assert agent.name in task.assignees
        assert task.priority.value == "high"
        assert session.agent_id == agent.id


class TestBuilderPatterns:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Demonstrate common patterns when using builders."""
    
    def test_builder_reset_pattern(self):
        """Example: Reusing a builder with reset."""
        builder = a_task()
        
        # Create first task
        task1 = builder.with_title("Task 1").build()
        
        # Reset and create second task
        task2 = builder.reset().with_title("Task 2").build()
        
        assert task1.title == "Task 1"
        assert task2.title == "Task 2"
        assert task1.id != task2.id  # Different IDs
    
    def test_builder_as_fixture(self):
        """Example: Using builder in a fixture."""
        @pytest.fixture
        def high_priority_task():
            return (a_task()
                   .high_priority()
                   .with_labels(["urgent"])
                   .build())
        
        # Would be used in tests as:
        # def test_something(high_priority_task):
        #     assert high_priority_task.priority.value == "high"
    
    def test_builder_factory_pattern(self):
        """Example: Creating specialized builders."""
        def a_bug_task():
            return (a_task()
                   .with_labels(["bug"])
                   .high_priority())
        
        def a_feature_task():
            return (a_task()
                   .with_labels(["feature"])
                   .with_estimated_effort("1 week"))
        
        bug = a_bug_task().with_title("Fix crash").build()
        feature = a_feature_task().with_title("Add export").build()
        
        assert "bug" in bug.labels
        assert bug.priority.value == "high"
        assert "feature" in feature.labels