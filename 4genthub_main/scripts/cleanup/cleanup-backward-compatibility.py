#!/usr/bin/env python3
"""
Clean up backward compatibility code for Supabase.
This script removes all Supabase references and ensures clean PostgreSQL + Keycloak setup.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent

# Files to check and clean
FILES_TO_CLEAN = [
    "docker-system/docker-compose.yml",
    "4genthub_main/src/fastmcp/server/routes/auth_starlette.py",
    "4genthub_main/src/fastmcp/server/routes/auth_keycloak_enhanced.py",
    "4genthub_main/src/fastmcp/server/manage_connection_tool.py",
    "4genthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py",
    "4genthub_main/src/fastmcp/task_management/infrastructure/database/database_initializer.py",
    "4genthub-frontend/src/contexts/AuthContext.tsx",
]

# Files to remove (no longer needed)
FILES_TO_REMOVE = [
    "docker-compose.supabase.yml",
    "start-supabase-local.sh",
    "debug_supabase_connectivity.py",
    "clean_supabase_data.py",
]

def backup_file(filepath: Path) -> None:
    """Create a backup of a file before modifying it."""
    backup_path = filepath.with_suffix(filepath.suffix + '.backup')
    if not backup_path.exists():
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backed up: {filepath} -> {backup_path}")

def remove_supabase_imports(content: str) -> str:
    """Remove Supabase-related imports."""
    patterns = [
        r'^from supabase.*$',
        r'^import supabase.*$',
        r'^.*supabase_client.*$',
        r'^.*SupabaseClient.*$',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    return content

def remove_supabase_config(content: str) -> str:
    """Remove Supabase configuration lines."""
    patterns = [
        r'SUPABASE_[A-Z_]+\s*=.*',
        r'supabase_[a-z_]+\s*=.*',
        r'.*\${SUPABASE_.*?\}.*',
        r'.*\${REACT_APP_SUPABASE_.*?\}.*',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern + '\n', '', content)
    
    return content

def clean_database_config(content: str) -> str:
    """Clean database configuration to only support PostgreSQL."""
    # Remove Supabase-specific database type checks
    content = re.sub(
        r'if\s+.*database_type.*==.*["\']supabase["\'].*:.*?\n(?:\s+.*?\n)*?else:',
        'if False:  # Removed Supabase support\n    pass\nelse:',
        content,
        flags=re.DOTALL
    )
    
    # Set default database type to postgresql
    content = re.sub(
        r'database_type\s*=\s*os\.getenv\(["\']DATABASE_TYPE["\']\s*,\s*["\'].*?["\']\)',
        'database_type = os.getenv("DATABASE_TYPE", "postgresql")',
        content
    )
    
    return content

def clean_authentication_code(content: str) -> str:
    """Clean authentication code to only use Keycloak."""
    # Remove Supabase authentication checks
    patterns = [
        r'.*supabase.*authentication.*',
        r'.*if.*auth_provider.*==.*["\']supabase["\'].*',
        r'.*SupabaseAuthProvider.*',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern + '.*\n', '', content, flags=re.IGNORECASE)
    
    return content

def clean_frontend_auth(content: str) -> str:
    """Clean frontend authentication to remove Supabase."""
    # Remove Supabase client initialization
    content = re.sub(
        r'const\s+supabase\s*=.*?;.*?\n',
        '',
        content
    )
    
    # Remove Supabase imports
    content = re.sub(
        r"import.*from\s+['\"]@supabase/.*?['\"];?\n",
        '',
        content
    )
    
    return content

def process_file(filepath: Path) -> bool:
    """Process a single file to remove Supabase references."""
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return False
    
    try:
        # Backup the file
        backup_file(filepath)
        
        # Read content
        content = filepath.read_text()
        original_content = content
        
        # Apply cleanups based on file type
        if filepath.suffix == '.py':
            content = remove_supabase_imports(content)
            content = remove_supabase_config(content)
            content = clean_database_config(content)
            content = clean_authentication_code(content)
        elif filepath.suffix in ['.yml', '.yaml']:
            content = remove_supabase_config(content)
        elif filepath.suffix in ['.tsx', '.ts', '.jsx', '.js']:
            content = clean_frontend_auth(content)
            content = remove_supabase_config(content)
        
        # Write back if changed
        if content != original_content:
            filepath.write_text(content)
            print(f"✅ Cleaned: {filepath}")
            return True
        else:
            print(f"ℹ️  No changes needed: {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def remove_obsolete_files() -> None:
    """Remove files that are no longer needed."""
    for filename in FILES_TO_REMOVE:
        filepath = PROJECT_ROOT / filename
        if filepath.exists():
            try:
                if filepath.is_file():
                    filepath.unlink()
                    print(f"🗑️  Removed: {filepath}")
                elif filepath.is_dir():
                    shutil.rmtree(filepath)
                    print(f"🗑️  Removed directory: {filepath}")
            except Exception as e:
                print(f"❌ Error removing {filepath}: {e}")

def main():
    print("=" * 60)
    print("BACKWARD COMPATIBILITY CLEANUP")
    print("Removing all Supabase references...")
    print("=" * 60)
    
    # Process files to clean
    cleaned_count = 0
    for filename in FILES_TO_CLEAN:
        filepath = PROJECT_ROOT / filename
        if process_file(filepath):
            cleaned_count += 1
    
    # Remove obsolete files
    print("\n" + "=" * 60)
    print("Removing obsolete files...")
    print("=" * 60)
    remove_obsolete_files()
    
    print("\n" + "=" * 60)
    print(f"CLEANUP COMPLETE")
    print(f"Files cleaned: {cleaned_count}")
    print("=" * 60)
    
    print("\n📝 Next steps:")
    print("1. Review the changes made")
    print("2. Copy .env.clean to .env and update with your Keycloak details")
    print("3. Run: docker-compose up -d postgres")
    print("4. Run: python 4genthub_main/scripts/init_database.py")
    print("5. Configure your Keycloak instance")
    print("6. Test the authentication flow")

if __name__ == "__main__":
    main()