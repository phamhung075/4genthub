# DDD Refactoring Implementation Plan - Zero Breaking Changes Strategy

## Document Overview

**Purpose**: Comprehensive technical implementation plan for DDD compliance refactoring with ZERO breaking changes
**Strategy**: Strangler Fig Pattern + Feature Toggles + Parallel Implementation
**Application Status**: WORKING CORRECTLY - Must maintain all functionality
**Review Base**: `ai_docs/reports-status/ddd-compliance-review-2025-10-09.md`

**Violations Summary**:
- **Critical**: 5 violations
- **High**: 8 violations
- **Medium**: 7 violations
- **Low**: 3 violations
- **Total**: 23 violations

---

## Core Principles

### 1. Strangler Fig Pattern
**Concept**: New code grows around old code, gradually replacing it
- Build new implementation alongside old
- Redirect traffic gradually via feature flags
- Remove old code only when 100% confident
- Always have working fallback

### 2. Feature Toggle Pattern
**Concept**: Runtime switches control which implementation executes
- Environment variable: `DDD_REFACTOR_ENABLED=true/false`
- Per-feature flags: `USE_NEW_ORCHESTRATOR`, `USE_RICH_CONTEXT_MODEL`, etc.
- Default: `false` (old implementation) until proven
- Easy rollback: flip flag back to `false`

### 3. Adapter Pattern for Compatibility
**Concept**: Bridge between old and new interfaces
- Old code calls adapter → adapter calls new code
- New code uses new patterns internally
- External interfaces unchanged
- Transparent to MCP tool signatures

### 4. Parallel Testing Strategy
**Concept**: Both implementations run, results compared
- Shadow mode: Run both, use old results, log differences
- Validation mode: Run both, fail if results differ
- Cutover mode: Use new results, log if old differs
- Remove old: Delete old code after confidence period

---

## Phase Structure Overview

### Phase 1: Foundation & Infrastructure (Week 1-2)
**Goal**: Set up refactoring infrastructure without breaking anything
**Violations**: 0 direct fixes, pure foundation
**Confidence**: 100% - No code changes

### Phase 2: Low-Risk Application Layer (Week 3-4)
**Goal**: Fix application layer issues with minimal risk
**Violations**: Medium #3, High #3, Low #1
**Confidence**: 95% - Isolated changes

### Phase 3: Infrastructure Improvements (Week 5-7)
**Goal**: Fix infrastructure with session management improvements
**Violations**: Critical #3, Critical #4, Medium #5
**Confidence**: 90% - With comprehensive testing

### Phase 4: Domain Enrichment (Week 8-10)
**Goal**: Enrich domain models without breaking serialization
**Violations**: Critical #1, High #2, Medium #1, Medium #2
**Confidence**: 85% - Requires careful serialization handling

### Phase 5: Controller Refactoring (Week 11-13)
**Goal**: Thin controllers without changing MCP signatures
**Violations**: Critical #5, High #5, High #6, Medium #6
**Confidence**: 90% - External interface unchanged

### Phase 6: Domain Service Relocation (Week 14-15)
**Goal**: Move orchestrator to application layer
**Violations**: Critical #2
**Confidence**: 95% - Well-isolated change

### Phase 7: Cross-Cutting Concerns (Week 16-17)
**Goal**: Fix dependency directions and aggregate boundaries
**Violations**: High #7, High #8, Medium #7
**Confidence**: 85% - Architectural improvements

### Phase 8: Cleanup & Documentation (Week 18)
**Goal**: Remove old code, finalize documentation
**Violations**: Low #2, Low #3
**Confidence**: 100% - Documentation only

---

## Phase 1: Foundation & Infrastructure (Week 1-2)

### Goals
- ✅ Set up feature flag system
- ✅ Create testing infrastructure for parallel execution
- ✅ Establish rollback procedures
- ✅ Create monitoring/logging for refactoring
- ✅ Zero code changes to business logic

### Feature Flag System Setup

#### Step 1.1: Create Feature Flag Configuration
**File**: `agenthub_main/src/fastmcp/shared/config/feature_flags.py` (NEW)

```python
"""
Feature flag system for DDD refactoring.
Allows gradual rollout with instant rollback capability.
"""
import os
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class FeatureFlags:
    """
    Feature flags for DDD refactoring phases.
    All default to False for safety - old implementations remain active.
    """

    # Master switch - must be True to enable any refactoring
    ddd_refactor_enabled: bool = field(
        default_factory=lambda: os.getenv("DDD_REFACTOR_ENABLED", "false").lower() == "true"
    )

    # Phase 3: Infrastructure improvements
    use_unit_of_work: bool = field(
        default_factory=lambda: os.getenv("USE_UNIT_OF_WORK", "false").lower() == "true"
    )
    use_new_session_management: bool = field(
        default_factory=lambda: os.getenv("USE_NEW_SESSION_MANAGEMENT", "false").lower() == "true"
    )

    # Phase 4: Domain enrichment
    use_rich_context_model: bool = field(
        default_factory=lambda: os.getenv("USE_RICH_CONTEXT_MODEL", "false").lower() == "true"
    )
    use_context_serializer: bool = field(
        default_factory=lambda: os.getenv("USE_CONTEXT_SERIALIZER", "false").lower() == "true"
    )

    # Phase 5: Controller refactoring
    use_parameter_normalizer: bool = field(
        default_factory=lambda: os.getenv("USE_PARAMETER_NORMALIZER", "false").lower() == "true"
    )
    use_authorization_service: bool = field(
        default_factory=lambda: os.getenv("USE_AUTHORIZATION_SERVICE", "false").lower() == "true"
    )

    # Phase 6: Orchestrator relocation
    use_new_orchestrator: bool = field(
        default_factory=lambda: os.getenv("USE_NEW_ORCHESTRATOR", "false").lower() == "true"
    )

    # Testing modes
    shadow_mode: bool = field(
        default_factory=lambda: os.getenv("DDD_SHADOW_MODE", "false").lower() == "true"
    )  # Run both, use old, log differences
    validation_mode: bool = field(
        default_factory=lambda: os.getenv("DDD_VALIDATION_MODE", "false").lower() == "true"
    )  # Run both, fail if different

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a specific feature flag is enabled."""
        if not self.ddd_refactor_enabled:
            return False  # Master switch off - all flags disabled
        return getattr(self, flag_name, False)

    def to_dict(self) -> Dict[str, Any]:
        """Export all flags as dictionary."""
        return {
            "ddd_refactor_enabled": self.ddd_refactor_enabled,
            "use_unit_of_work": self.use_unit_of_work,
            "use_new_session_management": self.use_new_session_management,
            "use_rich_context_model": self.use_rich_context_model,
            "use_context_serializer": self.use_context_serializer,
            "use_parameter_normalizer": self.use_parameter_normalizer,
            "use_authorization_service": self.use_authorization_service,
            "use_new_orchestrator": self.use_new_orchestrator,
            "shadow_mode": self.shadow_mode,
            "validation_mode": self.validation_mode,
        }


# Global feature flags instance
_feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    return _feature_flags


def reload_feature_flags() -> FeatureFlags:
    """Reload feature flags from environment (useful for testing)."""
    global _feature_flags
    _feature_flags = FeatureFlags()
    return _feature_flags
```

**Testing**: No business logic changes, pure configuration

---

#### Step 1.2: Create Parallel Execution Framework
**File**: `agenthub_main/src/fastmcp/shared/refactoring/parallel_executor.py` (NEW)

```python
"""
Parallel execution framework for DDD refactoring.
Supports shadow mode and validation mode.
"""
import logging
from typing import Callable, Any, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import traceback

from ..config.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of parallel execution."""
    old_result: Any
    new_result: Any
    old_error: Optional[Exception] = None
    new_error: Optional[Exception] = None
    results_match: bool = False
    differences: Optional[Dict[str, Any]] = None


class ParallelExecutor:
    """
    Execute old and new implementations in parallel for validation.

    Modes:
    - Shadow: Run both, use old result, log differences
    - Validation: Run both, fail if results differ
    - Normal: Use feature flag to decide which to run
    """

    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self.flags = get_feature_flags()

    def execute(
        self,
        old_impl: Callable,
        new_impl: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute implementation(s) based on feature flags.

        Returns: Result from active implementation
        Raises: Exception if validation mode fails
        """
        # Check if new implementation should be used
        use_new = self.flags.is_enabled(self.feature_name)

        # Shadow mode: Run both, use old, log differences
        if self.flags.shadow_mode:
            return self._execute_shadow(old_impl, new_impl, *args, **kwargs)

        # Validation mode: Run both, fail if different
        if self.flags.validation_mode:
            return self._execute_validation(old_impl, new_impl, *args, **kwargs)

        # Normal mode: Use flag to decide
        if use_new:
            logger.info(f"Using NEW implementation for {self.feature_name}")
            return new_impl(*args, **kwargs)
        else:
            logger.debug(f"Using OLD implementation for {self.feature_name}")
            return old_impl(*args, **kwargs)

    def _execute_shadow(
        self,
        old_impl: Callable,
        new_impl: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Shadow mode: Run both, use old result, log differences."""
        old_result = None
        new_result = None
        old_error = None
        new_error = None

        # Execute old implementation
        try:
            old_result = old_impl(*args, **kwargs)
        except Exception as e:
            old_error = e
            logger.error(f"Old implementation error in {self.feature_name}: {e}")

        # Execute new implementation
        try:
            new_result = new_impl(*args, **kwargs)
        except Exception as e:
            new_error = e
            logger.error(f"New implementation error in {self.feature_name}: {e}")

        # Compare results
        exec_result = self._compare_results(old_result, new_result, old_error, new_error)

        # Log differences
        if not exec_result.results_match:
            logger.warning(
                f"Shadow mode difference detected in {self.feature_name}:\n"
                f"Differences: {json.dumps(exec_result.differences, indent=2)}"
            )
        else:
            logger.info(f"Shadow mode: Results match for {self.feature_name}")

        # Always use old result in shadow mode
        if old_error:
            raise old_error
        return old_result

    def _execute_validation(
        self,
        old_impl: Callable,
        new_impl: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Validation mode: Run both, fail if results differ."""
        old_result = None
        new_result = None
        old_error = None
        new_error = None

        # Execute both implementations
        try:
            old_result = old_impl(*args, **kwargs)
        except Exception as e:
            old_error = e

        try:
            new_result = new_impl(*args, **kwargs)
        except Exception as e:
            new_error = e

        # Compare results
        exec_result = self._compare_results(old_result, new_result, old_error, new_error)

        # Fail if results don't match
        if not exec_result.results_match:
            raise AssertionError(
                f"Validation failed for {self.feature_name}:\n"
                f"Differences: {json.dumps(exec_result.differences, indent=2)}"
            )

        # Use new result if validation passes
        if new_error:
            raise new_error
        return new_result

    def _compare_results(
        self,
        old_result: Any,
        new_result: Any,
        old_error: Optional[Exception],
        new_error: Optional[Exception]
    ) -> ExecutionResult:
        """Compare old and new results."""
        differences = {}

        # Both errored
        if old_error and new_error:
            if type(old_error) != type(new_error):
                differences["error_type"] = {
                    "old": type(old_error).__name__,
                    "new": type(new_error).__name__
                }
            results_match = type(old_error) == type(new_error)

        # One errored, one succeeded
        elif old_error or new_error:
            differences["error_mismatch"] = {
                "old_errored": old_error is not None,
                "new_errored": new_error is not None
            }
            results_match = False

        # Both succeeded - compare results
        else:
            results_match, differences = self._deep_compare(old_result, new_result)

        return ExecutionResult(
            old_result=old_result,
            new_result=new_result,
            old_error=old_error,
            new_error=new_error,
            results_match=results_match,
            differences=differences if differences else None
        )

    def _deep_compare(self, old: Any, new: Any) -> Tuple[bool, Dict[str, Any]]:
        """Deep comparison of results."""
        differences = {}

        # Type mismatch
        if type(old) != type(new):
            differences["type_mismatch"] = {
                "old": type(old).__name__,
                "new": type(new).__name__
            }
            return False, differences

        # Dict comparison
        if isinstance(old, dict):
            old_keys = set(old.keys())
            new_keys = set(new.keys())

            if old_keys != new_keys:
                differences["keys"] = {
                    "missing_in_new": list(old_keys - new_keys),
                    "extra_in_new": list(new_keys - old_keys)
                }

            for key in old_keys & new_keys:
                if old[key] != new[key]:
                    differences[f"value_diff[{key}]"] = {
                        "old": old[key],
                        "new": new[key]
                    }

        # List comparison
        elif isinstance(old, (list, tuple)):
            if len(old) != len(new):
                differences["length"] = {"old": len(old), "new": len(new)}
            else:
                for i, (old_item, new_item) in enumerate(zip(old, new)):
                    if old_item != new_item:
                        differences[f"item[{i}]"] = {
                            "old": old_item,
                            "new": new_item
                        }

        # Direct comparison
        else:
            if old != new:
                differences["value"] = {"old": old, "new": new}

        return len(differences) == 0, differences
```

