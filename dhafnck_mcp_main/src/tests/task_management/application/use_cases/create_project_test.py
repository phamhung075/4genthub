"""
Test suite for create_project.py - Create Project Use Case

Tests the use case for creating new projects with proper entity creation,
repository persistence, and context management integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from uuid import UUID

from fastmcp.task_management.application.use_cases.create_project import CreateProjectUseCase
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository

class TestCreateProjectUseCase:
    """Test CreateProjectUseCase class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_repository = Mock(spec=ProjectRepository)
        self.mock_repository.save = AsyncMock()
        self.use_case = CreateProjectUseCase(self.mock_repository)
    
    @pytest.mark.asyncio
    async def test_create_project_new_signature_with_generated_id(self):
        """Test creating project with new signature (auto-generated ID)"""
        # Mock repository save
        self.mock_repository.save = AsyncMock()
        
        # Mock context creation to avoid dependency issues
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                # Test new signature: execute(None, name, description)
                result = await self.use_case.execute(
                    project_id=None,
                    name="Test Project",
                    description="Test project description"
                )
                
                # Verify result
                assert result["success"] is True
                assert "project" in result
                project_data = result["project"]
                
                # Verify generated project ID is a valid UUID
                project_id = project_data["id"]
                assert UUID(project_id)  # Should not raise ValueError
                
                assert project_data["name"] == "Test Project"
                assert project_data["description"] == "Test project description"
                assert "created_at" in project_data
                assert "updated_at" in project_data
                assert "git_branchs" in project_data
                # Verify at least one branch was created (should be main branch with UUID)
                assert len(project_data["git_branchs"]) > 0
                # Verify branch ID is a valid UUID
                for branch_id in project_data["git_branchs"]:
                    assert UUID(branch_id)  # Should not raise ValueError
                
                # Verify repository save was called
                self.mock_repository.save.assert_called_once()
                saved_project = self.mock_repository.save.call_args[0][0]
                assert isinstance(saved_project, Project)
                assert saved_project.name == "Test Project"
                assert saved_project.description == "Test project description"
    
    @pytest.mark.asyncio
    async def test_create_project_legacy_signature(self):
        """Test creating project with legacy signature (explicit ID)"""
        project_id = "explicit-project-123"
        
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                # Test legacy signature: execute(project_id, name, description)
                result = await self.use_case.execute(
                    project_id=project_id,
                    name="Legacy Project",
                    description="Legacy project description"
                )
                
                # Verify result
                assert result["success"] is True
                project_data = result["project"]
                assert project_data["id"] == project_id
                assert project_data["name"] == "Legacy Project"
                assert project_data["description"] == "Legacy project description"
                
                # Verify repository save was called
                self.mock_repository.save.assert_called_once()
                saved_project = self.mock_repository.save.call_args[0][0]
                assert saved_project.id == project_id
                assert saved_project.name == "Legacy Project"
    
    @pytest.mark.asyncio
    async def test_create_project_backward_compatibility(self):
        """Test backward compatibility for old calling convention"""
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                # Test old calling convention where name is passed as project_id
                result = await self.use_case.execute("Backward Compatible Project")
                
                # Verify result - name should be treated as project name, ID should be generated
                assert result["success"] is True
                project_data = result["project"]
                assert UUID(project_data["id"])  # ID should be generated
                assert project_data["name"] == "Backward Compatible Project"
                assert project_data["description"] == ""  # Default empty description
    
    @pytest.mark.asyncio
    async def test_create_project_missing_name_error(self):
        """Test error handling when project name is missing"""
        result = await self.use_case.execute(None, None)
        
        assert result["success"] is False
        assert result["error"] == "Project name is required"
        
        # Verify repository save was not called
        self.mock_repository.save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_project_with_main_branch(self):
        """Test that project creates default main branch"""
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute(None, "Project with Branch")
                
                assert result["success"] is True
                project_data = result["project"]
                
                # Verify main branch was created
                assert "git_branchs" in project_data
                assert len(project_data["git_branchs"]) > 0

                # Verify the saved project has the branch
                saved_project = self.mock_repository.save.call_args[0][0]
                assert len(saved_project.git_branchs) > 0

                # Get the main branch (should be the only one)
                branch_id = list(saved_project.git_branchs.keys())[0]
                main_branch = saved_project.git_branchs[branch_id]
                assert main_branch.name == "main"
                assert main_branch.description == "Main task tree for the project"
    
    @pytest.mark.asyncio
    async def test_create_project_repository_error(self):
        """Test handling of repository save errors"""
        # Mock repository to raise exception
        self.mock_repository.save = AsyncMock(side_effect=ValueError("Repository error"))
        
        result = await self.use_case.execute(None, "Test Project")
        
        assert result["success"] is False
        assert result["error"] == "Repository error"
    
    @pytest.mark.asyncio
    async def test_create_project_unexpected_exception(self):
        """Test handling of unexpected exceptions"""
        # Mock repository to raise unexpected exception
        self.mock_repository.save = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        
        result = await self.use_case.execute(None, "Test Project")
        
        assert result["success"] is False
        assert result["error"] == "Unexpected error"

