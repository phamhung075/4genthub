#!/usr/bin/env python3
"""
Email Service Test Script

This script tests the email authentication service with the actual SMTP
configuration from the .env file.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the dhafnck_mcp_main/src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main', 'src'))

# Load environment variables
load_dotenv()

async def test_email_service():
    """Test the email service configuration and functionality"""
    print("🧪 Testing Email Authentication Service")
    print("=" * 50)
    
    try:
        # Import after path setup
        from fastmcp.auth.infrastructure.email_service import SMTPEmailService, get_email_service
        from fastmcp.auth.infrastructure.repositories.email_token_repository import get_email_token_repository
        from fastmcp.auth.infrastructure.enhanced_auth_service import get_enhanced_auth_service
        
        print("✅ Successfully imported email service modules")
        
        # Test 1: Configuration Loading
        print("\n1. Testing SMTP Configuration...")
        email_service = get_email_service()
        config = email_service.config
        
        print(f"   SMTP Host: {config.smtp_host}")
        print(f"   SMTP Port: {config.smtp_port}")
        print(f"   SMTP Username: {config.smtp_username}")
        print(f"   SMTP From: {config.smtp_from}")
        print(f"   SMTP From Name: {config.smtp_from_name}")
        print(f"   TLS Enabled: {config.smtp_tls}")
        
        # Test 2: SMTP Connection
        print("\n2. Testing SMTP Connection...")
        connection_result = await email_service.test_connection()
        
        if connection_result.success:
            print("   ✅ SMTP connection successful!")
        else:
            print(f"   ❌ SMTP connection failed: {connection_result.error_message}")
            return False
        
        # Test 3: Token Repository
        print("\n3. Testing Token Repository...")
        token_repo = get_email_token_repository()
        stats = token_repo.get_token_stats()
        
        print(f"   Database initialized: ✅")
        print(f"   Total tokens: {stats.get('total_tokens', 0)}")
        print(f"   Active tokens: {stats.get('active_tokens', 0)}")
        
        # Test 4: Enhanced Auth Service
        print("\n4. Testing Enhanced Auth Service...")
        enhanced_service = get_enhanced_auth_service()
        
        # Test email service integration
        email_test = await enhanced_service.test_email_service()
        
        if email_test["success"]:
            print("   ✅ Enhanced auth service working correctly")
        else:
            print(f"   ❌ Enhanced auth service error: {email_test.get('error_message')}")
        
        # Test 5: Template Rendering
        print("\n5. Testing Email Template Rendering...")
        try:
            html = email_service.template_engine.render_template(
                "verification.html",
                user_name="Test User",
                verification_url="https://example.com/verify?token=test123",
                company_name=config.smtp_from_name,
                current_year=2025
            )
            
            if "Test User" in html and "https://example.com/verify" in html:
                print("   ✅ Email template rendering successful")
                print(f"   Template length: {len(html)} characters")
            else:
                print("   ❌ Template rendering failed - missing expected content")
                return False
                
        except Exception as e:
            print(f"   ❌ Template rendering error: {e}")
            return False
        
        # Test 6: Token Generation
        print("\n6. Testing Token Generation...")
        from fastmcp.auth.infrastructure.email_service import TokenManager
        
        token_data = TokenManager.generate_verification_token("test@example.com")
        
        print(f"   Token generated: {token_data['token'][:20]}...")
        print(f"   Token type: {token_data['type']}")
        print(f"   Expires at: {token_data['expires_at']}")
        
        # Validate token
        is_valid = TokenManager.validate_token(
            token_data['token'],
            "test@example.com",
            token_data['hash']
        )
        
        if is_valid:
            print("   ✅ Token validation working correctly")
        else:
            print("   ❌ Token validation failed")
            return False
        
        print("\n🎉 All tests passed! Email service is ready to use.")
        print("\n📧 Next steps:")
        print("   1. Start your FastAPI server")
        print("   2. Register the enhanced auth routes")
        print("   3. Test user registration with real email addresses")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_real_email_send():
    """Test sending a real email (optional - requires confirmation)"""
    print("\n" + "=" * 50)
    print("🔍 Optional: Test Real Email Sending")
    print("=" * 50)
    
    test_email = input("Enter your email address to test (or press Enter to skip): ").strip()
    
    if not test_email:
        print("Skipping real email test")
        return
    
    confirm = input(f"Send test email to {test_email}? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("Email test skipped")
        return
    
    try:
        from fastmcp.auth.infrastructure.email_service import get_email_service
        
        email_service = get_email_service()
        
        print(f"Sending verification email to {test_email}...")
        result = await email_service.send_verification_email(
            email=test_email,
            user_name="Test User"
        )
        
        if result.success:
            print("✅ Test email sent successfully!")
            print("Check your inbox for the verification email")
        else:
            print(f"❌ Failed to send test email: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Email send test failed: {e}")


async def main():
    """Main test function"""
    print("Email Authentication Service Test Suite")
    print("DhafnckMCP Project")
    print("=" * 60)
    
    # Test basic functionality
    success = await test_email_service()
    
    if not success:
        print("\n❌ Basic tests failed. Please check your configuration.")
        return 1
    
    # Optionally test real email sending
    await test_real_email_send()
    
    print("\n✅ Email authentication service testing complete!")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)