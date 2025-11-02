"""Unit test for AgentManagementFacade visibility update fix"""

import pytest
from unittest.mock import Mock
from uuid import uuid4

from fastmcp.agent_management.application.facades.agent_management_facade import AgentManagementFacade
from fastmcp.agent_management.domain.entities.user_agent_instance import UserAgentInstance
from fastmcp.agent_management.domain.value_objects.user_id import UserId
from fastmcp.agent_management.domain.value_objects.user_agent_instance_id import UserAgentInstanceId
from fastmcp.agent_management.domain.value_objects.agent_template_id import AgentTemplateId
from fastmcp.agent_management.domain.value_objects.agent_configuration import AgentConfiguration


class TestFacadeVisibilityUpdate:
    """Test that update_instance properly handles visibility changes with share_token generation"""

    def test_update_visibility_to_public_generates_share_token(self):
        """Test that setting visibility='public' automatically generates a share_token"""

        # Setup mocks
        mock_instance_repo = Mock()
        mock_template_repo = Mock()
        mock_instantiation_service = Mock()
        mock_sharing_service = Mock()

        # Create test instance (private, no share_token)
        instance_id = UserAgentInstanceId.generate_new()
        user_id = UserId(str(uuid4()))
        template_id = AgentTemplateId(str(uuid4()))

        test_instance = UserAgentInstance(
            id=instance_id,
            user_id=user_id,
            template_id=template_id,
            agent_name="Test Agent",
            is_customized=False,
            is_enabled=True,
            configuration=AgentConfiguration.from_dict({
                "system_prompt": "Test prompt",
                "tools": [],
                "capabilities": {},
                "rules": [],
                "output_format": {}
            }),
            visibility="private",
            share_token=None
        )

        # Mock repository to return our test instance
        mock_instance_repo.find_by_id.return_value = test_instance

        # Mock sharing service to return a token
        mock_sharing_service.generate_share_token.return_value = "a" * 64  # 64-char token

        # After sharing service is called, simulate the instance being updated
        updated_instance = UserAgentInstance(
            id=instance_id,
            user_id=user_id,
            template_id=template_id,
            agent_name="Test Agent",
            is_customized=False,
            is_enabled=True,
            configuration=test_instance.configuration,
            visibility="public",
            share_token="a" * 64
        )

        # Mock save to return updated instance
        mock_instance_repo.save.return_value = updated_instance

        # Create facade with mocks
        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
            sharing_service=mock_sharing_service
        )

        # Execute: Update visibility to 'public'
        result = facade.update_instance(
            user_id=user_id,
            instance_id=str(instance_id),
            visibility="public"
        )

        # Verify: Sharing service was called to generate token
        mock_sharing_service.generate_share_token.assert_called_once_with(
            instance_id, user_id
        )

        # Verify: Instance was re-fetched after sharing service call
        assert mock_instance_repo.find_by_id.call_count >= 2

        # Verify: Final save was called
        mock_instance_repo.save.assert_called_once()

        # Verify: Result has public visibility and share_token
        assert result.visibility == "public"
        assert result.share_token == "a" * 64


    def test_update_visibility_to_private_revokes_share_token(self):
        """Test that setting visibility='private' revokes the share_token"""

        # Setup mocks
        mock_instance_repo = Mock()
        mock_template_repo = Mock()
        mock_instantiation_service = Mock()
        mock_sharing_service = Mock()

        # Create test instance (public, with share_token)
        instance_id = UserAgentInstanceId.generate_new()
        user_id = UserId(str(uuid4()))
        template_id = AgentTemplateId(str(uuid4()))

        test_instance = UserAgentInstance(
            id=instance_id,
            user_id=user_id,
            template_id=template_id,
            agent_name="Test Agent",
            is_customized=False,
            is_enabled=True,
            configuration=AgentConfiguration.from_dict({
                "system_prompt": "Test prompt",
                "tools": [],
                "capabilities": {},
                "rules": [],
                "output_format": {}
            }),
            visibility="public",
            share_token="a" * 64
        )

        # Mock repository to return our test instance
        mock_instance_repo.find_by_id.return_value = test_instance

        # Mock sharing service to return success
        mock_sharing_service.revoke_share_token.return_value = True

        # After sharing service is called, simulate the instance being updated
        updated_instance = UserAgentInstance(
            id=instance_id,
            user_id=user_id,
            template_id=template_id,
            agent_name="Test Agent",
            is_customized=False,
            is_enabled=True,
            configuration=test_instance.configuration,
            visibility="private",
            share_token=None
        )

        # Mock save to return updated instance
        mock_instance_repo.save.return_value = updated_instance

        # Create facade with mocks
        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
            sharing_service=mock_sharing_service
        )

        # Execute: Update visibility to 'private'
        result = facade.update_instance(
            user_id=user_id,
            instance_id=str(instance_id),
            visibility="private"
        )

        # Verify: Sharing service was called to revoke token
        mock_sharing_service.revoke_share_token.assert_called_once_with(
            instance_id, user_id
        )

        # Verify: Instance was re-fetched after sharing service call
        assert mock_instance_repo.find_by_id.call_count >= 2

        # Verify: Final save was called
        mock_instance_repo.save.assert_called_once()

        # Verify: Result has private visibility and no share_token
        assert result.visibility == "private"
        assert result.share_token is None
