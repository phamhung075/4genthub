# DhafnckMCP Test Creation Guide - DDD Architecture

## Executive Summary

Based on comprehensive analysis of the DhafnckMCP codebase, **613 source files** have been analyzed with only **19.1% test coverage**. This guide provides prioritized recommendations for creating unit tests focusing on Domain-Driven Design (DDD) layers.

### Current Coverage by DDD Layer:
- **Domain**: 51.1% (47/92 files) 🟡 - NEEDS IMPROVEMENT
- **Application**: 21.8% (32/147 files) 🔴 - CRITICAL GAP
- **Infrastructure**: 23.7% (22/93 files) 🔴 - CRITICAL GAP  
- **Interface**: 3.3% (6/184 files) 🔴 - LOWEST PRIORITY FOR UNIT TESTS

## 🎯 Strategic Priority: Domain Layer First

### Why Domain Layer Testing is Critical:
1. **Business Logic Core**: Contains essential business rules and invariants
2. **High ROI**: Domain entities and value objects are stable and provide maximum testing value
3. **Foundation**: Other layers depend on domain correctness
4. **Low Dependencies**: Domain objects are easier to test in isolation

## 🔥 Top 10 Critical Files Needing Tests

### 1. Rule Value Objects (`fastmcp/task_management/domain/value_objects/rule_value_objects.py`)
**Priority: 130 | 7 classes, 28 methods | 219 LOC**

**Test File**: `dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/value_objects/rule_value_objects_test.py`

```python
# Test Template
import pytest
from fastmcp.task_management.domain.value_objects.rule_value_objects import (
    RuleFormat, RuleType, ConflictResolution, RuleMetadata
)

class TestRuleFormat:
    def test_enum_values(self):
        """Test RuleFormat enum has expected values"""
        assert RuleFormat.MDC.value == "mdc"
        assert RuleFormat.JSON.value == "json"
        # Test all enum values
        
class TestRuleMetadata:
    def test_creation_with_valid_data(self):
        """Test RuleMetadata creation with valid data"""
        metadata = RuleMetadata(
            path="/test/rule.md",
            format=RuleFormat.MD,
            type=RuleType.TASK,
            size=1024,
            modified=1640995200.0,
            checksum="abc123"
        )
        assert metadata.path == "/test/rule.md"
        assert metadata.format == RuleFormat.MD
        
    def test_modified_datetime_property(self):
        """Test modified_datetime property conversion"""
        metadata = RuleMetadata(...)
        datetime_obj = metadata.modified_datetime
        assert isinstance(datetime_obj, datetime)
```

### 2. Workflow Hints (`fastmcp/task_management/domain/value_objects/hints.py`)
**Priority: 128 | 5 classes, 11 methods | 196 LOC**

```python
# Test Template
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastmcp.task_management.domain.value_objects.hints import (
    HintType, HintPriority, HintMetadata, WorkflowHint, HintCollection
)

class TestHintMetadata:
    def test_confidence_validation(self):
        """Test confidence score validation"""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            HintMetadata(
                source="test",
                confidence=1.5,  # Invalid
                reasoning="test"
            )
            
    def test_valid_metadata_creation(self):
        """Test valid metadata creation"""
        metadata = HintMetadata(
            source="vision_system",
            confidence=0.85,
            reasoning="Task blocked on dependency"
        )
        assert metadata.confidence == 0.85

class TestWorkflowHint:
    def test_create_factory_method(self):
        """Test WorkflowHint.create factory method"""
        task_id = uuid4()
        metadata = HintMetadata(
            source="test", 
            confidence=0.9, 
            reasoning="test"
        )
        
        hint = WorkflowHint.create(
            task_id=task_id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Complete dependency first",
            suggested_action="Review task X",
            metadata=metadata
        )
        
        assert hint.task_id == task_id
        assert hint.type == HintType.NEXT_ACTION
        assert isinstance(hint.id, UUID)
        
    def test_is_expired(self):
        """Test hint expiration logic"""
        # Test non-expiring hint
        hint = WorkflowHint.create(...)
        assert not hint.is_expired()
        
        # Test expired hint
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_hint = WorkflowHint.create(..., expires_at=past_time)
        assert expired_hint.is_expired()

class TestHintCollection:
    def test_add_hint_validation(self):
        """Test hint collection validates task_id match"""
        task_id = uuid4()
        collection = HintCollection(task_id=task_id)
        
        wrong_task_hint = WorkflowHint.create(
            task_id=uuid4(),  # Different task_id
            ...
        )
        
        with pytest.raises(ValueError, match="Hint task_id must match collection task_id"):
            collection.add_hint(wrong_task_hint)
```

