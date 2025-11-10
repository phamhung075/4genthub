"""
Regression test for Agent Repository timestamp initialization bug.

This test prevents regression of the critical bug where Agent entity timestamps
(created_at, updated_at) were not included in _entity_to_model_dict, causing
database NOT NULL constraint violations during agent registration.

Bug Context:
- Agent entity properly initialized timestamps via BaseTimestampEntity
- ORMAgentRepository._entity_to_model_dict() didn't include timestamps in dict
- Database INSERT failed with: null value in column "created_at" violates not-null constraint

Fix:
- Added created_at and updated_at to _entity_to_model_dict return dictionary
- Lines 223-224 in agent_repository.py

Test Date: 2025-10-31
Bug Report: ai_docs/testing-qa/mcp-tools-comprehensive-test-report-2025-10-31.md
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.domain.entities.agent import Agent as AgentEntity
from fastmcp.task_management.domain.value_objects.agent_id import AgentId
from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import (
    ORMAgentRepository,
)


class TestAgentRepositoryTimestampRegression:
    """Regression tests for agent timestamp initialization bug fix"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = Mock()
        session.query = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        return session

    @pytest.fixture
    def agent_repository(self, mock_session):
        """Create agent repository with mocked session"""
        repo = ORMAgentRepository(session=mock_session, user_id="test-user-id")
        return repo

    @pytest.fixture
    def sample_agent_entity(self):
        """Create a sample agent entity with proper timestamp initialization"""
        agent = AgentEntity(
            id=AgentId(str(uuid.uuid4())),
            name="test-agent",
            description="Test agent for timestamp regression"
        )
        # Timestamps should be automatically initialized by BaseTimestampEntity
        assert agent.created_at is not None, "Agent entity should have created_at initialized"
        assert agent.updated_at is not None, "Agent entity should have updated_at initialized"
        return agent

    def test_entity_to_model_dict_includes_timestamps(self, agent_repository, sample_agent_entity):
        """
        REGRESSION TEST: Verify _entity_to_model_dict includes timestamps

        This is the core bug fix test. The _entity_to_model_dict method MUST include
        created_at and updated_at in the returned dictionary to prevent database
        constraint violations.
        """
        # Convert entity to model dict
        model_dict = agent_repository._entity_to_model_dict(sample_agent_entity)

        # CRITICAL: Verify timestamps are in the dictionary
        assert "created_at" in model_dict, (
            "REGRESSION: created_at missing from model dict! "
            "This will cause database constraint violation during agent registration."
        )
        assert "updated_at" in model_dict, (
            "REGRESSION: updated_at missing from model dict! "
            "This will cause database constraint violation during agent registration."
        )

        # Verify timestamp values are datetime objects
        assert isinstance(model_dict["created_at"], datetime), (
            "created_at should be a datetime object"
        )
        assert isinstance(model_dict["updated_at"], datetime), (
            "updated_at should be a datetime object"
        )

        # Verify timestamps match entity timestamps
        assert model_dict["created_at"] == sample_agent_entity.created_at
        assert model_dict["updated_at"] == sample_agent_entity.updated_at

    def test_entity_to_model_dict_timestamps_are_utc(self, agent_repository, sample_agent_entity):
        """
        Verify that timestamps in model dict are timezone-aware UTC

        Database expects UTC timestamps, so we must ensure the conversion
        preserves timezone information.
        """
        model_dict = agent_repository._entity_to_model_dict(sample_agent_entity)

        created_at = model_dict["created_at"]
        updated_at = model_dict["updated_at"]

        # Verify timezone awareness
        assert created_at.tzinfo is not None, "created_at should be timezone-aware"
        assert updated_at.tzinfo is not None, "updated_at should be timezone-aware"

        # Verify UTC timezone
        assert created_at.tzinfo == UTC or created_at.tzinfo.utcoffset(None).total_seconds() == 0
        assert updated_at.tzinfo == UTC or updated_at.tzinfo.utcoffset(None).total_seconds() == 0

    def test_entity_timestamps_initialized_by_base_class(self):
        """
        Verify that AgentEntity timestamps are properly initialized by BaseTimestampEntity

        This test confirms the entity layer is working correctly. The bug was in
        the repository layer, not the entity initialization.
        """
        # Create new agent entity
        agent = AgentEntity(
            id=AgentId(str(uuid.uuid4())),
            name="timestamp-test-agent",
            description="Testing timestamp initialization"
        )

        # Verify BaseTimestampEntity.__post_init__() set timestamps
        assert agent.created_at is not None, "BaseTimestampEntity should initialize created_at"
        assert agent.updated_at is not None, "BaseTimestampEntity should initialize updated_at"

        # Verify timestamps are recent (within last second)
        now = datetime.now(UTC)
        time_diff_created = (now - agent.created_at).total_seconds()
        time_diff_updated = (now - agent.updated_at).total_seconds()

        assert time_diff_created < 1.0, "created_at should be very recent"
        assert time_diff_updated < 1.0, "updated_at should be very recent"

        # Verify timestamps are UTC
        assert agent.created_at.tzinfo == UTC
        assert agent.updated_at.tzinfo == UTC

    def test_model_to_entity_includes_timestamps(self, agent_repository):
        """
        Verify reverse conversion (_model_to_entity) also handles timestamps correctly

        This test confirms the bidirectional mapping is complete.
        """
        from fastmcp.task_management.infrastructure.database.models import (
            Agent as AgentModel,
        )

        # Create mock agent model with timestamps
        now = datetime.now(UTC)
        agent_model = AgentModel(
            id=str(uuid.uuid4()),
            name="model-test-agent",
            description="Test agent model",
            created_at=now,
            updated_at=now,
            capabilities=[],
            status="available",
            model_metadata={}
        )

        # Convert to entity
        agent_entity = agent_repository._model_to_entity(agent_model)

        # Verify timestamps are preserved
        assert agent_entity.created_at == agent_model.created_at
        assert agent_entity.updated_at == agent_model.updated_at

    def test_full_entity_to_model_dict_structure(self, agent_repository, sample_agent_entity):
        """
        Verify complete structure of entity-to-model conversion

        This comprehensive test ensures all required fields are present,
        preventing similar bugs with other fields.
        """
        model_dict = agent_repository._entity_to_model_dict(sample_agent_entity)

        # Required database fields
        required_fields = [
            "id",
            "name",
            "description",
            "capabilities",
            "status",
            "availability_score",
            "created_at",  # CRITICAL: Must be present
            "updated_at",  # CRITICAL: Must be present
            "model_metadata"
        ]

        for field in required_fields:
            assert field in model_dict, (
                f"Required field '{field}' missing from model dict. "
                f"This may cause database errors during agent operations."
            )

    def test_agent_registration_with_timestamps_integration(self, agent_repository, sample_agent_entity, mock_session):
        """
        Integration test: Verify agent registration doesn't fail due to missing timestamps

        This test simulates the actual registration flow that was failing before the fix.
        """
        # Mock the create method to simulate database INSERT
        with patch.object(agent_repository, 'create') as mock_create:
            # Create a mock Agent model that would be returned from database
            from fastmcp.task_management.infrastructure.database.models import (
                Agent as AgentModel,
            )

            mock_agent_model = AgentModel(
                id=str(sample_agent_entity.id),
                name=sample_agent_entity.name,
                description=sample_agent_entity.description,
                created_at=sample_agent_entity.created_at,
                updated_at=sample_agent_entity.updated_at,
                capabilities=[],
                status="available",
                model_metadata={}
            )
            mock_create.return_value = mock_agent_model

            # Mock exists check
            with patch.object(agent_repository, 'exists', return_value=False):
                # Mock find_by_name check
                with patch.object(agent_repository, 'find_by_name', return_value=None):
                    # Attempt registration
                    agent_repository.register_agent(sample_agent_entity)

                    # Verify create was called with proper timestamp data
                    mock_create.assert_called_once()
                    call_kwargs = mock_create.call_args[1]

                    # CRITICAL: Verify timestamps were passed to database
                    assert "created_at" in call_kwargs, (
                        "REGRESSION: created_at not passed to database during agent registration!"
                    )
                    assert "updated_at" in call_kwargs, (
                        "REGRESSION: updated_at not passed to database during agent registration!"
                    )

                    # Verify timestamps are datetime objects
                    assert isinstance(call_kwargs["created_at"], datetime)
                    assert isinstance(call_kwargs["updated_at"], datetime)

    def test_timestamp_consistency_across_operations(self, agent_repository):
        """
        Verify timestamp handling is consistent across different repository operations
        """
        # Create agent entity
        agent = AgentEntity(
            id=AgentId(str(uuid.uuid4())),
            name="consistency-test-agent",
            description="Testing timestamp consistency"
        )

        # Get initial model dict
        initial_dict = agent_repository._entity_to_model_dict(agent)
        initial_created_at = initial_dict["created_at"]
        initial_updated_at = initial_dict["updated_at"]

        # Simulate time passing and entity touch
        import time
        time.sleep(0.01)
        agent.touch("test_update")

        # Get updated model dict
        updated_dict = agent_repository._entity_to_model_dict(agent)
        updated_created_at = updated_dict["created_at"]
        updated_updated_at = updated_dict["updated_at"]

        # Verify created_at remains unchanged
        assert updated_created_at == initial_created_at, (
            "created_at should never change after initial creation"
        )

        # Verify updated_at changed after touch
        assert updated_updated_at > initial_updated_at, (
            "updated_at should increase after entity modification"
        )


