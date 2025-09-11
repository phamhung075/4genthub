"""
Integration Tests for MCP Auto-Injection System

This package contains integration tests that verify the interactions between
different components of the MCP auto-injection system. These tests validate
end-to-end workflows and component communication patterns.

Test Categories:
- Hook-to-MCP Server Communication
- Authentication Flow with Keycloak
- Cache Integration with Session Context
- Fallback Strategy Validation
- Cross-Component Error Handling

Coverage Focus: Component interactions and data flow validation
"""

import pytest
import sys
from pathlib import Path

# Add hooks and source directories to Python path
hooks_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude" / "hooks"
src_path = Path(__file__).parent.parent.parent.parent / "src"

for path in [hooks_path, src_path]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))