### 3. Rule Content Entity (`fastmcp/task_management/domain/entities/rule_content.py`)
**Priority: 124 | 9 classes, 2 methods | 88 LOC**

```python
# Test Template
import pytest
from fastmcp.task_management.domain.entities.rule_content import (
    RuleFormat, RuleType, RuleMetadata, RuleContent, ConflictResolution
)

class TestRuleContent:
    def test_creation_with_valid_data(self):
        """Test RuleContent creation with valid data"""
        metadata = RuleMetadata(
            path="/test.md",
            format=RuleFormat.MD,
            type=RuleType.TASK,
            size=100,
            modified=1640995200.0,
            checksum="abc123"
        )
        
        rule_content = RuleContent(
            metadata=metadata,
            raw_content="# Test Rule",
            parsed_content={"title": "Test Rule"},
            sections={"header": "Test"},
            references=[],
            variables={}
        )
        
        assert rule_content.metadata == metadata
        assert rule_content.raw_content == "# Test Rule"
        
    def test_post_init_validation_empty_content(self):
        """Test post_init validation for empty content"""
        metadata = RuleMetadata(...)
        
        with pytest.raises(ValueError, match="Rule content cannot be empty"):
            RuleContent(
                metadata=metadata,
                raw_content="",  # Empty content should fail
                parsed_content={},
                sections={},
                references=[],
                variables={}
            )
            
    def test_post_init_validation_missing_metadata(self):
        """Test post_init validation for missing metadata"""
        with pytest.raises(ValueError, match="Rule metadata is required"):
            RuleContent(
                metadata=None,
                raw_content="content",
                parsed_content={},
                sections={},
                references=[],
                variables={}
            )
```

## 🚀 Quick Win Files (Easy Targets)

### Domain Value Objects - Start Here:
1. **Context Enums** - Simple enum testing
2. **Compliance Objects** - Data validation logic
3. **Agent Value Objects** - Agent coordination data

### Test Creation Commands (Copy & Run):

```bash
# Create test directories
mkdir -p dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/value_objects
mkdir -p dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/entities
mkdir -p dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/services
mkdir -p dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/repositories

# Create high-priority test files
touch dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/value_objects/rule_value_objects_test.py
touch dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/value_objects/hints_test.py
touch dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/entities/rule_content_test.py
touch dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/value_objects/compliance_objects_test.py
touch dhafnck_mcp_main/src/tests/unit/fastmcp/task_management/domain/repositories/rule_repository_test.py
```

## 📋 Domain Layer Test Patterns

### 1. Entity Testing Pattern
```python
class TestDomainEntity:
    def test_creation_with_valid_data(self):
        """Test entity creation with valid data"""
        pass
        
    def test_validation_rules(self):
        """Test business validation rules"""
        pass
        
    def test_invariants(self):
        """Test domain invariants are maintained"""
        pass
        
    def test_equality_and_hashing(self):
        """Test entity identity and equality"""
        pass
```

### 2. Value Object Testing Pattern
```python
class TestValueObject:
    def test_immutability(self):
        """Test value object is immutable"""
        pass
        
    def test_equality_by_value(self):
        """Test equality is based on values, not identity"""
        pass
        
    def test_validation_constraints(self):
        """Test value constraints are enforced"""
        pass
        
    def test_serialization(self):
        """Test to/from dict conversion"""
        pass
```

### 3. Repository Interface Testing Pattern
```python
class TestRepositoryInterface:
    def test_method_signatures(self):
        """Test repository interface methods are properly defined"""
        pass
        
    def test_abstract_methods(self):
        """Test abstract methods raise NotImplementedError"""
        pass
```

