"""
Unit tests for MCP Auto-Injection System

This package contains unit tests for all components of the MCP auto-injection system
including token management, cache functionality, client implementations, and hook systems.

Test Categories:
- Token Management (JWT authentication)
- Cache Management (Session context caching)  
- MCP Client (HTTP client implementations)
- Session Hooks (Context injection)
- Performance Monitoring (Metrics and optimization)

Coverage Target: 100% for critical paths
"""

import pytest
import sys
from pathlib import Path

# Add hooks directory to Python path for testing
hooks_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude" / "hooks"
if str(hooks_path) not in sys.path:
    sys.path.insert(0, str(hooks_path))