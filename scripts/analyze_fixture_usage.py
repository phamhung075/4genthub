#!/usr/bin/env python3
"""
Pytest Fixture Usage Analyzer
Scans pytest fixtures and checks if they're actually used in the test suite
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set

def extract_fixtures_from_file(file_path: Path) -> List[Tuple[str, int]]:
    """Extract fixture names and line numbers from a Python file"""
    fixtures = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                # Match @pytest.fixture decorator
                if '@pytest.fixture' in line:
                    # Look ahead for function definition
                    for j in range(i, min(i+5, len(lines)+1)):
                        func_match = re.match(r'^\s*def\s+(\w+)\s*\(', lines[j-1])
                        if func_match:
                            fixture_name = func_match.group(1)
                            fixtures.append((fixture_name, i))
                            break
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return fixtures

def find_fixture_usage(fixture_name: str, tests_dir: Path) -> List[str]:
    """Find files that use a specific fixture"""
    usage_files = []

    try:
        # Search for fixture usage in function parameters
        result = subprocess.run(
            ['grep', '-r', '-l', f'def.*{fixture_name}.*:', str(tests_dir)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            usage_files.extend([
                line.strip() for line in result.stdout.strip().split('\n')
                if line.strip() and '.py' in line
            ])

        # Also check for pytest.param or indirect usage
        result2 = subprocess.run(
            ['grep', '-r', '-l', f'pytest.param.*{fixture_name}', str(tests_dir)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result2.returncode == 0:
            usage_files.extend([
                line.strip() for line in result2.stdout.strip().split('\n')
                if line.strip() and '.py' in line
            ])

    except subprocess.TimeoutExpired:
        print(f"Timeout searching for {fixture_name}")
    except Exception as e:
        print(f"Error searching for {fixture_name}: {e}")

    return list(set(usage_files))  # Remove duplicates

def analyze_fixture_usage(tests_dir: Path) -> Dict[str, any]:
    """Analyze all fixtures in tests directory"""

    print("🔍 Scanning for pytest fixtures...")

    all_fixtures = {}
    fixture_files = []

    # Find all Python files with fixtures
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                fixtures_in_file = extract_fixtures_from_file(file_path)

                if fixtures_in_file:
                    fixture_files.append(file_path)
                    for fixture_name, line_num in fixtures_in_file:
                        all_fixtures[fixture_name] = {
                            'file': str(file_path.relative_to(tests_dir.parent)),
                            'line': line_num,
                            'used_in': []
                        }

    print(f"   Found {len(all_fixtures)} fixtures in {len(fixture_files)} files")
    print(f"\n🔎 Checking fixture usage...")

    # Check usage for each fixture
    for i, (fixture_name, info) in enumerate(all_fixtures.items(), 1):
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(all_fixtures)} fixtures checked...")

        # Skip autouse fixtures - they're automatically used
        if 'autouse=True' in str(info['file']):
            fixture_file = tests_dir.parent / info['file']
            with open(fixture_file, 'r') as f:
                content = f.read()
                if f'@pytest.fixture' in content:
                    # Check if this specific fixture has autouse
                    lines = content.split('\n')
                    for idx in range(max(0, info['line']-5), min(len(lines), info['line']+5)):
                        if 'autouse=True' in lines[idx]:
                            info['autouse'] = True
                            break

        # Find usage
        usage_files = find_fixture_usage(fixture_name, tests_dir)

        # Filter out the definition file itself (unless it's also used there)
        definition_file = str((tests_dir.parent / info['file']).resolve())
        usage_files_filtered = []

        for usage_file in usage_files:
            usage_path = Path(usage_file).resolve()
            if str(usage_path) == definition_file:
                # Check if it's actually used in the same file (not just defined)
                with open(usage_path, 'r') as f:
                    content = f.read()
                    # Count occurrences - if more than 1, it's used elsewhere in same file
                    if content.count(f'def {fixture_name}(') > 0 and content.count(fixture_name) > 1:
                        usage_files_filtered.append(usage_file)
            else:
                usage_files_filtered.append(usage_file)

        info['used_in'] = usage_files_filtered

    return all_fixtures

def generate_report(fixtures: Dict[str, any]) -> None:
    """Generate report of unused fixtures"""

    unused_fixtures = {
        name: info for name, info in fixtures.items()
        if not info['used_in'] and not info.get('autouse', False)
    }

    print(f"\n{'='*70}")
    print(f"📊 FIXTURE USAGE ANALYSIS RESULTS")
    print(f"{'='*70}\n")

    print(f"Total fixtures found: {len(fixtures)}")
    print(f"Autouse fixtures (always used): {sum(1 for f in fixtures.values() if f.get('autouse', False))}")
    print(f"Used fixtures: {sum(1 for f in fixtures.values() if f['used_in'])}")
    print(f"Unused fixtures: {len(unused_fixtures)}")

    if unused_fixtures:
        print(f"\n⚠️  POTENTIALLY UNUSED FIXTURES ({len(unused_fixtures)}):")
        print(f"{'─'*70}\n")

        # Group by file
        by_file = {}
        for name, info in unused_fixtures.items():
            file = info['file']
            if file not in by_file:
                by_file[file] = []
            by_file[file].append((name, info['line']))

        for file, fixtures_list in sorted(by_file.items()):
            print(f"\n📄 {file}")
            for name, line in sorted(fixtures_list, key=lambda x: x[1]):
                print(f"   Line {line:4d}: {name}()")
    else:
        print(f"\n✅ All fixtures are being used!")

    print(f"\n{'='*70}\n")

def main():
    # Get tests directory relative to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    tests_dir = project_root / 'agenthub_main' / 'src' / 'tests'

    if not tests_dir.exists():
        print(f"❌ Tests directory not found: {tests_dir}")
        return 1

    fixtures = analyze_fixture_usage(tests_dir)
    generate_report(fixtures)

    return 0

if __name__ == '__main__':
    exit(main())
