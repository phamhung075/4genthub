"""
E2E Test Configuration for Agent Management

Reuses integration test fixtures and adds E2E-specific setup.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fastmcp.agent_management.application.facades.agent_management_facade import (
    AgentManagementFacade,
)
from fastmcp.agent_management.domain.entities.agent_template import AgentTemplate
from fastmcp.agent_management.domain.services.agent_customization_service import (
    AgentCustomizationService,
)
from fastmcp.agent_management.domain.services.agent_instantiation_service import (
    AgentInstantiationService,
)
from fastmcp.agent_management.domain.services.agent_sharing_service import (
    AgentSharingService,
)
from fastmcp.agent_management.domain.value_objects import AgentTemplateId

# Import facade dependencies
from fastmcp.agent_management.infrastructure.repositories.orm.agent_template_repository import (
    ORMAgentTemplateRepository,
)
from fastmcp.agent_management.infrastructure.repositories.orm.user_agent_instance_repository import (
    ORMUserAgentInstanceRepository,
)

# Import fixtures from integration tests


@pytest.fixture
def test_user_id():
    """Generate test user ID for E2E tests"""
    return str(uuid4())


@pytest.fixture
def test_template(db_session):
    """Create a test agent template for E2E testing"""
    template_repo = ORMAgentTemplateRepository(db_session)

    template = AgentTemplate(
        id=AgentTemplateId(uuid4()),
        slug="test-e2e-agent",
        name="Test E2E Agent",
        category="testing",
        version="1.0.0",
        default_configuration={
            "instructions": "Original instructions for testing",
            "rules": ["Original rule 1", "Original rule 2"],
            "capabilities": ["capability1", "capability2"],
            "output_format": "Original output format"
        },
        metadata={
            "description": "Agent for E2E testing",
            "author": "Test Suite"
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    template_repo.create(template)
    db_session.commit()

    yield template

    # Cleanup
    try:
        template_repo.delete_by_id(template.id)
        db_session.commit()
    except Exception:
        pass


@pytest.fixture
def agent_management_facade(db_session):
    """Create AgentManagementFacade for E2E tests"""
    template_repo = ORMAgentTemplateRepository(db_session)
    instance_repo = ORMUserAgentInstanceRepository(db_session)

    instantiation_service = AgentInstantiationService(template_repo, instance_repo)
    customization_service = AgentCustomizationService(instance_repo)
    sharing_service = AgentSharingService(instance_repo)

    facade = AgentManagementFacade(
        template_repository=template_repo,
        instance_repository=instance_repo,
        instantiation_service=instantiation_service,
        customization_service=customization_service,
        sharing_service=sharing_service
    )

    return facade
