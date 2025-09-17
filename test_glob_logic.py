#!/usr/bin/env python3
"""Test different matching logic for Glob patterns."""

def test_current_logic():
    print("=== Current Logic (p in pattern.lower()) ===")
    trigger_patterns = ['**/*.py', '**/*.js', '**/*.ts', '**/*.md']
    test_patterns = ['**/*.py', '**/*.test.js']

    for test_pattern in test_patterns:
        matches = []
        for p in trigger_patterns:
            match = p in test_pattern.lower()
            matches.append((p, match))
            print(f"'{p}' in '{test_pattern}' = {match}")
        any_match = any(p in test_pattern.lower() for p in trigger_patterns)
        print(f"Result for '{test_pattern}': {any_match}")
        print()

def test_extension_logic():
    print("=== Extension Logic (pattern ends with extension) ===")
    trigger_patterns = ['**/*.py', '**/*.js', '**/*.ts', '**/*.md']
    test_patterns = ['**/*.py', '**/*.test.js']

    for test_pattern in test_patterns:
        matches = []
        for p in trigger_patterns:
            # Extract extension from trigger pattern
            if '*.' in p:
                ext = '.' + p.split('*.')[-1]
                match = test_pattern.lower().endswith(ext)
                matches.append((p, ext, match))
                print(f"'{test_pattern}' ends with '{ext}' (from '{p}') = {match}")

        any_match = any(
            test_pattern.lower().endswith('.' + p.split('*.')[-1])
            for p in trigger_patterns if '*.' in p
        )
        print(f"Result for '{test_pattern}': {any_match}")
        print()

def test_contains_logic():
    print("=== Contains Logic (more flexible) ===")
    trigger_patterns = ['**/*.py', '**/*.js', '**/*.ts', '**/*.md']
    test_patterns = ['**/*.py', '**/*.test.js']

    for test_pattern in test_patterns:
        matches = []
        for p in trigger_patterns:
            # Extract extension and check if test pattern contains it
            if '*.' in p:
                ext = '.' + p.split('*.')[-1]
                match = ext in test_pattern.lower()
                matches.append((p, ext, match))
                print(f"'{ext}' (from '{p}') in '{test_pattern}' = {match}")

        any_match = any(
            ('.' + p.split('*.')[-1]) in test_pattern.lower()
            for p in trigger_patterns if '*.' in p
        )
        print(f"Result for '{test_pattern}': {any_match}")
        print()

if __name__ == "__main__":
    test_current_logic()
    test_extension_logic()
    test_contains_logic()