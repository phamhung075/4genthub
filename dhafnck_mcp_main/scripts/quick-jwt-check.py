#!/usr/bin/env python3
"""
Quick JWT Configuration Check Script

Simple script to verify JWT configuration without complex dependencies.
"""

import os
import sys
import jwt
from datetime import datetime, timedelta, timezone

def main():
    print("🔍 Quick JWT Configuration Check")
    print("=" * 40)
    
    # Check environment variables
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    issues = []
    
    # Check JWT_SECRET_KEY
    if not jwt_secret:
        issues.append("❌ JWT_SECRET_KEY not defined")
    else:
        print(f"✅ JWT_SECRET_KEY defined ({len(jwt_secret)} characters)")
        if jwt_secret == "default-secret-key-change-in-production":
            issues.append("⚠️  JWT_SECRET_KEY is using default value (insecure)")
        elif len(jwt_secret) < 32:
            issues.append(f"⚠️  JWT_SECRET_KEY is short ({len(jwt_secret)} chars, recommend 32+)")
    
    # Check SUPABASE_JWT_SECRET
    if not supabase_secret:
        issues.append("❌ SUPABASE_JWT_SECRET not defined")
    else:
        print(f"✅ SUPABASE_JWT_SECRET defined ({len(supabase_secret)} characters)")
    
    # Check consistency
    if jwt_secret and supabase_secret:
        if jwt_secret == supabase_secret:
            print("✅ JWT secrets match - authentication should work")
        else:
            issues.append("⚠️  JWT secrets mismatch - may cause authentication issues")
            print(f"   Backend uses: JWT_SECRET_KEY ({len(jwt_secret)} chars)")
            print(f"   Frontend uses: SUPABASE_JWT_SECRET ({len(supabase_secret)} chars)")
    
    # Test JWT functionality if we have a secret
    test_secret = jwt_secret or supabase_secret
    if test_secret:
        print("\n🔧 Testing JWT functionality...")
        
        # Test token generation
        try:
            payload = {
                'user_id': 'test-user-123',
                'email': 'test@example.com',
                'type': 'api_token',
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(hours=1)
            }
            
            token = jwt.encode(payload, test_secret, algorithm="HS256")
            print(f"✅ JWT token generation successful ({len(token)} chars)")
            
            # Test token validation
            decoded = jwt.decode(token, test_secret, algorithms=["HS256"])
            print(f"✅ JWT token validation successful (user: {decoded.get('user_id')})")
            
            # Test with both secrets if different
            if jwt_secret and supabase_secret and jwt_secret != supabase_secret:
                print("\n🔀 Testing dual secret compatibility...")
                
                # Generate with frontend secret, validate with backend secret
                frontend_token = jwt.encode(payload, supabase_secret, algorithm="HS256")
                print(f"✅ Token generated with SUPABASE_JWT_SECRET")
                
                try:
                    jwt.decode(frontend_token, jwt_secret, algorithms=["HS256"])
                    print("✅ Backend can validate frontend tokens")
                except jwt.InvalidSignatureError:
                    print("❌ Backend CANNOT validate frontend tokens - this is the problem!")
                
                # Test the opposite
                backend_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
                try:
                    jwt.decode(backend_token, supabase_secret, algorithms=["HS256"])  
                    print("✅ Frontend can validate backend tokens")
                except jwt.InvalidSignatureError:
                    print("❌ Frontend CANNOT validate backend tokens")
            
        except Exception as e:
            issues.append(f"❌ JWT functionality test failed: {e}")
    
    # Summary
    print("\n" + "=" * 40)
    if issues:
        print("🚨 Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 Solutions:")
        if "JWT_SECRET_KEY not defined" in str(issues):
            print("   - Set JWT_SECRET_KEY: export JWT_SECRET_KEY=$(openssl rand -hex 32)")
        if "SUPABASE_JWT_SECRET not defined" in str(issues):
            print("   - Set SUPABASE_JWT_SECRET: export SUPABASE_JWT_SECRET=$(openssl rand -hex 32)")
        if "secrets mismatch" in str(issues):
            print("   - Unify secrets: export SUPABASE_JWT_SECRET=$JWT_SECRET_KEY")
            print("   - Or apply the dual secret fix in DualAuthMiddleware")
        
        return False
    else:
        print("✅ Configuration looks good!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)