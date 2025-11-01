"""
Integration Tests for Agent Instantiation Flow

This module tests the complete agent instantiation workflow from
facade → domain service → repositories → database, verifying that
all layers work together correctly with real database persistence.

Test Coverage:
- Complete get_or_create_instance workflow
- Auto-creation from templates
- Usage tracking persistence
- Template loading from database
- User agent instance customization persistence
"""

import pytest
from datetime import datetime, timezone, timedelta

from fastmcp.agent_management.application.facades.agent_management_facade import AgentManagementFacade
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository
)
from fastmcp.agent_management.domain.services import AgentInstantiationService
from fastmcp.agent_management.domain.value_objects import UserId
from fastmcp.agent_management.infrastructure.database.models import (
    AgentTemplateORM,
    UserAgentInstanceORM
)


class TestAgentInstantiationFlow:
    """Integration tests for complete agent instantiation flow"""

    def test_get_or_create_returns_existing_instance_with_database_persistence(
        self,
        db_session,
        sample_agent_template,
        sample_user_instance,
        sample_user_id
    ):
        """
        Test that get_or_create_instance returns existing instance from database.

        Verifies:
        - Repository correctly retrieves instance from database
        - Instance data matches what was stored
        - No duplicate instances created
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        # Override db_session in repositories
        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Record initial count
        initial_count = db_session.query(UserAgentInstanceORM).count()

        # Act
        result = facade.get_or_create_instance(
            user_id=sample_user_id,
            agent_slug="coding-agent"
        )

        # Assert
        assert result.id == sample_user_instance.id
        assert result.agent_name == "My Custom Coding Agent"
        assert result.is_customized is True
        assert "Glob" in result.configuration.tools  # Verify custom tool persisted
        assert "Go" in result.configuration.capabilities["languages"]  # Verify custom capability persisted

        # Verify no new instance was created
        final_count = db_session.query(UserAgentInstanceORM).count()
        assert final_count == initial_count

    def test_auto_creates_instance_when_not_found_with_database_persistence(
        self,
        db_session,
        sample_agent_template
    ):
        """
        Test that get_or_create_instance auto-creates from template when instance doesn't exist.

        Verifies:
        - New instance is created in database
        - Instance has default configuration from template
        - All fields are correctly persisted
        """
        # Arrange
        new_user_id = UserId.generate_new()
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        # Override db_session
        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Record initial count
        initial_count = db_session.query(UserAgentInstanceORM).count()

        # Act
        result = facade.get_or_create_instance(
            user_id=new_user_id,
            agent_slug="coding-agent"
        )

        # Assert - Instance created
        assert result is not None
        assert result.user_id == new_user_id
        assert result.template_id == sample_agent_template.id
        assert result.is_customized is False  # New instance starts as default
        assert result.agent_name == sample_agent_template.name  # Uses template name

        # Verify configuration matches template default
        assert result.configuration.system_prompt == sample_agent_template.default_configuration.system_prompt
        assert set(result.configuration.tools) == set(sample_agent_template.default_configuration.tools)

        # Verify instance was saved to database
        final_count = db_session.query(UserAgentInstanceORM).count()
        assert final_count == initial_count + 1

        # Verify database record
        db_instance = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.id == str(result.id.value)
        ).first()
        assert db_instance is not None
        assert db_instance.user_id == str(new_user_id.value)
        assert db_instance.template_id == str(sample_agent_template.id.value)
        assert db_instance.is_customized is False

    def test_usage_tracking_persists_to_database(
        self,
        db_session,
        sample_agent_template,
        sample_user_instance,
        sample_user_id
    ):
        """
        Test that usage tracking (last_used_at) is correctly persisted to database.

        Verifies:
        - track_usage() updates last_used_at
        - Updated timestamp is saved to database
        - Subsequent retrieval shows updated timestamp
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Record initial last_used_at (should be None)
        initial_last_used = sample_user_instance.last_used_at
        assert initial_last_used is None

        # Act - Call get_agent_for_call which tracks usage
        result = facade.get_agent_for_call(
            user_id=sample_user_id,
            agent_slug="coding-agent"
        )

        # Assert - Usage was tracked
        assert "last_used" in result["metadata"]
        assert result["metadata"]["last_used"] is not None

        # Verify database was updated
        db_instance = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.id == str(sample_user_instance.id.value)
        ).first()
        assert db_instance is not None
        assert db_instance.last_used_at is not None
        assert isinstance(db_instance.last_used_at, datetime)

        # Verify timestamp is recent (within last 5 seconds)
        time_diff = datetime.now(timezone.utc) - db_instance.last_used_at
        assert time_diff < timedelta(seconds=5)

    def test_get_agent_for_call_returns_correct_format_from_database(
        self,
        db_session,
        sample_agent_template,
        sample_user_instance,
        sample_user_id
    ):
        """
        Test that get_agent_for_call returns correctly formatted data from database.

        Verifies:
        - All required fields are present
        - Data types are correct (lists not tuples for JSON)
        - Customized configuration is correctly retrieved
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Act
        result = facade.get_agent_for_call(
            user_id=sample_user_id,
            agent_slug="coding-agent"
        )

        # Assert - Response structure
        assert isinstance(result, dict)
        assert "name" in result
        assert "slug" in result
        assert "system_prompt" in result
        assert "tools" in result
        assert "capabilities" in result
        assert "is_customized" in result
        assert "instance_id" in result
        assert "template_id" in result

        # Assert - Data types for JSON serialization
        assert isinstance(result["tools"], list)  # Not tuple
        assert isinstance(result["rules"], list)  # Not tuple
        assert isinstance(result["capabilities"], dict)

        # Assert - Customized data from database
        assert result["name"] == "My Custom Coding Agent"
        assert result["is_customized"] is True
        assert "Glob" in result["tools"]  # Custom tool
        assert "Go" in result["capabilities"]["languages"]  # Custom capability

    def test_multiple_users_can_have_different_instances_of_same_template(
        self,
        db_session,
        sample_agent_template
    ):
        """
        Test that multiple users can each have their own instance of the same template.

        Verifies:
        - User isolation (each user gets own instance)
        - No cross-user data leakage
        - Database correctly handles multiple instances of same template
        """
        # Arrange
        user1_id = UserId.generate_new()
        user2_id = UserId.generate_new()

        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Act - Create instances for both users
        instance1 = facade.get_or_create_instance(user1_id, "coding-agent")
        instance2 = facade.get_or_create_instance(user2_id, "coding-agent")

        # Assert - Different instances
        assert instance1.id != instance2.id
        assert instance1.user_id == user1_id
        assert instance2.user_id == user2_id
        assert instance1.template_id == sample_agent_template.id
        assert instance2.template_id == sample_agent_template.id

        # Verify in database
        user1_instances = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.user_id == str(user1_id.value)
        ).all()
        user2_instances = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.user_id == str(user2_id.value)
        ).all()

        assert len(user1_instances) == 1
        assert len(user2_instances) == 1
        assert user1_instances[0].id != user2_instances[0].id

    def test_template_not_found_raises_error(
        self,
        db_session
    ):
        """
        Test that requesting non-existent template raises appropriate error.

        Verifies:
        - Error handling for missing templates
        - Clear error message
        - No instance created in database
        """
        # Arrange
        user_id = UserId.generate_new()
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Agent template not found"):
            facade.get_or_create_instance(user_id, "nonexistent-agent")

        # Verify no instance was created
        instances = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.user_id == str(user_id.value)
        ).all()
        assert len(instances) == 0

    def test_concurrent_get_or_create_for_same_user_and_template(
        self,
        db_session,
        sample_agent_template
    ):
        """
        Test that concurrent get_or_create calls for same user+template don't create duplicates.

        Verifies:
        - Database transaction isolation
        - No duplicate instances created
        - Both calls get the same instance
        """
        # Arrange
        user_id = UserId.generate_new()
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template_repo._session = db_session
        instance_repo._session = db_session

        instantiation_service = AgentInstantiationService(template_repository=template_repo)
        facade = AgentManagementFacade(
            template_repository=template_repo,
            instance_repository=instance_repo,
            instantiation_service=instantiation_service
        )

        # Act - Simulate concurrent calls (sequential in test, but tests the logic)
        instance1 = facade.get_or_create_instance(user_id, "coding-agent")
        instance2 = facade.get_or_create_instance(user_id, "coding-agent")

        # Assert - Same instance returned
        assert instance1.id == instance2.id
        assert instance1.user_id == user_id
        assert instance2.user_id == user_id

        # Verify only one instance in database
        instances = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.user_id == str(user_id.value),
            UserAgentInstanceORM.template_id == str(sample_agent_template.id.value)
        ).all()
        assert len(instances) == 1


class TestRepositoryIntegration:
    """Integration tests for repository layer with database"""

    def test_template_repository_find_by_slug(
        self,
        db_session,
        sample_agent_template
    ):
        """Test that template repository correctly retrieves template by slug"""
        # Arrange
        repo = ORMAgentTemplateRepository()
        repo._session = db_session

        # Act
        result = repo.find_by_slug("coding-agent")

        # Assert
        assert result is not None
        assert result.slug == "coding-agent"
        assert result.name == "Coding Agent"
        assert result.id == sample_agent_template.id

    def test_instance_repository_find_by_user_and_template_slug(
        self,
        db_session,
        sample_user_instance,
        sample_user_id
    ):
        """Test that instance repository correctly retrieves instance by user and template"""
        # Arrange
        repo = ORMUserAgentInstanceRepository()
        repo._session = db_session

        # Act
        result = repo.find_by_user_and_template_slug(
            user_id=sample_user_id,
            template_slug="coding-agent"
        )

        # Assert
        assert result is not None
        assert result.id == sample_user_instance.id
        assert result.user_id == sample_user_id
        assert result.is_customized is True

    def test_instance_repository_save_creates_new_record(
        self,
        db_session,
        sample_agent_template
    ):
        """Test that instance repository correctly saves new instance to database"""
        # Arrange
        from fastmcp.agent_management.domain.entities import UserAgentInstance
        from fastmcp.agent_management.domain.value_objects import (
            UserAgentInstanceId,
            UserId,
            AgentConfiguration
        )

        user_id = UserId.generate_new()
        instance_id = UserAgentInstanceId.generate_new()

        configuration = AgentConfiguration(
            system_prompt="Test instance prompt",
            tools=["Read", "Write"],
            capabilities={"test": True}
        )

        instance = UserAgentInstance(
            id=instance_id,
            user_id=user_id,
            template_id=sample_agent_template.id,
            agent_name="Test Agent",
            is_customized=False,
            configuration=configuration,
            visibility="private",
            last_used_at=None,
            metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        repo = ORMUserAgentInstanceRepository()
        repo._session = db_session

        initial_count = db_session.query(UserAgentInstanceORM).count()

        # Act
        result = repo.save(instance)

        # Assert
        assert result is not None
        assert result.id == instance_id

        # Verify database record
        final_count = db_session.query(UserAgentInstanceORM).count()
        assert final_count == initial_count + 1

        db_record = db_session.query(UserAgentInstanceORM).filter(
            UserAgentInstanceORM.id == str(instance_id.value)
        ).first()
        assert db_record is not None
        assert db_record.agent_name == "Test Agent"
        assert db_record.is_customized is False


if __name__ == "__main__":
    print("\n=== Running Agent Instantiation Integration Tests ===\n")
    pytest.main([__file__, "-v", "--tb=short"])
