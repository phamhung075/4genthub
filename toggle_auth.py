#!/usr/bin/env python3
"""
Toggle Authentication On/Off for Development

This script allows you to quickly enable or disable authentication
for development purposes.
"""
import os
import sys
from pathlib import Path

def read_env_file(env_path):
    """Read environment file and return lines"""
    with open(env_path, 'r') as f:
        return f.readlines()

def write_env_file(env_path, lines):
    """Write lines back to environment file"""
    with open(env_path, 'w') as f:
        f.writelines(lines)

def toggle_auth(enable=None):
    """Toggle AUTH_ENABLED in .env.dev file"""
    env_path = Path('.env.dev')

    if not env_path.exists():
        print("❌ .env.dev not found!")
        return False

    lines = read_env_file(env_path)
    auth_found = False
    new_lines = []

    for line in lines:
        if line.strip().startswith('AUTH_ENABLED='):
            auth_found = True
            current_value = line.split('=')[1].strip().lower()

            if enable is None:
                # Toggle current value
                new_value = 'false' if current_value == 'true' else 'true'
            else:
                new_value = 'true' if enable else 'false'

            new_lines.append(f'AUTH_ENABLED={new_value}\n')
            print(f"✅ Changed AUTH_ENABLED from {current_value} to {new_value}")
        else:
            new_lines.append(line)

    if not auth_found:
        # Add AUTH_ENABLED if not found
        new_value = 'true' if enable else 'false'
        new_lines.append(f'\nAUTH_ENABLED={new_value}\n')
        print(f"✅ Added AUTH_ENABLED={new_value}")

    write_env_file(env_path, new_lines)
    return True

def main():
    """Main function"""
    print("🔐 Authentication Toggle Script")
    print("=" * 40)

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['on', 'enable', 'true', '1']:
            toggle_auth(enable=True)
        elif arg in ['off', 'disable', 'false', '0']:
            toggle_auth(enable=False)
        else:
            print("Usage: python toggle_auth.py [on|off]")
            return
    else:
        # Interactive mode
        print("\nCurrent authentication status:")
        env_path = Path('.env.dev')
        if env_path.exists():
            lines = read_env_file(env_path)
            for line in lines:
                if line.strip().startswith('AUTH_ENABLED='):
                    current = line.split('=')[1].strip()
                    print(f"  AUTH_ENABLED = {current}")
                    break

        print("\nOptions:")
        print("  1. Enable authentication (AUTH_ENABLED=true)")
        print("  2. Disable authentication (AUTH_ENABLED=false)")
        print("  3. Toggle current value")
        print("  4. Exit")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == '1':
            toggle_auth(enable=True)
        elif choice == '2':
            toggle_auth(enable=False)
        elif choice == '3':
            toggle_auth(enable=None)
        elif choice == '4':
            print("👋 Exiting...")
            return
        else:
            print("❌ Invalid choice")
            return

    print("\n⚠️  IMPORTANT: You need to restart the backend for changes to take effect!")
    print("  Run: pkill -f 'python.*mcp_entry_point' && python agenthub_main/src/fastmcp/server/mcp_entry_point.py")

if __name__ == "__main__":
    main()