# DDD Architecture Audit - Detailed Requirements

## Objective
Perform comprehensive Domain-Driven Design (DDD) architecture audit to identify ALL code violating DDD principles and layer boundaries.

## Scope - Complete System Review

### 1. Domain Layer Analysis
**Location**: `agenthub_main/src/fastmcp/task_management/domain/`

**Entities** (`entities/*.py`):
- Check: Do entities contain ANY infrastructure/persistence logic?
- Check: Are all business rules in entity methods?
- Check: Are entities using ORM decorators or database-specific code?
- Check: Do entities depend on repositories or external services?

**Value Objects** (`value_objects/*.py`):
- Check: Are value objects immutable?
- Check: Do they have identity-based equality or value-based?
- Check: Are they free from infrastructure concerns?

**Domain Services** (`services/*.py`):
- Check: Do they orchestrate multiple entities/aggregates?
- Check: Are they stateless?
- Check: Do they depend on infrastructure?

**Repository Interfaces** (`repositories/*.py`):
- Check: Are these ONLY interfaces/abstract classes?
- Check: No implementation details should exist here
- Check: Return domain entities, not ORM models

### 2. Application Layer Analysis
**Location**: `agenthub_main/src/fastmcp/task_management/application/`

**Use Cases** (`use_cases/*.py`):
- Check: Do they orchestrate domain operations?
- Check: Are they depending directly on ORM models?
- Check: Do they contain business logic (should be in domain)?
- Check: Are they calling infrastructure directly instead of through ports?

**Services** (`services/*.py`):
- Check: Proper delegation to domain layer?
- Check: No business logic here?
- Check: Using repository interfaces, not implementations?

**DTOs** (`dtos/*.py`):
- Check: Are these ONLY data transfer objects?
- Check: No business logic?
- Check: No domain entity mixing?

### 3. Infrastructure Layer Analysis
**Location**: `agenthub_main/src/fastmcp/task_management/infrastructure/`

**Repositories** (`repositories/orm/*.py`):
- Check: Do they properly convert ORM ↔ Domain Entity?
- Check: Like agent_repository.py bug - are there others calling domain methods on ORM models?
- Check: Are they returning domain entities, not ORM models?
- Check: Is `_model_to_entity()` complete for ALL entity fields?
- Check: Is `_entity_to_model_dict()` complete for ALL entity fields?

**Database Models** (`database/models.py`):
- Check: Are ORM models kept separate from domain entities?
- Check: No business logic in ORM models?
- Check: Proper table/column naming?

**External Services**:
- Check: Properly isolated behind interfaces?
- Check: Not leaking into domain layer?

### 4. Interface Layer Analysis
**Location**: `agenthub_main/src/fastmcp/task_management/interface/`

**MCP Controllers** (`mcp/controllers/*.py`):
- Check: Are they thin - just routing and validation?
- Check: Delegating to application services?
- Check: Not containing business logic?
- Check: Proper error handling without exposing internals?

## Anti-Patterns to Identify

### Anti-Pattern 1: Domain Logic in Repository
**Example**: agent_repository.py was manipulating ORM models directly
**Search for**:
- Repositories that directly modify ORM model fields without converting to entity
- Repositories implementing business rules instead of delegating to entities
- Repositories calling `save()` on ORM models instead of entities

### Anti-Pattern 2: Incomplete Entity Conversion
**Example**: agent_repository.py `_model_to_entity()` wasn't extracting assigned_trees
**Check for EACH repository**:
- `_model_to_entity()` extracts ALL fields from model_metadata and direct fields
- `_entity_to_model_dict()` includes ALL entity fields
- Round-trip conversion works: Entity → ORM → Entity preserves all data

### Anti-Pattern 3: Business Logic in Application Layer
**Check use cases and application services**:
- Implementing validation (should be in domain entities)
- Calculating business metrics (should be in domain services)
- Enforcing business rules (should be in entities)

### Anti-Pattern 4: Infrastructure Leaking into Domain
**Check domain entities**:
- Import SQLAlchemy or ORM types
- Import repository implementations (should use interfaces only)
- Depend on external service implementations

### Anti-Pattern 5: Anemic Domain Model
**Check entities**:
- Have only getters/setters with no business methods
- All logic is in services instead of entities
- Are basically data containers

### Anti-Pattern 6: Circular Dependencies
**Check import chains**:
- Domain importing from infrastructure
- Application importing from interface
- Any circular import patterns

## Output Document Structure