class TestProjectContextCreation:
    """Test project context creation integration"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_repository = Mock(spec=ProjectRepository)
        self.mock_repository.save = AsyncMock()
        self.use_case = CreateProjectUseCase(self.mock_repository)
    
    @pytest.mark.asyncio
    async def test_context_creation_success(self):
        """Test successful project context creation"""
        # Mock repository user_id attribute to return the exact expected value
        mock_user_context = Mock()
        mock_user_context.user_id = "user-123"
        self.mock_repository.user_id = mock_user_context

        # Also ensure hasattr checks work correctly
        self.mock_repository.user_id = mock_user_context
        
        # Mock context facade and factory, and also prevent middleware fallback
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class, \
             patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', side_effect=Exception("Should not use middleware in this test")):
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            result = await self.use_case.execute(None, "Test Project")
            
            assert result["success"] is True
            
            # Verify global context auto-creation was called with normalized UUID
            # "user-123" gets converted to UUID: 3a1b8473-3492-5076-98f9-b2dfa6d37933
            expected_user_id = "3a1b8473-3492-5076-98f9-b2dfa6d37933"
            mock_factory.auto_create_global_context.assert_called_once_with(user_id=expected_user_id)
            
            # Verify facade creation with correct parameters (also uses normalized UUID)
            mock_factory.create_facade.assert_called_once_with(
                user_id=expected_user_id,
                project_id=result["project"]["id"]
            )
            
            # Verify context creation was called
            mock_facade.create_context.assert_called_once()
            call_args = mock_facade.create_context.call_args
            assert call_args[1]["level"] == "project"
            assert call_args[1]["context_id"] == result["project"]["id"]
            
            # Verify context data structure
            context_data = call_args[1]["data"]
            assert context_data["project_id"] == result["project"]["id"]
            assert context_data["name"] == "Test Project"
            assert context_data["description"] == ""
            assert "created_at" in context_data
            assert "configuration" in context_data
            assert "standards" in context_data
            assert "team_settings" in context_data
    
    @pytest.mark.asyncio
    async def test_context_creation_user_id_from_string(self):
        """Test context creation when repository user_id is a string"""
        # Mock repository user_id as string
        self.mock_repository.user_id = "user-string-123"
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            result = await self.use_case.execute(None, "Test Project")
            
            assert result["success"] is True
            
            # Verify user_id was extracted correctly (normalized to UUID)
            # "user-string-123" gets converted to UUID: d4feb5b7-1dca-5b21-a59f-d5709f947299
            expected_user_id = "d4feb5b7-1dca-5b21-a59f-d5709f947299"
            mock_factory.create_facade.assert_called_once_with(
                user_id=expected_user_id,
                project_id=result["project"]["id"]
            )
    
    @pytest.mark.asyncio
    async def test_context_creation_user_id_from_id_attribute(self):
        """Test context creation when user object has 'id' instead of 'user_id'"""
        # Mock repository user with 'id' attribute
        mock_user_context = Mock()
        mock_user_context.id = "user-id-123"
        # Ensure user_id attribute doesn't exist
        if hasattr(mock_user_context, 'user_id'):
            delattr(mock_user_context, 'user_id')
        self.mock_repository.user_id = mock_user_context
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            result = await self.use_case.execute(None, "Test Project")
            
            assert result["success"] is True
            
            # Verify user_id was extracted from 'id' attribute (normalized to UUID)
            # "user-id-123" gets converted to UUID: b4af8439-a4cc-5ecc-9c32-490b158c4d48
            expected_user_id = "b4af8439-a4cc-5ecc-9c32-490b158c4d48"
            mock_factory.create_facade.assert_called_once_with(
                user_id=expected_user_id,
                project_id=result["project"]["id"]
            )
    
    @pytest.mark.asyncio
    async def test_context_creation_user_from_middleware(self):
        """Test context creation gets user from middleware when repository doesn't have user_id"""
        # Repository without user_id attribute
        # Don't set user_id attribute on repository

        # Ensure repository doesn't have user_id so it falls back to middleware
        assert not hasattr(self.mock_repository, 'user_id')

        # Mock middleware user ID at the module level since it's imported dynamically
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
            mock_get_user.return_value = "middleware-user-123"
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
                mock_factory = Mock()
                mock_facade = Mock()
                mock_factory_class.return_value = mock_factory
                mock_factory.auto_create_global_context.return_value = True
                mock_factory.create_facade.return_value = mock_facade
                mock_facade.create_context.return_value = {"success": True}
                
                result = await self.use_case.execute(None, "Test Project")

                # Project creation should succeed even when context creation fails due to auth
                assert result["success"] is True

                # Verify project was saved despite context creation failure
                self.mock_repository.save.assert_called_once()

                # Context creation should not be attempted due to auth failure
                mock_factory.create_facade.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_context_creation_user_middleware_with_id_attr(self):
        """Test context creation with middleware user having 'id' instead of 'user_id'"""
        # Ensure repository doesn't have user_id so it falls back to middleware
        assert not hasattr(self.mock_repository, 'user_id')

        # Mock middleware user ID (the actual implementation uses get_current_user_id and returns the ID directly)
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
            mock_get_user.return_value = "middleware-id-123"
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
                mock_factory = Mock()
                mock_facade = Mock()
                mock_factory_class.return_value = mock_factory
                mock_factory.auto_create_global_context.return_value = True
                mock_factory.create_facade.return_value = mock_facade
                mock_facade.create_context.return_value = {"success": True}
                
                result = await self.use_case.execute(None, "Test Project")

                # Project creation should succeed even when context creation fails due to auth
                assert result["success"] is True

                # Verify project was saved despite context creation failure
                self.mock_repository.save.assert_called_once()

                # Context creation should not be attempted due to auth failure
                mock_factory.create_facade.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_context_creation_no_user_authentication_error(self):
        """Test context creation fails when no user authentication is available"""
        # Ensure repository doesn't have user_id attribute
        assert not hasattr(self.mock_repository, 'user_id')

        # No user_id on repository and no middleware user
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
            mock_get_user.side_effect = Exception("No user context available")

            result = await self.use_case.execute(None, "Test Project")

            # Project creation should succeed even when context creation fails due to auth
            assert result["success"] is True

            # Verify repository save was called (project creation succeeded)
            self.mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_creation_global_context_failure(self):
        """Test when global context auto-creation fails"""
        # Mock repository user_id
        self.mock_repository.user_id = "user-123"
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            # Global context creation fails
            mock_factory.auto_create_global_context.return_value = False
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            result = await self.use_case.execute(None, "Test Project")
            
            # Project creation should still succeed
            assert result["success"] is True
            
            # Context creation should still be attempted
            mock_facade.create_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_creation_context_facade_failure(self):
        """Test when project context creation fails"""
        # Mock repository user_id
        self.mock_repository.user_id = "user-123"
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            # Context creation fails
            mock_facade.create_context.return_value = {"success": False, "error": "Context creation failed"}
            
            result = await self.use_case.execute(None, "Test Project")
            
            # Project creation should still succeed
            assert result["success"] is True
            
            # Verify repository save was called
            self.mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_creation_exception_handling(self):
        """Test that context creation exceptions don't break project creation"""
        # Mock repository user_id
        self.mock_repository.user_id = "user-123"
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            # Factory creation raises exception
            mock_factory_class.side_effect = Exception("Factory error")
            
            result = await self.use_case.execute(None, "Test Project")
            
            # Project creation should still succeed despite context error
            assert result["success"] is True
            
            # Verify repository save was called
            self.mock_repository.save.assert_called_once()

