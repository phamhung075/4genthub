#!/usr/bin/env python3
"""
JWT Authentication End-to-End Verification Script

This script tests the complete JWT authentication flow:
1. Token generation with different secrets
2. Middleware validation with dual secret support  
3. User context extraction and propagation
4. End-to-end authentication flow

Usage:
    python scripts/jwt-authentication-verification.py
    python scripts/jwt-authentication-verification.py --verbose
    python scripts/jwt-authentication-verification.py --test-endpoints
"""

import os
import sys
import json
import requests
import jwt
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from fastmcp.auth.domain.services.jwt_service import JWTService
except ImportError as e:
    print(f"⚠️  Could not import JWTService: {e}")
    print("Will use manual JWT testing only")
    JWTService = None

# Load environment variables first
try:
    from dotenv import load_dotenv
    env_files = ['.env', '.env.development', '.env.local']
    for env_file in env_files:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"📁 Loaded environment from: {env_file}")
            break
except ImportError:
    print("⚠️  python-dotenv not available, using system environment only")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JWTAuthenticationTester:
    """Comprehensive JWT authentication testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.results = {
            'configuration': {},
            'token_generation': {},
            'token_validation': {},
            'middleware_tests': {},
            'endpoint_tests': {},
            'summary': {'passed': 0, 'failed': 0, 'warnings': 0}
        }
        
        # Set up logging level based on verbosity
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
    def log(self, message: str, level: str = "info"):
        """Log message with appropriate level"""
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "debug":
            logger.debug(message)
            
        if self.verbose or level in ["warning", "error"]:
            print(f"[{level.upper()}] {message}")
    
    def test_configuration(self) -> bool:
        """Test JWT configuration setup"""
        self.log("🔍 Testing JWT Configuration", "info")
        
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        supabase_secret = os.getenv("SUPABASE_JWT_SECRET") 
        
        config_results = {}
        issues = []
        
        # Check JWT_SECRET_KEY
        if not jwt_secret:
            issues.append("JWT_SECRET_KEY not defined")
            config_results['jwt_secret_key'] = {'status': 'missing', 'length': 0}
        else:
            config_results['jwt_secret_key'] = {
                'status': 'present',
                'length': len(jwt_secret),
                'is_default': jwt_secret == "default-secret-key-change-in-production"
            }
            self.log(f"✅ JWT_SECRET_KEY defined ({len(jwt_secret)} characters)")
            
            if jwt_secret == "default-secret-key-change-in-production":
                issues.append("JWT_SECRET_KEY is using default value (insecure)")
            elif len(jwt_secret) < 32:
                issues.append(f"JWT_SECRET_KEY is too short ({len(jwt_secret)} chars, recommend 32+)")
        
        # Check SUPABASE_JWT_SECRET
        if not supabase_secret:
            issues.append("SUPABASE_JWT_SECRET not defined")
            config_results['supabase_jwt_secret'] = {'status': 'missing', 'length': 0}
        else:
            config_results['supabase_jwt_secret'] = {
                'status': 'present', 
                'length': len(supabase_secret)
            }
            self.log(f"✅ SUPABASE_JWT_SECRET defined ({len(supabase_secret)} characters)")
        
        # Check consistency
        if jwt_secret and supabase_secret:
            if jwt_secret == supabase_secret:
                config_results['secrets_match'] = True
                self.log("✅ JWT secrets match - authentication should work")
            else:
                config_results['secrets_match'] = False
                issues.append("JWT secrets mismatch - may cause authentication issues")
                self.log("⚠️  JWT secrets differ - may cause authentication issues", "warning")
                self.log(f"   Backend uses: JWT_SECRET_KEY ({len(jwt_secret)} chars)", "warning")
                self.log(f"   Frontend uses: SUPABASE_JWT_SECRET ({len(supabase_secret)} chars)", "warning")
        
        self.results['configuration'] = config_results
        
        if issues:
            for issue in issues:
                self.log(f"❌ {issue}", "error")
                self.results['summary']['failed'] += 1
            return False
        else:
            self.log("✅ Configuration validation passed")
            self.results['summary']['passed'] += 1
            return True
    
    def test_token_generation(self) -> Dict[str, Any]:
        """Test token generation with different secrets"""
        self.log("🔍 Testing JWT Token Generation", "info")
        
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        generation_results = {}
        test_user_data = {
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        # Test with JWT_SECRET_KEY
        try:
            if JWTService is None:
                raise Exception("JWTService not available")
                
            jwt_service = JWTService(secret_key=jwt_secret)
            jwt_token = jwt_service.create_access_token(
                user_id=test_user_data['user_id'],
                email=test_user_data['email'],
                roles=test_user_data['roles']
            )
            generation_results['jwt_secret_key'] = {
                'status': 'success',
                'token_length': len(jwt_token),
                'token_preview': jwt_token[:50] + "..." if len(jwt_token) > 50 else jwt_token
            }
            self.log(f"✅ Token generated with JWT_SECRET_KEY ({len(jwt_token)} chars)")
            
        except Exception as e:
            generation_results['jwt_secret_key'] = {'status': 'failed', 'error': str(e)}
            self.log(f"❌ Token generation with JWT_SECRET_KEY failed: {e}", "error")
        
        # Test with SUPABASE_JWT_SECRET if different
        if supabase_secret and supabase_secret != jwt_secret:
            try:
                supabase_jwt_service = JWTService(secret_key=supabase_secret)
                supabase_token = supabase_jwt_service.create_access_token(
                    user_id=test_user_data['user_id'],
                    email=test_user_data['email'],
                    roles=test_user_data['roles']
                )
                generation_results['supabase_jwt_secret'] = {
                    'status': 'success',
                    'token_length': len(supabase_token),
                    'token_preview': supabase_token[:50] + "..." if len(supabase_token) > 50 else supabase_token
                }
                self.log(f"✅ Token generated with SUPABASE_JWT_SECRET ({len(supabase_token)} chars)")
                
            except Exception as e:
                generation_results['supabase_jwt_secret'] = {'status': 'failed', 'error': str(e)}
                self.log(f"❌ Token generation with SUPABASE_JWT_SECRET failed: {e}", "error")
        
        # Test manual JWT generation for comparison
        try:
            manual_payload = {
                'user_id': test_user_data['user_id'],
                'email': test_user_data['email'],
                'type': 'api_token',
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(hours=24)
            }
            manual_token = jwt.encode(manual_payload, jwt_secret, algorithm="HS256")
            generation_results['manual_jwt'] = {
                'status': 'success',
                'token_length': len(manual_token),
                'token_preview': manual_token[:50] + "..." if len(manual_token) > 50 else manual_token
            }
            self.log(f"✅ Manual JWT token generated ({len(manual_token)} chars)")
            
        except Exception as e:
            generation_results['manual_jwt'] = {'status': 'failed', 'error': str(e)}
            self.log(f"❌ Manual JWT generation failed: {e}", "error")
        
        self.results['token_generation'] = generation_results
        
        # Return a token for further testing
        if 'jwt_secret_key' in generation_results and generation_results['jwt_secret_key']['status'] == 'success':
            return jwt_token
        elif 'manual_jwt' in generation_results and generation_results['manual_jwt']['status'] == 'success':
            return manual_token
        else:
            return None
    
    def test_token_validation(self, token: str) -> bool:
        """Test token validation with different services"""
        if not token:
            self.log("❌ No token available for validation testing", "error")
            return False
            
        self.log("🔍 Testing JWT Token Validation", "info")
        
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        validation_results = {}
        
        # Test with JWT_SECRET_KEY
        try:
            jwt_service = JWTService(secret_key=jwt_secret)
            payload = jwt_service.verify_token(token, expected_type="access")
            if payload:
                validation_results['jwt_secret_key'] = {
                    'status': 'success',
                    'user_id': payload.get('sub') or payload.get('user_id'),
                    'token_type': payload.get('type'),
                    'expires': payload.get('exp')
                }
                self.log(f"✅ Token validated with JWT_SECRET_KEY (user: {payload.get('sub') or payload.get('user_id')})")
            else:
                validation_results['jwt_secret_key'] = {'status': 'failed', 'error': 'No payload returned'}
                
        except Exception as e:
            validation_results['jwt_secret_key'] = {'status': 'failed', 'error': str(e)}
            self.log(f"❌ Token validation with JWT_SECRET_KEY failed: {e}", "error")
        
        # Test with SUPABASE_JWT_SECRET if different
        if supabase_secret and supabase_secret != jwt_secret:
            try:
                supabase_jwt_service = JWTService(secret_key=supabase_secret)
                payload = supabase_jwt_service.verify_token(token, expected_type="access")
                if payload:
                    validation_results['supabase_jwt_secret'] = {
                        'status': 'success',
                        'user_id': payload.get('sub') or payload.get('user_id'),
                        'token_type': payload.get('type'),
                        'expires': payload.get('exp')
                    }
                    self.log(f"✅ Token validated with SUPABASE_JWT_SECRET (user: {payload.get('sub') or payload.get('user_id')})")
                else:
                    validation_results['supabase_jwt_secret'] = {'status': 'failed', 'error': 'No payload returned'}
                    
            except Exception as e:
                validation_results['supabase_jwt_secret'] = {'status': 'failed', 'error': str(e)}
                self.log(f"❌ Token validation with SUPABASE_JWT_SECRET failed: {e}", "error")
        
        # Test with PyJWT directly
        for secret_name, secret_value in [("JWT_SECRET_KEY", jwt_secret), ("SUPABASE_JWT_SECRET", supabase_secret)]:
            if not secret_value:
                continue
                
            try:
                payload = jwt.decode(token, secret_value, algorithms=["HS256"])
                validation_results[f'direct_{secret_name.lower()}'] = {
                    'status': 'success',
                    'user_id': payload.get('sub') or payload.get('user_id'),
                    'token_type': payload.get('type'),
                    'expires': payload.get('exp')
                }
                self.log(f"✅ Direct PyJWT validation with {secret_name} succeeded")
                
            except jwt.ExpiredSignatureError:
                validation_results[f'direct_{secret_name.lower()}'] = {'status': 'expired', 'error': 'Token expired'}
                self.log(f"⚠️  Direct PyJWT validation with {secret_name}: token expired", "warning")
            except jwt.InvalidTokenError as e:
                validation_results[f'direct_{secret_name.lower()}'] = {'status': 'invalid', 'error': str(e)}
                self.log(f"❌ Direct PyJWT validation with {secret_name} failed: {e}", "error")
        
        self.results['token_validation'] = validation_results
        
        # Count successes
        successes = [r for r in validation_results.values() if r['status'] == 'success']
        if successes:
            self.results['summary']['passed'] += 1
            return True
        else:
            self.results['summary']['failed'] += 1
            return False
    
    def test_endpoints(self, token: str) -> bool:
        """Test authenticated endpoints with the token"""
        if not token:
            self.log("❌ No token available for endpoint testing", "error")
            return False
            
        self.log("🔍 Testing Authenticated Endpoints", "info")
        
        endpoint_results = {}
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Test endpoints
        test_endpoints = [
            {'path': '/health', 'method': 'GET', 'auth_required': False},
            {'path': '/api/v2/projects', 'method': 'GET', 'auth_required': True},
            {'path': '/api/v2/tasks', 'method': 'GET', 'auth_required': True},
            {'path': '/mcp/health', 'method': 'GET', 'auth_required': True},
        ]
        
        for endpoint in test_endpoints:
            path = endpoint['path']
            method = endpoint['method'].upper()
            auth_required = endpoint['auth_required']
            
            try:
                url = f"{self.base_url}{path}"
                
                # Make request with and without auth
                test_headers = headers if auth_required else {}
                
                if method == 'GET':
                    response = requests.get(url, headers=test_headers, timeout=10)
                elif method == 'POST':
                    response = requests.post(url, headers=test_headers, json={}, timeout=10)
                else:
                    continue
                
                endpoint_results[path] = {
                    'status_code': response.status_code,
                    'auth_required': auth_required,
                    'success': response.status_code < 400,
                    'response_size': len(response.content)
                }
                
                if response.status_code < 400:
                    self.log(f"✅ {method} {path} - {response.status_code}")
                elif response.status_code == 401 and auth_required:
                    self.log(f"❌ {method} {path} - 401 Unauthorized (authentication failed)", "error")
                elif response.status_code == 404:
                    self.log(f"⚠️  {method} {path} - 404 Not Found (endpoint may not exist)", "warning")
                else:
                    self.log(f"⚠️  {method} {path} - {response.status_code}", "warning")
                    
            except requests.RequestException as e:
                endpoint_results[path] = {
                    'error': str(e),
                    'auth_required': auth_required,
                    'success': False
                }
                self.log(f"❌ {method} {path} - Request failed: {e}", "error")
        
        self.results['endpoint_tests'] = endpoint_results
        
        # Count successes
        successes = [r for r in endpoint_results.values() if r.get('success', False)]
        if successes:
            self.results['summary']['passed'] += 1
            return True
        else:
            self.results['summary']['failed'] += 1
            return False
    
    def test_middleware_compatibility(self, token: str) -> bool:
        """Test middleware compatibility with dual secret support"""
        if not token:
            self.log("❌ No token available for middleware testing", "error")
            return False
            
        self.log("🔍 Testing Middleware Dual Secret Support", "info")
        
        # This would require a more complex setup with a test server
        # For now, we'll simulate the middleware logic
        
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        middleware_results = {}
        
        # Simulate the middleware dual secret logic
        secrets_to_try = []
        if supabase_secret:
            secrets_to_try.append(("SUPABASE_JWT_SECRET", supabase_secret))
        if jwt_secret and jwt_secret != "default-secret-key-change-in-production":
            secrets_to_try.append(("JWT_SECRET_KEY", jwt_secret))
        
        middleware_results['secrets_available'] = len(secrets_to_try)
        middleware_results['secret_attempts'] = []
        
        for secret_name, secret_value in secrets_to_try:
            try:
                jwt_service = JWTService(secret_key=secret_value)
                
                # Try different token types
                for token_type in ["api_token", "access"]:
                    try:
                        payload = jwt_service.verify_token(token, expected_type=token_type)
                        if payload:
                            middleware_results['secret_attempts'].append({
                                'secret_name': secret_name,
                                'token_type': token_type,
                                'status': 'success',
                                'user_id': payload.get('user_id') or payload.get('sub')
                            })
                            self.log(f"✅ Middleware simulation: {secret_name} + {token_type} type = SUCCESS")
                            break
                    except Exception as e:
                        middleware_results['secret_attempts'].append({
                            'secret_name': secret_name,
                            'token_type': token_type,
                            'status': 'failed',
                            'error': str(e)
                        })
                        self.log(f"❌ Middleware simulation: {secret_name} + {token_type} type = FAILED: {e}", "debug")
                        
            except Exception as e:
                middleware_results['secret_attempts'].append({
                    'secret_name': secret_name,
                    'status': 'service_failed',
                    'error': str(e)
                })
                self.log(f"❌ Middleware simulation: {secret_name} service creation failed: {e}", "error")
        
        self.results['middleware_tests'] = middleware_results
        
        # Check if any attempt succeeded
        successes = [a for a in middleware_results['secret_attempts'] if a.get('status') == 'success']
        if successes:
            self.log(f"✅ Middleware compatibility test passed ({len(successes)} successful attempts)")
            self.results['summary']['passed'] += 1
            return True
        else:
            self.log("❌ Middleware compatibility test failed - no successful validation attempts", "error")
            self.results['summary']['failed'] += 1
            return False
    
    def run_full_test_suite(self, test_endpoints: bool = False) -> Dict[str, Any]:
        """Run the complete test suite"""
        self.log("🚀 Starting JWT Authentication Verification", "info")
        self.log("=" * 60, "info")
        
        # Test 1: Configuration
        config_ok = self.test_configuration()
        
        # Test 2: Token Generation
        token = self.test_token_generation()
        
        # Test 3: Token Validation
        if token:
            validation_ok = self.test_token_validation(token)
            
            # Test 4: Middleware Compatibility
            middleware_ok = self.test_middleware_compatibility(token)
            
            # Test 5: Endpoints (optional)
            if test_endpoints:
                endpoint_ok = self.test_endpoints(token)
        else:
            self.log("❌ Skipping validation tests - no token generated", "error")
            self.results['summary']['failed'] += 2
        
        # Generate summary
        self.generate_summary()
        
        return self.results
    
    def generate_summary(self):
        """Generate test summary and recommendations"""
        self.log("=" * 60, "info")
        self.log("📊 Test Summary", "info")
        self.log("=" * 60, "info")
        
        summary = self.results['summary']
        total_tests = summary['passed'] + summary['failed'] + summary['warnings']
        
        self.log(f"✅ Passed: {summary['passed']}")
        self.log(f"❌ Failed: {summary['failed']}")
        self.log(f"⚠️  Warnings: {summary['warnings']}")
        self.log(f"📊 Total: {total_tests}")
        
        if summary['failed'] == 0:
            self.log("🎉 All tests passed! JWT authentication should be working correctly.", "info")
        else:
            self.log("🚨 Some tests failed. Review the errors above and check your configuration.", "error")
        
        # Recommendations
        config = self.results.get('configuration', {})
        if not config.get('secrets_match', True):
            self.log("\n💡 RECOMMENDATION: Unify JWT secrets", "info")
            self.log("   Set JWT_SECRET_KEY and SUPABASE_JWT_SECRET to the same value", "info")
            self.log("   See jwt-authentication-configuration.md for details", "info")
        
        if config.get('jwt_secret_key', {}).get('is_default', False):
            self.log("\n🔒 SECURITY: Change default JWT secret", "warning")  
            self.log("   Generate a secure secret: openssl rand -hex 32", "warning")
            
        # Export results for further analysis
        results_file = "jwt_verification_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        self.log(f"\n📄 Detailed results exported to: {results_file}")


def main():
    parser = argparse.ArgumentParser(description='JWT Authentication End-to-End Verification')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL for the API server (default: http://localhost:8000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--test-endpoints', action='store_true',
                       help='Test actual API endpoints (requires running server)')
    
    args = parser.parse_args()
    
    # Check if we can run full tests
    if JWTService is None:
        print("❌ Cannot run full test suite without 4genthub modules")
        print("Run from project root with proper Python environment")
        print("\nQuick configuration check:")
        
        # At least check configuration
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        if not jwt_secret:
            print("❌ JWT_SECRET_KEY not defined")
        else:
            print(f"✅ JWT_SECRET_KEY defined ({len(jwt_secret)} characters)")
            
        if not supabase_secret:
            print("❌ SUPABASE_JWT_SECRET not defined")  
        else:
            print(f"✅ SUPABASE_JWT_SECRET defined ({len(supabase_secret)} characters)")
            
        if jwt_secret and supabase_secret:
            if jwt_secret == supabase_secret:
                print("✅ JWT secrets match")
            else:
                print("⚠️  JWT secrets differ - may cause authentication issues")
                
        sys.exit(1)
    
    # Run tests
    tester = JWTAuthenticationTester(base_url=args.base_url, verbose=args.verbose)
    results = tester.run_full_test_suite(test_endpoints=args.test_endpoints)
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()