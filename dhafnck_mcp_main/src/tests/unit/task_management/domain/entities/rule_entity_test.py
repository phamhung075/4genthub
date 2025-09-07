"""Unit tests for Rule Domain Entities - Domain Entities for Rule Management"""

import pytest
from typing import Dict, Any, List

from fastmcp.task_management.domain.entities.rule_entity import (
    RuleMetadata,
    RuleContent,
    RuleInheritance
)
from fastmcp.task_management.domain.enums.rule_enums import (
    RuleFormat,
    RuleType,
    InheritanceType
)


class TestRuleMetadata:
    """Test suite for RuleMetadata domain entity."""

    @pytest.fixture
    def sample_metadata(self) -> RuleMetadata:
        """Create a sample RuleMetadata for testing."""
        return RuleMetadata(
            path="/rules/auth/jwt_rules.yml",
            format=RuleFormat.YAML,
            type=RuleType.BUSINESS,
            size=1024,
            modified=1640995200.0,
            checksum="abc123def456",
            dependencies=["base_auth.yml", "token_validation.yml"],
            version="1.0",
            author="security_team",
            description="JWT authentication and authorization rules",
            tags=["auth", "security", "jwt"]
        )

    @pytest.fixture
    def minimal_metadata(self) -> RuleMetadata:
        """Create minimal RuleMetadata for testing."""
        return RuleMetadata(
            path="/rules/simple.yml",
            format=RuleFormat.YAML,
            type=RuleType.VALIDATION,
            size=512,
            modified=1640995200.0,
            checksum="simple123",
            dependencies=[]
        )

    def test_rule_metadata_creation(self, sample_metadata: RuleMetadata):
        """Test RuleMetadata creation with all fields."""
        # Assert
        assert sample_metadata.path == "/rules/auth/jwt_rules.yml"
        assert sample_metadata.format == RuleFormat.YAML
        assert sample_metadata.type == RuleType.BUSINESS
        assert sample_metadata.size == 1024
        assert sample_metadata.modified == 1640995200.0
        assert sample_metadata.checksum == "abc123def456"
        assert sample_metadata.dependencies == ["base_auth.yml", "token_validation.yml"]
        assert sample_metadata.version == "1.0"
        assert sample_metadata.author == "security_team"
        assert sample_metadata.description == "JWT authentication and authorization rules"
        assert sample_metadata.tags == ["auth", "security", "jwt"]

    def test_rule_metadata_minimal_creation(self, minimal_metadata: RuleMetadata):
        """Test RuleMetadata creation with minimal fields."""
        # Assert
        assert minimal_metadata.path == "/rules/simple.yml"
        assert minimal_metadata.format == RuleFormat.YAML
        assert minimal_metadata.type == RuleType.VALIDATION
        assert minimal_metadata.version == "1.0"  # Default value
        assert minimal_metadata.author == "system"  # Default value
        assert minimal_metadata.description == ""  # Default value
        assert minimal_metadata.tags == []  # Default value

    def test_post_init_none_tags(self):
        """Test __post_init__ handles None tags properly."""
        # Arrange & Act
        metadata = RuleMetadata(
            path="/test.yml",
            format=RuleFormat.YAML,
            type=RuleType.BUSINESS,
            size=100,
            modified=1640995200.0,
            checksum="test123",
            dependencies=[],
            tags=None
        )

        # Assert
        assert metadata.tags == []

    class TestTagManagement:
        """Test cases for tag management methods."""

        def test_add_tag(self, minimal_metadata: RuleMetadata):
            """Test adding a tag."""
            # Act
            minimal_metadata.add_tag("new_tag")

            # Assert
            assert "new_tag" in minimal_metadata.tags
            assert minimal_metadata.has_tag("new_tag")

        def test_add_duplicate_tag(self, sample_metadata: RuleMetadata):
            """Test adding a duplicate tag doesn't create duplicates."""
            # Arrange
            original_tags = sample_metadata.tags.copy()
            
            # Act
            sample_metadata.add_tag("auth")  # Already exists

            # Assert
            assert sample_metadata.tags == original_tags
            assert sample_metadata.tags.count("auth") == 1

        def test_remove_existing_tag(self, sample_metadata: RuleMetadata):
            """Test removing an existing tag."""
            # Act
            sample_metadata.remove_tag("security")

            # Assert
            assert "security" not in sample_metadata.tags
            assert not sample_metadata.has_tag("security")
            assert "auth" in sample_metadata.tags  # Other tags remain

        def test_remove_nonexistent_tag(self, sample_metadata: RuleMetadata):
            """Test removing a non-existent tag doesn't raise error."""
            # Arrange
            original_tags = sample_metadata.tags.copy()
            
            # Act
            sample_metadata.remove_tag("nonexistent")

            # Assert
            assert sample_metadata.tags == original_tags

        def test_has_tag_existing(self, sample_metadata: RuleMetadata):
            """Test has_tag returns True for existing tag."""
            # Act & Assert
            assert sample_metadata.has_tag("jwt") is True

        def test_has_tag_nonexistent(self, sample_metadata: RuleMetadata):
            """Test has_tag returns False for non-existent tag."""
            # Act & Assert
            assert sample_metadata.has_tag("nonexistent") is False

    class TestDependencyManagement:
        """Test cases for dependency management methods."""

        def test_add_dependency(self, minimal_metadata: RuleMetadata):
            """Test adding a dependency."""
            # Act
            minimal_metadata.add_dependency("new_dependency.yml")

            # Assert
            assert "new_dependency.yml" in minimal_metadata.dependencies
            assert minimal_metadata.has_dependency("new_dependency.yml")

        def test_add_duplicate_dependency(self, sample_metadata: RuleMetadata):
            """Test adding a duplicate dependency doesn't create duplicates."""
            # Arrange
            original_deps = sample_metadata.dependencies.copy()
            
            # Act
            sample_metadata.add_dependency("base_auth.yml")  # Already exists

            # Assert
            assert sample_metadata.dependencies == original_deps
            assert sample_metadata.dependencies.count("base_auth.yml") == 1

        def test_remove_existing_dependency(self, sample_metadata: RuleMetadata):
            """Test removing an existing dependency."""
            # Act
            sample_metadata.remove_dependency("token_validation.yml")

            # Assert
            assert "token_validation.yml" not in sample_metadata.dependencies
            assert not sample_metadata.has_dependency("token_validation.yml")
            assert "base_auth.yml" in sample_metadata.dependencies  # Other deps remain

        def test_remove_nonexistent_dependency(self, sample_metadata: RuleMetadata):
            """Test removing a non-existent dependency doesn't raise error."""
            # Arrange
            original_deps = sample_metadata.dependencies.copy()
            
            # Act
            sample_metadata.remove_dependency("nonexistent.yml")

            # Assert
            assert sample_metadata.dependencies == original_deps

        def test_has_dependency_existing(self, sample_metadata: RuleMetadata):
            """Test has_dependency returns True for existing dependency."""
            # Act & Assert
            assert sample_metadata.has_dependency("base_auth.yml") is True

        def test_has_dependency_nonexistent(self, sample_metadata: RuleMetadata):
            """Test has_dependency returns False for non-existent dependency."""
            # Act & Assert
            assert sample_metadata.has_dependency("nonexistent.yml") is False