**Testing**: Unit tests for comparison logic, no business impact

---

#### Step 1.3: Create Rollback Procedures
**File**: `ai_docs/operations/ddd-refactoring-rollback.md` (NEW)

```markdown
# DDD Refactoring Rollback Procedures

## Instant Rollback - Feature Flags

### Emergency Rollback (Any Phase)
**Time**: < 5 minutes
**Impact**: Zero downtime

**Steps**:
1. Set master flag to false:
   ```bash
   # In .env or environment
   DDD_REFACTOR_ENABLED=false
   ```

2. Restart application:
   ```bash
   docker-compose restart backend
   ```

3. Verify rollback:
   ```bash
   curl http://localhost:8000/health
   # Check logs for "Using OLD implementation"
   ```

### Granular Rollback (Specific Feature)
**Time**: < 5 minutes
**Impact**: Zero downtime

**Steps**:
1. Disable specific feature flag:
   ```bash
   # Example: Roll back orchestrator only
   USE_NEW_ORCHESTRATOR=false

   # Keep other features enabled
   DDD_REFACTOR_ENABLED=true
   USE_UNIT_OF_WORK=true  # Still enabled
   ```

2. Restart application
3. Verify specific feature reverted

## Database Rollback Procedures

### If Migration Applied
**Time**: < 10 minutes
**Impact**: Possible brief downtime

**Steps**:
1. Roll back migration:
   ```bash
   alembic downgrade -1
   ```

2. Disable feature flags
3. Restart application
4. Verify data integrity

## Code Rollback (Git)

### Emergency Code Revert
**Time**: < 15 minutes
**Impact**: Deploy required

**Steps**:
1. Identify last working commit:
   ```bash
   git log --oneline
   ```

2. Revert to safe commit:
   ```bash
   git revert <commit-hash>
   # OR hard reset in dev:
   git reset --hard <commit-hash>
   ```

3. Redeploy:
   ```bash
   ./docker-system/docker-menu.sh  # Option R
   ```

## Validation After Rollback

**Checklist**:
- [ ] Health endpoint returns 200
- [ ] Feature flags show old implementation
- [ ] MCP tools respond correctly
- [ ] Test suite passes
- [ ] No errors in logs
- [ ] Performance metrics normal

## Communication Template

**Incident**: DDD refactoring rollback
**Phase**: [Phase number and name]
**Reason**: [Why rollback needed]
**Impact**: [What functionality affected]
**Resolution**: [Which flags disabled]
**Status**: Rolled back successfully
**Next Steps**: [Investigation/fixes needed]
```

**Testing**: Documentation review, no code changes

---

#### Step 1.4: Create Monitoring & Logging
**File**: `agenthub_main/src/fastmcp/shared/refactoring/refactoring_logger.py` (NEW)

```python
"""
Specialized logging for DDD refactoring progress.
Tracks which implementations are used and logs differences.
"""
import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime

from ..config.feature_flags import get_feature_flags


class RefactoringLogger:
    """Logger specifically for DDD refactoring tracking."""

    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(f"ddd_refactor.{component_name}")
        self.flags = get_feature_flags()

    def log_implementation_choice(self, feature_name: str, using_new: bool):
        """Log which implementation is being used."""
        impl_type = "NEW" if using_new else "OLD"
        self.logger.info(
            f"[{self.component_name}] Using {impl_type} implementation for {feature_name}",
            extra={
                "component": self.component_name,
                "feature": feature_name,
                "implementation": impl_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_shadow_difference(
        self,
        feature_name: str,
        differences: Dict[str, Any]
    ):
        """Log differences found in shadow mode."""
        self.logger.warning(
            f"[{self.component_name}] Shadow mode difference in {feature_name}",
            extra={
                "component": self.component_name,
                "feature": feature_name,
                "differences": differences,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_validation_failure(
        self,
        feature_name: str,
        differences: Dict[str, Any],
        old_result: Any,
        new_result: Any
    ):
        """Log validation mode failures."""
        self.logger.error(
            f"[{self.component_name}] Validation FAILED for {feature_name}",
            extra={
                "component": self.component_name,
                "feature": feature_name,
                "differences": differences,
                "old_result_summary": self._summarize(old_result),
                "new_result_summary": self._summarize(new_result),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_validation_success(self, feature_name: str):
        """Log validation mode successes."""
        self.logger.info(
            f"[{self.component_name}] Validation PASSED for {feature_name}",
            extra={
                "component": self.component_name,
                "feature": feature_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_phase_start(self, phase_number: int, phase_name: str):
        """Log when a refactoring phase starts."""
        self.logger.info(
            f"[{self.component_name}] Starting Phase {phase_number}: {phase_name}",
            extra={
                "component": self.component_name,
                "phase": phase_number,
                "phase_name": phase_name,
                "flags": self.flags.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_phase_complete(self, phase_number: int, phase_name: str):
        """Log when a refactoring phase completes."""
        self.logger.info(
            f"[{self.component_name}] Completed Phase {phase_number}: {phase_name}",
            extra={
                "component": self.component_name,
                "phase": phase_number,
                "phase_name": phase_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _summarize(self, obj: Any) -> str:
        """Create brief summary of object for logging."""
        if obj is None:
            return "None"
        if isinstance(obj, dict):
            return f"Dict with {len(obj)} keys"
        if isinstance(obj, (list, tuple)):
            return f"List with {len(obj)} items"
        return str(type(obj).__name__)
```

**Testing**: Unit tests for logging, no business logic

---

### Phase 1 Deliverables

**Created Files**:
1. ✅ `agenthub_main/src/fastmcp/shared/config/feature_flags.py`
2. ✅ `agenthub_main/src/fastmcp/shared/refactoring/parallel_executor.py`
3. ✅ `agenthub_main/src/fastmcp/shared/refactoring/refactoring_logger.py`
4. ✅ `ai_docs/operations/ddd-refactoring-rollback.md`

**Tests Created**:
1. ✅ `tests/unit/shared/test_feature_flags.py`
2. ✅ `tests/unit/shared/test_parallel_executor.py`
3. ✅ `tests/unit/shared/test_refactoring_logger.py`

**Acceptance Criteria**:
- [ ] All feature flags default to `false`
- [ ] ParallelExecutor can run both implementations
- [ ] Rollback procedures documented and tested
- [ ] Logging infrastructure in place
- [ ] Zero changes to existing business logic
- [ ] All tests pass

**Effort**: 2 weeks (10 working days)
**Confidence**: 100% - Pure infrastructure, no business logic changes

---

## Phase 2: Low-Risk Application Layer (Week 3-4)

### Goals
- ✅ Fix application layer issues with minimal risk
- ✅ Address: Medium #3, High #3, Low #1
- ✅ Improve exception handling
- ✅ Extract business logic from facades
- ✅ Make transaction boundaries explicit

### Violation Medium #3: Business Logic in Facade

**Current Code**: `application/facades/unified_context_facade.py:55-71`
```python
def _add_scope_to_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Add scope information to context data."""
    result = data.copy()  # Data manipulation logic
    if self._user_id and "user_id" not in result:
        result["user_id"] = self._user_id
    # ... business logic continues
```

#### Step 2.1: Create Scope Management Service
**File**: `agenthub_main/src/fastmcp/application/services/scope_management_service.py` (NEW)

```python
"""
Scope management service for context data.
Extracted from UnifiedContextFacade to follow DDD principles.
"""
from typing import Dict, Any, Optional


class ScopeManagementService:
    """
    Application service for adding scope information to context data.

    Responsibilities:
    - Add user_id scope to context data
    - Add project_id scope when needed
    - Ensure consistent scope handling across contexts
    """

    def __init__(self, user_id: Optional[str] = None, project_id: Optional[str] = None):
        self.user_id = user_id
        self.project_id = project_id

    def add_scope_to_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add scope information (user_id, project_id) to context data.

        Args:
            data: Original context data

        Returns:
            Context data with scope information added
        """
        result = data.copy()

        # Add user scope if not already present
        if self.user_id and "user_id" not in result:
            result["user_id"] = self.user_id

        # Add project scope if applicable
        if self.project_id and "project_id" not in result:
            result["project_id"] = self.project_id

        return result

    def validate_scope(self, data: Dict[str, Any]) -> bool:
        """
        Validate that required scope information is present.

        Args:
            data: Context data to validate

        Returns:
            True if scope is valid, False otherwise
        """
        # User ID is always required
        if "user_id" not in data:
            return False

        return True
```

**Testing**:
```python
# tests/unit/application/services/test_scope_management_service.py
def test_add_scope_to_data_adds_user_id():
    service = ScopeManagementService(user_id="user123")
    result = service.add_scope_to_data({"key": "value"})
    assert result["user_id"] == "user123"
    assert result["key"] == "value"

def test_add_scope_does_not_override_existing():
    service = ScopeManagementService(user_id="user123")
    result = service.add_scope_to_data({"user_id": "existing", "key": "value"})
    assert result["user_id"] == "existing"  # Not overridden
```

---

#### Step 2.2: Update Facade to Use Service (Adapter Pattern)
**File**: `application/facades/unified_context_facade.py:55-71`

**Old Implementation** (Keep temporarily):
```python
# OLD IMPLEMENTATION - Will be deprecated
def _add_scope_to_data_old(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """DEPRECATED: Old scope addition logic."""
    result = data.copy()
    if self._user_id and "user_id" not in result:
        result["user_id"] = self._user_id
    return result
```

**New Implementation** (Add alongside):
```python
from ..services.scope_management_service import ScopeManagementService
from ...shared.config.feature_flags import get_feature_flags
from ...shared.refactoring.parallel_executor import ParallelExecutor

class UnifiedContextFacade:
    def __init__(self, user_id: Optional[str] = None):
        self._user_id = user_id

        # NEW: Scope management service
        self._scope_service = ScopeManagementService(user_id=user_id)

        # Feature flag support
        self._flags = get_feature_flags()
        self._parallel_executor = ParallelExecutor("use_scope_service")

    def _add_scope_to_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add scope information to context data.
        Uses feature flag to switch between old and new implementation.
        """
        # Adapter pattern: Both implementations available
        old_impl = lambda: self._add_scope_to_data_old(data)
        new_impl = lambda: self._scope_service.add_scope_to_data(data)

        # Parallel executor handles feature flag logic
        return self._parallel_executor.execute(old_impl, new_impl)

    # Keep old implementation as fallback
    def _add_scope_to_data_old(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """DEPRECATED: Old scope addition logic - will be removed in Phase 8."""
        result = data.copy()
        if self._user_id and "user_id" not in result:
            result["user_id"] = self._user_id
        return result
```

**Migration Path**:
1. Week 3: Add new service and adapter (both implementations live)
2. Week 4: Enable feature flag in dev: `USE_SCOPE_SERVICE=true`
3. Week 4: Run shadow mode, verify identical results
4. Week 5: Enable in production (flag=true)
5. Phase 8: Remove old implementation after confidence period

**Rollback**: Set `USE_SCOPE_SERVICE=false`

---

### Violation High #3: Generic Exception Handling

**Current Code**: `application/facades/unified_context_facade.py:110-115, 146-150, 194-200`
```python
except Exception as e:  # Too broad
    logger.error(f"Failed to create context: {e}")
    return {"success": False, "error": str(e)}
```

#### Step 2.3: Create Exception Translation Layer
**File**: `agenthub_main/src/fastmcp/application/exceptions/exception_translator.py` (NEW)

