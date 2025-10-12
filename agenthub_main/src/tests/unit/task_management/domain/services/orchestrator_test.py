"""
DEPRECATED: Domain Orchestrator Tests

These tests verified the domain layer orchestrator which has been deprecated.

MIGRATION COMPLETE:
- Domain orchestrator (domain/services/orchestrator.py) has been deprecated
- Application orchestrator (application/orchestration/project_orchestrator.py) is now the only implementation
- DDD principle: Multi-aggregate coordination belongs in APPLICATION layer, not DOMAIN layer

This test file is no longer needed as:
1. The domain orchestrator has been replaced by the application orchestrator
2. Orchestration is an application service, not a domain service
3. The domain layer should only contain single-aggregate domain services

The orchestrator functionality is now tested in:
- tests/unit/application/orchestration/test_project_orchestrator.py

This file can be safely removed.
"""

# This file is kept as a marker indicating the migration is complete.
# All functionality has moved to the application layer.
# Domain services should only operate on single aggregates.
