"""
End-to-End Tests for MCP Auto-Injection System

This package contains end-to-end tests that validate complete user scenarios
and real-world workflows. These tests use minimal mocking and test actual
system behavior from session start to context injection.

Test Categories:
- Complete Session Lifecycle
- Multi-Tool Interaction Scenarios  
- Context Persistence Validation
- Error Recovery Scenarios
- Real-World Usage Patterns
- Performance Under Load

Coverage Focus: Full system validation with realistic scenarios
"""

import pytest
import sys
import os
from pathlib import Path

# Add all necessary paths for E2E testing
hooks_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude" / "hooks"
src_path = Path(__file__).parent.parent.parent.parent / "src"

for path in [hooks_path, src_path]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Set up E2E test environment variables
os.environ.setdefault("TESTING_MODE", "e2e")
os.environ.setdefault("SESSION_CACHE_TTL", "60")  # Short TTL for E2E tests
os.environ.setdefault("TASK_CACHE_TTL", "30")
os.environ.setdefault("GIT_CACHE_TTL", "15")