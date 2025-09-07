#!/usr/bin/env python3
"""Test script to verify authentication enforcement.

This script tests that:
1. Operations without authentication throw proper errors
2. Default_id values are rejected
3. Proper authentication is accepted
4. Compatibility mode works when enabled
"""

import os
import sys
import uuid
import traceback

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp.task_management.domain.constants import validate_user_id
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)
from fastmcp.config.auth_config import AuthConfig
from fastmcp.task_management.application.factories.project_facade_factory import (
    ProjectFacadeFactory
)

def test_validate_user_id():
    """Test the validate_user_id function."""
    print("\n=== Testing validate_user_id ===")
    
    # Test 1: None should raise UserAuthenticationRequiredError
    try:
        validate_user_id(None, "Test operation")
        print("❌ FAIL: None should raise UserAuthenticationRequiredError")
    except UserAuthenticationRequiredError as e:
        print(f"✅ PASS: None raised UserAuthenticationRequiredError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 2: Empty string should raise UserAuthenticationRequiredError
    try:
        validate_user_id("", "Test operation")
        print("❌ FAIL: Empty string should raise UserAuthenticationRequiredError")
    except UserAuthenticationRequiredError as e:
        print(f"✅ PASS: Empty string raised UserAuthenticationRequiredError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 3: "default_id" should raise DefaultUserProhibitedError
    try:
        validate_user_id("default_id", "Test operation")
        print("❌ FAIL: 'default_id' should raise DefaultUserProhibitedError")
    except DefaultUserProhibitedError as e:
        print(f"✅ PASS: 'default_id' raised DefaultUserProhibitedError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 4: Zero UUID should raise DefaultUserProhibitedError
    try:
        validate_user_id("00000000-0000-0000-0000-000000000000", "Test operation")
        print("❌ FAIL: Zero UUID should raise DefaultUserProhibitedError")
    except DefaultUserProhibitedError as e:
        print(f"✅ PASS: Zero UUID raised DefaultUserProhibitedError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 5: Valid UUID should pass
    try:
        valid_uuid = str(uuid.uuid4())
        result = validate_user_id(valid_uuid, "Test operation")
        if result == valid_uuid:
            print(f"✅ PASS: Valid UUID accepted: {valid_uuid}")
        else:
            print(f"❌ FAIL: Valid UUID returned different value: {result}")
    except Exception as e:
        print(f"❌ FAIL: Valid UUID raised exception: {e}")
    
    # Test 6: Valid string should pass
    try:
        valid_user = "user-123-abc"
        result = validate_user_id(valid_user, "Test operation")
        if result == valid_user:
            print(f"✅ PASS: Valid string accepted: {valid_user}")
        else:
            print(f"❌ FAIL: Valid string returned different value: {result}")
    except Exception as e:
        print(f"❌ FAIL: Valid string raised exception: {e}")

def test_compatibility_mode():
    """Test the compatibility mode configuration."""
    print("\n=== Testing Compatibility Mode ===")
    
    # Test with compatibility mode OFF (default)
    print("\n--- Compatibility Mode OFF ---")
    os.environ['ALLOW_DEFAULT_USER'] = 'false'
    
    if not AuthConfig.is_default_user_allowed():
        print("✅ PASS: Default user is not allowed")
    else:
        print("❌ FAIL: Default user should not be allowed")
    
    try:
        AuthConfig.get_fallback_user_id()
        print("❌ FAIL: get_fallback_user_id should raise exception")
    except UserAuthenticationRequiredError as e:
        print(f"✅ PASS: get_fallback_user_id raised exception: {e}")
    
    # Test with compatibility mode ON
    print("\n--- Compatibility Mode ON ---")
    os.environ['ALLOW_DEFAULT_USER'] = 'true'
    
    if AuthConfig.is_default_user_allowed():
        print("✅ PASS: Default user is allowed in compatibility mode")
    else:
        print("❌ FAIL: Default user should be allowed in compatibility mode")
    
    try:
        fallback_id = AuthConfig.get_fallback_user_id()
        if fallback_id == "compatibility-default-user":
            print(f"✅ PASS: get_fallback_user_id returned: {fallback_id}")
        else:
            print(f"❌ FAIL: Unexpected fallback ID: {fallback_id}")
    except Exception as e:
        print(f"❌ FAIL: get_fallback_user_id raised exception: {e}")
    
    # Reset to default
    os.environ['ALLOW_DEFAULT_USER'] = 'false'

def test_facade_factory():
    """Test the project facade factory authentication requirements."""
    print("\n=== Testing Project Facade Factory ===")
    
    factory = ProjectFacadeFactory()
    
    # Test 1: Creating facade without user_id should fail
    print("\n--- Test missing user_id ---")
    try:
        # This should fail because create_project_facade now requires user_id
        # and doesn't have a default parameter
        # Note: This will cause a TypeError since the parameter is required
        factory.create_project_facade()  # type: ignore
        print("❌ FAIL: Should have raised error for missing user_id")
    except TypeError as e:
        if "missing" in str(e).lower() and "user_id" in str(e):
            print(f"✅ PASS: Missing user_id parameter raised TypeError: {e}")
        else:
            print(f"❌ FAIL: Unexpected TypeError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 2: Creating facade with None should fail
    print("\n--- Test None user_id ---")
    try:
        factory.create_project_facade(user_id=None)  # type: ignore
        print("❌ FAIL: None user_id should raise UserAuthenticationRequiredError")
    except UserAuthenticationRequiredError as e:
        print(f"✅ PASS: None user_id raised UserAuthenticationRequiredError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 3: Creating facade with "default_id" should fail
    print("\n--- Test default_id ---")
    try:
        factory.create_project_facade(user_id="default_id")
        print("❌ FAIL: 'default_id' should raise DefaultUserProhibitedError")
    except DefaultUserProhibitedError as e:
        print(f"✅ PASS: 'default_id' raised DefaultUserProhibitedError: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
    
    # Test 4: Creating facade with valid user_id should work
    print("\n--- Test valid user_id ---")
    try:
        valid_user_id = str(uuid.uuid4())
        facade = factory.create_project_facade(user_id=valid_user_id)
        if facade:
            print(f"✅ PASS: Created facade with valid user_id: {valid_user_id}")
        else:
            print(f"❌ FAIL: No facade returned")
    except Exception as e:
        print(f"❌ FAIL: Valid user_id raised exception: {e}")
        traceback.print_exc()

def main():
    """Run all tests."""
    print("=" * 60)
    print("AUTHENTICATION ENFORCEMENT TEST SUITE")
    print("=" * 60)
    
    test_validate_user_id()
    test_compatibility_mode()
    test_facade_factory()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()