```python
"""
Exception translation layer for application layer.
Translates domain and infrastructure exceptions to application responses.
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ...domain.exceptions.base_exceptions import (
    DomainException,
    ValidationException,
    ResourceNotFoundException,
    BusinessRuleViolationException
)
from ...infrastructure.exceptions import (
    DatabaseException,
    CacheException,
    ExternalServiceException
)

logger = logging.getLogger(__name__)


@dataclass
class ErrorResponse:
    """Standardized error response."""
    success: bool = False
    error_type: str = "UnknownError"
    error_message: str = ""
    error_details: Optional[Dict[str, Any]] = None
    status_code: int = 500

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "success": self.success,
            "error": self.error_message,
            "error_type": self.error_type
        }
        if self.error_details:
            result["details"] = self.error_details
        return result


class ExceptionTranslator:
    """
    Translates domain and infrastructure exceptions to application responses.

    Benefits:
    - Specific exception handling instead of catch-all
    - Consistent error responses
    - Proper logging with context
    - Hides internal details from external callers
    """

    @staticmethod
    def translate(exception: Exception, context: Optional[str] = None) -> ErrorResponse:
        """
        Translate exception to standardized error response.

        Args:
            exception: Exception to translate
            context: Optional context string for logging

        Returns:
            ErrorResponse with appropriate type and message
        """
        # Domain exceptions (business logic violations)
        if isinstance(exception, ValidationException):
            return ErrorResponse(
                success=False,
                error_type="ValidationError",
                error_message=str(exception),
                error_details={"field": getattr(exception, "field", None)},
                status_code=400
            )

        if isinstance(exception, ResourceNotFoundException):
            return ErrorResponse(
                success=False,
                error_type="NotFoundError",
                error_message=str(exception),
                error_details={"resource": getattr(exception, "resource_type", None)},
                status_code=404
            )

        if isinstance(exception, BusinessRuleViolationException):
            return ErrorResponse(
                success=False,
                error_type="BusinessRuleViolation",
                error_message=str(exception),
                error_details={"rule": getattr(exception, "rule", None)},
                status_code=422
            )

        # Infrastructure exceptions (technical failures)
        if isinstance(exception, DatabaseException):
            logger.error(f"Database error in {context}: {exception}", exc_info=True)
            return ErrorResponse(
                success=False,
                error_type="DatabaseError",
                error_message="A database error occurred",  # Hide details
                status_code=500
            )

        if isinstance(exception, CacheException):
            logger.warning(f"Cache error in {context}: {exception}")
            # Cache errors are non-critical, log but continue
            return ErrorResponse(
                success=False,
                error_type="CacheError",
                error_message="Cache temporarily unavailable",
                status_code=503
            )

        if isinstance(exception, ExternalServiceException):
            logger.error(f"External service error in {context}: {exception}")
            return ErrorResponse(
                success=False,
                error_type="ExternalServiceError",
                error_message="External service temporarily unavailable",
                status_code=503
            )

        # Generic domain exception
        if isinstance(exception, DomainException):
            return ErrorResponse(
                success=False,
                error_type="DomainError",
                error_message=str(exception),
                status_code=400
            )

        # Unknown exception (fallback)
        logger.error(
            f"Unexpected exception in {context}: {type(exception).__name__}",
            exc_info=True
        )
        return ErrorResponse(
            success=False,
            error_type="InternalError",
            error_message="An unexpected error occurred",
            status_code=500
        )
```

**Testing**:
```python
# tests/unit/application/exceptions/test_exception_translator.py
def test_translate_validation_exception():
    exc = ValidationException(message="Invalid email", field="email")
    result = ExceptionTranslator.translate(exc)
    assert result.error_type == "ValidationError"
    assert result.status_code == 400
    assert result.error_details["field"] == "email"

def test_translate_unknown_exception_hides_details():
    exc = ValueError("Internal calculation error")
    result = ExceptionTranslator.translate(exc, context="create_context")
    assert result.error_type == "InternalError"
    assert result.error_message == "An unexpected error occurred"  # Details hidden
```

---

#### Step 2.4: Update Facade with Specific Exception Handling
**File**: `application/facades/unified_context_facade.py:110-115` (and similar locations)

**Old Implementation**:
```python
def create_context_old(self, level: str, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """OLD implementation with catch-all exception."""
    try:
        # ... context creation logic ...
        return {"success": True, "context": result}
    except Exception as e:  # Too broad
        logger.error(f"Failed to create context: {e}")
        return {"success": False, "error": str(e)}
```

**New Implementation** (Adapter Pattern):
```python
from ..exceptions.exception_translator import ExceptionTranslator
from ...shared.refactoring.parallel_executor import ParallelExecutor

class UnifiedContextFacade:
    def __init__(self, user_id: Optional[str] = None):
        # ... existing initialization ...
        self._exception_translator = ExceptionTranslator()
        self._create_executor = ParallelExecutor("use_exception_translator")

    def create_context(self, level: str, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create context with proper exception handling.
        Uses feature flag to switch between old and new exception handling.
        """
        old_impl = lambda: self._create_context_old(level, context_id, data)
        new_impl = lambda: self._create_context_new(level, context_id, data)

        return self._create_executor.execute(old_impl, new_impl)

    def _create_context_new(self, level: str, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """NEW implementation with specific exception handling."""
        try:
            # Existing context creation logic (unchanged)
            scoped_data = self._add_scope_to_data(data)

            if level == "global":
                result = self._create_global_context(context_id, scoped_data)
            elif level == "project":
                result = self._create_project_context(context_id, scoped_data)
            # ... etc

            return {"success": True, "context": result}

        # Specific exception handling - translate to application responses
        except (ValidationException, ResourceNotFoundException,
                BusinessRuleViolationException, DomainException) as e:
            # Domain exceptions - expected business errors
            error_response = self._exception_translator.translate(e, context="create_context")
            return error_response.to_dict()

        except (DatabaseException, CacheException, ExternalServiceException) as e:
            # Infrastructure exceptions - technical failures
            error_response = self._exception_translator.translate(e, context="create_context")
            return error_response.to_dict()

        except Exception as e:
            # Unknown exception - last resort fallback
            error_response = self._exception_translator.translate(e, context="create_context")
            return error_response.to_dict()

    def _create_context_old(self, level: str, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """DEPRECATED: Old implementation - will be removed in Phase 8."""
        try:
            # ... existing logic unchanged ...
            return {"success": True, "context": result}
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            return {"success": False, "error": str(e)}
```

**Migration Path**:
1. Week 3: Add ExceptionTranslator and new implementation
2. Week 4: Shadow mode - verify both produce same results
3. Week 4: Enable flag: `USE_EXCEPTION_TRANSLATOR=true` in dev
4. Week 5: Production rollout
5. Phase 8: Remove old exception handling

**Rollback**: Set `USE_EXCEPTION_TRANSLATOR=false`

**Benefits**:
- ✅ Specific exception types caught
- ✅ Better error messages for users
- ✅ Proper logging with context
- ✅ Internal details hidden in production
- ✅ No breaking changes to external API

---

### Violation Low #1: Missing Transaction Boundaries

**Current Issue**: Some use cases don't explicitly define transaction boundaries

#### Step 2.5: Create Transaction Decorator
**File**: `agenthub_main/src/fastmcp/application/decorators/transactional.py` (NEW)

```python
"""
Transaction boundary decorator for use cases.
Makes transaction management explicit and declarative.
"""
import functools
import logging
from typing import Callable, Any
from contextlib import contextmanager

from ...infrastructure.database.database_config import get_session_factory

logger = logging.getLogger(__name__)


def transactional(read_only: bool = False):
    """
    Decorator to mark use case methods with explicit transaction boundaries.

    Args:
        read_only: If True, transaction is read-only (optimization hint)

    Usage:
        @transactional()
        def create_task(self, ...):
            # Entire method runs in transaction
            # Auto-commit on success, auto-rollback on exception
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            session_factory = get_session_factory()

            with session_factory() as session:
                try:
                    # Bind session to thread/context (if needed)
                    result = func(*args, **kwargs)

                    if not read_only:
                        session.commit()
                        logger.debug(f"Transaction committed for {func.__name__}")

                    return result

                except Exception as e:
                    if not read_only:
                        session.rollback()
                        logger.error(f"Transaction rolled back for {func.__name__}: {e}")
                    raise

        # Mark function as transactional (for introspection)
        wrapper._transactional = True
        wrapper._read_only = read_only

        return wrapper
    return decorator


@contextmanager
def transaction_scope(read_only: bool = False):
    """
    Context manager for explicit transaction boundaries.

    Usage:
        with transaction_scope():
            # Code runs in transaction
            repository.save(entity)
            # Auto-commit on exit
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session

        if not read_only:
            session.commit()
            logger.debug("Transaction committed")

    except Exception as e:
        if not read_only:
            session.rollback()
            logger.error(f"Transaction rolled back: {e}")
        raise

    finally:
        session.close()
```

---

#### Step 2.6: Apply Transaction Boundaries to Use Cases
**Example**: `application/use_cases/complete_task_optimized.py`

**Old Implementation**:
```python
class CompleteTaskOptimized:
    def execute(self, task_id: str, completion_summary: str) -> Dict[str, Any]:
        # No explicit transaction boundary
        task = self.task_repository.get(task_id)
        task.complete(completion_summary)
        self.task_repository.save(task)
        return {"success": True}
```

**New Implementation**:
```python
from ..decorators.transactional import transactional

class CompleteTaskOptimized:

    @transactional()  # Explicit transaction boundary
    def execute(self, task_id: str, completion_summary: str) -> Dict[str, Any]:
        """
        Complete task with explicit transaction management.
        Entire method runs in a transaction - commits on success, rolls back on error.
        """
        task = self.task_repository.get(task_id)
        task.complete(completion_summary)
        self.task_repository.save(task)

        # If any exception occurs, transaction auto-rolls back
        return {"success": True}

    @transactional(read_only=True)  # Read-only optimization
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Read-only use case - no writes allowed."""
        task = self.task_repository.get(task_id)
        return {"status": task.status}
```

**Migration Strategy**:
- No feature flag needed - decorators don't change behavior
- Add decorators gradually to use cases
- Existing code continues to work (backward compatible)
- No breaking changes

**Benefits**:
- ✅ Transaction boundaries explicit and visible
- ✅ Automatic commit/rollback handling
- ✅ Read-only optimization hints
- ✅ Better error recovery
- ✅ Self-documenting code

---

### Phase 2 Deliverables

**Created Files**:
1. ✅ `application/services/scope_management_service.py`
2. ✅ `application/exceptions/exception_translator.py`
3. ✅ `application/decorators/transactional.py`

**Modified Files** (with adapters):
1. ✅ `application/facades/unified_context_facade.py` (both implementations)

**Tests Created**:
1. ✅ `tests/unit/application/services/test_scope_management_service.py`
2. ✅ `tests/unit/application/exceptions/test_exception_translator.py`
3. ✅ `tests/unit/application/decorators/test_transactional.py`
4. ✅ `tests/integration/application/test_facade_with_new_services.py`

**Feature Flags**:
- `USE_SCOPE_SERVICE=false` (default)
- `USE_EXCEPTION_TRANSLATOR=false` (default)

**Acceptance Criteria**:
- [ ] All new services have unit tests
- [ ] Facade works with both old and new implementations
- [ ] Shadow mode shows identical results
- [ ] Transaction decorators applied to key use cases
- [ ] Rollback procedures tested
- [ ] All existing tests still pass
- [ ] No breaking changes to external APIs

**Effort**: 2 weeks (10 working days)
**Confidence**: 95% - Low risk, well-isolated changes

---

## Phase 3: Infrastructure Improvements (Week 5-7)

### Goals
- ✅ Fix infrastructure layer issues
- ✅ Address: Critical #3, Critical #4, Medium #5
- ✅ Implement Unit of Work pattern
- ✅ Improve session management
- ✅ Better database exception handling

### Violation Critical #4: Session Management Coupling

**Current Problem**: `infrastructure/repositories/base_orm_repository.py:45-76`
- Complex session management in repository
- Multiple session sources with priority logic
- Repositories tightly coupled to session strategy

**Solution**: Unit of Work pattern

---

#### Step 3.1: Create Unit of Work Pattern
**File**: `agenthub_main/src/fastmcp/infrastructure/uow/unit_of_work.py` (NEW)