## 🔄 Application Layer Testing Strategy

### Use Cases (Priority: High)
- **Focus**: Business workflow orchestration
- **Test Approach**: Mock domain services and repositories
- **Coverage Goal**: 70%

### Facades (Priority: High)  
- **Focus**: Application service coordination
- **Test Approach**: Integration tests with real domain objects
- **Coverage Goal**: 70%

## 🔌 Infrastructure Layer Testing Strategy

### Repositories (Priority: Medium)
- **Focus**: Data access correctness
- **Test Approach**: In-memory implementations and mocks
- **Coverage Goal**: 60%

### ORM Models (Priority: Medium)
- **Focus**: Entity mapping and relationships
- **Test Approach**: Database integration tests
- **Coverage Goal**: 60%

## 🌐 Interface Layer Testing Strategy

### Controllers (Priority: Low for Unit Tests)
- **Recommendation**: Focus on integration tests instead
- **Unit Test Coverage Goal**: 40%
- **Integration Test Coverage Goal**: 80%

## 📊 Testing Tools and Framework

### Recommended Test Stack:
```python
# test_requirements.txt additions
pytest>=7.0.0
pytest-asyncio>=0.21.0  
pytest-mock>=3.10.0
pytest-cov>=4.0.0
factory-boy>=3.2.0      # For test data factories
faker>=18.0.0           # For fake data generation
```

### Test Configuration:
```python
# pytest.ini
[tool:pytest]
testpaths = dhafnck_mcp_main/src/tests
python_files = *test*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=dhafnck_mcp_main/src/fastmcp
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=50
```

## 🎯 Success Metrics

### Target Coverage by Layer:
- **Domain**: 80% (currently 51.1%)
- **Application**: 70% (currently 21.8%)  
- **Infrastructure**: 60% (currently 23.7%)
- **Interface**: 40% (currently 3.3%)

### Milestones:
1. **Week 1**: Complete top 10 domain value objects and entities
2. **Week 2**: Add domain services and repository interfaces
3. **Week 3**: Focus on application use cases and facades
4. **Week 4**: Infrastructure repositories and data access

## 💡 Best Practices

### 1. Test Naming Convention:
- `test_creation_with_valid_data`
- `test_validation_with_invalid_data`
- `test_business_logic_method_name`

### 2. Test Organization:
```
tests/unit/
├── fastmcp/
│   ├── task_management/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   ├── services/
│   │   │   └── repositories/
│   │   ├── application/
│   │   └── infrastructure/
│   └── connection_management/
```

### 3. Mock Strategy:
- **Domain Layer**: Minimal mocking (pure domain objects)
- **Application Layer**: Mock repositories and external services
- **Infrastructure Layer**: Mock external systems (databases, APIs)

### 4. Test Data Management:
```python
# Use factory pattern for test data
from factory import Factory, Faker, SubFactory

class RuleMetadataFactory(Factory):
    class Meta:
        model = RuleMetadata
    
    path = Faker('file_path')
    format = RuleFormat.MD
    type = RuleType.TASK
    size = Faker('random_int', min=1, max=10000)
    modified = Faker('unix_time')
    checksum = Faker('md5')
```

## 🚀 Implementation Plan

### Phase 1: Domain Foundation (Days 1-7)
1. Create test infrastructure and patterns
2. Test top 10 domain value objects
3. Test critical domain entities
4. Establish test data factories

### Phase 2: Domain Services (Days 8-14)  
1. Test domain services
2. Test repository interfaces
3. Test domain events
4. Add domain exception testing

### Phase 3: Application Layer (Days 15-21)
1. Test use cases with mocked dependencies
2. Test application facades
3. Test event handlers
4. Add application service testing

### Phase 4: Infrastructure (Days 22-28)
1. Test repository implementations
2. Test database models and migrations
3. Test external service integrations
4. Add factory and builder pattern tests

This guide provides a systematic approach to achieving comprehensive test coverage while respecting DDD architecture principles. Start with domain layer tests for maximum ROI and build upward through the layers.