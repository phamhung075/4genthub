"""
API Contract Tests - Verify backend responses match frontend TypeScript expectations.

This package contains integration tests that document and verify the contract
between backend API responses and frontend TypeScript type definitions.

Following TDD (Test-Driven Development) approach:
1. Tests document expected behavior based on comparison matrix analysis
2. Tests initially FAIL for known mismatches (8 identified)
3. Code is fixed to make tests pass
4. Tests serve as regression prevention

Test Categories:
- test_task_api_contracts.py: Backend API response structure validation
- test_websocket_contracts.py: WebSocket message format validation

Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md
"""