```python
"""
Unit of Work pattern implementation.
Manages database sessions and coordinates repositories in a single transaction.
"""
from __future__ import annotations
import logging
from typing import Optional, Protocol, runtime_checkable
from contextlib import contextmanager

from sqlalchemy.orm import Session
from ..database.database_config import get_session_factory
from ..repositories.task_repository_impl import TaskRepositoryImpl
from ..repositories.project_repository_impl import ProjectRepositoryImpl
from ..repositories.context_repository_impl import ContextRepositoryImpl
from ..repositories.agent_repository_impl import AgentRepositoryImpl

logger = logging.getLogger(__name__)


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    """Protocol defining Unit of Work contract."""

    session: Session
    tasks: TaskRepositoryImpl
    projects: ProjectRepositoryImpl
    contexts: ContextRepositoryImpl
    agents: AgentRepositoryImpl

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class UnitOfWork:
    """
    Unit of Work manages database session and coordinates repositories.

    Benefits:
    - Single transaction for multiple repository operations
    - Automatic session lifecycle management
    - Clean separation of session management from repositories
    - Thread-safe session handling

    Usage:
        with UnitOfWork() as uow:
            task = uow.tasks.get(task_id)
            task.complete()
            uow.tasks.save(task)
            # Auto-commits on context exit
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Unit of Work.

        Args:
            session: Optional existing session (for nested UoW or testing)
        """
        self._session_factory = get_session_factory()
        self._provided_session = session
        self._session: Optional[Session] = None
        self._is_owner = session is None  # Track if we created the session

        # Repository instances (lazy-loaded)
        self._tasks: Optional[TaskRepositoryImpl] = None
        self._projects: Optional[ProjectRepositoryImpl] = None
        self._contexts: Optional[ContextRepositoryImpl] = None
        self._agents: Optional[AgentRepositoryImpl] = None

    def __enter__(self) -> UnitOfWork:
        """Enter context manager - create/acquire session."""
        if self._provided_session:
            self._session = self._provided_session
        else:
            self._session = self._session_factory()

        logger.debug(f"UnitOfWork entered (owner={self._is_owner})")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - commit/rollback and close."""
        if exc_type is not None:
            # Exception occurred - rollback
            if self._is_owner:
                self.rollback()
        else:
            # Success - commit
            if self._is_owner:
                self.commit()

        # Close session if we own it
        if self._is_owner:
            self.close()

        logger.debug(f"UnitOfWork exited (owner={self._is_owner}, exception={exc_type is not None})")

    @property
    def session(self) -> Session:
        """Get current database session."""
        if not self._session:
            raise RuntimeError("UnitOfWork not entered - use 'with UnitOfWork() as uow:'")
        return self._session

    @property
    def tasks(self) -> TaskRepositoryImpl:
        """Get task repository with current session."""
        if not self._tasks:
            self._tasks = TaskRepositoryImpl(session=self.session)
        return self._tasks

    @property
    def projects(self) -> ProjectRepositoryImpl:
        """Get project repository with current session."""
        if not self._projects:
            self._projects = ProjectRepositoryImpl(session=self.session)
        return self._projects

    @property
    def contexts(self) -> ContextRepositoryImpl:
        """Get context repository with current session."""
        if not self._contexts:
            self._contexts = ContextRepositoryImpl(session=self.session)
        return self._contexts

    @property
    def agents(self) -> AgentRepositoryImpl:
        """Get agent repository with current session."""
        if not self._agents:
            self._agents = AgentRepositoryImpl(session=self.session)
        return self._agents

    def commit(self) -> None:
        """Commit current transaction."""
        if self._session and self._is_owner:
            self._session.commit()
            logger.debug("UnitOfWork committed")

    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._session and self._is_owner:
            self._session.rollback()
            logger.debug("UnitOfWork rolled back")

    def close(self) -> None:
        """Close session."""
        if self._session and self._is_owner:
            self._session.close()
            self._session = None
            logger.debug("UnitOfWork closed")


@contextmanager
def get_unit_of_work(session: Optional[Session] = None):
    """
    Context manager to get Unit of Work instance.

    Args:
        session: Optional existing session for nested transactions

    Yields:
        UnitOfWork instance

    Usage:
        with get_unit_of_work() as uow:
            task = uow.tasks.get(task_id)
            uow.commit()
    """
    uow = UnitOfWork(session=session)
    with uow:
        yield uow
```

**Testing**:
```python
# tests/unit/infrastructure/uow/test_unit_of_work.py
def test_uow_commits_on_success():
    with UnitOfWork() as uow:
        task = uow.tasks.create(title="Test")
        # Auto-commits on exit

    # Verify task was saved
    with UnitOfWork() as uow:
        saved_task = uow.tasks.get(task.id)
        assert saved_task.title == "Test"

def test_uow_rollback_on_exception():
    try:
        with UnitOfWork() as uow:
            task = uow.tasks.create(title="Test")
            raise ValueError("Simulated error")
    except ValueError:
        pass

    # Verify task was NOT saved (rolled back)
    with UnitOfWork() as uow:
        with pytest.raises(ResourceNotFoundException):
            uow.tasks.get(task.id)
```

---

#### Step 3.2: Update Use Cases to Use UnitOfWork
**File**: `application/use_cases/complete_task_optimized.py` (example)

**Old Implementation**:
```python
class CompleteTaskOptimized:
    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository

    def execute(self, task_id: str, summary: str) -> Dict[str, Any]:
        # Uses repository directly (session management unclear)
        task = self.task_repository.get(task_id)
        task.complete(summary)
        self.task_repository.save(task)
        return {"success": True}
```

**New Implementation** (Adapter Pattern):
```python
from ...infrastructure.uow.unit_of_work import UnitOfWork, get_unit_of_work
from ...shared.refactoring.parallel_executor import ParallelExecutor
from ...shared.config.feature_flags import get_feature_flags

class CompleteTaskOptimized:
    def __init__(self, task_repository: Optional[TaskRepository] = None):
        # Support both old (injected repo) and new (UoW) patterns
        self.task_repository = task_repository  # For old implementation
        self._flags = get_feature_flags()
        self._executor = ParallelExecutor("use_unit_of_work")

    def execute(self, task_id: str, summary: str) -> Dict[str, Any]:
        """Execute with feature flag support for UoW pattern."""
        old_impl = lambda: self._execute_old(task_id, summary)
        new_impl = lambda: self._execute_new(task_id, summary)

        return self._executor.execute(old_impl, new_impl)

    def _execute_new(self, task_id: str, summary: str) -> Dict[str, Any]:
        """NEW implementation using Unit of Work."""
        with get_unit_of_work() as uow:
            # All repository operations use same session
            task = uow.tasks.get(task_id)
            task.complete(summary)
            uow.tasks.save(task)

            # Update related context
            context = uow.contexts.get_for_task(task_id)
            context.mark_completed()
            uow.contexts.save(context)

            # Auto-commits on context exit

        return {"success": True, "task": task.to_dict()}

    def _execute_old(self, task_id: str, summary: str) -> Dict[str, Any]:
        """DEPRECATED: Old implementation - will be removed in Phase 8."""
        task = self.task_repository.get(task_id)
        task.complete(summary)
        self.task_repository.save(task)
        return {"success": True, "task": task.to_dict()}
```

**Migration Path**:
1. Week 5: Implement UnitOfWork
2. Week 5-6: Add new implementations to use cases (both available)
3. Week 6: Shadow mode testing
4. Week 7: Enable flag `USE_UNIT_OF_WORK=true` in dev
5. Week 7: Production rollout after validation
6. Phase 8: Remove old repository injection pattern

**Rollback**: Set `USE_UNIT_OF_WORK=false`

---

### Violation Critical #3: Infrastructure Validation Logic

**Current Problem**: `infrastructure/repositories/base_orm_repository.py:102-124`
- Infrastructure layer makes validation decisions
- Creates domain exceptions from infrastructure

**Solution**: Throw infrastructure exceptions, translate in application layer

---

#### Step 3.3: Create Infrastructure Exception Hierarchy
**File**: `agenthub_main/src/fastmcp/infrastructure/exceptions/__init__.py` (NEW)

```python
"""
Infrastructure-specific exceptions.
These are technical failures, not business rule violations.
"""


class InfrastructureException(Exception):
    """Base exception for infrastructure layer."""
    pass


class DatabaseConnectionException(InfrastructureException):
    """Database connection failed."""
    pass


class DatabaseIntegrityException(InfrastructureException):
    """Database integrity constraint violated."""

    def __init__(self, message: str, constraint: str, data: dict):
        super().__init__(message)
        self.constraint = constraint
        self.data = data


class DatabaseTimeoutException(InfrastructureException):
    """Database operation timed out."""
    pass


class CacheException(InfrastructureException):
    """Cache operation failed."""
    pass


class ExternalServiceException(InfrastructureException):
    """External service call failed."""
    pass
```

---

#### Step 3.4: Update Repository to Throw Infrastructure Exceptions
**File**: `infrastructure/repositories/base_orm_repository.py:102-124`

**Old Implementation**:
```python
from ...domain.exceptions.base_exceptions import ValidationException  # WRONG LAYER

def create(self, **kwargs) -> ModelType:
    try:
        instance = self.model_class(**kwargs)
        session.add(instance)
        session.flush()
        return instance
    except IntegrityError as e:
        # WRONG: Infrastructure creating domain exceptions
        raise ValidationException(
            message=f"Integrity constraint violation: {str(e)}",
            field="unknown",
            value=str(kwargs)
        )
```

**New Implementation** (Adapter Pattern):
```python
from ..exceptions import DatabaseIntegrityException  # Infrastructure exception
from ...shared.config.feature_flags import get_feature_flags

def create(self, **kwargs) -> ModelType:
    """
    Create new model instance.
    Uses feature flag to switch exception handling strategy.
    """
    flags = get_feature_flags()

    if flags.is_enabled("use_infrastructure_exceptions"):
        return self._create_new(**kwargs)
    else:
        return self._create_old(**kwargs)

def _create_new(self, **kwargs) -> ModelType:
    """NEW: Throw infrastructure exceptions."""
    try:
        instance = self.model_class(**kwargs)
        session.add(instance)
        session.flush()
        session.refresh(instance)
        return instance
    except IntegrityError as e:
        # Throw infrastructure exception (let application layer translate)
        constraint_name = self._extract_constraint_name(e)
        raise DatabaseIntegrityException(
            message=f"Database integrity constraint violated: {constraint_name}",
            constraint=constraint_name,
            data=kwargs
        )
    except OperationalError as e:
        raise DatabaseTimeoutException(f"Database operation timed out: {e}")
    except SQLAlchemyError as e:
        raise InfrastructureException(f"Database error: {e}")

def _create_old(self, **kwargs) -> ModelType:
    """DEPRECATED: Old implementation - will be removed in Phase 8."""
    try:
        instance = self.model_class(**kwargs)
        session.add(instance)
        session.flush()
        return instance
    except IntegrityError as e:
        # Old behavior - creating domain exceptions (incorrect layer)
        raise ValidationException(
            message=f"Integrity constraint violation: {str(e)}",
            field="unknown",
            value=str(kwargs)
        )

@staticmethod
def _extract_constraint_name(integrity_error: IntegrityError) -> str:
    """Extract constraint name from SQLAlchemy IntegrityError."""
    error_msg = str(integrity_error.orig)
    # Parse constraint name from error message (DB-specific)
    # Example: "UNIQUE constraint failed: tasks.title"
    if "UNIQUE constraint" in error_msg:
        parts = error_msg.split(":")
        if len(parts) > 1:
            return parts[1].strip()
    return "unknown_constraint"
```

---

#### Step 3.5: Update Application Layer to Translate Exceptions
**File**: `application/exceptions/exception_translator.py` (extend from Phase 2)

