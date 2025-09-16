#!/usr/bin/env python3
"""
Deploy clean hooks - backup old hooks and switch to new clean architecture.
"""
import shutil
from pathlib import Path
from datetime import datetime


def deploy_clean_hooks():
    """Deploy the new clean hook architecture."""
    hooks_dir = Path(__file__).parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("=== Deploying Clean Hook Architecture ===\n")
    
    # Backup existing hooks
    print("1. Backing up existing hooks...")
    backup_dir = hooks_dir / f'backup_{timestamp}'
    backup_dir.mkdir(exist_ok=True)
    
    hooks_to_backup = [
        'pre_tool_use.py',
        'post_tool_use.py'
    ]
    
    for hook in hooks_to_backup:
        old_hook = hooks_dir / hook
        if old_hook.exists():
            backup_path = backup_dir / hook
            shutil.copy2(old_hook, backup_path)
            print(f"  ✓ Backed up {hook}")
    
    # Deploy new hooks
    print("\n2. Deploying new clean hooks...")
    
    # Copy clean versions to active names
    deployments = [
        ('pre_tool_use_clean.py', 'pre_tool_use.py'),
        ('post_tool_use_clean.py', 'post_tool_use.py')
    ]
    
    for source, target in deployments:
        source_path = hooks_dir / source
        target_path = hooks_dir / target
        
        if source_path.exists():
            shutil.copy2(source_path, target_path)
            # Make executable
            target_path.chmod(0o755)
            print(f"  ✓ Deployed {target}")
        else:
            print(f"  ✗ Source not found: {source}")
    
    # Verify deployment
    print("\n3. Verifying deployment...")
    
    # Check that new hooks import correctly
    verification_passed = True
    for hook in ['pre_tool_use.py', 'post_tool_use.py']:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            try:
                # Try to import the modules
                import importlib.util
                spec = importlib.util.spec_from_file_location(hook[:-3], hook_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"  ✓ {hook} imports successfully")
            except Exception as e:
                print(f"  ✗ {hook} import failed: {e}")
                verification_passed = False
        else:
            print(f"  ✗ {hook} not found")
            verification_passed = False
    
    # Summary
    print("\n=== Deployment Summary ===")
    if verification_passed:
        print("✅ Clean hooks deployed successfully!")
        print(f"📁 Backups saved to: {backup_dir}")
        print("\nNew architecture features:")
        print("  • SOLID principles applied")
        print("  • Single responsibility components")
        print("  • Modular validators, processors, and hint providers")
        print("  • Centralized configuration from .env.claude")
        print("  • Clean logging to logs/claude directory")
        print("  • Data stored in .claude/data directory")
    else:
        print("⚠️ Deployment completed with errors")
        print(f"📁 Backups available at: {backup_dir}")
        print("   You can restore by copying backup files back")
    
    print("\nTo rollback if needed:")
    print(f"  cp {backup_dir}/*.py {hooks_dir}/")


if __name__ == '__main__':
    deploy_clean_hooks()