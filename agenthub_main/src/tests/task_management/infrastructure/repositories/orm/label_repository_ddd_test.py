"""
DDD Compliance Tests for Label Repository

This module tests the DDD architecture compliance of the label repository,
specifically verifying the implementation of _entity_to_model_dict() method
and proper DDD patterns in update operations.

Reference:
- ai_docs/code-quality/ddd-architecture-audit-2025-10-08.md
- agent_repository.py (reference implementation)

Test Strategy:
- Verify _entity_to_model_dict() method exists and functions correctly
- Verify update operations follow DDD pattern (entity → model dict → ORM)
- Test round-trip conversion (model → entity → model dict)
- Validate all fields are correctly converted
"""

import pytest
import uuid
import inspect
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

from fastmcp.task_management.infrastructure.repositories.orm.label_repository import ORMLabelRepository
from fastmcp.task_management.infrastructure.database.models import Label
from fastmcp.task_management.domain.entities.label import Label as LabelEntity
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    NotFoundError,
    ValidationError
)


class TestLabelRepositoryDDDCompliance:
    """
    DDD Compliance Tests for Label Repository

    These tests verify that label_repository follows DDD architecture patterns
    as established in agent_repository (reference implementation).
    """

    @pytest.fixture
    def mock_db_adapter(self):
        """Mock database adapter for testing"""
        adapter = Mock()
        session = MagicMock()
        adapter.get_session.return_value.__enter__ = Mock(return_value=session)
        adapter.get_session.return_value.__exit__ = Mock(return_value=None)
        return adapter

    @pytest.fixture
    def repository(self, mock_db_adapter):
        """Repository instance for testing"""
        repo = ORMLabelRepository(db_adapter=mock_db_adapter)
        repo.user_id = str(uuid.uuid4())  # Set user_id for testing
        return repo

    @pytest.fixture
    def sample_label_entity(self):
        """Sample label entity for testing"""
        return LabelEntity(
            id=1,
            name="Bug",
            color="#ff0000",
            description="Bug-related tasks",
            created_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def sample_label_model(self):
        """Sample label ORM model for testing"""
        model = Mock(spec=Label)
        model.id = 1
        model.name = "Bug"
        model.color = "#ff0000"
        model.description = "Bug-related tasks"
        model.created_at = datetime.now(timezone.utc)
        model.user_id = str(uuid.uuid4())
        return model

    # ============================================================================
    # CRITICAL TEST 1: Method Existence
    # ============================================================================

    def test_entity_to_model_dict_method_exists(self, repository):
        """
        CRITICAL TEST 1: Verify _entity_to_model_dict() method exists

        This is the core DDD compliance requirement - the repository MUST have
        this method to convert domain entities to infrastructure layer data.
        """
        assert hasattr(repository, '_entity_to_model_dict'), \
            "DDD VIOLATION: label_repository must have _entity_to_model_dict() method"

        assert callable(getattr(repository, '_entity_to_model_dict')), \
            "_entity_to_model_dict must be a callable method"

    def test_model_to_entity_method_exists(self, repository):
        """
        Verify _model_to_entity() method exists (should already be present)
        """
        assert hasattr(repository, '_model_to_entity'), \
            "Repository must have _model_to_entity() method"

        assert callable(getattr(repository, '_model_to_entity')), \
            "_model_to_entity must be a callable method"

    # ============================================================================
    # CRITICAL TEST 2: Method Signature
    # ============================================================================

    def test_entity_to_model_dict_signature(self, repository):
        """
        CRITICAL TEST 2: Verify _entity_to_model_dict() has correct signature

        Method must accept a LabelEntity parameter and return a dictionary.
        """
        import inspect
        sig = inspect.signature(repository._entity_to_model_dict)
        params = list(sig.parameters.keys())

        # Should have 'entity' parameter
        assert 'entity' in params, \
            "_entity_to_model_dict must have 'entity' parameter"

        # Get the type annotation if available
        entity_param = sig.parameters['entity']
        if entity_param.annotation != inspect.Parameter.empty:
            # Verify it's annotated as LabelEntity
            assert 'LabelEntity' in str(entity_param.annotation) or 'Label' in str(entity_param.annotation), \
                "entity parameter should be annotated as LabelEntity"

    # ============================================================================
    # CRITICAL TEST 3: Entity to Model Dict Conversion
    # ============================================================================

    def test_entity_to_model_dict_converts_all_fields(self, repository, sample_label_entity):
        """
        CRITICAL TEST 3: Verify _entity_to_model_dict() converts all required fields

        Must convert: id, name, color, description, user_id
        """
        result = repository._entity_to_model_dict(sample_label_entity)

        # Verify result is a dictionary
        assert isinstance(result, dict), \
            "_entity_to_model_dict must return a dictionary"

        # Verify all required fields are present
        required_fields = ['id', 'name', 'color', 'description', 'user_id']
        for field in required_fields:
            assert field in result, \
                f"_entity_to_model_dict must include '{field}' field"

    def test_entity_to_model_dict_field_values(self, repository, sample_label_entity):
        """
        Verify _entity_to_model_dict() correctly maps field values
        """
        result = repository._entity_to_model_dict(sample_label_entity)

        # Verify field values match entity
        assert result['id'] == sample_label_entity.id, \
            "id field must match entity.id"
        assert result['name'] == sample_label_entity.name, \
            "name field must match entity.name"
        assert result['color'] == sample_label_entity.color, \
            "color field must match entity.color"
        assert result['description'] == sample_label_entity.description, \
            "description field must match entity.description"
        assert result['user_id'] == repository.user_id, \
            "user_id field must match repository.user_id"

    # ============================================================================
    # CRITICAL TEST 4: Round-Trip Conversion
    # ============================================================================

    def test_round_trip_conversion(self, repository, sample_label_model):
        """
        CRITICAL TEST 4: Verify round-trip conversion works correctly

        Flow: ORM Model → Entity → Model Dict
        This ensures data integrity through the conversion pipeline.
        """
        # Step 1: Model to Entity
        entity = repository._model_to_entity(sample_label_model)

        # Verify entity is created correctly
        assert isinstance(entity, LabelEntity), \
            "_model_to_entity must return LabelEntity instance"
        assert entity.id == sample_label_model.id
        assert entity.name == sample_label_model.name
        assert entity.color == sample_label_model.color
        assert entity.description == sample_label_model.description

        # Step 2: Entity to Model Dict
        model_dict = repository._entity_to_model_dict(entity)

        # Verify model dict matches original
        assert model_dict['id'] == sample_label_model.id
        assert model_dict['name'] == sample_label_model.name
        assert model_dict['color'] == sample_label_model.color
        assert model_dict['description'] == sample_label_model.description

    # ============================================================================
    # CRITICAL TEST 5: Update Operation Uses DDD Pattern
    # ============================================================================

    def test_update_label_uses_ddd_pattern(self):
        """
        CRITICAL TEST 5: Verify update_label() follows DDD pattern

        The update operation MUST:
        1. Convert ORM model to domain entity
        2. Modify entity fields
        3. Convert entity back to model dict
        4. Apply model dict to ORM model
        """
        # Get source code of update_label method
        source = inspect.getsource(ORMLabelRepository.update_label)

        # Verify DDD pattern is followed
        assert "_model_to_entity" in source, \
            "update_label must call _model_to_entity to convert to domain entity"

        assert "_entity_to_model_dict" in source, \
            "update_label must call _entity_to_model_dict to convert back to model dict"

        # Verify correct flow order
        model_to_entity_pos = source.find("_model_to_entity")
        entity_to_dict_pos = source.find("_entity_to_model_dict")

        assert model_to_entity_pos < entity_to_dict_pos, \
            "update_label must call _model_to_entity BEFORE _entity_to_model_dict"

    def test_update_label_has_ddd_comments(self):
        """
        Verify update_label() has DDD compliance comments

        Following agent_repository pattern, should have comments like:
        - "DDD-COMPLIANT: Convert ORM model to domain entity"
        - "DDD-COMPLIANT: Convert entity back to model dict"
        """
        source = inspect.getsource(ORMLabelRepository.update_label)

        # Check for DDD compliance comments
        assert "DDD-COMPLIANT" in source or "DDD" in source.upper(), \
            "update_label should have DDD compliance comments for clarity"

    # ============================================================================
    # CRITICAL TEST 6: Update Operation Integration Test
    # ============================================================================

    def test_update_label_integration_pattern(self):
        """
        CRITICAL TEST 6: Verify update_label follows complete DDD integration pattern

        This test verifies the complete update flow pattern is correctly implemented:
        1. Fetch model from database
        2. Convert to entity (_model_to_entity)
        3. Modify entity fields
        4. Validate entity (_validate_entity)
        5. Convert to model dict (_entity_to_model_dict)
        6. Update ORM model fields
        7. Commit and return

        We verify this by checking the source code follows the pattern.
        """
        source = inspect.getsource(ORMLabelRepository.update_label)

        # Verify all steps are present in correct order
        assert "query(Label)" in source, \
            "Step 1: Must fetch model from database"

        assert "_model_to_entity" in source, \
            "Step 2: Must convert model to entity"

        # Find positions of key operations to verify order
        positions = {
            'fetch': source.find("query(Label)"),
            'to_entity': source.find("_model_to_entity"),
            'validate': source.find("_validate_entity"),
            'to_dict': source.find("_entity_to_model_dict"),
            'commit': source.find("commit()")
        }

        # Verify operations happen in correct order
        assert positions['fetch'] < positions['to_entity'], \
            "Must fetch before converting to entity"

        assert positions['to_entity'] < positions['validate'], \
            "Must convert to entity before validation"

        assert positions['validate'] < positions['to_dict'], \
            "Must validate before converting to dict"

        assert positions['to_dict'] < positions['commit'], \
            "Must convert to dict before commit"

    # ============================================================================
    # CRITICAL TEST 7: Documentation
    # ============================================================================

    def test_entity_to_model_dict_has_documentation(self, repository):
        """
        CRITICAL TEST 7: Verify _entity_to_model_dict() has proper documentation

        Documentation must explain:
        - What the method does
        - DDD compliance purpose
        - Parameters and return value
        """
        docstring = repository._entity_to_model_dict.__doc__

        assert docstring is not None, \
            "_entity_to_model_dict must have documentation"

        docstring_lower = docstring.lower()

        # Check for key documentation elements
        assert any(keyword in docstring_lower for keyword in ["convert", "entity", "model"]), \
            "Documentation must explain conversion purpose"

        assert any(keyword in docstring_lower for keyword in ["ddd", "domain"]), \
            "Documentation must mention DDD compliance"

    # ============================================================================
    # CRITICAL TEST 8: Edge Cases
    # ============================================================================

    def test_entity_to_model_dict_handles_empty_description(self, repository):
        """
        Verify _entity_to_model_dict() handles empty description correctly
        """
        entity = LabelEntity(
            id=1,
            name="Test",
            color="#000000",
            description="",  # Empty description
            created_at=datetime.now(timezone.utc)
        )

        result = repository._entity_to_model_dict(entity)

        assert result['description'] == "", \
            "Empty description must be preserved"

    def test_entity_to_model_dict_handles_special_characters(self, repository):
        """
        Verify _entity_to_model_dict() handles special characters in fields
        """
        entity = LabelEntity(
            id=1,
            name="Bug (Critical)",
            color="#ff0000",
            description="Description with 'quotes' and \"double quotes\"",
            created_at=datetime.now(timezone.utc)
        )

        result = repository._entity_to_model_dict(entity)

        assert result['name'] == entity.name, \
            "Special characters in name must be preserved"
        assert result['description'] == entity.description, \
            "Special characters in description must be preserved"

    # ============================================================================
    # CRITICAL TEST 9: Validation Integration
    # ============================================================================

    def test_update_label_validates_entity(self):
        """
        CRITICAL TEST 9: Verify update_label() calls entity validation

        Following DDD principles, domain entity validation should be triggered
        during the update operation.
        """
        source = inspect.getsource(ORMLabelRepository.update_label)

        # Check if validation is called
        assert "_validate_entity" in source or "validate" in source.lower(), \
            "update_label should trigger entity validation"


class TestLabelRepositoryDDDPatternComparison:
    """
    Compare label_repository implementation with agent_repository (reference)

    These tests ensure label_repository follows the same DDD patterns as
    the reference implementation in agent_repository.
    """

    def test_has_same_conversion_methods_as_reference(self):
        """
        Verify label_repository has the same conversion methods as agent_repository
        """
        from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import ORMAgentRepository

        # Get methods from both repositories
        label_methods = dir(ORMLabelRepository)
        agent_methods = dir(ORMAgentRepository)

        # Both must have these conversion methods
        required_methods = ['_model_to_entity', '_entity_to_model_dict']

        for method in required_methods:
            assert method in label_methods, \
                f"label_repository must have {method} method like agent_repository"
            assert method in agent_methods, \
                f"agent_repository reference has {method} method"

    def test_update_pattern_matches_reference_structure(self):
        """
        Verify update_label follows same DDD pattern as agent_repository update operations
        """
        # Get agent_repository update operation (assign_agent_to_tree as example)
        from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import ORMAgentRepository
        agent_source = inspect.getsource(ORMAgentRepository.assign_agent_to_tree)

        # Get label_repository update operation
        label_source = inspect.getsource(ORMLabelRepository.update_label)

        # Both should follow DDD pattern
        agent_has_ddd = "_model_to_entity" in agent_source and "_entity_to_model_dict" in agent_source
        label_has_ddd = "_model_to_entity" in label_source and "_entity_to_model_dict" in label_source

        assert agent_has_ddd, "Reference implementation uses DDD pattern"
        assert label_has_ddd, "label_repository must use same DDD pattern as reference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