```python
# Add infrastructure exception translation
from ...infrastructure.exceptions import (
    DatabaseIntegrityException,
    DatabaseTimeoutException,
    InfrastructureException
)
from ...domain.exceptions.base_exceptions import ValidationException

class ExceptionTranslator:
    @staticmethod
    def translate(exception: Exception, context: Optional[str] = None) -> ErrorResponse:
        """Translate exceptions including new infrastructure types."""

        # Infrastructure → Domain translation
        if isinstance(exception, DatabaseIntegrityException):
            # Translate to domain validation exception
            field = ExceptionTranslator._infer_field_from_constraint(
                exception.constraint,
                exception.data
            )
            return ExceptionTranslator.translate(
                ValidationException(
                    message=f"Duplicate or invalid value for {field}",
                    field=field,
                    value=exception.data.get(field)
                )
            )

        if isinstance(exception, DatabaseTimeoutException):
            logger.error(f"Database timeout in {context}: {exception}")
            return ErrorResponse(
                success=False,
                error_type="ServiceUnavailable",
                error_message="Service temporarily unavailable, please retry",
                status_code=503
            )

        # ... existing exception handling ...

    @staticmethod
    def _infer_field_from_constraint(constraint: str, data: dict) -> str:
        """
        Infer field name from constraint violation.
        Example: "tasks.title" → "title"
        """
        if "." in constraint:
            parts = constraint.split(".")
            return parts[-1]

        # Fallback: guess from data keys
        if "email" in data:
            return "email"
        if "title" in data:
            return "title"

        return "unknown"
```

**Benefits**:
- ✅ Proper layer separation
- ✅ Infrastructure doesn't know about domain exceptions
- ✅ Application layer controls business error responses
- ✅ More specific error handling

---

### Violation Medium #5: Generic Error Handling in Repository

**Solution**: Handle specific SQLAlchemy exceptions

#### Step 3.6: Improve Exception Specificity
**File**: `infrastructure/repositories/base_orm_repository.py:66-73, 90-97`

**Old Code**:
```python
except SQLAlchemyError as e:  # Too broad
    session.rollback()
    logger.error(f"Database error: {e}")
    raise DatabaseException(...)
```

**New Code**:
```python
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    DataError,
    ProgrammingError,
    SQLAlchemyError
)
from ..exceptions import (
    DatabaseIntegrityException,
    DatabaseTimeoutException,
    DatabaseConnectionException,
    InfrastructureException
)

def get_by_id(self, id: str) -> Optional[ModelType]:
    """Get entity by ID with specific exception handling."""
    try:
        with self.get_db_session() as session:
            return session.query(self.model_class).filter_by(id=id).first()

    # Specific SQLAlchemy exceptions
    except OperationalError as e:
        # Database connection or timeout issues
        if "timeout" in str(e).lower():
            raise DatabaseTimeoutException(f"Query timeout for {self.model_class.__name__}")
        else:
            raise DatabaseConnectionException(f"Database connection error: {e}")

    except DataError as e:
        # Invalid data format (e.g., invalid UUID)
        raise InfrastructureException(f"Invalid data format: {e}")

    except ProgrammingError as e:
        # SQL syntax error or table doesn't exist
        raise InfrastructureException(f"Database programming error: {e}")

    except SQLAlchemyError as e:
        # Fallback for other SQLAlchemy errors
        raise InfrastructureException(f"Database error: {e}")
```

**Migration**: No feature flag needed - this is pure improvement within infrastructure layer

---

### Phase 3 Deliverables

**Created Files**:
1. ✅ `infrastructure/uow/unit_of_work.py`
2. ✅ `infrastructure/exceptions/__init__.py`

**Modified Files** (with adapters):
1. ✅ `infrastructure/repositories/base_orm_repository.py` (both implementations)
2. ✅ `application/use_cases/*.py` (gradual UoW adoption)
3. ✅ `application/exceptions/exception_translator.py` (extended)

**Tests Created**:
1. ✅ `tests/unit/infrastructure/uow/test_unit_of_work.py`
2. ✅ `tests/unit/infrastructure/exceptions/test_infrastructure_exceptions.py`
3. ✅ `tests/integration/infrastructure/test_repository_exceptions.py`
4. ✅ `tests/integration/application/test_use_case_with_uow.py`

**Feature Flags**:
- `USE_UNIT_OF_WORK=false` (default)
- `USE_INFRASTRUCTURE_EXCEPTIONS=false` (default)

**Acceptance Criteria**:
- [ ] UnitOfWork pattern implemented and tested
- [ ] All use cases can use both old and new session management
- [ ] Infrastructure exceptions properly defined
- [ ] Application layer translates infrastructure → domain exceptions
- [ ] Shadow mode shows identical behavior
- [ ] Rollback procedures tested
- [ ] All tests pass with both implementations
- [ ] No breaking changes to external APIs

**Effort**: 3 weeks (15 working days)
**Confidence**: 90% - Core infrastructure changes, comprehensive testing required

---

## Phase 4: Domain Enrichment (Week 8-10)

### Goals
- ✅ Enrich domain models without breaking serialization
- ✅ Address: Critical #1, High #2, Medium #1, Medium #2
- ✅ Add business methods to TaskContextUnified
- ✅ Extract serialization from domain entities
- ✅ Maintain backward compatibility

### Violation Critical #1: Anemic Domain Model (TaskContextUnified)

**Current Code**: `domain/entities/context.py:220-313`
```python
@dataclass
class TaskContextUnified:
    """Task context entity - ANEMIC MODEL"""
    id: str
    branch_id: str
    task_data: Dict[str, Any] = field(default_factory=dict)

    def dict(self) -> Dict[str, Any]:  # Only serialization
        return {...}
```

**Problem**: No business logic, just data container

**Solution**: Add business methods while maintaining serialization compatibility

---

#### Step 4.1: Create Rich Domain Model (Strangler Fig)
**File**: `domain/entities/context.py:220-313` (modify)

**Strategy**: Add methods gradually, keep existing dict() for backward compatibility

**New Implementation**:
```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..value_objects.task_status import TaskStatus
from ..value_objects.priority import Priority
from ..exceptions.base_exceptions import (
    BusinessRuleViolationException,
    ValidationException
)


@dataclass
class TaskContextUnified:
    """
    Rich domain model for task context.

    Responsibilities:
    - Manage task progress tracking
    - Enforce business rules for task completion
    - Handle task blocker management
    - Manage task insights and learnings
    """

    # Core identity
    id: str
    branch_id: str
    task_id: str

    # Task data (backward compatible)
    task_data: Dict[str, Any] = field(default_factory=dict)

    # Domain behavior fields (NEW - optional for backward compatibility)
    _progress_percentage: Optional[int] = field(default=None, init=False)
    _blockers: List[str] = field(default_factory=list, init=False)
    _insights: List[Dict[str, Any]] = field(default_factory=list, init=False)
    _status: Optional[TaskStatus] = field(default=None, init=False)

    def __post_init__(self):
        """Initialize derived fields from task_data (backward compatible)."""
        # Extract from task_data if present
        if "progress_percentage" in self.task_data:
            self._progress_percentage = self.task_data["progress_percentage"]

        if "blockers" in self.task_data:
            self._blockers = self.task_data.get("blockers", [])

        if "insights" in self.task_data:
            self._insights = self.task_data.get("insights", [])

        if "status" in self.task_data:
            status_str = self.task_data["status"]
            self._status = TaskStatus.from_string(status_str) if status_str else None

    # ========== RICH DOMAIN BEHAVIOR (NEW) ==========

    def update_progress(self, percentage: int, notes: Optional[str] = None) -> None:
        """
        Update task progress with business rule validation.

        Args:
            percentage: Progress 0-100
            notes: Optional progress notes

        Raises:
            ValidationException: If percentage out of range
            BusinessRuleViolationException: If progress decreases
        """
        # Validation
        if not 0 <= percentage <= 100:
            raise ValidationException(
                message=f"Progress must be 0-100, got {percentage}",
                field="progress_percentage",
                value=percentage
            )

        # Business rule: Progress should not decrease
        if self._progress_percentage is not None and percentage < self._progress_percentage:
            raise BusinessRuleViolationException(
                message=f"Progress cannot decrease from {self._progress_percentage}% to {percentage}%",
                rule="progress_non_decreasing"
            )

        # Update progress
        old_progress = self._progress_percentage
        self._progress_percentage = percentage

        # Update task_data (backward compatibility)
        self.task_data["progress_percentage"] = percentage
        if notes:
            self.task_data["progress_notes"] = notes

        # Auto-update status based on progress
        self._update_status_from_progress()

        # Domain event (if event system enabled)
        # self._domain_events.append(ProgressUpdated(self.id, old_progress, percentage))

    def add_blocker(self, blocker_description: str, severity: str = "medium") -> None:
        """
        Add blocker to task.

        Args:
            blocker_description: Description of what's blocking progress
            severity: Blocker severity (low, medium, high, critical)

        Raises:
            ValidationException: If blocker empty or severity invalid
        """
        if not blocker_description or not blocker_description.strip():
            raise ValidationException(
                message="Blocker description cannot be empty",
                field="blocker_description",
                value=blocker_description
            )

        valid_severities = ["low", "medium", "high", "critical"]
        if severity not in valid_severities:
            raise ValidationException(
                message=f"Severity must be one of {valid_severities}",
                field="severity",
                value=severity
            )

        # Add blocker
        blocker = {
            "description": blocker_description,
            "severity": severity,
            "added_at": datetime.utcnow().isoformat()
        }
        self._blockers.append(blocker_description)  # Simple version

        # Update task_data (backward compatibility)
        if "blockers" not in self.task_data:
            self.task_data["blockers"] = []
        self.task_data["blockers"].append(blocker)

        # Auto-mark task as blocked if high/critical blocker
        if severity in ["high", "critical"]:
            self._status = TaskStatus.BLOCKED
            self.task_data["status"] = "blocked"

    def remove_blocker(self, blocker_description: str) -> None:
        """Remove blocker when resolved."""
        if blocker_description in self._blockers:
            self._blockers.remove(blocker_description)

            # Update task_data
            self.task_data["blockers"] = [
                b for b in self.task_data.get("blockers", [])
                if b.get("description") != blocker_description
            ]

            # Unblock task if no more blockers
            if not self._blockers and self._status == TaskStatus.BLOCKED:
                self._status = TaskStatus.IN_PROGRESS
                self.task_data["status"] = "in_progress"

    def add_insight(
        self,
        insight: str,
        category: str = "technical",
        importance: str = "medium"
    ) -> None:
        """
        Add insight/learning from task work.

        Args:
            insight: The insight or learning
            category: Category (technical, business, performance, etc.)
            importance: Importance level (low, medium, high, critical)
        """
        if not insight or not insight.strip():
            raise ValidationException(
                message="Insight cannot be empty",
                field="insight",
                value=insight
            )

        insight_entry = {
            "content": insight,
            "category": category,
            "importance": importance,
            "recorded_at": datetime.utcnow().isoformat()
        }

        self._insights.append(insight_entry)

        # Update task_data
        if "insights" not in self.task_data:
            self.task_data["insights"] = []
        self.task_data["insights"].append(insight_entry)

    def validate_for_completion(self) -> bool:
        """
        Validate if task can be completed.

        Returns:
            True if can complete, False otherwise

        Raises:
            BusinessRuleViolationException: If completion requirements not met
        """
        # Business rule: Cannot complete if blockers exist
        if self._blockers:
            raise BusinessRuleViolationException(
                message=f"Cannot complete task with {len(self._blockers)} active blockers",
                rule="no_blockers_for_completion"
            )

        # Business rule: Progress must be 100%
        if self._progress_percentage is not None and self._progress_percentage < 100:
            raise BusinessRuleViolationException(
                message=f"Cannot complete task at {self._progress_percentage}% progress",
                rule="full_progress_for_completion"
            )

        return True

    def mark_complete(self, completion_summary: str) -> None:
        """
        Mark task as complete with validation.

        Args:
            completion_summary: Summary of what was completed

        Raises:
            BusinessRuleViolationException: If cannot complete
        """
        # Validate completion eligibility
        self.validate_for_completion()

        # Mark complete
        self._status = TaskStatus.DONE
        self._progress_percentage = 100

        # Update task_data
        self.task_data["status"] = "done"
        self.task_data["progress_percentage"] = 100
        self.task_data["completion_summary"] = completion_summary
        self.task_data["completed_at"] = datetime.utcnow().isoformat()

    def _update_status_from_progress(self) -> None:
        """Auto-update status based on progress percentage."""
        if self._progress_percentage == 0:
            self._status = TaskStatus.TODO
            self.task_data["status"] = "todo"
        elif 0 < self._progress_percentage < 100:
            if self._status != TaskStatus.BLOCKED:  # Don't override blocked
                self._status = TaskStatus.IN_PROGRESS
                self.task_data["status"] = "in_progress"
        elif self._progress_percentage == 100:
            self._status = TaskStatus.DONE
            self.task_data["status"] = "done"

    # ========== BACKWARD COMPATIBLE SERIALIZATION ==========

    def dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary (BACKWARD COMPATIBLE).
        This method preserved for existing serialization code.
        """
        # Return task_data (which is kept in sync with domain fields)
        return {
            "id": self.id,
            "branch_id": self.branch_id,
            "task_id": self.task_id,
            **self.task_data  # Includes all domain state
        }

    def to_dict(self) -> Dict[str, Any]:
        """Alias for dict() (some code uses this)."""
        return self.dict()
```

