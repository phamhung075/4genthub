#!/usr/bin/env python3
"""
Test Coverage Analysis Script
Identifies Python source files in 4genthub_main/src that don't have corresponding tests.
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Dict, Set

def find_python_files(directory: str, exclude_patterns: List[str] = None) -> List[Path]:
    """Find all Python files in a directory, excluding patterns."""
    if exclude_patterns is None:
        exclude_patterns = ['__pycache__', '*.pyc', '__init__.py']
    
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_patterns)]
        
        for file in files:
            if file.endswith('.py'):
                # Skip excluded files
                if any(fnmatch.fnmatch(file, pattern) for pattern in exclude_patterns):
                    continue
                    
                file_path = Path(root) / file
                python_files.append(file_path)
    
    return python_files

def get_expected_test_path(source_file: Path, src_dir: Path, test_dir: Path) -> Path:
    """Generate the expected test file path for a source file."""
    # Get relative path from src directory
    relative_path = source_file.relative_to(src_dir)
    
    # Convert to test path
    test_relative_path = Path('unit') / relative_path
    
    # Change extension to _test.py
    test_file_name = test_relative_path.stem + '_test.py'
    test_path = test_dir / test_relative_path.parent / test_file_name
    
    return test_path

def analyze_test_coverage():
    """Analyze test coverage and identify missing tests."""
    base_dir = Path('4genthub_main')
    src_dir = base_dir / 'src' / 'fastmcp'
    test_dir = base_dir / 'src' / 'tests'
    
    # Find all source files
    source_files = find_python_files(str(src_dir))
    
    # Find all test files
    test_files = find_python_files(str(test_dir))
    test_file_paths = set(str(f) for f in test_files)
    
    # Analyze coverage
    missing_tests = []
    covered_files = []
    
    for source_file in source_files:
        expected_test_path = get_expected_test_path(source_file, src_dir, test_dir)
        
        if str(expected_test_path) in test_file_paths:
            covered_files.append(source_file)
        else:
            # Check if test exists with different naming conventions
            alt_test_paths = [
                expected_test_path.parent / (expected_test_path.stem.replace('_test', '_tests') + '.py'),
                expected_test_path.parent / ('test_' + source_file.stem + '.py'),
            ]
            
            found_alternative = False
            for alt_path in alt_test_paths:
                if str(alt_path) in test_file_paths:
                    covered_files.append(source_file)
                    found_alternative = True
                    break
            
            if not found_alternative:
                missing_tests.append({
                    'source_file': source_file,
                    'expected_test_path': expected_test_path,
                    'domain': get_domain_from_path(source_file),
                    'layer': get_layer_from_path(source_file)
                })
    
    return missing_tests, covered_files, source_files

def get_domain_from_path(file_path: Path) -> str:
    """Extract domain from file path."""
    parts = file_path.parts
    domains = ['task_management', 'connection_management', 'auth']
    
    for part in parts:
        if part in domains:
            return part
    
    return 'core'

def get_layer_from_path(file_path: Path) -> str:
    """Extract DDD layer from file path."""
    parts = file_path.parts
    layers = ['domain', 'application', 'infrastructure', 'interface']
    
    for part in parts:
        if part in layers:
            return part
    
    return 'other'

def prioritize_missing_tests(missing_tests: List[Dict]) -> Dict[str, List[Dict]]:
    """Prioritize missing tests by importance."""
    priorities = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }
    
    for missing in missing_tests:
        source_file = missing['source_file']
        file_name = source_file.name
        layer = missing['layer']
        domain = missing['domain']
        
        # Critical: Core domain services, entities, and use cases
        if (layer in ['domain', 'application'] and 
            ('service' in file_name or 'entity' in file_name or 'use_case' in file_name or 
             'facade' in file_name or 'repository' in file_name)):
            priorities['critical'].append(missing)
        
        # High: Application facades and controllers
        elif (layer == 'application' and 'facade' in file_name) or \
             (layer == 'interface' and 'controller' in file_name):
            priorities['high'].append(missing)
        
        # Medium: Infrastructure components and value objects
        elif layer == 'infrastructure' or 'value_object' in file_name:
            priorities['medium'].append(missing)
        
        # Low: Everything else
        else:
            priorities['low'].append(missing)
    
    return priorities

def generate_report():
    """Generate the test coverage report."""
    missing_tests, covered_files, all_source_files = analyze_test_coverage()
    priorities = prioritize_missing_tests(missing_tests)
    
    total_files = len(all_source_files)
    covered_count = len(covered_files)
    missing_count = len(missing_tests)
    coverage_percent = (covered_count / total_files * 100) if total_files > 0 else 0
    
    print("=" * 80)
    print("TEST COVERAGE ANALYSIS REPORT")
    print("=" * 80)
    print(f"Total Source Files: {total_files}")
    print(f"Files with Tests: {covered_count}")
    print(f"Files without Tests: {missing_count}")
    print(f"Coverage: {coverage_percent:.1f}%")
    print()
    
    print("MISSING TESTS BY PRIORITY:")
    print("-" * 40)
    
    for priority, items in priorities.items():
        if not items:
            continue
            
        print(f"\n{priority.upper()} PRIORITY ({len(items)} files):")
        print("=" * 30)
        
        # Group by domain and layer
        by_domain = {}
        for item in items:
            domain = item['domain']
            if domain not in by_domain:
                by_domain[domain] = {}
            
            layer = item['layer']
            if layer not in by_domain[domain]:
                by_domain[domain][layer] = []
            
            by_domain[domain][layer].append(item)
        
        for domain, layers in by_domain.items():
            print(f"\n  {domain.upper()}:")
            for layer, files in layers.items():
                print(f"    {layer}:")
                for file_info in files[:5]:  # Show first 5
                    source_file = file_info['source_file']
                    print(f"      - {source_file}")
                if len(files) > 5:
                    print(f"      ... and {len(files) - 5} more")
    
    # Generate summary for each domain
    print(f"\nSUMMARY BY DOMAIN:")
    print("-" * 30)
    domain_stats = {}
    for missing in missing_tests:
        domain = missing['domain']
        if domain not in domain_stats:
            domain_stats[domain] = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        # Determine priority
        layer = missing['layer']
        file_name = missing['source_file'].name
        
        if (layer in ['domain', 'application'] and 
            ('service' in file_name or 'entity' in file_name or 'use_case' in file_name or 
             'facade' in file_name or 'repository' in file_name)):
            domain_stats[domain]['critical'] += 1
        elif (layer == 'application' and 'facade' in file_name) or \
             (layer == 'interface' and 'controller' in file_name):
            domain_stats[domain]['high'] += 1
        elif layer == 'infrastructure' or 'value_object' in file_name:
            domain_stats[domain]['medium'] += 1
        else:
            domain_stats[domain]['low'] += 1
    
    for domain, stats in domain_stats.items():
        total = sum(stats.values())
        print(f"{domain}: {total} missing tests")
        print(f"  Critical: {stats['critical']}, High: {stats['high']}, Medium: {stats['medium']}, Low: {stats['low']}")
    
    return priorities

if __name__ == "__main__":
    generate_report()