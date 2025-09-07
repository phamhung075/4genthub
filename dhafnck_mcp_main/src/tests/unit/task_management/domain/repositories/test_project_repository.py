"""Unit tests for ProjectRepository interface."""

import pytest
import pytest_asyncio
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.agent import Agent, AgentCapability, AgentStatus
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class MockProjectRepository(ProjectRepository):
    """Mock implementation of ProjectRepository for testing."""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        
    async def save(self, project: Project) -> None:
        """Save a project to the repository."""
        self.projects[project.id] = project
    
    async def find_by_id(self, project_id: str) -> Optional[Project]:
        """Find a project by its ID."""
        return self.projects.get(project_id)
    
    async def find_all(self) -> List[Project]:
        """Find all projects."""
        return list(self.projects.values())
    
    async def delete(self, project_id: str) -> bool:
        """Delete a project by its ID."""
        if project_id in self.projects:
            del self.projects[project_id]
            return True
        return False
    
    async def exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        return project_id in self.projects
    
    async def update(self, project: Project) -> None:
        """Update an existing project."""
        if project.id not in self.projects:
            raise ValueError(f"Project with ID {project.id} not found")
        self.projects[project.id] = project
    
    async def find_by_name(self, name: str) -> Optional[Project]:
        """Find a project by its name."""
        for project in self.projects.values():
            if project.name == name:
                return project
        return None
    
    async def count(self) -> int:
        """Count total number of projects."""
        return len(self.projects)
    
    async def find_projects_with_agent(self, agent_id: str) -> List[Project]:
        """Find projects that have a specific agent registered."""
        results = []
        for project in self.projects.values():
            if agent_id in project.registered_agents:
                results.append(project)
        return results
    
    async def find_projects_by_status(self, status: str) -> List[Project]:
        """Find projects by their status."""
        # For simplicity, we'll check if any task tree has the given status
        results = []
        for project in self.projects.values():
            for tree in project.git_branchs.values():
                if hasattr(tree, 'status') and tree.status.value == status:
                    results.append(project)
                    break
        return results
    
    async def get_project_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all projects."""
        total_projects = len(self.projects)
        total_trees = sum(len(p.git_branchs) for p in self.projects.values())
        total_agents = sum(len(p.registered_agents) for p in self.projects.values())
        total_sessions = sum(len(p.active_work_sessions) for p in self.projects.values())
        
        return {
            "total_projects": total_projects,
            "total_git_branchs": total_trees,
            "total_registered_agents": total_agents,
            "active_work_sessions": total_sessions,
            "projects_with_cross_tree_deps": sum(
                1 for p in self.projects.values() 
                if p.cross_tree_dependencies
            )
        }
    
    async def unassign_agent_from_tree(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Unassign an agent from a specific task tree within a project."""
        project = await self.find_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        if git_branch_id in project.agent_assignments:
            if project.agent_assignments[git_branch_id] == agent_id:
                del project.agent_assignments[git_branch_id]
                return {"status": "success", "message": "Agent unassigned"}
        
        return {"status": "not_found", "message": "Assignment not found"}