**File**: `ai_docs/code-quality/ddd-architecture-audit-2025-10-08.md`

### Required Sections:

#### 1. Executive Summary
- Total violations found (count by severity)
- Most critical violations
- Overall architecture health score
- Quick stats table

#### 2. Domain Layer Violations
For EACH violation:
- **File**: exact file path with line numbers
- **Violation Type**: specific anti-pattern name
- **Current Code**: code snippet showing the problem
- **Why It's Wrong**: DDD principle violated
- **Recommended Fix**: specific code changes
- **Impact**: consequences if not fixed
- **Priority**: Critical/High/Medium/Low

#### 3. Application Layer Violations
Same format as domain layer

#### 4. Infrastructure Layer Violations
Same format, focus on repository patterns

#### 5. Interface Layer Violations
Same format

#### 6. Cross-Cutting Concerns
Violations spanning multiple layers

#### 7. Dependency Direction Analysis
```
✓ Domain → (nothing)
✓ Application → Domain
✓ Infrastructure → Domain + Application
✓ Interface → Application
✗ Any violations of above
```

#### 8. Prioritized Fix Roadmap

**Critical** (breaks architecture fundamentally):
- List violations that cause bugs or prevent scaling
- Must fix before next release

**High** (causes maintenance issues):
- List violations creating technical debt
- Should fix in next sprint

**Medium** (code smells):
- List violations affecting code quality
- Plan to fix in next month

**Low** (consistency):
- List minor improvements
- Fix when touching related code

#### 9. Repository Conversion Completeness Matrix

| Repository | _model_to_entity | _entity_to_model_dict | Round-trip Works | Issues |
|------------|------------------|----------------------|------------------|--------|
| AgentRepository | ✅ FIXED | ✅ | ✅ | Fixed in this session |
| TaskRepository | ? | ? | ? | To be checked |
| ProjectRepository | ? | ? | ? | To be checked |
| ... | ... | ... | ... | ... |

#### 10. Recommendations
- Architectural patterns to adopt
- Refactoring strategies
- Testing strategies for fixes
- Code review checklist for future changes

## Files to Review (Minimum)

### Domain Layer
```
domain/entities/*.py (ALL entity files)
domain/value_objects/*.py (ALL value objects)
domain/repositories/*.py (ALL interfaces)
domain/services/*.py (ALL domain services)
domain/events/*.py (ALL events)
```

### Application Layer
```
application/use_cases/*.py (ALL use cases)
application/services/*.py (ALL app services)
application/dtos/*.py (ALL DTOs)
```

### Infrastructure Layer
```
infrastructure/repositories/orm/*.py (ALL repositories - CRITICAL)
infrastructure/database/models.py
infrastructure/repositories/base*.py
```

### Interface Layer
```
interface/mcp/controllers/*.py (ALL controllers)
```

## Success Criteria
- ✅ Every layer reviewed systematically
- ✅ Every repository checked for conversion completeness
- ✅ All violations documented with file:line references
- ✅ Every violation has recommended fix
- ✅ Violations prioritized for remediation
- ✅ Document is actionable and specific
- ✅ Includes before/after code examples
- ✅ Provides testing strategy for fixes

## Audit Methodology

1. **Discovery Phase**:
   - Use Grep to search for anti-patterns
   - Check all import statements for layer violations
   - List all repository files

2. **Analysis Phase**:
   - Read each suspicious file
   - Document violations with context
   - Categorize by severity

3. **Documentation Phase**:
   - Create structured report
   - Include code examples
   - Provide fix recommendations

4. **Validation Phase**:
   - Verify all files reviewed
   - Check completeness of recommendations
   - Ensure actionable fixes

## Expected Findings

Based on agent_repository.py bug, likely to find:
- ✗ Other repositories with incomplete `_model_to_entity()` conversions
- ✗ Repositories manipulating ORM models directly
- ✗ Business logic scattered in application/infrastructure layers
- ✗ Mixed concerns in controllers
- ✗ Circular dependencies
- ✗ Anemic domain models
- ✗ Infrastructure leaking into domain

## Time Estimate
- Domain layer review: 2-3 hours
- Application layer review: 1-2 hours
- Infrastructure layer review: 3-4 hours (most complex)
- Interface layer review: 1-2 hours
- Documentation: 2-3 hours
- **Total**: 9-14 hours

## References
- agent_repository.py fix (lines 157-191, 480-508, 540-566)
- agent.py domain methods (lines 142-157)
- Clean Architecture by Robert C. Martin
- Domain-Driven Design by Eric Evans