class TestTimestampBugPreventionGuidelines:
    """
    Documentation tests that serve as guidelines for preventing similar bugs
    """

    def test_entity_to_model_conversion_guidelines(self):
        """
        GUIDELINE: When creating entity-to-model conversion methods,
        ALWAYS include ALL fields that have database NOT NULL constraints.

        Checklist for _entity_to_model_dict implementations:
        1. ✅ Include all base class fields (created_at, updated_at)
        2. ✅ Include all required database columns
        3. ✅ Preserve timezone information for datetime fields
        4. ✅ Test the conversion with actual database operations
        5. ✅ Add regression tests for critical fields
        """
        # This test exists purely for documentation
        assert True, "Follow the guidelines in the docstring"

    def test_timestamp_field_requirements(self):
        """
        GUIDELINE: All domain entities inheriting from BaseTimestampEntity
        must ensure their repository conversions include timestamps.

        Required fields in ALL _entity_to_model_dict methods:
        - created_at (datetime, UTC, NOT NULL)
        - updated_at (datetime, UTC, NOT NULL)

        Common patterns that cause bugs:
        1. ❌ Forgetting to include parent class fields in conversion
        2. ❌ Assuming database will auto-populate timestamps (it won't)
        3. ❌ Not testing the actual database INSERT operation
        4. ❌ Missing timezone information in datetime fields
        """
        assert True, "Follow the guidelines in the docstring"


# Pytest markers for test organization
pytestmark = [
    pytest.mark.unit,
    pytest.mark.regression,
    pytest.mark.agent_repository,
    pytest.mark.timestamp_bug_fix
]