class TestProjectRepositoryInterface:
    
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

    """Test the ProjectRepository interface contract."""
    
    def test_repository_implements_all_abstract_methods(self):
        """Test that MockProjectRepository implements all abstract methods."""
        repo = MockProjectRepository()
        
        # Check all abstract methods are implemented
        assert hasattr(repo, 'save')
        assert hasattr(repo, 'find_by_id')
        assert hasattr(repo, 'find_all')
        assert hasattr(repo, 'delete')
        assert hasattr(repo, 'exists')
        assert hasattr(repo, 'update')
        assert hasattr(repo, 'find_by_name')
        assert hasattr(repo, 'count')
        assert hasattr(repo, 'find_projects_with_agent')
        assert hasattr(repo, 'find_projects_by_status')
        assert hasattr(repo, 'get_project_health_summary')
        assert hasattr(repo, 'unassign_agent_from_tree')
    
    def test_repository_is_abstract(self):
        """Test that ProjectRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ProjectRepository()


class TestProjectRepositorySaveOperation:
    
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

    """Test repository save operations."""
    
    @pytest.mark.asyncio
    async def test_save_new_project(self):
        """Test saving a new project."""
        repo = MockProjectRepository()
        project = Project.create(
            name="Test Project",
            description="Test Description"
        )
        
        await repo.save(project)
        assert await repo.count() == 1
        assert await repo.exists(project.id)
    
    @pytest.mark.asyncio
    async def test_save_multiple_projects(self):
        """Test saving multiple projects."""
        repo = MockProjectRepository()
        
        projects = [
            Project.create(name="Project 1", description="Description 1"),
            Project.create(name="Project 2", description="Description 2"),
            Project.create(name="Project 3", description="Description 3")
        ]
        
        for project in projects:
            await repo.save(project)
        
        assert await repo.count() == 3
        for project in projects:
            assert await repo.exists(project.id)


class TestProjectRepositoryFindOperations:
    
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

    """Test repository find operations."""
    
    @pytest_asyncio.fixture
    async def populated_repo(self):
        """Create a repository with test data."""
        repo = MockProjectRepository()
        
        # Create projects with different configurations
        project1 = Project.create(name="Web Application", description="Main web app")
        project2 = Project.create(name="Mobile App", description="Mobile application")
        project3 = Project.create(name="API Service", description="Backend API")
        
        # Add agents to projects
        agent1 = Agent(
            id="agent-1",
            name="Development Agent",
            capabilities={AgentCapability.BACKEND_DEVELOPMENT, AgentCapability.TESTING}
        )
        agent2 = Agent(
            id="agent-2",
            name="DevOps Agent",
            capabilities={AgentCapability.DEVOPS}
        )
        agent3 = Agent(
            id="agent-3",
            name="QA Agent",
            capabilities={AgentCapability.TESTING}
        )
        
        project1.register_agent(agent1)
        project1.register_agent(agent2)
        project2.register_agent(agent1)
        project2.register_agent(agent3)
        project3.register_agent(agent2)
        
        # Add task trees to projects
        tree1 = project1.create_git_branch("feature-auth", "Authentication Feature")
        tree2 = project1.create_git_branch("feature-ui", "UI Improvements")
        tree3 = project2.create_git_branch("mobile-login", "Mobile Login")
        tree4 = project3.create_git_branch("api-v2", "API Version 2")
        
        # Assign agents to trees
        project1.assign_agent_to_tree(agent1.id, tree1.id)
        project1.assign_agent_to_tree(agent2.id, tree2.id)
        project2.assign_agent_to_tree(agent1.id, tree3.id)
        project3.assign_agent_to_tree(agent2.id, tree4.id)
        
        # Save all projects
        await repo.save(project1)
        await repo.save(project2)
        await repo.save(project3)
        
        return repo, {
            "project1": project1,
            "project2": project2,
            "project3": project3,
            "agent1": agent1,
            "agent2": agent2,
            "agent3": agent3
        }
    
    @pytest.mark.asyncio
    async def test_find_by_id_existing(self, populated_repo):
        """Test finding an existing project by ID."""
        repo, data = populated_repo
        project = await repo.find_by_id(data["project1"].id)
        
        assert project is not None
        assert project.id == data["project1"].id
        assert project.name == "Web Application"
    
    @pytest.mark.asyncio
    async def test_find_by_id_non_existing(self, populated_repo):
        """Test finding a non-existing project by ID returns None."""
        repo, _ = populated_repo
        project = await repo.find_by_id("non-existent-id")
        
        assert project is None
    
    @pytest.mark.asyncio
    async def test_find_all(self, populated_repo):
        """Test finding all projects."""
        repo, _ = populated_repo
        projects = await repo.find_all()
        
        assert len(projects) == 3
        assert all(isinstance(project, Project) for project in projects)
        project_names = {p.name for p in projects}
        assert project_names == {"Web Application", "Mobile App", "API Service"}
    
    @pytest.mark.asyncio
    async def test_find_by_name_existing(self, populated_repo):
        """Test finding a project by name."""
        repo, data = populated_repo
        project = await repo.find_by_name("Mobile App")
        
        assert project is not None
        assert project.name == "Mobile App"
        assert project.id == data["project2"].id
    
    @pytest.mark.asyncio
    async def test_find_by_name_non_existing(self, populated_repo):
        """Test finding a non-existing project by name returns None."""
        repo, _ = populated_repo
        project = await repo.find_by_name("Non-existent Project")
        
        assert project is None
    
    @pytest.mark.asyncio
    async def test_find_projects_with_agent(self, populated_repo):
        """Test finding projects with a specific agent."""
        repo, data = populated_repo
        
        # Find projects with agent1 (should be project1 and project2)
        projects_with_agent1 = await repo.find_projects_with_agent(data["agent1"].id)
        assert len(projects_with_agent1) == 2
        project_names = {p.name for p in projects_with_agent1}
        assert project_names == {"Web Application", "Mobile App"}
        
        # Find projects with agent2 (should be project1 and project3)
        projects_with_agent2 = await repo.find_projects_with_agent(data["agent2"].id)
        assert len(projects_with_agent2) == 2
        project_names = {p.name for p in projects_with_agent2}
        assert project_names == {"Web Application", "API Service"}
        
        # Find projects with agent3 (should be only project2)
        projects_with_agent3 = await repo.find_projects_with_agent(data["agent3"].id)
        assert len(projects_with_agent3) == 1
        assert projects_with_agent3[0].name == "Mobile App"
    
    @pytest.mark.asyncio
    async def test_find_projects_by_status(self, populated_repo):
        """Test finding projects by status."""
        repo, data = populated_repo
        
        # Update some task tree statuses for testing
        for tree in data["project1"].git_branchs.values():
            tree.status = TaskStatus.in_progress()
        for tree in data["project2"].git_branchs.values():
            tree.status = TaskStatus.todo()
        
        # Re-save projects with updated statuses
        await repo.save(data["project1"])
        await repo.save(data["project2"])
        
        # Find projects with in_progress status
        in_progress_projects = await repo.find_projects_by_status("in_progress")
        assert len(in_progress_projects) == 1
        assert in_progress_projects[0].name == "Web Application"
        
        # Find projects with todo status (both project2 and project3 have todo status by default)
        todo_projects = await repo.find_projects_by_status("todo")
        assert len(todo_projects) == 2
        project_names = {p.name for p in todo_projects}
        assert "Mobile App" in project_names


class TestProjectRepositoryUpdateDeleteOperations:
    
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

    """Test repository update and delete operations."""
    
    @pytest.mark.asyncio
    async def test_update_existing_project(self):
        """Test updating an existing project."""
        repo = MockProjectRepository()
        
        # Create and save project
        project = Project.create(name="Original Name", description="Original Description")
        await repo.save(project)
        
        # Update project
        project.name = "Updated Name"
        project.description = "Updated Description"
        await repo.update(project)
        
        # Verify update
        updated_project = await repo.find_by_id(project.id)
        assert updated_project.name == "Updated Name"
        assert updated_project.description == "Updated Description"
    
    @pytest.mark.asyncio
    async def test_update_non_existing_project(self):
        """Test updating a non-existing project raises error."""
        repo = MockProjectRepository()
        project = Project.create(name="Test Project", description="Test")
        
        with pytest.raises(ValueError, match="not found"):
            await repo.update(project)
    
    @pytest.mark.asyncio
    async def test_delete_existing_project(self):
        """Test deleting an existing project."""
        repo = MockProjectRepository()
        
        # Create and save project
        project = Project.create(name="Project to Delete", description="Will be deleted")
        await repo.save(project)
        
        # Verify project exists
        assert await repo.exists(project.id)
        assert await repo.count() == 1
        
        # Delete project
        result = await repo.delete(project.id)
        assert result is True
        assert not await repo.exists(project.id)
        assert await repo.count() == 0
    
    @pytest.mark.asyncio
    async def test_delete_non_existing_project(self):
        """Test deleting a non-existing project returns False."""
        repo = MockProjectRepository()
        
        result = await repo.delete("non-existent-id")
        assert result is False


class TestProjectRepositoryUtilityOperations:
    
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

    """Test repository utility operations."""
    
    @pytest.mark.asyncio
    async def test_exists_for_existing_project(self):
        """Test exists returns True for existing project."""
        repo = MockProjectRepository()
        project = Project.create(name="Existing Project", description="This exists")
        await repo.save(project)
        
        assert await repo.exists(project.id) is True
    
    @pytest.mark.asyncio
    async def test_exists_for_non_existing_project(self):
        """Test exists returns False for non-existing project."""
        repo = MockProjectRepository()
        
        assert await repo.exists("non-existent-id") is False
    
    @pytest.mark.asyncio
    async def test_count_empty_repository(self):
        """Test count returns 0 for empty repository."""
        repo = MockProjectRepository()
        assert await repo.count() == 0
    
    @pytest.mark.asyncio
    async def test_count_with_projects(self):
        """Test count returns correct number of projects."""
        repo = MockProjectRepository()
        
        for i in range(5):
            project = Project.create(name=f"Project {i+1}", description=f"Description {i+1}")
            await repo.save(project)
        
        assert await repo.count() == 5
    
    @pytest.mark.asyncio
    async def test_get_project_health_summary(self):
        """Test getting project health summary."""
        repo = MockProjectRepository()
        
        # Create projects with various configurations
        project1 = Project.create(name="Project 1", description="Test")
        tree1 = project1.create_git_branch("tree1", "Tree 1")
        tree2 = project1.create_git_branch("tree2", "Tree 2")
        
        agent1 = Agent(id="agent-1", name="Agent 1", capabilities={AgentCapability.BACKEND_DEVELOPMENT})
        agent2 = Agent(id="agent-2", name="Agent 2", capabilities={AgentCapability.TESTING})
        project1.register_agent(agent1)
        project1.register_agent(agent2)
        
        # Add cross-tree dependency
        task1 = Task.create(
            id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440001"),
            title="Task 1",
            description="In tree 1"
        )
        task2 = Task.create(
            id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440002"),
            title="Task 2",
            description="In tree 2"
        )
        tree1.add_root_task(task1)
        tree2.add_root_task(task2)
        project1.add_cross_tree_dependency(task2.id.value, task1.id.value)
        
        project2 = Project.create(name="Project 2", description="Test")
        tree3 = project2.create_git_branch("tree3", "Tree 3")
        
        await repo.save(project1)
        await repo.save(project2)
        
        # Get health summary
        summary = await repo.get_project_health_summary()
        
        assert summary["total_projects"] == 2
        assert summary["total_git_branchs"] == 3
        assert summary["total_registered_agents"] == 2
        assert summary["active_work_sessions"] == 0
        assert summary["projects_with_cross_tree_deps"] == 1
    
    @pytest.mark.asyncio
    async def test_unassign_agent_from_tree(self):
        """Test unassigning an agent from a task tree."""
        repo = MockProjectRepository()
        
        # Create project with agent assignment
        project = Project.create(name="Test Project", description="Test")
        tree = project.create_git_branch("feature", "Feature Branch")
        agent = Agent(id="test-agent", name="Test Agent", capabilities={AgentCapability.BACKEND_DEVELOPMENT})
        project.register_agent(agent)
        project.assign_agent_to_tree(agent.id, tree.id)
        
        await repo.save(project)
        
        # Unassign agent
        result = await repo.unassign_agent_from_tree(project.id, agent.id, tree.id)
        assert result["status"] == "success"
        
        # Verify unassignment
        updated_project = await repo.find_by_id(project.id)
        assert tree.id not in updated_project.agent_assignments
    
    @pytest.mark.asyncio
    async def test_unassign_agent_from_non_existing_project(self):
        """Test unassigning agent from non-existing project raises error."""
        repo = MockProjectRepository()
        
        with pytest.raises(ValueError, match="Project .* not found"):
            await repo.unassign_agent_from_tree("non-existent", "agent-id", "tree-id")


class TestProjectRepositoryIntegration:
    
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

    """Test repository integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_project_lifecycle(self):
        """Test complete project lifecycle through repository."""
        repo = MockProjectRepository()
        
        # Create and save new project
        project = Project.create(
            name="Software Development Project",
            description="Complete software development lifecycle"
        )
        await repo.save(project)
        project_id = project.id
        
        # Verify project was saved
        assert await repo.exists(project_id)
        saved_project = await repo.find_by_id(project_id)
        assert saved_project.name == "Software Development Project"
        
        # Add agents and task trees
        dev_agent = Agent(
            id="dev-agent",
            name="Development Team",
            capabilities={AgentCapability.BACKEND_DEVELOPMENT, AgentCapability.TESTING}
        )
        ops_agent = Agent(
            id="ops-agent",
            name="Operations Team",
            capabilities={AgentCapability.DEVOPS}
        )
        
        saved_project.register_agent(dev_agent)
        saved_project.register_agent(ops_agent)
        
        feature_tree = saved_project.create_git_branch("feature-payment", "Payment Feature")
        infra_tree = saved_project.create_git_branch("infra-setup", "Infrastructure Setup")
        
        saved_project.assign_agent_to_tree(dev_agent.id, feature_tree.id)
        saved_project.assign_agent_to_tree(ops_agent.id, infra_tree.id)
        
        # Update project
        await repo.update(saved_project)
        
        # Verify updates
        updated_project = await repo.find_by_id(project_id)
        assert len(updated_project.registered_agents) == 2
        assert len(updated_project.git_branchs) == 2
        assert len(updated_project.agent_assignments) == 2
        
        # Search for project
        found_by_name = await repo.find_by_name("Software Development Project")
        assert found_by_name.id == project_id
        
        projects_with_dev_agent = await repo.find_projects_with_agent(dev_agent.id)
        assert len(projects_with_dev_agent) == 1
        assert projects_with_dev_agent[0].id == project_id
        
        # Get health summary
        summary = await repo.get_project_health_summary()
        assert summary["total_projects"] == 1
        assert summary["total_git_branchs"] == 2
        assert summary["total_registered_agents"] == 2
        
        # Unassign an agent
        unassign_result = await repo.unassign_agent_from_tree(project_id, dev_agent.id, feature_tree.id)
        assert unassign_result["status"] == "success"
        
        # Delete project
        assert await repo.delete(project_id) is True
        assert not await repo.exists(project_id)
        assert await repo.count() == 0
    
    @pytest.mark.asyncio
    async def test_repository_isolation(self):
        """Test that repository operations don't affect each other."""
        repo1 = MockProjectRepository()
        repo2 = MockProjectRepository()
        
        # Add project to repo1
        project = Project.create(name="Project in Repo 1", description="Test")
        await repo1.save(project)
        
        # Verify isolation
        assert await repo1.count() == 1
        assert await repo2.count() == 0
        assert await repo1.exists(project.id)
        assert not await repo2.exists(project.id)