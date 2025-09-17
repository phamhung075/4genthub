#!/usr/bin/env python3
"""
Security Demonstration Script

This script demonstrates the security improvements in the health check system,
showing how different access levels return different amounts of information.

Run this script to see the difference between:
1. Client-safe health check (minimal info)
2. Authenticated health check (limited details)  
3. Admin health check (full details)
4. Legacy insecure health check (all details exposed)

Author: Security Enhancement
Date: 2025-01-30
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp.server.secure_health_check import secure_health_check, client_health_check, admin_health_check


def print_section(title: str, content: Dict[str, Any]):
    """Print a formatted section"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(content, indent=2, default=str))


async def demonstrate_security_levels():
    """Demonstrate different security levels"""
    
    print("🔒 SECURE HEALTH CHECK DEMONSTRATION")
    print("This demonstrates how different access levels return different information")
    
    # 1. Client-safe health check (minimal information)
    print("\n" + "="*80)
    print("1. CLIENT ACCESS LEVEL - Minimal Information (Production Safe)")
    print("="*80)
    print("This is what external clients should see - no sensitive information exposed.")
    
    client_result = await client_health_check()
    print_section("Client Health Check", client_result)
    
    # 2. Authenticated user health check (limited details)
    print("\n" + "="*80)
    print("2. AUTHENTICATED ACCESS LEVEL - Limited Details")
    print("="*80)
    print("This is what authenticated users can see - basic operational info.")
    
    auth_result = await secure_health_check(
        user_id="authenticated_user",
        is_admin=False,
        is_internal=False
    )
    print_section("Authenticated Health Check", auth_result)
    
    # 3. Admin health check (full details)
    print("\n" + "="*80)
    print("3. ADMIN ACCESS LEVEL - Full Administrative Details")
    print("="*80)
    print("This is what administrators can see - complete system information.")
    
    admin_result = await admin_health_check(user_id="admin_user")
    print_section("Admin Health Check", admin_result)
    
    # 4. Security comparison
    print("\n" + "="*80)
    print("4. SECURITY COMPARISON")
    print("="*80)
    
    print("\n🔒 INFORMATION EXPOSURE ANALYSIS:")
    print("-" * 40)
    
    # Check what information is exposed at each level
    client_keys = set(client_result.keys())
    auth_keys = set(auth_result.keys())
    admin_keys = set(admin_result.keys())
    
    print(f"Client Level Keys: {sorted(client_keys)}")
    print(f"Auth Level Keys: {sorted(auth_keys)}")
    print(f"Admin Level Keys: {sorted(admin_keys)}")
    
    print(f"\nInformation Progression:")
    print(f"• Client → Auth: +{len(auth_keys - client_keys)} additional fields")
    print(f"• Auth → Admin: +{len(admin_keys - auth_keys)} additional fields")
    print(f"• Total Admin Fields: {len(admin_keys)} fields")
    
    # Check for sensitive information
    sensitive_fields = ['environment', 'pythonpath', 'tasks_json_path', 'projects_file_path']
    
    print(f"\n🚨 SENSITIVE INFORMATION EXPOSURE:")
    print("-" * 40)
    
    for level, result in [("Client", client_result), ("Auth", auth_result), ("Admin", admin_result)]:
        exposed_sensitive = []
        for field in sensitive_fields:
            if field in result or any(field in str(v) for v in result.values() if isinstance(v, dict)):
                exposed_sensitive.append(field)
        
        if exposed_sensitive:
            print(f"• {level}: ⚠️  Exposes {exposed_sensitive}")
        else:
            print(f"• {level}: ✅ No sensitive paths exposed")
    
    print(f"\n✅ SECURITY RECOMMENDATIONS:")
    print("-" * 40)
    print("• Use CLIENT level for public/external health checks")
    print("• Use AUTHENTICATED level for logged-in users")
    print("• Use ADMIN level only for administrative interfaces")
    print("• Never expose full details to untrusted clients")
    print("• Implement proper authentication before using higher access levels")


async def demonstrate_legacy_vs_secure():
    """Demonstrate the difference between legacy and secure approaches"""
    
    print("\n" + "="*80)
    print("LEGACY vs SECURE COMPARISON")
    print("="*80)
    
    print("\n🔓 LEGACY APPROACH (INSECURE):")
    print("The old health check exposed ALL information to ANY client:")
    
    # Simulate what the legacy system would return
    legacy_example = {
        "success": True,
        "status": "healthy",
        "server_name": "agenthub - Task Management & Agent Orchestration",
        "version": "2.1.0",
        "environment": {
            "pythonpath": "/app/src:/app",
            "tasks_json_path": "/data/tasks",
            "projects_file_path": "/data/projects/projects.json",
            "agent_library_dir": "/app/agent-library",
            "auth_enabled": "true",
            "supabase_configured": False
        },
        "authentication": {"enabled": True, "mvp_mode": False},
        "connections": {"active_connections": 0, "server_restart_count": 0}
    }
    
    print_section("Legacy Health Check (INSECURE)", legacy_example)
    
    print("\n🔒 SECURE APPROACH:")
    print("The new system filters information based on access level:")
    
    secure_client = await client_health_check()
    print_section("Secure Client Health Check", secure_client)
    
    print(f"\n📊 SECURITY IMPROVEMENT:")
    print("-" * 40)
    legacy_info_count = len(str(legacy_example))
    secure_info_count = len(str(secure_client))
    reduction_percent = ((legacy_info_count - secure_info_count) / legacy_info_count) * 100
    
    print(f"• Legacy response size: {legacy_info_count} characters")
    print(f"• Secure client response size: {secure_info_count} characters")
    print(f"• Information reduction: {reduction_percent:.1f}%")
    print(f"• Sensitive paths exposed: Legacy=YES, Secure=NO")


if __name__ == "__main__":
    print("🔒 SECURE HEALTH CHECK SECURITY DEMONSTRATION")
    print("=" * 80)
    
    try:
        asyncio.run(demonstrate_security_levels())
        asyncio.run(demonstrate_legacy_vs_secure())
        
        print("\n" + "="*80)
        print("✅ DEMONSTRATION COMPLETE")
        print("="*80)
        print("\nKey Takeaways:")
        print("• Different access levels return appropriate information")
        print("• Client-safe responses prevent information disclosure")
        print("• Admin responses provide full diagnostic information")
        print("• Proper access control is essential for security")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        sys.exit(1) 