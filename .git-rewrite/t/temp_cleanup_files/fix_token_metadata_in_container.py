#!/usr/bin/env python3
"""
Fix token metadata in running Docker container.

Replace all instances of direct metadata access with proper dict check.
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    container_name = "dhafnck-mcp-server"
    file_path = "/app/src/fastmcp/server/routes/token_router.py"
    
    print("🔧 Fixing token metadata in running container...")
    
    # First, let's backup the current file
    backup_cmd = f"docker exec {container_name} cp {file_path} {file_path}.backup"
    success, out, err = run_command(backup_cmd)
    if not success:
        print(f"❌ Failed to backup file: {err}")
        return False
    
    print("✅ Backed up original file")
    
    # Fix the metadata references using sed commands
    fixes = [
        # Fix the direct metadata references in FastAPI endpoints
        's/metadata=token.metadata/metadata=token.token_metadata if isinstance(token.token_metadata, dict) else {}/g',
        # Fix any remaining direct metadata access
        's/metadata=old_token.token_metadata/metadata=old_token.token_metadata if isinstance(old_token.token_metadata, dict) else {}/g',
        's/metadata=new_token.metadata/metadata=new_token.token_metadata if isinstance(new_token.token_metadata, dict) else {}/g',
    ]
    
    for fix in fixes:
        cmd = f"docker exec {container_name} sed -i '{fix}' {file_path}"
        success, out, err = run_command(cmd)
        if success:
            print(f"✅ Applied fix: {fix}")
        else:
            print(f"⚠️  Could not apply fix: {fix} - {err}")
    
    print("🔄 Restarting container to apply changes...")
    restart_cmd = f"docker restart {container_name}"
    success, out, err = run_command(restart_cmd)
    if success:
        print("✅ Container restarted successfully")
        return True
    else:
        print(f"❌ Failed to restart container: {err}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)