"""
Repository Layer Tests for Orphaned Agent Import Functionality

Tests the ORM repository methods that filter orphaned imports from marketplace
and detect orphaned status:
1. find_public_instances() - marketplace filtering
2. is_orphaned() - orphaned detection

Test Strategy:
- Unit tests for repository layer (infrastructure)
- Test SQL queries and data access logic in isolation
- Verify business rules: orphaned imports excluded from marketplace
- Verify defensive coding: non-existent instances handled gracefully

Requirements Coverage:
- Marketplace filtering excludes orphaned imports
- Orphaned detection method works correctly
- Original agents always included in marketplace
- Active imports (original exists) included in marketplace
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastmcp.agent_management.domain.entities import AgentTemplate, UserAgentInstance
from fastmcp.agent_management.domain.value_objects import (
    AgentConfiguration,
    AgentTemplateId,
    UserAgentInstanceId,
    UserId,
)
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository,
)

# ============================================================================
# HELPER FUNCTIONS FOR TEST SETUP
# ============================================================================

def create_test_template(slug: str = "test-agent") -> AgentTemplate:
    """Create a test agent template"""
    template_id = AgentTemplateId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="Test agent for orphaned import tests",
        tools=["Read", "Write"],
        capabilities={"test": True},
        rules=["Test rule"],
        output_format=None
    )

    return AgentTemplate(
        id=template_id,
        slug=slug,
        name=f"Test Agent {slug}",
        description="Test agent for unit tests",
        category="test",
        version="1.0.0",
        default_configuration=configuration,
        metadata={"source": "test"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


def create_test_instance(
    user_id: UserId,
    template_id: AgentTemplateId,
    visibility: str = "public",
    share_token: str = None,
    original_creator_id: UserAgentInstanceId = None
) -> UserAgentInstance:
    """Create a test user agent instance"""
    instance_id = UserAgentInstanceId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="Test instance",
        tools=["Read"],
        capabilities={},
        rules=[],
        output_format=None
    )

    return UserAgentInstance(
        id=instance_id,
        user_id=user_id,
        template_id=template_id,
        agent_name="Test Instance",
        configuration=configuration,
        is_enabled=True,
        is_customized=False,
        visibility=visibility,
        share_token=share_token or (str(uuid4())[:64] if visibility == "public" else None),
        original_creator_id=original_creator_id,
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_used_at=None
    )


# ============================================================================
# TEST SUITE: find_public_instances() - MARKETPLACE FILTERING
# ============================================================================

class TestFindPublicInstances:
    """Test marketplace filtering excludes orphaned imports"""

    def test_find_public_instances_excludes_orphaned_imports(self):
        """
        GIVEN: An orphaned import (original creator deleted their agent)
        WHEN: Querying public instances for marketplace
        THEN: Orphaned import is NOT included in results
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        # Create template
        template = create_test_template("orphan-test-1")
        template_repo.save(template)

        # Create original agent
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id, visibility="public")
        instance_repo.save(original_instance)

        # User B imports the agent
        user_b = UserId.from_string(str(uuid4()))
        imported_instance = create_test_instance(
            user_b,
            template.id,
            visibility="public",
            original_creator_id=user_a  # User ID of original creator
        )
        instance_repo.save(imported_instance)

        # User A deletes their original agent (creates orphan)
        instance_repo.delete(original_instance.id)

        # Act - Query marketplace
        public_instances = instance_repo.find_public_instances(limit=100, offset=0)
        public_ids = [inst.id.value for inst in public_instances]

        # Assert - Orphaned import NOT in marketplace
        assert imported_instance.id.value not in public_ids, \
            "Orphaned import should be excluded from marketplace"

        # Cleanup
        if imported_instance.id.value not in public_ids:
            instance_repo.delete(imported_instance.id)
        template_repo.delete(template.id)

        print("✅ test_find_public_instances_excludes_orphaned_imports passed")

    def test_find_public_instances_includes_active_imports(self):
        """
        GIVEN: An active import (original creator's agent still exists)
        WHEN: Querying public instances for marketplace
        THEN: Active import IS included in results
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template = create_test_template("active-import-test")
        template_repo.save(template)

        # Create original agent
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id, visibility="public")
        instance_repo.save(original_instance)

        # User B imports (original still exists - active import)
        user_b = UserId.from_string(str(uuid4()))
        imported_instance = create_test_instance(
            user_b,
            template.id,
            visibility="public",
            original_creator_id=user_a  # User ID of the original creator
        )
        instance_repo.save(imported_instance)

        # Act - Query marketplace
        public_instances = instance_repo.find_public_instances(limit=100, offset=0)
        public_ids = [inst.id.value for inst in public_instances]

        # Assert - Both original and import in marketplace
        assert original_instance.id.value in public_ids, \
            "Original agent should be in marketplace"
        assert imported_instance.id.value in public_ids, \
            "Active import should be in marketplace"

        # Cleanup
        instance_repo.delete(imported_instance.id)
        instance_repo.delete(original_instance.id)
        template_repo.delete(template.id)

        print("✅ test_find_public_instances_includes_active_imports passed")

    def test_find_public_instances_includes_original_agents(self):
        """
        GIVEN: Original public agents (not imported)
        WHEN: Querying public instances for marketplace
        THEN: Original agents ARE included in results
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template = create_test_template("original-test")
        template_repo.save(template)

        # Create original agent (no original_creator_id)
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id, visibility="public")
        instance_repo.save(original_instance)

        # Act - Query marketplace
        public_instances = instance_repo.find_public_instances(limit=100, offset=0)
        public_ids = [inst.id.value for inst in public_instances]

        # Assert - Original agent in marketplace
        assert original_instance.id.value in public_ids, \
            "Original public agent should be in marketplace"

        # Cleanup
        instance_repo.delete(original_instance.id)
        template_repo.delete(template.id)

        print("✅ test_find_public_instances_includes_original_agents passed")


