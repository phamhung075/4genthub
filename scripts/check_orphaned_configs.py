#!/usr/bin/env python3
"""
Check for orphaned configuration entries
"""

import json
import os
from pathlib import Path

def check_package_json(project_root: Path):
    """Check package.json for orphaned references"""

    print("🔍 Checking package.json configurations...")
    print("="*70)

    orphaned = []

    # Check frontend package.json
    frontend_pkg = project_root / "agenthub-frontend" / "package.json"
    if frontend_pkg.exists():
        with open(frontend_pkg, 'r') as f:
            pkg = json.load(f)

        print("\n📦 Frontend package.json:")
        print("─"*70)

        # Check scripts
        scripts = pkg.get('scripts', {})
        suspicious_scripts = []

        for script_name, script_command in scripts.items():
            # Check for common orphaned patterns
            if 'jest' in script_command and not (project_root / "agenthub-frontend" / "jest.config.js").exists():
                suspicious_scripts.append((script_name, "References jest but no jest.config.js"))

            if 'cypress' in script_command and not (project_root / "agenthub-frontend" / "cypress.json").exists():
                suspicious_scripts.append((script_name, "References cypress but no cypress.json"))

        if suspicious_scripts:
            print("\n⚠️  Potentially orphaned scripts:")
            for name, reason in suspicious_scripts:
                print(f"   • {name}: {reason}")
        else:
            print("✅ No orphaned scripts detected")

    return orphaned


def check_vscode_settings(project_root: Path):
    """Check VSCode settings for orphaned references"""

    print("\n\n🔍 Checking VSCode settings...")
    print("="*70)

    vscode_settings = project_root / ".vscode" / "settings.json"

    if not vscode_settings.exists():
        print("   No .vscode/settings.json found")
        return []

    orphaned = []

    try:
        with open(vscode_settings, 'r') as f:
            settings = json.load(f)

        print("\n⚙️  VSCode Settings:")
        print("─"*70)

        # Check Python paths
        python_paths = settings.get('python.analysis.extraPaths', [])
        for path in python_paths:
            full_path = project_root / path
            if not full_path.exists():
                orphaned.append(f"python.analysis.extraPaths: {path} (does not exist)")

        # Check test paths
        test_path = settings.get('python.testing.pytestArgs', [])
        for path in test_path:
            if not path.startswith('-'):  # Skip flags
                full_path = project_root / path
                if not full_path.exists():
                    orphaned.append(f"python.testing.pytestArgs: {path} (does not exist)")

        if orphaned:
            print("\n⚠️  Orphaned settings:")
            for item in orphaned:
                print(f"   • {item}")
        else:
            print("✅ No orphaned VSCode settings detected")

    except json.JSONDecodeError:
        print("❌ Could not parse VSCode settings.json")

    return orphaned


def check_docker_configs(project_root: Path):
    """Check Docker configurations"""

    print("\n\n🔍 Checking Docker configurations...")
    print("="*70)

    docker_compose = project_root / "docker-compose.yml"

    if not docker_compose.exists():
        print("   No docker-compose.yml found")
        return []

    orphaned = []

    # Read docker-compose.yml
    with open(docker_compose, 'r') as f:
        content = f.read()

    print("\n🐳 Docker Compose:")
    print("─"*70)

    # Check for common volume paths
    volume_paths = [
        './agenthub_main',
        './agenthub-frontend',
        './scripts',
        './data'
    ]

    for path in volume_paths:
        if path in content:
            full_path = project_root / path.lstrip('./')
            if not full_path.exists():
                orphaned.append(f"Volume mount: {path} (does not exist)")

    if orphaned:
        print("\n⚠️  Orphaned Docker references:")
        for item in orphaned:
            print(f"   • {item}")
    else:
        print("✅ No orphaned Docker configurations detected")

    return orphaned


def check_pytest_config(project_root: Path):
    """Check pytest configuration"""

    print("\n\n🔍 Checking pytest configuration...")
    print("="*70)

    pytest_ini = project_root / "agenthub_main" / "pytest.ini"
    pyproject = project_root / "agenthub_main" / "pyproject.toml"

    config_file = pytest_ini if pytest_ini.exists() else pyproject

    if not config_file.exists():
        print("   No pytest.ini or pyproject.toml found")
        return []

    orphaned = []

    with open(config_file, 'r') as f:
        content = f.read()

    print(f"\n🧪 Pytest Config ({config_file.name}):")
    print("─"*70)

    # Check for common test paths in config
    if 'testpaths' in content or 'python_files' in content:
        lines = content.split('\n')
        for line in lines:
            if 'testpaths' in line or 'python_files' in line:
                # Extract paths - this is a simple check
                if '=' in line:
                    paths_str = line.split('=')[1].strip()
                    # Simple parsing - just check if major directories exist
                    if 'src/tests' in paths_str:
                        test_dir = project_root / "agenthub_main" / "src" / "tests"
                        if not test_dir.exists():
                            orphaned.append(f"Test path: src/tests (does not exist)")

    if orphaned:
        print("\n⚠️  Orphaned pytest config:")
        for item in orphaned:
            print(f"   • {item}")
    else:
        print("✅ No orphaned pytest configurations detected")

    return orphaned


def check_env_files(project_root: Path):
    """Check for .env.example references to non-existent services"""

    print("\n\n🔍 Checking environment configuration examples...")
    print("="*70)

    env_example = project_root / ".env.example"

    if not env_example.exists():
        print("   No .env.example found")
        return []

    print("\n🔐 Environment Variables:")
    print("─"*70)

    with open(env_example, 'r') as f:
        content = f.read()

    # Check for common orphaned patterns
    orphaned = []

    if 'REDIS' in content:
        # Check if Redis is actually used
        redis_used = False
        for root, dirs, files in os.walk(project_root / "agenthub_main" / "src"):
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    with open(filepath, 'r') as f:
                        if 'redis' in f.read().lower():
                            redis_used = True
                            break
            if redis_used:
                break

        if not redis_used:
            orphaned.append("REDIS_* variables (Redis not used in codebase)")

    if orphaned:
        print("\n⚠️  Potentially orphaned env vars:")
        for item in orphaned:
            print(f"   • {item}")
    else:
        print("✅ No obviously orphaned environment variables")

    return orphaned


def main():
    project_root = Path(__file__).parent.parent

    print("\n" + "="*70)
    print("ORPHANED CONFIGURATION CHECK")
    print("="*70 + "\n")

    all_orphaned = []

    all_orphaned.extend(check_package_json(project_root))
    all_orphaned.extend(check_vscode_settings(project_root))
    all_orphaned.extend(check_docker_configs(project_root))
    all_orphaned.extend(check_pytest_config(project_root))
    all_orphaned.extend(check_env_files(project_root))

    print("\n\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)

    if all_orphaned:
        print(f"\n⚠️  Found {len(all_orphaned)} potential orphaned configurations")
        print("\n💡 RECOMMENDATION:")
        print("   Review each item and either:")
        print("   1. Remove the configuration if truly orphaned")
        print("   2. Create the missing resource if needed")
        print("   3. Update the configuration to point to correct location")
    else:
        print("\n✅ No orphaned configurations detected!")
        print("   All configuration files appear to reference valid resources")

    print("\n" + "="*70 + "\n")

    return 0 if not all_orphaned else 1


if __name__ == '__main__':
    exit(main())