class TestRuleContent:
    """Test suite for RuleContent domain entity."""

    @pytest.fixture
    def sample_metadata(self) -> RuleMetadata:
        """Create sample metadata for RuleContent."""
        return RuleMetadata(
            path="/rules/test.yml",
            format=RuleFormat.YAML,
            type=RuleType.BUSINESS,
            size=512,
            modified=1640995200.0,
            checksum="test123",
            dependencies=[]
        )

    @pytest.fixture
    def sample_rule_content(self, sample_metadata: RuleMetadata) -> RuleContent:
        """Create a sample RuleContent for testing."""
        return RuleContent(
            metadata=sample_metadata,
            raw_content="version: 1.0\nrules:\n  - name: test_rule",
            parsed_content={
                "version": "1.0",
                "rules": [{"name": "test_rule"}]
            },
            sections={
                "header": "version: 1.0",
                "rules": "rules:\n  - name: test_rule",
                "footer": "# End of rules"
            },
            references=["common_rules.yml", "validation_rules.yml"],
            variables={
                "max_attempts": 3,
                "timeout_seconds": 30,
                "enabled": True
            }
        )

    def test_rule_content_creation(self, sample_rule_content: RuleContent):
        """Test RuleContent creation with all fields."""
        # Assert
        assert sample_rule_content.raw_content == "version: 1.0\nrules:\n  - name: test_rule"
        assert sample_rule_content.parsed_content["version"] == "1.0"
        assert len(sample_rule_content.sections) == 3
        assert len(sample_rule_content.references) == 2
        assert len(sample_rule_content.variables) == 3

    def test_rule_content_properties(self, sample_rule_content: RuleContent):
        """Test RuleContent properties."""
        # Act & Assert
        assert sample_rule_content.rule_path == "/rules/test.yml"
        assert sample_rule_content.rule_type == RuleType.BUSINESS
        assert sample_rule_content.rule_format == RuleFormat.YAML

    class TestSectionManagement:
        """Test cases for section management methods."""

        def test_get_existing_section(self, sample_rule_content: RuleContent):
            """Test getting an existing section."""
            # Act & Assert
            assert sample_rule_content.get_section("header") == "version: 1.0"
            assert sample_rule_content.get_section("rules") == "rules:\n  - name: test_rule"

        def test_get_nonexistent_section(self, sample_rule_content: RuleContent):
            """Test getting a non-existent section returns None."""
            # Act & Assert
            assert sample_rule_content.get_section("nonexistent") is None

        def test_set_new_section(self, sample_rule_content: RuleContent):
            """Test setting a new section."""
            # Act
            sample_rule_content.set_section("metadata", "author: test")

            # Assert
            assert sample_rule_content.get_section("metadata") == "author: test"
            assert sample_rule_content.has_section("metadata")

        def test_set_existing_section(self, sample_rule_content: RuleContent):
            """Test updating an existing section."""
            # Act
            sample_rule_content.set_section("header", "version: 2.0")

            # Assert
            assert sample_rule_content.get_section("header") == "version: 2.0"

        def test_has_section_existing(self, sample_rule_content: RuleContent):
            """Test has_section returns True for existing section."""
            # Act & Assert
            assert sample_rule_content.has_section("rules") is True

        def test_has_section_nonexistent(self, sample_rule_content: RuleContent):
            """Test has_section returns False for non-existent section."""
            # Act & Assert
            assert sample_rule_content.has_section("nonexistent") is False

    class TestVariableManagement:
        """Test cases for variable management methods."""

        def test_get_existing_variable(self, sample_rule_content: RuleContent):
            """Test getting an existing variable."""
            # Act & Assert
            assert sample_rule_content.get_variable("max_attempts") == 3
            assert sample_rule_content.get_variable("enabled") is True

        def test_get_nonexistent_variable_with_default(self, sample_rule_content: RuleContent):
            """Test getting a non-existent variable with default."""
            # Act & Assert
            assert sample_rule_content.get_variable("nonexistent", "default") == "default"

        def test_get_nonexistent_variable_without_default(self, sample_rule_content: RuleContent):
            """Test getting a non-existent variable without default returns None."""
            # Act & Assert
            assert sample_rule_content.get_variable("nonexistent") is None

        def test_set_new_variable(self, sample_rule_content: RuleContent):
            """Test setting a new variable."""
            # Act
            sample_rule_content.set_variable("new_var", "new_value")

            # Assert
            assert sample_rule_content.get_variable("new_var") == "new_value"
            assert sample_rule_content.has_variable("new_var")

        def test_set_existing_variable(self, sample_rule_content: RuleContent):
            """Test updating an existing variable."""
            # Act
            sample_rule_content.set_variable("max_attempts", 5)

            # Assert
            assert sample_rule_content.get_variable("max_attempts") == 5

        def test_has_variable_existing(self, sample_rule_content: RuleContent):
            """Test has_variable returns True for existing variable."""
            # Act & Assert
            assert sample_rule_content.has_variable("timeout_seconds") is True

        def test_has_variable_nonexistent(self, sample_rule_content: RuleContent):
            """Test has_variable returns False for non-existent variable."""
            # Act & Assert
            assert sample_rule_content.has_variable("nonexistent") is False

    class TestReferenceManagement:
        """Test cases for reference management methods."""

        def test_add_new_reference(self, sample_rule_content: RuleContent):
            """Test adding a new reference."""
            # Act
            sample_rule_content.add_reference("new_rules.yml")

            # Assert
            assert "new_rules.yml" in sample_rule_content.references
            assert sample_rule_content.has_reference("new_rules.yml")

        def test_add_duplicate_reference(self, sample_rule_content: RuleContent):
            """Test adding a duplicate reference doesn't create duplicates."""
            # Arrange
            original_refs = sample_rule_content.references.copy()
            
            # Act
            sample_rule_content.add_reference("common_rules.yml")  # Already exists

            # Assert
            assert sample_rule_content.references == original_refs
            assert sample_rule_content.references.count("common_rules.yml") == 1

        def test_remove_existing_reference(self, sample_rule_content: RuleContent):
            """Test removing an existing reference."""
            # Act
            sample_rule_content.remove_reference("validation_rules.yml")

            # Assert
            assert "validation_rules.yml" not in sample_rule_content.references
            assert not sample_rule_content.has_reference("validation_rules.yml")
            assert "common_rules.yml" in sample_rule_content.references  # Other refs remain

        def test_remove_nonexistent_reference(self, sample_rule_content: RuleContent):
            """Test removing a non-existent reference doesn't raise error."""
            # Arrange
            original_refs = sample_rule_content.references.copy()
            
            # Act
            sample_rule_content.remove_reference("nonexistent.yml")

            # Assert
            assert sample_rule_content.references == original_refs

        def test_has_reference_existing(self, sample_rule_content: RuleContent):
            """Test has_reference returns True for existing reference."""
            # Act & Assert
            assert sample_rule_content.has_reference("common_rules.yml") is True

        def test_has_reference_nonexistent(self, sample_rule_content: RuleContent):
            """Test has_reference returns False for non-existent reference."""
            # Act & Assert
            assert sample_rule_content.has_reference("nonexistent.yml") is False