**Migration Strategy**:
1. **Week 8**: Add rich methods to TaskContextUnified
2. **Backward Compatibility**: Keep `task_data` dict in sync with new fields
3. **Week 8**: Existing serialization (`dict()`) continues to work
4. **Week 9**: Update application layer to use rich methods
5. **Week 10**: Validation and rollout

**Feature Flag**: Not needed - enrichment is additive, doesn't break existing code

**Testing**:
```python
# tests/unit/domain/entities/test_context_rich_model.py
def test_update_progress_validates_range():
    context = TaskContextUnified(id="1", branch_id="b1", task_id="t1")

    with pytest.raises(ValidationException):
        context.update_progress(150)  # Out of range

def test_update_progress_prevents_decrease():
    context = TaskContextUnified(id="1", branch_id="b1", task_id="t1")
    context.update_progress(50)

    with pytest.raises(BusinessRuleViolationException):
        context.update_progress(30)  # Decreasing not allowed

def test_rich_model_backward_compatible_serialization():
    context = TaskContextUnified(id="1", branch_id="b1", task_id="t1")
    context.update_progress(75, notes="Almost done")
    context.add_insight("Found optimization opportunity", category="performance")

    # Old serialization method still works
    data = context.dict()
    assert data["progress_percentage"] == 75
    assert len(data["insights"]) == 1
    assert data["insights"][0]["category"] == "performance"

def test_cannot_complete_with_blockers():
    context = TaskContextUnified(id="1", branch_id="b1", task_id="t1")
    context.add_blocker("Waiting for API access", severity="high")

    with pytest.raises(BusinessRuleViolationException):
        context.mark_complete("Done")
```

**Benefits**:
- ✅ Rich domain model with business logic
- ✅ Business rules enforced (progress validation, blocker management)
- ✅ Backward compatible serialization
- ✅ No breaking changes to existing code
- ✅ Gradual adoption - can use old or new interface

---

### Violation High #2: Serialization in Domain Entities

**Problem**: `domain/entities/context.py` - Domain entities have `dict()` methods for serialization

**Solution**: Create serializer in infrastructure layer, adapt gradually

---

#### Step 4.2: Create Context Serializer
**File**: `infrastructure/serializers/context_serializer.py` (NEW)

```python
"""
Context serialization in infrastructure layer.
Separates presentation concerns from domain logic.
"""
from typing import Dict, Any, List
from datetime import datetime

from ...domain.entities.context import (
    TaskContextUnified,
    GlobalContext,
    ProjectContext,
    BranchContext
)
from ...domain.value_objects.priority import Priority
from ...domain.value_objects.task_status import TaskStatus


class ContextSerializer:
    """
    Infrastructure service for context serialization.

    Responsibilities:
    - Convert domain entities to dictionaries for API responses
    - Handle value object serialization
    - Format dates/timestamps
    - Control what fields are exposed externally
    """

    @staticmethod
    def serialize_task_context(context: TaskContextUnified) -> Dict[str, Any]:
        """
        Serialize TaskContextUnified to dictionary.

        Args:
            context: Domain entity to serialize

        Returns:
            Dictionary suitable for API response
        """
        return {
            "id": context.id,
            "branch_id": context.branch_id,
            "task_id": context.task_id,
            "progress_percentage": context._progress_percentage,
            "status": str(context._status) if context._status else None,
            "blockers": [
                ContextSerializer._serialize_blocker(b)
                for b in context.task_data.get("blockers", [])
            ],
            "insights": [
                ContextSerializer._serialize_insight(i)
                for i in context.task_data.get("insights", [])
            ],
            "task_data": context.task_data,  # Full data for backward compatibility
        }

    @staticmethod
    def serialize_global_context(context: GlobalContext) -> Dict[str, Any]:
        """Serialize GlobalContext."""
        return {
            "id": context.id,
            "user_id": context.user_id,
            "data": context.data,
            "created_at": ContextSerializer._format_datetime(context.created_at),
            "updated_at": ContextSerializer._format_datetime(context.updated_at),
        }

    @staticmethod
    def serialize_project_context(context: ProjectContext) -> Dict[str, Any]:
        """Serialize ProjectContext."""
        return {
            "id": context.id,
            "project_id": context.project_id,
            "user_id": context.user_id,
            "data": context.data,
            "created_at": ContextSerializer._format_datetime(context.created_at),
            "updated_at": ContextSerializer._format_datetime(context.updated_at),
        }

    @staticmethod
    def serialize_branch_context(context: BranchContext) -> Dict[str, Any]:
        """Serialize BranchContext."""
        return {
            "id": context.id,
            "branch_id": context.git_branch_id,
            "project_id": context.project_id,
            "user_id": context.user_id,
            "data": context.data,
            "created_at": ContextSerializer._format_datetime(context.created_at),
            "updated_at": ContextSerializer._format_datetime(context.updated_at),
        }

    @staticmethod
    def _serialize_blocker(blocker: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize blocker entry."""
        return {
            "description": blocker.get("description", ""),
            "severity": blocker.get("severity", "medium"),
            "added_at": blocker.get("added_at", datetime.utcnow().isoformat())
        }

    @staticmethod
    def _serialize_insight(insight: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize insight entry."""
        return {
            "content": insight.get("content", ""),
            "category": insight.get("category", "technical"),
            "importance": insight.get("importance", "medium"),
            "recorded_at": insight.get("recorded_at", datetime.utcnow().isoformat())
        }

    @staticmethod
    def _format_datetime(dt: Any) -> str:
        """Format datetime to ISO string."""
        if isinstance(dt, datetime):
            return dt.isoformat()
        if isinstance(dt, str):
            return dt
        return datetime.utcnow().isoformat()

    @staticmethod
    def serialize_value_object(obj: Any) -> Any:
        """
        Serialize value objects (Priority, TaskStatus, etc.).

        Args:
            obj: Value object to serialize

        Returns:
            Serialized representation (usually string)
        """
        if isinstance(obj, (Priority, TaskStatus)):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj


class ContextDeserializer:
    """
    Infrastructure service for context deserialization.
    Reconstructs domain entities from dictionaries.
    """

    @staticmethod
    def deserialize_task_context(data: Dict[str, Any]) -> TaskContextUnified:
        """
        Deserialize dictionary to TaskContextUnified.

        Args:
            data: Dictionary from database or API

        Returns:
            TaskContextUnified domain entity
        """
        # Extract core fields
        id = data.get("id")
        branch_id = data.get("branch_id")
        task_id = data.get("task_id")

        # Task data (everything else)
        task_data = {k: v for k, v in data.items() if k not in ["id", "branch_id", "task_id"]}

        # Create entity (will auto-initialize from task_data)
        return TaskContextUnified(
            id=id,
            branch_id=branch_id,
            task_id=task_id,
            task_data=task_data
        )

    # Similar deserialize methods for other context types...
```

---

#### Step 4.3: Update Application Layer to Use Serializer (Adapter)
**File**: `application/facades/unified_context_facade.py` (example usage)

**Old Code**:
```python
def get_context(self, context_id: str) -> Dict[str, Any]:
    context = self.context_repository.get(context_id)
    return context.dict()  # Domain entity serialization
```

**New Code** (Adapter Pattern):
```python
from ...infrastructure.serializers.context_serializer import ContextSerializer
from ...shared.config.feature_flags import get_feature_flags

class UnifiedContextFacade:
    def __init__(self):
        self._serializer = ContextSerializer()
        self._flags = get_feature_flags()

    def get_context(self, context_id: str) -> Dict[str, Any]:
        """Get context with serialization based on feature flag."""
        context = self.context_repository.get(context_id)

        if self._flags.is_enabled("use_context_serializer"):
            # NEW: Use infrastructure serializer
            return self._serializer.serialize_task_context(context)
        else:
            # OLD: Use domain entity method
            return context.dict()
```

**Migration Path**:
1. Week 8-9: Create ContextSerializer
2. Week 9: Update facades to support both paths
3. Week 9: Shadow mode testing
4. Week 10: Enable flag `USE_CONTEXT_SERIALIZER=true`
5. Phase 8: Remove `dict()` methods from domain entities

**Rollback**: Set `USE_CONTEXT_SERIALIZER=false`

---

### Phase 4 Deliverables

**Modified Files**:
1. ✅ `domain/entities/context.py` (enriched with business methods)

**Created Files**:
1. ✅ `infrastructure/serializers/context_serializer.py`
2. ✅ `infrastructure/serializers/__init__.py`

**Tests Created**:
1. ✅ `tests/unit/domain/entities/test_context_rich_model.py`
2. ✅ `tests/unit/infrastructure/serializers/test_context_serializer.py`
3. ✅ `tests/integration/application/test_facade_with_serializer.py`

**Feature Flags**:
- `USE_CONTEXT_SERIALIZER=false` (default)

**Acceptance Criteria**:
- [ ] TaskContextUnified has rich business methods
- [ ] Business rules enforced (progress validation, blocker management)
- [ ] Backward compatible serialization maintained
- [ ] ContextSerializer handles all context types
- [ ] Application layer works with both old and new serialization
- [ ] Shadow mode validates identical output
- [ ] All tests pass
- [ ] No breaking changes to MCP tool responses

**Effort**: 3 weeks (15 working days)
**Confidence**: 85% - Requires careful serialization compatibility testing

---

## Phase 5: Controller Refactoring (Week 11-13)

### Goals
- ✅ Thin controllers without changing MCP tool signatures
- ✅ Address: Critical #5, High #5, High #6, Medium #6
- ✅ Extract parameter normalization
- ✅ Extract authorization logic
- ✅ Maintain exact MCP tool interfaces

### Violation Critical #5: Fat Controller with Business Logic

**Current Problem**: `interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py:420-446`
- Controller contains parameter transformation logic
- String-to-list conversion logic embedded in controller

**Solution**: Extract to ParameterNormalizerService in application layer

---

#### Step 5.1: Create Parameter Normalizer Service
**File**: `application/services/parameter_normalizer_service.py` (NEW)

```python
"""
Parameter normalization service for MCP controllers.
Handles conversion of flexible input formats to standard types.
"""
from typing import Any, List, Dict, Optional, Union


class ParameterNormalizerService:
    """
    Application service for normalizing MCP tool parameters.

    Responsibilities:
    - Convert string → list (comma-separated)
    - Convert string → dict (JSON parsing)
    - Handle flexible boolean formats
    - Standardize parameter formats across MCP tools

    Benefits:
    - Controllers stay thin (no business logic)
    - Consistent parameter handling
    - Easy to test and maintain
    - Reusable across all MCP controllers
    """

    @staticmethod
    def normalize_list_parameter(
        value: Union[str, List[str], None],
        delimiter: str = ","
    ) -> Optional[List[str]]:
        """
        Normalize parameter to list of strings.

        Args:
            value: Input value (string, list, or None)
            delimiter: Delimiter for string splitting (default: comma)

        Returns:
            List of strings, or None if input was None

        Examples:
            "agent1,agent2" → ["agent1", "agent2"]
            "agent1" → ["agent1"]
            ["agent1", "agent2"] → ["agent1", "agent2"]
            None → None
            "" → []
        """
        if value is None:
            return None

        # Already a list
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]

        # String conversion
        if isinstance(value, str):
            if not value.strip():
                return []

            # Split by delimiter and clean
            if delimiter in value:
                return [v.strip() for v in value.split(delimiter) if v.strip()]
            else:
                # Single value
                return [value.strip()] if value.strip() else []

        # Fallback: convert to string and wrap in list
        return [str(value).strip()] if value else []

    @staticmethod
    def normalize_dict_parameter(
        value: Union[str, Dict[str, Any], None]
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize parameter to dictionary.

        Args:
            value: Input value (JSON string, dict, or None)

        Returns:
            Dictionary, or None if input was None

        Examples:
            '{"key": "value"}' → {"key": "value"}
            {"key": "value"} → {"key": "value"}
            None → None
        """
        if value is None:
            return None

        # Already a dict
        if isinstance(value, dict):
            return value

        # String conversion (JSON)
        if isinstance(value, str):
            if not value.strip():
                return {}

            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                # Not valid JSON - return as single-key dict
                return {"value": value}

        # Fallback
        return {}

    @staticmethod
    def normalize_boolean_parameter(
        value: Union[str, bool, int, None],
        default: bool = False
    ) -> bool:
        """
        Normalize parameter to boolean.

        Args:
            value: Input value (various formats)
            default: Default value if None

        Returns:
            Boolean value

        Examples:
            "true" → True
            "1" → True
            "yes" → True
            "on" → True
            True → True
            1 → True
            None → default
        """
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return value != 0

        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes", "on"]

        return default

    @staticmethod
    def normalize_assignees(assignees: Union[str, List[str], None]) -> Optional[List[str]]:
        """
        Normalize assignees parameter (wrapper for list normalization).

        Examples:
            "coding-agent,test-agent" → ["coding-agent", "test-agent"]
            "@coding-agent" → ["@coding-agent"]
        """
        return ParameterNormalizerService.normalize_list_parameter(assignees)

    @staticmethod
    def normalize_labels(labels: Union[str, List[str], None]) -> Optional[List[str]]:
        """Normalize labels parameter (wrapper for list normalization)."""
        return ParameterNormalizerService.normalize_list_parameter(labels)

    @staticmethod
    def normalize_dependencies(
        dependencies: Union[str, List[str], None]
    ) -> Optional[List[str]]:
        """Normalize dependencies parameter (wrapper for list normalization)."""
        return ParameterNormalizerService.normalize_list_parameter(dependencies)
```

