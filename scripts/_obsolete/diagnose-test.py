#!/usr/bin/env python3
"""Diagnose test failures by running tests in isolation"""

import sys
import os

# Setup path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')
os.chdir('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main')

# Now import and run test
try:
    # Set required env var
    os.environ["HOOK_JWT_SECRET"] = "test-secret-key-for-hook-auth"

    # Try importing the module
    from fastmcp.auth.hook_auth import (
        HookAuthValidator,
        hook_auth_validator,
        get_hook_authenticated_user,
        is_hook_request,
        get_token_from_mcp_json,
        create_hook_token,
        HOOK_JWT_ALGORITHM,
        HOOK_JWT_SECRET
    )
    print("✓ All imports successful")

    # Check if all functions are available
    funcs = [
        HookAuthValidator,
        hook_auth_validator,
        get_hook_authenticated_user,
        is_hook_request,
        get_token_from_mcp_json,
        create_hook_token
    ]

    for func in funcs:
        print(f"✓ {func.__name__ if hasattr(func, '__name__') else func.__class__.__name__} available")

    print(f"✓ HOOK_JWT_ALGORITHM = {HOOK_JWT_ALGORITHM}")
    print(f"✓ HOOK_JWT_SECRET exists = {HOOK_JWT_SECRET is not None}")

except ImportError as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"✗ Other error: {e}")
    import traceback
    traceback.print_exc()