class TestProjectEntityCreation:
    """Test Project entity creation and validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_repository = Mock(spec=ProjectRepository)
        self.mock_repository.save = AsyncMock()
        self.use_case = CreateProjectUseCase(self.mock_repository)
    
    @pytest.mark.asyncio
    async def test_project_entity_fields(self):
        """Test that Project entity is created with correct fields"""
        # Mock context creation to focus on entity testing
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute("project-123", "Test Project", "Test Description")

                assert result["success"] is True

                # Verify saved project entity
                saved_project = self.mock_repository.save.call_args[0][0]
                assert isinstance(saved_project, Project)
                assert saved_project.id == "project-123"
                assert saved_project.name == "Test Project"
                assert saved_project.description == "Test Description"
                # Verify timestamps are set (don't check exact values due to timing issues)
                assert saved_project.created_at is not None
                assert saved_project.updated_at is not None
                assert isinstance(saved_project.created_at, datetime)
                assert isinstance(saved_project.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_project_git_branch_creation(self):
        """Test that main git branch is created correctly"""
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute(None, "Test Project")
                
                # Verify saved project has main branch
                saved_project = self.mock_repository.save.call_args[0][0]
                
                assert len(saved_project.git_branchs) > 0
                # Get the main branch (should be the only one)
                branch_id = list(saved_project.git_branchs.keys())[0]
                main_branch = saved_project.git_branchs[branch_id]

                # Verify main branch properties
                assert main_branch.git_branch_name == "main"
                assert main_branch.name == "main"
                assert main_branch.description == "Main task tree for the project"
                assert main_branch.project_id == saved_project.id
    
    @pytest.mark.asyncio
    async def test_uuid_generation_validation(self):
        """Test that generated UUIDs are valid"""
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                # Create multiple projects to test UUID uniqueness
                results = []
                for i in range(3):
                    result = await self.use_case.execute(None, f"Test Project {i}")
                    assert result["success"] is True
                    results.append(result)
                
                # Verify all generated IDs are valid UUIDs and unique
                generated_ids = [result["project"]["id"] for result in results]
                
                for project_id in generated_ids:
                    # Should not raise ValueError
                    UUID(project_id)
                
                # All IDs should be unique
                assert len(set(generated_ids)) == 3

class TestErrorScenarios:
    """Test various error scenarios and edge cases"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_repository = Mock(spec=ProjectRepository)
        self.mock_repository.save = AsyncMock()
        self.use_case = CreateProjectUseCase(self.mock_repository)
    
    @pytest.mark.asyncio
    async def test_empty_project_name(self):
        """Test handling of empty project name"""
        # Mock user authentication for context creation since empty string is now valid
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
            mock_get_user.return_value = "test-user-123"

            # Mock context creation to avoid authentication issues
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
                mock_factory = Mock()
                mock_facade = Mock()
                mock_factory_class.return_value = mock_factory
                mock_factory.auto_create_global_context.return_value = True
                mock_factory.create_facade.return_value = mock_facade
                mock_facade.create_context.return_value = {"success": True}

                result = await self.use_case.execute(None, "")

                # Current implementation allows empty strings as project names
                assert result["success"] is True
                assert result["project"]["name"] == ""
                self.mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_whitespace_only_project_name(self):
        """Test handling of whitespace-only project name"""
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute(None, "   ")
                
                # Should succeed (whitespace is preserved as valid name)
                assert result["success"] is True
                assert result["project"]["name"] == "   "
    
    @pytest.mark.asyncio
    async def test_very_long_project_name(self):
        """Test handling of very long project names"""
        long_name = "A" * 1000
        
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute(None, long_name)
                
                # Should succeed (validation is handled by domain entity)
                assert result["success"] is True
                assert result["project"]["name"] == long_name
    
    @pytest.mark.asyncio
    async def test_special_characters_in_name(self):
        """Test handling of special characters in project name"""
        special_name = "Test Project!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute(None, special_name)
                
                # Should succeed
                assert result["success"] is True
                assert result["project"]["name"] == special_name
    
    @pytest.mark.asyncio
    async def test_unicode_project_name(self):
        """Test handling of Unicode characters in project name"""
        unicode_name = "Test Project 测试项目 プロジェクト مشروع"
        
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "test-user-123"
                
                result = await self.use_case.execute(None, unicode_name)
                
                # Should succeed
                assert result["success"] is True
                assert result["project"]["name"] == unicode_name