**Testing**:
```python
# tests/unit/application/services/test_parameter_normalizer_service.py
def test_normalize_list_comma_separated():
    result = ParameterNormalizerService.normalize_list_parameter("a,b,c")
    assert result == ["a", "b", "c"]

def test_normalize_list_single_value():
    result = ParameterNormalizerService.normalize_list_parameter("single")
    assert result == ["single"]

def test_normalize_list_already_list():
    result = ParameterNormalizerService.normalize_list_parameter(["a", "b"])
    assert result == ["a", "b"]

def test_normalize_list_empty_string():
    result = ParameterNormalizerService.normalize_list_parameter("")
    assert result == []

def test_normalize_dict_json_string():
    result = ParameterNormalizerService.normalize_dict_parameter('{"key": "value"}')
    assert result == {"key": "value"}

def test_normalize_boolean_various_formats():
    assert ParameterNormalizerService.normalize_boolean_parameter("true") is True
    assert ParameterNormalizerService.normalize_boolean_parameter("1") is True
    assert ParameterNormalizerService.normalize_boolean_parameter("yes") is True
    assert ParameterNormalizerService.normalize_boolean_parameter("false") is False
    assert ParameterNormalizerService.normalize_boolean_parameter(None, default=True) is True
```

---

#### Step 5.2: Update Controller to Use Normalizer (Adapter)
**File**: `interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py:420-446`

**Old Implementation**:
```python
def manage_task(self, action: str, assignees: str | None = None, **kwargs):
    # BUSINESS LOGIC IN CONTROLLER - WRONG!
    if assignees is not None and isinstance(assignees, str):
        if "," in assignees:
            assignees = [a.strip() for a in assignees.split(",") if a.strip()]
        else:
            assignees = [assignees.strip()] if assignees.strip() else []

    # Similar logic for labels, dependencies...
```

**New Implementation** (Adapter Pattern):
```python
from ....application.services.parameter_normalizer_service import ParameterNormalizerService
from ....shared.config.feature_flags import get_feature_flags

class TaskMcpController:
    def __init__(self):
        self._normalizer = ParameterNormalizerService()
        self._flags = get_feature_flags()

    def manage_task(
        self,
        action: str,
        assignees: str | List[str] | None = None,
        labels: str | List[str] | None = None,
        dependencies: str | List[str] | None = None,
        **kwargs
    ):
        """
        Main MCP tool entry point.
        Signature UNCHANGED - backward compatible.
        """
        # Normalize parameters based on feature flag
        if self._flags.is_enabled("use_parameter_normalizer"):
            # NEW: Use application service
            assignees = self._normalizer.normalize_assignees(assignees)
            labels = self._normalizer.normalize_labels(labels)
            dependencies = self._normalizer.normalize_dependencies(dependencies)
        else:
            # OLD: Inline logic (backward compatibility)
            assignees = self._normalize_assignees_old(assignees)
            labels = self._normalize_labels_old(labels)
            dependencies = self._normalize_dependencies_old(dependencies)

        # Delegate to action handlers (unchanged)
        if action == "create":
            return self._handle_create(assignees=assignees, labels=labels, **kwargs)
        # ... other actions

    def _normalize_assignees_old(self, assignees):
        """DEPRECATED: Old inline normalization logic."""
        if assignees is not None and isinstance(assignees, str):
            if "," in assignees:
                return [a.strip() for a in assignees.split(",") if a.strip()]
            else:
                return [assignees.strip()] if assignees.strip() else []
        return assignees

    # Similar old methods for labels, dependencies...
```

**Migration Path**:
1. Week 11: Create ParameterNormalizerService
2. Week 11: Add adapter to controller (both paths available)
3. Week 12: Shadow mode - verify identical results
4. Week 12: Enable flag `USE_PARAMETER_NORMALIZER=true` in dev
5. Week 13: Production rollout
6. Phase 8: Remove old inline normalization logic

**Rollback**: Set `USE_PARAMETER_NORMALIZER=false`

**Benefits**:
- ✅ Controller is thin (no business logic)
- ✅ MCP tool signature UNCHANGED (backward compatible)
- ✅ Parameter handling is testable and reusable
- ✅ Consistent across all MCP tools
- ✅ Zero breaking changes

---

### Violation High #6: Permission Checking in Controller

**Current Problem**: `interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py:852-953`
- 100-line permission checking method in controller
- Authorization logic mixed with interface layer

**Solution**: Extract to AuthorizationService in application layer

---

#### Step 5.3: Create Authorization Service
**File**: `application/services/authorization_service.py` (NEW)

```python
"""
Authorization service for task and resource access control.
Handles permission checks for user access to tasks, projects, branches.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ...domain.entities.task import Task
from ...domain.entities.project import Project
from ...domain.entities.git_branch import GitBranch
from ...domain.exceptions.base_exceptions import (
    AuthorizationException,
    ResourceNotFoundException
)
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)


@dataclass
class AuthorizationResult:
    """Result of authorization check."""
    is_authorized: bool
    reason: Optional[str] = None
    required_permission: Optional[str] = None


class AuthorizationService:
    """
    Application service for authorization and permission checks.

    Responsibilities:
    - Check if user can access/modify tasks
    - Check if user can access/modify projects
    - Check if user can access/modify git branches
    - Enforce role-based access control (if applicable)

    Benefits:
    - Centralized authorization logic
    - Consistent permission checks
    - Easier to audit and modify rules
    - Testable in isolation
    """

    def __init__(
        self,
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        self.task_repository = task_repository
        self.project_repository = project_repository

    def can_user_access_task(
        self,
        user_id: str,
        task_id: str
    ) -> AuthorizationResult:
        """
        Check if user can access a task.

        Args:
            user_id: User attempting access
            task_id: Task being accessed

        Returns:
            AuthorizationResult with authorization decision
        """
        try:
            task = self.task_repository.get(task_id)
        except ResourceNotFoundException:
            return AuthorizationResult(
                is_authorized=False,
                reason="Task not found",
                required_permission="task.read"
            )

        # Business rule: User can access task if they're assigned or own the project
        if self._is_user_assigned_to_task(user_id, task):
            return AuthorizationResult(is_authorized=True)

        if self._is_user_project_owner(user_id, task.project_id):
            return AuthorizationResult(is_authorized=True)

        # Default: deny access
        return AuthorizationResult(
            is_authorized=False,
            reason="User not assigned to task or project",
            required_permission="task.read"
        )

    def can_user_modify_task(
        self,
        user_id: str,
        task_id: str
    ) -> AuthorizationResult:
        """
        Check if user can modify a task.

        Args:
            user_id: User attempting modification
            task_id: Task being modified

        Returns:
            AuthorizationResult with authorization decision
        """
        # First check read access
        read_result = self.can_user_access_task(user_id, task_id)
        if not read_result.is_authorized:
            return AuthorizationResult(
                is_authorized=False,
                reason=read_result.reason,
                required_permission="task.write"
            )

        # Business rule: Can modify if can read (for now)
        # Can add more restrictive rules here (e.g., only assignees can modify)
        return AuthorizationResult(is_authorized=True)

    def can_user_complete_task(
        self,
        user_id: str,
        task_id: str
    ) -> AuthorizationResult:
        """
        Check if user can complete a task.

        Args:
            user_id: User attempting completion
            task_id: Task being completed

        Returns:
            AuthorizationResult with authorization decision
        """
        task = self.task_repository.get(task_id)

        # Business rule: Only assignees can complete tasks
        if not self._is_user_assigned_to_task(user_id, task):
            return AuthorizationResult(
                is_authorized=False,
                reason="Only assigned users can complete tasks",
                required_permission="task.complete"
            )

        return AuthorizationResult(is_authorized=True)

    def can_user_delete_task(
        self,
        user_id: str,
        task_id: str
    ) -> AuthorizationResult:
        """
        Check if user can delete a task.

        Args:
            user_id: User attempting deletion
            task_id: Task being deleted

        Returns:
            AuthorizationResult with authorization decision
        """
        task = self.task_repository.get(task_id)

        # Business rule: Only project owners can delete tasks
        if not self._is_user_project_owner(user_id, task.project_id):
            return AuthorizationResult(
                is_authorized=False,
                reason="Only project owners can delete tasks",
                required_permission="task.delete"
            )

        return AuthorizationResult(is_authorized=True)

    def require_task_access(self, user_id: str, task_id: str) -> None:
        """
        Require task access or raise exception.

        Args:
            user_id: User attempting access
            task_id: Task being accessed

        Raises:
            AuthorizationException: If access denied
        """
        result = self.can_user_access_task(user_id, task_id)
        if not result.is_authorized:
            raise AuthorizationException(
                message=f"Access denied: {result.reason}",
                required_permission=result.required_permission,
                user_id=user_id,
                resource_id=task_id
            )

    def require_task_modification(self, user_id: str, task_id: str) -> None:
        """Require task modification permission or raise exception."""
        result = self.can_user_modify_task(user_id, task_id)
        if not result.is_authorized:
            raise AuthorizationException(
                message=f"Modification denied: {result.reason}",
                required_permission=result.required_permission,
                user_id=user_id,
                resource_id=task_id
            )

    # Helper methods

    def _is_user_assigned_to_task(self, user_id: str, task: Task) -> bool:
        """Check if user is assigned to task."""
        if hasattr(task, 'assignees'):
            return user_id in [a.user_id for a in task.assignees]
        return False

    def _is_user_project_owner(self, user_id: str, project_id: str) -> bool:
        """Check if user owns the project."""
        try:
            project = self.project_repository.get(project_id)
            return project.owner_id == user_id
        except ResourceNotFoundException:
            return False
```

**Testing**:
```python
# tests/unit/application/services/test_authorization_service.py
def test_user_can_access_assigned_task():
    # Setup
    task = Task(id="t1", project_id="p1", assignees=[Agent(user_id="user1")])
    task_repo = Mock()
    task_repo.get.return_value = task

    service = AuthorizationService(task_repo, Mock())

    # Test
    result = service.can_user_access_task("user1", "t1")
    assert result.is_authorized is True

def test_user_cannot_access_unassigned_task():
    task = Task(id="t1", project_id="p1", assignees=[])
    task_repo = Mock()
    task_repo.get.return_value = task
    project_repo = Mock()
    project_repo.get.return_value = Project(id="p1", owner_id="other_user")

    service = AuthorizationService(task_repo, project_repo)

    result = service.can_user_access_task("user1", "t1")
    assert result.is_authorized is False
    assert "not assigned" in result.reason

def test_require_task_access_raises_on_denial():
    task_repo = Mock()
    task_repo.get.side_effect = ResourceNotFoundException("Task not found")

    service = AuthorizationService(task_repo, Mock())

    with pytest.raises(AuthorizationException):
        service.require_task_access("user1", "t1")
```

