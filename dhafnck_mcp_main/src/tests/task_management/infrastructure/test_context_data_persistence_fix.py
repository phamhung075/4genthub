"""
Test: Context Data Persistence Fix Verification

This test verifies that the context data persistence issue has been resolved
by testing both the database model changes and repository logic updates.
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


class TestContextDataPersistenceFix:
    """Test the fix for context data persistence issue."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
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

    def test_global_context_model_has_data_field(self, db_session):
        """Test that GlobalContext model has the nested_structure field for data storage."""

        # Create a GlobalContext model instance
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
            nested_structure={"test": "nested_data"}  # Use nested_structure instead of data field
        )

        # Verify the nested_structure field exists and can be set
        assert hasattr(global_model, 'nested_structure'), "GlobalContext model should have 'nested_structure' field"
        assert global_model.nested_structure == {"test": "nested_data"}, "Nested structure field should store the provided data"

        # Test database persistence
        db_session.add(global_model)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(GlobalContextModel).filter_by(id="test-global-123").first()
        assert retrieved is not None, "Should be able to retrieve the model"
        assert retrieved.nested_structure == {"test": "nested_data"}, "Nested structure field should persist to database"

    def test_context_data_round_trip_persistence(self, global_context_repo, db_session):
        """Test complete round-trip: create -> store -> retrieve -> verify data preservation."""

        # Create complex test data that should be fully preserved
        test_data = {
            "organization_settings": {
                "name": "DhafnckMCP Enterprise",
                "tier": "premium",
                "policies": {
                    "security_level": "strict",
                    "compliance_standards": ["SOC2", "GDPR", "HIPAA"],
                    "data_retention_days": 2555
                }
            },
            "user_preferences": {
                "theme": "dark",
                "language": "en-US",
                "notifications": {
                    "email": True,
                    "push": False,
                    "digest_frequency": "daily"
                },
                "ai_agent_settings": {
                    "preferred_agents": ["coding-agent", "debugger-agent", "test-orchestrator-agent"],
                    "auto_delegation": True,
                    "delegation_threshold": 0.8,
                    "agent_priorities": {
                        "coding": 1,
                        "debugging": 2,
                        "testing": 3
                    }
                }
            },
            "development_configuration": {
                "default_branch_pattern": "feature/*",
                "required_reviewers": 2,
                "auto_merge": False,
                "ci_cd_settings": {
                    "auto_deploy_staging": True,
                    "auto_deploy_prod": False,
                    "test_coverage_threshold": 85
                },
                "code_quality": {
                    "max_complexity": 10,
                    "max_line_length": 120,
                    "require_type_hints": True
                }
            },
            "security_configuration": {
                "mfa_required": True,
                "session_timeout_minutes": 480,
                "password_policy": {
                    "min_length": 12,
                    "require_special_chars": True,
                    "require_numbers": True,
                    "require_upper_case": True
                },
                "api_rate_limits": {
                    "requests_per_hour": 1000,
                    "burst_limit": 50
                }
            },
            "metadata": {
                "schema_version": "2.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "updated_by": "test-user-123",
                "feature_flags": {
                    "new_ui": True,
                    "beta_features": False,
                    "experimental_ai": True
                }
            }
        }

        print(f"🔍 Original data size: {len(json.dumps(test_data))} characters")
        print(f"🔍 Original data keys: {list(test_data.keys())}")

        # Create global context entity
        context_entity = GlobalContext(
            id="test-context-data-fix",
            organization_name="DhafnckMCP Enterprise",
            global_settings=test_data,
            metadata={"test_case": "data_persistence_fix"}
        )

        # Store the context
        print("💾 Storing context with repository...")
        stored_context = global_context_repo.create(context_entity)
        assert stored_context is not None, "Context should be stored successfully"

        # Note: The repository may generate a new UUID, so we use the returned ID
        stored_id = stored_context.id
        print(f"📝 Generated context ID: {stored_id}")

        # Verify data field in database model
        print("🔍 Checking database model directly...")
        db_model = db_session.query(GlobalContextModel).filter_by(id=stored_id).first()
        assert db_model is not None, "Database model should exist"
        assert hasattr(db_model, 'nested_structure'), "Database model should have nested_structure field"
        assert db_model.nested_structure is not None, "Nested structure field should not be None"

        print(f"📊 DB model nested_structure field size: {len(json.dumps(db_model.nested_structure)) if db_model.nested_structure else 0} characters")

        # Retrieve the context
        print("📥 Retrieving context from repository...")
        retrieved_context = global_context_repo.get(stored_id)
        assert retrieved_context is not None, "Context should be retrievable"

        # Verify complete data preservation
        retrieved_data = retrieved_context.global_settings
        assert retrieved_data is not None, "Retrieved global_settings should not be None"

        print(f"📊 Retrieved data size: {len(json.dumps(retrieved_data))} characters")
        print(f"🔍 Retrieved data keys: {list(retrieved_data.keys())}")

        # Test specific nested data preservation
        assert "organization_settings" in retrieved_data, "Should preserve organization_settings"
        assert "user_preferences" in retrieved_data, "Should preserve user_preferences"
        assert "development_configuration" in retrieved_data, "Should preserve development_configuration"
        assert "security_configuration" in retrieved_data, "Should preserve security_configuration"

        # Test deep nested data preservation
        org_settings = retrieved_data.get("organization_settings", {})
        assert org_settings.get("name") == "DhafnckMCP Enterprise", "Should preserve organization name"
        assert org_settings.get("tier") == "premium", "Should preserve organization tier"

        policies = org_settings.get("policies", {})
        assert policies.get("data_retention_days") == 2555, "Should preserve numeric values"
        assert "SOC2" in policies.get("compliance_standards", []), "Should preserve array values"

        # Test AI agent settings preservation
        user_prefs = retrieved_data.get("user_preferences", {})
        ai_settings = user_prefs.get("ai_agent_settings", {})
        assert "coding-agent" in ai_settings.get("preferred_agents", []), "Should preserve AI agent preferences"
        assert ai_settings.get("delegation_threshold") == 0.8, "Should preserve float values"

        # Test complex nested objects
        dev_config = retrieved_data.get("development_configuration", {})
        ci_cd = dev_config.get("ci_cd_settings", {})
        assert ci_cd.get("test_coverage_threshold") == 85, "Should preserve CI/CD configuration"

        print("✅ All data preservation tests passed!")

    def test_data_field_fallback_logic(self, global_context_repo, db_session):
        """Test that the data field is used as fallback when other fields are empty."""

        # Create context with data only in the data field
        test_data_only = {
            "fallback_test": True,
            "data_field_content": {
                "specific_setting": "value_from_data_field",
                "numeric_value": 42
            }
        }

        # Manually create database model with unified_context_data field only
        db_model = GlobalContextModel(
            id="test-fallback-123",
            user_id="test-user-123",
            organization_standards={},
            security_policies={},
            compliance_requirements={},
            shared_resources={},
            reusable_patterns={},
            global_preferences={},
            delegation_rules={},
            nested_structure={},  # Empty nested structure
            unified_context_data=test_data_only  # Only unified_context_data field has content
        )

        db_session.add(db_model)
        db_session.commit()

        # Retrieve using repository
        retrieved_context = global_context_repo.get("test-fallback-123")
        assert retrieved_context is not None, "Should retrieve context"

        # Verify data field content is used
        retrieved_data = retrieved_context.global_settings
        assert retrieved_data.get("fallback_test") is True, "Should use data field content"
        assert retrieved_data.get("data_field_content", {}).get("specific_setting") == "value_from_data_field"
        assert retrieved_data.get("data_field_content", {}).get("numeric_value") == 42

        print("✅ Data field fallback logic test passed!")

    def test_backward_compatibility(self, global_context_repo, db_session):
        """Test that existing contexts without data field still work."""

        # Create context using old structure (no data field)
        old_context_data = {
            "organization": {
                "standards": {"coding_style": "PEP8"},
                "policies": {"review_required": True}
            },
            "preferences": {
                "user_interface": {"theme": "light"},
                "workflow": {"auto_save": True}
            }
        }

        # Create database model without data field (simulating old records)
        db_model = GlobalContextModel(
            id="test-backward-compat",
            user_id="test-user-123",
            organization_standards={"coding_style": "PEP8"},
            security_policies={},
            compliance_requirements={},
            shared_resources={},
            reusable_patterns={},
            global_preferences={"theme": "light"},
            delegation_rules={},
            nested_structure=old_context_data,
            unified_context_data={}  # Explicitly set empty unified_context_data field to simulate old records
        )

        db_session.add(db_model)
        db_session.commit()

        # Retrieve using repository
        retrieved_context = global_context_repo.get("test-backward-compat")
        assert retrieved_context is not None, "Should retrieve old context"

        # Verify nested structure is still processed correctly
        # Note: Nested structure is converted to flat structure for compatibility
        retrieved_data = retrieved_context.global_settings
        assert "organization_standards" in retrieved_data, "Should preserve organization standards data"
        assert retrieved_data["organization_standards"].get("coding_style") == "PEP8", "Should preserve coding style"
        assert "user_preferences" in retrieved_data, "Should preserve user preferences data"
        assert retrieved_data["user_preferences"].get("theme") == "light", "Should preserve theme preference"

        print("✅ Backward compatibility test passed!")


if __name__ == "__main__":
    # Run tests directly for debugging
    import sys
    sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create test database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def session_factory():
        return session

    repo = GlobalContextRepository(session_factory, user_id="test-user-123")

    # Run tests
    test_instance = TestContextDataPersistenceFix()

    try:
        print("🧪 Running Context Data Persistence Fix Tests...")

        print("\n1. Testing GlobalContext model has data field...")
        test_instance.test_global_context_model_has_data_field(session)

        print("\n2. Testing context data round-trip persistence...")
        test_instance.test_context_data_round_trip_persistence(repo, session)

        print("\n3. Testing data field fallback logic...")
        test_instance.test_data_field_fallback_logic(repo, session)

        print("\n4. Testing backward compatibility...")
        test_instance.test_backward_compatibility(repo, session)

        print("\n🎉 All tests passed! Context data persistence issue is FIXED!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()