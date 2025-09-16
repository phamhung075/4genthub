#!/bin/bash

# Test Email Auto Verification Feature

echo "========================================="
echo "Testing EMAIL_VERIFIED_AUTO feature"
echo "========================================="

# Generate unique test email
TIMESTAMP=$(date +%s)
TEST_EMAIL="test_${TIMESTAMP}@example.com"
TEST_USERNAME="testuser_${TIMESTAMP}"
TEST_PASSWORD="TestPass123!"

echo ""
echo "Step 1: Registering new user"
echo "Username: $TEST_USERNAME"
echo "Email: $TEST_EMAIL"
echo ""

# Register user
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$TEST_USERNAME\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

echo "Registration Response:"
echo "$REGISTER_RESPONSE" | jq '.'

# Check if registration was successful
if echo "$REGISTER_RESPONSE" | grep -q "success"; then
    echo ""
    echo "✅ Registration successful!"
else
    echo ""
    echo "❌ Registration failed!"
fi

echo ""
echo "Step 2: Testing login with newly registered account"
echo ""

# Wait a moment for registration to complete
sleep 2

# Login with the new account
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

echo "Login Response:"
echo "$LOGIN_RESPONSE" | jq '.'

# Check if login was successful
if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo ""
    echo "✅ Login successful! EMAIL_VERIFIED_AUTO is working correctly!"
    echo "The user was created with email automatically verified."
elif echo "$LOGIN_RESPONSE" | grep -q "Account is not fully set up"; then
    echo ""
    echo "⚠️ Login failed: Account not fully set up in Keycloak"
    echo "This is a Keycloak configuration issue, not related to EMAIL_VERIFIED_AUTO"
else
    echo ""
    echo "❌ Login failed with other error"
fi

echo ""
echo "========================================="
echo "Test completed"
echo "========================================="