---

#### Step 5.4: Update Controller to Use Authorization Service (Adapter)
**File**: `interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py:852-953`

**Old Implementation**:
```python
def _check_task_permissions(self, user_id: str, task_id: str, action: str) -> bool:
    """100+ lines of permission checking logic in controller - WRONG!"""
    task = self.task_facade.get_task(task_id)
    # ... complex permission logic ...
```

**New Implementation** (Adapter Pattern):
```python
from ....application.services.authorization_service import AuthorizationService
from ....shared.config.feature_flags import get_feature_flags

class TaskMcpController:
    def __init__(self, task_facade, authorization_service: Optional[AuthorizationService] = None):
        self.task_facade = task_facade
        self._authorization_service = authorization_service  # Injected
        self._flags = get_feature_flags()

    def manage_task(self, action: str, user_id: str, task_id: str = None, **kwargs):
        """Main MCP tool entry point."""

        # Permission check based on feature flag
        if task_id and action in ["update", "complete", "delete"]:
            if self._flags.is_enabled("use_authorization_service"):
                # NEW: Use application service
                self._check_permissions_new(user_id, task_id, action)
            else:
                # OLD: Inline logic
                self._check_task_permissions_old(user_id, task_id, action)

        # Proceed with action handling (unchanged)
        if action == "create":
            return self._handle_create(user_id=user_id, **kwargs)
        # ... other actions

    def _check_permissions_new(self, user_id: str, task_id: str, action: str) -> None:
        """NEW: Use AuthorizationService for permission checks."""
        if action == "update":
            self._authorization_service.require_task_modification(user_id, task_id)
        elif action == "complete":
            result = self._authorization_service.can_user_complete_task(user_id, task_id)
            if not result.is_authorized:
                raise AuthorizationException(
                    message=result.reason,
                    required_permission=result.required_permission
                )
        elif action == "delete":
            result = self._authorization_service.can_user_delete_task(user_id, task_id)
            if not result.is_authorized:
                raise AuthorizationException(
                    message=result.reason,
                    required_permission=result.required_permission
                )

    def _check_task_permissions_old(self, user_id: str, task_id: str, action: str) -> bool:
        """DEPRECATED: Old 100-line permission check - will be removed in Phase 8."""
        # ... existing 100+ line logic unchanged ...
        pass
```

**Migration Path**:
1. Week 11-12: Create AuthorizationService
2. Week 12: Add adapter to controller (both paths available)
3. Week 12: Shadow mode - verify identical results
4. Week 13: Enable flag `USE_AUTHORIZATION_SERVICE=true`
5. Week 13: Production rollout
6. Phase 8: Remove old permission check method

**Rollback**: Set `USE_AUTHORIZATION_SERVICE=false`

**Benefits**:
- ✅ Controller is thin (100+ lines removed)
- ✅ Authorization logic testable in isolation
- ✅ Consistent permission checks across all controllers
- ✅ MCP tool behavior unchanged
- ✅ Zero breaking changes

---

### Phase 5 Deliverables

**Created Files**:
1. ✅ `application/services/parameter_normalizer_service.py`
2. ✅ `application/services/authorization_service.py`

**Modified Files** (with adapters):
1. ✅ `interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py`
2. ✅ `interface/api_controllers/task_api_controller.py` (similar changes)

**Tests Created**:
1. ✅ `tests/unit/application/services/test_parameter_normalizer_service.py`
2. ✅ `tests/unit/application/services/test_authorization_service.py`
3. ✅ `tests/integration/interface/test_controller_with_services.py`

**Feature Flags**:
- `USE_PARAMETER_NORMALIZER=false` (default)
- `USE_AUTHORIZATION_SERVICE=false` (default)

**Acceptance Criteria**:
- [ ] ParameterNormalizerService handles all parameter formats
- [ ] AuthorizationService implements all permission checks
- [ ] Controllers work with both old and new services
- [ ] MCP tool signatures UNCHANGED (critical!)
- [ ] Shadow mode validates identical behavior
- [ ] All tests pass
- [ ] Rollback procedures tested
- [ ] No breaking changes to external APIs

**Effort**: 3 weeks (15 working days)
**Confidence**: 90% - Well-isolated changes, external interface unchanged

---

## Summary of Phases 6-8

*Due to length constraints, I'll provide condensed versions of the remaining phases. Each follows the same Strangler Fig + Feature Toggle pattern established above.*

---

## Phase 6: Domain Service Relocation (Week 14-15)

### Violation Critical #2: Orchestrator in Domain Layer

**Migration**:
1. Create `application/services/project_orchestration_service.py` (NEW)
2. Copy Orchestrator logic to application layer
3. Adapter pattern: Both implementations available
4. Feature flag: `USE_NEW_ORCHESTRATOR`
5. Gradual cutover, then remove old

**Key Points**:
- Orchestrator is application-level workflow, not domain logic
- Keep domain services pure (single-entity business rules)
- No breaking changes - both versions work identically

**Effort**: 2 weeks
**Confidence**: 95%

---

## Phase 7: Cross-Cutting Concerns (Week 16-17)

### Violations High #7, High #8, Medium #7

**Tasks**:
1. **Define Aggregate Boundaries**:
   - Document Task, Project, GitBranch as aggregate roots
   - Enforce invariants through aggregate roots only

2. **Fix Dependency Directions**:
   - Audit: Interface → Application → Domain ← Infrastructure
   - Remove any reverse dependencies

3. **Document Ubiquitous Language**:
   - Create glossary in `ai_docs/core-architecture/ubiquitous-language.md`
   - Standardize terminology across codebase

**Effort**: 2 weeks
**Confidence**: 85%

---

## Phase 8: Cleanup & Documentation (Week 18)

### Goals
- Remove old implementations after confidence period
- Update documentation
- Final testing and validation

**Tasks**:
1. **Code Cleanup**:
   - Remove all `_old()` methods
   - Remove old inline logic from controllers
   - Clean up adapters and feature flags

2. **Documentation**:
   - Update architecture docs
   - Document new patterns
   - Create migration guide for future refactorings

3. **Final Validation**:
   - Full regression testing
   - Performance benchmarking
   - Security audit

**Effort**: 1 week
**Confidence**: 100%

---

## Testing Strategy

### Unit Testing Requirements

**Per Phase**:
- [ ] 100% coverage of new services
- [ ] Test both old and new implementations
- [ ] Test feature flag switching
- [ ] Test edge cases and error conditions

**Test Structure**:
```
tests/
├── unit/
│   ├── domain/
│   │   └── entities/test_context_rich_model.py
│   ├── application/
│   │   ├── services/test_parameter_normalizer.py
│   │   └── services/test_authorization.py
│   └── infrastructure/
│       └── uow/test_unit_of_work.py
├── integration/
│   ├── test_facade_with_new_services.py
│   └── test_uow_with_repositories.py
└── e2e/
    └── test_mcp_tools_unchanged.py
```

### Integration Testing Strategy

**Shadow Mode Testing**:
```python
# Enable shadow mode
export DDD_SHADOW_MODE=true
export USE_PARAMETER_NORMALIZER=true

# Run integration tests
pytest tests/integration/ -v

# Check logs for differences
grep "Shadow mode difference" logs/refactoring.log
```

### Validation Mode Testing

```python
# Enable validation mode (strict)
export DDD_VALIDATION_MODE=true
export USE_UNIT_OF_WORK=true

# Run tests - will fail if ANY difference
pytest tests/integration/ -v
# Should pass with ZERO failures
```

### Regression Testing

**Critical Test Suite** (must pass in all phases):
- [ ] All existing MCP tool tests
- [ ] All existing API endpoint tests
- [ ] Database integrity tests
- [ ] Performance benchmarks (no degradation)
- [ ] Security tests

---

## Performance Benchmarks

### Baseline Metrics (Before Refactoring)

**Measure**:
- Task creation time
- Task listing time
- Context resolution time
- Database query count
- Memory usage

**Acceptance Criteria**:
- Performance degradation < 5%
- Query count unchanged or reduced
- Memory usage unchanged or reduced

### Monitoring During Rollout

**Metrics to Track**:
- Response times (p50, p95, p99)
- Error rates
- Database connection pool usage
- Cache hit rates

**Alerts**:
- Response time > 1.5x baseline → investigate
- Error rate > 0.1% → rollback
- Database timeouts → rollback

---

## Rollback Procedures Summary

### Instant Rollback (Master Switch)
```bash
# .env
DDD_REFACTOR_ENABLED=false

# Restart
docker-compose restart backend
```

### Granular Rollback (Per Feature)
```bash
# Disable specific feature
USE_UNIT_OF_WORK=false
USE_PARAMETER_NORMALIZER=false
# etc.

# Restart
docker-compose restart backend
```

### Git Rollback (Emergency)
```bash
git revert <refactoring-commit>
./docker-system/docker-menu.sh  # Option R
```

---

## Success Metrics

### Phase Completion Criteria

**Each phase must achieve**:
- [ ] All new tests pass
- [ ] All existing tests still pass
- [ ] Shadow mode shows < 0.1% differences
- [ ] Validation mode passes 100%
- [ ] Performance within 5% of baseline
- [ ] Rollback procedure tested successfully
- [ ] Documentation updated

### Overall Success Criteria

**Project complete when**:
- [ ] All 23 violations addressed
- [ ] Zero breaking changes introduced
- [ ] All feature flags enabled in production
- [ ] Old code removed (Phase 8)
- [ ] Documentation complete
- [ ] DDD compliance > 90%

---

## Risk Mitigation

### High-Risk Areas

**Phase 3 (Infrastructure)**:
- **Risk**: Session management changes could cause data corruption
- **Mitigation**: Extensive transaction testing, use UoW in shadow mode for 1 week

**Phase 4 (Domain Enrichment)**:
- **Risk**: Serialization changes could break MCP tools
- **Mitigation**: Parallel serialization testing, validate all MCP responses identical

**Phase 5 (Controllers)**:
- **Risk**: Parameter changes could break MCP signatures
- **Mitigation**: Keep signatures EXACTLY the same, only change internals

### Contingency Plans

**If Shadow Mode Shows Differences**:
1. Identify root cause of difference
2. Fix new implementation to match old
3. Re-run shadow mode until 100% match
4. Only then proceed to enable feature flag

**If Production Issues Occur**:
1. Immediate rollback via feature flag
2. Investigate in dev environment
3. Fix and re-test
4. Gradual re-rollout with monitoring

---

## Timeline Summary

| Phase | Duration | Effort | Confidence |
|-------|----------|--------|------------|
| 1: Foundation | Week 1-2 | 2 weeks | 100% |
| 2: Application Layer | Week 3-4 | 2 weeks | 95% |
| 3: Infrastructure | Week 5-7 | 3 weeks | 90% |
| 4: Domain Enrichment | Week 8-10 | 3 weeks | 85% |
| 5: Controllers | Week 11-13 | 3 weeks | 90% |
| 6: Orchestrator | Week 14-15 | 2 weeks | 95% |
| 7: Cross-Cutting | Week 16-17 | 2 weeks | 85% |
| 8: Cleanup | Week 18 | 1 week | 100% |
| **TOTAL** | **18 weeks** | **18 weeks** | **92% avg** |

---

## Conclusion

This implementation plan ensures **ZERO breaking changes** through:

1. **Strangler Fig Pattern**: New code grows alongside old, gradual replacement
2. **Feature Toggles**: Runtime switches enable instant rollback
3. **Adapter Pattern**: Both implementations available during transition
4. **Parallel Testing**: Shadow and validation modes ensure correctness
5. **Backward Compatibility**: External interfaces unchanged throughout

**Key Principles**:
- ✅ Application keeps working at all times
- ✅ MCP tool signatures never change
- ✅ Rollback always available (< 5 minutes)
- ✅ Comprehensive testing at every step
- ✅ Gradual, confident progression

**Final State**:
- ✅ All 23 DDD violations addressed
- ✅ 90%+ DDD compliance achieved
- ✅ Clean, maintainable codebase
- ✅ Zero production incidents
- ✅ Team confidence in architecture

---

**Document Version**: 1.0
**Created**: 2025-10-09
**Author**: System Architect Agent
**Status**: Ready for Implementation