class TestRuleInheritance:
    """Test suite for RuleInheritance domain entity."""

    @pytest.fixture
    def sample_inheritance(self) -> RuleInheritance:
        """Create a sample RuleInheritance for testing."""
        return RuleInheritance(
            parent_path="/rules/base/common.yml",
            child_path="/rules/auth/specific.yml",
            inheritance_type=InheritanceType.MERGE,
            inherited_sections=["validation", "common_rules"],
            overridden_sections=["auth_rules"],
            merged_variables={
                "timeout": 30,
                "max_retries": 3,
                "debug_mode": False
            },
            inheritance_depth=2,
            conflicts=["conflicting_rule_1"]
        )

    @pytest.fixture
    def minimal_inheritance(self) -> RuleInheritance:
        """Create minimal RuleInheritance for testing."""
        return RuleInheritance(
            parent_path="/rules/parent.yml",
            child_path="/rules/child.yml",
            inheritance_type=InheritanceType.OVERRIDE
        )

    def test_rule_inheritance_creation(self, sample_inheritance: RuleInheritance):
        """Test RuleInheritance creation with all fields."""
        # Assert
        assert sample_inheritance.parent_path == "/rules/base/common.yml"
        assert sample_inheritance.child_path == "/rules/auth/specific.yml"
        assert sample_inheritance.inheritance_type == InheritanceType.MERGE
        assert sample_inheritance.inherited_sections == ["validation", "common_rules"]
        assert sample_inheritance.overridden_sections == ["auth_rules"]
        assert sample_inheritance.merged_variables["timeout"] == 30
        assert sample_inheritance.inheritance_depth == 2
        assert sample_inheritance.conflicts == ["conflicting_rule_1"]

    def test_rule_inheritance_minimal_creation(self, minimal_inheritance: RuleInheritance):
        """Test RuleInheritance creation with minimal fields."""
        # Assert
        assert minimal_inheritance.parent_path == "/rules/parent.yml"
        assert minimal_inheritance.child_path == "/rules/child.yml"
        assert minimal_inheritance.inheritance_type == InheritanceType.OVERRIDE
        assert minimal_inheritance.inherited_sections == []  # Default
        assert minimal_inheritance.overridden_sections == []  # Default
        assert minimal_inheritance.merged_variables == {}  # Default
        assert minimal_inheritance.inheritance_depth == 0  # Default
        assert minimal_inheritance.conflicts == []  # Default

    class TestInheritedSectionManagement:
        """Test cases for inherited section management."""

        def test_add_inherited_section(self, minimal_inheritance: RuleInheritance):
            """Test adding an inherited section."""
            # Act
            minimal_inheritance.add_inherited_section("new_section")

            # Assert
            assert "new_section" in minimal_inheritance.inherited_sections
            assert minimal_inheritance.is_section_inherited("new_section")

        def test_add_duplicate_inherited_section(self, sample_inheritance: RuleInheritance):
            """Test adding a duplicate inherited section doesn't create duplicates."""
            # Arrange
            original_sections = sample_inheritance.inherited_sections.copy()
            
            # Act
            sample_inheritance.add_inherited_section("validation")  # Already exists

            # Assert
            assert sample_inheritance.inherited_sections == original_sections
            assert sample_inheritance.inherited_sections.count("validation") == 1

        def test_is_section_inherited_existing(self, sample_inheritance: RuleInheritance):
            """Test is_section_inherited returns True for existing inherited section."""
            # Act & Assert
            assert sample_inheritance.is_section_inherited("validation") is True

        def test_is_section_inherited_nonexistent(self, sample_inheritance: RuleInheritance):
            """Test is_section_inherited returns False for non-existent inherited section."""
            # Act & Assert
            assert sample_inheritance.is_section_inherited("nonexistent") is False

    class TestOverriddenSectionManagement:
        """Test cases for overridden section management."""

        def test_add_overridden_section(self, minimal_inheritance: RuleInheritance):
            """Test adding an overridden section."""
            # Act
            minimal_inheritance.add_overridden_section("new_override")

            # Assert
            assert "new_override" in minimal_inheritance.overridden_sections
            assert minimal_inheritance.is_section_overridden("new_override")

        def test_add_duplicate_overridden_section(self, sample_inheritance: RuleInheritance):
            """Test adding a duplicate overridden section doesn't create duplicates."""
            # Arrange
            original_sections = sample_inheritance.overridden_sections.copy()
            
            # Act
            sample_inheritance.add_overridden_section("auth_rules")  # Already exists

            # Assert
            assert sample_inheritance.overridden_sections == original_sections
            assert sample_inheritance.overridden_sections.count("auth_rules") == 1

        def test_is_section_overridden_existing(self, sample_inheritance: RuleInheritance):
            """Test is_section_overridden returns True for existing overridden section."""
            # Act & Assert
            assert sample_inheritance.is_section_overridden("auth_rules") is True

        def test_is_section_overridden_nonexistent(self, sample_inheritance: RuleInheritance):
            """Test is_section_overridden returns False for non-existent overridden section."""
            # Act & Assert
            assert sample_inheritance.is_section_overridden("nonexistent") is False

    class TestConflictManagement:
        """Test cases for conflict management."""

        def test_add_conflict(self, minimal_inheritance: RuleInheritance):
            """Test adding a conflict."""
            # Act
            minimal_inheritance.add_conflict("new_conflict")

            # Assert
            assert "new_conflict" in minimal_inheritance.conflicts
            assert minimal_inheritance.has_conflicts()

        def test_add_duplicate_conflict(self, sample_inheritance: RuleInheritance):
            """Test adding a duplicate conflict doesn't create duplicates."""
            # Arrange
            original_conflicts = sample_inheritance.conflicts.copy()
            
            # Act
            sample_inheritance.add_conflict("conflicting_rule_1")  # Already exists

            # Assert
            assert sample_inheritance.conflicts == original_conflicts
            assert sample_inheritance.conflicts.count("conflicting_rule_1") == 1

        def test_has_conflicts_true(self, sample_inheritance: RuleInheritance):
            """Test has_conflicts returns True when conflicts exist."""
            # Act & Assert
            assert sample_inheritance.has_conflicts() is True

        def test_has_conflicts_false(self, minimal_inheritance: RuleInheritance):
            """Test has_conflicts returns False when no conflicts exist."""
            # Act & Assert
            assert minimal_inheritance.has_conflicts() is False

    class TestMergedVariableManagement:
        """Test cases for merged variable management."""

        def test_merge_variable(self, minimal_inheritance: RuleInheritance):
            """Test merging a variable."""
            # Act
            minimal_inheritance.merge_variable("test_key", "test_value")

            # Assert
            assert minimal_inheritance.get_merged_variable("test_key") == "test_value"

        def test_merge_variable_overwrite(self, sample_inheritance: RuleInheritance):
            """Test merging a variable overwrites existing value."""
            # Act
            sample_inheritance.merge_variable("timeout", 60)

            # Assert
            assert sample_inheritance.get_merged_variable("timeout") == 60

        def test_get_merged_variable_existing(self, sample_inheritance: RuleInheritance):
            """Test getting an existing merged variable."""
            # Act & Assert
            assert sample_inheritance.get_merged_variable("max_retries") == 3
            assert sample_inheritance.get_merged_variable("debug_mode") is False

        def test_get_merged_variable_with_default(self, sample_inheritance: RuleInheritance):
            """Test getting a non-existent merged variable with default."""
            # Act & Assert
            assert sample_inheritance.get_merged_variable("nonexistent", "default") == "default"

        def test_get_merged_variable_without_default(self, sample_inheritance: RuleInheritance):
            """Test getting a non-existent merged variable without default returns None."""
            # Act & Assert
            assert sample_inheritance.get_merged_variable("nonexistent") is None


