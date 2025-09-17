#!/usr/bin/env python3
"""Simple pattern matching test."""

def test_pattern_matching():
    # Simulate the context_triggers
    context_triggers = {
        'Grep': {
            'patterns': ['todo', 'fixme', 'bug', 'error', 'test'],
            'priority': 'low'
        },
        'Glob': {
            'patterns': ['**/*.py', '**/*.js', '**/*.ts', '**/*.md'],
            'priority': 'low'
        }
    }

    test_cases = [
        ("Grep", {"pattern": "todo", "path": "."}),
        ("Grep", {"pattern": "fixme", "glob": "*.py"}),
        ("Grep", {"pattern": "bug report", "path": "src/"}),
        ("Glob", {"pattern": "**/*.py"}),
        ("Glob", {"pattern": "**/*.test.js"}),
    ]

    for tool_name, tool_input in test_cases:
        print(f"Testing: {tool_name} with {tool_input}")

        if tool_name not in context_triggers:
            print(f"  {tool_name} not in context_triggers")
            continue

        trigger_config = context_triggers[tool_name]
        print(f"  trigger_config: {trigger_config}")

        if 'patterns' in trigger_config:
            pattern = tool_input.get('pattern', '') or tool_input.get('query', '')
            print(f"  input pattern: '{pattern}'")
            print(f"  input pattern (lower): '{pattern.lower()}'")

            available_patterns = trigger_config['patterns']
            print(f"  available patterns: {available_patterns}")

            matches = []
            for p in available_patterns:
                match = p in pattern.lower()
                matches.append((p, match))
                print(f"    '{p}' in '{pattern.lower()}' = {match}")

            any_match = any(p in pattern.lower() for p in available_patterns)
            print(f"  final result: any_match = {any_match}")

        print()

if __name__ == "__main__":
    test_pattern_matching()