"""
DEPRECATED: Orchestrator Router Tests

These tests verified the Strangler Fig pattern feature flag behavior for
migrating from domain orchestrator to application orchestrator.

MIGRATION COMPLETE:
- Feature flag FEATURE_APPLICATION_ORCHESTRATOR has been removed
- Domain orchestrator has been deprecated
- Application orchestrator is now the only implementation

This test file is no longer needed as:
1. The feature flag no longer exists
2. There is only one orchestrator implementation (application layer)
3. The router now always returns the application orchestrator

The orchestrator functionality itself is tested in:
- tests/unit/application/orchestration/test_project_orchestrator.py

This file can be safely removed.
"""

# This file is kept as a marker indicating the migration is complete.
# All functionality has moved to the application layer.
# No tests are needed here as there's no longer a routing decision to test.
