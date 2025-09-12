#!/usr/bin/env python3
"""
Frontend Authentication Fix Script
This script provides multiple solutions for fixing the frontend task listing issue.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def solution_1_disable_auth():
    """Solution 1: Disable authentication for development."""
    print_section("SOLUTION 1: DISABLE AUTHENTICATION (QUICKEST FIX)")
    
    env_file = Path("/home/daihungpham/__projects__/agentic-project/.env")
    
    print("This solution disables authentication to allow frontend access during development.")
    print("✅ Pros: Immediate fix, no frontend changes needed")
    print("❌ Cons: Security disabled, not suitable for production")
    print()
    
    if env_file.exists():
        print("Steps to implement:")
        print("1. Edit .env file")
        print("2. Change DHAFNCK_AUTH_ENABLED=true to DHAFNCK_AUTH_ENABLED=false")
        print("3. Restart the server")
        print()
        
        # Read current .env
        content = env_file.read_text()
        
        if "DHAFNCK_AUTH_ENABLED=true" in content:
            confirm = input("Do you want to apply this fix? (y/N): ").strip().lower()
            if confirm == 'y':
                # Create backup
                backup_file = env_file.with_suffix('.env.backup')
                backup_file.write_text(content)
                print(f"✅ Backup created: {backup_file}")
                
                # Apply fix
                new_content = content.replace("DHAFNCK_AUTH_ENABLED=true", "DHAFNCK_AUTH_ENABLED=false")
                env_file.write_text(new_content)
                print("✅ Authentication disabled in .env file")
                print("🔄 Please restart the server for changes to take effect")
                return True
            else:
                print("❌ Solution 1 not applied")
        else:
            print("ℹ️ Authentication is already disabled or configuration not found")
    else:
        print("❌ .env file not found")
    
    return False

def solution_2_generate_dev_token():
    """Solution 2: Generate a development token."""
    print_section("SOLUTION 2: GENERATE DEVELOPMENT TOKEN")
    
    print("This solution generates a valid JWT token for development use.")
    print("✅ Pros: Maintains security, allows testing authentication flow")
    print("❌ Cons: Requires frontend configuration changes")
    print()
    
    try:
        # Add src to path for imports
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        
        import jwt
        from datetime import datetime, timedelta
        
        # Read JWT secret from environment
        env_file = Path("/home/daihungpham/__projects__/agentic-project/.env")
        if env_file.exists():
            env_content = env_file.read_text()
            jwt_secret = None
            for line in env_content.split('\n'):
                if line.startswith('JWT_SECRET_KEY='):
                    jwt_secret = line.split('=', 1)[1]
                    break
            
            if jwt_secret:
                # Generate development token
                payload = {
                    'sub': 'dev-user-123',
                    'email': 'developer@localhost.com',
                    'iat': datetime.now(timezone.utc),
                    'exp': datetime.now(timezone.utc) + timedelta(days=30)
                }
                
                token = jwt.encode(payload, jwt_secret, algorithm='HS256')
                
                print("Generated development token:")
                print(f"Token: {token}")
                print()
                print("To use this token:")
                print("1. Open browser developer tools")
                print("2. Go to Application > Cookies")
                print("3. Add cookie: name='access_token', value='{token}'")
                print("4. Refresh the page")
                print()
                
                # Save token to file
                token_file = Path("/home/daihungpham/__projects__/agentic-project/dev_token.txt")
                token_file.write_text(f"access_token={token}\n\nInstructions:\n1. Copy the token above\n2. Set it as 'access_token' cookie in browser\n3. Refresh the frontend")
                print(f"✅ Token saved to: {token_file}")
                return True
            else:
                print("❌ JWT_SECRET_KEY not found in .env file")
        else:
            print("❌ .env file not found")
            
    except ImportError:
        print("❌ PyJWT library not available. Install with: pip install pyjwt")
    except Exception as e:
        print(f"❌ Error generating token: {e}")
    
    return False

def solution_3_mvp_mode_fix():
    """Solution 3: Ensure MVP mode allows unauthenticated access."""
    print_section("SOLUTION 3: MVP MODE AUTHENTICATION BYPASS")
    
    print("This solution ensures MVP mode properly bypasses authentication.")
    print("✅ Pros: Maintains security for production, allows development access")
    print("❌ Cons: May require code changes")
    print()
    
    # Check if MVP mode is enabled
    env_file = Path("/home/daihungpham/__projects__/agentic-project/.env")
    if env_file.exists():
        content = env_file.read_text()
        mvp_enabled = "DHAFNCK_MVP_MODE=true" in content
        auth_enabled = "DHAFNCK_AUTH_ENABLED=true" in content
        
        print(f"Current configuration:")
        print(f"  MVP Mode: {'Enabled' if mvp_enabled else 'Disabled'}")
        print(f"  Auth Required: {'Yes' if auth_enabled else 'No'}")
        print()
        
        if mvp_enabled and auth_enabled:
            print("✅ Configuration is correct for MVP mode")
            print("ℹ️ The issue may be in the authentication middleware logic")
            print()
            print("Recommended actions:")
            print("1. Check authentication middleware bypasses for MVP mode")
            print("2. Verify V2 API routes handle MVP mode correctly")
            print("3. Ensure MCP endpoints respect MVP mode settings")
            return True
        else:
            print("❌ Configuration needs adjustment")
            if not mvp_enabled:
                print("  - MVP mode is disabled")
            if not auth_enabled:
                print("  - Authentication is already disabled")
    
    return False

def solution_4_cors_fix():
    """Solution 4: Fix CORS configuration."""
    print_section("SOLUTION 4: CORS CONFIGURATION FIX")
    
    print("This solution ensures CORS is properly configured for frontend access.")
    print("✅ Pros: Fixes cross-origin issues")
    print("❌ Cons: May not solve authentication issues")
    print()
    
    env_file = Path("/home/daihungpham/__projects__/agentic-project/.env")
    if env_file.exists():
        content = env_file.read_text()
        
        # Check current CORS configuration
        cors_line = None
        for line in content.split('\n'):
            if line.startswith('CORS_ORIGINS='):
                cors_line = line
                break
        
        if cors_line:
            origins = cors_line.split('=', 1)[1]
            print(f"Current CORS origins: {origins}")
            
            # Check if frontend port 3800 is included
            if "3800" not in origins:
                print("❌ Frontend port 3800 not in CORS origins")
                
                confirm = input("Add http://localhost:3800 to CORS origins? (y/N): ").strip().lower()
                if confirm == 'y':
                    new_origins = origins + ",http://localhost:3800"
                    new_content = content.replace(cors_line, f"CORS_ORIGINS={new_origins}")
                    
                    # Create backup
                    backup_file = env_file.with_suffix('.env.backup.cors')
                    backup_file.write_text(content)
                    
                    # Apply fix
                    env_file.write_text(new_content)
                    print("✅ CORS configuration updated")
                    print("🔄 Please restart the server for changes to take effect")
                    return True
            else:
                print("✅ CORS configuration includes frontend port")
        else:
            print("❌ CORS_ORIGINS not found in .env file")
    
    return False

def solution_5_comprehensive_debug():
    """Solution 5: Enable comprehensive debugging."""
    print_section("SOLUTION 5: ENABLE COMPREHENSIVE DEBUGGING")
    
    print("This solution enables detailed debugging to identify the exact issue.")
    print("✅ Pros: Provides detailed information for troubleshooting")
    print("❌ Cons: Generates verbose logs")
    print()
    
    env_file = Path("/home/daihungpham/__projects__/agentic-project/.env")
    if env_file.exists():
        content = env_file.read_text()
        
        changes = []
        
        # Enable debug options
        debug_options = [
            ('DEBUG_SERVICE_ENABLED', 'true'),
            ('DEBUG_HTTP_REQUESTS', 'true'),
            ('DEBUG_API_V2', 'true'),
            ('DEBUG_AUTHENTICATION', 'true'),
            ('DEBUG_FRONTEND_ISSUES', 'true'),
            ('FASTMCP_LOG_LEVEL', 'DEBUG'),
            ('APP_LOG_LEVEL', 'DEBUG')
        ]
        
        for option, value in debug_options:
            if f"{option}={value}" not in content:
                # Find the line and update it
                lines = content.split('\n')
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith(f"{option}="):
                        lines[i] = f"{option}={value}"
                        changes.append(f"{option}: enabled")
                        updated = True
                        break
                if not updated:
                    # Add new line
                    lines.append(f"{option}={value}")
                    changes.append(f"{option}: added")
                content = '\n'.join(lines)
        
        if changes:
            confirm = input(f"Enable {len(changes)} debug options? (y/N): ").strip().lower()
            if confirm == 'y':
                # Create backup
                backup_file = env_file.with_suffix('.env.backup.debug')
                backup_file.write_text(env_file.read_text())
                
                # Apply changes
                env_file.write_text(content)
                print("✅ Debug options enabled:")
                for change in changes:
                    print(f"  - {change}")
                print("🔄 Please restart the server to see detailed logs")
                return True
        else:
            print("✅ Debug options are already enabled")
    
    return False

def main():
    """Main function to present solutions."""
    print("FRONTEND TASK LISTING DEBUG AND FIX SCRIPT")
    print("==========================================")
    print()
    print("This script provides multiple solutions to fix the frontend task listing issue.")
    print("The issue: Frontend shows 'No context available for this task' because")
    print("authentication is enabled but frontend has no valid tokens.")
    print()
    
    solutions = [
        ("Disable Authentication (Quick Fix)", solution_1_disable_auth),
        ("Generate Development Token", solution_2_generate_dev_token),
        ("Fix MVP Mode Authentication", solution_3_mvp_mode_fix),
        ("Fix CORS Configuration", solution_4_cors_fix),
        ("Enable Comprehensive Debugging", solution_5_comprehensive_debug)
    ]
    
    print("Available solutions:")
    for i, (name, _) in enumerate(solutions, 1):
        print(f"{i}. {name}")
    print("0. Run diagnostic only")
    print()
    
    try:
        choice = input("Select a solution (0-5): ").strip()
        
        if choice == "0":
            print_section("DIAGNOSTIC INFORMATION")
            solution_3_mvp_mode_fix()  # This just shows current config
            return
        
        choice_num = int(choice)
        if 1 <= choice_num <= len(solutions):
            name, func = solutions[choice_num - 1]
            print(f"\nExecuting: {name}")
            success = func()
            
            if success:
                print_section("NEXT STEPS")
                print("1. Restart the backend server")
                print("   cd dhafnck_mcp_main && python -m fastmcp.server.mcp_entry_point --transport=streamable-http")
                print("2. Refresh the frontend at http://localhost:3800")
                print("3. Check if task listing now works")
                print("4. If issues persist, run the debug script:")
                print("   python scripts/debug_frontend_tasks.py --comprehensive")
            else:
                print("\n❌ Solution could not be applied. Please check the output above.")
        else:
            print("❌ Invalid choice")
    
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
    except KeyboardInterrupt:
        print("\n👋 Script cancelled by user")

if __name__ == "__main__":
    main()