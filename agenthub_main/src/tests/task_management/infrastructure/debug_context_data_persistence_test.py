"""
Debug Test: Context Data Persistence Issue Reproduction

This test reproduces the bug where context data field content is not being
properly stored or returned from the database.
"""

import pytest
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastmcp.task_management.infrastructure.database.models import GlobalContext as GlobalContextModel
from fastmcp.task_management.infrastructure.database.database_config import Base
from fastmcp.task_management.infrastructure.repositories.global_context_repository import GlobalContextRepository
from fastmcp.task_management.domain.entities.context import GlobalContext

class TestContextDataPersistenceBug:
    """Test to reproduce and fix the context data persistence bug."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=True)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def session_factory(self, db_session):
        """Session factory for repository."""
        def _session_factory():
            return db_session
        return _session_factory

    @pytest.fixture
    def global_context_repo(self, session_factory):
        """Global context repository with test user."""
        return GlobalContextRepository(session_factory, user_id="test-user-123")

    def test_reproduce_data_field_missing_bug(self, global_context_repo, db_session):
        """Reproduce the bug where data field is not stored/returned."""

        # Create complex test data
        test_data = {
            "organization_settings": {
                "name": "Test Organization",
                "policies": {
                    "security": "strict",
                    "compliance": "SOC2"
                }
            },
            "user_preferences": {
                "theme": "dark",
                "notifications": True,
                "ai_agent_settings": {
                    "preferred_agents": ["coding-agent", "debugger-agent"],
                    "auto_delegation": True
                }
            },
            "workflow_templates": {
                "default_branch_pattern": "feature/*",
                "required_reviewers": 2
            }
        }

        # Create global context entity
        context_entity = GlobalContext(
            id="test-context-123",
            organization_name="Test Org",
            global_settings=test_data,
            metadata={"test": True}
        )

        print(f"🔍 Original data to store: {json.dumps(test_data, indent=2)}")

        # Store the context
        stored_context = global_context_repo.create(context_entity)
        print(f"✅ Context stored with ID: {stored_context.id}")

        # Retrieve the context
        retrieved_context = global_context_repo.get("test-context-123")

        assert retrieved_context is not None, "Context should be retrievable"
        print(f"📄 Retrieved global_settings: {json.dumps(retrieved_context.global_settings, indent=2)}")

        # Check if the data field exists in database model
        db_model = db_session.query(GlobalContextModel).filter_by(id="test-context-123").first()

        print(f"🔍 Database model attributes: {dir(db_model)}")
        print(f"🔍 Has 'data' field: {hasattr(db_model, 'data')}")
        print(f"🔍 Has 'nested_structure' field: {hasattr(db_model, 'nested_structure')}")

        if hasattr(db_model, 'data'):
            print(f"📊 DB model data field: {db_model.data}")
        else:
            print("❌ ISSUE: DB model missing 'data' field")

        if hasattr(db_model, 'nested_structure'):
            print(f"📊 DB model nested_structure: {json.dumps(db_model.nested_structure, indent=2)}")

        # The bug: retrieved context should contain the original data
        # But due to missing 'data' field in GlobalContext model, it might be lost
        assert retrieved_context.global_settings is not None, "Global settings should not be None"

        # Test if specific data is preserved
        original_org_name = test_data.get("organization_settings", {}).get("name")
        retrieved_org_data = retrieved_context.global_settings.get("organization_settings", {})

        print(f"🔍 Original org name: {original_org_name}")
        print(f"🔍 Retrieved org data: {retrieved_org_data}")

        # This assertion might fail due to the bug
        if original_org_name:
            retrieved_org_name = retrieved_org_data.get("name") if isinstance(retrieved_org_data, dict) else None
            if retrieved_org_name != original_org_name:
                print(f"❌ BUG REPRODUCED: Expected '{original_org_name}', got '{retrieved_org_name}'")
                print("🔧 This confirms the context data persistence issue!")

    def test_check_database_schema_differences(self, db_session):
        """Check the difference between GlobalContext and ProjectContext schemas."""

        # Test GlobalContext model
        global_model = GlobalContextModel(
            id="test-global-123",
            user_id="test-user",
            organization_standards={},
            security_policies={},
            compliance_requirements={},
            shared_resources={},
            reusable_patterns={},
            global_preferences={},
            delegation_rules={},
            nested_structure={"test": "data"}
        )

        db_session.add(global_model)
        db_session.commit()

        # Check what fields exist
        print("🔍 GlobalContext model fields:")
        for attr in dir(global_model):
            if not attr.startswith('_') and not callable(getattr(global_model, attr)):
                value = getattr(global_model, attr)
                print(f"  - {attr}: {type(value)} = {value}")

        # Key finding: GlobalContext has no 'data' field
        print(f"❌ GlobalContext has 'data' field: {hasattr(global_model, 'data')}")
        print(f"✅ GlobalContext has 'nested_structure' field: {hasattr(global_model, 'nested_structure')}")


if __name__ == "__main__":
    # Run the test directly
    import sys
    sys.path.append('/home/daihungpham/__projects__/agentic-project/agenthub_main/src')

    # Create test instance and run
    test_instance = TestContextDataPersistenceBug()

    # Mock fixtures for direct execution
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def session_factory():
        return session

    repo = GlobalContextRepository(session_factory, user_id="test-user-123")

    try:
        print("🧪 Running Context Data Persistence Bug Reproduction Test...")
        test_instance.test_reproduce_data_field_missing_bug(repo, session)
        test_instance.test_check_database_schema_differences(session)
        print("✅ Test completed!")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()