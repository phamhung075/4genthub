#!/usr/bin/env python3
"""Debug script for context injector pattern matching."""

import sys
import os
import importlib.util

# Load the module directly
spec = importlib.util.spec_from_file_location(
    "context_injector",
    "/home/daihungpham/__projects__/agentic-project/.claude/hooks/utils/context_injector.py"
)
context_injector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_injector)

ContextRelevanceDetector = context_injector.ContextRelevanceDetector

def debug_pattern_matching():
    detector = ContextRelevanceDetector()

    test_cases = [
        ("Grep", {"pattern": "todo", "path": "."}),
        ("Grep", {"pattern": "fixme", "glob": "*.py"}),
        ("Grep", {"pattern": "bug report", "path": "src/"}),
        ("Glob", {"pattern": "**/*.py"}),
        ("Glob", {"pattern": "**/*.test.js"}),
    ]

    print("Debug: Context triggers:")
    print(f"Grep triggers: {detector.context_triggers.get('Grep', 'NOT FOUND')}")
    print(f"Glob triggers: {detector.context_triggers.get('Glob', 'NOT FOUND')}")
    print()

    for tool_name, tool_input in test_cases:
        print(f"Testing: {tool_name} with {tool_input}")

        # Get trigger config
        trigger_config = detector.context_triggers.get(tool_name, {})
        print(f"  trigger_config: {trigger_config}")

        # Check if patterns exist
        has_patterns = 'patterns' in trigger_config
        print(f"  has patterns: {has_patterns}")

        if has_patterns:
            patterns = trigger_config['patterns']
            print(f"  available patterns: {patterns}")

            # Get pattern from tool_input
            pattern = tool_input.get('pattern', '') or tool_input.get('query', '')
            print(f"  input pattern: '{pattern}'")
            print(f"  input pattern (lower): '{pattern.lower()}'")

            # Check each pattern match
            matches = []
            for p in patterns:
                in_pattern = p in pattern.lower()
                matches.append((p, in_pattern))
                print(f"    '{p}' in '{pattern.lower()}': {in_pattern}")

            any_match = any(p in pattern.lower() for p in patterns)
            print(f"  any match: {any_match}")

        # Call the actual method
        is_relevant, priority, context_reqs = detector.is_context_relevant(tool_name, tool_input)
        print(f"  Result: is_relevant={is_relevant}, priority={priority}")
        print()

if __name__ == "__main__":
    debug_pattern_matching()