# Integration tests for realistic scenarios
class TestRuleEntitiesIntegration:
    """Integration tests for rule entities working together."""

    def test_rule_content_with_inheritance(self):
        """Test RuleContent working with RuleInheritance."""
        # Arrange
        parent_metadata = RuleMetadata(
            path="/rules/base.yml",
            format=RuleFormat.YAML,
            type=RuleType.BUSINESS,
            size=512,
            modified=1640995200.0,
            checksum="parent123",
            dependencies=[]
        )

        parent_content = RuleContent(
            metadata=parent_metadata,
            raw_content="base: rules",
            parsed_content={"base": "rules"},
            sections={"common": "shared rules"},
            references=[],
            variables={"base_timeout": 30}
        )

        child_metadata = RuleMetadata(
            path="/rules/child.yml",
            format=RuleFormat.YAML,
            type=RuleType.BUSINESS,
            size=256,
            modified=1640995300.0,
            checksum="child123",
            dependencies=["base.yml"]
        )

        child_content = RuleContent(
            metadata=child_metadata,
            raw_content="child: specific rules",
            parsed_content={"child": "specific rules"},
            sections={"specific": "child rules"},
            references=["base.yml"],
            variables={"child_timeout": 60}
        )

        inheritance = RuleInheritance(
            parent_path=parent_content.rule_path,
            child_path=child_content.rule_path,
            inheritance_type=InheritanceType.MERGE,
            inheritance_depth=1
        )

        # Act - Simulate inheritance processing
        inheritance.add_inherited_section("common")
        inheritance.add_overridden_section("specific")
        inheritance.merge_variable("base_timeout", parent_content.get_variable("base_timeout"))
        inheritance.merge_variable("child_timeout", child_content.get_variable("child_timeout"))

        # Assert
        assert inheritance.is_section_inherited("common")
        assert inheritance.is_section_overridden("specific")
        assert inheritance.get_merged_variable("base_timeout") == 30
        assert inheritance.get_merged_variable("child_timeout") == 60
        assert not inheritance.has_conflicts()

    def test_complex_rule_hierarchy(self):
        """Test complex rule hierarchy with multiple levels."""
        # Arrange - Create a 3-level hierarchy
        rules_data = [
            ("/rules/global.yml", "global", {"global_var": "global_value"}),
            ("/rules/domain/auth.yml", "auth", {"auth_var": "auth_value", "global_var": "overridden"}),
            ("/rules/domain/auth/jwt.yml", "jwt", {"jwt_var": "jwt_value"})
        ]

        rule_contents = []
        inheritances = []

        # Create rule contents
        for path, content_type, variables in rules_data:
            metadata = RuleMetadata(
                path=path,
                format=RuleFormat.YAML,
                type=RuleType.BUSINESS,
                size=len(path),
                modified=1640995200.0,
                checksum=f"checksum_{content_type}",
                dependencies=[]
            )

            rule_content = RuleContent(
                metadata=metadata,
                raw_content=f"{content_type}: rules",
                parsed_content={content_type: "rules"},
                sections={content_type: f"{content_type} rules"},
                references=[],
                variables=variables
            )
            rule_contents.append(rule_content)

        # Create inheritance relationships
        # global <- auth
        auth_inheritance = RuleInheritance(
            parent_path=rule_contents[0].rule_path,
            child_path=rule_contents[1].rule_path,
            inheritance_type=InheritanceType.MERGE,
            inheritance_depth=1
        )
        auth_inheritance.add_inherited_section("global")
        auth_inheritance.merge_variable("global_var", "overridden")  # Override
        auth_inheritance.merge_variable("auth_var", "auth_value")
        auth_inheritance.add_conflict("global_var")  # Mark conflict

        # auth <- jwt
        jwt_inheritance = RuleInheritance(
            parent_path=rule_contents[1].rule_path,
            child_path=rule_contents[2].rule_path,
            inheritance_type=InheritanceType.MERGE,
            inheritance_depth=2
        )
        jwt_inheritance.add_inherited_section("global")
        jwt_inheritance.add_inherited_section("auth")
        jwt_inheritance.merge_variable("global_var", "overridden")  # From auth
        jwt_inheritance.merge_variable("auth_var", "auth_value")  # From auth
        jwt_inheritance.merge_variable("jwt_var", "jwt_value")  # Own

        inheritances.extend([auth_inheritance, jwt_inheritance])

        # Assert - Test the hierarchy
        assert len(rule_contents) == 3
        assert len(inheritances) == 2

        # Test auth level
        assert auth_inheritance.has_conflicts()
        assert auth_inheritance.inheritance_depth == 1
        assert auth_inheritance.get_merged_variable("global_var") == "overridden"

        # Test jwt level (deepest)
        assert jwt_inheritance.inheritance_depth == 2
        assert jwt_inheritance.is_section_inherited("global")
        assert jwt_inheritance.is_section_inherited("auth")
        assert jwt_inheritance.get_merged_variable("jwt_var") == "jwt_value"
        assert len(jwt_inheritance.merged_variables) == 3