# ============================================================================
# TEST SUITE: is_orphaned() - ORPHANED DETECTION
# ============================================================================

class TestIsOrphaned:
    """Test orphaned detection method"""

    def test_is_orphaned_returns_true_for_orphaned_import(self):
        """
        GIVEN: An imported agent whose original creator deleted their agent
        WHEN: Checking if instance is orphaned
        THEN: Returns True
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template = create_test_template("orphan-detect-test")
        template_repo.save(template)

        # Create original and import
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id)
        instance_repo.save(original_instance)

        user_b = UserId.from_string(str(uuid4()))
        imported_instance = create_test_instance(
            user_b,
            template.id,
            original_creator_id=user_a  # User ID of original creator
        )
        instance_repo.save(imported_instance)

        # Delete original (creates orphan)
        instance_repo.delete(original_instance.id)

        # Act
        is_orphaned = instance_repo.is_orphaned(imported_instance.id)

        # Assert
        assert is_orphaned is True, \
            "Instance with deleted original_creator_id should be orphaned"

        # Cleanup
        instance_repo.delete(imported_instance.id)
        template_repo.delete(template.id)

        print("✅ test_is_orphaned_returns_true_for_orphaned_import passed")

    def test_is_orphaned_returns_false_for_original_agent(self):
        """
        GIVEN: An original agent (no original_creator_id)
        WHEN: Checking if instance is orphaned
        THEN: Returns False
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template = create_test_template("original-detect-test")
        template_repo.save(template)

        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id)
        instance_repo.save(original_instance)

        # Act
        is_orphaned = instance_repo.is_orphaned(original_instance.id)

        # Assert
        assert is_orphaned is False, \
            "Original agent (no original_creator_id) should not be orphaned"

        # Cleanup
        instance_repo.delete(original_instance.id)
        template_repo.delete(template.id)

        print("✅ test_is_orphaned_returns_false_for_original_agent passed")

    def test_is_orphaned_returns_false_for_active_import(self):
        """
        GIVEN: An imported agent whose original creator still exists
        WHEN: Checking if instance is orphaned
        THEN: Returns False
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()

        template = create_test_template("active-detect-test")
        template_repo.save(template)

        # Create original and import
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id)
        instance_repo.save(original_instance)

        user_b = UserId.from_string(str(uuid4()))
        imported_instance = create_test_instance(
            user_b,
            template.id,
            original_creator_id=user_a  # User ID of original creator
        )
        instance_repo.save(imported_instance)

        # Act (original still exists)
        is_orphaned = instance_repo.is_orphaned(imported_instance.id)

        # Assert
        assert is_orphaned is False, \
            "Import with existing original should not be orphaned"

        # Cleanup
        instance_repo.delete(imported_instance.id)
        instance_repo.delete(original_instance.id)
        template_repo.delete(template.id)

        print("✅ test_is_orphaned_returns_false_for_active_import passed")

    def test_is_orphaned_returns_false_for_nonexistent_instance(self):
        """
        GIVEN: A non-existent instance ID
        WHEN: Checking if instance is orphaned
        THEN: Returns False (defensive coding)
        """
        # Arrange
        instance_repo = ORMUserAgentInstanceRepository()
        fake_id = UserAgentInstanceId.generate_new()

        # Act
        is_orphaned = instance_repo.is_orphaned(fake_id)

        # Assert
        assert is_orphaned is False, \
            "Non-existent instance should return False (defensive)"

        print("✅ test_is_orphaned_returns_false_for_nonexistent_instance passed")
