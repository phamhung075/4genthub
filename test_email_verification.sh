#!/bin/bash

# Test EMAIL_VERIFIED_AUTO=false behavior

echo "========================================="
echo "Testing EMAIL_VERIFIED_AUTO=false"
echo "========================================="

# Generate unique test email
TIMESTAMP=$(date +%s)
TEST_EMAIL="test_verify_${TIMESTAMP}@example.com"
TEST_USERNAME="testverify_${TIMESTAMP}"
TEST_PASSWORD="TestPass123!"

# First, set EMAIL_VERIFIED_AUTO to false
export EMAIL_VERIFIED_AUTO="false"

echo ""
echo "Step 1: Testing with EMAIL_VERIFIED_AUTO=false"
echo "Username: $TEST_USERNAME"
echo "Email: $TEST_EMAIL"
echo ""

# Register user
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$TEST_USERNAME\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

echo "Registration Response:"
echo "$REGISTER_RESPONSE" | jq '.'

# Check if registration shows email verification is required
if echo "$REGISTER_RESPONSE" | grep -q "check your email"; then
    echo ""
    echo "✅ Registration correctly indicates email verification is required!"
else
    echo ""
    echo "⚠️ Registration should indicate email verification is required"
fi

echo ""
echo "Step 2: Testing login (should fail with email verification message)"
echo ""

# Wait a moment for registration to complete
sleep 2

# Login with the new account (should fail)
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

echo "Login Response:"
echo "$LOGIN_RESPONSE" | jq '.'

# Check if login fails with appropriate message
if echo "$LOGIN_RESPONSE" | grep -q "email"; then
    echo ""
    echo "✅ Login correctly requires email verification!"
elif echo "$LOGIN_RESPONSE" | grep -q "Account is not fully set up"; then
    echo ""
    echo "⚠️ Login failed with generic error - should specify email verification needed"
else
    echo ""
    echo "❌ Unexpected login response"
fi

echo ""
echo "========================================="
echo "Test completed"
echo "========================================="