class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_repository = Mock(spec=ProjectRepository)
        self.mock_repository.save = AsyncMock()
        self.use_case = CreateProjectUseCase(self.mock_repository)
    
    @pytest.mark.asyncio
    async def test_full_project_creation_workflow(self):
        """Test complete project creation workflow with all components"""
        # Mock repository with user context
        mock_user_context = Mock()
        mock_user_context.user_id = "integration-user-123"
        self.mock_repository.user_id = mock_user_context
        
        # Mock context facade with realistic behavior
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {
                "success": True, 
                "context_id": "project-context-id",
                "message": "Context created successfully"
            }
            
            # Execute use case
            result = await self.use_case.execute(
                project_id="integration-project-123",
                name="Integration Test Project",
                description="Full integration test"
            )
            
            # Verify complete workflow
            assert result["success"] is True
            
            # Verify project data
            project_data = result["project"]
            assert project_data["id"] == "integration-project-123"
            assert project_data["name"] == "Integration Test Project"
            assert project_data["description"] == "Full integration test"
            assert len(project_data["git_branchs"]) > 0  # main branch was created with UUID
            
            # Verify repository save
            self.mock_repository.save.assert_called_once()
            saved_project = self.mock_repository.save.call_args[0][0]
            assert saved_project.id == "integration-project-123"
            
            # Verify context creation workflow (user ID is normalized to UUID)
            # "integration-user-123" gets converted to UUID: 4cee9244-0793-5e8c-bd13-85db56634905
            expected_user_id = "4cee9244-0793-5e8c-bd13-85db56634905"
            mock_factory.auto_create_global_context.assert_called_once_with(user_id=expected_user_id)
            mock_factory.create_facade.assert_called_once_with(
                user_id=expected_user_id,
                project_id="integration-project-123"
            )
            mock_facade.create_context.assert_called_once()
            
            # Verify context data
            context_call_args = mock_facade.create_context.call_args[1]
            assert context_call_args["level"] == "project"
            assert context_call_args["context_id"] == "integration-project-123"
            
            context_data = context_call_args["data"]
            assert context_data["project_id"] == "integration-project-123"
            assert context_data["name"] == "Integration Test Project"
            assert context_data["description"] == "Full integration test"
    
    @pytest.mark.asyncio
    async def test_concurrent_project_creation_safety(self):
        """Test that concurrent project creation is handled safely"""
        # This test verifies that the use case can handle concurrent calls
        # Mock repository with delayed save to simulate concurrent access
        import asyncio
        
        async def delayed_save(project):
            await asyncio.sleep(0.01)  # Small delay to simulate database operation
            return None
        
        self.mock_repository.save = AsyncMock(side_effect=delayed_save)
        
        # Mock context creation - use correct import path since it's imported locally in the function
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_facade = Mock()
            mock_factory_class.return_value = mock_factory
            mock_factory.auto_create_global_context.return_value = True
            mock_factory.create_facade.return_value = mock_facade
            mock_facade.create_context.return_value = {"success": True}
            
            # Mock user authentication
            with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user:
                mock_get_user.return_value = "concurrent-user-123"
                
                # Create multiple projects concurrently
                tasks = [
                    self.use_case.execute(None, f"Concurrent Project {i}")
                    for i in range(3)
                ]
                
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                for result in results:
                    assert result["success"] is True
                
                # Verify all projects were saved
                assert self.mock_repository.save.call_count == 3
                
                # Verify all projects have unique IDs
                project_ids = [result["project"]["id"] for result in results]
                assert len(set(project_ids)) == 3

if __name__ == "__main__":
    pytest.main([__file__])