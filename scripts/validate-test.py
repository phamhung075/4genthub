#!/usr/bin/env python3
"""Validate test by running test methods directly"""

import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

# Setup path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')
os.chdir('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main')

# Set required env var
os.environ["HOOK_JWT_SECRET"] = "test-secret-key-for-hook-auth"

try:
    # Import the module
    from fastmcp.auth.hook_auth import (
        HookAuthValidator,
        HOOK_JWT_SECRET,
        HOOK_JWT_ALGORITHM
    )
    from jose import jwt

    # Run a simple test
    print("Testing HookAuthValidator.validate_hook_token with valid token...")

    validator = HookAuthValidator()

    # Create a valid token
    payload = {
        "sub": "test-user",
        "type": "api_token",
        "iss": "dhafnck-mcp",
        "aud": "mcp-server",
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    }
    token = jwt.encode(payload, HOOK_JWT_SECRET, algorithm=HOOK_JWT_ALGORITHM)

    # Validate
    result = validator.validate_hook_token(token)

    # Verify
    assert result["sub"] == "test-user", f"Expected sub='test-user', got {result.get('sub')}"
    assert result["type"] == "api_token", f"Expected type='api_token', got {result.get('type')}"
    assert result["iss"] == "dhafnck-mcp", f"Expected iss='dhafnck-mcp', got {result.get('iss')}"

    print("✓ Test passed: validate_hook_token with valid token")

except AssertionError as e:
    print(f"✗ Test failed: {e}")
except Exception as e:
    print(f"✗ Error running test: {e}")
    import traceback
    traceback.print_exc()